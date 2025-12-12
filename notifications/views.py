"""Представления для приложения уведомлений."""

import logging
import time
import threading

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, NotificationStatus, NotificationType
from .serializers import NotificationSerializer, SendNotificationSerializer
from .services import NotificationService


class HealthCheckView(APIView):
    """Простая вьюха для проверки работоспособности сервиса."""

    def get(self, request, *args, **kwargs):  # noqa
        return Response(
            {"status": "ok", "service": "Notification Service", "version": "1.0.0"}
        )


class SimpleView(TemplateView):
    """Простая HTML-страница для проверки работы сервера."""

    template_name = "notifications/simple.html"


class NotificationSendView(View):
    """Главная страница с формой отправки уведомлений нескольким пользователям."""

    template_name = "notifications/send.html"

    def get(self, request, *args, **kwargs):  # noqa
        from django.contrib.auth import get_user_model

        User = get_user_model()
        users_qs = User.objects.filter(is_staff=False).order_by("username")

        # Берём из сессии последних выбранных пользователей для отображения статусов
        last_ids = request.session.get("last_notification_user_ids")
        started_at_iso = request.session.get("last_notification_started_at")
        send_statuses: list[dict] | None = None

        if last_ids and started_at_iso:
            from django.utils.dateparse import parse_datetime

            started_at = parse_datetime(started_at_iso)
            if started_at is None:
                started_at = None

            selected_users = users_qs.filter(id__in=last_ids)

            # Формируем статусы отправки только для выбранных пользователей
            send_statuses = []
            notification_types = [
                NotificationType.TELEGRAM,
                NotificationType.EMAIL,
                NotificationType.SMS,
            ]

            any_pending = False

            for user in selected_users:
                user_item: dict = {
                    "user_label": getattr(user, "username", str(user)),
                    "statuses": [],
                }

                for nt in notification_types:
                    qs = Notification.objects.filter(user=user, notification_type=nt)
                    if started_at is not None:
                        qs = qs.filter(created_at__gte=started_at)
                    last_notif = qs.order_by("-created_at").first()

                    if not last_notif:
                        status_key = "not_sent"
                        status_label = "Не отправлялось"
                    else:
                        if last_notif.status == NotificationStatus.PENDING:
                            status_key = "pending"
                            status_label = "В процессе"
                            any_pending = True
                        elif last_notif.status in (
                            NotificationStatus.SENT,
                            NotificationStatus.DELIVERED,
                        ):
                            status_key = "success"
                            status_label = "Успешно отправлено"
                        elif last_notif.status == NotificationStatus.FAILED:
                            status_key = "error"
                            status_label = "Ошибка отправки"
                        else:
                            status_key = "unknown"
                            status_label = "Статус неизвестен"

                    # Явно задаём подписи типов, чтобы избежать переводов вроде
                    # "Адрес электронной почты" в статусах.
                    if nt == NotificationType.TELEGRAM:
                        type_label = "Telegram"
                    elif nt == NotificationType.EMAIL:
                        type_label = "Email"
                    elif nt == NotificationType.SMS:
                        type_label = "SMS"
                    else:
                        type_label = NotificationType(nt).label

                    user_item["statuses"].append(
                        {
                            "type": nt,
                            "type_label": type_label,
                            "status": status_key,
                            "status_label": status_label,
                        }
                    )

                send_statuses.append(user_item)

            # Если по последней рассылке больше нет ни одного pending-статуса,
            # очищаем данные о последнем запуске, чтобы при следующих обновлениях
            # страница не показывала старые уведомления.
            if not any_pending:
                request.session.pop("last_notification_user_ids", None)
                request.session.pop("last_notification_started_at", None)

        return render(
            request,
            self.template_name,
            {
                "users": users_qs,
                "send_statuses": send_statuses,
            },
        )

    def post(self, request, *args, **kwargs):  # noqa
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user_ids = request.POST.getlist("users")
        message_text = request.POST.get("message", "").strip()
        if not user_ids or not message_text:
            messages.error(
                request, "Выберите хотя бы одного пользователя и введите сообщение."
            )
            return redirect("home")

        users_qs = User.objects.filter(id__in=user_ids, is_staff=False).order_by(
            "username"
        )

        ids_and_chats = [(u.pk, getattr(u, "telegram_chat_id", None)) for u in users_qs]
        logger.info("[NotificationSendView] Selected users: %s", ids_and_chats)

        # Запускаем асинхронную рассылку в отдельном потоке, чтобы не блокировать HTTP-запрос
        def _run_batch_in_thread(user_ids_local: list[int], message: str) -> None:
            import asyncio
            import traceback

            from django.contrib.auth import get_user_model as _get_user_model

            UserModel = _get_user_model()
            users_local = list(
                UserModel.objects.filter(id__in=user_ids_local, is_staff=False)
            )

            async def send_for_user(u):
                service = NotificationService(user=u)
                try:
                    return await service.send_notification(message=message)
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "[NotificationSendView] Exception while sending for user id=%s: %s\n%s",
                        getattr(u, "pk", None),
                        exc,
                        traceback.format_exc(),
                    )
                    return False

            async def run_batch():
                tasks = [send_for_user(u) for u in users_local]
                return await asyncio.gather(*tasks, return_exceptions=True)

            t_start_local = time.monotonic()
            logger.info("[NotificationSendView] Background batch send start")
            try:

                async def _main_with_timeout():
                    return await asyncio.wait_for(run_batch(), timeout=90)

                results_local = asyncio.run(_main_with_timeout())
                success_count_local = sum(1 for r in results_local if r is True)
                logger.info(
                    "[NotificationSendView] Background batch finished: success_count=%s, duration=%.3fs",
                    success_count_local,
                    time.monotonic() - t_start_local,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "[NotificationSendView] Background batch failed: %s\n%s",
                    exc,
                    traceback.format_exc(),
                )

        user_ids_int = [int(uid) for uid in user_ids]
        # Сохраняем выбранных пользователей в сессию, чтобы показать статусы после redirect
        request.session["last_notification_user_ids"] = user_ids_int
        from django.utils import timezone

        request.session["last_notification_started_at"] = timezone.now().isoformat()
        threading.Thread(
            target=_run_batch_in_thread,
            args=(user_ids_int, message_text),
            daemon=True,
        ).start()
        # Используем PRG: после запуска фоновой рассылки перенаправляем на GET,
        # чтобы обновление страницы не вызывало повторный POST.
        return redirect("home")


