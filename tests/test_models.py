import pytest
from django.core.exceptions import ValidationError

from core.models import Contact, ContactType


class TestContactFormatPhone:
    def test_format_phone_russian(self):
        result = Contact._format_phone("+7 999 123-45-67")
        assert result == "8 999-123-45-67"

    def test_format_phone_without_plus(self):
        result = Contact._format_phone("89991234567")
        assert result == "8 999-123-45-67"

    def test_format_phone_wrong_length_unchanged(self):
        raw = "123"
        assert Contact._format_phone(raw) == raw


class TestContactLink:
    def test_phone_link(self):
        contact = Contact(title="Тест", contact_type=ContactType.PHONE, value="+79991234567")
        assert contact.link.startswith("tel:")

    def test_email_link(self):
        contact = Contact(title="Тест", contact_type=ContactType.EMAIL, value="test@example.com")
        assert contact.link == "mailto:test@example.com"

    def test_other_link_returns_value(self):
        contact = Contact(title="Тест", contact_type=ContactType.TELEGRAM, value="@username")
        assert contact.link == "@username"

    def test_empty_link(self):
        contact = Contact(title="Тест", contact_type=ContactType.PHONE, value="")
        assert contact.link == ""


class TestPurchaseRequestClean:
    def test_leasing_requires_inn(self):
        from core.models import PurchaseRequest, RequestType

        pr = PurchaseRequest(name="Тест", phone="+79991234567", request_type=RequestType.LEASING)
        with pytest.raises(ValidationError) as exc_info:
            pr.clean()
        assert "inn" in exc_info.value.message_dict

    def test_leasing_inn_format_invalid(self):
        from core.models import PurchaseRequest, RequestType

        pr = PurchaseRequest(
            name="Тест",
            phone="+79991234567",
            request_type=RequestType.LEASING,
            inn="123",
        )
        with pytest.raises(ValidationError) as exc_info:
            pr.clean()
        assert "inn" in exc_info.value.message_dict

    def test_purchase_no_inn_required(self):
        from core.models import PurchaseRequest, RequestType

        pr = PurchaseRequest(name="Тест", phone="+79991234567", request_type=RequestType.PURCHASE)
        # Не должно выбрасывать исключение
        pr.clean()
