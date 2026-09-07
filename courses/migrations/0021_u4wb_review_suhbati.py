"""Unit 4 WB REVIEW — suhbatni mashqning oldiga qaytaradi.

2026-09-07. 0019 da "Suhbat matni:" bilan boshlanadigan blok javob kaliti
deb hisoblanib, talabadan yashirilgan edi — aslida u mashqning O'Z MATNI
(variantlari ochiq turgan A/B suhbati), ya'ni usiz mashqni yechib
bo'lmasdi. 0019 dagi naqsh tuzatildi (yangi bazalarda umuman yashirilmaydi),
bu migratsiya esa allaqachon yashirilgan bazalarni to'g'irlaydi va
suhbatni tanlovdan OLDINGI joyiga qaytaradi.

Mantiq `courses/pre_intermediate_tuzatish.py` da; barcha tuzatishlar
idempotent, shuning uchun bu yerda ham hammasi qayta chaqiriladi.
"""

from django.db import migrations

from courses.pre_intermediate_tuzatish import tuzat


def qolla(apps, schema_editor):
    KursTugun = apps.get_model("courses", "KursTugun")
    KursMashq = apps.get_model("courses", "KursMashq")
    # 0019 belgisini olib tashlaymiz — bu blok javob kaliti emas.
    for mashq in KursMashq.objects.filter(bloklar__icontains="Suhbat matni:"):
        ozgardi = False
        for blok in mashq.bloklar or []:
            if not isinstance(blok, dict) or not blok.get("oqituvchi_uchun"):
                continue
            if str(blok.get("matn", "")).strip().lower().startswith("suhbat matni:"):
                del blok["oqituvchi_uchun"]
                ozgardi = True
        if ozgardi:
            mashq.save(update_fields=["bloklar"])

    tuzat(KursTugun, KursMashq)


class Migration(migrations.Migration):

    dependencies = [("courses", "0020_pre_intermediate_mashq_turlari")]

    operations = [migrations.RunPython(qolla, migrations.RunPython.noop)]
