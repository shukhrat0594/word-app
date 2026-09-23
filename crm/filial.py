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
    if int(filial_id) not in s:
        raise ValueError("Bu filialga ruxsatingiz yo'q")


def guruh_q(user, prefix=""):
    """Guruh querysetlari uchun (`prefix` — masalan `"azolik__guruh__"`)."""
    return filial_q(user, f"{prefix}moliya__filial")


def guruh_tekshir(user, guruh):
    moliya = getattr(guruh, "moliya", None)
    if not filial_korinadimi(user, moliya.filial_id if moliya else None):
        raise Http404


def talaba_korinadimi(user, talaba_id):
    """Talabaning filiali — uning guruhlaridan (yoki hisoblaridan).
    Hech qaysi guruhda yo'q talaba hammaga ko'rinadi."""
    s = ruxsat_filiallari(user)
    if s is None:
        return True
    from academics.models import GuruhAzoligi

    from .models import Hisob

    azoliklar = GuruhAzoligi.objects.filter(talaba_id=talaba_id)
    if not azoliklar.exists():
        return True
    return (
        azoliklar.filter(guruh_q(user, "guruh__")).exists()
        or Hisob.objects.filter(talaba_id=talaba_id, filial_id__in=s).exists()
    )


def talaba_tekshir(user, talaba_id):
    if not talaba_korinadimi(user, talaba_id):
        raise Http404


def lid_tekshir(user, lid):
    if not filial_korinadimi(user, lid.filial_id):
        raise Http404


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
    idlar = set(profil.filiallar.values_list("id", flat=True))
    return not idlar or bool(idlar & s)


def _guruh_orqali(user, guruh_id):
    if guruh_id is None:
        return
    from academics.models import Guruh

    guruh = Guruh.objects.select_related("moliya").filter(pk=guruh_id).first()
    if guruh is not None:
        guruh_tekshir(user, guruh)


def obyekt_tekshir(user, turi, pk):
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
        talaba_tekshir(user, pk)
    elif turi == "lid":
        lid = m.Lid.objects.filter(pk=pk).first()
        if lid is not None:
            lid_tekshir(user, lid)
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
