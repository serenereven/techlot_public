import os

# Минимальные переменные окружения для тестов
os.environ.setdefault("DATABASE_URL", "sqlite:///test_db.sqlite3")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests")
os.environ.setdefault("DEBUG", "False")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
os.environ.setdefault("BITRIX_WEBHOOK_URL", "https://example.com/rest/")
os.environ.setdefault("BITRIX_CATALOG_WEBHOOK_URL", "https://example.com/rest/")
