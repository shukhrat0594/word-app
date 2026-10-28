from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0028_test_guruh_boyicha'),
    ]

    operations = [
        migrations.AddField(
            model_name='kurssoz',
            name='sinonimlar',
            field=models.JSONField(blank=True, default=dict, help_text='2026-10-28 (Matn-TZ 674): shu turkumdagi QO\'SHIMCHA to\'g\'ri tarjimalar — {"uz": [...], "ru": [...]}, masalan award (v) -> taqdirlamoq, mukofot bermoq, e\'tirof etmoq. Tekshiruvda `uz`/`ru` bilan birga to\'g\'ri hisoblanadi (har til alohida). `soz_sinonimlari` buyrug\'i bilan to\'ldiriladi; bo\'sh bo\'lsa faqat `uz`/`ru` tekshiriladi.'),
        ),
    ]
