"""Провайдер для отправки уведомлений в Telegram."""

import asyncio
import logging

from django.conf import settings
from telegram import Bot
from telegram.error import NetworkError, TelegramError
from telegram.request import HTTPXRequest

from .base import NotificationProvider

logger = logging.getLogger(__name__)


class TelegramProvider(NotificationProvider):
    """Провайдер для отправки уведомлений в Telegram."""

    def __init__(self) -> None:
        # Таймаут HTTP-запроса в секундах (используется как дефолт)
        self.timeout: int = 15

    @property
    def name(self) -> str:
        return "telegram"

    @property
    def is_configured(self) -> bool:
        """Проверяет, сконфигурирован ли Telegram-провайдер."""
        return hasattr(settings, "TELEGRAM_BOT_TOKEN") and settings.TELEGRAM_BOT_TOKEN

    async def send(self, recipient: str, message: str, **kwargs) -> bool:
        """
        Отправляет уведомление в Telegram.

        Args:
            recipient: ID чата или имя пользователя получателя (начинается с @ для username)
            message: Текст сообщения
            **kwargs:
                - parse_mode (str): Режим форматирования ('Markdown' или 'HTML')
                - disable_web_page_preview (bool): Отключить предпросмотр веб-страниц

        Returns:
            bool: True, если сообщение успешно отправлено, иначе False
        """
        if not self.is_configured:
            logger.error(
                "[TelegramProvider] Провайдер не сконфигурирован (нет TELEGRAM_BOT_TOKEN)"
            )
            return False

        parse_mode = kwargs.get("parse_mode")
        disable_web_page_preview = kwargs.get("disable_web_page_preview", True)

        # Создаём отдельный HTTP-клиент и Bot на каждую отправку,
        # и корректно закрываем клиент после использования.
        request = HTTPXRequest()
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, request=request)

        try:
            await bot.send_message(
                chat_id=recipient,
                text=message,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
            logger.info(
                f"[TelegramProvider] Сообщение успешно отправлено в чат {recipient}"
            )
            return True

        except TelegramError as exc:
            logger.error(
                "[TelegramProvider] Ошибка Telegram при отправке в чат %s: %s",
                recipient,
                exc,
                exc_info=True,
            )
            return False
        except (asyncio.TimeoutError, NetworkError, OSError) as exc:
            logger.error(
                "[TelegramProvider] Ошибка сети при отправке в Telegram в чат %s: %s",
                recipient,
                exc,
                exc_info=True,
            )
            return False
        finally:
            # Аккуратно закрываем HTTP-клиент, поддерживая как sync-, так и async-API.
            try:
                close_method = getattr(request, "close", None)
                if close_method is not None:
                    res = close_method()
                    if asyncio.iscoroutine(res):
                        await res
            except (RuntimeError, OSError):
                pass
