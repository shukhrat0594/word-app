"""Ota-ona boti bo'limi: tizim roli "administrator" (bazada saqlanadi) yangi kalitlarni olsin.

Kodning `_STANDART` ro'yxati faqat tizim roli bazada YO'Q bo'lganda ishlaydi (migratsiya 0007
shu ro'yxatdan to'ldirgan), shuning uchun mavjud administrator roliga kalitlarni qo'shamiz.
Boshqa rollarga (kassir, marketolog...) tegilmaydi. Owner hamma ruxsatni o'zi oladi.
"""

from django.db import migrations

KALITLAR = ["otabot", "otabot.ulash", "otabot.sozlama"]


def qosh(apps, schema_editor):
    CrmRol = apps.get_model("crm", "CrmRol")
    for rol in CrmRol.objects.filter(lavozim="admin"):
        royxat = list(rol.ruxsatlar or [])
        yangi = [k for k in KALITLAR if k not in royxat]
        if yangi:
            rol.ruxsatlar = royxat + yangi
            rol.save(update_fields=["ruxsatlar"])


def olib_tashla(apps, schema_editor):
    CrmRol = apps.get_model("crm", "CrmRol")
    for rol in CrmRol.objects.filter(lavozim="admin"):
        rol.ruxsatlar = [k for k in (rol.ruxsatlar or []) if k not in KALITLAR]
        rol.save(update_fields=["ruxsatlar"])


class Migration(migrations.Migration):
    dependencies = [("crm", "0013_davomat_kechikdi")]
    operations = [migrations.RunPython(qosh, olib_tashla)]
