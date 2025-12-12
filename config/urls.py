from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from notifications.views import HealthCheckView, NotificationSendView, SimpleView

urlpatterns = [
    path("", NotificationSendView.as_view(), name="home"),
    re_path(r"^health/?$", HealthCheckView.as_view(), name="health-check"),
    re_path(r"^status/?$", SimpleView.as_view(), name="service-status"),
    # API маршруты: одинаково работают с / и без него
    re_path(r"^api/?", include("notifications.urls")),
    re_path(r"^api/auth/?", include("users.urls")),
    # Админ-панель: /admin и /admin/ работают одинаково
    re_path(r"^admin/?", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
