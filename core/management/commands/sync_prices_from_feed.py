"""
Management command: sync_prices_from_feed

Запуск вручную:
    python manage.py sync_prices_from_feed
    python manage.py sync_prices_from_feed --url https://example.com/feed.xml

Cron (каждые сутки в 06:00):
0 6 * * * docker exec techlot_web python manage.py sync_prices_from_feed >> /var/log/sync_prices.log 2>&1
"""

import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.import_utils import SBERLEASING_FEED_URL, sync_prices_from_feed
from core.models import Vehicle

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Обновляет цены на технику из XML-фида SberLeasing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            default=SBERLEASING_FEED_URL,
            help="URL фида (по умолчанию фид SberLeasing)",
        )

    def handle(self, *args, **options):
        self.stdout.write("Запуск синхронизации цен из фида...")

        User = get_user_model()
        user_id = User.objects.filter(is_superuser=True).values_list("id", flat=True).first()

        try:
            result = sync_prices_from_feed(
                Vehicle=Vehicle,
                url=options["url"],
                user_id=user_id,
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Ошибка при загрузке фида: {e}"))
            logger.exception("Ошибка sync_prices_from_feed")
            raise SystemExit(1)

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: обновлено={result['updated']}, "
                f"пропущено={result['skipped']}, "
                f"ошибок={result['errors']}"
            )
        )