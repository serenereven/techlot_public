from django.db import models


class SoftDeletePublishQuerySet(models.QuerySet):
    # --- soft delete ---
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)

    # --- publishable ---
    def published(self):
        # ⚡ published ВСЕГДА только из alive
        return self.filter(is_published=True)

    def drafts(self):
        # если нужно — тоже только из alive
        return self.filter(is_published=False)

BaseSoftDeletePublishManager = models.Manager.from_queryset(SoftDeletePublishQuerySet)

class SoftDeleteAllManager(BaseSoftDeletePublishManager):
    """Все записи (включая удаленные)"""
    pass


class SoftDeleteAliveManager(BaseSoftDeletePublishManager):
    """Только не удаленные (по умолчанию)"""
    def get_queryset(self):
        return super().get_queryset().alive()


class SoftDeleteDeletedManager(BaseSoftDeletePublishManager):
    """Только удаленные"""
    def get_queryset(self):
        return super().get_queryset().deleted()

class PublishedManager(BaseSoftDeletePublishManager):
    """Только опубликованные (по умолчанию alive)"""
    def get_queryset(self):
        return super().get_queryset().published()

class DraftsManager(BaseSoftDeletePublishManager):
    """Только черновики (по умолчанию alive)"""
    def get_queryset(self):
        return super().get_queryset().drafts()
