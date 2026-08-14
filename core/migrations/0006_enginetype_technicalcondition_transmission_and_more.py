import uuid
import common.models.fields
import django.db.models.deletion
from django.db import migrations, models


def forwards(apps, schema_editor):
    Vehicle = apps.get_model("core", "Vehicle")
    EngineType = apps.get_model("core", "EngineType")
    Transmission = apps.get_model("core", "Transmission")
    TechnicalCondition = apps.get_model("core", "TechnicalCondition")

    # Если до этого в БД хранились "value" из choices — маппим в человекочитаемые названия
    engine_map = {
        "diesel": "Дизель",
        "petrol": "Бензин",
        "gas": "Газ",
        "electric": "Электро",
        "hybrid": "Гибрид",
        "other": "Другое",
    }
    transmission_map = {
        "manual": "МКПП",
        "automatic": "АКПП",
        "robot": "Робот",
        "cvt": "Вариатор",
        "other": "Другое",
    }
    condition_map = {
        "excellent": "Отличное",
        "good": "Хорошее",
        "ok": "Удовлетворительное",
        "needs_repair": "Требует ремонта",
    }

    for v in Vehicle.objects.all():
        # В этой миграции (на старой схеме) это обычные строковые поля
        et_raw = (getattr(v, "engine_type", "") or "").strip()
        tr_raw = (getattr(v, "transmission", "") or "").strip()
        tc_raw = (getattr(v, "technical_condition", "") or "").strip()

        if et_raw:
            et_name = engine_map.get(et_raw, et_raw)
            et_obj, _ = EngineType.objects.get_or_create(name=et_name)
            v.engine_type_fk = et_obj

        if tr_raw:
            tr_name = transmission_map.get(tr_raw, tr_raw)
            tr_obj, _ = Transmission.objects.get_or_create(name=tr_name)
            v.transmission_fk = tr_obj

        if tc_raw:
            tc_name = condition_map.get(tc_raw, tc_raw)
            tc_obj, _ = TechnicalCondition.objects.get_or_create(name=tc_name)
            v.technical_condition_fk = tc_obj

        v.save(update_fields=["engine_type_fk", "transmission_fk", "technical_condition_fk"])


def backwards(apps, schema_editor):
    # Обратная миграция не обязательна, но оставим noop
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_alter_purchaserequest_phone_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="EngineType",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=80, unique=True, verbose_name="Тип двигателя")),
            ],
            options={
                "verbose_name": "Тип двигателя",
                "verbose_name_plural": "Типы двигателя",
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="TechnicalCondition",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=80, unique=True, verbose_name="Техническое состояние")),
            ],
            options={
                "verbose_name": "Техническое состояние",
                "verbose_name_plural": "Технические состояния",
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="Transmission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=80, unique=True, verbose_name="Коробка передач")),
            ],
            options={
                "verbose_name": "Коробка передач",
                "verbose_name_plural": "Коробки передач",
                "ordering": ("name",),
            },
        ),
        # Оставляем вашу правку phone как есть
        migrations.AlterField(
            model_name="purchaserequest",
            name="phone",
            field=common.models.fields.PhoneField(
                max_length=16,
                validators=[common.models.fields.validate_phone, common.models.fields.validate_phone],
                verbose_name="Телефон",
            ),
        ),
        # 1) Добавляем новые FK-поля (временные имена)
        migrations.AddField(
            model_name="vehicle",
            name="engine_type_fk",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="vehicles",
                to="core.enginetype",
                verbose_name="Тип двигателя",
            ),
        ),
        migrations.AddField(
            model_name="vehicle",
            name="transmission_fk",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="vehicles",
                to="core.transmission",
                verbose_name="Коробка передач",
            ),
        ),
        migrations.AddField(
            model_name="vehicle",
            name="technical_condition_fk",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="vehicles",
                to="core.technicalcondition",
                verbose_name="Техническое состояние",
            ),
        ),
        # 2) Переносим данные из старых строковых полей в справочники + FK
        migrations.RunPython(forwards, backwards),
        # 3) Удаляем старые строковые поля
        migrations.RemoveField(model_name="vehicle", name="engine_type"),
        migrations.RemoveField(model_name="vehicle", name="transmission"),
        migrations.RemoveField(model_name="vehicle", name="technical_condition"),
        # 4) Переименовываем новые FK-поля в “красивые” имена
        migrations.RenameField(model_name="vehicle", old_name="engine_type_fk", new_name="engine_type"),
        migrations.RenameField(model_name="vehicle", old_name="transmission_fk", new_name="transmission"),
        migrations.RenameField(model_name="vehicle", old_name="technical_condition_fk", new_name="technical_condition"),
    ]
