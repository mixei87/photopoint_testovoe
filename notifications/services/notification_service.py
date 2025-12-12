"""
Сервис для отправки уведомлений через различные провайдеры.
"""

import asyncio
import logging
from typing import Any, TypeVar
from asgiref.sync import sync_to_async
from ..models import Notification, NotificationStatus
from .providers import (
    EmailProvider,
    SMSProvider,
    TelegramProvider,
    NotificationProvider,
)
from asyncio import TimeoutError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=NotificationProvider)


class NotificationService:
    """Сервис для управления отправкой уведомлений."""

    PROVIDERS: dict[str, NotificationProvider] = {
        "email": EmailProvider(),
        "sms": SMSProvider(),
        "telegram": TelegramProvider(),
    }

    # Таймаут по умолчанию для каждого типа уведомления (в секундах)
    DEFAULT_TIMEOUT = 15

    def __init__(self, user=None):
        """Инициализация сервиса уведомлений.

        Args:
            user: Пользователь, которому отправляются уведомления
        """
        self.user = user

    async def send_notification(
        self,
        message: str,
        priority: list[str] | None = None,
        **provider_kwargs: Any,
    ) -> bool:
        """
        Асинхронно отправляет уведомление пользователю через указанные провайдеры по приоритету.

        Args:
            message: Текст уведомления
            priority: Список типов уведомлений в порядке приоритета, например ['telegram', 'email', 'sms']
            **provider_kwargs: Дополнительные аргументы для провайдеров
                - provider_timeout (int): Таймаут для каждого типа уведомления (в секундах)

        Returns:
            bool: True, если уведомление было успешно отправлено хотя бы одним провайдером
        """
        if priority is None:
            priority = ["telegram", "email", "sms"]
        logger.info(
            f"[NotificationService] Start send, user={getattr(self.user, 'id', None)}, priority={priority}"
        )

        if not self.user:
            logger.error("Не указан пользователь для отправки уведомления")
            return False
        provider_timeout = provider_kwargs.pop("provider_timeout", self.DEFAULT_TIMEOUT)

        async def try_send_with_provider(
            notification_type: str,
        ) -> tuple[str, str] | None:
            """Пытается отправить уведомление указанного типа.

            Для каждой попытки создаётся отдельная запись Notification с
            notification_type, равным типу уведомления (email, sms, telegram).
            """
            if notification_type not in self.PROVIDERS:
                logger.warning(
                    f"Тип уведомления {notification_type} не найден в доступных провайдерах"
                )
                return None
            notification = await sync_to_async(Notification.objects.create)(
                user=self.user,
                message=message,
                status=NotificationStatus.PENDING.value,
                notification_type=notification_type,
            )
            provider = self.PROVIDERS[notification_type]
            recipient = self._get_recipient_for_notification_type(notification_type)
            if not recipient:
                logger.warning(
                    f"[NotificationService] Нет получателя для типа уведомления {notification_type}"
                )
                await sync_to_async(notification.mark_as_failed)(
                    error_message="no recipient for provider",
                )
                return None
            try:
                provider_kwargs.setdefault(notification_type, {})[
                    "timeout"
                ] = provider_timeout

                success = await asyncio.wait_for(
                    provider.send(
                        recipient=recipient,
                        message=message,
                        **provider_kwargs.get(notification_type, {}),
                    ),
                    timeout=provider_timeout,
                )

                if success:
                    await sync_to_async(notification.mark_as_sent)(
                        provider_data={
                            "provider": notification_type,
                            "recipient": recipient,
                        }
                    )
                    return notification_type, recipient

                await sync_to_async(notification.mark_as_failed)(
                    error_message="provider returned False",
                )

            except TimeoutError:
                logger.warning(
                    f"[NotificationService] Таймаут при отправке уведомления типа {notification_type}"
                )
                await sync_to_async(notification.mark_as_failed)(
                    error_message="provider timeout",
                )
            except Exception as e:
                logger.error(
                    f"[NotificationService] Ошибка при отправке уведомления типа {notification_type}: {str(e)}",
                    exc_info=True,
                )
                await sync_to_async(notification.mark_as_failed)(
                    error_message=str(e),
                )

            return None

        # Пытаемся отправить уведомление через каждый тип (провайдера) по порядку приоритета (последовательно)
        for notification_type in priority:
            result = await try_send_with_provider(notification_type)
            if result:
                prov, recipient = result
                logger.info(f"[NotificationService] Success via {prov} -> {recipient}")
                return True

        logger.warning(
            "[NotificationService] Все типы уведомлений исчерпаны, отправка не удалась"
        )
        return False

    def _get_recipient_for_notification_type(
        self, notification_type: str
    ) -> str | None:
        """
        Возвращает получателя для указанного типа уведомления.

        Args:
            notification_type: Тип уведомления (email, sms, telegram)

        Returns:
            str: Адрес получателя или None, если не удалось определить
        """
        if not self.user:
            return None

        elif notification_type == "email":
            if hasattr(self.user, "get_notification_email"):
                return self.user.get_notification_email()
            return getattr(self.user, "email", None)

        elif notification_type == "sms":
            raw_phone = getattr(self.user, "phone_number", None)
            if not raw_phone:
                return None

            phone = raw_phone.lstrip("+")
            if not phone or not phone[0].isdigit():
                return None

            return phone

        elif notification_type == "telegram":
            user_chat_id = getattr(self.user, "telegram_chat_id", None)
            if user_chat_id:
                logger.debug(
                    f"[NotificationService] Resolved telegram recipient from user: {user_chat_id}"
                )
                return user_chat_id
            return None

        return None
