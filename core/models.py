from django.db import models
from common.models import (
    UUIDPrimaryKeyModel,
    FullContentModel,
    PhoneField,
    NormalizedEmailField,
    TimeStampedModel,
    PublishableModel,
)

# =========================
# Справочники
# =========================

class Region(UUIDPrimaryKeyModel):
    name = models.CharField("Регион", max_length=120, unique=True, db_index=True)

    class Meta:
        verbose_name = "Регион"
        verbose_name_plural = "Регионы"
        ordering = ("name",)

    def __str__(self):
        return self.name


class City(UUIDPrimaryKeyModel):
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name="cities",
        verbose_name="Регион",
    )
    name = models.CharField("Город", max_length=120, db_index=True)

    maps_code = models.TextField("Код карты", blank=True, null=True, db_index=True)

    class Meta:
        verbose_name = "Город"
        verbose_name_plural = "Города"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["region", "name"],
                name="core_city_region_name_uniq",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.region})"


class Brand(UUIDPrimaryKeyModel):
    name = models.CharField("Марка", max_length=80, unique=True, db_index=True)

    class Meta:
        verbose_name = "Марка"
        verbose_name_plural = "Марки"
        ordering = ("name",)

    def __str__(self):
        return self.name


class VehicleModel(UUIDPrimaryKeyModel):
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="models",
        verbose_name="Марка",
        blank=True,
        null=True,
    )
    name = models.CharField("Модель", max_length=120, db_index=True)

    class Meta:
        verbose_name = "Модель"
        verbose_name_plural = "Модели"
        ordering = ("brand__name", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["brand", "name"],
                name="core_vehiclemodel_brand_name_uniq",
            )
        ]

    def __str__(self):
        return f"{self.brand.name} {self.name}"

class EngineType(UUIDPrimaryKeyModel):
    name = models.CharField("Тип двигателя", max_length=80, unique=True)

    class Meta:
        verbose_name = "Тип двигателя"
        verbose_name_plural = "Типы двигателя"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Transmission(UUIDPrimaryKeyModel):
    name = models.CharField("Коробка передач", max_length=80, unique=True)

    class Meta:
        verbose_name = "Коробка передач"
        verbose_name_plural = "Коробки передач"
        ordering = ("name",)

    def __str__(self):
        return self.name


class TechnicalCondition(UUIDPrimaryKeyModel):
    name = models.CharField("Техническое состояние", max_length=80, unique=True)

    class Meta:
        verbose_name = "Техническое состояние"
        verbose_name_plural = "Технические состояния"
        ordering = ("name",)

    def __str__(self):
        return self.name

class VehicleType(UUIDPrimaryKeyModel):
    code = models.CharField("Код", max_length=32, unique=True, db_index=True)
    name = models.CharField("Название", max_length=120)
    image = models.ImageField("Изображение", upload_to="vehicles_types/", blank=True)
    order = models.PositiveSmallIntegerField("Порядок", default=0, db_index=True)

    class Meta:
        verbose_name = "Тип техники"
        verbose_name_plural = "Типы техники"
        ordering = ("name",)

    def __str__(self):
        return self.name

# =========================
# Каталог
# =========================

class StockStatus(models.TextChoices):
    AWAITING = "awaiting", "В ожидании поступления"
    IN_STOCK = "in_stock", "В наличии"
    RESERVED = "reserved", "В резерве"
    LEASING = "leasing", "Продажа в лизинг" 
    SOLD = "sold", "Продано"

