from django.db import migrations, models
import django.db.models.deletion


def cleanup_orphan_lookups(apps, schema_editor):
    """
    Удаляет записи справочников без единой связанной техники
    (учитывает и мягко удалённую технику — deleted_at IS NOT NULL).
    """
    Vehicle = apps.get_model("core", "Vehicle")
    VehicleType = apps.get_model("core", "VehicleType")
    EngineType = apps.get_model("core", "EngineType")
    Transmission = apps.get_model("core", "Transmission")
    TechnicalCondition = apps.get_model("core", "TechnicalCondition")

    lookup_fields = {
        "VehicleType": (VehicleType, "vehicle_type"),
        "EngineType": (EngineType, "engine_type"),
        "Transmission": (Transmission, "transmission"),
        "TechnicalCondition": (TechnicalCondition, "technical_condition"),
    }

    for name, (Model, field_name) in lookup_fields.items():
        used_ids = set(Vehicle.objects.exclude(**{f"{field_name}_id": None}).values_list(f"{field_name}_id", flat=True))
        deleted_count, _ = Model.objects.exclude(pk__in=used_ids).delete()
        print(f"  {name}: удалено {deleted_count} записей")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0011_vehicle_bitrix_id_alter_basicpage_slug_and_more"),
    ]

    operations = [
        # 1. Чистим осиротевшие записи пока ещё стоит PROTECT
        migrations.RunPython(cleanup_orphan_lookups, migrations.RunPython.noop),
        # 2. Меняем on_delete → SET_NULL
        migrations.AlterField(
            model_name="vehicle",
            name="vehicle_type",
            field=models.ForeignKey(
                to="core.vehicletype",
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="vehicles",
                verbose_name="\u0422\u0438\u043f \u0442\u0435\u0445\u043d\u0438\u043a\u0438",
                db_index=True,
                blank=True,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="vehicle",
            name="engine_type",
            field=models.ForeignKey(
                to="core.enginetype",
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="vehicles",
                verbose_name="\u0422\u0438\u043f \u0434\u0432\u0438\u0433\u0430\u0442\u0435\u043b\u044f",
                blank=True,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="vehicle",
            name="transmission",
            field=models.ForeignKey(
                to="core.transmission",
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="vehicles",
                verbose_name="\u041a\u043e\u0440\u043e\u0431\u043a\u0430 \u043f\u0435\u0440\u0435\u0434\u0430\u0447",
                blank=True,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="vehicle",
            name="technical_condition",
            field=models.ForeignKey(
                to="core.technicalcondition",
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="vehicles",
                verbose_name="\u0422\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u043e\u0435 \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435",
                blank=True,
                null=True,
                db_index=True,
            ),
        ),
    ]