class LastBatchStatusView(APIView):
    """JSON-эндпоинт для получения статусов последней рассылки."""

    def get(self, request, *args, **kwargs): # noqa
        from django.contrib.auth import get_user_model

        User = get_user_model()
        users_qs = User.objects.filter(is_staff=False).order_by("username")

        last_ids = request.session.get("last_notification_user_ids")
        started_at_iso = request.session.get("last_notification_started_at")

        if not last_ids or not started_at_iso:
            return Response({"statuses": [], "any_pending": False})

        from django.utils.dateparse import parse_datetime

        started_at = parse_datetime(started_at_iso)
        if started_at is None:
            started_at = None

        selected_users = users_qs.filter(id__in=last_ids)

        notification_types = [
            NotificationType.TELEGRAM,
            NotificationType.EMAIL,
            NotificationType.SMS,
        ]

        send_statuses: list[dict] = []
        any_pending = False

        for user in selected_users:
            user_item: dict = {
                "user_id": user.pk,
                "user_label": getattr(user, "username", str(user)),
                "statuses": [],
            }

            for nt in notification_types:
                qs = Notification.objects.filter(user=user, notification_type=nt)
                if started_at is not None:
                    qs = qs.filter(created_at__gte=started_at)
                last_notif = qs.order_by("-created_at").first()

                if not last_notif:
                    status_key = "not_sent"
                    status_label = "Не отправлялось"
                else:
                    if last_notif.status == NotificationStatus.PENDING:
                        status_key = "pending"
                        status_label = "В процессе"
                        any_pending = True
                    elif last_notif.status in (
                        NotificationStatus.SENT,
                        NotificationStatus.DELIVERED,
                    ):
                        status_key = "success"
                        status_label = "Успешно отправлено"
                    elif last_notif.status == NotificationStatus.FAILED:
                        status_key = "error"
                        status_label = "Ошибка отправки"
                    else:
                        status_key = "unknown"
                        status_label = "Статус неизвестен"

                if nt == NotificationType.TELEGRAM:
                    type_label = "Telegram"
                elif nt == NotificationType.EMAIL:
                    type_label = "Email"
                elif nt == NotificationType.SMS:
                    type_label = "SMS"
                else:
                    type_label = NotificationType(nt).label

                user_item["statuses"].append(
                    {
                        "type": nt,
                        "type_label": type_label,
                        "status": status_key,
                        "status_label": status_label,
                    }
                )

            send_statuses.append(user_item)

        return Response({"statuses": send_statuses, "any_pending": any_pending})


logger = logging.getLogger(__name__)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с уведомлениями.
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Возвращает только уведомления текущего пользователя."""
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=["post"])
    def send(self, request, *args, **kwargs):  # noqa
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
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        service = NotificationService(user=request.user)

        # Вызываем асинхронную функцию синхронно с помощью asyncio
        import asyncio
        import traceback

        async def send_async():
            return await service.send_notification(
                message=serializer.validated_data["message"],
                priority=serializer.validated_data["priority"],
                **serializer.validated_data.get("provider_kwargs", {}),
            )

        try:
            success = asyncio.run(send_async())

            if success:
                return Response(
                    {"status": "Уведомление успешно отправлено"},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "error": "Не удалось отправить уведомление ни одним из способов",
                        "details": "Проверьте настройки провайдеров и получателей",
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except asyncio.TimeoutError:
            logger.error("Превышено время ожидания при отправке уведомления")
            return Response(
                {"error": "Превышено время ожидания при отправке уведомления"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при отправке уведомления: {str(e)}\n{traceback.format_exc()}"
            )
            return Response(
                {"error": "Внутренняя ошибка сервера", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, *args, **kwargs):  # noqa
        """Помечает уведомление как прочитанное."""
        notification = self.get_object()
        notification.status = "read"
        notification.save()

        return Response(
            {"status": "Уведомление помечено как прочитанное"},
            status=status.HTTP_200_OK,
        )
