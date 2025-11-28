"""
Модели для приложения уведомлений.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

User = get_user_model()


# Перечисления вынесены в отдельные классы
class NotificationStatus(models.TextChoices):
    """Статусы уведомлений."""

    PENDING = "pending", _("Ожидает отправки")
    SENT = "sent", _("Отправлено")
    DELIVERED = "delivered", _("Доставлено")
    FAILED = "failed", _("Ошибка")
    READ = "read", _("Прочитано")


class NotificationType(models.TextChoices):
    """Типы уведомлений."""

    EMAIL = "email", _("Email")
    SMS = "sms", _("SMS")
    TELEGRAM = "telegram", _("Telegram")


class Notification(models.Model):
    """Модель для хранения уведомлений."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Пользователь"),
        db_index=True,
    )

    message = models.TextField(verbose_name=_("Текст уведомления"))

    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        verbose_name=_("Статус"),
        db_index=True,
    )

    notification_type = models.CharField(
        max_length=10,
        choices=NotificationType.choices,
        verbose_name=_("Тип уведомления"),
        db_index=True,
    )

    # Для хранения дополнительной информации о провайдере
    provider_data = models.JSONField(
        default=dict, blank=True, verbose_name=_("Данные провайдера")
    )

    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Дата создания"), db_index=True
    )

    sent_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Дата отправки")
    )

    class Meta:
        verbose_name = _("уведомление")
        verbose_name_plural = _("уведомления")
        ordering = ["-created_at"]
        db_table = "notifications"  # Имя таблицы в БД

    def __str__(self):
        return f"Уведомление #{self.id} для {self.user}"

    def mark_as_sent(self, provider_data=None):
        """Отмечает уведомление как отправленное."""
        self.status = NotificationStatus.SENT
        self.sent_at = timezone.now()
        if provider_data:
            self.provider_data.update(provider_data)
        self.save(update_fields=["status", "sent_at", "provider_data", "updated_at"])

    def mark_as_delivered(self):
        """Отмечает уведомление как доставленное."""
        self.status = NotificationStatus.DELIVERED
        self.save(update_fields=["status", "updated_at"])

    def mark_as_failed(self, error_message=None):
        """Отмечает уведомление как не отправленное."""
        self.status = NotificationStatus.FAILED
        if error_message:
            self.provider_data["error"] = error_message
        self.save(update_fields=["status", "provider_data", "updated_at"])

    def mark_as_read(self):
        """Отмечает уведомление как прочитанное."""
        self.status = NotificationStatus.READ
        self.save(update_fields=["status", "updated_at"])

    @classmethod
    def create_for_user(cls, user, message, notification_type, **kwargs):
        """Создает уведомление для пользователя."""
        return cls.objects.create(
            user=user, message=message, notification_type=notification_type, **kwargs
        )
