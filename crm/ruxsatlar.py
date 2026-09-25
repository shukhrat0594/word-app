"""CRM ruxsatlari daraxti va foydalanuvchining ruxsatlarini aniqlash
(video-TZ, 2026-09-23 — SoffCRM "Yangi rol yaratish" oynasi).

Daraxt ikki qavatli: bo'lim ("lidlar") -> amallar ("lidlar.excel").
Backend BO'LIM darajasida tekshiradi (`CrmRuxsati`), amal kalitlari
frontendda tugmalarni yashirish uchun. Pulni o'chirish/tuzatish kabi
xavfli amallar baribir alohida `FaqatOwner` bilan himoyalangan.
"""

from accounts.models import User
from accounts.permissions import owner_mi

# (kalit, nomi, [(kichik_kalit, nomi), ...]) — tartib interfeysdagi tartib.
RUXSAT_DARAXTI = [
    ("bosh_sahifa", "Bosh sahifa", [
        ("bosh_sahifa.faol_lidlar", "Faol lidlar"),
        ("bosh_sahifa.faol_talabalar", "Faol talabalar"),
        ("bosh_sahifa.markaz_foydaliligi", "Markaz foydaliligi"),
        ("bosh_sahifa.qarzdorlar", "Qarzdorlar"),
        ("bosh_sahifa.moliya", "Moliya ko'rsatkichlari"),
        ("bosh_sahifa.dars_jadvali", "Dars jadvali"),
    ]),
    ("lidlar", "Lidlar", [
        ("lidlar.qoshish", "Yangi qo'shish"),
        ("lidlar.guruhga", "Guruhga qo'shish"),
        ("lidlar.arxiv", "Arxiv"),
        ("lidlar.bolim", "Bo'lim yaratish"),
        ("lidlar.tahrirlash", "Tahrirlash"),
        ("lidlar.excel", "Excel"),
        ("lidlar.qora_royxat", "Qora ro'yxat"),
    ]),
    ("guruhlar", "Guruhlar", [
        ("guruhlar.qoshish", "Guruh qo'shish"),
        ("guruhlar.tahrirlash", "Tahrirlash"),
        ("guruhlar.davomat", "Davomat belgilash"),
        ("guruhlar.talaba_qoshish", "Guruhga o'quvchi qo'shish"),
        ("guruhlar.chegirma", "Chegirmalar"),
        ("guruhlar.dars_kochirish", "Darsni ko'chirish / qo'shimcha dars"),
    ]),
    ("talabalar", "O'quvchilar", [
        ("talabalar.qoshish", "Yangi o'quvchi"),
        ("talabalar.tahrirlash", "Tahrirlash"),
        ("talabalar.qora_royxat", "Qora ro'yxat"),
        ("talabalar.excel", "Excel"),
    ]),
    ("moliya", "Moliya", [
        ("moliya.tolov", "To'lov qabul qilish"),
        ("moliya.qaytarish", "Pul qaytarish"),
        ("moliya.hisob", "Qarzdorlik yozuvlari (qo'shish va tahrirlash)"),
    ]),
    ("hisobotlar", "Hisobotlar", [
        ("hisobotlar.moliya", "Moliyaviy hisobot"),
        ("hisobotlar.dinamika", "Dinamika"),
        ("hisobotlar.excel", "Excel"),
    ]),
    ("xodimlar", "Xodimlar", [
        ("xodimlar.qoshish", "Xodim qo'shish"),
        ("xodimlar.tahrirlash", "Tahrirlash"),
        ("xodimlar.oylik", "Oylik va ulushni ko'rish"),
    ]),
    ("sozlamalar", "Sozlamalar", [
        ("sozlamalar.filiallar", "Filiallar va xonalar"),
        ("sozlamalar.narxlar", "Kurs narxlari"),
        ("sozlamalar.rollar", "Rollar"),
    ]),
]

BOLIMLAR = [b[0] for b in RUXSAT_DARAXTI]
BARCHA_KALITLAR = set(BOLIMLAR) | {k for _, _, bolalar in RUXSAT_DARAXTI for k, _ in bolalar}

# Maxsus rol berilmagan xodimning BOSHLANG'ICH ruxsatlari (lavozim
# bo'yicha). 2026-09-23 dan ular bazada — tizim rollari (`CrmRol.lavozim`),
# migratsiya 0007 shu ro'yxatdan to'ldiradi va owner keyin tahrirlaydi.
# Bu yerdagi qiymat faqat tizim roli bazada YO'Q bo'lsa ishlaydi.
# Administrator va CEO — hammasi. O'qituvchi CRM'ga KIRMAYDI: u LMS'da
# ishlaydi (davomat, mashqlar), CRM pul va boshqaruv uchun.
_STANDART = {
    "admin": BOLIMLAR,
    "ceo": BOLIMLAR,
    "kassir": ["bosh_sahifa", "talabalar", "moliya"],
    "marketolog": ["bosh_sahifa", "lidlar"],
    "watcher": ["bosh_sahifa", "hisobotlar"],
}

