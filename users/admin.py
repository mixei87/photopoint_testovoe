"""
Админка для приложения пользователей.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User
from .forms import CustomUserCreationForm


class UserAdmin(BaseUserAdmin):
    """Админка для модели пользователя."""
    add_form = CustomUserCreationForm
    
    list_display = (
        'username',
        'email',
        'first_name',
        'phone_number',
        'notification_email',
        'is_active',
        'date_joined',
    )
    
    list_filter = (
        'is_active',
        'date_joined',
    )
    
    search_fields = (
        'username',
        'email',
        'notification_email',
        'first_name',
        'phone_number',
        'telegram_chat_id',
    )
    
    ordering = ('username',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Личная информация'), {
            'fields': (
                'first_name',
                'email',
                'notification_email',
                'phone_number',
                'telegram_chat_id',
            )
        }),
        (_('Permissions'), {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            ),
        }),
        (_('Important dates'), {
            'fields': (
                'last_login',
                'date_joined',
            ),
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'email',
                'first_name',
                'notification_email',
                'phone_number',
                'telegram_chat_id',
                'password1',
                'password2',
            ),
        }),
    )


# Регистрируем модель пользователя с кастомной админкой
admin.site.register(User, UserAdmin)
