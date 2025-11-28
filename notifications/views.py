"""
Представления для приложения уведомлений.
"""
import logging
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Notification

class HealthCheckView(APIView):
    """
    Простая вьюха для проверки работоспособности сервиса
    """
    def get(self, request, *args, **kwargs):
        return Response({
            'status': 'ok',
            'service': 'Notification Service',
            'version': '1.0.0'
        })

class SimpleView(View):
    """
    Простая HTML-страница для проверки работы сервера
    """
    def get(self, request, *args, **kwargs):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Notification Service</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    padding: 20px;
                    border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #333;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 10px;
                }
                .status {
                    color: #4CAF50;
                    font-weight: bold;
                }
                .info {
                    margin-top: 20px;
                    padding: 15px;
                    background-color: #e7f3fe;
                    border-left: 6px solid #2196F3;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Сервис уведомлений</h1>
                <div class="status">Статус: <span style="color: green;">Работает</span></div>
                
                <div class="info">
                    <h3>Доступные эндпоинты:</h3>
                    <ul>
                        <li><strong>Админ-панель:</strong> <a href="/admin/">/admin/</a></li>
                    </ul>
                </div>
                
                <div style="margin-top: 20px; font-size: 0.9em; color: #666;">
                    <p>Версия: 1.0.0</p>
                </div>
            </div>
        </body>
        </html>
        """
        return HttpResponse(html)

class NotificationSendView(View):
    """Главная страница с формой отправки уведомлений нескольким пользователям."""
    template_name = 'notifications/send.html'

    def get(self, request, *args, **kwargs):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.all().order_by('username')
        return render(request, self.template_name, {
            'users': users,
        })

    def post(self, request, *args, **kwargs):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_ids = request.POST.getlist('users')
        message_text = request.POST.get('message', '').strip()
        if not user_ids or not message_text:
            messages.error(request, 'Выберите хотя бы одного пользователя и введите сообщение.')
            return redirect('home')

        # Создаем уведомления для выбранных пользователей
        users = User.objects.filter(id__in=user_ids)
        created = 0
        for u in users:
            try:
                Notification.create_for_user(
                    user=u,
                    message=message_text,
                    notification_type=getattr(u, 'notification_priority', 'telegram') or 'telegram'
                )
                created += 1
            except Exception:
                # Пропускаем ошибки по отдельным пользователям, продолжая обработку
                continue

        if created:
            messages.success(request, f'Создано уведомлений: {created}.')
        else:
            messages.warning(request, 'Не удалось создать уведомления.')
        return redirect('home')

logger = logging.getLogger(__name__)
from rest_framework.permissions import IsAuthenticated
from .serializers import NotificationSerializer, SendNotificationSerializer
from .services import NotificationService

class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с уведомлениями.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Возвращает только уведомления текущего пользователя."""
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def send(self, request, *args, **kwargs):
        """
        Отправляет уведомление пользователю через выбранные провайдеры.
        
        Пример запроса:
        {
            "message": "Важное уведомление!",
            "priority": ["telegram", "email", "sms"],
            "provider_kwargs": {
                "email": {
                    "subject": "Важное уведомление",
                    "from_email": "noreply@example.com",
                    "html_message": "<p>Важное уведомление!</p>"
                },
                "telegram": {
                    "parse_mode": "Markdown"
                },
                "sms": {
                    "from_phone": "+1234567890"
                }
            },
            "timeout": 60,  # Общий таймаут в секундах (опционально)
            "provider_timeout": 30  # Таймаут для каждого провайдера (опционально)
        }
        """
        serializer = SendNotificationSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = NotificationService(user=request.user)
        
        # Вызываем асинхронную функцию синхронно с помощью asyncio
        import asyncio
        import traceback
        
        async def send_async():
            return await service.send_notification(
                message=serializer.validated_data['message'],
                priority=serializer.validated_data['priority'],
                **serializer.validated_data.get('provider_kwargs', {})
            )
        
        # Запускаем асинхронную функцию в цикле событий
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            success = loop.run_until_complete(send_async())
            
            if success:
                return Response(
                    {"status": "Уведомление успешно отправлено"},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        "error": "Не удалось отправить уведомление ни одним из способов",
                        "details": "Проверьте настройки провайдеров и получателей"
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except asyncio.TimeoutError:
            logger.error("Превышено время ожидания при отправке уведомления")
            return Response(
                {"error": "Превышено время ожидания при отправке уведомления"},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке уведомления: {str(e)}\n{traceback.format_exc()}")
            return Response(
                {
                    "error": "Внутренняя ошибка сервера",
                    "details": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        finally:
            try:
                # Завершаем все асинхронные задачи
                pending = asyncio.all_tasks(loop=loop)
                for task in pending:
                    task.cancel()
                    try:
                        loop.run_until_complete(task)
                    except (asyncio.CancelledError, Exception):
                        pass
                
                # Закрываем цикл событий
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
                
            except Exception as e:
                logger.error(f"Ошибка при завершении цикла событий: {str(e)}")
            
            # Убедимся, что цикл событий закрыт
            if loop.is_running():
                loop.stop()
                loop.close()
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Помечает уведомление как прочитанное."""
        notification = self.get_object()
        notification.status = 'read'
        notification.save()
        
        return Response(
            {"status": "Уведомление помечено как прочитанное"},
            status=status.HTTP_200_OK
        )
