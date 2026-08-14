import logging

from celery import shared_task
# from celery.schedules import crontab

from core.import_utils import sync_prices_from_feed
from core.models import Vehicle

from django.db import DataError, IntegrityError

logger = logging.getLogger(__name__)


NON_RETRYABLE_EXCEPTIONS = (DataError, IntegrityError, ValueError)


@shared_task(
    name="core.tasks.sync_vehicle_from_bitrix",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="bitrix",
)
def sync_vehicle_from_bitrix(self, bitrix_product_id: int) -> str:
    logger.info("Task sync_vehicle_from_bitrix[%s]: product_id=%s", self.request.id, bitrix_product_id)

    try:
        from core.services.bitrix.sync import sync_vehicle

        vehicle = sync_vehicle(bitrix_product_id)
    except NON_RETRYABLE_EXCEPTIONS as exc:
        logger.error(
            "Task sync_vehicle_from_bitrix %s: неповторимая ошибка, retry не поможет: %s",
            bitrix_product_id,
            exc,
        )
        raise
    except Exception as exc:
        logger.exception(
            "Task sync_vehicle_from_bitrix %s: необработанная ошибка: %s",
            bitrix_product_id,
            exc,
        )
        raise self.retry(exc=exc) from exc

    if vehicle is None:
        logger.warning("Task sync_vehicle_from_bitrix %s: товар пропущен", bitrix_product_id)
        return f"skipped:{bitrix_product_id}"

    return f"synced:{vehicle.pk}"


@shared_task(
    name="core.tasks.sync_prices_sberleasing",
    queue="default",
)
def sync_prices_sberleasing() -> str:
    """Обновляет цены из XML-фида SberLeasing. Запускается по расписанию раз в сутки."""
    logger.info("Task sync_prices_sberleasing: start")

    try:
        result = sync_prices_from_feed(Vehicle=Vehicle)
    except Exception as exc:
        logger.exception("Task sync_prices_sberleasing: ошибка: %s", exc)
        raise

    logger.info(
        "Task sync_prices_sberleasing: обновлено=%d, пропущено=%d, ошибок=%d",
        result["updated"],
        result["skipped"],
        result["errors"],
    )
    return f"updated={result['updated']} skipped={result['skipped']} errors={result['errors']}"


# Расписание для celery beat — добавить в settings.py:
#
# from celery.schedules import crontab
# CELERY_BEAT_SCHEDULE = {
#     "sync_prices_sberleasing": {
#         "task": "core.tasks.sync_prices_sberleasing",
#         "schedule": crontab(hour=6, minute=0),  # каждый день в 06:00
#     },
# }
