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
"""

from decouple import config
from django.core.management import call_command
from django.core.management.base import BaseCommand

from accounts.models import Markaz, User
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

        call_command("wordapp_import")
        call_command("listening_yangi_mashqlar")
