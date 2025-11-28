"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from notifications.views import HealthCheckView, SimpleView, NotificationSendView

urlpatterns = [
    # Основные маршруты
    path('', NotificationSendView.as_view(), name='home'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
    
    # API маршруты
    path('api/', include('notifications.urls')),
    path('api/auth/', include('users.urls')),
    
    # Админ-панель
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
