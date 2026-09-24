"""Filial bo'yicha cheklov (2026-09-23, Shuhrat).

Xodimga filial(lar) biriktirilgan bo'lsa — CRM'da FAQAT o'sha filiallar
ma'lumotini ko'radi. Qoida BITTA joyda (shu modul) — har bir view o'z
so'rovini shu yerdagi funksiyalar bilan toraytiradi.

Qarorlar:
  * owner (saytdagi owner = CRM'dagi CEO) — hech qanday cheklov yo'q;
  * filial biriktirilmagan xodim — hozircha hamma filialni ko'radi;
  * filiali yo'q ma'lumot (guruhsiz o'quvchi, filialsiz lid/guruh/hisob)
    hammaga ko'rinadi;
  * cheklov SERVERDA: `?filial=` filtri ustiga qo'yiladi (AND), ya'ni
    boshqa filial ID'si yuborilsa bo'sh natija; ID bo'yicha ochishda —
    404 (yozuv borligini ham oshkor qilmaydi).
"""

from django.db.models import Q
from django.http import Http404

from accounts.permissions import owner_mi

_KESH = "_crm_filiallar_kesh"


def ruxsat_filiallari(user):
    """`None` — cheklovsiz; aks holda ko'rish mumkin bo'lgan filial ID'lari."""
    if user is None or not user.is_authenticated:
        return set()
    if hasattr(user, _KESH):
        return getattr(user, _KESH)
    natija = None
    if not owner_mi(user):
        profil = getattr(user, "crm_xodim", None)
        if profil is not None:
            idlar = set(profil.filiallar.values_list("id", flat=True))
            natija = idlar or None
    # Bitta so'rov ichida bir necha marta chaqiriladi — foydalanuvchi
    # obyekti har so'rovda yangidan olinadi (JWT), kesh eskirmaydi.
    setattr(user, _KESH, natija)
    return natija


def cheklanganmi(user):
    return ruxsat_filiallari(user) is not None


def filial_q(user, yol, filialsiz_ham=True):
    """`yol` (masalan `"moliya__filial"`) bo'yicha ruxsat filtri.
    `filialsiz_ham` — filiali yo'q yozuv ham ko'rinadi (qaror)."""
    s = ruxsat_filiallari(user)
    if s is None:
        return Q()
    q = Q(**{f"{yol}__in": s})
    if filialsiz_ham:
        q |= Q(**{f"{yol}__isnull": True})
    return q


def filial_korinadimi(user, filial_id):
    s = ruxsat_filiallari(user)
    return s is None or filial_id is None or filial_id in s


def filial_tekshir(user, filial_id):
    """Yangi yozuvga filial tanlanganda: cheklangan xodim faqat o'z
    filialini tanlaydi va filialsiz qoldira olmaydi (aks holda yozuv
    "hammaniki" bo'lib ketardi). Xato bo'lsa ValueError."""
    s = ruxsat_filiallari(user)
    if s is None:
        return
    if not filial_id:
        raise ValueError("Filialni tanlang")
    try:
        filial_id = int(filial_id)
    except (TypeError, ValueError):
        raise ValueError("Filial noto'g'ri") from None
    if filial_id not in s:
        raise ValueError("Bu filialga ruxsatingiz yo'q")


def guruh_q(user, prefix=""):
    """Guruh querysetlari uchun (`prefix` — masalan `"azolik__guruh__"`)."""
    return filial_q(user, f"{prefix}moliya__filial")


def tolov_q(user, prefix=""):
    """To'lov filtri. Filial — HISOBDAN (u yaratilgan paytdagi snapshot),
    hisobsiz to'lovda (qaytarish, avans) — guruhdan. Faqat guruhga
    qaralsa, guruhi o'chirilgan to'lov (`guruh=NULL`) "filialsiz" bo'lib
    hamma filialga ko'rinardi; guruh boshqa filialga ko'chsa esa to'lov
    hisob bilan boshqa-boshqa filialda chiqardi."""
    if ruxsat_filiallari(user) is None:
        return Q()
    return (
        (Q(**{f"{prefix}hisob__isnull": False}) & filial_q(user, f"{prefix}hisob__filial"))
        | (Q(**{f"{prefix}hisob__isnull": True}) & guruh_q(user, f"{prefix}guruh__"))
    )


