"""Elementary WB Unit 2 "-or / -er" mashqi javob kalitlarini tuzatadi.

2026-10-10. Mantiq `courses/elementary_tuzatish.py` da; tuzatish
IDEMPOTENT, `reverse` — bo'sh amal.
"""

from django.db import migrations

from courses.elementary_tuzatish import tuzat


def qolla(apps, schema_editor):
    hisobot = tuzat(
        apps.get_model("courses", "KursTugun"), apps.get_model("courses", "KursMashq")
    )
    for izoh, bajarildi in hisobot:
        print(f"  Elementary: {'QOLLANDI' if bajarildi else 'topilmadi'} {izoh}")


class Migration(migrations.Migration):

    dependencies = [("courses", "0024_kurssozyechim")]

    operations = [migrations.RunPython(qolla, migrations.RunPython.noop)]
