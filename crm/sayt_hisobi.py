"""Saytdagi "O'chirish" CRM o'quvchisini O'CHIRMAYDI (Shuhrat, 2026-09-25).

Sayt hisobi va CRM talabasi — bitta `accounts.User` yozuvi. Sayt admini
uni o'chirsa, CRM'dagi guruh a'zoligi, moliya va tarix ham ketardi. Shu
sababli CRM'ga tegishli talabaning faqat saytga kirishi yopiladi
(`accounts.savat.sayt_kirishini_yop`).

Tekshiruv accounts'ning ro'yxatiga `apps.CrmConfig.ready()` da qo'shiladi:
bog'lanish yo'nalishi saqlanadi (crm -> LMS), CRM olib tashlansa u o'zi
yo'qoladi.
"""

from django.db.models import Q

from academics.models import GuruhAzoligi
from accounts.models import User


def crm_talabalari(user_idlar):
    """Berilganlardan CRM'ga tegishli talabalar: CRM profili, CRM guruhidagi
    a'zolik, pul yozuvi, guruhdan chiqish yozuvi yoki liddan kelgani bor."""
    from .models import GuruhdanChiqish, Hisob, Lid, TalabaProfil, Tolov

    idlar = set(User.objects.filter(pk__in=list(user_idlar), role=User.Role.STUDENT).values_list("pk", flat=True))
    if not idlar:
        return set()
    topildi = set()
    for qs, maydon in (
        (TalabaProfil.objects.filter(user_id__in=idlar), "user_id"),
        (GuruhAzoligi.objects.filter(talaba_id__in=idlar).filter(
            Q(moliya__isnull=False) | Q(guruh__moliya__isnull=False)), "talaba_id"),
        (Hisob.objects.filter(talaba_id__in=idlar), "talaba_id"),
        (Tolov.objects.filter(talaba_id__in=idlar), "talaba_id"),
        (GuruhdanChiqish.objects.filter(talaba_id__in=idlar), "talaba_id"),
        (Lid.objects.filter(talaba_id__in=idlar), "talaba_id"),
    ):
        topildi |= set(qs.values_list(maydon, flat=True))
    return topildi
