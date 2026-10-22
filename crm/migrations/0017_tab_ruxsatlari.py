"""Hisobotlar va Moliya tablari, bosh sahifadagi "Shu oy ketganlar" — alohida ruxsat (TZ #477, 2026-10-22).

Mavjud rollar ko'rib turgan narsasini yo'qotmasin: bo'limning biror ruxsati
bor rol (avval butun bo'limni ko'rardi) — shu bo'limning yangi kalitlarini oladi.
"""

from django.db import migrations

YANGI = {
    "bosh_sahifa": ["bosh_sahifa.ketganlar"],
    "moliya": ["moliya.qarzdorlar", "moliya.tolovlar", "moliya.hisobot"],
    # `hisobotlar.dinamika` avval ham bor edi, lekin tekshirilmasdi — endi
    # tab unga bog'landi, shuning uchun u ham beriladi (orqaga qaytarilmaydi).
    "hisobotlar": ["hisobotlar.dinamika", "hisobotlar.tolovlar", "hisobotlar.lidlar", "hisobotlar.ketganlar",
                   "hisobotlar.bitiruvchilar"],
}
HAMMASI = {k for v in YANGI.values() for k in v} - {"hisobotlar.dinamika"}


def _bolimli(royxat, bolim):
    return any(k == bolim or k.startswith(bolim + ".") for k in royxat)


def kochir(apps, schema_editor):
    CrmRol = apps.get_model("crm", "CrmRol")
    for rol in CrmRol.objects.all():
        eski = list(rol.ruxsatlar or [])
        yangi = list(eski)
        for bolim, kalitlar in YANGI.items():
            if _bolimli(eski, bolim):
                yangi += [k for k in kalitlar if k not in yangi]
        if yangi != eski:
            rol.ruxsatlar = yangi
            rol.save(update_fields=["ruxsatlar"])


def qaytar(apps, schema_editor):
    CrmRol = apps.get_model("crm", "CrmRol")
    for rol in CrmRol.objects.all():
        eski = list(rol.ruxsatlar or [])
        yangi = [k for k in eski if k not in HAMMASI]
        if yangi != eski:
            rol.ruxsatlar = yangi
            rol.save(update_fields=["ruxsatlar"])


class Migration(migrations.Migration):
    dependencies = [("crm", "0016_narxlar_harakatlar_bolimlari")]
    operations = [migrations.RunPython(kochir, qaytar)]
