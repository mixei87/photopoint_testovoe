"""Провайдер для отправки SMS-уведомлений через Exolve."""

import logging
import asyncio
from typing import Any

import requests
from django.conf import settings

from .base import NotificationProvider

logger = logging.getLogger(__name__)


class SMSProvider(NotificationProvider):
    """Провайдер для асинхронной отправки SMS-уведомлений через Exolve."""

    def __init__(self) -> None:
        self.timeout: int = 15
        self.api_url: str = "https://api.exolve.ru/messaging/v1/SendSMS"
        self.auth_token: str | None = getattr(settings, "SMS_AUTH_TOKEN", None)
        self.from_number: str | None = getattr(settings, "SMS_PHONE_NUMBER", None)

    @property
    def name(self) -> str:
        return "sms"

    @property
    def is_configured(self) -> bool:
        """Проверяет, сконфигурирован ли SMS-провайдер Exolve."""
        return bool(self.auth_token and self.from_number)

    async def send(self, recipient: str, message: str, **kwargs: Any) -> bool:
        """Асинхронно отправляет SMS через Exolve.

        Args:
            recipient: Номер телефона получателя (начинается с цифры, без +)
            message: Текст сообщения
            **kwargs:
                - timeout (int): Таймаут HTTP-запроса (по умолчанию 15)

        Returns:
            bool: True, если SMS успешно отправлено, иначе False
        """
        if not self.is_configured:
            logger.error("SMS провайдер Exolve не сконфигурирован")
            return False

        timeout = kwargs.get("timeout", self.timeout)
        payload = {
            "number": self.from_number,
            "destination": recipient,
            "text": message,
        }
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }

        def _send_sync() -> requests.Response:
            return requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=timeout,
            )

        try:
            response: requests.Response = await asyncio.to_thread(_send_sync)
            if response.status_code != 200:
                logger.error(
                    "Exolve вернул код %s при отправке на %s",
                    response.status_code,
                    recipient,
                )
                return False
            logger.info("SMS успешно отправлено на %s через Exolve", recipient)
            return True
        except Exception as e:
            logger.error(
                "Исключение при отправке SMS на %s через Exolve: %s",
                recipient,
                str(e),
                exc_info=True,
            )
            return False
