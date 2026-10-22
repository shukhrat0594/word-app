"""Bosh sahifaning har kartochkasi va bo'limi — alohida ruxsat (TZ #490, 2026-10-22).

Mavjud rollar ko'rib turgan narsasini yo'qotmasin:
- bosh sahifaning biror ruxsati bor rol — avval ruxsatsiz ko'rinadigan
  kartochkalarni (guruhlar, o'qituvchilar...) oladi;
- avval boshqa kalitga bog'langan kartochka — o'sha kalit bor rolga beriladi;
- "Moliya" bo'limi avval `hisobotlar` bilan ko'rinardi — endi
  `bosh_sahifa.moliya` ham kerak, shuning uchun ikkalasi bor rolga beriladi.
"""

from django.db import migrations

OCHIQ_EDI = ["bosh_sahifa.guruhlar", "bosh_sahifa.jami_guruhdagi", "bosh_sahifa.sinov_darsida",
             "bosh_sahifa.oqituvchilar", "bosh_sahifa.muzlatilgan"]
AJRATILGAN = {
    "bosh_sahifa.faol_lidlar": ["bosh_sahifa.yangi_lidlar_bugun", "bosh_sahifa.yangi_guruhga_qabul"],
    "bosh_sahifa.qarzdorlar": ["bosh_sahifa.joriy_oy_qarzi"],
}
HAMMASI = set(OCHIQ_EDI) | {k for v in AJRATILGAN.values() for k in v}


def _bolimli(royxat, bolim):
    return any(k == bolim or k.startswith(bolim + ".") for k in royxat)


def kochir(apps, schema_editor):
    CrmRol = apps.get_model("crm", "CrmRol")
    for rol in CrmRol.objects.all():
        eski = list(rol.ruxsatlar or [])
        if "bosh_sahifa" in eski or not _bolimli(eski, "bosh_sahifa"):
            continue  # butun bo'lim (hammasi o'zi beriladi) yoki bosh sahifa yopiq
        yangi = list(eski)
        qoshiladi = list(OCHIQ_EDI)
        for eski_kalit, kalitlar in AJRATILGAN.items():
            if eski_kalit in eski:
                qoshiladi += kalitlar
        if _bolimli(eski, "hisobotlar"):
            qoshiladi.append("bosh_sahifa.moliya")
        yangi += [k for k in qoshiladi if k not in yangi]
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
    dependencies = [("crm", "0017_tab_ruxsatlari")]
    operations = [migrations.RunPython(kochir, qaytar)]
