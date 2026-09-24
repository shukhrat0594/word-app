"""Lid doskasi filialga bog'lanadi (2026-09-23, Shuhrat: "doskaga ham filial").

Mavjud doskalar filialsiz qoladi — ya'ni umumiy: hamma filialga ko'rinadi,
o'zgartirish esa faqat filialga bog'lanmagan xodimda. Filial ustunlaridan
taxmin qilinmaydi: bitta doskada turli filial ustunlari bo'lishi mumkin.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0009_xodim_filiallar_ceo'),
    ]

    operations = [
        migrations.AddField(
            model_name='liddoska',
            name='filial',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lid_doskalari', to='crm.filial'),
        ),
    ]
