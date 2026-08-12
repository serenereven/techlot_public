"""
Django settings for techlot project using Django 5.2.8.
"""

from pathlib import Path
import os, sys
from django.apps import AppConfig
from celery.schedules import crontab

def str_to_bool(value):
    return str(value).lower() in ("true", "1", "yes")

CSRF_TRUSTED_ORIGINS = os.getenv(
    "DJANGO_CSRF_TRUSTED_ORIGINS", ""
).split(",")

SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https")
    if str_to_bool(os.getenv("DJANGO_SECURE_PROXY_SSL_HEADER", False))
    else None
)

SECURE_SSL_REDIRECT = str_to_bool(
    os.getenv("DJANGO_SECURE_SSL_REDIRECT", False)
)

SESSION_COOKIE_SECURE = str_to_bool(
    os.getenv("DJANGO_SESSION_COOKIE_SECURE", False)
)

CSRF_COOKIE_SECURE = str_to_bool(
    os.getenv("DJANGO_CSRF_COOKIE_SECURE", False)
)


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

DEBUG = os.getenv("DJANGO_DEBUG", "False")

ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS",).split(",")

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    "django.contrib.sites",
    "django.contrib.sitemaps",
    'django.contrib.humanize',

    'common',
    'core',

    'ckeditor',
    'ckeditor_uploader',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'techlot.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                
                "core.context_processors.global_header_footer",
            ],
        },
    },
]

WSGI_APPLICATION = 'techlot.wsgi.application'

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
DATABASES = {
    'default': {
        'ENGINE': os.getenv("DB_ENGINE"),
        'NAME': os.getenv("DB_NAME"),
        'USER': os.getenv("DB_USER"),
        'PASSWORD': os.getenv("DB_PASSWORD"),
        'HOST': os.getenv("DB_HOST"),
        'PORT': os.getenv("DB_PORT"),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ru-RU'
TIME_ZONE = 'Europe/Moscow' 
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'

# Media files
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.yandex.ru'
# EMAIL_PORT = 465
# EMAIL_USE_SSL = True
# #EMAIL_USE_TLS = True

# EMAIL_HOST_USER = ''
# EMAIL_HOST_PASSWORD = ''

# DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
# SERVER_EMAIL = EMAIL_HOST_USER
# EMAIL_ADMIN = EMAIL_HOST_USER

# CKEDITOR
CKEDITOR_UPLOAD_PATH = 'uploads/'
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Minimal',
        'toolbar_Minimal': [
            ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript', 'Superscript'],
            {'name': 'links',       'items': ['Link']},
            {'name': 'paragraph',   'items': ['NumberedList', 'BulletedList']},
            {'name': 'insert',      'items': ['Table']},
            {'name': 'raw',         'items': ['Source']},
        ],
        'height': 300,
        'width': '100%',
        'toolbarCanCollapse': False,
        'removePlugins': 'image,flash,iframe,forms,smiley,about,elementspath,scayt,wsc,',
        # если не хотите строгую фильтрацию, раскомментируйте:
        # 'allowedContent': True,
    }
}


# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# CACHES = {
#     "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
# }
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Ядро'
    
    def ready(self):
        import core.signals


BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL")
BITRIX_ASSIGNED_ID = os.getenv("BITRIX_ASSIGNED_ID")
BITRIX_TIMEOUT = 5

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ROUTES = {
    "core.tasks.sync_vehicle_from_bitrix": {"queue": "bitrix"},
}
CELERY_BEAT_SCHEDULE = {
    "sync_prices_sberleasing": {
        "task": "core.tasks.sync_prices_sberleasing",
        "schedule": crontab(hour=6, minute=0),  # каждый день в 06:00
    },
}

# Bitrix — входящий вебхук для чтения каталога товаров
# Отдельный от BITRIX_WEBHOOK_URL (лиды)
BITRIX_CATALOG_WEBHOOK_URL = os.getenv("BITRIX_CATALOG_WEBHOOK_URL")

# Секретный токен — Bitrix будет слать его в заголовке X-Bitrix-Token
# Генерируем один раз: python -c "import secrets; print(secrets.token_hex(32))"
# Передаём Bitrix-разработчику — он вставит в настройки исходящего события
BITRIX_INCOMING_TOKEN = os.getenv("BITRIX_INCOMING_TOKEN")

# Таймаут запросов к Bitrix REST (секунды)
BITRIX_TIMEOUT = int(os.getenv("BITRIX_TIMEOUT", default=15))

# Антидубли: блокировка повторных событий на N секунд
BITRIX_DEDUP_TTL = int(os.getenv("BITRIX_DEDUP_TTL", default=10))

BITRIX_CATALOG_SECRET = os.getenv("BITRIX_CATALOG_SECRET", default="no_secret")