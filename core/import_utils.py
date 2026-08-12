import logging
import re
import urllib.request
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

import pandas as pd
from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils.text import slugify

logger = logging.getLogger(__name__)

SBERLEASING_FEED_URL = "https://www.sberleasing.ru/upload/feeds/realizaciya_dealers_feed.xml"


def normalize(value):
    if value is None:
        return ""
    try:
        if isinstance(value, float) and pd.isna(value):
            return ""
    except Exception:
        pass
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return str(value).strip()
    return str(value).strip()


def has_changes(obj, data: dict) -> bool:
    for field, new_value in data.items():
        if getattr(obj, field) != new_value:
            return True
    return False


FEDERAL_CITIES = {
    "москва": "Москва",
    "санкт-петербург": "Санкт-Петербург",
    "севастополь": "Севастополь",
}

REGION_PATTERNS = [
    r"(Республика\s+[А-ЯЁа-яё\s\-]+)",
    r"([А-ЯЁа-яё\s\-]+?\s+область)",
    r"([А-ЯЁа-яё\s\-]+?\s+край)",
    r"([А-ЯЁа-яё\s\-]+?\s+автономный округ)",
]

COLUMN_ALIASES = {
    "Забронировано?": ["Забронировано?", "Бронь"],
    "Название": ["Название", "Наименование"],
    "Вид техники": ["Вид техники", "Вид теххники", "Тип техники"],
    "Марка": ["Марка", "Бренд"],
    "Модель": ["Модель"],
    "VIN": ["VIN", "Vin", "vin"],
    "Год выпуска": ["Год выпуска", "Год"],
    "Адрес": ["Адрес", "Местоположение"],
    "Стоимость": ["Стоимость", "Цена"],
    "Пробег": ["Пробег", "Пробег, км"],
    "Тип двигателя": ["Тип двигателя", "Тип Двигателя", "Двигатель", "Тип мотора"],
    "Мощность двигателя": ["Мощность двигателя", "Мощность Двигателя", "Мощность", "Мощность, л.с.", "л.с."],
    "Коробка передач": ["Коробка передач", "Коробка передач ", "КПП", "Трансмиссия"],
    "Колесная формула": ["Колесная формула", "Колёсная формула", "Колесная схема", "Колёсная схема"],
    "Техническое состояние": ["Техническое состояние", "Состояние", "Тех. состояние", "Техническое сост."],
    "Цвет": ["Цвет", "Окрас"],
}

# Алиасы для прайс-листа (VIN + цена)
PRICE_COLUMN_ALIASES = {
    "VIN": ["VIN", "Vin", "vin"],
    "Стоимость": ["Стоимость", "Цена", "Price", "price"],
}


def parse_region_city(address: str) -> tuple[str | None, str | None]:
    if not address:
        return None, None

    text = str(address).strip()
    lower = text.lower()

    for key, name in FEDERAL_CITIES.items():
        if key in lower:
            return name, text

    region = None
    region_span = None
    for pattern in REGION_PATTERNS:
        m = re.search(pattern, text)
        if m:
            region = m.group(1).strip()
            region_span = m.span(1)
            break

    if not region:
        return None, text

    start, end = region_span
    city = (text[:start] + text[end:]).strip().strip(" ,;|-–—")
    return region, city or None


def get_col(row, df_columns, logical_name: str):
    aliases = COLUMN_ALIASES.get(logical_name, [])
    for col in aliases:
        if col in df_columns:
            return row[col]
    raise KeyError(f"Колонка '{logical_name}' не найдена (алиасы: {aliases})")


def get_col_optional(row, df_columns, logical_name: str, default=""):
    aliases = COLUMN_ALIASES.get(logical_name, [])
    for col in aliases:
        if col in df_columns:
            return row[col]
    return default


def _get_price_col(row, df_columns, logical_name: str):
    """get_col для прайс-листа (использует PRICE_COLUMN_ALIASES)."""
    aliases = PRICE_COLUMN_ALIASES.get(logical_name, [])
    for col in aliases:
        if col in df_columns:
            return row[col]
    raise KeyError(f"Колонка '{logical_name}' не найдена (алиасы: {aliases})")


def make_code(value: str, max_len: int = 32) -> str:
    value = normalize(value)
    code = slugify(value, allow_unicode=True)[:max_len]
    return code or "other"


