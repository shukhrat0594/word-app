from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from audit.models import FaoliyatYozuvi, LoginHistory
from audit.utils import logla, maydon_diff
from config import narxlar as NARX

from .authentication import asl_owner_mi
from .models import Markaz, User
from .permissions import birlamchi_owner_mi, owner_mi


def _parolni_tekshir(parol, user=None):
    """Django'ning standart parol qoidalari bilan tekshiradi (uzunlik,
    umumiy parollar, foydalanuvchi ma'lumotiga o'xshashlik va h.k.).

    Xato bo'lsa xabarlar ro'yxatini, hammasi joyida bo'lsa None qaytaradi.
    """
    try:
        validate_password(parol, user=user)
    except DjangoValidationError as e:
        return list(e.messages)
    return None


class NarxlarView(APIView):
    """Yagona narx manbai (`config/narxlar.py`) — frontend shu yerdan o'qiydi.

    Narx o'zgarsa faqat `config/narxlar.py` tahrirlanadi, frontend/backend'da
    hech qayerda qattiq yozilgan (hardcode) narx qolmaydi.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "writing_tezkor": NARX.WRITING_TEZKOR,
                "speaking_matn": NARX.SPEAKING_MATN,
                "speaking_tezkor": NARX.SPEAKING_TEZKOR,
            }
        )


class ProfilView(APIView):
    """Joriy foydalanuvchi profili + markaz brendingi (nom, logo)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        markaz = None
        if u.markaz:
            markaz = {
                "id": u.markaz.id,
                "name": u.markaz.name,
                "logo_url": u.markaz.logo.url if u.markaz.logo else None,
                "brend_rang": u.markaz.brend_rang,
                # 2026-07-27: pastki panel uchun — faqat to'ldirilganlari
                "ijtimoiy": u.markaz.ijtimoiy_havolalar(),
            }
        return Response(
            {
                "id": u.id,
                "username": u.username,
                "ism": u.get_full_name() or u.username,
                # "role"/"is_owner" — SIMULYATSIYAGA BO'YSUNADI (2026-07-29,
                # "Ko'rish rejimi" faol bo'lsa, bular butun ilova nima
                # ko'rishini belgilaydi — accounts/authentication.py).
                "role": u.role,
                "markaz": markaz,
                "is_owner": owner_mi(u),
                "parol_bormi": u.has_usable_password(),
                # Simulyatsiyadan MUSTAQIL — faqat "Ko'rish rejimi"
                # tugmalarini ko'rsatish/yashirish uchun (aks holda owner
                # simulyatsiya paytida o'zini qaytarib bo'lmay qolar edi).
                "asl_owner_mi": asl_owner_mi(u),
                "korish_rejimi": u.korish_rejimi,
                "korinadigan_panellar": u.korinadigan_panellar,
            }
        )


class KorishRejimiView(APIView):
    """Owner uchun — "Ko'rish rejimi" (View As) tanlash: Owner/Admin/
    Talaba/Mehmon (2026-07-29). Tanlangач butun ilova (backend+frontend)
    owner'ni HAQIQATAN shu rol deb ko'radi — batafsil izoh:
    accounts/authentication.py.

    MUHIM: `request.user`ni to'g'ridan-to'g'ri SAQLAMAYMIZ — agar
    simulyatsiya allaqachon faol bo'lsa, `request.user.role`/
    `is_superuser` XOTIRADA soxta qiymatlarga almashtirilgan (shu
    so'rovning o'zida ham!) va `.save()` chaqirilsa ular bazaga
    yozilib qolardi. Shuning uchun bazadan YANGI (toza) nusxa olinadi,
    faqat `korish_rejimi` maydoni `update_fields` bilan yoziladi."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not asl_owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)

        rejim = request.data.get("korish_rejimi")
        if rejim not in User.KorishRejimi.values:
            return Response({"detail": "Noto'g'ri 'korish_rejimi' qiymati"}, status=400)

        # Xotiradagi (ehtimol allaqachon soxtalashtirilgan) ob'ektga emas,
        # bazadan olingan TOZA nusxaga yozamiz.
        haqiqiy = User.objects.get(pk=request.user.pk)
        haqiqiy.korish_rejimi = rejim
        haqiqiy.save(update_fields=["korish_rejimi"])
        return Response({"korish_rejimi": rejim})


class MarkazlarView(APIView):
    """Owner uchun — markazlar ro'yxati va yangi markaz yaratish.

    Faqat platforma egasi (superuser) kira oladi — markazlarni ochish/yopish
    biznes darajasidagi qaror, markaz adminlariga tegishli emas.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)
        return Response(
            [
                {
                    "id": m.id,
                    "name": m.name,
                    "logo_url": m.logo.url if m.logo else None,
                    "brend_rang": m.brend_rang,
                    "ai_provider": m.ai_provider,
                    "admin_soni": m.users.filter(role=User.Role.ADMIN).count(),
                    "tasdiqlangan": m.tasdiqlangan,
                    "soruvchi": (
                        {"id": m.soruvchi.id, "ism": m.soruvchi.get_full_name() or m.soruvchi.username}
                        if m.soruvchi else None
                    ),
                    "created_at": m.created_at,
                }
                for m in Markaz.objects.all().order_by("tasdiqlangan", "-created_at")
            ]
        )

    def post(self, request):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)
        if Markaz.objects.exists():
            return Response(
                {"detail": "Platforma hozircha faqat bitta markaz bilan ishlaydi"},
                status=400,
            )

        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"detail": "name majburiy"}, status=400)

        markaz = Markaz.objects.create(
            name=name,
            ai_provider=request.data.get("ai_provider") or Markaz.AIProvider.GEMINI,
            brend_rang=request.data.get("brend_rang") or "#FFD400",
            logo=request.data.get("logo") or None,
            tasdiqlangan=True,
        )
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=markaz,
            obyekt_turi="Markaz",
            snapshot={"name": markaz.name, "ai_provider": markaz.ai_provider},
        )
        return Response(
            {"id": markaz.id, "name": markaz.name, "ai_provider": markaz.ai_provider},
            status=201,
        )


