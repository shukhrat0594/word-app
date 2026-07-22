"""Mavjud (deploy vaqtida allaqachon bazada bo'lgan) 'public' mashqlarni AI
tomonidan yaratilgan deb belgilaydi — bu bosqichgacha barcha `korinish=public`
mashqlar faqat seed management-buyruqlar (wordapp_import va h.k.) orqali
yaratilgan, admin UI orqali qo'lda kiritilgan mashqlar hammasi `private`
edi (2026-07-22 tekshirilgan holat). Shundan keyin yaratiladigan yangi
`public` mashqlar (admin UI orqali qo'lda ham public qilib belgilanishi
mumkin) bu migratsiyaga ta'sir qilmaydi — faqat bir martalik orqaga
moslashtirish."""

from django.db import migrations


def belgila(apps, schema_editor):
    Mashq = apps.get_model("exercises", "Mashq")
    Mashq.objects.filter(korinish="public").update(sun_iy_intellekt_yaratgan=True)


def orqaga(apps, schema_editor):
    Mashq = apps.get_model("exercises", "Mashq")
    Mashq.objects.filter(sun_iy_intellekt_yaratgan=True).update(sun_iy_intellekt_yaratgan=False)


class Migration(migrations.Migration):

    dependencies = [
        ("exercises", "0008_mashq_sun_iy_intellekt_yaratgan"),
    ]

    operations = [
        migrations.RunPython(belgila, orqaga),
    ]
