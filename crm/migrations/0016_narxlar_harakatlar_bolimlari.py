""""Kurs narxlari" va "Harakatlar tarixi" — rol oynasida alohida bo'lim (video-TZ, 2026-10-16).

Avval ikkalasi `sozlamalar` bo'limi ostida edi. Mavjud rollar huquqini yo'qotmasin:
- `sozlamalar.narxlar` -> `narxlar.korish` + `narxlar.tahrirlash`;
- Sozlamalar'ning biror ruxsati bor rol "Harakatlar tarixi"ni ko'rardi -> `harakatlar.korish`.
"""

from django.db import migrations

ESKI_NARX = "sozlamalar.narxlar"
NARX = ["narxlar.korish", "narxlar.tahrirlash"]
HARAKAT = "harakatlar.korish"


def _sozlamali(royxat):
    return any(k == "sozlamalar" or k.startswith("sozlamalar.") for k in royxat)


def kochir(apps, schema_editor):
    CrmRol = apps.get_model("crm", "CrmRol")
    for rol in CrmRol.objects.all():
        eski = list(rol.ruxsatlar or [])
        yangi = [k for k in eski if k != ESKI_NARX]
        if ESKI_NARX in eski or "sozlamalar" in eski:
            yangi += [k for k in NARX if k not in yangi]
        if _sozlamali(eski) and HARAKAT not in yangi:
            yangi.append(HARAKAT)
        if yangi != eski:
            rol.ruxsatlar = yangi
            rol.save(update_fields=["ruxsatlar"])


def qaytar(apps, schema_editor):
    CrmRol = apps.get_model("crm", "CrmRol")
    for rol in CrmRol.objects.all():
        eski = list(rol.ruxsatlar or [])
        yangi = [k for k in eski if k not in NARX and k not in ("narxlar", "harakatlar", HARAKAT)]
        if "narxlar.tahrirlash" in eski and ESKI_NARX not in yangi:
            yangi.append(ESKI_NARX)
        if yangi != eski:
            rol.ruxsatlar = yangi
            rol.save(update_fields=["ruxsatlar"])


class Migration(migrations.Migration):
    dependencies = [("crm", "0015_kurs_narxi_dars_uchun")]
    operations = [migrations.RunPython(kochir, qaytar)]