def tolov_filiali_q(filial_id, prefix=""):
    """`?filial=` tanlovi — `tolov_q` bilan bir xil qoida."""
    return (
        Q(**{f"{prefix}hisob__isnull": False, f"{prefix}hisob__filial_id": filial_id})
        | Q(**{f"{prefix}hisob__isnull": True, f"{prefix}guruh__moliya__filial_id": filial_id})
    )


def guruh_tekshir(user, guruh):
    moliya = getattr(guruh, "moliya", None)
    if not filial_korinadimi(user, moliya.filial_id if moliya else None):
        raise Http404


def talaba_korinadimi(user, talaba_id, oqish=False):
    """Talabaning filiali — uning guruhlaridan (yoki hisoblaridan).
    Hech qaysi guruhda yo'q talaba hammaga ko'rinadi.

    `oqish=True` — qora ro'yxatdagi o'quvchi HAMMA filialga ko'rinadi
    (Shuhrat, 2026-09-23, lidlardagi kabi); o'zgartirish — o'z filialida."""
    s = ruxsat_filiallari(user)
    if s is None:
        return True
    try:
        talaba_id = int(talaba_id)
    except (TypeError, ValueError):
        return False
    from academics.models import GuruhAzoligi

    from .models import Hisob, TalabaProfil

    if oqish and TalabaProfil.objects.filter(user_id=talaba_id, qora_royxat=True).exists():
        return True

    azoliklar = GuruhAzoligi.objects.filter(talaba_id=talaba_id)
    if not azoliklar.exists():
        return True
    return (
        azoliklar.filter(guruh_q(user, "guruh__")).exists()
        or Hisob.objects.filter(talaba_id=talaba_id, filial_id__in=s).exists()
    )


def talaba_tekshir(user, talaba_id, oqish=False):
    if not talaba_korinadimi(user, talaba_id, oqish=oqish):
        raise Http404


def talaba_boshqa_filialda(user, talaba_id):
    """Cheklangan xodim uchun: talabaning ko'rinmaydigan filialda hisobi
    yoki to'lovi bormi. Kartada umumiy balans yonida belgi (summasiz)
    chiqadi — "boshqa filialda ham hisobi bor" (Shuhrat qarori)."""
    if ruxsat_filiallari(user) is None:
        return False
    from .models import Hisob, Tolov

    return (
        Hisob.objects.filter(talaba_id=talaba_id).exclude(filial_q(user, "filial")).exists()
        or Tolov.objects.filter(talaba_id=talaba_id).exclude(tolov_q(user)).exists()
    )


def talaba_guruhga_bogliqmi(talaba_id, guruh_id):
    """Pul yozuvi (to'lov, qo'lda hisob) faqat shu guruhda o'qigan
    talabaga: hozir a'zo, yoki shu guruhda hisobi / chiqish yozuvi bor
    (guruhdan chiqib, qarzi qolgan). Aks holda istalgan talabaga — shu
    jumladan boshqa filialnikiga — o'z guruhi orqali pul yozilardi."""
    from academics.models import GuruhAzoligi

    from .models import GuruhdanChiqish, Hisob

    return (
        GuruhAzoligi.objects.filter(talaba_id=talaba_id, guruh_id=guruh_id).exists()
        or Hisob.objects.filter(talaba_id=talaba_id, guruh_id=guruh_id).exists()
        or GuruhdanChiqish.objects.filter(talaba_id=talaba_id, guruh_id=guruh_id).exists()
    )


def lid_tekshir(user, lid, oqish=False):
    """`oqish=True` — qora ro'yxatdagi lid HAMMA filialga ko'rinadi
    (Shuhrat, 2026-09-23: boshqa filialga "yomon" mijoz qayta yozilmasin);
    uni o'zgartirish esa baribir faqat o'z filialida."""
    if oqish and lid.qora_royxat:
        return
    if not filial_korinadimi(user, lid.filial_id):
        raise Http404


def umumiy_yozuv_taqiq(user, filial_id, nima):
    """Filialsiz (hamma filialga umumiy) yozuvni — lid doskasi yoki
    ustunini — filialga bog'langan xodim o'zgartira/o'chira olmaydi:
    bu boshqa filiallarga ham ta'sir qiladi. Xato bo'lsa ValueError."""
    if filial_id is None and cheklanganmi(user):
        raise ValueError(f"Umumiy {nima} barcha filiallarga tegishli — uni filialga bog'lanmagan xodim o'zgartiradi")


