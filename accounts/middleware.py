"""2026-08-15: "Kirish cheklovi" yoqilgan paytda OWNER ham quyidagi
amallarni bajara olmaydi — Railway'ga ko'chirish davrida eski (Render)
saytda tasodifan yangi ma'lumot yaratib/tahrirlab/yechib qo'ymasligi
uchun (foydalanuvchi talabi):

  - IELTS testlari / AI mashqlari / Kurslar — yaratish, tahrirlash,
    o'chirish VA yechish (talaba sifatida ishlash)
  - Guruh, foydalanuvchi (talaba/xodim) — yaratish, tahrirlash
  - "Ko'rish rejimi" (profil turini simulyatsiya qilib almashtirish)

Boshqa ODDIY foydalanuvchilar (owner'dan tashqari) bu paytda umuman
tizimga kira olmaydi (`accounts/authentication.py`) — shuning uchun bu
middleware FAQAT owner'ning o'ziga tegishli.

MUHIM: bu yerda `AuthenticationFailed` EMAS, oddiy 403 JSON javob
qaytariladi — DRF'da autentifikatsiya xatosi 401 bo'lib chiqadi,
frontend esa 401'ni "seans tugadi" deb talqin qilib AVTOMATIK chiqarib
yuboradi (`api.js`). Bu yerda esa faqat SHU AMAL taqiqlangan, owner
tizimdan chiqarilmasligi kerak — shuning uchun oddiy Django middleware
(DRF permission emas) va aniq 403 javob."""

from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication

YOZISH_METODLARI = {"POST", "PUT", "PATCH", "DELETE"}

# Prefiks bo'yicha tekshiriladi — shu bilan boshlangan har qanday yo'l
# (masalan "/api/imtihon" — "/api/imtihon-mock/..." ham shunga kiradi).
CHEKLANGAN_YOZISH_YOLLARI = (
    "/api/mashqlar",       # IELTS testlari + AI mashqlari (Mashq)
    "/api/imtihon",        # IELTS testlari + AI mashqlari + Mock (ImtihonTest/ImtihonMock)
    "/api/kurslar",        # Kurslar bo'limi
    "/api/guruhlar",       # Guruh yaratish/tahrirlash/a'zolik
    "/api/talabalar",      # Talaba yaratish/tahrirlash
    "/api/xodimlar",       # Xodim (o'qituvchi/admin) yaratish/tahrirlash
    "/api/foydalanuvchilar",  # Foydalanuvchi yaratish/tahrirlash (barcha sub-amallar)
    "/api/profil/korish-rejimi",  # "Ko'rish rejimi" (profil turini almashtirish)
)


class OwnerYozishCheklashMiddleware:
    """Yuqoridagi yo'llarga mutatsion (POST/PUT/PATCH/DELETE) so'rov
    kelsa va so'rovchi haqiqiy OWNER bo'lsa, `Markaz.kirish_cheklangan`
    tekshiriladi. GET so'rovlar (ko'rish) hech qachon bloklanmaydi."""

    def __init__(self, get_response):
        self.get_response = get_response
        self._jwt_auth = JWTAuthentication()

    def __call__(self, request):
        if (
            request.method in YOZISH_METODLARI
            and request.path.startswith(CHEKLANGAN_YOZISH_YOLLARI)
        ):
            user = self._foydalanuvchini_ol(request)
            if user is not None and user.is_superuser:
                from .models import Markaz

                markaz = Markaz.objects.first()
                if markaz and markaz.kirish_cheklangan:
                    return JsonResponse(
                        {
                            "detail": "Kirish cheklovi faol — bu amal vaqtincha bloklangan",
                            "kod": "yozish_cheklangan",
                        },
                        status=403,
                    )
        return self.get_response(request)

    def _foydalanuvchini_ol(self, request):
        """JWT'ni o'zi qayta hal qiladi — bu ODDIY Django middleware,
        DRF authentication'idan OLDIN ishlaydi, `request.user` hali
        mavjud emas (JWT session emas, DRF darajasida hal qilinadi)."""
        try:
            natija = self._jwt_auth.authenticate(request)
        except Exception:
            return None
        return natija[0] if natija else None


class ZaxiraTekshiruvMiddleware:
    """Avtomatik kunlik zaxira uchun "turtki" (2026-09-03).

    Loyihada cron/Celery ATAYLAB yo'q (`accounts/zaxira.py` va
    `relizlar.py` izohlariga qara) — shuning uchun "vaqt keldimi?"
    savoli SO'ROV paytida beriladi. Ish o'zi fon oqimida bajariladi,
    ya'ni foydalanuvchi so'rovi kutib turmaydi.

    Juda arzon: `fonda_tekshir` jarayon ichida daqiqada bir martadan
    ko'p bazaga qaramaydi, qolgan chaqiruvlar darhol qaytadi. Statik
    fayllar va autentifikatsiya so'rovlari uchun ham chaqirilishi
    muammo emas — bir xil hisoblagichga tushadi.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            from .zaxira import fonda_tekshir

            fonda_tekshir()
        except Exception:  # noqa: BLE001 — zaxira hech qachon saytni buzmasin
            pass
        return self.get_response(request)
