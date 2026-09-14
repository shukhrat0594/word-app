from django.apps import AppConfig


class CrmConfig(AppConfig):
    """CRM (moliya) ilovasi — LMS'dan ATAYLAB ajratilgan.

    `ready()` QASDDAN bo'sh: bu yerda signal ulash yoki LMS modellariga
    tegish mumkin emas (TZ 3.0, 3-qoida). Sabab — signal ko'rinmas
    bog'lanish: CRM o'chirilganda uni olib tashlash esdan chiqadi va
    sababi topilmaydigan xato beradi. CRM'ning kengaytma yozuvlari
    (`GuruhMoliya`, `AzolikMoliya`) signal bilan emas, kerak bo'lgan
    joyda `get_or_create` bilan paydo bo'ladi.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "crm"
    verbose_name = "CRM / Moliya"
