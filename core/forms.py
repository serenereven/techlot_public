from django import forms
from .models import PurchaseRequest, RequestType
from .models import VehicleType, Brand, VehicleModel, City, StockStatus
import re


class PurchaseRequestForm(forms.ModelForm):

    class Meta:
        model = PurchaseRequest
        fields = [
            "name",
            "phone",
            "inn",
            "request_type",
        ]
        widgets = {
            "request_type": forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = super().clean()

        request_type = cleaned_data.get("request_type")
        inn = cleaned_data.get("inn")

        if request_type == RequestType.LEASING:
            if not inn:
                self.add_error("inn", "ИНН обязателен для лизинга")
            elif not re.fullmatch(r"\d{10}|\d{12}", inn):
                self.add_error("inn", "ИНН должен содержать 10 или 12 цифр")

        return cleaned_data


class VehicleFilterForm(forms.Form):
    vehicle_type = forms.ModelChoiceField(
        queryset=VehicleType.objects.all().order_by("name"),
        required=False,
        empty_label="Тип техники",
        widget=forms.Select(attrs={"class": "uk-select"}),
    )

    brand = forms.MultipleChoiceField(required=False, choices=[])
    model = forms.MultipleChoiceField(required=False, choices=[])
    city = forms.UUIDField(required=False)

    year_min = forms.IntegerField(
        required=False, min_value=1900,
        widget=forms.NumberInput(attrs={"class": "uk-input", "placeholder": "Год от"})
    )
    year_max = forms.IntegerField(
        required=False, min_value=1900,
        widget=forms.NumberInput(attrs={"class": "uk-input", "placeholder": "Год до"})
    )

    price_min = forms.IntegerField(
        required=False, min_value=0,
        widget=forms.NumberInput(attrs={"class": "uk-input", "placeholder": "Цена от, ₽"})
    )
    price_max = forms.IntegerField(
        required=False, min_value=0,
        widget=forms.NumberInput(attrs={"class": "uk-input", "placeholder": "Цена до, ₽"})
    )

    status = forms.ChoiceField(
        required=False,
        choices=[("", "Статус")] + list(StockStatus.choices),
        widget=forms.Select(attrs={"class": "uk-select"}),
    )

    def clean(self):
        cleaned = super().clean()
        y1, y2 = cleaned.get("year_min"), cleaned.get("year_max")
        if y1 and y2 and y1 > y2:
            cleaned["year_min"], cleaned["year_max"] = y2, y1

        p1, p2 = cleaned.get("price_min"), cleaned.get("price_max")
        if p1 and p2 and p1 > p2:
            cleaned["price_min"], cleaned["price_max"] = p2, p1
        return cleaned