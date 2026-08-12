from unittest.mock import patch, MagicMock
from tests.fixtures.bitrix_product_1077 import PRODUCT_1077
from core.services.bitrix.mapper import map_bitrix_to_vehicle_fields, extract_photo_urls


def make_mock_obj(name):
    obj = MagicMock()
    obj.name = name
    return obj


def mock_get_or_create(model_class, **kwargs):
    return make_mock_obj(kwargs.get("name", ""))


def patched_fields(brand_enums=None):
    """Вызывает маппер с замоканными всеми обращениями к БД."""
    mock_region = make_mock_obj("Не указан")
    with patch("core.services.bitrix.mapper._get_or_create", side_effect=mock_get_or_create), \
         patch("core.models.Region.objects.get_or_create", return_value=(mock_region, True)):
        return map_bitrix_to_vehicle_fields(PRODUCT_1077, brand_enums=brand_enums)


class TestMapBitrixToVehicleFields:

    def test_vin(self):
        assert patched_fields()["vin"] == "LGWFF7A57RJ648638"

    def test_mileage(self):
        assert patched_fields()["mileage_km"] == 30088

    def test_color(self):
        assert patched_fields()["color"] == "Белый"

    def test_stock_status(self):
        assert patched_fields()["stock_status"] == "in_stock"

    def test_is_published(self):
        assert patched_fields()["is_published"] is True

    def test_technical_condition(self):
        assert patched_fields()["technical_condition"].name == "Хорошее"

    def test_vehicle_type(self):
        assert patched_fields()["vehicle_type"].name == "Легковые"

    def test_brand_null_valueEnum_returns_none(self):
        # без справочника бренд должен быть None
        assert patched_fields()["brand"] is None

    def test_year(self):
        assert patched_fields()["year"] == 2023

    def test_model_created_from_string(self):
        fields = patched_fields(brand_enums={"207": "GWM"})
        assert fields["model"] is not None
        assert fields["model"].name == "GWM TANK 300"

    def test_brand_resolved_from_enums(self):
        assert patched_fields(brand_enums={"207": "GWM"})["brand"].name == "GWM"

    def test_no_photos(self):
        assert extract_photo_urls(PRODUCT_1077) == []

    def test_photos_parsed(self):
        product = {
            **PRODUCT_1077,
            "property45": [
                {"value": {"urlMachine": "https://cdn.example.com/photo1.jpg"}},
                {"value": {"urlMachine": "https://cdn.example.com/photo2.jpg"}},
            ]
        }
        assert extract_photo_urls(product) == [
            "https://cdn.example.com/photo1.jpg",
            "https://cdn.example.com/photo2.jpg",
        ]