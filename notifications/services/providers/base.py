"""
Базовый класс для всех провайдеров уведомлений.
"""
from abc import ABC, abstractmethod


class NotificationProvider(ABC):
    """Абстрактный базовый класс для всех провайдеров уведомлений."""

    @abstractmethod
    async def send(self, recipient: str, message: str, **kwargs) -> bool:
        """
        Отправляет уведомление.

        Args:
            recipient: Получатель уведомления (email, номер телефона, id чата и т.д.)
            message: Текст уведомления
            **kwargs: Дополнительные параметры

        Returns:
            bool: True, если уведомление успешно отправлено, иначе False
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Возвращает имя провайдера."""
        pass

    @property
    def is_configured(self) -> bool:
        """Проверяет, сконфигурирован ли провайдер."""
        return True
