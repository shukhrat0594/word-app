from django.apps import AppConfig


class OtabotConfig(AppConfig):
    """Ota-ona nazorati boti (Telegram, @UtmostParentsBot).

    Alohida ilova: LMS (`accounts`, `academics`...) va `crm` ma'lumotlarini O'QIYDI,
    lekin ular `parentsbot`ga bog'liq emas. Bot Railway'da alohida jarayon sifatida
    ishlaydi: `python manage.py parentsbot`.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "parentsbot"
    verbose_name = "Ota-ona nazorati"
