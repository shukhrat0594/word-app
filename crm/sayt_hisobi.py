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


def saytdan_chiqarildi(azolik, kim):
    """Talaba SAYTdagi Guruhlar sahifasidan olib tashlanmoqda (`academics.views` ilgagi).

    2026-11-09: avval a'zolik shunchaki o'chardi — joriy oy hisobi to'liq qarz bo'lib
    qolar, "Ketgan o'quvchilar"da esa iz qolmasdi. Endi CRM'dagi "Guruhdan chiqarish"
    bilan bir xil yo'l: hisob bugungi kungacha qayta hisoblanadi va chiqish yozuvi
    qoladi. CRM bu guruhni bilmasa (moliyasi yo'q) yoki o'chirilgan bo'lsa — tegilmaydi."""
    from django.conf import settings
    from django.utils import timezone

    if not getattr(settings, "CRM_YOQILGAN", False):
        return
    from .models import AzolikMoliya, GuruhdanChiqish

    if getattr(azolik.guruh, "moliya", None) is None:
        return
    if getattr(azolik, "moliya", None) is None:
        # Hali CRM ochilmagan — yozuv `mantiq._moliyasiz_azoliklarni_och` qoidasi bilan.
        AzolikMoliya.objects.get_or_create(
            azolik=azolik, defaults={"boshlanish_sana": timezone.localtime(azolik.created_at).date()}
        )
        azolik.refresh_from_db()
    from .boshqaruv import guruhdan_chiqar

    guruhdan_chiqar(kim, azolik, timezone.localdate(), GuruhdanChiqish.SababTuri.BOSHQA,
                    "Saytdagi Guruhlar sahifasidan olib tashlandi")


def guruh_saytda_qaytarildi(guruh):
    """Arxivlangan guruh SAYTda qayta faollashtirildi — `mantiq.guruh_arxivdan_qaytganda`."""
    from django.conf import settings

    if not getattr(settings, "CRM_YOQILGAN", False):
        return
    from . import mantiq

    mantiq.guruh_arxivdan_qaytganda(guruh)


def talabani_tahrirlay_oladi(user, talaba_id):
    """CRM xodimi: "o'quvchini tahrirlash" ruxsati bor va talaba uning
    filialiga ko'rinadi. Saytdagi `PATCH /api/talabalar/<id>/` uchun."""
    from .filial import talaba_korinadimi
    from .ruxsatlar import ruxsatlar

    return "talabalar.tahrirlash" in ruxsatlar(user) and talaba_korinadimi(user, talaba_id)
