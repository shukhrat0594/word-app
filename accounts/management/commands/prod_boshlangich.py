"""Production bootstrap — Render'da har deploy'da xavfsiz ishlaydi (idempotent).

Shell'siz muhit (Render Free) uchun: build command oxiriga qo'shiladi.
Uch ish qiladi, har biri faqat kerak bo'lsa:
  1. Markaz yo'q bo'lsa — "Utmost o'quv markazi" yaratadi.
  2. Superuser (owner) yo'q bo'lsa — OWNER_USERNAME/OWNER_PAROL env
     o'zgaruvchilaridan yaratadi. Mavjud foydalanuvchilarga TEGMAYDI —
     parol faqat yangi yaratilganda o'rnatiladi.
  3. O'yin kontenti (Soz) bo'sh bo'lsa — games/fixtures/oyinlar.json yuklaydi.
  4. word-app-backup'dan IELTS mashqlarini import qiladi (wordapp_import,
     ichkarida o'zi idempotent — audio fayllarni esa HAR safar qayta
     nusxalaydi, chunki disk har deploy'da tozalanadi).
  5. Gemini TTS bilan yozilgan yangi Listening mashqlarini qo'shadi
     (listening_yangi_mashqlar) — audio fayli repo'da tayyor bo'lsa faqat
     nusxalaydi (API chaqirmaydi), hali generatsiya qilinmagan bo'lsa
     bepul kvota bo'yicha urinadi va tugasa xatosiz to'xtaydi.
  6. Kunlik bulutdagi agent qo'shgan yangi mashqlarni bazaga kiritadi
     (kunlik_mashqlarni_ishga_tushir — 2026-07-22, /schedule orqali
     sozlangan kunlik avtomatik mashq qo'shish tizimi).
  7. BIR MARTALIK (2026-07-29): Beginner'ning eski, qattiq kodlangan 14 ta
     Headway Unit'ini (talaba javoblari bilan birga) o'chiradi — Beginner
     endi boshqa darajalar bilan bir xil "admin Unit sonini belgilaydi"
     mexanizmiga o'tkazilmoqda (foydalanuvchi talabi, tasdiqlangan:
     "Ha, o'chir va qaytadan qur"). `kurslar_urugla`dan OLDIN ishga
     tushishi SHART — aks holda kurslar_urugla eski Unit'lar hali
     mavjud deb ularga tegmay qo'yar edi. Idempotent: Beginner'da
     unit_darsi=True tugun qolmagach, keyingi deploy'larda hech narsa
     qilmaydi (bo'sh filter — 0 ta o'chiriladi).
"""

from decouple import config
from django.core.management import call_command
from django.core.management.base import BaseCommand

from accounts.models import Markaz, User
from courses.models import KursTugun
from exercises.models import ImtihonTest, Mashq
from games.models import Soz


class Command(BaseCommand):
    help = "Production boshlang'ich ma'lumotlari (idempotent)"

    def handle(self, *args, **options):
        markaz = Markaz.objects.first()
        if not markaz:
            markaz = Markaz.objects.create(name="Utmost o'quv markazi")
            self.stdout.write("Markaz yaratildi: Utmost o'quv markazi")
        else:
            self.stdout.write(f"Markaz mavjud: {markaz.name}")

        # Bitta markaz rejimi: barcha kontent shu yagona markazga tegishli
        # bo'lishi shart. Eski kod ba'zan request.user.markaz'ni ishlatgan
        # bo'lishi mumkin edi — mos kelmagan yozuvlarni tuzatamiz.
        notogri_mashq = Mashq.objects.exclude(markaz=markaz).update(markaz=markaz)
        notogri_test = ImtihonTest.objects.exclude(markaz=markaz).update(markaz=markaz)
        if notogri_mashq or notogri_test:
            self.stdout.write(
                f"Markaz nomuvofiqligi tuzatildi: {notogri_mashq} mashq, {notogri_test} test"
            )

        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write("Owner mavjud — tegilmadi")
        else:
            username = config("OWNER_USERNAME", default="")
            parol = config("OWNER_PAROL", default="")
            if username and parol:
                # Hisob Google login orqali (student sifatida) allaqachon
                # ochilgan bo'lishi mumkin — u holda owner darajasiga
                # ko'tariladi; mavjud parolga tegilmaydi.
                user, created = User.objects.get_or_create(username=username)
                user.role = User.Role.ADMIN
                user.markaz = markaz
                user.is_superuser = True
                user.is_staff = True
                if created or not user.has_usable_password():
                    user.set_password(parol)
                user.save()
                holat = "yaratildi" if created else "owner darajasiga ko'tarildi"
                self.stdout.write(f"Owner {holat}: {username}")
            else:
                self.stdout.write(
                    "OWNER_USERNAME/OWNER_PAROL berilmagan — owner yaratilmadi"
                )

        if Soz.objects.exists():
            self.stdout.write(f"O'yin kontenti mavjud: {Soz.objects.count()} so'z")
        else:
            call_command("loaddata", "oyinlar")
            self.stdout.write(f"O'yin kontenti yuklandi: {Soz.objects.count()} so'z")

        self._beginner_eski_unitlarni_tozala()

        call_command("wordapp_import")
        call_command("listening_yangi_mashqlar")
        call_command("writing_speaking_yangi_mashqlar")
        call_command("kurslar_urugla")
        call_command("kunlik_mashqlarni_ishga_tushir")

    def _beginner_eski_unitlarni_tozala(self):
        """2026-07-29, bir martalik: Beginner'ning qattiq kodlangan 14 ta
        Headway Unit'ini (talaba javoblari bilan birga, KASKAD) o'chiradi
        — Beginner ham endi boshqa darajalar kabi admin panelidan "Unit
        soni" orqali qayta quriladi. `kurslar_urugla`dan OLDIN chaqirilishi
        SHART (docstring'ga qarang)."""
        beginner = KursTugun.objects.filter(kalit="beginner").first()
        if not beginner:
            return
        eski_unitlar = KursTugun.objects.filter(parent=beginner, unit_darsi=True)
        soni = eski_unitlar.count()
        if not soni:
            return  # allaqachon tozalangan (yoki hali yaratilmagan)
        eski_unitlar.delete()
        self.stdout.write(
            self.style.WARNING(
                f"Beginner'ning {soni} ta eski Unit'i o'chirildi "
                "(yangi Unit-soni mexanizmiga o'tish, 2026-07-29)"
            )
        )
