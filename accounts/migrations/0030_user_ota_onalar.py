from django.db import migrations, models


def fk_dan_kochir(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for talaba in User.objects.filter(ota_ona__isnull=False).only("id", "ota_ona_id"):
        talaba.ota_onalar.add(talaba.ota_ona_id)


def m2m_dan_qaytar(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for talaba in User.objects.filter(ota_onalar__isnull=False).distinct():
        talaba.ota_ona_id = talaba.ota_onalar.order_by("id").values_list("id", flat=True).first()
        talaba.save(update_fields=["ota_ona"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0029_qurilma_sorovi"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="ota_onalar",
            field=models.ManyToManyField(
                blank=True,
                help_text="Faqat 'Talaba' roli uchun — kuzatuvchi ota-onalar (bir nechta bo'lishi mumkin)",
                limit_choices_to={"role": "parent"},
                related_name="farzandlar_yangi",
                to="accounts.user",
            ),
        ),
        migrations.RunPython(fk_dan_kochir, m2m_dan_qaytar),
        migrations.RemoveField(model_name="user", name="ota_ona"),
        migrations.AlterField(
            model_name="user",
            name="ota_onalar",
            field=models.ManyToManyField(
                blank=True,
                help_text="Faqat 'Talaba' roli uchun — kuzatuvchi ota-onalar (bir nechta bo'lishi mumkin)",
                limit_choices_to={"role": "parent"},
                related_name="farzandlar",
                to="accounts.user",
            ),
        ),
    ]
