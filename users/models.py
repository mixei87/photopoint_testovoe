"""
Модели для приложения пользователей.
"""

import re
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser


def validate_phone(value):
    """Валидация номера телефона."""
    if not value:
        return
    pattern = r"^\+?[1-9]\d{9,14}$"
    if not re.match(pattern, value):
        raise ValidationError("Некорректный формат номера телефона")


class User(AbstractUser):
    """Кастомная модель пользователя."""

    # Удаляем ненужные поля
    last_name = None
    
    # Административные поля
    is_staff = models.BooleanField(
        'Статус персонала',
        default=False,
        help_text='Определяет доступ к админке'
    )
    is_superuser = models.BooleanField(
        'Статус суперпользователя',
        default=False,
        help_text='Полные права на управление сайтом'
    )

    # Обязательные поля
    first_name = models.CharField("Имя", max_length=150, blank=True)

    # Email для входа (необязательный)
    email = models.EmailField(
        "Email",
        blank=True,
        null=True,
        validators=[],
        help_text="Необязательное поле. Должен быть действительный email.",
    )

    # Email для уведомлений
    notification_email = models.EmailField(
        "Email для уведомлений",
        blank=True,
        null=True,
        help_text="Email для отправки уведомлений",
    )

    # Телефон (необязательный)
    phone_number = models.CharField(
        "Номер телефона",
        max_length=20,
        blank=True,
        null=True,
        validators=[validate_phone],
        help_text="Формат: +1234567890",
    )

    # Telegram
    telegram_chat_id = models.CharField(
        "ID чата Telegram",
        max_length=100,
        blank=True,
        null=True,
        help_text="ID чата в Telegram для уведомлений",
    )

    # Приоритеты уведомлений
    NOTIFICATION_PRIORITY = [
        ("telegram", "Telegram"),
        ("email", "Email"),
        ("sms", "SMS"),
    ]

    notification_priority = models.CharField(
        "Приоритет уведомлений",
        max_length=10,
        choices=NOTIFICATION_PRIORITY,
        default="telegram",
    )

    USERNAME_FIELD = "username"  # Используем username для входа
    REQUIRED_FIELDS = []  # Убираем обязательный email

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"
        db_table = "users"

    def __str__(self):
        return self.username

    @property
    def full_name(self):
        """Возвращает имя пользователя."""
        return self.first_name or self.username

    def clean(self):
        """Валидация модели."""
        super().clean()
        if self.phone_number:
            self.phone_number = self.phone_number.strip()
            validate_phone(self.phone_number)

    def get_notification_email(self):
        """Возвращает email для уведомлений."""
        return self.notification_email or self.email

    def get_available_notification_methods(self):
        """Возвращает доступные способы уведомлений."""
        methods = []
        if self.telegram_chat_id:
            methods.append("telegram")
        if self.get_notification_email():
            methods.append("email")
        if self.phone_number:
            methods.append("sms")
        return methods
