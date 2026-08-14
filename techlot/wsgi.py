import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "techlot.settings")

import celery_app  # инициализируем Celery до Django

application = get_wsgi_application()
