from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from audit.models import FaoliyatYozuvi, LoginHistory
from audit.utils import logla, maydon_diff

from .authentication import asl_owner_mi
from .models import Bildirishnoma, Markaz, User
# `birlamchi_owner_mi` 2026-08-09 da ishlatilmay qoldi — u FAQAT rol
# o'zgartirishda kerak edi ("owner'ning rolini faqat asosiy owner
# o'zgartiradi"), u esa endi yopiq. Funksiya `permissions.py`da qoldi.
from .permissions import owner_mi
from .relizlar import relizlarni_sinxronla


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
                "rasm_url": f"/api/foydalanuvchilar/{u.id}/rasm/" if u.rasm else None,
                # 2026-08-14 — o'z profili, hammasi (shaxsiylari ham) ko'rinadi.
                "bio": u.bio,
                "telefon": u.telefon,
                "ota_ona_telefon": u.ota_ona_telefon,
                "tugilgan_sana": u.tugilgan_sana,
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
        # `select_related`/`prefetch_related` SHART (2026-08-09): pastda har
        # qator uchun `u.markaz.name` va `u.farzandlar.all()` o'qiladi, ya'ni
        # ularsiz HAR FOYDALANUVCHI uchun alohida so'rov ketardi (o'lchandi:
        # 4 foydalanuvchida 4 so'rov, shundan 3 tasi faqat `markaz` uchun —
        # 200 odamda 200 dan oshardi). Bular bilan jami 2 ta so'rov.
        qs = (
            User.objects
            .select_related("markaz")
            .prefetch_related("farzandlar")
            .order_by("-date_joined")
        )
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
                    "rasm_url": f"/api/foydalanuvchilar/{u.id}/rasm/" if u.rasm else None,
                    # 2026-08-12: qiymatning o'zi emas, faqat "bor/yo'q" —
                    # "Qurilmani tiklash" tugmasini ko'rsatish/berkitish uchun.
                    "qurilma_bormi": bool(u.qurilmalar),
                    # 2026-08-13: limit tahrirlash (owner-only) va
                    # hozir nechta qurilma band ekanini ko'rsatish uchun.
                    "qurilma_limiti": u.qurilma_limiti,
                    "qurilmalar_soni": len(u.qurilmalar),
                    # 2026-08-14 — owner ko'radi (shaxsiylari ham).
                    "bio": u.bio,
                    "telefon": u.telefon,
                    "ota_ona_telefon": u.ota_ona_telefon,
                    "tugilgan_sana": u.tugilgan_sana,
                    # Ota-ona uchun — biriktirilgan farzandlar (2026-08-09).
                    "farzandlar": [
                        {"id": f.id, "ism": f.get_full_name() or f.username}
                        for f in u.farzandlar.all()
                    ] if u.role == User.Role.PARENT else [],
                    # Talaba uchun — allaqachon biriktirilganmi (frontend
                    # band talabani belgilashga ruxsat bermasligi uchun).
                    "ota_ona_id": u.ota_ona_id,
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
        elif rol == "parent":
            # 2026-08-08: model'da PARENT allaqachon bor edi, lekin bu
            # ro'yxatlarda yo'qligi uchun ilovadan ota-ona YARATIB
            # bo'lmasdi (faqat Django admin panelidan).
            role_value = User.Role.PARENT
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
    """ROL O'ZGARTIRISH YOPIQ (2026-08-09, foydalanuvchi qarori).

    Qoida: rol FAQAT foydalanuvchi YARATILAYOTGANDA tanlanadi
    (`FoydalanuvchiYaratishView` — u "owner"ni ham qabul qiladi, ya'ni
    ikkinchi owner ham shu yo'ldan ochiladi). Bitta odamga ikki xil rol
    kerak bo'lsa — unga ALOHIDA profil ochiladi.

    Nega butunlay yopildi: rol o'zgarganda undan kelib chiqadigan
    bog'lanishlar mos kelmay qolardi — masalan talabaning `ota_ona`
    FK'si (u endi o'qituvchi bo'lsa ham ota-ona uning natijalarini
    ko'rishda davom etardi) va `korinadigan_panellar` ro'yxati (eski
    rolning panellari yangi rolga to'g'ri kelmaydi). Ularning har birini
    tozalash mantiqi qurish o'rniga, foydalanuvchi soddaroq qoidani
    tanladi: rol o'zgarmaydi.

    Endpoint ATAYLAB o'chirilmadi — sababini tushuntirib rad etadi
    (409). Aks holda eski/keshlangan frontend 404 olib, "server
    buzilgan"dek ko'rinardi. Django admin panelida rol maydoni ochiq
    qoladi — bu owner uchun ataylab qoldirilgan zaxira yo'l.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)
        return Response(
            {"detail": (
                "Rolni o'zgartirib bo'lmaydi — u faqat foydalanuvchi "
                "yaratilayotganda tanlanadi. Boshqa rol kerak bo'lsa, "
                "alohida profil ochib bering."
            )},
            status=409,
        )


class FoydalanuvchiFarzandlarView(APIView):
    """Ota-onaga farzand(lar) biriktirish (2026-08-09, foydalanuvchi
    talabi). Avval buni FAQAT Django admin panelida qilish mumkin edi,
    ya'ni ilovadan ota-ona yaratilsa ham unga bola bog'lab bo'lmasdi.

    QOIDA: bitta ota-onada bir NECHTA farzand bo'lishi mumkin, lekin
    bitta bola FAQAT BITTA ota-onaga biriktiriladi. Cheklov modelda
    (`User.ota_ona` FK) — bu yerda faqat tushunarli xato beriladi,
    aks holda boshqa ota-onaning bolasi jimgina tortib olinardi.

    Body: {"farzandlar": [talaba_id, ...]} — TO'LIQ ro'yxat (ro'yxatda
    yo'q, lekin avval biriktirilgan bolalar uzib qo'yiladi)."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        u = request.user
        if not (owner_mi(u) or u.role == User.Role.ADMIN):
            return Response({"detail": "Faqat owner/admin uchun"}, status=403)

        ota_ona = get_object_or_404(User, pk=pk)
        if ota_ona.role != User.Role.PARENT:
            return Response({"detail": "Bu foydalanuvchi ota-ona emas"}, status=400)

        idlar = request.data.get("farzandlar")
        if not isinstance(idlar, list) or not all(isinstance(i, int) for i in idlar):
            return Response({"detail": "farzandlar — id'lar ro'yxati bo'lishi kerak"}, status=400)

        talabalar = list(User.objects.filter(pk__in=idlar, role=User.Role.STUDENT))
        topilmadi = set(idlar) - {t.pk for t in talabalar}
        if topilmadi:
            return Response(
                {"detail": f"Talaba topilmadi (yoki roli talaba emas): {sorted(topilmadi)}"},
                status=400,
            )

        band = [
            t for t in talabalar
            if t.ota_ona_id is not None and t.ota_ona_id != ota_ona.pk
        ]
        if band:
            nomlar = ", ".join(f"{t.get_full_name() or t.username}" for t in band)
            return Response(
                {"detail": f"Bu talaba(lar) allaqachon boshqa ota-onaga biriktirilgan: {nomlar}"},
                status=400,
            )

        # Ro'yxatdan chiqarilganlarni uzamiz, keyin yangilarini bog'laymiz.
        User.objects.filter(ota_ona=ota_ona).exclude(pk__in=idlar).update(ota_ona=None)
        User.objects.filter(pk__in=idlar).update(ota_ona=ota_ona)

        logla(
            foydalanuvchi=u,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=ota_ona,
            obyekt_turi="Foydalanuvchi",
            ozgarishlar={"farzandlar": {"yangi": idlar}},
        )
        return Response({
            "id": ota_ona.id,
            "farzandlar": [
                {"id": t.id, "ism": t.get_full_name() or t.username}
                for t in ota_ona.farzandlar.all()
            ],
        })


