import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Базовые настройки
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG").lower() == "true"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS").split(",")

# Приложения
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "users",
    "notifications",
]

# Промежуточное ПО
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

# URL-конфигурация
ROOT_URLCONF = "config.urls"

# Шаблоны
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# WSGI
WSGI_APPLICATION = "config.wsgi.application"

# База данных
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_INTERNAL_PORT"),
        "OPTIONS": {"client_encoding": "UTF8", "options": "-c search_path=public"},
    }
}

# Валидация паролей
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 6,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Локализация
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# Пользовательская модель пользователя
AUTH_USER_MODEL = "users.User"

# Настройки для логирования
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    # Базовый логгер по умолчанию
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        # Логгер HTTP-запросов Django (404/500 и т.п.).
        # Поднимаем уровень до ERROR, чтобы 404 (WARNING) не дублировались в логах.
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        # Логгер встроенного dev-сервера (строка вида "GET /... 404").
        # Оставляем только один вывод от него, не пропуская вверх к root.
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # Наши сервисы уведомлений
        "notifications.services.notification_service": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "notifications.services.providers.telegram_provider": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# Отключаем обработку статических файлов
STATIC_URL = "/static/"

# Настройки Email (Brevo)
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY")
EMAIL_SENDER_EMAIL = os.getenv("EMAIL_SENDER_EMAIL")
EMAIL_SENDER_NAME = os.getenv("EMAIL_SENDER_NAME")

# Настройки Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Настройки SMS (Exolve)
SMS_AUTH_TOKEN = os.getenv("SMS_AUTH_TOKEN")
SMS_PHONE_NUMBER = os.getenv("SMS_PHONE_NUMBER")

# Глобальные настройки DRF.
REST_FRAMEWORK = {
    # Оставляем стандартные рендереры DRF, включая Browsable API, чтобы
    # /api/ и другие endpoints отображались в удобном HTML-интерфейсе.
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}
