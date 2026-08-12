import re
from django.core.exceptions import ValidationError
from django.db import models


def _extract_digits(value: str) -> str:
    """Оставляет только цифры."""
    return re.sub(r"\D", "", value or "")


def _normalize_phone(digits: str) -> str:
    """
    Приводит к формату +7XXXXXXXXXX.
    Принимает 8XXXXXXXXXX или 7XXXXXXXXXX (11 цифр).
    """
    if digits.startswith("8") or digits.startswith("7"):
        digits = "7" + digits[1:]
    return "+" + digits


def validate_phone(value: str):
    digits = _extract_digits(value)
    if len(digits) != 11 or digits[0] not in ("7", "8"):
        raise ValidationError(
            "Введите российский номер телефона (11 цифр, начиная с 7 или 8)."
        )


class NormalizedEmailField(models.EmailField):
    """EmailField со strip + lower перед сохранением."""

    def to_python(self, value):
        value = super().to_python(value)
        if isinstance(value, str):
            value = value.strip().lower()
        return value


class PhoneField(models.CharField):
    """
    Телефон с нормализацией и валидацией.
    Принимает любой формат (маска фронта, вставка, ручной ввод),
    хранит всегда в виде 8 888-888-88-88.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 15)

        validators = list(kwargs.get("validators", []))
        validators.append(validate_phone)
        kwargs["validators"] = validators

        super().__init__(*args, **kwargs)

    def to_python(self, value):
        value = super().to_python(value)
        if not isinstance(value, str):
            return value
        digits = _extract_digits(value)
        if not digits:
            return value  # пусть валидатор разбирается
        return _normalize_phone(digits)