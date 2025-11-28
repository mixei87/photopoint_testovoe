"""
Сериализаторы для приложения уведомлений.
"""
from rest_framework import serializers
from .models import Notification, NotificationStatus


class NotificationSerializer(serializers.ModelSerializer):
    """Сериализатор для модели уведомлений."""
    
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'user',
            'message',
            'status',
            'status_display',
            'provider_used',
            'provider_priority',
            'recipient',
            'created_at',
            'updated_at',
            'sent_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'status',
            'status_display',
            'provider_used',
            'recipient',
            'created_at',
            'updated_at',
            'sent_at',
        ]


class SendNotificationSerializer(serializers.Serializer):
    """Сериализатор для отправки уведомлений."""
    
    message = serializers.CharField(
        required=True,
        help_text='Текст уведомления'
    )
    
    priority = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            ('email', 'Email'),
            ('sms', 'SMS'),
            ('telegram', 'Telegram'),
        ]),
        required=False,
        help_text='Приоритет провайдеров в порядке убывания приоритета',
        default=['telegram', 'email', 'sms']
    )
    
    provider_kwargs = serializers.DictField(
        required=False,
        default=dict,
        help_text='Дополнительные параметры для провайдеров',
        child=serializers.DictField()
    )
    
    def validate_priority(self, value):
        """Проверяет, что все провайдеры в списке приоритетов валидны."""
        valid_providers = {'email', 'sms', 'telegram'}
        
        if not value:
            return ['telegram', 'email', 'sms']
            
        if not all(provider in valid_providers for provider in value):
            raise serializers.ValidationError(
                f"Недопустимый провайдер. Допустимые значения: {', '.join(valid_providers)}"
            )
            
        return value
    
    def validate(self, data):
        """Дополнительная валидация данных."""
        # Можно добавить дополнительную валидацию здесь
        return data
