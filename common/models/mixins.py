from __future__ import annotations

import uuid

from django.db import models
from django.db.models import UniqueConstraint
from django.utils import timezone
from django.utils.text import slugify
from django.utils.html import strip_tags

from .managers import (
    PublishedManager,
    DraftsManager,
    SoftDeleteAllManager,
    SoftDeleteAliveManager,
    SoftDeleteDeletedManager,
)


class UUIDPrimaryKeyModel(models.Model):
    """
    UUID как primary key
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Soft delete вместо реального удаления:
    - delete() ставит deleted_at
    - hard_delete() реально удаляет
    - restore() восстанавливает

    Менеджеры:
    - objects: все (включая удаленные)
    - alive: только не удаленные
    - deleted: только удаленные
    """
    deleted_at = models.DateTimeField("Удалено", blank=True, null=True, db_index=True)

    objects = SoftDeleteAllManager()
    alive = SoftDeleteAliveManager()
    deleted = SoftDeleteDeletedManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])


class PublishableModel(models.Model):
    """
    Публикация + менеджеры:
    - objects: всё
    - published: только опубликованные
    - drafts: только черновики
    """
    is_published = models.BooleanField("Опубликовано", default=False)
    published_at = models.DateTimeField(
        "Дата публикации", blank=True, null=True, db_index=True
    )

    objects = models.Manager()
    published = PublishedManager()
    drafts = DraftsManager()

    class Meta:
        abstract = True

    def publish(self, commit: bool = True):
        self.is_published = True
        if not self.published_at:
            self.published_at = timezone.now()

        if commit:
            self.save(update_fields=["is_published", "published_at"])

    def unpublish(self, commit: bool = True):
        self.is_published = False
        if commit:
            self.save(update_fields=["is_published"])


class SluggedModel(models.Model):
    """
    Production-ready slug:
    - slug индексированный
    - уникальность через DB constraint
    - slug, slug-2, slug-3...
    """
    slug = models.SlugField("Slug", max_length=255, blank=True, db_index=True, unique=True)

    class Meta:
        abstract = True
        constraints = [
            UniqueConstraint(fields=["slug"], name="%(app_label)s_%(class)s_slug_uniq"),
        ]

    def get_slug_source(self) -> str:
        return getattr(self, "title", "") or ""

    def _slug_queryset(self):
        return self.__class__.objects.all()

    def generate_unique_slug(self) -> str:
        base = slugify(self.get_slug_source()) or "item"
        slug = base

        qs = self._slug_queryset()
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        i = 2
        while qs.filter(slug=slug).exists():
            slug = f"{base}-{i}"
            i += 1

        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)


class SEOModel(models.Model):
    """
    SEO поля + дефолты из title/content
    """
    meta_title = models.CharField("Meta title", max_length=255, blank=True)
    meta_description = models.CharField("Meta description", max_length=160, blank=True)
    meta_keywords = models.CharField("Meta keywords", max_length=255, blank=True)

    og_title = models.CharField("OG title", max_length=255, blank=True)
    og_description = models.CharField("OG description", max_length=160, blank=True)

    class Meta:
        abstract = True

    def get_seo_title_fallback(self) -> str:
        return getattr(self, "title", "") or ""

    def get_seo_description_fallback(self) -> str:
        content = getattr(self, "content", "") or ""
        return strip_tags(content).strip()

    def _truncate(self, text: str, max_len: int) -> str:
        text = (text or "").strip()
        if len(text) <= max_len:
            return text
        return text[: max_len - 1].rstrip() + "…"

    def apply_seo_defaults(self):
        if not self.meta_title:
            self.meta_title = self._truncate(self.get_seo_title_fallback(), 255)

        if not self.meta_description:
            self.meta_description = self._truncate(
                self.get_seo_description_fallback(), 160
            )

        if not self.og_title:
            self.og_title = self.meta_title

        if not self.og_description:
            self.og_description = self.meta_description

    def save(self, *args, **kwargs):
        self.apply_seo_defaults()
        super().save(*args, **kwargs)


class FullContentModel(
    UUIDPrimaryKeyModel,
    TimeStampedModel,
    SoftDeleteModel,
    PublishableModel,
    SluggedModel,
    SEOModel,
):
    """
    Полная база: UUID + timestamps + soft delete + publish + slug + SEO + title/content
    """
    title = models.CharField("Заголовок", max_length=255)
    content = models.TextField("Контент", blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.title