class VehiclePhoto(models.Model):
    vehicle = models.ForeignKey(
        "Vehicle",
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name="Техника",
    )

    image = models.ImageField("Фото", upload_to="vehicles/photos/")
    caption = models.CharField("Подпись", max_length=120, blank=True)
    sort_order = models.PositiveSmallIntegerField("Порядок", default=0, db_index=True)
    is_main = models.BooleanField("Главное", default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Фото техники"
        verbose_name_plural = "Фото техники"
        ordering = ("sort_order", "created_at")
        indexes = [
            models.Index(fields=["vehicle", "is_main"]),
            models.Index(fields=["vehicle", "sort_order"]),
        ]

    def __str__(self):
        return f"Фото для {self.vehicle_id}"


class Vehicle(FullContentModel):
    """
    Карточка техники в каталоге.
    FullContentModel даёт:
    - UUID id
    - created/updated
    - soft delete
    - publish + managers published/drafts
    - slug + SEO
    - title + content (content = описание)
    """

    bitrix_id = models.IntegerField(
        verbose_name="Bitrix ID", 
        null=True, blank=True, unique=True, db_index=True
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name="vehicles",
        verbose_name="Город",
        db_index=True,
        blank=True,
        null=True,
    )
    vehicle_type = models.ForeignKey(
        VehicleType,
        on_delete=models.SET_NULL,
        related_name="vehicles",
        verbose_name="Тип техники",
        db_index=True,
        blank=True,
        null=True,
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="vehicles",
        verbose_name="Марка",
        db_index=True,
        blank=True,
        null=True,
    )
    model = models.ForeignKey(
        VehicleModel,
        on_delete=models.PROTECT,
        related_name="vehicles",
        verbose_name="Модель",
        db_index=True,
        blank=True,
        null=True, 
    )
    engine_type = models.ForeignKey(
        EngineType,
        on_delete=models.SET_NULL,
        related_name="vehicles",
        verbose_name="Тип двигателя",
        blank=True,
        null=True,
    )
    transmission = models.ForeignKey(
        Transmission,
        on_delete=models.SET_NULL,
        related_name="vehicles",
        verbose_name="Коробка передач",
        blank=True,
        null=True,
    )
    technical_condition = models.ForeignKey(
        TechnicalCondition,
        on_delete=models.SET_NULL,
        related_name="vehicles",
        verbose_name="Техническое состояние",
        blank=True,
        null=True,
        db_index=True,
    )

    vin = models.CharField("VIN", max_length=32, blank=True, db_index=True)

    mileage_km = models.PositiveIntegerField("Пробег, км", default=0, blank=True, null=True)

    year = models.PositiveSmallIntegerField("Год выпуска", db_index=True, blank=True, null=True)

    color = models.CharField("Цвет", max_length=40, blank=True)

    engine_power_hp = models.DecimalField(
        "Мощность двигателя, л.с.",
        max_digits=8,      # хватит до 99999.99
        decimal_places=3,  # 2 знака после запятой
        blank=True,
        null=True,
    )
    wheel_formula = models.CharField(
        "Колесная формула",
        max_length=20,
        blank=True,
        db_index=True,
        help_text="Например: 4x2, 6x4, 6x6",
        null=True,
    )
    price_rub = models.DecimalField(
        "Стоимость, ₽",
        max_digits=12,
        decimal_places=0,
        db_index=True,
        blank=True,
        null=True,
    )
    stock_status = models.CharField(
        "Статус",
        max_length=20,
        choices=StockStatus.choices,
        default=StockStatus.IN_STOCK,
        db_index=True,
        blank=True,
        null=True,
    )

    to_homepage = models.BooleanField("На главную", default=False, db_index=True)

    class Meta:
        verbose_name = "Техника"
        verbose_name_plural = "Техника"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["vehicle_type", "stock_status"]),
            models.Index(fields=["brand", "model"]),
            models.Index(fields=["city"]),
            models.Index(fields=["year"]),
            models.Index(fields=["price_rub"]),
            models.Index(fields=["mileage_km"]),
        ]
        constraints = [
            # VIN уникален только если заполнен (пустые допускаются)
            models.UniqueConstraint(
                fields=["vin"],
                condition=~models.Q(vin=""),
                name="core_vehicle_vin_unique_when_not_empty",
            )
        ]

    def __str__(self):
        try:
            brand = self.brand.name if self.brand_id else ""
            model = self.model.name if self.model_id else ""
        except Exception:
            brand, model = "Без марки", "Без модели"
        return f"{brand} {model} ({self.year}).".replace("  ", " ")

    @property
    def gallery(self):
        # все фото из связанной модели VehiclePhoto
        return self.photos.all()

    @property
    def main_photo(self):
        """
        Главное изображение:
        1) фото с is_main=True
        2) первое фото из галереи
        """
        main_obj = self.photos.filter(is_main=True).first()
        if main_obj and main_obj.image:
            return main_obj.image

        first_obj = self.photos.first()
        if first_obj and first_obj.image:
            return first_obj.image

        return None


# =========================
# Заявка на покупку
# =========================
class RequestType(models.TextChoices):
    PURCHASE = "purchase", "Покупка"
    LEASING = "leasing", "Лизинг"
    
