import common.models.fields
import django.db.models.deletion
import uuid
from django.db import migrations, models


def forwards_copy_vehicle_type(apps, schema_editor):
    Vehicle = apps.get_model("core", "Vehicle")
    VehicleType = apps.get_model("core", "VehicleType")

    # В этот момент в состоянии миграции у Vehicle есть:
    # - vehicle_type (старое строковое поле с кодом)
    # - vehicle_type_fk (новое FK поле)
    qs = Vehicle.objects.all().only("id", "vehicle_type")

    to_update = []
    for v in qs.iterator():
        code = (getattr(v, "vehicle_type", "") or "").strip()
        if not code:
            continue

        # безопасность под max_length=32
        code = code[:32]

        vt, _ = VehicleType.objects.get_or_create(
            code=code,
            defaults={"name": code},
        )

        v.vehicle_type_fk_id = vt.id
        to_update.append(v)

    if to_update:
        Vehicle.objects.bulk_update(to_update, ["vehicle_type_fk"])


def backwards_copy_vehicle_type(apps, schema_editor):
    # Откат данных делаем no-op (можно усложнить, если нужно)
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_alter_purchaserequest_phone_alter_vehicle_mileage_km_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="VehicleType",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.CharField(max_length=32, unique=True, verbose_name="Код")),
                ("name", models.CharField(max_length=120, verbose_name="Название")),
            ],
            options={
                "verbose_name": "Тип техники",
                "verbose_name_plural": "Типы техники",
                "ordering": ("name",),
            },
        ),

        migrations.RenameIndex(
            model_name="vehicle",
            new_name="core_vehicl_vehicle_38a2a5_idx",
            old_name="core_vehicl_vehicle_dfecc7_idx",
        ),

        migrations.AlterField(
            model_name="purchaserequest",
            name="phone",
            field=common.models.fields.PhoneField(
                max_length=16,
                validators=[common.models.fields.validate_phone, common.models.fields.validate_phone],
                verbose_name="Телефон",
            ),
        ),

        # ✅ Вместо AlterField на vehicle_type делаем перенос через новое поле

        migrations.AddField(
            model_name="vehicle",
            name="vehicle_type_fk",
            field=models.ForeignKey(
                to="core.vehicletype",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="vehicles",
                verbose_name="Тип техники",
                null=True,
                blank=True,
            ),
        ),

        migrations.RunPython(forwards_copy_vehicle_type, backwards_copy_vehicle_type),

        migrations.RemoveField(
            model_name="vehicle",
            name="vehicle_type",
        ),

        migrations.RenameField(
            model_name="vehicle",
            old_name="vehicle_type_fk",
            new_name="vehicle_type",
        ),
    ]