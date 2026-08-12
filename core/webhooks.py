import logging

import requests as req
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.tasks import sync_vehicle_from_bitrix

logger = logging.getLogger(__name__)

# События товаров которые нас интересуют
TRACKED_EVENTS = {
    "CATALOG.PRODUCT.ON.ADD",
    "CATALOG.PRODUCT.ON.UPDATE",
    "ONCATALOGPRODUCTADD",
    "ONCATALOGPRODUCTUPDATE",
}

@csrf_exempt
def bitrix_catalog_webhook(request):
    """
    Единый обработчик событий от Bitrix24.

    GET  — проверка доступности URL (Bitrix делает перед подпиской)
    POST — события товаров и установка приложения
    """
    # Bitrix проверяет доступность URL через GET
    if request.method == "GET":
        return JsonResponse({"ok": True})

    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    event = request.POST.get("event", "").upper()
    logger.info("bitrix_webhook: получено событие %s", event)

    # Установка приложения
    if event == "ONAPPINSTALL":
        access_token = request.POST.get("auth[access_token]")
        domain = request.POST.get("auth[domain]")
        logger.info("bitrix_webhook: ONAPPINSTALL domain=%s", domain)
        if access_token and domain:
            _bind_catalog_events(access_token, domain)
        return JsonResponse({"ok": True})

    # События товаров
    product_id_raw = (
        request.POST.get("data[FIELDS][ID]")
        or request.POST.get("data[FIELDS][PRODUCT_ID]")
    )

    if not product_id_raw:
        logger.warning("bitrix_webhook: нет product_id в событии %s", event)
        return JsonResponse({"ok": False, "error": "no product_id"}, status=400)

    try:
        product_id = int(product_id_raw)
    except (ValueError, TypeError):
        logger.warning("bitrix_webhook: product_id не число: %s", product_id_raw)
        return JsonResponse({"ok": False, "error": "invalid product_id"}, status=400)

    if event not in TRACKED_EVENTS:
        logger.info("bitrix_webhook: событие %s не отслеживается, пропускаем", event)
        return JsonResponse({"ok": True, "skipped": True})

    # Антидубли
    dedup_key = f"bitrix_webhook:product:{product_id}"
    ttl = getattr(settings, "BITRIX_DEDUP_TTL", 10)

    if not cache.add(dedup_key, "1", timeout=ttl):
        logger.info(
            "bitrix_webhook: дубль события %s product_id=%s, пропускаем",
            event, product_id,
        )
        return JsonResponse({"ok": True, "dedup": True})

    sync_vehicle_from_bitrix.apply_async(args=[product_id], countdown=33)

    logger.info(
        "bitrix_webhook: %s product_id=%s → задача в очереди",
        event, product_id,
    )
    return JsonResponse({"ok": True})

#---------------------------------------------------------------
# Helpers
#---------------------------------------------------------------

def _bind_catalog_events(access_token: str, domain: str) -> None:
    """
    Подписывает вебхук на события каталога Bitrix24.
    
    URL обработчика берётся из настроек Django (BITRIX_WEBHOOK_HANDLER_URL).
    Токен для проверки запроса хранится в BITRIX_CATALOG_SECRET.
    """
    from django.conf import settings
    
    handler_url = getattr(
        settings, 
        "BITRIX_WEBHOOK_HANDLER_URL", 
        "https://example.com/webhooks/bitrix/catalog/"
    )
    # Добавляем секретный токен для проверки подлинности запроса
    if hasattr(settings, "BITRIX_CATALOG_SECRET") and settings.BITRIX_CATALOG_SECRET:
        handler_url = f"{handler_url}{settings.BITRIX_CATALOG_SECRET}/"
    
    old_handler_url = getattr(settings, "BITRIX_OLD_HANDLER_URL", None)

    for event in ("CATALOG.PRODUCT.ON.ADD", "CATALOG.PRODUCT.ON.UPDATE"):
        # Сначала удаляем старую подписку (если указан старый URL)
        if old_handler_url:
            try:
                resp = req.post(
                    f"https://{domain}/rest/event.unbind",
                    json={"event": event, "handler": old_handler_url, "auth": access_token},
                    timeout=getattr(settings, "BITRIX_TIMEOUT", 10),
                )
                logger.info("event.unbind %s: %s", event, resp.json())
            except Exception as e:
                logger.error("event.unbind %s: %s", event, e)

        # Создаём новую подписку
        try:
            resp = req.post(
                f"https://{domain}/rest/event.bind",
                json={"event": event, "handler": handler_url, "auth": access_token},
                timeout=getattr(settings, "BITRIX_TIMEOUT", 10),
            )
            data = resp.json()
            if data.get("result"):
                logger.info("event.bind %s: OK", event)
            else:
                logger.error("event.bind %s: %s", event, data)
        except Exception as e:
            logger.error("event.bind %s: %s", event, e)

def _get_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")