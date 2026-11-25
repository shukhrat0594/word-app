# Matn-TZ 759 (2026-11-25): "head_teacher" roli 12 belgi — 10 dan 20 ga.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("audit", "0002_loginhistory"),
    ]

    operations = [
        migrations.AlterField(
            model_name="loginhistory",
            name="rol",
            field=models.CharField(
                help_text="Login paytidagi rol snapshoti (keyin o'zgarishi mumkin)",
                max_length=20,
            ),
        ),
    ]