def get_or_create_cached(*, Model, cache: dict, name: str):
    name = normalize(name)
    if not name:
        return None
    key = name.lower()
    obj = cache.get(key)
    if obj:
        return obj
    obj, _ = Model.objects.get_or_create(name=name)
    cache[key] = obj
    return obj


def log_admin_action(user_id, obj, action_flag, message=""):
    LogEntry.objects.log_action(
        user_id=user_id,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=str(obj),
        action_flag=action_flag,
        change_message=message,
    )

_YEAR_RE = re.compile(r"(19\d{2}|20\d{2}|21\d{2})")
_NUM_RE = re.compile(r"[^\d,.\-]+")


def parse_year(value):
    s = normalize(value)
    if not s:
        return None
    m = _YEAR_RE.search(s)
    if m:
        y = int(m.group(1))
        return y if 1900 <= y <= 2100 else None
    return None


def to_decimal(value, default=None) -> Decimal | None:
    s = normalize(value)
    if not s:
        return default
    s = _NUM_RE.sub("", s)
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    elif "," in s and "." in s:
        s = s.replace(",", "")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return default


def to_int(value, default=None):
    s = normalize(value)
    if not s:
        return default
    s = _NUM_RE.sub("", s)
    try:
        return int(s)
    except ValueError:
        return default


class DryRunRollback(Exception):
    pass


