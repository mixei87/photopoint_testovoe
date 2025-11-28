"""
Сервис для отправки уведомлений через различные провайдеры.
"""
import logging
import asyncio
from typing import Any, TypeVar, Type
from ..models import Notification, NotificationStatus
from .providers import EmailProvider, SMSProvider, TelegramProvider, NotificationProvider
from asyncio import TimeoutError

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=NotificationProvider)

class NotificationService:
    """Сервис для управления отправкой уведомлений."""
    
    # Доступные провайдеры уведомлений
    PROVIDERS: dict[str, NotificationProvider] = {
        'email': EmailProvider(),
        'sms': SMSProvider(),
        'telegram': TelegramProvider(),
    }
    
    # Таймауты по умолчанию (в секундах)
    DEFAULT_TIMEOUT = 30
    DEFAULT_OVERALL_TIMEOUT = 60  # Общий таймаут на все попытки отправки
    
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
        **provider_kwargs: Any
    ) -> bool:
        """
        Асинхронно отправляет уведомление пользователю через указанные провайдеры по приоритету.
        
        Args:
            message: Текст уведомления
            priority: Список провайдеров в порядке приоритета, например ['telegram', 'email', 'sms']
            **provider_kwargs: Дополнительные аргументы для провайдеров
                - timeout (int): Общий таймаут на все попытки отправки (в секундах)
                - provider_timeout (int): Таймаут для каждого провайдера (в секундах)
                
        Returns:
            bool: True, если уведомление было успешно отправлено хотя бы одним провайдером
        """
        if priority is None:
            priority = ['telegram', 'email', 'sms']
            
        if not self.user:
            logger.error("Не указан пользователь для отправки уведомления")
            return False
            
        # Получаем таймауты
        overall_timeout = provider_kwargs.pop('timeout', self.DEFAULT_OVERALL_TIMEOUT)
        provider_timeout = provider_kwargs.pop('provider_timeout', self.DEFAULT_TIMEOUT)
        
        # Создаем запись об уведомлении
        notification = Notification.objects.create(
            user=self.user,
            message=message,
            status=NotificationStatus.PENDING.value,
            provider_priority=','.join(priority)
        )
        
        async def try_send_with_provider(provider_name: str) -> tuple[str, str] | None:
            """Пытается отправить уведомление через указанный провайдер."""
            if provider_name not in self.PROVIDERS:
                logger.warning(f"Провайдер {provider_name} не найден")
                return None
                
            provider = self.PROVIDERS[provider_name]
            
            # Получаем получателя для данного типа провайдера
            recipient = self._get_recipient_for_provider(provider_name)
            if not recipient:
                logger.warning(f"Не удалось определить получателя для провайдера {provider_name}")
                return None
                
            # Пытаемся отправить уведомление с таймаутом
            try:
                # Устанавливаем таймаут для провайдера, если он не указан явно
                provider_kwargs.setdefault(provider_name, {})['timeout'] = provider_timeout
                
                success = await asyncio.wait_for(
                    provider.send(
                        recipient=recipient,
                        message=message,
                        **provider_kwargs.get(provider_name, {})
                    ),
                    timeout=provider_timeout
                )
                
                if success:
                    return provider_name, recipient
                    
            except TimeoutError:
                logger.warning(f"Таймаут при отправке через {provider_name}")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления через {provider_name}: {str(e)}", exc_info=True)
                
            return None
        
        # Пытаемся отправить уведомление через каждый провайдер по порядку приоритета
        try:
            # Создаем задачи для каждого провайдера
            tasks = [try_send_with_provider(provider_name) for provider_name in priority]
            
            # Ожидаем первую успешную отправку или завершение всех попыток
            done, pending = await asyncio.wait(
                [asyncio.create_task(task) for task in tasks],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=overall_timeout
            )
            
            # Отменяем оставшиеся задачи
            for task in pending:
                task.cancel()
            
            # Проверяем результаты выполненных задач
            for task in done:
                try:
                    result = await task
                    if result:
                        provider_name, recipient = result
                        notification.status = NotificationStatus.SENT.value
                        notification.provider_used = provider_name
                        notification.recipient = recipient
                        notification.save()
                        return True
                except Exception as e:
                    logger.error(f"Ошибка при обработке результата отправки: {str(e)}", exc_info=True)
            
            # Если ни один провайдер не смог отправить уведомление
            notification.status = NotificationStatus.FAILED.value
            notification.save()
            return False
            
        except asyncio.TimeoutError:
            logger.error(f"Превышен общий таймаут ({overall_timeout} сек.) при отправке уведомления")
            notification.status = NotificationStatus.FAILED.value
            notification.save()
            return False
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке уведомления: {str(e)}", exc_info=True)
            notification.status = NotificationStatus.FAILED.value
            notification.save()
            return False
    
    def _get_recipient_for_provider(self, provider_name: str) -> str | None:
        """
        Возвращает получателя для указанного провайдера.
        
        Args:
            provider_name: Имя провайдера
            
        Returns:
            str: Адрес получателя или None, если не удалось определить
        """
        if not self.user:
            return None
            
        if provider_name == 'email':
            return self.user.email
            
        elif provider_name == 'sms':
            return getattr(self.user, 'phone_number', None)
            
        elif provider_name == 'telegram':
            return getattr(self.user, 'telegram_chat_id', None)
            
        return None
