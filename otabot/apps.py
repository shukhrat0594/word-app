from django.apps import AppConfig


class OtabotConfig(AppConfig):
    """Ota-ona nazorati boti (Telegram, @UtmostParentsBot).

    Alohida ilova: LMS (`accounts`, `academics`...) va `crm` ma'lumotlarini O'QIYDI,
    lekin ular `otabot`ga bog'liq emas. Bot Railway'da alohida jarayon sifatida
    ishlaydi: `python manage.py otabot`.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "otabot"
    verbose_name = "Ota-ona boti"
