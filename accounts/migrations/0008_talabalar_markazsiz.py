# Generated manually 2026-08-02 — talabalar markazga bog'lanmaydi, mavjud
# ma'lumotlar (agar bo'lsa) tozalanadi.

from django.db import migrations


def _talabalarni_markazsizlantir(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(role="student").update(markaz=None)


def _hech_narsa(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_user_korish_rejimi"),
    ]

    operations = [
        migrations.RunPython(_talabalarni_markazsizlantir, _hech_narsa),
    ]
