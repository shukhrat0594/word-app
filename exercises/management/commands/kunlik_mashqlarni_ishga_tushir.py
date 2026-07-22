"""Kunlik bulutdagi (scheduled) agent qo'shgan yangi mashqlarni bazaga
kiritadi (2026-07-22, /schedule orqali sozlangan kunlik avtomatik mashq
qo'shish tizimi uchun).

Manba: exercises/import_data/kunlik_mashqlar.json — bulutdagi agent har
kuni shu faylga yangi yozuv(lar) qo'shib, git push qiladi. Bu buyruq
HAR deploy'da (prod_boshlangich orqali) ishga tushadi va faylni o'qib,
hali bazada yo'q yozuvlarni Mashq sifatida yaratadi.

Idempotent: "name"+"bolim"+"tur" bo'yicha mavjud Mashq bo'lsa qayta
yaratilmaydi. Listening uchun audio Gemini TTS orqali generatsiya
qilinadi (listening_yangi_mashqlar.py bilan bir xil mexanizm) — bepul
kvota tugasa RateLimitTugadi'ni ushlab, xatosiz o'tkazib yuboradi
(keyingi deploy'da davom etadi).

2026-07-22 (2): ixtiyoriy "rasm_fayl" maydoni qo'shildi — bulutdagi agent
diagramma/jadval/grafik (masalan Writing Task 1) generatsiya qilib,
exercises/import_data/ ostiga PNG sifatida qo'shishi mumkin, shu maydonda
nisbiy yo'lini ko'rsatadi (masalan "kunlik_rasmlar/xxx.png") — bu buyruq
o'sha faylni o'qib, saqlash (R2/lokal) orqali Mashq.rasm'ga biriktiradi."""

import json

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from accounts.models import Markaz
from exercises.gemini_tts import RateLimitTugadi, audio_yarat
from exercises.models import Bolim, Mashq

IMPORT_DIR = settings.BASE_DIR / "exercises" / "import_data"
MANBA_FAYL = IMPORT_DIR / "kunlik_mashqlar.json"


class Command(BaseCommand):
    help = "Kunlik bulutdagi agent qo'shgan yangi mashqlarni (kunlik_mashqlar.json) bazaga kiritadi"

    def handle(self, *args, **options):
        if not MANBA_FAYL.exists():
            self.stdout.write("kunlik_mashqlar.json topilmadi — o'tkazib yuborildi")
            return

        markaz = Markaz.objects.first()
        if not markaz:
            self.stdout.write(self.style.WARNING("Markaz topilmadi — o'tkazib yuborildi"))
            return

        try:
            yozuvlar = json.loads(MANBA_FAYL.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"kunlik_mashqlar.json noto'g'ri formatda: {e}"))
            return

        yaratildi = 0
        for y in yozuvlar:
            bolim = y.get("bolim")
            tur = y.get("tur")
            name = y.get("name")
            if not (bolim and tur and name):
                self.stdout.write(self.style.WARNING("Yozuvda bolim/tur/name yetishmayapti — o'tkazib yuborildi"))
                continue
            if Mashq.objects.filter(markaz=markaz, name=name, bolim=bolim, tur=tur).exists():
                continue

            nomlik = slugify(name)[:60] or "mashq"

            mashq = Mashq(
                markaz=markaz, name=name, bolim=bolim, tur=tur, korinish="public",
                sun_iy_intellekt_yaratgan=True,
                matn=y.get("matn", ""),
                namuna_javob=y.get("namuna_javob", ""),
                savollar=y.get("savollar") or [],
            )

            if bolim == Bolim.LISTENING:
                transkript = y.get("transkript", "")
                if not transkript:
                    self.stdout.write(self.style.WARNING(f"{name}: transkript yo'q — o'tkazib yuborildi"))
                    continue
                try:
                    speakerlar = [("Speaker1", "Kore"), ("Speaker2", "Puck")] if y.get("dialog") else None
                    wav_bytes = audio_yarat(transkript, "gemini-2.5-flash-preview-tts", speakerlar=speakerlar)
                except RateLimitTugadi as e:
                    self.stdout.write(self.style.WARNING(f"{name}: audio limiti tugadi — {e}"))
                    continue
                nisbiy_yol = f"mashqlar/audio/kunlik-{nomlik}.wav"
                if default_storage.exists(nisbiy_yol):
                    default_storage.delete(nisbiy_yol)
                default_storage.save(nisbiy_yol, ContentFile(wav_bytes))
                mashq.audio_fayl = nisbiy_yol

            rasm_fayl = y.get("rasm_fayl")
            if rasm_fayl:
                manba_rasm = IMPORT_DIR / rasm_fayl
                if manba_rasm.exists():
                    kengaytma = manba_rasm.suffix or ".png"
                    nisbiy_rasm = f"mashqlar/rasm/kunlik-{nomlik}{kengaytma}"
                    if default_storage.exists(nisbiy_rasm):
                        default_storage.delete(nisbiy_rasm)
                    default_storage.save(nisbiy_rasm, ContentFile(manba_rasm.read_bytes()))
                    mashq.rasm = nisbiy_rasm
                else:
                    self.stdout.write(self.style.WARNING(f"{name}: rasm_fayl topilmadi ({rasm_fayl})"))

            try:
                mashq.full_clean()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"{name}: yaroqsiz — {e}"))
                continue
            mashq.save()
            yaratildi += 1
            self.stdout.write(self.style.SUCCESS(f"{name}: yaratildi"))

        self.stdout.write(self.style.SUCCESS(f"Jami yaratildi: {yaratildi}"))
