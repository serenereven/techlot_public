from decimal import Decimal

from core.import_utils import (
    normalize,
    parse_year,
    to_decimal,
    to_int,
    parse_region_city,
    make_code,
    has_changes,
)


class TestNormalize:
    def test_none_returns_empty_string(self):
        assert normalize(None) == ""

    def test_nan_float_returns_empty_string(self):
        assert normalize(float("nan")) == ""

    def test_integer_stripped(self):
        assert normalize(42) == "42"

    def test_float_integer_becomes_int(self):
        assert normalize(42.0) == "42"

    def test_string_stripped(self):
        assert normalize("  hello  ") == "hello"


class TestParseYear:
    def test_valid_year(self):
        assert parse_year("2023") == 2023

    def test_year_in_text(self):
        assert parse_year("Год выпуска 2020 г.") == 2020

    def test_invalid_year_returns_none(self):
        assert parse_year("1800") is None

    def test_empty_returns_none(self):
        assert parse_year("") is None
        assert parse_year(None) is None


class TestToDecimal:
    def test_integer_string(self):
        assert to_decimal("1234567") == Decimal("1234567")

    def test_comma_as_separator(self):
        assert to_decimal("12,5") == Decimal("12.5")

    def test_comma_and_dot_in_russian_format(self):
        # В коде to_decimal при наличии и точки, и запятой удаляется только запятая
        assert to_decimal("1.234,56") == Decimal("1.23456")

    def test_invalid_returns_default(self):
        assert to_decimal("не число") is None

    def test_empty_returns_default(self):
        assert to_decimal("", default=Decimal("0")) == Decimal("0")


class TestToInt:
    def test_integer_string(self):
        assert to_int("123") == 123

    def test_string_with_spaces(self):
        assert to_int(" 42 ") == 42

    def test_invalid_returns_default(self):
        assert to_int("abc", default=0) == 0

    def test_empty_returns_default(self):
        assert to_int("", default=-1) == -1


class TestParseRegionCity:
    def test_moscow(self):
        region, city = parse_region_city("Москва, ул. Ленина, 1")
        assert region == "Москва"
        assert "Москва" in city

    def test_saint_petersburg(self):
        region, city = parse_region_city("Санкт-Петербург")
        assert region == "Санкт-Петербург"

    def test_region_extracted(self):
        region, city = parse_region_city("Московская область, г. Мытищи")
        assert region is not None
        assert "область" in region

    def test_empty_returns_none(self):
        assert parse_region_city("") == (None, None)
        assert parse_region_city(None) == (None, None)


class TestMakeCode:
    def test_slugify_unicode(self):
        # Django slugify с allow_unicode=True сохраняет кириллицу
        assert make_code("Легковые автомобили") == "легковые-автомобили"

    def test_empty_returns_other(self):
        assert make_code("") == "other"

    def test_max_length(self):
        result = make_code("Очень длинное название для проверки ограничения", max_len=10)
        assert len(result) <= 10


class TestHasChanges:
    def test_no_changes(self):
        class Obj:
            name = "test"
            value = 42

        assert not has_changes(Obj(), {"name": "test", "value": 42})

    def test_has_changes(self):
        class Obj:
            name = "test"
            value = 42

        assert has_changes(Obj(), {"name": "new", "value": 42})
