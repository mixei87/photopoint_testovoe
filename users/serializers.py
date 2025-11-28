"""
Сериализаторы для приложения пользователей.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions as django_exceptions
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели пользователя."""
    
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'phone_number',
            'telegram_chat_id',
            'is_staff',
            'is_active',
            'date_joined',
            'last_login',
        ]
        read_only_fields = [
            'id',
            'is_staff',
            'is_active',
            'date_joined',
            'last_login',
        ]
        extra_kwargs = {
            'email': {'required': True},
        }
    
    def validate_email(self, value):
        """Проверяет, что email уникален."""
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")
        return value


class UserCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания пользователя."""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password],
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )
    
    class Meta:
        model = User
        fields = [
            'email',
            'username',
            'password',
            'password_confirm',
            'first_name',
            'last_name',
            'phone_number',
            'telegram_chat_id',
        ]
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate(self, attrs):
        """Проверяет, что пароли совпадают."""
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({"password": _("Пароли не совпадают.")})
        return attrs
    
    def create(self, validated_data):
        """Создает нового пользователя."""
        try:
            user = User.objects.create_user(
                email=validated_data['email'],
                username=validated_data['username'],
                password=validated_data['password'],
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', ''),
                phone_number=validated_data.get('phone_number'),
                telegram_chat_id=validated_data.get('telegram_chat_id'),
            )
            return user
        except django_exceptions.ValidationError as e:
            raise serializers.ValidationError({"error": e.messages}) from e


class UserUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления данных пользователя."""
    
    class Meta:
        model = User
        fields = [
            'email',
            'username',
            'first_name',
            'last_name',
            'phone_number',
            'telegram_chat_id',
        ]
        extra_kwargs = {
            'email': {'required': False},
            'username': {'required': False},
        }
    
    def validate_email(self, value):
        """Проверяет, что email уникален."""
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля."""
    
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
    )
    new_password_confirm = serializers.CharField(required=True)
    
    def validate_old_password(self, value):
        """Проверяет старый пароль."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный старый пароль.")
        return value
    
    def validate(self, attrs):
        """Проверяет, что новые пароли совпадают."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "Пароли не совпадают."})
        return attrs
    
    def save(self, **kwargs):
        """Сохраняет новый пароль."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
