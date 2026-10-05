"""XP yozuviga `tur` (ielts | kurs | umumiy) — Kurslar reytingi alohida hisobda.

Mavjud yozuvlar "ielts" bo'lib qoladi (mashq, Writing, Speaking), faqat davomat XP'si "umumiy"
(ikkala reytingga ham hisoblanadi).
"""

from django.db import migrations, models


def davomatni_umumiy_qil(apps, schema_editor):
    XPYozuv = apps.get_model("gamification", "XPYozuv")
    XPYozuv.objects.filter(sabab="davomat_keldi").update(tur="umumiy")


class Migration(migrations.Migration):

    dependencies = [
        ('gamification', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='xpyozuv',
            name='tur',
            field=models.CharField(db_index=True, default='ielts', max_length=10),
        ),
        migrations.RunPython(davomatni_umumiy_qil, migrations.RunPython.noop),
    ]