class PurchaseRequest(UUIDPrimaryKeyModel, TimeStampedModel):
    """
    Заявка на покупку (форма обратной связи)
    """

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="purchase_requests",
        verbose_name="Техника",
    )

    source = models.CharField(
        "Источник",
        max_length=50,
        default="site",
        db_index=True,
        help_text="Например: site, instagram, avito",
    )

    name = models.CharField("Имя", max_length=120)
    phone = PhoneField("Телефон")

    request_type = models.CharField(
        "Тип заявки",
        max_length=20,
        choices=RequestType.choices,
        default=RequestType.PURCHASE,
        db_index=True,
    )

    inn = models.CharField(
        "ИНН",
        max_length=12,
        blank=True,
        null=True,
    )

    bitrix_sent = models.BooleanField(default=False)
    bitrix_error = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"
        ordering = ("-created_at",)

    def __str__(self):
        if self.vehicle_id:
            return f"Заявка ({self.source}) — {self.name} — {self.vehicle}"
        return f"Заявка ({self.source}) — {self.name}"

    def clean(self):
        from django.core.exceptions import ValidationError
        import re

        if self.request_type == RequestType.LEASING:
            if not self.inn:
                raise ValidationError({"inn": "ИНН обязателен для заявки на лизинг"})

            if not re.fullmatch(r"\d{10}|\d{12}", self.inn):
                raise ValidationError({"inn": "ИНН должен содержать 10 или 12 цифр"})


# =========================
# Контакты
# =========================

class ContactType(models.TextChoices):
    PHONE = "receiver", "Телефон"
    EMAIL = "mail", "Email"
    TELEGRAM = "telegram", "Telegram"
    WHATSAPP = "whatsapp", "WhatsApp"
    VK = "vk", "ВКонтакте"
    LINK = "link-external", "Ссылка"
    ADDRESS = "location", "Адрес"
    # OTHER = "other", "Другое"


class Contact(UUIDPrimaryKeyModel, TimeStampedModel, PublishableModel):
    """
    Контакты для вывода на сайте: телефон, telegram, whatsapp и т.д.
    Публикация управляется через PublishableModel.
    """

    title = models.CharField("Название", max_length=120)
    contact_type = models.CharField(
        "Тип",
        max_length=20,
        choices=ContactType.choices,
        db_index=True,
    )
    value = models.CharField(
        "Значение",
        max_length=255,
        help_text="Например: +79991234567 / email@site.ru / username / https://t.me/username",
    )

    sort_order = models.PositiveSmallIntegerField("Порядок", default=0, db_index=True)

    class Meta:
        verbose_name = "Контакт"
        verbose_name_plural = "Контакты"
        ordering = ("sort_order", "title")
        indexes = [
            models.Index(fields=["contact_type"]),
            models.Index(fields=["sort_order"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_contact_type_display()})"

    @property
    def normalized_value(self) -> str:
        return (self.value or "").strip()

    @property
    def link(self) -> str:
        """
        Упрощённый href:
        - phone -> tel:+79991234567
        - email -> mailto:email@site.ru
        - остальные -> value как есть
        """
        v = (self.value or "").strip()
        if not v:
            return ""

        if self.contact_type == ContactType.PHONE:
            phone = v.replace(" ", "").replace("-", "")
            if not phone.startswith("+") and phone.isdigit():
                phone = f"+7{phone[1:]}"
            return f"tel:{phone}"

        if self.contact_type == ContactType.EMAIL:
            return f"mailto:{v}"

        return v

    def save(self, *args, **kwargs):
        if self.contact_type == ContactType.PHONE:
            self.value = self._format_phone(self.value)
        super().save(*args, **kwargs)

    @staticmethod
    def _format_phone(raw: str) -> str:
        """Приводит телефон к виду 8 495-065-90-92."""

        digits = "".join(c for c in (raw or "") if c.isdigit())

        if len(digits) != 11:
            return raw

        return f"8 {digits[1:4]}-{digits[4:7]}-{digits[7:9]}-{digits[9:11]}"


# =========================
# Простые страницы
# =========================

class BasicPage(FullContentModel):
    is_navbar = models.BooleanField("В меню", default=False)
    
    class Meta:
        verbose_name = "Простая страница"
        verbose_name_plural = "Простые страницы"
        ordering = ("title",)