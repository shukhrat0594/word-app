# Matn-TZ 759 (2026-11-25): "Head Teacher" (kuzatuvchi) roli.
# "head_teacher" 12 belgi — maydon 10 dan 20 ga kengaytirildi.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0033_qurilma_v2"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "Administrator"),
                    ("teacher", "O'qituvchi"),
                    ("student", "Talaba"),
                    ("parent", "Ota-ona"),
                    ("oddiy", "Oddiy foydalanuvchi"),
                    ("head_teacher", "Head Teacher"),
                ],
                db_index=True,
                default="student",
                max_length=20,
            ),
        ),
    ]
