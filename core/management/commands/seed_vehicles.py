import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    Region,
    City,
    Brand,
    VehicleModel,
    Vehicle,
    VehicleType,
    EngineType,
    TransmissionType,
    TechnicalCondition,
    StockStatus,
)


class Command(BaseCommand):
    help = "Seed 10 test vehicles and related dictionaries."

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)

        # =========================
        # Регионы и города
        # =========================
        regions_data = {
            "Московская область": ["Москва", "Химки", "Подольск"],
            "Ленинградская область": ["Санкт-Петербург", "Всеволожск"],
        }

        cities: list[City] = []

        for region_name, city_names in regions_data.items():
            region, _ = Region.objects.get_or_create(name=region_name)

            for city_name in city_names:
                city, _ = City.objects.get_or_create(region=region, name=city_name)
                cities.append(city)

        # =========================
        # Бренды и модели
        # =========================
        brands_models = {
            "КАМАЗ": ["65115", "5490"],
            "MAN": ["TGX", "TGS"],
            "Volvo": ["FH", "FMX"],
            "Scania": ["R500", "G450"],
            "Mercedes-Benz": ["Actros", "Arocs"],
        }

        vehicle_models: list[VehicleModel] = []

        for brand_name, models_list in brands_models.items():
            brand, _ = Brand.objects.get_or_create(name=brand_name)

            for model_name in models_list:
                vm, _ = VehicleModel.objects.get_or_create(brand=brand, name=model_name)
                vehicle_models.append(vm)

        # =========================
        # Варианты для генерации
        # =========================
        vehicle_types = [
            VehicleType.TRUCK,
            VehicleType.TRAILER,
            VehicleType.SEMI_TRAILER,
            VehicleType.SPECIAL,
            VehicleType.OTHER,
        ]

        engine_types = [
            EngineType.DIESEL,
            EngineType.PETROL,
            EngineType.GAS,
            EngineType.ELECTRIC,
            EngineType.HYBRID,
            EngineType.OTHER,
        ]

        transmissions = [
            TransmissionType.MANUAL,
            TransmissionType.AUTOMATIC,
            TransmissionType.ROBOT,
            TransmissionType.CVT,
            TransmissionType.OTHER,
        ]

        conditions = [
            TechnicalCondition.EXCELLENT,
            TechnicalCondition.GOOD,
            TechnicalCondition.OK,
            TechnicalCondition.NEEDS_REPAIR,
        ]

        stock_statuses = [
            StockStatus.IN_STOCK,
            StockStatus.RESERVED,
            StockStatus.SOLD,
        ]

        wheel_formulas = ["4x2", "6x4", "6x6", "8x4"]
        colors = ["Белый", "Серый", "Синий", "Красный", "Черный"]

        # =========================
        # Создаём 10 автомобилей
        # =========================
        created = 0

        for i in range(1, 11):
            city = random.choice(cities)

            vm = random.choice(vehicle_models)
            brand = vm.brand

            year = random.randint(2008, 2024)
            mileage = random.randint(5_000, 950_000)
            price = random.randint(900_000, 12_000_000)

            title = f"{brand.name} {vm.name} ({year})"

            # VIN иногда пустой (у тебя уникальность только когда vin != "")
            vin = f"TESTVIN{i:02d}{random.randint(100000, 999999)}" if random.random() < 0.7 else ""

            obj = Vehicle(
                # FullContentModel
                title=title,
                content=(
                    f"Тестовый автомобиль №{i}. "
                    f"Пробег: {mileage} км. "
                    f"Год: {year}. "
                    f"Состояние: {random.choice(conditions).label}."
                ),

                # Локация
                city=city,

                # Тип техники
                vehicle_type=random.choice(vehicle_types),

                # Справочники
                brand=brand,
                model=vm,

                # Техническое
                engine_type=random.choice(engine_types),
                vin=vin,
                mileage_km=mileage,
                transmission=random.choice(transmissions),
                year=year,
                technical_condition=random.choice(conditions),
                color=random.choice(colors),
                engine_power_hp=random.choice([None, 150, 200, 240, 310, 420, 500]),
                wheel_formula=random.choice(wheel_formulas),

                # Цена и наличие
                price_rub=Decimal(price),
                stock_status=random.choice(stock_statuses),

                # Фото пропускаем (main_photo=None по умолчанию)
            )

            # slug заполнять НЕ надо -> у тебя SluggedModel сам сделает уникальный slug
            # SEO поля тоже сами проставятся на save()

            # Публикация: корректно через метод publish()
            obj.publish(commit=False)
            obj.save()

            created += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Seed complete: created {created} vehicles"))
        self.stdout.write(self.style.SUCCESS(f"Regions: {Region.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Cities: {City.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Brands: {Brand.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Vehicle models: {VehicleModel.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Vehicles: {Vehicle.objects.count()}"))