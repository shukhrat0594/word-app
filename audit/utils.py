from .models import FaoliyatYozuvi


def _markaz_of(user, obyekt):
    """Yozuvni qaysi markazga bog'lash kerakligini aniqlaydi — avval obyektning
    o'zidagi markaz, bo'lmasa harakatni bajargan foydalanuvchining markazi."""
    for manba in (obyekt, user):
        markaz = getattr(manba, "markaz", None)
        if markaz is not None:
            return markaz
    if obyekt.__class__.__name__ == "Markaz":
        return obyekt
    return None


def maydon_diff(eski_qiymatlar: dict, yangi_qiymatlar: dict) -> dict:
    """Ikki {maydon: qiymat} lug'atini solishtirib, faqat o'zgargan
    maydonlarni {maydon: {"eski":..., "yangi":...}} shaklida qaytaradi."""
    diff = {}
    for maydon, yangi in yangi_qiymatlar.items():
        eski = eski_qiymatlar.get(maydon)
        if eski != yangi:
            diff[maydon] = {"eski": eski, "yangi": yangi}
    return diff


def logla(
    *,
    foydalanuvchi,
    harakat,
    obyekt,
    obyekt_turi,
    obyekt_nomi=None,
    eski_qiymatlar=None,
    yangi_qiymatlar=None,
    snapshot=None,
    ozgarishlar=None,
):
    """Bitta audit yozuvini yaratadi.

    - `yaratish`/`ochirish` uchun `snapshot` (to'liq holat) beriladi.
    - `ozgartirish` uchun odatda `eski_qiymatlar`+`yangi_qiymatlar` beriladi,
      faqat farq qiladiganlari avtomatik hisoblanib saqlanadi (o'zgarish
      yo'q bo'lsa yozuv yaratilmaydi).
    - Maxfiy maydonlar (parol) uchun tayyor `ozgarishlar` lug'ati to'g'ridan-
      to'g'ri berilishi mumkin (haqiqiy qiymat emas, faqat "amal bajarildi"
      belgisi bilan) — bu holda diff avtomatik hisoblanmaydi.
    """
    if ozgarishlar is not None:
        pass
    elif harakat == FaoliyatYozuvi.Harakat.OZGARTIRISH:
        ozgarishlar = maydon_diff(eski_qiymatlar or {}, yangi_qiymatlar or {})
        if not ozgarishlar:
            return None
    else:
        ozgarishlar = snapshot or {}

    return FaoliyatYozuvi.objects.create(
        foydalanuvchi=foydalanuvchi,
        harakat=harakat,
        obyekt_turi=obyekt_turi,
        obyekt_id=getattr(obyekt, "pk", None),
        obyekt_nomi=(obyekt_nomi or str(obyekt))[:200],
        ozgarishlar=ozgarishlar,
        markaz=_markaz_of(foydalanuvchi, obyekt),
    )