# Tizim rollari: (lavozim, nomi) — interfeysdagi tartib.
TIZIM_ROLLARI = [
    ("admin", "Administrator"),
    # CEO — tizim roli EMAS: saytdagi owner CRM'da CEO (2026-09-23), unga
    # cheklov yo'q; migratsiya 0009 CEO rolini olib tashlaydi.
    ("kassir", "Kassir"),
    ("marketolog", "Marketolog"),
    ("watcher", "Kuzatuvchi"),
    ("oqituvchi", "O'qituvchi"),
    ("support", "Support teacher"),
    ("boshqa", "Boshqa"),
]


def _kengaytir(kalitlar):
    """Bo'lim kaliti berilgan bo'lsa — uning hamma amallari ham beriladi;
    faqat amal berilgan bo'lsa — bo'limning o'zi ham (aks holda amal
    ochiq, lekin bo'lim yopiq bo'lib qolardi)."""
    natija = set()
    for k in kalitlar or []:
        if k not in BARCHA_KALITLAR:
            continue
        natija.add(k)
        if "." in k:
            natija.add(k.split(".", 1)[0])
    for bolim, _, bolalar in RUXSAT_DARAXTI:
        if bolim in (kalitlar or []):
            natija.update(kk for kk, _ in bolalar)
    return natija


def standart_ruxsatlar(lavozim):
    """Tizim roli uchun boshlang'ich (kengaytirilgan) ruxsatlar."""
    return sorted(_kengaytir(_STANDART.get(lavozim, [])))


def _lavozim(user, profil):
    if profil is not None:
        return profil.lavozim
    # LMS'da yaratilgan, CRM profili yo'q xodimlar.
    if user.role == User.Role.ADMIN:
        return "admin"
    if user.role == User.Role.TEACHER:
        return "oqituvchi"
    return None


_KESH = "_crm_ruxsatlar_kesh"


def ruxsatlar(user):
    """Foydalanuvchining CRM ruxsatlari to'plami (bo'sh = CRM yopiq).

    Tartib: owner — doim hammasi; maxsus rol berilgan bo'lsa — o'sha rol
    (administratorda ham: "Administrator 1" kabi cheklangan rol
    ishlasin); aks holda lavozimning tizim roli (bazada, owner
    tahrirlaydi); u ham bo'lmasa — `_STANDART`.

    Natija foydalanuvchi obyektida keshlanadi: bitta so'rovda 3-4 marta
    chaqiriladi (`CrmRuxsati`, amal tekshiruvlari) va har safar tizim
    rolini bazadan o'qirdi. Foydalanuvchi har so'rovda yangidan olinadi
    (JWT), ya'ni kesh keyingi so'rovga o'tmaydi. Nusxa qaytariladi —
    chaqiruvchi to'plamni o'zgartirsa, kesh buzilmasin.
    """
    if not user or not user.is_authenticated:
        return set()
    if not hasattr(user, _KESH):
        setattr(user, _KESH, _hisobla(user))
    return set(getattr(user, _KESH))


def _hisobla(user):
    if owner_mi(user):
        return set(BARCHA_KALITLAR)
    if not user.is_active:
        return set()
    profil = getattr(user, "crm_xodim", None)
    if profil is not None and profil.rol_id and profil.rol.faol and not profil.rol.lavozim:
        return _kengaytir(profil.rol.ruxsatlar)
    lavozim = _lavozim(user, profil)
    if lavozim is None:
        return set()
    from .models import CrmRol

    tizim = CrmRol.objects.filter(lavozim=lavozim).values_list("ruxsatlar", flat=True).first()
    if tizim is not None:
        return _kengaytir(tizim)
    return _kengaytir(_STANDART.get(lavozim, []))


# Saytda (LMS) faqat CRM xodimiga ko'rinadigan menyu: `korinadigan_panellar`
# ga shu yoziladi — LMS Layout'i `MAJBURIY_PANELLAR` ("/", "/profil")dan
# boshqasini yashiradi. Bo'sh ro'yxat EMAS: LMS API bo'sh ro'yxatni
# "cheklovsiz" deb saqlaydi. Bu faqat MENYU cheklovi (LMS qarori,
# 2026-08-05) — sahifa manzili yoki API'ni yopmaydi.
CRM_XODIM_PANELLARI = ["/"]


def sayt_menyusini_toraytir(user):
    """CRM xodimi (LMS roli "oddiy") saytga kirsa — mehmon menyusi (AI
    mashqlari, o'yinlar, reyting) ko'rinmasin (2026-09-23, Shuhrat).
    O'qituvchi/administratorga o'tsa — biz qo'ygan cheklov olinadi."""
    if user.role == User.Role.ODDIY:
        if not user.korinadigan_panellar:
            user.korinadigan_panellar = list(CRM_XODIM_PANELLARI)
    elif user.korinadigan_panellar == CRM_XODIM_PANELLARI:
        user.korinadigan_panellar = None


def lms_roli(lavozim):
    """Xodim lavozimidan LMS roli. Faqat o'qituvchi va administrator
    saytda maxsus huquq oladi; kassir/marketolog va h.k. — "oddiy",
    ya'ni saytda boshqaruv yo'q, CRM'ga rol ruxsatlari bilan kiradi."""
    if lavozim in ("oqituvchi", "support"):
        return User.Role.TEACHER
    if lavozim in ("admin", "ceo"):
        return User.Role.ADMIN
    return User.Role.ODDIY
