# core/management/commands/sync_bitrix_vehicle.py
#
# Использование:
#   python manage.py sync_bitrix_vehicle <product_id>
#   python manage.py sync_bitrix_vehicle <product_id> --dry-run
#
# --dry-run: делает запрос к Bitrix и печатает что получилось,
#            но ничего не сохраняет в БД.

import json
from django.core.management.base import BaseCommand, CommandError
from core.services.bitrix.catalog import BitrixCatalogClient
from core.services.bitrix.mapper import map_bitrix_to_vehicle_fields, extract_photo_urls
from core.services.bitrix.sync import sync_vehicle


class Command(BaseCommand):
    help = "Синхронизирует один товар из Bitrix по его ID"

    def add_arguments(self, parser):
        parser.add_argument("product_id", type=int, help="ID товара в Bitrix")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только показать данные из Bitrix, не сохранять",
        )

    def handle(self, *args, **options):
        product_id = options["product_id"]
        dry_run = options["dry_run"]

        self.stdout.write(f"→ Запрашиваем товар {product_id} из Bitrix...")

        client = BitrixCatalogClient()

        # 1. Получаем карточку товара
        try:
            product = client.get_product(product_id)
        except Exception as e:
            raise CommandError(f"Ошибка получения товара: {e}") from e
        if not product:
            raise CommandError("Bitrix вернул пустой ответ")

        self.stdout.write("\n[RAW] Ответ catalog.product.get:")
        self.stdout.write(json.dumps(product, ensure_ascii=False, indent=2))

        # 2. Получаем цену
        price = client.get_price(product_id)
        self.stdout.write(f"\n[PRICE] {price}")

        # 3. Маппим поля
        fields = map_bitrix_to_vehicle_fields(product)
        if price is not None:
            fields["price_rub"] = price

        self.stdout.write("\n[MAPPED] Поля после маппинга:")
        for k, v in fields.items():
            self.stdout.write(f"  {k}: {v!r}")

        # 4. Фото
        photo_urls = extract_photo_urls(product) or []
        self.stdout.write(f"\n[PHOTOS] Найдено URL фото: {len(photo_urls)}")
        for url in photo_urls:
            self.stdout.write(f"  {url}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n--dry-run: в БД ничего не сохранено"))
            return

        # 5. Полная синхронизация
        self.stdout.write("\n→ Сохраняем в БД...")
        vehicle = sync_vehicle(product_id)

        if vehicle is None:
            self.stdout.write(self.style.WARNING("sync_vehicle вернул None — товар пропущен"))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Vehicle сохранён: pk={vehicle.pk}, slug={vehicle.slug}, фото={vehicle.photos.count()}"
                )
            )
