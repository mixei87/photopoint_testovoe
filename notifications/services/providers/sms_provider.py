"""
Провайдер для отправки SMS-уведомлений через Twilio.
"""
import logging
from twilio.http.async_http_client import AsyncTwilioHttpClient
from twilio.rest import Client as TwilioClient
from django.conf import settings
from .base import NotificationProvider
from asyncio import TimeoutError

logger = logging.getLogger(__name__)


class SMSProvider(NotificationProvider):
    """Провайдер для отправки SMS-уведомлений через Twilio."""

    def __init__(self):
        self._client = None
        self.timeout = 30  # Таймаут в секундах
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.phone_number = settings.TWILIO_PHONE_NUMBER

    @property
    def client(self):
        """Ленивая инициализация асинхронного клиента Twilio."""
        if self._client is None:
            http_client = AsyncTwilioHttpClient()
            self._client = TwilioClient(
                self.account_sid,
                self.auth_token,
                http_client=http_client
            )
        return self._client

    @property
    def name(self) -> str:
        return "sms"

    @property
    def is_configured(self) -> bool:
        """Проверяет, сконфигурирован ли SMS-провайдер."""
        required_settings = [
            'TWILIO_ACCOUNT_SID',
            'TWILIO_AUTH_TOKEN',
            'TWILIO_PHONE_NUMBER'
        ]
        return all(hasattr(settings, setting) for setting in required_settings)

    async def send(self, recipient: str, message: str, **kwargs) -> bool:
        """
        Асинхронно отправляет SMS-уведомление.
        
        Args:
            recipient: Номер телефона получателя в международном формате (начинается с +)
            message: Текст сообщения
            **kwargs: 
                - from_phone (str): Номер отправителя (по умолчанию TWILIO_PHONE_NUMBER)
                - timeout (int): Таймаут в секундах (по умолчанию 30)
                
        Returns:
            bool: True, если SMS успешно отправлено, иначе False
        """
        if not self.is_configured:
            logger.error("SMS провайдер не сконфигурирован")
            return False

        from_phone = kwargs.get('from_phone', settings.TWILIO_PHONE_NUMBER)
        timeout = kwargs.get('timeout', self.timeout)

        try:
            client = self.client
            message = await client.messages.create_async(
                body=message,
                from_=from_phone,
                to=recipient,
                timeout=timeout
            )

            if message.sid:
                logger.info(
                    f"SMS успешно отправлено на {recipient}, SID: {message.sid}")
                return True

            logger.warning(
                f"Не удалось отправить SMS на {recipient}: неизвестная ошибка")
            return False

        except TimeoutError:
            logger.error(f"Таймаут при отправке SMS на {recipient}")
            return False

        except Exception as e:
            logger.error(f"Ошибка при отправке SMS на {recipient}: {str(e)}",
                         exc_info=True)
            return False