class MarkazSorovView(APIView):
    """2026-07-18: platforma hozircha faqat BITTA markaz bilan ishlaydi
    (`Utmost o'quv markazi`) — yangi markaz so'rash imkoniyati o'chirilgan.
    Kod (model maydonlari, tasdiqlash oqimi) saqlanib qolgan — kelajakda
    qayta ko'p-markazli rejimga o'tilsa shu yerdan davom ettiriladi.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            [
                {
                    "id": m.id,
                    "name": m.name,
                    "tasdiqlangan": m.tasdiqlangan,
                    "created_at": m.created_at,
                }
                for m in Markaz.objects.filter(soruvchi=request.user).order_by("-created_at")
            ]
        )

    def post(self, request):
        return Response(
            {"detail": "Platforma hozircha faqat bitta markaz bilan ishlaydi"},
            status=400,
        )


class MarkazTasdiqlashView(APIView):
    """Owner uchun — kutilayotgan markaz so'rovini tasdiqlaydi.

    Tasdiqlangach so'rov yuborgan foydalanuvchi shu markazning administratori
    bo'ladi (avtomatik — alohida parol/login kerak emas, u allaqachon o'z
    hisobiga ega).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)

        markaz = get_object_or_404(Markaz, pk=pk)
        if markaz.tasdiqlangan:
            return Response({"detail": "Bu markaz allaqachon tasdiqlangan"}, status=400)

        markaz.tasdiqlangan = True
        markaz.save(update_fields=["tasdiqlangan"])

        if markaz.soruvchi:
            markaz.soruvchi.role = User.Role.ADMIN
            markaz.soruvchi.markaz = markaz
            markaz.soruvchi.save(update_fields=["role", "markaz"])

        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=markaz,
            obyekt_turi="Markaz",
            eski_qiymatlar={"tasdiqlangan": False},
            yangi_qiymatlar={"tasdiqlangan": True},
        )
        return Response({"id": markaz.id, "tasdiqlangan": True})


class MarkazRadEtishView(APIView):
    """Owner uchun — kutilayotgan (hali tasdiqlanmagan) markaz so'rovini rad etadi."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)

        markaz = get_object_or_404(Markaz, pk=pk)
        if markaz.tasdiqlangan:
            return Response(
                {"detail": "Tasdiqlangan markazni bu yerdan o'chirib bo'lmaydi"}, status=400
            )
        nomi = markaz.name
        markaz_id = markaz.id
        markaz.delete()
        FaoliyatYozuvi.objects.create(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OCHIRISH,
            obyekt_turi="Markaz",
            obyekt_id=markaz_id,
            obyekt_nomi=nomi,
            ozgarishlar={"sabab": "so'rov rad etildi"},
        )
        return Response({"detail": "So'rov rad etildi"})


def _markaz_sozlama_dict(m):
    return {
        "id": m.id,
        "name": m.name,
        "logo_url": m.logo.url if m.logo else None,
        "brend_rang": m.brend_rang,
        # Bu yerda BARCHA maydonlar qaytadi (bo'shlari ham) — admin formasi
        # to'ldirilmaganini ham ko'rsatishi kerak. Pastki panelda esa faqat
        # to'ldirilganlari chiqadi (`ijtimoiy_havolalar`).
        "ijtimoiy": {k: getattr(m, k) for k, _ in Markaz.IJTIMOIY_MAYDONLAR},
    }


class IjtimoiyHavolalarView(APIView):
    """OCHIQ endpoint (2026-07-27) — pastki panel uchun markazning ijtimoiy
    tarmoq havolalari.

    Nega login talab qilinmaydi: panel saytning HAMMA sahifasida, jumladan
    login ekranida ham ko'rinishi kerak. `/api/profil/` esa
    autentifikatsiya talab qiladi, ya'ni kirmagan mehmon uchun ishlamaydi.

    Maxfiylik xavfi yo'q: bu havolalar ommaga mo'ljallangan (kanal/profil
    sahifalari), faqat TO'LDIRILGANLARI qaytadi va boshqa hech qanday
    markaz ma'lumoti berilmaydi.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        m = Markaz.objects.first()
        return Response(m.ijtimoiy_havolalar() if m else {})


def _havolani_normalla(qiymat):
    """Admin "instagram.com/utmost" deb yozsa ham ishlasin — sxema
    qo'shiladi. Noto'g'ri havola bo'lsa ValidationError ko'tariladi."""
    from django.core.validators import URLValidator

    qiymat = (qiymat or "").strip()
    if not qiymat:
        return ""
    if not qiymat.startswith(("http://", "https://")):
        qiymat = "https://" + qiymat
    URLValidator()(qiymat)
    return qiymat


