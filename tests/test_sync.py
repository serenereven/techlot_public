from decimal import Decimal
from unittest.mock import patch, MagicMock
import pytest
from tests.fixtures.bitrix_product_1077 import PRODUCT_1077, PRICE_1077, BRAND_ENUMS
from core.services.bitrix.sync import sync_vehicle


def make_client():
    client = MagicMock()
    client.get_product.return_value = PRODUCT_1077
    client.get_price.return_value = Decimal(PRICE_1077)
    client.get_property_enums.return_value = BRAND_ENUMS
    client.download_photo.return_value = None
    return client


@pytest.mark.django_db
class TestSyncVehicle:
    @patch("core.services.bitrix.sync.LogEntry.objects.log_action")
    @patch("core.services.bitrix.sync.BitrixCatalogClient")
    def test_creates_vehicle(self, MockClient, mock_log_action):
        MockClient.return_value = make_client()
        vehicle = sync_vehicle(1077)
        assert vehicle is not None
        assert vehicle.vin == "LGWFF7A57RJ648638"
        assert vehicle.price_rub == Decimal("3647000")
        assert vehicle.mileage_km == 30088
        assert vehicle.color == "Белый"
        assert vehicle.stock_status == "in_stock"

    @patch("core.services.bitrix.sync.LogEntry.objects.log_action")
    @patch("core.services.bitrix.sync.BitrixCatalogClient")
    def test_brand_resolved(self, MockClient, mock_log_action):
        MockClient.return_value = make_client()
        vehicle = sync_vehicle(1077)
        assert vehicle.brand is not None
        assert vehicle.brand.name == "GWM"

    @patch("core.services.bitrix.sync.LogEntry.objects.log_action")
    @patch("core.services.bitrix.sync.BitrixCatalogClient")
    def test_upsert_no_duplicate(self, MockClient, mock_log_action):
        MockClient.return_value = make_client()
        v1 = sync_vehicle(1077)
        MockClient.return_value = make_client()
        v2 = sync_vehicle(1077)
        assert v1.pk == v2.pk

    @patch("core.services.bitrix.sync.LogEntry.objects.log_action")
    @patch("core.services.bitrix.sync.BitrixCatalogClient")
    def test_returns_none_on_error(self, MockClient, mock_log_action):
        from core.services.bitrix.exceptions import BitrixError

        client = make_client()
        client.get_product.side_effect = BitrixError("timeout")
        MockClient.return_value = client
        assert sync_vehicle(1077) is None
