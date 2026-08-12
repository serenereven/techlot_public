from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import requests
from django.conf import settings

from .client import BitrixClient
from .exceptions import BitrixRequestError

logger = logging.getLogger(__name__)


class BitrixCatalogClient(BitrixClient):
    """
    Расширение базового клиента методами каталога товаров.
    Использует BITRIX_CATALOG_WEBHOOK_URL из settings.
    """

    def __init__(self):
        self.base_url = settings.BITRIX_CATALOG_WEBHOOK_URL
        self.timeout = getattr(settings, "BITRIX_TIMEOUT", 15)

    # Товар
    def get_product(self, product_id: int) -> dict[str, Any]:
        """
        Возвращает полную карточку товара включая все свойства (property*).
        Bitrix отдаёт: {"result": {"element": {...}}}
        """
        data = self.call("catalog.product.get", {"id": product_id})
        result = data.get("result", {})
        # Bitrix возвращает товар в "product" (catalog.product.get)
        return result.get("product") or result.get("element") or {}

    # Цена
    def get_price(self, product_id: int) -> Decimal | None:
        """
        Получает цену товара через catalog.price.list.
        Возвращает Decimal или None если цены нет.
        """
        try:
            data = self.call(
                "catalog.price.list",
                {"filter": {"productId": product_id}},
            )
            prices = data.get("result", {}).get("prices", [])
            if not prices:
                return None
            raw = prices[0].get("price")
            return Decimal(str(raw)) if raw is not None else None
        except Exception as e:
            logger.error("get_price product_id=%s: %s", product_id, e)
            return None

    # Фото
    def download_photo(self, url_machine: str) -> bytes | None:
        """
        Скачивает фото по urlMachine из property45.
        urlMachine уже содержит подписанный URL — просто GET-запрос.
        """
        try:
            response = requests.get(url_machine, timeout=self.timeout)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            logger.error("download_photo %s: %s", url_machine, e)
            return None

    def get_property_enums(self, property_id: int) -> dict[str, str]:
        """
        Возвращает маппинг {id → value} для списочного свойства.
        Обходит пагинацию Bitrix (по 50 записей).
        """
        result = {}
        start = 0
        while True:
            try:
                data = self.call(
                    "catalog.productPropertyEnum.list",
                    {"filter": {"propertyId": property_id}, "start": start},
                )
            except Exception as e:
                logger.error("get_property_enums property_id=%s start=%s: %s", property_id, start, e)
                break

            items = data.get("result", {}).get("productPropertyEnums", [])
            for item in items:
                if "id" in item and "value" in item:
                    result[str(item["id"])] = item["value"]

            next_start = data.get("next")
            if not next_start:
                break
            start = next_start

        logger.info("get_property_enums property_id=%s: загружено %d значений", property_id, len(result))
        return result

    def get_first_offer(self, product_id: int) -> dict | None:
        """Возвращает первую вариацию основного товара."""
        try:
            data = self.call(
                "catalog.product.offer.list",
                {
                    "filter": {"parentId": product_id},
                    "select": ["*"],
                    "limit": 1,
                },
            )
            offers = data.get("result", {}).get("offers", [])
            return offers[0] if offers else None
        except Exception as e:
            logger.error("get_first_offer %s: %s", product_id, e)
            return None