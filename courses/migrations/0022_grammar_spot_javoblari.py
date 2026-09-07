"""GRAMMAR SPOT javoblarini talabadan yashiradi (o'qituvchida qoladi).

2026-09-07. Mantiq `courses/grammar_spot_tuzatish.py` da. Javob savolning
o'z qatoriga yozilgani uchun butun blokni yashirib bo'lmaydi — javob qismi
alohida qatorga ajratiladi va qator darajasida belgilanadi.
"""

from django.db import migrations

from courses.grammar_spot_tuzatish import tuzat


def qolla(apps, schema_editor):
    tuzat(apps.get_model("courses", "KursTugun"), apps.get_model("courses", "KursMashq"))


class Migration(migrations.Migration):

    dependencies = [("courses", "0021_u4wb_review_suhbati")]

    operations = [migrations.RunPython(qolla, migrations.RunPython.noop)]
