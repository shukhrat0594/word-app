"""Pre-Intermediate: mashq turi noto'g'ri qayta yaratilgan 6 ta sahifani tuzatadi.

2026-09-07. Mantiq `courses/pre_intermediate_tuzatish.py` da — kitob kontenti
migratsiya faylida yotmasligi va keyin ham o'qish oson bo'lishi uchun.

Tuzatishlar IDEMPOTENT (allaqachon qo'llangan bo'lsa hech narsa qilmaydi),
shuning uchun `reverse` — bo'sh amal: ular kontent xatosini to'g'irlaydi,
qaytarish uchun sabab yo'q.
"""

from django.db import migrations

from courses.pre_intermediate_tuzatish import tuzat


def qolla(apps, schema_editor):
    tuzat(apps.get_model("courses", "KursTugun"), apps.get_model("courses", "KursMashq"))


class Migration(migrations.Migration):

    dependencies = [("courses", "0019_javob_kaliti_oqituvchiga")]

    operations = [migrations.RunPython(qolla, migrations.RunPython.noop)]
