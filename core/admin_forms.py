from django import forms


class VehicleImportForm(forms.Form):
    file = forms.FileField(label="Excel файл (.xlsx)")
    dry_run = forms.BooleanField(
        label="Dry-run (без сохранения)",
        required=False,
        initial=True,
        help_text="Проверить данные без записи в БД",
    )
    publish = forms.BooleanField(
        label="Опубликовать после импорта",
        required=False,
        initial=False,
    )
