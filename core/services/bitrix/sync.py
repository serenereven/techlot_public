from __future__ import annotations
import logging
from typing import Any
from django.core.files.base import ContentFile
from django.db import transaction
from core.models import Vehicle, VehiclePhoto
from .catalog import BitrixCatalogClient
from .exceptions import BitrixError
from .mapper import map_bitrix_to_vehicle_fields, extract_photo_urls
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

# Поля, без которых обновление существующей карточки не выполняется.
# Это защита от затирания корректных данных неполным ответом Битрикс
# в момент, когда 1С ещё не закончил запись.
REQUIRED_FIELDS = ["brand"]


def sync_vehicle(bitrix_product_id: int) -> Vehicle | None:
    client = BitrixCatalogClient()

    try:
        product = client.get_product(bitrix_product_id)
    except BitrixError as e:
        logger.error(
            "sync_vehicle %s: ошибка получения товара: %s",
            bitrix_product_id,
            e,
        )
        return None

    if not product:
        logger.warning(
            "sync_vehicle %s: пустой ответ от Bitrix",
            bitrix_product_id,
        )
        return None

    # ---------------------------------------------------------
    # Если пришла вариация (offer), то свойства техники
    # берём у родительского товара.
    # Цена и фотографии остаются от offer.
    # ---------------------------------------------------------
    if _is_offer(product):
        parent_id = _get_parent_id(product)

        if not parent_id:
            logger.warning(
                "sync_vehicle %s: не удалось определить parentId",
                bitrix_product_id,
            )
            return None

        try:
            parent_product = client.get_product(parent_id)
        except BitrixError as e:
            logger.error(
                "sync_vehicle %s: ошибка получения родителя %s: %s",
                bitrix_product_id,
                parent_id,
                e,
            )
            return None

        if not parent_product:
            logger.warning(
                "sync_vehicle %s: родитель %s не найден",
                bitrix_product_id,
                parent_id,
            )
            return None

        sync_id = parent_id
        fields = map_bitrix_to_vehicle_fields(parent_product)

    else:
        sync_id = bitrix_product_id
        fields = map_bitrix_to_vehicle_fields(product)

    # Цена всегда берётся именно у SKU (или у самого товара)
    price = client.get_price(bitrix_product_id)

    if price is not None:
        fields["price_rub"] = price
    else:
        fields["price_rub"] = 0

    with transaction.atomic():
        vehicle = _upsert_vehicle(sync_id, fields)

        if vehicle is None:
            return None

        # Фото также оставляем от SKU
        _sync_photos(vehicle, product, client)

    logger.info(
        "sync_vehicle %s: готово → Vehicle pk=%s",
        bitrix_product_id,
        vehicle.pk,
    )

    return vehicle


# ------------------------------------------------------------------
# Внутренние функции
# ------------------------------------------------------------------


def _is_offer(product: dict[str, Any]) -> bool:
    """
    Определяет является ли товар вариацией (offer/SKU).
    Bitrix у вариаций заполняет parentId.
    parentId может прийти как dict {"value": "1281"} или как число.
    """
    parent = product.get("parentId")
    if parent is None:
        return False
    if isinstance(parent, dict):
        return bool(parent.get("value"))
    return bool(parent)


def _get_parent_id(product: dict[str, Any]) -> int | None:
    """Извлекает ID основного товара из поля parentId."""
    parent = product.get("parentId")
    if isinstance(parent, dict):
        try:
            return int(parent.get("value", 0))
        except (TypeError, ValueError):
            return None
    try:
        return int(parent)
    except (TypeError, ValueError):
        return None


def _upsert_vehicle(bitrix_id: int, fields: dict[str, Any]) -> Vehicle | None:
    vehicle = None
    is_new = False

    if hasattr(Vehicle, "bitrix_id"):
        vehicle = Vehicle.alive.filter(bitrix_id=bitrix_id).first()

    if vehicle is None and fields.get("vin"):
        vehicle = Vehicle.alive.filter(vin=fields["vin"]).first()

    if vehicle is None:
        # Новая карточка: создаём только если данные полные.
        # Пустышку создавать не имеет смысла — задача уйдёт на повтор.
        missing = [f for f in REQUIRED_FIELDS if not fields.get(f)]
        if missing:
            logger.warning(
                "sync_vehicle %s: новая карточка, но поля %s пустые — пропускаем",
                bitrix_id,
                missing,
            )
            return None

        vehicle = Vehicle()
        is_new = True
        logger.info("sync_vehicle %s: создаём новый Vehicle", bitrix_id)
    else:
        is_new = False
        # Существующая карточка: не перезаписываем данные неполным ответом.
        missing = [f for f in REQUIRED_FIELDS if not fields.get(f)]
        if missing:
            logger.warning(
                "sync_vehicle %s: обновление Vehicle pk=%s заблокировано — поля %s пустые, "
                "данные из 1С ещё не подтянулись",
                bitrix_id,
                vehicle.pk,
                missing,
            )
            return None
        logger.info("sync_vehicle %s: обновляем Vehicle pk=%s", bitrix_id, vehicle.pk)

    for field, value in fields.items():
        setattr(vehicle, field, value)

    if hasattr(vehicle, "bitrix_id"):
        vehicle.bitrix_id = bitrix_id

    vehicle.save()

    LogEntry.objects.log_action(
        user_id=1,
        content_type_id=ContentType.objects.get_for_model(Vehicle).pk,
        object_id=vehicle.pk,
        object_repr=str(vehicle),
        action_flag=ADDITION if is_new else CHANGE,
        change_message=f"{'Импортировано' if is_new else 'Обновлено'} из Bitrix24 (product_id={bitrix_id})",
    )

    return vehicle


def _sync_photos(vehicle: Vehicle, product: dict[str, Any], client: BitrixCatalogClient) -> None:
    """
    Скачивает фото из Bitrix и сохраняет в VehiclePhoto.
    Поддерживает property45 и property49 (разные iblock).
    """
    urls = extract_photo_urls(product)

    if not urls:
        logger.info("sync_vehicle %s: фото не найдены", vehicle.pk)
        return

    vehicle.photos.all().delete()

    saved = 0
    for sort_order, url in enumerate(urls):
        # urlMachine может быть относительным — дополняем базовым URL
        if url.startswith("/rest/"):
            from django.conf import settings

            # from urllib.parse import urlparse
            base = settings.BITRIX_CATALOG_WEBHOOK_URL.rstrip("/")
            # parsed = urlparse(base)
            # Токен уже есть в base_url вебхука
            url = f"{base}{url[5:]}"  # убираем /rest и подставляем полный URL с токеном

        content = client.download_photo(url)
        if not content:
            continue

        photo = VehiclePhoto(
            vehicle=vehicle,
            sort_order=sort_order,
            is_main=(sort_order == 0),
        )
        filename = f"bitrix_{vehicle.pk}_{sort_order}.jpg"
        photo.image.save(filename, ContentFile(content), save=True)
        saved += 1

    logger.info("sync_vehicle %s: сохранено %d фото", vehicle.pk, saved)
