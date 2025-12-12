"""Провайдер для отправки уведомлений по электронной почте через Brevo."""

import logging
import asyncio
from typing import Any

import requests
from django.conf import settings

from .base import NotificationProvider

logger = logging.getLogger(__name__)


class EmailProvider(NotificationProvider):
    """Провайдер для асинхронной отправки уведомлений по электронной почте."""

    def __init__(self) -> None:
        # Таймаут HTTP-запроса в секундах
        self.timeout: int = 15

    @property
    def name(self) -> str:
        return "email"

    @property
    def is_configured(self) -> bool:
        """Проверяет, сконфигурирован ли email-провайдер Brevo."""
        return bool(
            getattr(settings, "EMAIL_API_KEY", None)
            and getattr(settings, "EMAIL_SENDER_EMAIL", None)
        )

    async def send(
        self, recipient: str, message: str, **kwargs: dict[str, Any]
    ) -> bool:
        """Асинхронно отправляет уведомление по электронной почте через Brevo.

        Args:
            recipient: Email-адрес получателя (можно с именем: "Name <user@example.com>")
            message: Текст сообщения (HTML/текст)
            **kwargs:
                - subject (str): Тема письма (по умолчанию 'Уведомление')
                - sender_name (str): Имя отправителя (по умолчанию EMAIL_SENDER_NAME или 'Notification Service')
                - timeout (int): Таймаут HTTP-запроса (по умолчанию 30)

        Returns:
            bool: True, если письмо успешно отправлено, иначе False
        """
        if not self.is_configured:
            logger.error("Email провайдер Brevo не сконфигурирован")
            return False

        api_key = settings.EMAIL_API_KEY
        sender_email = settings.EMAIL_SENDER_EMAIL
        sender_name = (
            getattr(settings, "EMAIL_SENDER_NAME", None) or "Notification Service"
        )

        subject = kwargs.get("subject", "Уведомление")
        timeout = kwargs.get("timeout", self.timeout)
        recipient_name = kwargs.get("recipient_name", "") or recipient

        # Формируем JSON для Brevo в требуемом формате
        # {
        #     "sender": {"name": EMAIL_SENDER_NAME, "email": EMAIL_SENDER_EMAIL},
        #     "to": [{"email": <email из БД>, "name": <name из БД>}],
        #     "htmlContent": <простой текст>,
        #     "subject": <тема>
        # }

        url = "https://api.brevo.com/v3/smtp/email"
        payload = {
            "sender": {
                "name": sender_name,
                "email": sender_email,
            },
            "to": [
                {
                    "email": recipient,
                    "name": recipient_name,
                }
            ],
            "htmlContent": message,
            "subject": subject,
        }

        headers = {
            "api-key": api_key,
            "Content-Type": "application/json",
        }

        def _send_sync() -> requests.Response:
            return requests.post(url, json=payload, headers=headers, timeout=timeout)

        try:
            response: requests.Response = await asyncio.to_thread(_send_sync)
            if response.status_code not in (200, 201, 202):
                logger.error(
                    "Brevo вернул код %s при отправке на %s",
                    response.status_code,
                    recipient,
                )
                return False

            logger.info(
                "Письмо успешно отправлено на %s через Brevo",
                recipient,
            )
            return True
        except Exception as e:
            logger.error(
                "Исключение при отправке письма на %s через Brevo: %s",
                recipient,
                str(e),
                exc_info=True,
            )
            return False
