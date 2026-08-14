import re
import django_filters
from django import forms
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Vehicle, Brand, VehicleModel, City, VehicleType, StockStatus
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank


def get_clean_queryset(model_class):
    cache_key = f"clean_queryset_{model_class.__name__}"
    valid_ids = cache.get(cache_key)

    if valid_ids is None:
        pattern = re.compile(r"^[a-zA-Z0-9а-яА-ЯёЁ\s]+$")
        valid_ids = [obj_id for obj_id, name in model_class.objects.values_list("id", "name") if pattern.match(name)]
        cache.set(cache_key, valid_ids, timeout=3600)

    return model_class.objects.filter(id__in=valid_ids)


def get_available_vehicle_types():
    """
    Типы техники, для которых есть хотя бы одна опубликованная карточка.
    Кэш на 5 минут, без инвалидации по сигналам — обновление с небольшой задержкой.
    """
    cache_key = "available_vehicle_types"
    ids = cache.get(cache_key)

    if ids is None:
        ids = list(
            Vehicle.published.alive()
            .order_by("-to_homepage", "-created_at")
            .filter(vehicle_type__isnull=False)
            .values_list("vehicle_type_id", flat=True)
            .distinct()
        )
        cache.set(cache_key, ids, timeout=300)

    return VehicleType.objects.filter(id__in=ids).order_by("order")


@receiver([post_save, post_delete], sender=Brand)
def invalidate_brand_cache(sender, **kwargs):
    cache.delete("clean_queryset_Brand")


@receiver([post_save, post_delete], sender=VehicleModel)
def invalidate_vehicle_model_cache(sender, **kwargs):
    cache.delete("clean_queryset_VehicleModel")


class VehicleFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filter_search", label="Поиск")

    brand = django_filters.ModelMultipleChoiceFilter(
        field_name="brand",
        queryset=lambda request: get_clean_queryset(Brand),
        conjoined=False,
    )
    model = django_filters.ModelMultipleChoiceFilter(
        field_name="model",
        queryset=lambda request: get_clean_queryset(VehicleModel),
        conjoined=False,
    )
    city = django_filters.ModelChoiceFilter(
        field_name="city",
        queryset=City.objects.all(),
    )
    year_min = django_filters.NumberFilter(field_name="year", lookup_expr="gte", label="Год от")
    year_max = django_filters.NumberFilter(field_name="year", lookup_expr="lte", label="Год до")
    price_min = django_filters.NumberFilter(field_name="price_rub", lookup_expr="gte", label="Цена от")
    price_max = django_filters.NumberFilter(field_name="price_rub", lookup_expr="lte", label="Цена до")

    stock_status = django_filters.MultipleChoiceFilter(
        field_name="stock_status",
        choices=StockStatus.choices,
        label="Наличие",
        conjoined=False,
    )

    vehicle_type = django_filters.ModelMultipleChoiceFilter(
        field_name="vehicle_type",
        queryset=lambda request: get_available_vehicle_types(),
        widget=forms.CheckboxSelectMultiple,
    )

    SORT_CHOICES = (
        ("-created_at", "Сначала новые"),
        ("created_at", "Сначала старые"),
        ("price_rub", "По цене (подешевле)"),
        ("-price_rub", "По цене (подороже)"),
    )

    sort = django_filters.ChoiceFilter(
        choices=SORT_CHOICES,
        method="filter_sort",
        label="Сортировка",
        empty_label=None,
    )

    def filter_search(self, queryset, name, value):
        if not value or not value.strip():
            return queryset

        vector = (
            SearchVector("title", weight="A", config="russian")
            + SearchVector("content", weight="B", config="russian")
            + SearchVector("brand__name", weight="A", config="russian")
            + SearchVector("model__name", weight="A", config="russian")
            + SearchVector("city__name", weight="A", config="russian")
            + SearchVector("vin", weight="A", config="simple")
        )
        query = SearchQuery(value.strip(), config="russian", search_type="websearch")
        return queryset.annotate(rank=SearchRank(vector, query)).filter(rank__gt=0).order_by("-rank")

    def filter_sort(self, queryset, name, value):
        allowed = {c[0] for c in self.SORT_CHOICES}
        if value in allowed:
            return queryset.order_by(value)
        return queryset

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.form.fields.values():
            if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.update({"class": "uk-select"})
            elif isinstance(field.widget, (forms.NumberInput, forms.TextInput)):
                field.widget.attrs.update(
                    {
                        "class": "uk-input uk-border-rounded",
                        "placeholder": field.label,
                    }
                )

    class Meta:
        model = Vehicle
        fields = ["vehicle_type", "brand", "model", "city", "stock_status", "sort"]