def _rasm_korish_ruxsati(request_user, target_user):
    """2026-08-15: profil rasmini kim ko'ra oladi — o'zi, owner/admin
    (hammasi), o'qituvchi (o'z guruhidagi talabalar), ota-ona (o'z
    farzandi), bir xil guruhdagi talabalar (klassdoshlar)."""
    if request_user.pk == target_user.pk:
        return True
    if owner_mi(request_user) or request_user.role == User.Role.ADMIN:
        return True

    from academics.models import Guruh

    if request_user.role == User.Role.TEACHER:
        return Guruh.objects.filter(oqituvchi=request_user, talabalar=target_user).exists()
    if request_user.role == User.Role.PARENT:
        return target_user.ota_ona_id == request_user.pk
    return Guruh.objects.filter(talabalar=request_user).filter(talabalar=target_user).exists()


class FoydalanuvchiRasmView(APIView):
    """Profil rasmi — yuklash (POST) va ko'rish (GET).

    R2 bucket YOPIQ (`config/settings.py` B3.2 izohi), shuning uchun
    to'g'ridan-to'g'ri `.url` bilan emas, shu autentifikatsiyalangan
    endpoint orqali uzatiladi — mavjud `KursMashqRasmView` bilan bir xil
    naqsh.

    RUXSATLAR (2026-08-09 qarori):
      * QO'YISH (POST) — FAQAT foydalanuvchining O'ZI. Avval owner/admin
        ham boshqa odamga rasm qo'ya olardi; foydalanuvchi buni keraksiz
        deb topdi (profil rasmi shaxsiy narsa). `Foydalanuvchilar`
        sahifasidagi yuklash tugmasi ham shu bilan olib tashlandi.
      * O'CHIRISH (DELETE) — o'zi, VA owner/admin (moderatsiya uchun:
        nomaqbul rasm qo'yilsa kimdir olib tashlashi kerak). Boshqa
        odamning rasmi o'chirilganda SABAB (`izoh`) MAJBURIY va u
        egasiga "Ogohlantirish" bildirishnomasi bo'lib boradi — aks
        holda rasm jimgina yo'qolib, odam nima uchun ekanini bilmasdi.
        Admin owner'ning rasmiga TEGA OLMAYDI (huquq zinapoyasi).
      * KO'RISH (GET) — 2026-08-15 qarori: o'zi, owner/admin (hammasi),
        o'qituvchi (FAQAT o'z guruhidagi talabalar), ota-ona (FAQAT o'z
        farzandi), va bir xil guruhdagi talabalar (klassdoshlar) bir-
        birining rasmini ko'radi. Boshqa guruhdagi/markazdagi begona
        foydalanuvchi ID orqali ko'ra olmaydi — avval BUTUNLAY ochiq edi.
        Oqibat: reytingda (markaz bo'yicha, guruhlararo) boshqa
        guruhdagi talabalar uchun rasm o'rniga standart ikonka chiqadi
        — bu ATAYLAB shunday (foydalanuvchi tasdiqladi)."""

    permission_classes = [IsAuthenticated]
    # JSONParser — DELETE tanasida `izoh` JSON ko'rinishida keladi;
    # fayl parserlari yolg'iz qolsa u o'qilmasdi.
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    # 2 MB — avatar 200x200 atrofida ko'rsatiladi, bundan kattasi
    # keraksiz. Cheklov SHART: `user.rasm.save()` model validatorlarini
    # (`full_clean`) chaqirmaydi, ya'ni bu tekshiruvsiz istalgan hajmdagi
    # istalgan fayl to'g'ridan-to'g'ri R2'ga tushib ketardi.
    MAKS_HAJM = 2 * 1024 * 1024

    def get(self, request, pk):
        from django.http import FileResponse, Http404

        user = get_object_or_404(User, pk=pk)
        if not _rasm_korish_ruxsati(request.user, user):
            raise Http404
        if not user.rasm:
            raise Http404
        javob = FileResponse(user.rasm.open("rb"))
        javob["Content-Disposition"] = "inline"
        return javob

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if request.user.pk != user.pk:
            return Response({"detail": "Faqat o'z rasmingizni qo'yishingiz mumkin"}, status=403)
        rasm = request.FILES.get("rasm")
        if not rasm:
            return Response({"detail": "rasm majburiy"}, status=400)
        if rasm.size > self.MAKS_HAJM:
            return Response(
                {"detail": f"Rasm hajmi {self.MAKS_HAJM // (1024 * 1024)} MB dan oshmasin"},
                status=400,
            )
        # Kengaytmaga ishonib bo'lmaydi (".png" deb atalgan istalgan fayl
        # yuborilishi mumkin) — mazmuni haqiqatda rasmmi, shuni tekshiramiz,
        # aks holda ochilmaydigan fayl saqlanib, avatar buzilib qolardi.
        from PIL import Image, UnidentifiedImageError

        try:
            Image.open(rasm).verify()
        except (UnidentifiedImageError, OSError, ValueError):
            return Response({"detail": "Fayl rasm emas yoki buzuq"}, status=400)
        rasm.seek(0)  # `verify` faylni oxirigacha o'qidi

        # Eskisini O'CHIRAMIZ. Aks holda `save()` yangi nom bilan yozadi
        # (Django takrorlanuvchi nomga suffiks qo'shadi) va eski fayl R2'da
        # yetim qolardi — har almashtirishda yana bitta axlat fayl.
        if user.rasm:
            user.rasm.delete(save=False)
        user.rasm.save(f"{user.id}_{rasm.name}", rasm, save=True)
        return Response({"id": user.id, "rasm_url": f"/api/foydalanuvchilar/{user.id}/rasm/"})

    def delete(self, request, pk):
        u = request.user
        user = get_object_or_404(User, pk=pk)
        ozi = u.pk == user.pk
        moderator = owner_mi(u) or u.role == User.Role.ADMIN
        if not (ozi or moderator):
            return Response({"detail": "Ruxsat yo'q"}, status=403)
        # Admin owner'ning rasmini o'chira olmaydi — aks holda pastroq
        # huquqli rol yuqorisiga ta'sir qilardi.
        if not ozi and user.is_superuser and not owner_mi(u):
            return Response({"detail": "Owner'ning rasmiga tega olmaysiz"}, status=403)

        izoh = ""
        if not ozi:
            izoh = str(request.data.get("izoh") or "").strip()
            if not izoh:
                return Response(
                    {"detail": "O'chirish sababini yozing — u foydalanuvchiga xabar bo'lib boradi"},
                    status=400,
                )
            izoh = izoh[:1000]

        if not user.rasm:
            return Response({"detail": "Bu foydalanuvchida rasm yo'q"}, status=400)
        user.rasm.delete(save=True)

        if not ozi:
            # Kalitga aniq vaqt qo'shiladi: rasm bir necha marta
            # o'chirilishi mumkin va HAR BIRI alohida xabar bo'lishi kerak
            # (`kalit` unique — barqaror kalit ikkinchi xabarni yutib
            # yuborardi).
            Bildirishnoma.objects.create(
                foydalanuvchi=user,
                turi=Bildirishnoma.Turi.OGOHLANTIRISH,
                kalit=f"ogohlantirish:rasm:{timezone.now().isoformat()}"[:200],
                sarlavha="Profil rasmingiz o'chirildi",
                matn=izoh,
            )
            logla(
                foydalanuvchi=u,
                harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
                obyekt=user,
                obyekt_turi="Foydalanuvchi",
                ozgarishlar={"rasm": {"eski": "bor edi", "yangi": "o'chirildi"}, "izoh": izoh},
            )
        return Response(status=204)


