"""
Представления для приложения пользователей.
"""
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login, logout
from django.utils.translation import gettext_lazy as _

from .models import User
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с пользователями.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """
        Разрешает регистрацию без аутентификации.
        """
        if self.action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()
    
    def get_serializer_class(self):
        """
        Выбирает сериализатор в зависимости от действия.
        """
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return self.serializer_class
    
    def get_object(self):
        """
        Возвращает текущего пользователя.
        """
        if self.action in ['me', 'change_password']:
            return self.request.user
        return super().get_object()
    
    def create(self, request, *args, **kwargs):
        """
        Создает нового пользователя и возвращает токены.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Автоматически входим пользователя
        login(request, user)
        
        # Генерируем токены
        refresh = RefreshToken.for_user(user)
        
        return Response(
            {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request, *args, **kwargs):
        """
        Возвращает или обновляет данные текущего пользователя.
        """
        if request.method == 'GET':
            return self.retrieve(request, *args, **kwargs)
        elif request.method in ['PUT', 'PATCH']:
            return self.update(request, *args, **kwargs)
    
    @action(detail=False, methods=['post'])
    def logout(self, request, *args, **kwargs):
        """
        Выход пользователя из системы.
        """
        logout(request)
        return Response(
            {"detail": _("Вы успешно вышли из системы.")},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'])
    def change_password(self, request, *args, **kwargs):
        """
        Изменяет пароль пользователя.
        """
        user = self.get_object()
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Сохраняем новый пароль
        serializer.save()
        
        return Response(
            {"detail": _("Пароль успешно изменен.")},
            status=status.HTTP_200_OK
        )
