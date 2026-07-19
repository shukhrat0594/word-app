from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from config import narxlar as NARX

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
            }
        return Response(
            {
                "id": u.id,
                "username": u.username,
                "ism": u.get_full_name() or u.username,
                "role": u.role,
                "markaz": markaz,
                "is_owner": owner_mi(u),
                "parol_bormi": u.has_usable_password(),
            }
        )


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
        markaz.delete()
        return Response({"detail": "So'rov rad etildi"})


class MarkazSozlamaView(APIView):
    """Markaz admini uchun — o'z markazining brendingi (logo, rang).

    Owner emas, balki shu markazning admini sozlaydi — nomi/AI provayder
    kabi biznes darajasidagi narsalar emas, faqat vizual taqdimot.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        if request.user.role != User.Role.ADMIN or not request.user.markaz_id:
            return Response({"detail": "Faqat markaz admini uchun"}, status=403)
        m = request.user.markaz
        return Response(
            {
                "id": m.id,
                "name": m.name,
                "logo_url": m.logo.url if m.logo else None,
                "brend_rang": m.brend_rang,
            }
        )

    def patch(self, request):
        if request.user.role != User.Role.ADMIN or not request.user.markaz_id:
            return Response({"detail": "Faqat markaz admini uchun"}, status=403)

        m = request.user.markaz
        rang = request.data.get("brend_rang")
        if rang:
            m.brend_rang = rang
        logo = request.data.get("logo")
        if logo:
            m.logo = logo
        m.save()
        return Response(
            {
                "id": m.id,
                "name": m.name,
                "logo_url": m.logo.url if m.logo else None,
                "brend_rang": m.brend_rang,
            }
        )


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

        user.role = role_value
        user.is_superuser = is_super
        user.is_staff = is_super
        if role_value in (User.Role.ADMIN, User.Role.TEACHER) and not user.markaz_id:
            markaz = Markaz.objects.first()
            if markaz:
                user.markaz = markaz
        user.save()

        return Response({"id": user.id, "role": user.role, "is_owner": user.is_superuser})


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
        user.delete()
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
        user.role = User.Role.ADMIN
        user.markaz = markaz
        if ism:
            user.first_name = ism
        user.set_password(parol)
        user.save()

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
        oqituvchilar = User.objects.filter(markaz_id=markaz_id, role=User.Role.TEACHER)
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

        return Response(
            {"id": user.id, "username": user.username, "yaratildi": created},
            status=201 if created else 200,
        )


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


class GoogleLoginView(APIView):
    """Talaba Google ID token yuboradi -> tekshiriladi -> JWT qaytariladi.

    Markaz biriktirilmaydi (markaz=None) -- buni keyinroq Markaz admin
    Guruhga qo'shganda avtomatik oladi (academics.Guruh signali).
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        token = request.data.get("id_token")
        if not token:
            return Response({"detail": "id_token majburiy"}, status=400)

        try:
            idinfo = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
            )
        except ValueError:
            return Response({"detail": "id_token yaroqsiz"}, status=401)

        email = idinfo["email"]
        user, created = User.objects.get_or_create(
            username=email,
            defaults={
                "email": email,
                "role": User.Role.STUDENT,
                "first_name": idinfo.get("given_name", ""),
                "last_name": idinfo.get("family_name", ""),
            },
        )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "created": created,
                "markaz_biriktirilgan": user.markaz_id is not None,
            }
        )
