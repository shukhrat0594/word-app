"""Intermediate: mashq shakli noto'g'ri qayta yaratilgan 4 ta sahifani tuzatadi.

2026-09-14. Mantiq `courses/intermediate_tuzatish.py` da — kitob kontenti
migratsiya faylida yotmasligi va keyin ham o'qish oson bo'lishi uchun.

Tuzatishlar IDEMPOTENT (allaqachon qo'llangan bo'lsa hech narsa qilmaydi),
shuning uchun `reverse` — bo'sh amal: ular kontent xatosini to'g'irlaydi,
qaytarish uchun sabab yo'q.
"""

from django.db import migrations

from courses.intermediate_tuzatish import tuzat


def qolla(apps, schema_editor):
    hisobot = tuzat(
        apps.get_model("courses", "KursTugun"), apps.get_model("courses", "KursMashq")
    )
    # Prodda (Railway) migratsiya deploy logida ko'rinadi — qaysi tuzatish
    # qo'llanganini, qaysi biri mashqni TOPMAGANINI shu yerdan bilamiz.
    # Matn ataylab ASCII: konsol kodlashi UTF-8 bo'lmasa `print` yiqilib,
    # butun deploy'ni to'xtatib qo'yishi mumkin edi.
    for izoh, bajarildi in hisobot:
        print(f"  Intermediate: {'QOLLANDI' if bajarildi else 'topilmadi'} {izoh}")


class Migration(migrations.Migration):

    dependencies = [("courses", "0022_grammar_spot_javoblari")]

    operations = [migrations.RunPython(qolla, migrations.RunPython.noop)]
