from techlot.settings import *  # noqa

# Тестовая база данных SQLite in-memory
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Минимальные настройки для тестов
SECRET_KEY = "test-secret-key-for-tests"
DEBUG = False

# Отключаем кеш для тестов
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# Минимальные настройки для Celery (чтобы не падало при импорте)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Заглушки для Bitrix
BITRIX_WEBHOOK_URL = "https://example.com/rest/"
BITRIX_CATALOG_WEBHOOK_URL = "https://example.com/rest/"
BITRIX_TIMEOUT = 5
BITRIX_DEDUP_TTL = 10
