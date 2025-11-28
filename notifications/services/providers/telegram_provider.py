"""
Провайдер для отправки уведомлений в Telegram.
"""
import logging
from telegram import Bot
from telegram.error import TelegramError
from django.conf import settings
from .base import NotificationProvider

logger = logging.getLogger(__name__)

class TelegramProvider(NotificationProvider):
    """Провайдер для отправки уведомлений в Telegram."""
    
    def __init__(self):
        self._bot = None
        
    @property
    def bot(self):
        """Ленивая инициализация бота Telegram."""
        if self._bot is None and hasattr(settings, 'TELEGRAM_BOT_TOKEN'):
            self._bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        return self._bot
    
    @property
    def name(self) -> str:
        return "telegram"
    
    @property
    def is_configured(self) -> bool:
        """Проверяет, сконфигурирован ли Telegram-провайдер."""
        return hasattr(settings, 'TELEGRAM_BOT_TOKEN') and settings.TELEGRAM_BOT_TOKEN
    
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
            logger.error("Telegram провайдер не сконфигурирован")
            return False
            
        parse_mode = kwargs.get('parse_mode')
        disable_web_page_preview = kwargs.get('disable_web_page_preview', True)
        
        try:
            await self.bot.send_message(
                chat_id=recipient,
                text=message,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview
            )
            logger.info(f"Сообщение успешно отправлено в Telegram чат {recipient}")
            return True
            
        except TelegramError as e:
            logger.error(f"Ошибка при отправке сообщения в Telegram чат {recipient}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке в Telegram: {str(e)}")
            return False
