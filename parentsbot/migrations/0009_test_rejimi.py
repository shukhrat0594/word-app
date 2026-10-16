from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parentsbot', '0008_darhol_xabarlar'),
    ]

    operations = [
        migrations.AddField(
            model_name='parentsbotsozlama',
            name='test_rejimi',
            field=models.CharField(choices=[('ochiq', "O'chiq"), ('darhol', 'Darhol'), ('yigma', "Kunlik yig'mada")], default='darhol', max_length=6),
        ),
    ]