class MarkazSozlamaView(APIView):
    """Markaz admini uchun — o'z markazining brendingi (logo, rang) va
    ijtimoiy tarmoq havolalari.

    Nomi/AI provayder kabi biznes darajasidagi narsalar bu yerda emas —
    faqat vizual taqdimot. 2026-07-27: owner ham kira oladi (avval faqat
    admin edi) va ijtimoiy tarmoqlar qo'shildi.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def _markaz_ol(self, request):
        if owner_mi(request.user) or request.user.role == User.Role.ADMIN:
            markaz_id = _admin_markaz_ol(request.user)
            if markaz_id:
                return Markaz.objects.filter(pk=markaz_id).first()
        return None

    def get(self, request):
        m = self._markaz_ol(request)
        if not m:
            return Response({"detail": "Faqat markaz admini uchun"}, status=403)
        return Response(_markaz_sozlama_dict(m))

    def patch(self, request):
        m = self._markaz_ol(request)
        if not m:
            return Response({"detail": "Faqat markaz admini uchun"}, status=403)

        # Ijtimoiy tarmoqlar — bo'sh satr yuborilsa havola O'CHIRILADI
        # (panelda ko'rinmay qoladi), umuman yuborilmasa tegilmaydi.
        from django.core.exceptions import ValidationError as DjangoValidationError

        ijtimoiy_eski, ijtimoiy_yangi = {}, {}
        for kalit, nom in Markaz.IJTIMOIY_MAYDONLAR:
            if kalit not in request.data:
                continue
            try:
                yangi = _havolani_normalla(request.data.get(kalit))
            except DjangoValidationError:
                return Response(
                    {"detail": f"{nom} havolasi noto'g'ri ko'rinishda"}, status=400
                )
            if yangi != getattr(m, kalit):
                ijtimoiy_eski[kalit] = getattr(m, kalit) or "—"
                ijtimoiy_yangi[kalit] = yangi or "—"
                setattr(m, kalit, yangi)

        eski_rang = m.brend_rang
        logo_ozgardimi = False
        rang = request.data.get("brend_rang")
        if rang:
            m.brend_rang = rang
        logo = request.data.get("logo")
        if logo:
            m.logo = logo
            logo_ozgardimi = True
        m.save()
        ozgarishlar = maydon_diff({"brend_rang": eski_rang}, {"brend_rang": m.brend_rang})
        if logo_ozgardimi:
            ozgarishlar["logo"] = {"eski": "—", "yangi": "yangilandi"}
        ozgarishlar.update(maydon_diff(ijtimoiy_eski, ijtimoiy_yangi))
        if ozgarishlar:
            logla(
                foydalanuvchi=request.user,
                harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
                obyekt=m,
                obyekt_turi="Markaz",
                ozgarishlar=ozgarishlar,
            )
        return Response(_markaz_sozlama_dict(m))


class FoydalanuvchilarView(APIView):
    """Owner uchun — barcha foydalanuvchilar ro'yxati (parol boshqarish uchun)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)
        qs = User.objects.all().order_by("-date_joined")
        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(username__icontains=q)
        return Response(
            [
                {
                    "id": u.id,
                    "ism": u.get_full_name() or u.username,
                    "username": u.username,
                    "role": u.role,
                    "is_owner": u.is_superuser,
                    "markaz": u.markaz.name if u.markaz else None,
                    "parol_bormi": u.has_usable_password(),
                    "korinadigan_panellar": u.korinadigan_panellar,
                }
                for u in qs[:200]
            ]
        )


class FoydalanuvchiYaratishView(APIView):
    """Owner uchun — istalgan turdagi (owner/admin/teacher/student/oddiy)
    yangi foydalanuvchi yaratadi.

    "owner" roli — is_superuser=True qiladi, lekin platformada ko'pi
    bilan 2 ta owner bo'lishi mumkin (birinchisi — asosiy owner).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)

        username = (request.data.get("username") or "").strip()
        parol = request.data.get("parol") or ""
        ism = (request.data.get("ism") or "").strip()
        rol = request.data.get("rol") or ""

        if not username:
            return Response({"detail": "username majburiy"}, status=400)
        if not parol:
            return Response({"detail": "parol majburiy"}, status=400)
        if User.objects.filter(username=username).exists():
            return Response({"detail": "Bu login band"}, status=400)
        xatolar = _parolni_tekshir(parol)
        if xatolar:
            return Response({"detail": " ".join(xatolar)}, status=400)

        is_super = rol == "owner"
        if is_super:
            if User.objects.filter(is_superuser=True).count() >= 2:
                return Response(
                    {"detail": "Ko'pi bilan 2 ta owner bo'lishi mumkin"}, status=400
                )
            role_value = User.Role.ADMIN
        elif rol == "admin":
            role_value = User.Role.ADMIN
        elif rol == "teacher":
            role_value = User.Role.TEACHER
        elif rol == "student":
            role_value = User.Role.STUDENT
        elif rol == "oddiy":
            role_value = User.Role.ODDIY
        else:
            return Response({"detail": "Noto'g'ri rol"}, status=400)

        user = User(username=username, role=role_value, is_superuser=is_super, is_staff=is_super)
        if ism:
            user.first_name = ism
        if role_value in (User.Role.ADMIN, User.Role.TEACHER) and not is_super:
            markaz = Markaz.objects.first()
            if markaz:
                user.markaz = markaz
        user.set_password(parol)
        user.save()
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt=user,
            obyekt_turi="Foydalanuvchi",
            snapshot={"username": user.username, "role": user.role},
        )

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "is_owner": user.is_superuser,
            },
            status=201,
        )


class FoydalanuvchiRolView(APIView):
    """Owner uchun — istalgan foydalanuvchining rolini o'zgartiradi
    (owner/admin/teacher/student/oddiy), "owner" ham shu ro'yxatda.

    Cheklovlar: o'z rolini o'zgartira olmaysiz (tasodifan owner
    huquqidan mahrum bo'lmaslik uchun); owner qilishda jami owner soni
    2 tadan oshmaydi; oxirgi owner'ni pastga tushirib bo'lmaydi (kamida
    1 owner doim qolishi kerak); boshqa owner'ning rolini FAQAT asosiy
    (birinchi yaratilgan) owner o'zgartira oladi — ikkinchi owner asosiy
    owner'ni pastga tushira olmaydi.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)

        user = get_object_or_404(User, pk=pk)
        if user.pk == request.user.pk:
            return Response({"detail": "O'z rolingizni o'zgartira olmaysiz"}, status=400)
        if user.is_superuser and not birlamchi_owner_mi(request.user):
            return Response(
                {"detail": "Owner'ning rolini faqat asosiy owner o'zgartira oladi"},
                status=403,
            )

        rol = request.data.get("rol") or ""
        is_super = rol == "owner"
        if is_super:
            if not user.is_superuser and User.objects.filter(is_superuser=True).count() >= 2:
                return Response(
                    {"detail": "Ko'pi bilan 2 ta owner bo'lishi mumkin"}, status=400
                )
            role_value = User.Role.ADMIN
        elif rol == "admin":
            role_value = User.Role.ADMIN
        elif rol == "teacher":
            role_value = User.Role.TEACHER
        elif rol == "student":
            role_value = User.Role.STUDENT
        elif rol == "oddiy":
            role_value = User.Role.ODDIY
        else:
            return Response({"detail": "Noto'g'ri rol"}, status=400)

        if user.is_superuser and not is_super and User.objects.filter(is_superuser=True).count() <= 1:
            return Response(
                {"detail": "Oxirgi owner'ni pastga tushirib bo'lmaydi"}, status=400
            )

        eski_rol = user.role
        eski_owner = user.is_superuser
        user.role = role_value
        user.is_superuser = is_super
        user.is_staff = is_super
        if role_value in (User.Role.ADMIN, User.Role.TEACHER) and not user.markaz_id:
            markaz = Markaz.objects.first()
            if markaz:
                user.markaz = markaz
        user.save()
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=user,
            obyekt_turi="Foydalanuvchi",
            eski_qiymatlar={"role": eski_rol, "is_owner": eski_owner},
            yangi_qiymatlar={"role": user.role, "is_owner": user.is_superuser},
        )

        return Response({"id": user.id, "role": user.role, "is_owner": user.is_superuser})