def import_vehicles_xlsx(
    *,
    file,
    dry_run: bool,
    publish: bool,
    user_id,
    Region,
    City,
    Brand,
    VehicleModel,
    VehicleType,
    Vehicle,
    StockStatus,
    EngineType,
    Transmission,
    TechnicalCondition,
    skiprows: int = 1,
    preview_limit: int = 50,
):
    df = pd.read_excel(file, skiprows=skiprows, dtype=str).fillna("")
    columns = df.columns

    regions_cache = {r.name.lower(): r for r in Region.objects.all()}
    brands_cache = {b.name.lower(): b for b in Brand.objects.all()}
    vehicle_types_cache = {vt.code: vt for vt in VehicleType.objects.all()}
    engine_types_cache = {e.name.lower(): e for e in EngineType.objects.all()}
    transmissions_cache = {t.name.lower(): t for t in Transmission.objects.all()}
    tech_conditions_cache = {tc.name.lower(): tc for tc in TechnicalCondition.objects.all()}
    cities_cache = {}
    models_cache = {}

    created = updated = skipped = 0
    preview = []

    vins = [
        normalize(get_col(row, columns, "VIN"))
        for _, row in df.iterrows()
        if normalize(get_col(row, columns, "VIN"))
    ]
    existing_by_vin = {v.vin: v for v in Vehicle.objects.filter(vin__in=set(vins))} if vins else {}

    reserved_yes = {"да", "yes", "true", "1", "y"}

    try:
        with transaction.atomic():
            for _, row in df.iterrows():

                vin = normalize(get_col(row, columns, "VIN"))
                if not vin:
                    skipped += 1
                    if len(preview) < preview_limit:
                        preview.append(("skip", "—", "нет VIN"))
                    continue

                reserved_raw = normalize(get_col(row, columns, "Забронировано?")).lower()
                stock_status = StockStatus.RESERVED if reserved_raw in reserved_yes else StockStatus.IN_STOCK

                address = normalize(get_col(row, columns, "Адрес"))
                region_name, city_name = parse_region_city(address)

                region = None
                if region_name:
                    region_key = region_name.lower()
                    region = regions_cache.get(region_key)
                    if not region:
                        region, _ = Region.objects.get_or_create(name=region_name)
                        regions_cache[region_key] = region

                city = None
                if region and city_name:
                    city_key = (region.id, city_name.lower())
                    city = cities_cache.get(city_key)
                    if not city:
                        city, _ = City.objects.get_or_create(region=region, name=city_name)
                        cities_cache[city_key] = city

                vt_raw = normalize(get_col(row, columns, "Вид техники"))
                vehicle_type = None
                if vt_raw:
                    vt_code = make_code(vt_raw)
                    vehicle_type = vehicle_types_cache.get(vt_code)
                    if not vehicle_type:
                        vehicle_type = VehicleType.objects.create(code=vt_code, name=vt_raw)
                        vehicle_types_cache[vt_code] = vehicle_type

                brand_name = normalize(get_col(row, columns, "Марка"))
                brand = None
                if brand_name:
                    brand_key = brand_name.lower()
                    brand = brands_cache.get(brand_key)
                    if not brand:
                        brand, _ = Brand.objects.get_or_create(name=brand_name)
                        brands_cache[brand_key] = brand

                model_name = normalize(get_col(row, columns, "Модель"))
                model = None
                if brand and model_name:
                    model_key = (brand.id, model_name.lower())
                    model = models_cache.get(model_key)
                    if not model:
                        model, _ = VehicleModel.objects.get_or_create(brand=brand, name=model_name)
                        models_cache[model_key] = model

                engine_type = get_or_create_cached(
                    Model=EngineType,
                    cache=engine_types_cache,
                    name=get_col_optional(row, columns, "Тип двигателя"),
                )
                transmission = get_or_create_cached(
                    Model=Transmission,
                    cache=transmissions_cache,
                    name=get_col_optional(row, columns, "Коробка передач"),
                )
                technical_condition = get_or_create_cached(
                    Model=TechnicalCondition,
                    cache=tech_conditions_cache,
                    name=get_col_optional(row, columns, "Техническое состояние"),
                )

                year = parse_year(get_col(row, columns, "Год выпуска"))
                price = to_decimal(get_col(row, columns, "Стоимость"), default=None)
                mileage = to_int(get_col(row, columns, "Пробег"), default=None)
                engine_power_hp = to_decimal(get_col_optional(row, columns, "Мощность двигателя"), default=None)
                wheel_formula = normalize(get_col_optional(row, columns, "Колесная формула"))
                color = normalize(get_col_optional(row, columns, "Цвет"))

                title_raw = normalize(get_col(row, columns, "Название"))
                if not title_raw and brand and model:
                    parts = [brand.name, model.name]
                    if year:
                        parts.append(str(year))
                    title_raw = " ".join(parts)

                data = {}
                if stock_status:
                    data["stock_status"] = stock_status
                if title_raw:
                    data["title"] = title_raw
                if city:
                    data["city"] = city
                if vehicle_type:
                    data["vehicle_type"] = vehicle_type
                if brand:
                    data["brand"] = brand
                if model:
                    data["model"] = model
                if year:
                    data["year"] = year
                if price is not None:
                    data["price_rub"] = price
                if mileage is not None:
                    data["mileage_km"] = mileage
                if engine_type:
                    data["engine_type"] = engine_type
                if engine_power_hp is not None:
                    data["engine_power_hp"] = engine_power_hp
                if transmission:
                    data["transmission"] = transmission
                if wheel_formula:
                    data["wheel_formula"] = wheel_formula
                if technical_condition:
                    data["technical_condition"] = technical_condition
                if color:
                    data["color"] = color

                vehicle = existing_by_vin.get(vin)

                if vehicle:
                    if has_changes(vehicle, data):
                        updated += 1
                        if len(preview) < preview_limit:
                            preview.append(("update", title_raw or vin))

                        if not dry_run:
                            for field, value in data.items():
                                setattr(vehicle, field, value)

                            if getattr(vehicle, "deleted_at", None):
                                vehicle.restore()

                            if publish:
                                vehicle.publish(commit=False)

                            vehicle.save()
                            log_admin_action(user_id, vehicle, CHANGE, "Обновлено через импорт XLSX")
                    else:
                        skipped += 1
                        if len(preview) < preview_limit:
                            preview.append(("skip", title_raw or vin))
                else:
                    created += 1
                    if len(preview) < preview_limit:
                        preview.append(("create", title_raw or vin))

                    if not dry_run:
                        v = Vehicle.objects.create(**data, vin=vin, is_published=publish)
                        if publish:
                            v.publish()
                        existing_by_vin[vin] = v
                        log_admin_action(user_id, v, ADDITION, "Создано через импорт XLSX")

            if dry_run:
                raise DryRunRollback()

    except DryRunRollback:
        pass

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "preview": preview,
        "dry_run": dry_run,
    }


