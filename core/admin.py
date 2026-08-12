from django.contrib import admin, messages
from django.db import models, transaction
from django.utils.html import format_html
from django.shortcuts import render, redirect
from django.urls import path
from .admin_forms import VehicleImportForm
from .import_utils import import_vehicles_xlsx
from django import forms
from .models import *
from common.admin import (
    UUIDAdminMixin,
    TimeStampedAdminMixin,
    PublishableAdminMixin,
    FullContentAdmin,
)

import pandas as pd

# =========================
# Справочники
# =========================

@admin.register(Region)
class RegionAdmin(UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(City)
class CityAdmin(UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("name", "region")
    list_filter = ("region",)
    search_fields = ("name", "region__name")
    autocomplete_fields = ("region",)
    ordering = ("name",)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "maps_code":
            kwargs["widget"] = forms.Textarea
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(Brand)
class BrandAdmin(UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(VehicleModel)
class VehicleModelAdmin(UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("name", "brand")
    list_filter = ("brand",)
    search_fields = ("name", "brand__name")
    autocomplete_fields = ("brand",)
    ordering = ("brand__name", "name")

@admin.register(EngineType)
class EngineTypeAdmin(UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Transmission)
class TransmissionAdmin(UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(TechnicalCondition)
class TechnicalConditionAdmin(UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(VehicleType)
class VehicleTypeAdmin(UUIDAdminMixin, admin.ModelAdmin):
    list_display = ("name", "order")
    list_editable = ("order",)
    search_fields = ("name",)
    ordering = ("order",)

class VehiclePhotoInline(admin.TabularInline):
    model = VehiclePhoto
    extra = 1
    fields = ("image", "is_main", "sort_order", "caption")
    ordering = ("sort_order", "id")

# =========================
# Каталог (FullContentModel)
# =========================

@admin.register(Vehicle)
class VehicleAdmin(FullContentAdmin):
    inlines = [VehiclePhotoInline]
    list_display = ("title", "vin", "price_rub", "is_published", "to_homepage", "created_at")
    change_list_template = "admin/vehicle_changelist.html"
    list_editable = ("is_published", "to_homepage")
    autocomplete_fields = ("city", "vehicle_type", "brand", "model", "engine_type", "transmission", "technical_condition")
    search_fields = ("title", "vin", "id")
    fieldsets = (
        ("Контент", {"fields": ("title", "slug", "content")}),
        ("Публикация", {"fields": ("is_published", "to_homepage")}),
        ("Локация", {"fields": ("city",)}),
        ("Классификация", {"fields": ("vehicle_type", "brand", "model", "stock_status")}),
        ("Техническое", {"fields": (
            "year", "vin", "mileage_km",
            "engine_type", "engine_power_hp",
            "transmission", "wheel_formula",
            "technical_condition", "color"
        )}),
        ("Цена", {"fields": ("price_rub",)}),
        (
            "SEO",  
            {
                "fields": ("meta_title", "meta_description", "meta_keywords", "og_title", "og_description"),
                "classes": ("collapse",),
            },
        ),
        (
            "Служебное",
            {
                "fields": ("id", "created_at", "updated_at", "deleted_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-xlsx/",
                self.admin_site.admin_view(self.import_xlsx),
                name="vehicle_import_xlsx",
            )
        ]
        return custom_urls + urls
        
    def import_xlsx(self, request):
        if request.method == "POST":
            form = VehicleImportForm(request.POST, request.FILES)
            if form.is_valid():
                dry_run = form.cleaned_data["dry_run"]
                publish = form.cleaned_data["publish"]

                result = import_vehicles_xlsx(
                    file=form.cleaned_data["file"],
                    dry_run=dry_run,
                    publish=publish,
                    user_id=request.user.id,
                    Region=Region,
                    City=City,
                    Brand=Brand,
                    VehicleModel=VehicleModel,
                    VehicleType=VehicleType,
                    Vehicle=Vehicle,
                    StockStatus=StockStatus,
                    EngineType=EngineType,
                    Transmission=Transmission,
                    TechnicalCondition=TechnicalCondition,
                )

                created = result["created"]
                updated = result["updated"]
                skipped = result["skipped"]

                if dry_run:
                    self.message_user(
                        request,
                        f"DRY-RUN: будет создано {created}, обновлено {updated}, пропущено {skipped}",
                        messages.WARNING,
                    )
                else:
                    self.message_user(
                        request,
                        f"Импорт завершён: создано {created}, обновлено {updated}, пропущено {skipped}",
                        messages.SUCCESS,
                    )

                return render(
                    request,
                    "admin/import_xlsx_result.html",
                    {
                        "title": "Результат импорта",
                        "preview": result["preview"],
                        "dry_run": dry_run,
                    },
                )
        else:
            form = VehicleImportForm()

        return render(
            request,
            "admin/import_xlsx.html",
            {
                "form": form,
                "title": "Импорт техники",
            },
        )


# =========================
# Заявки
# =========================

@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(UUIDAdminMixin, TimeStampedAdminMixin, admin.ModelAdmin):
    list_display = ("created_at", "source", "name", "phone", "vehicle")
    list_filter = ("source", "created_at")
    search_fields = ("name", "phone", "vehicle__title", "vehicle__vin")
    autocomplete_fields = ("vehicle",)
    ordering = ("-created_at",)


# =========================
# Контакты
# =========================

@admin.register(Contact)
class ContactAdmin(UUIDAdminMixin, TimeStampedAdminMixin, PublishableAdminMixin, admin.ModelAdmin):
    list_display = (
        "sort_order",
        "title",
        "contact_type",
        "value",
        "is_published",
        "created_at",
    )

    list_display_links = ("title",)
    list_editable = ("sort_order",)

    list_filter = ("contact_type",)
    search_fields = ("title", "value")
    ordering = ("sort_order", "title")

    readonly_fields = ("id", "created_at", "updated_at", "published_at")

    fieldsets = (
        ("Контакт", {"fields": ("title", "contact_type", "value", "sort_order")}),
        ("Публикация", {"fields": ("is_published",)}),
        (
            "Служебное",
            {
                "fields": ("id", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


# =========================
# Простые страницы (FullContentModel)
# =========================

@admin.register(BasicPage)
class BasicPageAdmin(FullContentAdmin):
    list_display = ("title", "is_navbar", "is_published", "created_at")
    list_filter = ("is_navbar",)
    ordering = ("title",)

    fieldsets = (
        ("Контент", {"fields": ("title", "slug", "content")}),
        ("Публикация", {"fields": ("is_published","is_navbar")}),
        (
            "SEO",
            {
                "fields": ("meta_title", "meta_description", "meta_keywords", "og_title", "og_description"),
                "classes": ("collapse",),
            },
        ),
        (
            "Служебное",
            {
                "fields": ("id", "created_at", "updated_at", "deleted_at"),
                "classes": ("collapse",),
            },
        ),
    )