# frontend/src/components/Layout.jsx'dagi nav yo'llari bilan BIR XIL
# saqlanishi kerak (2026-08-05) — bu yerda faqat validatsiya uchun.
KORINADIGAN_PANEL_YOLLARI = {
    "/mashqlar", "/ielts-boshqarish", "/ai-mashqlari", "/kurslar", "/oyinlar",
    "/tarix", "/reyting", "/guruhlar", "/talabalar", "/xodimlar", "/davomat",
    "/ijtimoiy-tarmoqlar", "/foydalanuvchilar", "/hisobotlar",
}


class FoydalanuvchiPanellarView(APIView):
    """Rolga QO'SHIMCHA "ko'rinadigan panellar" cheklovi (2026-08-05,
    foydalanuvchi qarori — xavfsizroq variant: BACKEND ruxsat
    tekshiruvlari o'zgarmaydi, bu FAQAT frontend navigatsiyasini
    qo'shimcha toraytiradi).

    Owner — istalgan foydalanuvchiga; admin — FAQAT o'z markazidagi
    talabalarga (`role=student`) belgilay oladi."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if owner_mi(request.user):
            pass
        elif request.user.role == User.Role.ADMIN:
            if user.role != User.Role.STUDENT or user.markaz_id != request.user.markaz_id:
                return Response(
                    {"detail": "Faqat o'z markazingizdagi talabalarga belgilashingiz mumkin"},
                    status=403,
                )
        else:
            return Response({"detail": "Ruxsat yo'q"}, status=403)

        panellar = request.data.get("panellar")
        if panellar is not None:
            if not isinstance(panellar, list) or not all(isinstance(p, str) for p in panellar):
                return Response({"detail": "panellar — satrlar ro'yxati bo'lishi kerak"}, status=400)
            notogri = [p for p in panellar if p not in KORINADIGAN_PANEL_YOLLARI]
            if notogri:
                return Response({"detail": f"Noto'g'ri panel(lar): {notogri}"}, status=400)
            panellar = panellar or None  # bo'sh ro'yxat ham "cheklovsiz" hisoblanadi

        user.korinadigan_panellar = panellar
        user.save(update_fields=["korinadigan_panellar"])
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=user,
            obyekt_turi="Foydalanuvchi",
            ozgarishlar={"korinadigan_panellar": {"yangi": panellar}},
        )
        return Response({"id": user.id, "korinadigan_panellar": user.korinadigan_panellar})


class FoydalanuvchiNatijalariView(APIView):
    """Bitta talabaning BARCHA mashq/test natijalari — turi bo'yicha
    (reading/listening/writing/speaking/kurslar) bitta ro'yxatda,
    sana bo'yicha kamayish tartibida (2026-08-05, foydalanuvchi
    talabi).

    Ko'ra oladi: FOYDALANUVCHINING O'ZI (har doim, rolidan qat'i nazar —
    "oddiy" foydalanuvchi ham shu orqali "/tarix"da o'zinikini ko'radi),
    owner (istalgan foydalanuvchi), teacher (FAQAT o'z guruhidagi
    talabalar — `Guruh.talabalar`)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        talaba = get_object_or_404(User, pk=pk)
        u = request.user
        if u.pk == talaba.pk or owner_mi(u):
            pass
        elif u.role == User.Role.TEACHER:
            from academics.models import Guruh

            if not Guruh.objects.filter(oqituvchi=u, talabalar=talaba).exists():
                return Response({"detail": "Ruxsat yo'q"}, status=403)
        else:
            return Response({"detail": "Ruxsat yo'q"}, status=403)

        from assessment.models import SpeakingTekshiruv, WritingTekshiruv
        from courses.models import KursMashqYechim
        from exercises.models import MashqYechim, TestYechim

        natijalar = []
        for y in MashqYechim.objects.filter(talaba=talaba).select_related("mashq")[:100]:
            natijalar.append({
                "turi": y.mashq.bolim, "id": y.id, "nomi": y.mashq.name,
                "ball": y.ball, "jami": y.jami, "sana": y.created_at,
                "javoblar": y.javoblar, "natijalar": y.natijalar,
            })
        for y in TestYechim.objects.filter(talaba=talaba).select_related("test")[:100]:
            natijalar.append({
                "turi": y.test.bolim, "id": y.id, "nomi": y.test.name,
                "ball": y.ball, "jami": y.jami,
                "band": float(y.band) if y.band is not None else None,
                "sana": y.created_at, "javoblar": y.javoblar, "natijalar": y.natijalar,
            })
        for t in WritingTekshiruv.objects.filter(talaba=talaba)[:100]:
            natijalar.append({
                "turi": "writing", "id": t.id, "nomi": t.task_type or "Writing",
                "band": t.overall_band, "sana": t.created_at,
                "natija": t.natija, "matn": t.matn,
            })
        for t in SpeakingTekshiruv.objects.filter(talaba=talaba)[:100]:
            natijalar.append({
                "turi": "speaking", "id": t.id, "nomi": t.part_type or "Speaking",
                "band": t.overall_band, "sana": t.created_at, "natija": t.natija,
                "matn": t.matn, "audio_url": t.audio_fayl.url if t.audio_fayl else None,
            })
        for y in KursMashqYechim.objects.filter(talaba=talaba).select_related("mashq")[:100]:
            nomi = (y.mashq.matn or "").strip()[:60] or f"Mashq #{y.mashq.tartib}"
            natijalar.append({
                "turi": "kurslar", "id": y.id, "nomi": nomi,
                "ball": y.ball, "jami": y.jami, "sana": y.created_at,
                "javoblar": y.javoblar, "natijalar": y.natijalar,
            })

        natijalar.sort(key=lambda n: n["sana"], reverse=True)
        return Response({
            "talaba": {"id": talaba.id, "ism": talaba.get_full_name() or talaba.username},
            "natijalar": natijalar[:200],
        })