def import_prices_xlsx(
    *,
    file,
    dry_run: bool,
    user_id,
    Vehicle,
    skiprows: int = 0,
    preview_limit: int = 50,
):
    """
    Обновляет только цену (price_rub) по VIN.
    Машин, которых нет в файле, не трогает — цена остаётся старой.
    Машин, которых нет в БД, пропускает (не создаёт).
    """
    df = pd.read_excel(file, skiprows=skiprows, dtype=str).fillna("")
    columns = df.columns

    updated = skipped = 0
    preview = []

    # Собираем пары VIN → цена из файла
    price_by_vin: dict[str, Decimal] = {}
    for _, row in df.iterrows():
        vin = normalize(_get_price_col(row, columns, "VIN"))
        price = to_decimal(_get_price_col(row, columns, "Стоимость"), default=None)
        if vin and price is not None:
            price_by_vin[vin] = price

    if not price_by_vin:
        return {"updated": 0, "skipped": 0, "preview": [], "dry_run": dry_run}

    # Загружаем только те машины, чьи VIN есть в файле
    existing = {v.vin: v for v in Vehicle.objects.filter(vin__in=price_by_vin.keys())}

    try:
        with transaction.atomic():
            for vin, price in price_by_vin.items():
                vehicle = existing.get(vin)

                if not vehicle:
                    # VIN из файла не найден в БД — пропускаем
                    skipped += 1
                    if len(preview) < preview_limit:
                        preview.append(("skip", vin, "не найден в БД"))
                    continue

                if vehicle.price_rub == price:
                    # Цена не изменилась
                    skipped += 1
                    if len(preview) < preview_limit:
                        preview.append(("skip", vin, "цена не изменилась"))
                    continue

                updated += 1
                if len(preview) < preview_limit:
                    preview.append(("update", vin, f"{vehicle.price_rub} → {price}"))

                if not dry_run:
                    vehicle.price_rub = price
                    vehicle.save(update_fields=["price_rub", "updated_at"])
                    log_admin_action(user_id, vehicle, CHANGE, "Цена обновлена через прайс-лист XLSX")

            if dry_run:
                raise DryRunRollback()

    except DryRunRollback:
        pass

    return {
        "updated": updated,
        "skipped": skipped,
        "preview": preview,
        "dry_run": dry_run,
    }


def sync_prices_from_feed(
    *,
    Vehicle,
    user_id: int | None = None,
    url: str = SBERLEASING_FEED_URL,
    preview_limit: int = 50,
) -> dict:
    """
    Загружает XML-фид и обновляет price_rub по VIN.
    Машины, которых нет в фиде, не трогает.
    Машины из фида, которых нет в БД, пропускает.
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; price-sync/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        root = ElementTree.parse(resp).getroot()

    price_by_vin: dict[str, Decimal] = {}
    for ad in root.iter("Ad"):
        vin = (ad.findtext("VIN") or "").strip()
        raw = (ad.findtext("Price") or "").strip()
        if not vin or not raw:
            continue
        try:
            price_by_vin[vin] = Decimal(raw)
        except InvalidOperation:
            logger.warning("Некорректная цена в фиде: VIN=%s Price=%s", vin, raw)

    if not price_by_vin:
        logger.warning("Фид пуст или не содержит корректных записей: %s", url)
        return {"updated": 0, "skipped": 0, "errors": 0, "preview": []}

    existing = {v.vin: v for v in Vehicle.objects.filter(vin__in=price_by_vin.keys())}

    updated = skipped = errors = 0
    preview: list[tuple] = []

    with transaction.atomic():
        for vin, new_price in price_by_vin.items():
            vehicle = existing.get(vin)

            if not vehicle:
                skipped += 1
                if len(preview) < preview_limit:
                    preview.append(("skip", vin, "не найден в БД"))
                continue

            if vehicle.price_rub == new_price:
                skipped += 1
                if len(preview) < preview_limit:
                    preview.append(("skip", vin, "цена не изменилась"))
                continue

            try:
                old_price = vehicle.price_rub
                vehicle.price_rub = new_price
                vehicle.save(update_fields=["price_rub", "updated_at"])
                if user_id:
                    log_admin_action(user_id, vehicle, CHANGE, "Цена обновлена из XML SberLeasing")
                updated += 1
                if len(preview) < preview_limit:
                    preview.append(("update", vin, f"{old_price} → {new_price}"))
            except Exception:
                logger.exception("Ошибка при обновлении цены VIN=%s", vin)
                errors += 1

    logger.info("Синхронизация цен: обновлено=%d, пропущено=%d, ошибок=%d", updated, skipped, errors)
    return {"updated": updated, "skipped": skipped, "errors": errors, "preview": preview}