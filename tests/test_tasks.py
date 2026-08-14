from unittest.mock import patch, MagicMock
import pytest

from core.tasks import sync_vehicle_from_bitrix, sync_prices_sberleasing


class TestSyncVehicleFromBitrix:
    @patch("core.services.bitrix.sync.sync_vehicle")
    def test_successful_sync(self, mock_sync_vehicle):
        vehicle = MagicMock()
        vehicle.pk = 42
        mock_sync_vehicle.return_value = vehicle

        result = sync_vehicle_from_bitrix(1077)
        assert result == "synced:42"
        mock_sync_vehicle.assert_called_once_with(1077)


class TestSyncPricesSberleasing:
    @patch("core.tasks.sync_prices_from_feed")
    def test_returns_result_string(self, mock_sync_prices):
        mock_sync_prices.return_value = {
            "updated": 5,
            "skipped": 2,
            "errors": 0,
        }

        result = sync_prices_sberleasing()
        assert "updated=5" in result
        assert "skipped=2" in result
        assert "errors=0" in result

    @patch("core.tasks.sync_prices_from_feed")
    def test_raises_on_feed_error(self, mock_sync_prices):
        mock_sync_prices.side_effect = RuntimeError("network error")

        with pytest.raises(RuntimeError):
            sync_prices_sberleasing()
