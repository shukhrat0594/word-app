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
  7. BIR MARTALIK (2026-07-29(4)): Beginner...Upper-Intermediate (5 ta
     daraja, IELTS/CEFR'dan tashqari) ostidagi BARCHA mavjud kontentni
     (Unit, mashq, audio, rasm — nima bo'lsa) o'chiradi — foydalanuvchi
     tasdiqlagan ("ha bo'sh qaytsin"), admin "Unit soni" mexanizmidan
     BOSHIDAN foydalanishi uchun.

     OGOHLANTIRISH — BU QADAM KEYINGI COMMIT'DA OLIB TASHLANADI: agar bu
     shu ko'rinishda (shartsiz o'chirish) doimiy qolib ketsa, HAR
     DEPLOY'DA admin keyinchalik yaratgan HAQIQIY Unitlarni ham
     o'chirib yuborardi (aynan shu xato avvalgi versiyada — faqat
     Beginner uchun — bor edi va TUZATILDI). Shuning uchun bu funksiya
     faqat BITTA deploy uchun mo'ljallangan, keyin darhol olib
     tashlanishi SHART.
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

        self._ingliz_darajalarni_tozala()

        call_command("wordapp_import")
        call_command("listening_yangi_mashqlar")
        call_command("writing_speaking_yangi_mashqlar")
        call_command("kurslar_urugla")
        call_command("kunlik_mashqlarni_ishga_tushir")

    def _ingliz_darajalarni_tozala(self):
        """2026-07-29(4), BITTA DEPLOY UCHUN: Beginner...Upper-Intermediate
        ostidagi BARCHA mavjud tugunlarni (Unit, mashq, audio, rasm —
        nima bo'lsa) o'chiradi — `kurslar_urugla`dan OLDIN chaqirilishi
        SHART, aks holda kurslar_urugla eski Unit'lar hali mavjud deb
        ularga tegmay qo'yar edi.

        BU FUNKSIYA KEYINGI COMMIT'DA OLIB TASHLANISHI SHART (yuqoridagi
        modul docstringiga qarang) — shartsiz o'chirish doimiy qolsa,
        admin keyin yaratgan haqiqiy Unitlarni ham yo'q qilib yuborardi."""
        daraja_kalitlari = (
            "beginner", "elementary", "pre_intermediate",
            "intermediate", "upper_intermediate",
        )
        jami = 0
        for daraja_kalit in daraja_kalitlari:
            daraja = KursTugun.objects.filter(kalit=daraja_kalit).first()
            if not daraja:
                continue
            bolalar = KursTugun.objects.filter(parent=daraja)
            soni = bolalar.count()
            if soni:
                bolalar.delete()
                jami += soni
        if jami:
            self.stdout.write(
                self.style.WARNING(
                    f"Ingliz tili darajalari tozalandi: {jami} ta tugun o'chirildi "
                    "(Beginner...Upper-Intermediate, admin Unit sonini qaytadan kiritadi)"
                )
            )
