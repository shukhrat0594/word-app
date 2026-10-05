"""Avval yaratilgan "Ota-ona so'rovi" bildirishnomalari ham bosilganda CRM bo'limiga o'tsin."""

from django.db import migrations


def tuldir(apps, schema_editor):
    Bildirishnoma = apps.get_model("accounts", "Bildirishnoma")
    Bildirishnoma.objects.filter(kalit__startswith="parentsbot:sorov:", havola="").update(havola="/crm/parentsbot")


class Migration(migrations.Migration):
    dependencies = [
        ("parentsbot", "0001_initial"),
        ("accounts", "0028_bildirishnoma_havola"),
    ]
    operations = [migrations.RunPython(tuldir, migrations.RunPython.noop)]
