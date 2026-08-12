from django.contrib import admin, messages
from django.db import models
from django.utils import timezone
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.utils import timezone

admin.site.site_header = 'Администрирование сайта'
admin.site.site_title = 'Админ-панель'
admin.site.index_title = 'Добро пожаловать в панель управления'

# ----------------------------
# Filters
# ----------------------------

class DeletionStatusFilter(admin.SimpleListFilter):
    title = "Удаление"
    parameter_name = "deleted"

    def lookups(self, request, model_admin):
        return (
            ("alive", "Живые"),
            ("deleted", "Удалённые"),
            ("all", "Все"),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "alive":
            return queryset.filter(deleted_at__isnull=True)
        if value == "deleted":
            return queryset.filter(deleted_at__isnull=False)
        if value == "all":
            return queryset
        return queryset


# ----------------------------
# Admin Mixins
# ----------------------------

class UUIDAdminMixin:
    """Показывает UUID id как readonly (если есть поле id)."""

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if "id" in [f.name for f in self.model._meta.fields]:
            ro.append("id")
        return tuple(dict.fromkeys(ro))


class TimeStampedAdminMixin:
    """Readonly для created_at/updated_at (если они есть)."""

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        field_names = {f.name for f in self.model._meta.fields}

        if "created_at" in field_names:
            ro.append("created_at")
        if "updated_at" in field_names:
            ro.append("updated_at")

        return tuple(dict.fromkeys(ro))


class SoftDeleteAdminMixin:
    """
    - по умолчанию показывает только "живые" (НО даёт посмотреть deleted/all через фильтр)
    - стандартное "Удалить выбранные" = SOFT delete
    - actions: restore + hard delete
    """

    def get_list_filter(self, request):
        lf = list(super().get_list_filter(request))
        field_names = {f.name for f in self.model._meta.fields}
        if "deleted_at" in field_names and DeletionStatusFilter not in lf:
            lf.append(DeletionStatusFilter)
        return tuple(lf)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        field_names = {f.name for f in self.model._meta.fields}

        if "deleted_at" not in field_names:
            return qs

        # показываем живые по умолчанию, если не задан фильтр
        if "deleted" not in request.GET:
            return qs.filter(deleted_at__isnull=True)

        return qs

    # делаем дефолтное удаление (delete_selected) мягким
    def delete_model(self, request, obj):
        if hasattr(obj, "deleted_at"):
            obj.deleted_at = timezone.now()
            obj.save(update_fields=["deleted_at"])
        else:
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        model = queryset.model
        if hasattr(model, "deleted_at"):
            updated = queryset.update(deleted_at=timezone.now())
            self.message_user(request, f"Удалено (soft): {updated}", messages.SUCCESS)
        else:
            super().delete_queryset(request, queryset)

    @admin.action(description="Восстановить (restore)")
    def restore_selected(self, request, queryset):
        field_names = {f.name for f in self.model._meta.fields}
        if "deleted_at" not in field_names:
            return
        updated = queryset.update(deleted_at=None)
        self.message_user(request, f"Восстановлено: {updated}", messages.SUCCESS)

    @admin.action(description="Удалить НАВСЕГДА (hard delete)")
    def hard_delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено навсегда: {count}", messages.SUCCESS)

    def get_actions(self, request):
        actions = super().get_actions(request)

        field_names = {f.name for f in self.model._meta.fields}
        if "deleted_at" in field_names:
            actions.pop("soft_delete_selected", None)

            actions.setdefault("restore_selected", (
                self.restore_selected,
                "restore_selected",
                self.restore_selected.short_description,
            ))

        actions.setdefault("hard_delete_selected", (
            self.hard_delete_selected,
            "hard_delete_selected",
            self.hard_delete_selected.short_description,
        ))

        return actions


class PublishableAdminMixin:
    def get_list_filter(self, request):
        lf = list(super().get_list_filter(request))
        field_names = {f.name for f in self.model._meta.fields}
        if "is_published" in field_names and "is_published" not in lf:
            lf.append("is_published")
        return tuple(lf)

    @admin.action(description="Опубликовать")
    def publish_selected(self, request, queryset):
        field_names = {f.name for f in self.model._meta.fields}
        if "is_published" not in field_names:
            return

        now = timezone.now()
        if "published_at" in field_names:
            queryset.filter(published_at__isnull=True).update(published_at=now)

        updated = queryset.update(is_published=True)
        self.message_user(request, f"Опубликовано: {updated}", messages.SUCCESS)

    @admin.action(description="Снять с публикации")
    def unpublish_selected(self, request, queryset):
        field_names = {f.name for f in self.model._meta.fields}
        if "is_published" not in field_names:
            return

        updated = queryset.update(is_published=False)
        self.message_user(request, f"Снято с публикации: {updated}", messages.SUCCESS)


# ----------------------------
# Готовый Admin для FullContentModel
# ----------------------------

class FullContentAdmin(
    UUIDAdminMixin,
    TimeStampedAdminMixin,
    SoftDeleteAdminMixin,
    PublishableAdminMixin,
    admin.ModelAdmin,
):
    actions = (
        "publish_selected",
        "unpublish_selected",
        "restore_selected",
        # "soft_delete_selected",
        "delete_selected",  # и так soft
        "hard_delete_selected",
    )

    search_fields = ("title", "slug")
    list_display = ("title", "slug", "is_published", "published_at", "created_at")
    list_select_related = False
    ordering = ("-created_at",)

    formfield_overrides = {
        models.TextField: {'widget': CKEditorUploadingWidget},
    }

    prepopulated_fields = {"slug": ("title",)}

    def get_fieldsets(self, request, obj=None):
        if getattr(self, "fieldsets", None):
            return super().get_fieldsets(request, obj)

        field_names = {f.name for f in self.model._meta.fields}

        content_fields = []
        seo_fields = []
        publish_fields = []

        if "title" in field_names:
            content_fields.append("title")
        if "slug" in field_names:
            content_fields.append("slug")
        if "content" in field_names:
            content_fields.append("content")

        if "is_published" in field_names:
            publish_fields.append("is_published")
        # if "published_at" in field_names:
        #     publish_fields.append("published_at")

        for name in ("meta_title", "meta_description", "meta_keywords", "og_title", "og_description"):
            if name in field_names:
                seo_fields.append(name)

        fieldsets = []
        if content_fields:
            fieldsets.append(("Контент", {"fields": content_fields}))

        if publish_fields:
            fieldsets.append(("Публикация", {"fields": publish_fields}))

        if seo_fields:
            fieldsets.append(("SEO", {"fields": seo_fields, "classes": ("collapse",)}))

        service_fields = []
        for name in ("id", "created_at", "updated_at", "deleted_at"):
            if name in field_names:
                service_fields.append(name)

        if service_fields:
            fieldsets.append((
                "Служебное",
                {"fields": service_fields, "classes": ("collapse",)}
            ))

        return fieldsets
