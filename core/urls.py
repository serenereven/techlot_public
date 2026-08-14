from django.urls import path
from django.conf import settings
from .views import (
    IndexView,
    VehicleListView,
    VehicleAjaxListView,
    VehicleDetailView,
    BasicPageDetailView,
    AboutPageDetailView,
    api_brands,
    api_models,
    api_cities,
    purchase_request_ajax,
    export_vehicles_vin_excel,
)
from .webhooks import bitrix_catalog_webhook

bitrix_token = settings.BITRIX_INCOMING_TOKEN
app_name = "core"

urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path("catalog/", VehicleListView.as_view(), name="catalog"),
    path("catalog/ajax/", VehicleAjaxListView.as_view(), name="catalog_ajax"),
    path("catalog/<slug:slug>/", VehicleDetailView.as_view(), name="vehicle_detail"),
    path("ajax/purchase-request/", purchase_request_ajax, name="purchase_request_ajax"),
    path("about/", AboutPageDetailView.as_view(), name="about_page"),
    path("<slug:slug>/", BasicPageDetailView.as_view(), name="basic_page"),
    path("api/brands/", api_brands, name="api_brands"),
    path("api/models/", api_models, name="api_models"),
    path("api/cities/", api_cities, name="api_cities"),
    path("export/vehicles-vin-excel/", export_vehicles_vin_excel, name="export_vehicles_vin_excel"),
    path(
        "webhooks/bitrix/catalog/e608dd3fdbee717ca984a5f222eaddba/",
        bitrix_catalog_webhook,
        name="bitrix_catalog_webhook",
    ),
    path("webhooks/bitrix/catalog/", bitrix_catalog_webhook, name="bitrix_catalog_webhook_no_token"),
    path("webhooks/bitrix/catalog//", bitrix_catalog_webhook, name="bitrix_catalog_webhook_no_token_2"),
]