class QurilmaTiklashView(APIView):
    """Owner/admin uchun — foydalanuvchining BARCHA qurilmalarini
    tozalash (2026-08-12, 2026-08-13 ko'p-qurilmali qilib yangilandi).
    `qurilmalar` bo'sh bo'lsa keyingi login(lar) AVTOMATIK yangi
    ro'yxatni (limitgacha) to'ldiradi — bu yerda faqat RO'YXATNI
    TOZALASH kifoya.

    `qurilma_limiti`ga TEGMAYDI — faqat ro'yxatni bo'shatadi. Limitni
    o'zgartirish uchun alohida `QurilmaLimitiView`.

    Parol tiklashdan ATAYLAB MUSTAQIL (foydalanuvchi qarori) — ikkalasi
    bog'lanmagan, alohida harakat sifatida qoladi.

    Sabab (`izoh`) MAJBURIY — profil rasmi o'chirishdagi bilan bir xil
    naqsh: foydalanuvchi nega qayta "yangi qurilma" sifatida kirishini
    bilishi kerak."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        u = request.user
        if not (owner_mi(u) or u.role == User.Role.ADMIN):
            return Response({"detail": "Faqat owner/admin uchun"}, status=403)
        user = get_object_or_404(User, pk=pk)
        if user.is_superuser and not owner_mi(u):
            return Response({"detail": "Owner'ning qurilmasiga tega olmaysiz"}, status=403)

        izoh = str(request.data.get("izoh") or "").strip()
        if not izoh:
            return Response(
                {"detail": "Tiklash sababini yozing — u foydalanuvchiga xabar bo'lib boradi"},
                status=400,
            )
        izoh = izoh[:1000]

        if not user.qurilmalar:
            return Response({"detail": "Bu foydalanuvchida qurilma qulfi yo'q"}, status=400)
        user.qurilmalar = []
        user.save(update_fields=["qurilmalar"])

        Bildirishnoma.objects.create(
            foydalanuvchi=user,
            turi=Bildirishnoma.Turi.OGOHLANTIRISH,
            kalit=f"ogohlantirish:qurilma-tiklash:{timezone.now().isoformat()}"[:200],
            sarlavha="Qurilma qulfi tiklandi",
            matn=(
                f"{izoh}\n\nKeyingi login qilgan qurilmangiz endi 'asosiy' "
                "sifatida qayta belgilanadi."
            ),
        )
        logla(
            foydalanuvchi=u,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=user,
            obyekt_turi="Foydalanuvchi",
            ozgarishlar={"qurilmalar": {"eski": "bor edi", "yangi": "tozalandi"}, "izoh": izoh},
        )
        return Response(status=204)


class QurilmaLimitiView(APIView):
    """Owner uchun (2026-08-13, foydalanuvchi qarori: "hozircha bundan
    huquq faqat ownerda bo'lsin, keyinchalik adminga ham berish imkoni
    bilan" — shuning uchun bu yerda FAQAT `owner_mi` tekshiriladi,
    admin emas, lekin kod tuzilishi keyin adminga ochish oson bo'lsin
    deb `QurilmaTiklashView`bilan bir xil naqshda yozildi) —
    foydalanuvchining ruxsat etilgan qurilmalar sonini (`qurilma_limiti`)
    o'zgartiradi.

    Ro'yxatni (`qurilmalar`) TOZALAMAYDI — limit oshirilsa, bloklangan
    foydalanuvchi hech qanday qo'shimcha harakatsiz, keyingi login
    urinishida AVTOMATIK kira oladi (`_qurilma_tekshir`)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        u = request.user
        if not owner_mi(u):
            return Response({"detail": "Faqat owner uchun"}, status=403)
        user = get_object_or_404(User, pk=pk)

        limit = request.data.get("limit")
        if not isinstance(limit, int) or limit < 1 or limit > 20:
            return Response({"detail": "limit 1 dan 20 gacha butun son bo'lishi kerak"}, status=400)

        eski = user.qurilma_limiti
        user.qurilma_limiti = limit
        user.save(update_fields=["qurilma_limiti"])

        logla(
            foydalanuvchi=u,
            harakat=FaoliyatYozuvi.Harakat.OZGARTIRISH,
            obyekt=user,
            obyekt_turi="Foydalanuvchi",
            ozgarishlar={"qurilma_limiti": {"eski": eski, "yangi": limit}},
        )
        return Response({"qurilma_limiti": limit})


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
    owner va admin (istalgan foydalanuvchi — 2026-08-14: avval admin
    bu yerda 403 olardi, TalabalarView'da esa hammasini ko'rar edi,
    nomuvofiqlik tuzatildi), teacher (FAQAT o'z guruhidagi talabalar —
    `Guruh.talabalar`), ota-ona (FAQAT O'Z farzandi — 2026-08-09, avval
    bu shox yo'q edi va ota-ona 403 olardi)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        talaba = get_object_or_404(User, pk=pk)
        u = request.user
        if u.pk == talaba.pk or owner_mi(u) or u.role == User.Role.ADMIN:
            pass
        elif u.role == User.Role.TEACHER:
            from academics.models import Guruh

            if not Guruh.objects.filter(oqituvchi=u, talabalar=talaba).exists():
                return Response({"detail": "Ruxsat yo'q"}, status=403)
        elif u.role == User.Role.PARENT:
            if talaba.ota_ona_id != u.pk:
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
                {
                    "id": u.id, "ism": u.get_full_name() or u.username, "username": u.username,
                    # 2026-08-09: profil rasmini o'chirish uchun (yuqoridagi
                    # `TalabalarView` izohiga qarang). Bu sahifaga faqat
                    # owner/admin kiradi, ya'ni qo'shimcha rol tekshiruvi
                    # frontendda shart emas.
                    "rasm_url": f"/api/foydalanuvchilar/{u.id}/rasm/" if u.rasm else None,
                    "qurilma_bormi": bool(u.qurilmalar),
                    "qurilma_limiti": u.qurilma_limiti,
                    "qurilmalar_soni": len(u.qurilmalar),
                    "bio": u.bio,
                    "telefon": u.telefon,
                    "ota_ona_telefon": u.ota_ona_telefon,
                    "tugilgan_sana": u.tugilgan_sana,
                }
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
                    # 2026-08-09: "ko'rinadigan panellar" tanlovi endi ROLGA
                    # qarab chiqadi (`panelTanloviOl`). Bu ro'yxatda faqat
                    # talaba bo'lsa ham, rol ANIQ berilsin — komponent
                    # taxminga tayanmasin.
                    "role": t.role,
                    # 2026-08-09: owner/admin nomaqbul profil rasmini shu
                    # sahifadan o'chira olishi uchun (`FoydalanuvchiRasmView`).
                    # Adminda "Foydalanuvchilar" sahifasi YO'Q, shuning uchun
                    # unga yagona yo'l shu.
                    "rasm_url": f"/api/foydalanuvchilar/{t.id}/rasm/" if t.rasm else None,
                    "qurilma_bormi": bool(t.qurilmalar),
                    "qurilma_limiti": t.qurilma_limiti,
                    "qurilmalar_soni": len(t.qurilmalar),
                    "bio": t.bio,
                    "telefon": t.telefon,
                    "ota_ona_telefon": t.ota_ona_telefon,
                    "tugilgan_sana": t.tugilgan_sana,
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


class ProfilTahrirlashView(APIView):
    """Joriy foydalanuvchi o'z profilini tahrirlaydi (2026-08-14,
    foydalanuvchi talabi: "chap tomon tepada pochtam turibdi, ism
    familiyaga almashtira olay" + "yana nimalar qo'shish mumkin"
    so'roviga javoban qo'shilgan maydonlar).

    Ism — butun ism `first_name`ga yoziladi (`last_name` ishlatilmaydi,
    loyihada ajratilmagan). `bio` — OCHIQ (admin/owner ro'yxatlarida
    chiqadi). `telefon`/`ota_ona_telefon`/`tugilgan_sana` — SHAXSIY,
    faqat admin/owner ko'radi, boshqa endpoint'larga qo'shilmagan.
    ("maqsad"/"sabab" 2026-08-14'da qo'shilib, shu kuni foydalanuvchi
    qarori bilan olib tashlandi — "bu maydonlar kerak emas".)

    Barcha maydonlar IXTIYORIY — faqat yuborilganlari yangilanadi,
    yuborilmagani tegilmaydi (frontend qisman formani ham yubora oladi)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        u = request.user
        yangilanadigan = []

        if "ism" in request.data:
            ism = str(request.data.get("ism") or "").strip()
            if not ism:
                return Response({"detail": "Ism bo'sh bo'lmasin"}, status=400)
            if len(ism) > 150:
                return Response({"detail": "Ism juda uzun (150 belgigacha)"}, status=400)
            u.first_name = ism
            yangilanadigan.append("first_name")

        if "bio" in request.data:
            bio = str(request.data.get("bio") or "").strip()
            if len(bio) > 500:
                return Response({"detail": "'O'zim haqimda' 500 belgigacha bo'lsin"}, status=400)
            u.bio = bio
            yangilanadigan.append("bio")

        if "telefon" in request.data:
            telefon = str(request.data.get("telefon") or "").strip()
            if len(telefon) > 20:
                return Response({"detail": "Telefon raqami juda uzun"}, status=400)
            u.telefon = telefon
            yangilanadigan.append("telefon")

        if "ota_ona_telefon" in request.data:
            ota_ona_telefon = str(request.data.get("ota_ona_telefon") or "").strip()
            if len(ota_ona_telefon) > 20:
                return Response({"detail": "Telefon raqami juda uzun"}, status=400)
            u.ota_ona_telefon = ota_ona_telefon
            yangilanadigan.append("ota_ona_telefon")

        if "tugilgan_sana" in request.data:
            sana = request.data.get("tugilgan_sana") or None
            u.tugilgan_sana = sana
            yangilanadigan.append("tugilgan_sana")

        if not yangilanadigan:
            return Response({"detail": "Hech narsa yuborilmadi"}, status=400)

        try:
            u.full_clean(validate_unique=False)
        except DjangoValidationError as e:
            return Response({"detail": " ".join(e.messages)}, status=400)

        u.save(update_fields=yangilanadigan)
        return Response({
            "ism": u.get_full_name(),
            "bio": u.bio,
            "telefon": u.telefon,
            "ota_ona_telefon": u.ota_ona_telefon,
            "tugilgan_sana": u.tugilgan_sana,
        })


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
    throttling qo'shilgan (login urinishlar soni cheklanadi).

    2026-08-12: hisobni boshqalar bilan bo'lishmaslik uchun — OWNER'dan
    boshqa har bir foydalanuvchi FAQAT `qurilmalar` ro'yxatidagi (eng
    ko'pi bilan `qurilma_limiti` ta, standart 1) qurilmalardan kira
    oladi. Frontend har login so'rovida `qurilma_id` yuboradi
    (localStorage'da saqlangan tasodifiy ID). Parol TO'G'RI bo'lsa-da,
    yangi qurilma limitdan oshsa token BERILMAYDI (javob 403'ga
    almashtiriladi). Ro'yxat limitga yetmagan bo'lsa — kelgan ID
    AVTOMATIK qo'shiladi, qo'shimcha tasdiq shart emas (2026-08-13:
    owner qurilma limitini oshirsa, foydalanuvchi qayta urinib
    avtomatik kira oladi — alohida "ruxsat berish" tugmasi kerak
    emas)."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        javob = super().post(request, *args, **kwargs)
        if javob.status_code == 200:
            user = User.objects.filter(username=request.data.get("username")).first()
            if user is not None:
                if not owner_mi(user):
                    qurilma_javobi = _qurilma_tekshir(request, user)
                    if qurilma_javobi is not None:
                        return qurilma_javobi
                LoginHistory.objects.create(foydalanuvchi=user, rol=user.role)
        return javob


def _qurilma_tekshir(request, user):
    """OWNER bo'lmagan foydalanuvchi uchun qurilma cheklovi — mos kelmasa
    403 Response qaytaradi (login rad etiladi), mos kelsa/ro'yxatga yangi
    qo'shilsa None qaytaradi (davom etaveradi).

    2026-08-14: `select_for_update()` bilan qatorni qulflab qayta o'qiymiz
    — parallel (bir vaqtdagi) ikkita login urinishi limitni chetlab
    o'tishining oldini olish uchun (avval check-then-act race condition
    bor edi: ikkala so'rov ham "hali joy bor" deb o'qib, ikkalasi ham
    qo'shilib ketishi mumkin edi)."""
    qurilma_id = (request.data.get("qurilma_id") or "").strip()
    if not qurilma_id:
        return Response(
            {"detail": "Qurilma identifikatori yuborilmadi", "kod": "qurilma_id_yoq"},
            status=400,
        )

    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        if qurilma_id in user.qurilmalar:
            return None
        if len(user.qurilmalar) < user.qurilma_limiti:
            user.qurilmalar = [*user.qurilmalar, qurilma_id]
            user.save(update_fields=["qurilmalar"])
            return None

    for admin in User.objects.filter(role=User.Role.ADMIN) | User.objects.filter(is_superuser=True):
        Bildirishnoma.objects.create(
            foydalanuvchi=admin,
            turi=Bildirishnoma.Turi.OGOHLANTIRISH,
            kalit=f"ogohlantirish:qurilma:{user.id}:{timezone.now().isoformat()}"[:200],
            sarlavha="Boshqa qurilmadan kirishga urinish",
            matn=(
                f"Foydalanuvchi {user.username} ruxsat etilgan "
                f"{user.qurilma_limiti} ta qurilmadan tashqari yana 1 ta "
                "qurilmadan kirishga urindi. Agar bu haqiqatan shu "
                "foydalanuvchi bo'lsa (yangi telefon/kompyuter), 'Qurilma "
                "limiti'ni oshiring — keyingi urinishda avtomatik kiradi. "
                "Yoki 'Qurilmani tiklash' orqali eski qurilmalarni tozalab, "
                "qaytadan boshlang."
            ),
        )
    return Response(
        {
            "detail": "Bu hisob boshqa qurilmada faollashtirilgan. Administratorga murojaat qiling.",
            "kod": "qurilma_mos_emas",
        },
        status=403,
    )


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


class BildirishnomalarView(APIView):
    """Owner uchun — ilova ichidagi bildirishnomalar (2026-08-08).

    GET — ro'yxat. Har chaqiruvda `CHANGELOG.md` bilan sinxronlanadi:
    yangi reliz bo'lsa, shu yerda yozuvga aylanadi. Alohida webhook yoki
    fon-jarayon kerak emas — tafsilot `accounts.relizlar` izohida.

    POST — o'qilgan deb belgilash. Tanasi: {"id": N} yoki
    {"hammasi": true}.

    2026-08-09: avval FAQAT owner kira olardi (yagona manba reliz xabari
    edi). Endi HAR FOYDALANUVCHI o'zinikini ko'radi — "Ogohlantirish"
    turi qo'shildi (profil rasmi o'chirilganda egasiga boradi), busiz
    xabar manzilига yetmasdi. Har kim FAQAT o'zining yozuvlarini
    ko'radi/belgilaydi (`request.user.bildirishnomalar`), ya'ni
    `pk` bilan boshqasiga o'tish yo'li yo'q.

    Reliz sinxronizatsiyasi esa faqat owner uchun ishlaydi — reliz
    xabari boshqa rollarga tegishli emas."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if owner_mi(request.user):
            relizlarni_sinxronla(request.user)
        yozuvlar = request.user.bildirishnomalar.all()[:50]
        return Response({
            "oqilmagan": request.user.bildirishnomalar.filter(oqilgan=False).count(),
            "bildirishnomalar": [
                {
                    "id": b.id,
                    "turi": b.turi,
                    "sarlavha": b.sarlavha,
                    "matn": b.matn,
                    "oqilgan": b.oqilgan,
                    "sana": b.created_at.isoformat(),
                }
                for b in yozuvlar
            ],
        })

    def post(self, request):
        qatorlar = request.user.bildirishnomalar.filter(oqilgan=False)
        if not request.data.get("hammasi"):
            bildirishnoma_id = request.data.get("id")
            if not isinstance(bildirishnoma_id, int):
                return Response({"detail": "id yoki hammasi majburiy"}, status=400)
            qatorlar = qatorlar.filter(pk=bildirishnoma_id)
        soni = qatorlar.update(oqilgan=True)
        return Response({"belgilandi": soni,
                         "oqilmagan": request.user.bildirishnomalar.filter(oqilgan=False).count()})
