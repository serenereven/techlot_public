import pandas as pd
import io
from typing import Optional, Dict, List
from django.core.cache import cache


def generate_vehicles_vin_excel(request=None) -> bytes:
    """
    Генерирует Excel файл со списком техники (все поля).
    """
    from .models import Vehicle

    vehicles = Vehicle.objects.alive().published().select_related(
        'brand', 'model', 'city', 'city__region',
        'vehicle_type', 'engine_type', 'transmission', 'technical_condition',
    ).only(
        'vin', 'slug', 'brand__name', 'model__name', 'year',
        'price_rub', 'stock_status', 'city__name', 'city__region__name',
        'vehicle_type__name', 'engine_type__name', 'transmission__name',
        'technical_condition__name', 'mileage_km', 'color',
        'engine_power_hp', 'wheel_formula',
    ).order_by('-created_at')

    data = _prepare_vehicles_data(vehicles, request)
    excel_bytes = _create_excel_file(data)

    return excel_bytes


def _prepare_vehicles_data(vehicles, request=None) -> List[Dict]:
    """
    Подготавливает данные для экспорта (все поля).
    """
    data = []

    for vehicle in vehicles:
        # Формируем ссылку
        link = f"/catalog/{vehicle.slug}/"
        if request:
            link = request.build_absolute_uri(link)

        data.append({
            'VIN': vehicle.vin or '',
            'Марка': vehicle.brand.name if vehicle.brand else '',
            'Модель': vehicle.model.name if vehicle.model else '',
            'Тип техники': vehicle.vehicle_type.name if vehicle.vehicle_type else '',
            'Год': vehicle.year or '',
            'Цвет': vehicle.color or '',
            'Пробег, км': vehicle.mileage_km if vehicle.mileage_km is not None else '',
            'Тип двигателя': vehicle.engine_type.name if vehicle.engine_type else '',
            'Мощность, л.с.': float(vehicle.engine_power_hp) if vehicle.engine_power_hp else '',
            'Коробка передач': vehicle.transmission.name if vehicle.transmission else '',
            'Колесная формула': vehicle.wheel_formula or '',
            'Техническое состояние': vehicle.technical_condition.name if vehicle.technical_condition else '',
            'Стоимость, ₽': float(vehicle.price_rub) if vehicle.price_rub else '',
            'Статус': vehicle.get_stock_status_display() if vehicle.stock_status else '',
            'Город': vehicle.city.name if vehicle.city else '',
            'Регион': vehicle.city.region.name if vehicle.city and vehicle.city.region else '',
            'Ссылка': link,
        })

    return data


def _create_excel_file(data: List[Dict]) -> bytes:
    """
    Создает Excel файл из данных.
    """
    df = pd.DataFrame(data)

    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Техника', index=False)

        worksheet = writer.sheets['Техника']
        _format_worksheet(worksheet)

    buffer.seek(0)
    return buffer.getvalue()


def _format_worksheet(worksheet) -> None:
    """
    Форматирует колонки Excel файла.
    """
    column_widths = {
        'A': 20,  # VIN
        'B': 15,  # Марка
        'C': 20,  # Модель
        'D': 20,  # Тип техники
        'E': 8,   # Год
        'F': 15,  # Цвет
        'G': 12,  # Пробег, км
        'H': 20,  # Тип двигателя
        'I': 15,  # Мощность, л.с.
        'J': 20,  # Коробка передач
        'K': 18,  # Колесная формула
        'L': 25,  # Техническое состояние
        'M': 15,  # Стоимость, ₽
        'N': 15,  # Статус
        'O': 15,  # Город
        'P': 20,  # Регион
        'Q': 50,  # Ссылка
    }

    for col, width in column_widths.items():
        worksheet.column_dimensions[col].width = width


def get_cached_export_data(request, cache_key: str = 'vehicles_vin_export_data') -> bytes:
    """
    Получает данные из кеша или генерирует новые.
    """
    cached_data = cache.get(cache_key)

    if cached_data is None:
        excel_data = generate_vehicles_vin_excel(request)
        cache.set(cache_key, excel_data, timeout=3600)
        return excel_data

    return cached_data


def clear_export_cache(cache_key: str = 'vehicles_vin_export_data') -> None:
    """
    Очищает кеш экспорта.
    """
    cache.delete(cache_key)


def get_export_filename() -> str:
    """
    Генерирует имя файла для экспорта.
    """
    from django.utils import timezone

    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    return f"techlot_catalog_{timestamp}.xlsx"