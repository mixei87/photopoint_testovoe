"""
Админка для приложения уведомлений.
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Notification, NotificationStatus, NotificationType


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Админка для модели уведомлений."""
    list_display = (
        'id',
        'user',
        'notification_type',
        'status',
        'created_at',
        'sent_at',
    )
    
    list_filter = (
        'status',
        'notification_type',
        'created_at',
    )
    
    search_fields = (
        'user__username',
        'user__email',
        'message',
    )
    
    readonly_fields = (
        'created_at',
        'sent_at',
    )
    
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (_('Основная информация'), {
            'fields': (
                'user',
                'message',
                'notification_type',
                'status',
            )
        }),
        (_('Данные провайдера'), {
            'fields': (
                'provider_data',
            ),
        }),
        (_('Временные метки'), {
            'classes': ('collapse',),
            'fields': (
                'created_at',
                'sent_at',
            ),
        }),
    )
    
    def has_add_permission(self, request):
        # Запрещаем создание уведомлений через админку
        return False
