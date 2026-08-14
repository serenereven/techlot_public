from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Соответствие статусов Bitrix → StockStatus
# Значения берём из valueEnum поля property117
# ------------------------------------------------------------------
BITRIX_STATUS_MAP: dict[str, str] = {
    "\u0412 \u043d\u0430\u043b\u0438\u0447\u0438\u0438": "in_stock",
    "\u0412 \u0440\u0435\u0437\u0435\u0440\u0432\u0435": "reserved",
    "\u0412 \u043e\u0436\u0438\u0434\u0430\u043d\u0438\u0438 \u043f\u043e\u0441\u0442\u0443\u043f\u043b\u0435\u043d\u0438\u044f": "awaiting",
    "\u041f\u0440\u043e\u0434\u0430\u043d\u043e": "sold",
}

# ------------------------------------------------------------------
# Вспомогательные функции
# ------------------------------------------------------------------


def _prop_value(product: dict, prop_key: str) -> Any:
    """
    Извлекает значение пользовательского свойства.

    Bitrix отдаёт свойство в двух форматах:
    - dict:  {"value": "123", "valueEnum": "В наличии", "valueId": "2559"}
    - str:   "Y", "N"  (булевые поля)
    - None:  поле не заполнено

    Для списочных полей возвращаем valueEnum (читаемое значение),
    для остальных — value напрямую.
    """
    raw = product.get(prop_key)
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw.get("valueEnum") or raw.get("value")
    # "N" в Bitrix означает "не заполнено" для списочных полей
    if raw == "N":
        return None
    return raw


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (TypeError, InvalidOperation):
        return None


def _get_or_create(model_class, **kwargs):
    try:
        obj, _ = model_class.objects.get_or_create(**kwargs)
        return obj
    except Exception as e:
        logger.error("get_or_create %s %s: %s", model_class.__name__, kwargs, e)
        return None


# ------------------------------------------------------------------
# Маппинг полей
# ------------------------------------------------------------------


def map_bitrix_to_vehicle_fields(product: dict[str, Any]) -> dict[str, Any]:
    """
    Принимает dict от catalog.product.get и возвращает dict полей
    готовых для Vehicle(**fields) или update(**fields).

    Фото и цена обрабатываются отдельно в sync.py.
    """
    from core.models import (
        Brand,
        VehicleModel,
        VehicleType,
        EngineType,
        Transmission,
        TechnicalCondition,
        City,
    )

    fields: dict[str, Any] = {}

    # Базовые поля
    fields["title"] = product.get("name") or ""
    fields["content"] = product.get("detailText") or product.get("previewText") or ""

    # VIN / артикул — property109
    vin = _prop_value(product, "property109")
    if vin:
        fields["vin"] = str(vin).strip()

    # Пробег — property127
    mileage = _safe_int(_prop_value(product, "property127"))
    if mileage is not None:
        fields["mileage_km"] = mileage

    # Мощность двигателя — property131
    power = _safe_decimal(_prop_value(product, "property131"))
    if power is not None:
        fields["engine_power_hp"] = power

    # Цвет — property139
    color = _prop_value(product, "property139")
    if color:
        fields["color"] = str(color).strip()

    # Колёсная формула — property135
    wheel = _prop_value(product, "property135")
    if wheel:
        fields["wheel_formula"] = str(wheel).strip()

    # Опубликовано — property113 (булевое Y/N)
    is_published = _prop_value(product, "property113")
    fields["is_published"] = is_published == "Y"

    # Статус — property117 (списочное, берём valueEnum)
    raw_status = _prop_value(product, "property117")
    if raw_status:
        mapped = BITRIX_STATUS_MAP.get(str(raw_status))
        if mapped:
            fields["stock_status"] = mapped
        else:
            logger.warning("mapper: неизвестный статус Bitrix: %r", raw_status)

    # Марка — property123 (списочное, берём valueEnum)
    brand_name = _prop_value(product, "property123")
    brand = _get_or_create(Brand, name=str(brand_name).strip()) if brand_name else None
    fields["brand"] = brand

    # Модель — property141 (текстовое поле "Модель 2.0")
    model_name = _prop_value(product, "property141")
    fields["model"] = (
        _get_or_create(VehicleModel, brand=brand, name=str(model_name).strip()) if (model_name and brand) else None
    )

    # Год выпуска — property143
    year = _safe_int(_prop_value(product, "property143"))
    if year is not None:
        fields["year"] = year

    # Тип двигателя — property129
    engine_type_name = _prop_value(product, "property129")
    fields["engine_type"] = _get_or_create(EngineType, name=str(engine_type_name).strip()) if engine_type_name else None

    # Коробка передач — property133
    transmission_name = _prop_value(product, "property133")
    fields["transmission"] = (
        _get_or_create(Transmission, name=str(transmission_name).strip()) if transmission_name else None
    )

    # Техническое состояние — property137
    condition_name = _prop_value(product, "property137")
    fields["technical_condition"] = (
        _get_or_create(TechnicalCondition, name=str(condition_name).strip()) if condition_name else None
    )

    # Вид номенклатуры / тип техники — property107
    vehicle_type_name = _prop_value(product, "property107")
    fields["vehicle_type"] = (
        _get_or_create(VehicleType, name=str(vehicle_type_name).strip()) if vehicle_type_name else None
    )

    # Город / площадка — property119
    city_name = _prop_value(product, "property119")
    if city_name:
        fields["city"] = City.objects.filter(name=str(city_name).strip()).first()
    else:
        fields["city"] = None

    return fields


def extract_photo_urls(product: dict, **kwargs) -> list:
    """
    Возвращает список urlMachine из полей с фото.
    property45 — основной iblock (iblockId=15)
    property49 — второй iblock (iblockId=17)
    """
    urls = []
    for prop_key in ("property45", "property49"):
        for item in product.get(prop_key) or []:
            value = item.get("value") if isinstance(item, dict) else None
            if isinstance(value, dict):
                url = value.get("urlMachine")
                if url:
                    urls.append(url)
    return urls
