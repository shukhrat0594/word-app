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
        ("lidlar.ochirish", "O'chirish"),
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
        ("moliya.hisob", "Qarzdorlik yozuvlari"),
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

# Maxsus rol berilmagan xodimning standart ruxsatlari (lavozim bo'yicha).
# Administrator va CEO — hammasi. O'qituvchi CRM'ga KIRMAYDI: u LMS'da
# ishlaydi (davomat, mashqlar), CRM pul va boshqaruv uchun.
_STANDART = {
    "kassir": ["bosh_sahifa", "talabalar", "moliya"],
    "marketolog": ["bosh_sahifa", "lidlar"],
    "watcher": ["bosh_sahifa", "hisobotlar"],
}


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


def ruxsatlar(user):
    """Foydalanuvchining CRM ruxsatlari to'plami (bo'sh = CRM yopiq)."""
    if not user or not user.is_authenticated:
        return set()
    if owner_mi(user) or user.role == User.Role.ADMIN:
        return set(BARCHA_KALITLAR)
    profil = getattr(user, "crm_xodim", None)
    if profil is None or not user.is_active:
        return set()
    if profil.rol_id and profil.rol.faol:
        return _kengaytir(profil.rol.ruxsatlar)
    if profil.lavozim in ("admin", "ceo"):
        return set(BARCHA_KALITLAR)
    return _kengaytir(_STANDART.get(profil.lavozim, []))


def lms_roli(lavozim):
    """Xodim lavozimidan LMS roli. Faqat o'qituvchi va administrator
    saytda maxsus huquq oladi; kassir/marketolog va h.k. — "oddiy",
    ya'ni saytda boshqaruv yo'q, CRM'ga rol ruxsatlari bilan kiradi."""
    if lavozim in ("oqituvchi", "support"):
        return User.Role.TEACHER
    if lavozim in ("admin", "ceo"):
        return User.Role.ADMIN
    return User.Role.ODDIY
