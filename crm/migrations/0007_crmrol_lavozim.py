"""Tizim rollari (2026-09-23): lavozimlarning standart ruxsatlari bazaga
ko'chadi — owner ularni ham tahrirlay oladi.

Ruxsatlar `crm.ruxsatlar._STANDART`dan AYNAN hozirgi xatti-harakat bilan
to'ldiriladi: migratsiyadan keyin hech kimning ruxsati o'zgarmaydi.
"""

from django.db import migrations, models


def tizim_rollarini_yarat(apps, schema_editor):
    from crm.ruxsatlar import TIZIM_ROLLARI, standart_ruxsatlar

    CrmRol = apps.get_model("crm", "CrmRol")
    for lavozim, nomi in TIZIM_ROLLARI:
        if CrmRol.objects.filter(lavozim=lavozim).exists():
            continue
        # Shu nomli maxsus rol allaqachon bo'lsa — nomi unikal, qo'shimcha bilan.
        yakuniy = nomi
        if CrmRol.objects.filter(nomi__iexact=yakuniy).exists():
            yakuniy = f"{nomi} (lavozim)"
        CrmRol.objects.create(
            nomi=yakuniy, lavozim=lavozim, faol=True, ruxsatlar=standart_ruxsatlar(lavozim)
        )


def tizim_rollarini_ochir(apps, schema_editor):
    apps.get_model("crm", "CrmRol").objects.filter(lavozim__isnull=False).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0006_lid_yigilayotgan_guruh"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmrol",
            name="lavozim",
            field=models.CharField(blank=True, max_length=12, null=True, unique=True),
        ),
        migrations.RunPython(tizim_rollarini_yarat, tizim_rollarini_ochir),
    ]
