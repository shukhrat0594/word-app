from django.apps import AppConfig


class CrmConfig(AppConfig):
    """CRM (moliya) ilovasi — LMS'dan ATAYLAB ajratilgan.

    `ready()`da signal ulash yoki LMS modellariga tegish mumkin emas
    (TZ 3.0, 3-qoida). Sabab — signal ko'rinmas bog'lanish: CRM
    o'chirilganda uni olib tashlash esdan chiqadi va sababi topilmaydigan
    xato beradi. CRM'ning kengaytma yozuvlari (`GuruhMoliya`,
    `AzolikMoliya`) signal bilan emas, kerak bo'lgan joyda `get_or_create`
    bilan paydo bo'ladi.

    YAGONA istisno (2026-09-25): accounts'ning "saytdan o'chirilmaydiganlar"
    ro'yxatiga CRM talabasi tekshiruvi qo'shiladi (`crm/sayt_hisobi.py`).
    Bu signal emas va LMS modeliga tegmaydi — oddiy funksiya ro'yxati; CRM
    olib tashlansa u bilan birga yo'qoladi, sayt avvalgidek ishlaydi.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "crm"
    verbose_name = "CRM / Moliya"

    def ready(self):
        from accounts.savat import SAYTDAN_OCHIRILMAYDIGANLAR

        from .sayt_hisobi import crm_talabalari

        if crm_talabalari not in SAYTDAN_OCHIRILMAYDIGANLAR:
            SAYTDAN_OCHIRILMAYDIGANLAR.append(crm_talabalari)