def eslatma_tekshir(user, eslatma):
    if eslatma.guruh_id:
        guruh_tekshir(user, eslatma.guruh)
    if eslatma.talaba_id:
        talaba_tekshir(user, eslatma.talaba_id)
    if eslatma.lid_id:
        lid_tekshir(user, eslatma.lid)


def xodim_korinadimi(user, xodim_user):
    """Xodim — filiallari ruxsat to'plami bilan kesishsa yoki filiali
    umuman yo'q bo'lsa ko'rinadi."""
    s = ruxsat_filiallari(user)
    if s is None:
        return True
    profil = getattr(xodim_user, "crm_xodim", None)
    if profil is None:
        return True
    # `.all()` — ro'yxatlarda `prefetch_related("crm_xodim__filiallar")`
    # keshidan olinadi (`values_list` har xodimga alohida so'rov edi).
    idlar = {f.id for f in profil.filiallar.all()}
    return not idlar or bool(idlar & s)


def _guruh_orqali(user, guruh_id):
    if guruh_id is None:
        return
    from academics.models import Guruh

    guruh = Guruh.objects.select_related("moliya").filter(pk=guruh_id).first()
    if guruh is not None:
        guruh_tekshir(user, guruh)


def obyekt_tekshir(user, turi, pk, oqish=False):
    """URL'dagi `pk` bo'yicha yozuv shu foydalanuvchi filialiga tegishlimi.
    `CrmView` view'dagi `pk_turi` e'loniga qarab chaqiradi — har view'da
    alohida yozilsa, bittasi esdan chiqib, boshqa filial ma'lumoti ID
    orqali "sizib" chiqardi. Yozuv yo'q bo'lsa — jim (view o'zi 404 beradi)."""
    if ruxsat_filiallari(user) is None:
        return
    from academics.models import Guruh

    from . import models as m

    if turi == "guruh":
        guruh = Guruh.objects.select_related("moliya").filter(pk=pk).first()
        if guruh is not None:
            guruh_tekshir(user, guruh)
    elif turi == "talaba":
        talaba_tekshir(user, pk, oqish=oqish)
    elif turi == "lid":
        lid = m.Lid.objects.filter(pk=pk).first()
        if lid is not None:
            lid_tekshir(user, lid, oqish=oqish)
    elif turi == "azolik":
        am = m.AzolikMoliya.objects.select_related("azolik").filter(pk=pk).first()
        if am is not None:
            _guruh_orqali(user, am.azolik.guruh_id)
    elif turi == "chegirma":
        c = m.Chegirma.objects.select_related("azolik__azolik").filter(pk=pk).first()
        if c is not None:
            _guruh_orqali(user, c.azolik.azolik.guruh_id)
    elif turi == "dars_ozgarish":
        oz = m.DarsOzgarish.objects.filter(pk=pk).first()
        if oz is not None:
            _guruh_orqali(user, oz.guruh_id)
    elif turi == "hisob":
        h = m.Hisob.objects.filter(pk=pk).first()
        if h is not None and not filial_korinadimi(user, h.filial_id):
            raise Http404
    elif turi == "tolov":
        t = m.Tolov.objects.select_related("hisob").filter(pk=pk).first()
        if t is not None:
            if t.hisob_id and not filial_korinadimi(user, t.hisob.filial_id):
                raise Http404
            _guruh_orqali(user, t.guruh_id)
    elif turi == "eslatma":
        e = m.Eslatma.objects.select_related("guruh__moliya", "lid").filter(pk=pk).first()
        if e is not None:
            eslatma_tekshir(user, e)
    elif turi == "lid_doska":
        d = m.LidDoska.objects.filter(pk=pk).first()
        if d is not None and not filial_korinadimi(user, d.filial_id):
            raise Http404
    elif turi == "lid_bolim":
        b = m.LidBolim.objects.filter(pk=pk).first()
        if b is not None and not filial_korinadimi(user, b.filial_id):
            raise Http404
    elif turi == "xodim":
        from accounts.models import User

        xodim = User.objects.filter(pk=pk).first()
        if xodim is not None and not xodim_korinadimi(user, xodim):
            raise Http404
    else:
        raise ValueError(f"Noma'lum pk_turi: {turi}")
