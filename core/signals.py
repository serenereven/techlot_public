"""
Сигналы для очистки кеша при изменениях
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Vehicle
from .export_utils import clear_export_cache


@receiver([post_save, post_delete], sender=Vehicle)
def clear_vehicles_export_cache(sender, instance, **kwargs):
    """
    Очищает кеш экспорта при изменении техники.
    """
    clear_export_cache()