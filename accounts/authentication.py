"""Owner uchun "Ko'rish rejimi" (View As) — 2026-07-29.

Owner profil sahifasida Owner/Admin/Talaba/Mehmon orasida tanlaydi.
Bu FAQAT ko'rinish emas — TO'LIQ simulyatsiya: owner saytni HAQIQATAN
tanlangan rol sifatida ko'radi (masalan Talaba tanlansa, Unit qulfi
HAQIQATAN ishlaydi, admin tugmalari ko'rinmaydi, Kurslar bo'limi Mehmon
uchun butunlay yopiq bo'ladi va h.k.) — chunki butun kod bazasi (courses,
exercises, assessment...) `request.user.role`/`owner_mi(request.user)`
orqali tekshiradi, biz esa shu ikkalasini SO'ROV BOSHIDA almashtiramiz.

Nega markazlashgan joyda (har alohida view'da emas): loyihada o'nlab
joy `user.role`/`is_superuser` tekshiradi. Ularning HAMMASINI qidirib
o'zgartirish xato qilish xavfini oshiradi. Buning o'rniga BITTA joyda —
autentifikatsiya bosqichida — `request.user` ustida almashtirib qo'yamiz,
shundan keyin butun ilova hech narsani bilmay, oddiy holatdagidek ishlaydi.

MUHIM XAVFSIZLIK QOIDASI: bu almashtirish FAQAT XOTIRADA (Python
ob'ekti ustida), bazaga HECH QACHON yozilmaydi. Agar shu so'rov davomida
kimdir `request.user.save()` chaqirsa, SOXTA rol/is_superuser bazaga
yozilib qolar edi — shuning uchun (a) bu klass ehtiyotkorlik bilan faqat
`role`/`is_staff`/`is_superuser`ni almashtiradi (boshqa maydonlarga
tegmaydi) va (b) "Ko'rish rejimi"ni O'ZGARTIRISH endpointi (profil
sahifasidagi tugmalar) HECH QACHON `request.user`ni to'g'ridan-to'g'ri
saqlamaydi — bazadan YANGI nusxa olib, faqat `korish_rejimi` maydonini
`update_fields` bilan yozadi (`accounts/views.py: KorishRejimiView`).

Owner simulyatsiyada "qulflanib qolmasligi" uchun: haqiqiy owner
ekanligi `user._asl_owner_mi = True` sifatida SAQLAB QOLINADI (bu
maydon modelda emas, faqat shu so'rov uchun Python ob'ektida). Frontend
va `KorishRejimiView` shu belgiga qaraydi — `owner_mi()`/`is_superuser`
emas (ular simulyatsiya paytida ATAYLAB yolg'on qaytaradi)."""

import time
import threading

from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Markaz, User

# ── "Oxirgi faollik" (2026-09-03) ─────────────────────────────────────
# NEGA MIDDLEWARE EMAS: middleware'da `request.user` hali mavjud
# emas, JWT'ni QAYTA hal qilish kerak bo'lardi — bu har so'rovda
# qo'shimcha token dekodi VA foydalanuvchi so'rovi. Bu yer esa
# autentifikatsiya bosqichi: foydalanuvchi allaqachon qo'lda, ya'ni
# qo'shimcha xarajat faqat bitta kichik UPDATE.
#
# Va u ham har so'rovda emas: har foydalanuvchi uchun DAQIQADA BIR
# MARTA. Jarayon qayta ishga tushsa hisoblagich nolga qaytadi — bu
# muammo emas, shunchaki bitta qo'shimcha UPDATE.
FAOLLIK_ORALIGI_SEK = 60
_faollik_vaqti = {}
_faollik_qulfi = threading.Lock()


def faollikni_belgila(user):
    """Foydalanuvchining `oxirgi_faollik` maydonini yangilaydi (daqiqada
    bir martadan ko'p emas). `update` ishlatiladi — `save()` emas:
    "Ko'rish rejimi" simulyatsiyasida `request.user` ustidagi soxta
    rol bazaga yozilib qolmasin (shu fayl boshidagi xavfsizlik
    qoidasiga qara)."""
    hozir = time.monotonic()
    with _faollik_qulfi:
        oxirgi = _faollik_vaqti.get(user.pk, 0)
        if hozir - oxirgi < FAOLLIK_ORALIGI_SEK:
            return
        _faollik_vaqti[user.pk] = hozir
    try:
        User.objects.filter(pk=user.pk).update(oxirgi_faollik=timezone.now())
    except Exception:  # noqa: BLE001 — faollik yozuvi hech qachon so'rovni buzmasin
        pass


def asl_owner_mi(user):
    """Simulyatsiyadan MUSTAQIL — haqiqatan owner (superuser) ekanini
    tekshiradi. Faqat "Ko'rish rejimi"ni o'zgartirish/o'chirish kabi
    amallar uchun ishlatiladi — oddiy ruxsat tekshiruvlari esa
    `accounts.permissions.owner_mi()` (simulyatsiyaga BO'YSUNADIGAN)
    dan foydalanishda davom etadi."""
    return getattr(user, "_asl_owner_mi", user.is_superuser)


class KorishRejimliJWTAuthentication(JWTAuthentication):
    """Standart JWT autentifikatsiyasini o'raydi — owner uchun "Ko'rish
    rejimi" faol bo'lsa, `request.user`ni SO'ROV DAVOMIDA (xotirada)
    tanlangan rolga moslab qo'yadi."""

    def authenticate(self, request):
        natija = super().authenticate(request)
        if natija is None:
            return None
        user, token = natija
        faollikni_belgila(user)

        if not user.is_superuser:
            # 2026-08-15: "Kirish cheklovi" — owner'dan boshqa hamma
            # DARHOL chiqarib yuboriladi. Tekshiruv AYNAN shu yerda
            # (har so'rovda), faqat login'da emas: aks holda allaqachon
            # kirib turgan (faol seansdagi) foydalanuvchilar cheklov
            # yoqilganidan keyin ham ishlashda davom etardi.
            # `is_superuser` bu nuqtada HALI haqiqiy qiymat ("Ko'rish
            # rejimi" simulyatsiyasi pastda, undan keyin) — ya'ni owner
            # talaba rolini sinayotgan bo'lsa ham qulflanib qolmaydi.
            markaz = Markaz.objects.first()
            if markaz and markaz.kirish_cheklangan:
                raise AuthenticationFailed(
                    {"detail": "Saytga kirish vaqtincha cheklangan",
                     "kod": "kirish_cheklangan"},
                    code="kirish_cheklangan",
                )
            return user, token  # oddiy foydalanuvchilarga tegilmaydi

        rejim = user.korish_rejimi or User.KorishRejimi.OWNER
        if rejim == User.KorishRejimi.OWNER:
            return user, token  # owner o'z holicha ko'rmoqda — simulyatsiya o'chiq

        # Haqiqiy owner ekanini SAQLAB QOLAMIZ (pastda is_superuser
        # yolg'on qilib qo'yilishidan OLDIN) — aks holda owner o'zini
        # qaytadan Owner qilib qo'ya olmay qoladi.
        user._asl_owner_mi = True
        user.role = rejim
        user.is_staff = False
        user.is_superuser = False
        return user, token