class FoydalanuvchiOchirishView(APIView):
    """Owner yoki admin uchun — foydalanuvchi hisobini o'chiradi.

    Cheklovlar: o'zini o'chirib bo'lmaydi; owner'larni (superuser) hech kim
    o'chira olmaydi; owner bo'lmagan admin boshqa adminni o'chira olmaydi.
    O'chirish bilan birga foydalanuvchining barcha bog'liq ma'lumotlari
    (tekshiruv tarixi va h.k.) ham o'chadi (FK cascade).
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not (owner_mi(request.user) or request.user.role == User.Role.ADMIN):
            return Response({"detail": "Ruxsat yo'q"}, status=403)

        user = get_object_or_404(User, pk=pk)
        if user.pk == request.user.pk:
            return Response({"detail": "O'z hisobingizni o'chira olmaysiz"}, status=400)
        if user.is_superuser:
            return Response({"detail": "Owner hisobini o'chirib bo'lmaydi"}, status=400)
        if user.role == User.Role.ADMIN and not owner_mi(request.user):
            return Response(
                {"detail": "Adminni faqat owner o'chira oladi"}, status=403
            )

        username = user.username
        user_id = user.id
        rol = user.role
        user.delete()
        FaoliyatYozuvi.objects.create(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OCHIRISH,
            obyekt_turi="Foydalanuvchi",
            obyekt_id=user_id,
            obyekt_nomi=username,
            ozgarishlar={"username": username, "role": rol},
        )
        return Response({"detail": f"{username} o'chirildi"})


class OddiyStudentgaOtkazishView(APIView):
    """Owner yoki admin uchun — "oddiy foydalanuvchi"ni "talaba" roliga o'tkazadi."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not (owner_mi(request.user) or request.user.role == User.Role.ADMIN):
            return Response({"detail": "Ruxsat yo'q"}, status=403)
        user = get_object_or_404(User, pk=pk, role=User.Role.ODDIY)
        user.role = User.Role.STUDENT
        user.save(update_fields=["role"])
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=user,
            obyekt_turi="Foydalanuvchi",
            eski_qiymatlar={"role": User.Role.ODDIY},
            yangi_qiymatlar={"role": User.Role.STUDENT},
        )
        return Response({"id": user.id, "role": user.role})


