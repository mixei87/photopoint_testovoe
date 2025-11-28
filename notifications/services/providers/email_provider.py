"""
Провайдер для отправки уведомлений по электронной почте.
"""
import logging
import aiosmtplib
from email.message import EmailMessage
from django.conf import settings
from .base import NotificationProvider
from asyncio import TimeoutError
from typing import Any

logger = logging.getLogger(__name__)

class EmailProvider(NotificationProvider):
    """Провайдер для асинхронной отправки уведомлений по электронной почте."""
    
    def __init__(self):
        self.timeout = 30  # Таймаут в секундах
    
    @property
    def name(self) -> str:
        return "email"
    
    @property
    def is_configured(self) -> bool:
        """Проверяет, сконфигурирован ли email-провайдер."""
        required_settings = [
            'EMAIL_HOST',
            'EMAIL_HOST_USER',
            'EMAIL_HOST_PASSWORD',
            'EMAIL_PORT',
            'EMAIL_USE_TLS'
        ]
        return all(hasattr(settings, setting) for setting in required_settings)
    
    async def send(self, recipient: str, message: str, **kwargs: dict[str, Any]) -> bool:
        """
        Асинхронно отправляет уведомление по электронной почте.
        
        Args:
            recipient: Email-адрес получателя
            message: Текст сообщения
            **kwargs: 
                - subject (str): Тема письма (по умолчанию 'Уведомление')
                - from_email (str): Email отправителя (по умолчанию DEFAULT_FROM_EMAIL или EMAIL_HOST_USER)
                - timeout (int): Таймаут в секундах (по умолчанию 30)
                - html_message (str): HTML-версия письма (опционально)
                
        Returns:
            bool: True, если письмо успешно отправлено, иначе False
        """
        if not self.is_configured:
            logger.error("Email провайдер не сконфигурирован")
            return False
            
        subject = kwargs.get('subject', 'Уведомление')
        from_email = kwargs.get('from_email', getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER))
        timeout = kwargs.get('timeout', self.timeout)
        html_message = kwargs.get('html_message')
        
        # Создаем email сообщение
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = recipient
        
        if html_message:
            msg.set_content(message)
            msg.add_alternative(html_message, subtype='html')
        else:
            msg.set_content(message)
        
        try:
            # Настройки SMTP
            smtp_params = {
                'hostname': settings.EMAIL_HOST,
                'port': settings.EMAIL_PORT,
                'username': settings.EMAIL_HOST_USER,
                'password': settings.EMAIL_HOST_PASSWORD,
                'use_tls': settings.EMAIL_USE_TLS,
                'timeout': timeout
            }
            
            # Отправка письма
            async with aiosmtplib.SMTP(**smtp_params) as smtp:
                await smtp.send_message(msg)
            
            logger.info(f"Письмо успешно отправлено на {recipient}")
            return True
            
        except TimeoutError:
            logger.error(f"Таймаут при отправке письма на {recipient}")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при отправке письма на {recipient}: {str(e)}", exc_info=True)
            return False
