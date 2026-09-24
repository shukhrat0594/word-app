"""Mavjud CRM xodimlari (LMS roli "oddiy": kassir, marketolog...) — saytda
mehmon menyusi o'rniga faqat Bosh sahifa va Profil (2026-09-23).
Owner qo'lda panel belgilagan bo'lsa — tegilmaydi."""

from django.db import migrations

CRM_XODIM_PANELLARI = ["/"]  # `crm.ruxsatlar.CRM_XODIM_PANELLARI` bilan bir xil


def toraytir(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(role="oddiy", crm_xodim__isnull=False, korinadigan_panellar__isnull=True).update(
        korinadigan_panellar=CRM_XODIM_PANELLARI
    )


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0007_crmrol_lavozim"),
        ("accounts", "0026_ota_ona_ismi"),
    ]

    operations = [migrations.RunPython(toraytir, migrations.RunPython.noop)]
