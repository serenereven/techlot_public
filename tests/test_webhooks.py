import json
from unittest.mock import patch

import pytest
from django.test import RequestFactory

from core.webhooks import bitrix_catalog_webhook


@pytest.fixture
def rf():
    return RequestFactory()


class TestBitrixCatalogWebhook:
    def test_get_returns_ok(self, rf):
        request = rf.get("/webhooks/bitrix/catalog/")
        response = bitrix_catalog_webhook(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["ok"] is True

    def test_non_post_get_returns_method_not_allowed(self, rf):
        request = rf.put("/webhooks/bitrix/catalog/")
        response = bitrix_catalog_webhook(request)
        assert response.status_code == 405

    @patch("core.webhooks.sync_vehicle_from_bitrix.apply_async")
    @patch("core.webhooks.cache.add", return_value=True)
    def test_tracked_event_enqueues_task(self, mock_cache_add, mock_apply_async, rf):
        request = rf.post(
            "/webhooks/bitrix/catalog/",
            {
                "event": "CATALOG.PRODUCT.ON.ADD",
                "data[FIELDS][ID]": "1077",
            },
        )
        response = bitrix_catalog_webhook(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["ok"] is True
        mock_apply_async.assert_called_once()
        args = mock_apply_async.call_args
        assert args[1]["args"] == [1077]

    @patch("core.webhooks.sync_vehicle_from_bitrix.apply_async")
    @patch("core.webhooks.cache.add", return_value=True)
    def test_untracked_event_skipped(self, mock_cache_add, mock_apply_async, rf):
        request = rf.post(
            "/webhooks/bitrix/catalog/",
            {
                "event": "SOME.OTHER.EVENT",
                "data[FIELDS][ID]": "1077",
            },
        )
        response = bitrix_catalog_webhook(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data.get("skipped") is True
        mock_apply_async.assert_not_called()

    @patch("core.webhooks.cache.add", return_value=True)
    def test_no_product_id_returns_400(self, mock_cache_add, rf):
        request = rf.post(
            "/webhooks/bitrix/catalog/",
            {"event": "CATALOG.PRODUCT.ON.ADD"},
        )
        response = bitrix_catalog_webhook(request)
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data["ok"] is False

    @patch("core.webhooks.cache.add", return_value=True)
    def test_non_numeric_product_id_returns_400(self, mock_cache_add, rf):
        request = rf.post(
            "/webhooks/bitrix/catalog/",
            {
                "event": "CATALOG.PRODUCT.ON.ADD",
                "data[FIELDS][ID]": "not_a_number",
            },
        )
        response = bitrix_catalog_webhook(request)
        assert response.status_code == 400

    @patch("core.webhooks.sync_vehicle_from_bitrix.apply_async")
    @patch("core.webhooks.cache.add", return_value=False)
    def test_duplicate_event_dedup(self, mock_cache_add, mock_apply_async, rf):
        request = rf.post(
            "/webhooks/bitrix/catalog/",
            {
                "event": "CATALOG.PRODUCT.ON.ADD",
                "data[FIELDS][ID]": "1077",
            },
        )
        response = bitrix_catalog_webhook(request)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data.get("dedup") is True
        mock_apply_async.assert_not_called()
