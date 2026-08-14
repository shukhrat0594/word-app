"""Backup — faqat baza (Postgres/SQLite) yozuvlari, R2/media fayllar EMAS
(2026-08-15, Shuhrat bilan kelishilgan qaror — Render->Railway ko'chirish
uchun minimal versiya).

Nega media kiritilmagan: barcha rasm/audio (jumladan Markaz.logo — R2
storage'ga bog'liqligi 2026-08-15 tekshirilgan) `FileField`da faqat YO'L
sifatida saqlanadi, haqiqiy fayl R2'da turadi. Ikkala server (Render,
Railway) BIR XIL R2 bucket'ga ulangan bo'lsa (foydalanuvchi tasdiqladi —
Render'dan nusxa ko'chirilgan), baza ko'chsa fayllar AVTOMATIK to'g'ri
ishlaydi — alohida yuklab/qayta joylashtirish shart emas.

Kelajakda to'liq reja (REJA.md "Server/backup rejasi") uchtala tugmani
("Kompyuterga yuklab olish" / "R2'ga saqlash" / "tiklash") nazarda tutadi —
bu yerda faqat birinchi va uchinchisi, va ikkalasi ham FAQAT baza."""

import io
import json
import os
import tempfile
import zipfile
from datetime import datetime

from django.core.management import call_command
from django.db import transaction
from django.http import FileResponse
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import owner_mi

# Bu jadvallar bazadan-bazaga ko'chirilganda MUAMMO chiqarishi mumkin —
# ContentType/Permission har muhitda MIGRATSIYALAR TARTIBIGA qarab turli
# avtomatik ID bilan yaratiladi (`migrate` o'zi yaratadi, dumpdata/loaddata
# shart emas). Sessiya/JWT qora ro'yxati va admin logi — vaqtinchalik,
# ish yuritish ma'lumoti emas, ko'chirish shart emas.
CHIQARIB_TASHLANADIGAN_APPLAR = [
    "contenttypes",
    "auth.permission",
    "admin.logentry",
    "sessions.session",
    "token_blacklist",
]


class BackupYuklabOlishView(APIView):
    """GET — butun bazani (yuqoridagi ro'yxatdan tashqari) JSON'ga olib,
    ZIP qilib, browserga to'g'ridan-to'g'ri yuklab beradi. Faqat owner."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)

        buffer = io.StringIO()
        call_command(
            "dumpdata",
            *[f"--exclude={a}" for a in CHIQARIB_TASHLANADIGAN_APPLAR],
            natural_foreign=True,
            natural_primary=True,
            indent=2,
            stdout=buffer,
        )

        vaqt_belgisi = datetime.now().strftime("%Y-%m-%d_%H%M")
        fayl_nomi = f"backup_{vaqt_belgisi}.zip"

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("baza.json", buffer.getvalue())
        zip_buffer.seek(0)

        javob = FileResponse(zip_buffer, as_attachment=True, filename=fayl_nomi)
        return javob


class BackupdanTiklashView(APIView):
    """POST — yuklangan ZIP ichidagi `baza.json`ni `loaddata` bilan
    bazaga qayta yozadi. Faqat owner, VA `tasdiqlash="HA"` maydoni
    majburiy (frontend'dagi tasdiqlash dialogisiz bu endpoint ishlamaydi
    — tasodifan chaqirilishdan himoya)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if not owner_mi(request.user):
            return Response({"detail": "Faqat owner uchun"}, status=403)

        if request.data.get("tasdiqlash") != "HA":
            return Response(
                {"detail": "Tasdiqlash majburiy — bu amal joriy ma'lumotni butunlay almashtiradi"},
                status=400,
            )

        fayl = request.FILES.get("fayl")
        if not fayl:
            return Response({"detail": "ZIP fayl yuborilmadi"}, status=400)

        try:
            with zipfile.ZipFile(fayl) as z:
                nomlar = [n for n in z.namelist() if n.endswith(".json")]
                if not nomlar:
                    return Response({"detail": "ZIP ichida .json fayl topilmadi"}, status=400)
                xom_json = z.read(nomlar[0]).decode("utf-8")
        except zipfile.BadZipFile:
            return Response({"detail": "Fayl to'g'ri ZIP emas"}, status=400)

        try:
            # Format tekshiruvi — noto'g'ri JSON bo'lsa `loaddata` ichida
            # tushunarsiz xato berishi mumkin, oldindan aniq xabar beramiz.
            json.loads(xom_json)
        except (ValueError, TypeError):
            return Response({"detail": "JSON formati noto'g'ri"}, status=400)

        # `loaddata` fayl yo'lini kutadi (stdin orqali maxsus stream
        # qabul qilmaydi) — shuning uchun vaqtinchalik `.json` faylga
        # yozib, o'sha yo'lni beramiz.
        vaqtinchalik_yol = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as f:
                f.write(xom_json)
                vaqtinchalik_yol = f.name
            with transaction.atomic():
                call_command("loaddata", vaqtinchalik_yol)
        except Exception as e:
            return Response(
                {"detail": f"Tiklashda xatolik ({type(e).__name__}): {e}"},
                status=400,
            )
        finally:
            if vaqtinchalik_yol and os.path.exists(vaqtinchalik_yol):
                os.remove(vaqtinchalik_yol)

        return Response({"detail": "Baza muvaffaqiyatli tiklandi"})