class FoydalanuvchiParolTiklashView(APIView):
    """Owner uchun — istalgan foydalanuvchiga (rolidan qat'i nazar) yangi parol qo'yadi."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)

        user = get_object_or_404(User, pk=pk)
        parol = request.data.get("parol") or ""
        if not parol:
            return Response({"detail": "parol majburiy"}, status=400)
        xatolar = _parolni_tekshir(parol, user=user)
        if xatolar:
            return Response({"detail": " ".join(xatolar)}, status=400)

        user.set_password(parol)
        user.save()
        logla(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=user,
            obyekt_turi="Foydalanuvchi",
            obyekt_nomi=user.username,
            ozgarishlar={"parol": {"eski": "***", "yangi": "o'rnatildi"}},
        )
        return Response({"detail": "Parol o'rnatildi"})


class MarkazAdminTayinlashView(APIView):
    """Owner uchun — markazga administrator tayinlaydi (yangi yoki mavjud user).

    Username mavjud bo'lsa — o'sha userga admin roli + shu markaz beriladi
    (parol berilsa yangilanadi). Mavjud bo'lmasa — yangi user yaratiladi.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)

        try:
            markaz = Markaz.objects.get(pk=pk)
        except Markaz.DoesNotExist:
            return Response({"detail": "Markaz topilmadi"}, status=404)

        username = (request.data.get("username") or "").strip()
        parol = request.data.get("parol") or ""
        ism = (request.data.get("ism") or "").strip()
        if not username:
            return Response({"detail": "username majburiy"}, status=400)
        if not parol:
            return Response({"detail": "parol majburiy"}, status=400)
        xatolar = _parolni_tekshir(parol)
        if xatolar:
            return Response({"detail": " ".join(xatolar)}, status=400)

        user, created = User.objects.get_or_create(username=username)
        eski_rol = user.role
        user.role = User.Role.ADMIN
        user.markaz = markaz
        if ism:
            user.first_name = ism
        user.set_password(parol)
        user.save()
        if created:
            logla(
                foydalanuvchi=request.user,
                harakat=FaoliyatYozuvi.Harakat.YARATISH,
                obyekt=user,
                obyekt_turi="Foydalanuvchi",
                snapshot={"username": user.username, "role": user.role, "markaz": markaz.name},
            )
        else:
            logla(
                foydalanuvchi=request.user,
                harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
                obyekt=user,
                obyekt_turi="Foydalanuvchi",
                eski_qiymatlar={"role": eski_rol},
                yangi_qiymatlar={"role": user.role, "markaz": markaz.name, "parol": "o'rnatildi"},
            )

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "yaratildi": created,
                "markaz": markaz.name,
            },
            status=201 if created else 200,
        )


class XodimlarView(APIView):
    """Markaz admini uchun — o'z markazidagi o'qituvchilar ro'yxati va yaratish.

    Yaratish = ro'yxatdan o'tish emas: admin ism+login+parol kiritib
    o'qituvchi akkaunt ochadi (Markazlar.jsx'dagi admin tayinlash bilan bir
    xil uslub). Username mavjud bo'lsa — parol yangilanadi (parol tiklash).
    """

    permission_classes = [IsAuthenticated]

    def _markaz_ol(self, request):
        """Adminning o'z markazi, yoki owner bo'lsa (markazga biriktirilmagan
        bo'lsa ham) yagona mavjud markaz — bitta markaz rejimida owner ham
        xodim qo'sha oladi."""
        if request.user.markaz_id:
            return request.user.markaz_id
        if owner_mi(request.user):
            markaz = Markaz.objects.first()
            return markaz.id if markaz else None
        return None

    def get(self, request):
        ruxsat = owner_mi(request.user) or request.user.role == User.Role.ADMIN
        markaz_id = self._markaz_ol(request)
        if not ruxsat or not markaz_id:
            return Response({"detail": "Faqat markaz admini uchun"}, status=403)
        # `?arxiv=1` (2026-08-02) — arxivlangan (is_active=False) xodimlar,
        # standart holatda faqat faollari.
        arxiv = bool(request.query_params.get("arxiv"))
        oqituvchilar = User.objects.filter(
            markaz_id=markaz_id, role=User.Role.TEACHER, is_active=not arxiv
        )
        return Response(
            [
                {"id": u.id, "ism": u.get_full_name() or u.username, "username": u.username}
                for u in oqituvchilar
            ]
        )

    def post(self, request):
        ruxsat = owner_mi(request.user) or request.user.role == User.Role.ADMIN
        markaz_id = self._markaz_ol(request)
        if not ruxsat or not markaz_id:
            return Response({"detail": "Faqat markaz admini uchun"}, status=403)

        username = (request.data.get("username") or "").strip()
        parol = request.data.get("parol") or ""
        ism = (request.data.get("ism") or "").strip()
        if not username:
            return Response({"detail": "username majburiy"}, status=400)
        if not parol:
            return Response({"detail": "parol majburiy"}, status=400)
        xatolar = _parolni_tekshir(parol)
        if xatolar:
            return Response({"detail": " ".join(xatolar)}, status=400)

        user, created = User.objects.get_or_create(username=username)
        if not created and user.markaz_id not in (None, markaz_id):
            return Response(
                {"detail": "Bu login boshqa markazga tegishli"}, status=400
            )
        user.role = User.Role.TEACHER
        user.markaz_id = markaz_id
        if ism:
            user.first_name = ism
        user.set_password(parol)
        user.save()
        if created:
            logla(
                foydalanuvchi=request.user,
                harakat=FaoliyatYozuvi.Harakat.YARATISH,
                obyekt=user,
                obyekt_turi="Foydalanuvchi",
                snapshot={"username": user.username, "role": user.role},
            )
        else:
            logla(
                foydalanuvchi=request.user,
                harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
                obyekt=user,
                obyekt_turi="Foydalanuvchi",
                obyekt_nomi=user.username,
                ozgarishlar={"parol": {"eski": "***", "yangi": "yangilandi"}},
            )

        return Response(
            {"id": user.id, "username": user.username, "yaratildi": created},
            status=201 if created else 200,
        )


