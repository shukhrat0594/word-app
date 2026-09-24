"""Xodim — bir nechta filial; CEO — faqat owner (2026-09-23, Shuhrat).

1. `XodimProfil.filial` (bitta) -> `filiallar` (bir nechta): qiymat
   ko'chiriladi, eski maydon olib tashlanadi (filial bitta joyda turadi).
2. "Saytdagi owner CRM'da CEO bo'ladi" — CEO xodimga berilmaydigan lavozim:
   mavjud CEO lavozimli xodim Administratorga o'tadi, CEO tizim roli o'chadi.
"""

from django.db import migrations, models


def filialni_kochir(apps, schema_editor):
    XodimProfil = apps.get_model("crm", "XodimProfil")
    for p in XodimProfil.objects.exclude(filial__isnull=True):
        p.filiallar.add(p.filial_id)


def filialni_qaytar(apps, schema_editor):
    XodimProfil = apps.get_model("crm", "XodimProfil")
    for p in XodimProfil.objects.all():
        birinchi = p.filiallar.order_by("id").first()
        if birinchi is not None:
            p.filial_id = birinchi.id
            p.save(update_fields=["filial"])


def ceo_ni_olib_tashla(apps, schema_editor):
    apps.get_model("crm", "XodimProfil").objects.filter(lavozim="ceo").update(lavozim="admin")
    apps.get_model("crm", "CrmRol").objects.filter(lavozim="ceo").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0008_crm_xodim_sayt_menyusi"),
    ]

    operations = [
        migrations.AddField(
            model_name="xodimprofil",
            name="filiallar",
            field=models.ManyToManyField(blank=True, related_name="xodimlar_yangi", to="crm.filial"),
        ),
        migrations.RunPython(filialni_kochir, filialni_qaytar),
        migrations.RemoveField(model_name="xodimprofil", name="filial"),
        migrations.AlterField(
            model_name="xodimprofil",
            name="filiallar",
            field=models.ManyToManyField(blank=True, related_name="xodimlar", to="crm.filial"),
        ),
        migrations.RunPython(ceo_ni_olib_tashla, migrations.RunPython.noop),
    ]
