"""CRM ruxsatlari va bazaviy view.

MUHIM: himoya BACKENDDA. Frontendda menyuni yashirish himoya emas —
CRM manzilini bilib olgan talaba `/api/crm/...` ga to'g'ridan-to'g'ri
so'rov yubora oladi, shuning uchun har bir endpoint shu yerdan
tekshiriladi.
"""

from django.conf import settings
from django.http import Http404
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.views import APIView

from accounts.permissions import owner_mi

from .mantiq import hisoblarni_generatsiya_qil
from .ruxsatlar import ruxsatlar


class CrmRuxsati(BasePermission):
    """CRM'ga faqat admin va owner kiradi. Qolganlar — 403.

    `owner_mi()` "Ko'rish rejimi" simulyatsiyasiga BO'YSUNADI: owner
    rejimni Talabaga qo'ygan bo'lsa, u ham 403 oladi. Bu ATAYLAB
    shunday — butun loyiha shu qoidaga bo'ysunadi
    (`accounts/authentication.py`), va rejim aynan shuni sinash uchun.
    Frontend bu holatni alohida xabar bilan tushuntiradi
    (`src-crm/App.jsx`), aks holda owner tizimni buzuq deb o'ylardi.
    """

    message = "Bu bo'limga ruxsatingiz yo'q"

    def has_permission(self, request, view):
        # 2026-09-23 (video-TZ): admin/owner'dan tashqari xodim rollari
        # (kassir, marketolog, maxsus rol) ham kiradi — lekin faqat
        # ruxsat berilgan BO'LIMga. View `bolim` e'lon qiladi; `None`
        # bo'lsa istalgan CRM foydalanuvchisiga ochiq (filial ro'yxati,
        # eslatmalar kabi umumiy narsalar). `oqish_ochiq=True` — GET
        # hamma CRM foydalanuvchisiga, yozish esa faqat bo'lim egasiga.
        berilgan = ruxsatlar(request.user)
        if not berilgan:
            return False
        bolim = getattr(view, "bolim", None)
        if bolim is None:
            return True
        if request.method == "GET" and getattr(view, "oqish_ochiq", False):
            return True
        return bolim in berilgan


class FaqatOwner(BasePermission):
    """Qaytarib bo'lmaydigan yoki pulni o'zgartiradigan amallar uchun —
    hisob summasini tuzatish, to'lov yozuvini o'chirish."""

    message = "Bu amalni faqat owner bajara oladi"

    def has_permission(self, request, view):
        return owner_mi(request.user)


class CrmView(APIView):
    """Barcha CRM view'lari uchun asos.

    Ruxsatdan tashqari — HAR BIR GET so'rovida hisob generatsiyasini
    ishga tushiradi ("dangasa" usul, TZ 4.1). Cron yo'q: loyihadagi
    mavjud konvensiya (`Markaz.zaxira_avtomatik` — "shu vaqtdan keyingi
    birinchi so'rovda olinadi").

    NEGA MIDDLEWARE EMAS (TZ 3.0, 3-qoida): middleware LMS so'rovlarida
    ham ishlab ketardi va `settings.MIDDLEWARE`ga qator qo'shish kerak
    bo'lardi — ya'ni CRM o'chirilganda uni olib tashlash esdan chiqishi
    mumkin edi. Bu yerda esa u CRM bilan birga o'chadi.

    Generatsiya faqat ORQADA QOLGAN a'zoliklarni tanlaydi: hech nima
    qolmagan bo'lsa bitta indeksli so'rov 0 qator qaytaradi.
    """

    permission_classes = [IsAuthenticated, CrmRuxsati]

    def initial(self, request, *args, **kwargs):
        # CRM o'chirilgan bo'lsa (prod) — 404. ATAYLAB 403 emas: 403
        # "bu yerda nimadir bor, lekin senga ruxsat yo'q" degani, 404
        # esa bo'limning borligini ham oshkor qilmaydi.
        #
        # Tekshiruv URL darajasida emas, shu yerda: `config/urls.py`da
        # shartli `include` qilsak, testlar URL'larni import paytida
        # yo'qotardi va `override_settings` ish bermasdi.
        if not getattr(settings, "CRM_YOQILGAN", False):
            raise Http404("CRM yoqilmagan")

        super().initial(request, *args, **kwargs)  # avval autentifikatsiya va ruxsat
        if request.method == "GET":
            hisoblarni_generatsiya_qil()