class XodimDetailView(APIView):
    """Bitta xodimni (o'qituvchi) arxivlash/faollashtirish (2026-08-02) —
    `is_active=False` qilingan xodim tizimga kira olmaydi (SimpleJWT buni
    avtomatik cheklaydi) va ro'yxatlarda "faol" filtrida ko'rinmaydi.
    Butunlay o'chirish yo'q — bog'liq tarix (Davomat, KursMashqYechim va
    h.k.) saqlanib qolishi kerak."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        xodim = get_object_or_404(User, pk=pk, role=User.Role.TEACHER)
        tahrirlay_oladimi = owner_mi(request.user) or (
            request.user.role == User.Role.ADMIN
            and xodim.markaz_id == request.user.markaz_id
        )
        if not tahrirlay_oladimi:
            return Response({"detail": "Faqat markaz admini uchun"}, status=403)

        if "faol" in request.data:
            xodim.is_active = bool(request.data.get("faol"))
            xodim.save(update_fields=["is_active"])
        return Response({"id": xodim.id, "faol": xodim.is_active})


def _admin_markaz_ol(user):
    """Adminning o'z markazi, yoki owner bo'lsa (markazga biriktirilmagan
    bo'lsa ham) yagona mavjud markaz — bitta markaz rejimida owner ham
    talaba/xodim qo'sha oladi (XodimlarView._markaz_ol bilan bir xil)."""
    if user.markaz_id:
        return user.markaz_id
    if owner_mi(user):
        markaz = Markaz.objects.first()
        return markaz.id if markaz else None
    return None


class XodimlarExcelImportView(APIView):
    """Markaz admini/owner uchun — o'qituvchilarni Excel (.xlsx) orqali
    ommaviy kiritish. Format: A=ism, B=login, C=parol, birinchi qator
    sarlavha. Har bir muvaffaqiyatli yaratilgan xodim uchun audit yozuvi."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        ruxsat = owner_mi(request.user) or request.user.role == User.Role.ADMIN
        markaz_id = _admin_markaz_ol(request.user)
        if not ruxsat or not markaz_id:
            return Response({"detail": "Faqat markaz admini uchun"}, status=403)

        fayl = request.FILES.get("excel_fayl")
        if not fayl:
            return Response({"detail": "excel_fayl majburiy"}, status=400)

        from . import excel_import

        try:
            qatorlar = excel_import.qatorlarni_oqi(fayl)
        except Exception:
            return Response({"detail": "Excel fayl noto'g'ri formatda"}, status=400)

        yaratilganlar, xatolar = excel_import.foydalanuvchilarni_yarat(
            qatorlar, role=User.Role.TEACHER, markaz_id=markaz_id, User=User
        )
        for y in yaratilganlar:
            FaoliyatYozuvi.objects.create(
                foydalanuvchi=request.user,
                harakat=FaoliyatYozuvi.Harakat.YARATISH,
                obyekt_turi="Foydalanuvchi",
                obyekt_id=y["id"],
                obyekt_nomi=y["login"],
                ozgarishlar={"username": y["login"], "role": "teacher", "manba": "excel"},
            )

        return Response({"yaratildi": yaratilganlar, "xatolar": xatolar}, status=201)


class TalabalarView(APIView):
    """Talabalar ro'yxati — owner/admin uchun BARCHA talabalar (2026-08-02:
    talaba markazga bog'lanmaydi — "Utmost talabasi" yagona hisoblanadi,
    platforma bitta markaz bilan ishlayotgani uchun bu amalda ko'rinishni
    o'zgartirmaydi, lekin kod endi markazga tayanmaydi), o'qituvchi uchun
    faqat o'z guruhlaridagi talabalar.

    POST (2026-07-27) — admin/owner bitta talabani qo'lda qo'shadi. Avval
    faqat Excel orqali ommaviy kiritish bor edi, bir-ikkita talaba uchun
    esa fayl tayyorlash noqulay."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        # `?arxiv=1` (2026-08-02) — arxivlangan (is_active=False) talabalar,
        # standart holatda faqat faollari.
        arxiv = bool(request.query_params.get("arxiv"))
        if owner_mi(u) or u.role == User.Role.ADMIN:
            qs = User.objects.filter(role=User.Role.STUDENT, is_active=not arxiv)
        elif u.role == User.Role.TEACHER:
            qs = User.objects.filter(
                role=User.Role.STUDENT, is_active=not arxiv, talaba_guruhlari__oqituvchi=u
            ).distinct()
        else:
            return Response({"detail": "Ruxsat yo'q"}, status=403)

        return Response(
            [
                {
                    "id": t.id, "ism": t.get_full_name() or t.username, "username": t.username,
                    "korinadigan_panellar": t.korinadigan_panellar,
                }
                for t in qs.order_by("first_name", "username")
            ]
        )

    def post(self, request):
        """Bitta talaba qo'shish.

        Tekshiruvlar Excel importi bilan AYNAN bir xil bo'lishi uchun
        `excel_import.foydalanuvchilarni_yarat` qayta ishlatiladi (bitta
        qatorli ro'yxat bilan) — login bandligi, parol kuchi va bo'sh
        maydon qoidalari ikkala yo'lda ham bir xil ishlaydi, kod
        takrorlanmaydi.

        Mavjud login berilsa — parol ALMASHTIRILMAYDI, xato qaytadi
        (`XodimlarView`dan farqi shu: u yerda admin o'qituvchining parolini
        ataylab tiklay oladi, bu yerda esa mavjud talabaning parolini
        tasodifan almashtirib yuborish xavfli)."""
        ruxsat = owner_mi(request.user) or request.user.role == User.Role.ADMIN
        if not ruxsat:
            return Response({"detail": "Faqat admin uchun"}, status=403)

        from . import excel_import

        qator = {
            "qator": 0,
            "ism": (request.data.get("ism") or "").strip(),
            "login": (request.data.get("login") or "").strip(),
            "parol": (request.data.get("parol") or "").strip(),
        }
        # markaz_id=None (2026-08-02) — talaba markazga bog'lanmaydi.
        yaratilganlar, xatolar = excel_import.foydalanuvchilarni_yarat(
            [qator], role=User.Role.STUDENT, markaz_id=None, User=User
        )
        if xatolar:
            return Response({"detail": xatolar[0]["xato"]}, status=400)

        y = yaratilganlar[0]
        FaoliyatYozuvi.objects.create(
            foydalanuvchi=request.user,
            harakat=FaoliyatYozuvi.Harakat.YARATISH,
            obyekt_turi="Foydalanuvchi",
            obyekt_id=y["id"],
            obyekt_nomi=y["login"],
            ozgarishlar={"username": y["login"], "role": "student", "manba": "qolda"},
        )
        return Response({"id": y["id"], "ism": y["ism"], "username": y["login"]}, status=201)


class TalabaDetailView(APIView):
    """Bitta talabani arxivlash/faollashtirish (2026-08-02) — `is_active=
    False` qilingan talaba tizimga kira olmaydi (SimpleJWT avtomatik
    cheklaydi) va ro'yxatlarda "faol" filtrida ko'rinmaydi. Markazga
    bog'liqlik yo'q (istalgan admin/owner arxivlay oladi) — talaba
    markazga bog'lanmagani bilan bir xil qoida. Butunlay o'chirish yo'q —
    bog'liq tarix (KursMashqYechim, GuruhAzoligi va h.k.) saqlanib qoladi.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        ruxsat = owner_mi(request.user) or request.user.role == User.Role.ADMIN
        if not ruxsat:
            return Response({"detail": "Faqat admin uchun"}, status=403)
        talaba = get_object_or_404(User, pk=pk, role=User.Role.STUDENT)

        if "faol" in request.data:
            talaba.is_active = bool(request.data.get("faol"))
            talaba.save(update_fields=["is_active"])
        return Response({"id": talaba.id, "faol": talaba.is_active})


class TalabalarExcelImportView(APIView):
    """Markaz admini/owner uchun — talabalarni Excel (.xlsx) orqali ommaviy
    kiritish. Format: A=ism, B=login, C=parol, birinchi qator sarlavha."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        ruxsat = owner_mi(request.user) or request.user.role == User.Role.ADMIN
        if not ruxsat:
            return Response({"detail": "Faqat admin uchun"}, status=403)

        fayl = request.FILES.get("excel_fayl")
        if not fayl:
            return Response({"detail": "excel_fayl majburiy"}, status=400)

        from . import excel_import

        try:
            qatorlar = excel_import.qatorlarni_oqi(fayl)
        except Exception:
            return Response({"detail": "Excel fayl noto'g'ri formatda"}, status=400)

        # markaz_id=None (2026-08-02) — talaba markazga bog'lanmaydi.
        yaratilganlar, xatolar = excel_import.foydalanuvchilarni_yarat(
            qatorlar, role=User.Role.STUDENT, markaz_id=None, User=User
        )
        for y in yaratilganlar:
            FaoliyatYozuvi.objects.create(
                foydalanuvchi=request.user,
                harakat=FaoliyatYozuvi.Harakat.YARATISH,
                obyekt_turi="Foydalanuvchi",
                obyekt_id=y["id"],
                obyekt_nomi=y["login"],
                ozgarishlar={"username": y["login"], "role": "student", "manba": "excel"},
            )

        return Response({"yaratildi": yaratilganlar, "xatolar": xatolar}, status=201)


class ParolOzgartirishView(APIView):
    """Joriy foydalanuvchi o'z parolini o'zgartiradi.

    Agar foydalanuvchida hali ishlaydigan parol bo'lmasa (masalan Google
    orqali ro'yxatdan o'tgan talaba) — eski parol talab qilinmaydi (birinchi
    marta parol qo'yish). Aks holda eski parol tekshiriladi.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        yangi_parol = request.data.get("yangi_parol") or ""
        eski_parol = request.data.get("eski_parol") or ""

        if request.user.has_usable_password():
            if not eski_parol or not request.user.check_password(eski_parol):
                return Response({"detail": "Joriy parol noto'g'ri"}, status=400)

        xatolar = _parolni_tekshir(yangi_parol, user=request.user)
        if xatolar:
            return Response({"detail": " ".join(xatolar)}, status=400)

        request.user.set_password(yangi_parol)
        request.user.save()
        return Response({"detail": "Parol yangilandi"})


class XodimLoginView(TokenObtainPairView):
    """Standart JWT login (`/api/token/`) — brute-force'dan himoya uchun
    throttling qo'shilgan (login urinishlar soni cheklanadi)."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        javob = super().post(request, *args, **kwargs)
        if javob.status_code == 200:
            user = User.objects.filter(username=request.data.get("username")).first()
            if user is not None:
                LoginHistory.objects.create(foydalanuvchi=user, rol=user.role)
        return javob


class GoogleLoginView(APIView):
    """Google orqali kirish/ro'yxatdan o'tish (2026-08-05, foydalanuvchi
    qarori: BUTUNLAY YOPILDI — frontendda tugma olib tashlandi, bu yerda
    ham qo'shimcha himoya sifatida darhol 403 qaytariladi). Kod o'chirib
    tashlanmadi — kelgusida qayta ochish kerak bo'lsa, faqat pastdagi
    `return` qatori olib tashlanadi."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        return Response({"detail": "Google orqali kirish yopilgan"}, status=403)
