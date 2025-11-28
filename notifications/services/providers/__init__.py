"""
Провайдеры уведомлений.
"""

from .base import NotificationProvider
from .email_provider import EmailProvider
from .sms_provider import SMSProvider
from .telegram_provider import TelegramProvider

# Экспортируем все провайдеры для удобного импорта
__all__ = [
    'NotificationProvider',
    'EmailProvider',
    'SMSProvider',
    'TelegramProvider',
]
