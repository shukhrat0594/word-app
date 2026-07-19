"""Production bootstrap — Render'da har deploy'da xavfsiz ishlaydi (idempotent).

Shell'siz muhit (Render Free) uchun: build command oxiriga qo'shiladi.
Uch ish qiladi, har biri faqat kerak bo'lsa:
  1. Markaz yo'q bo'lsa — "Utmost o'quv markazi" yaratadi.
  2. Superuser (owner) yo'q bo'lsa — OWNER_USERNAME/OWNER_PAROL env
     o'zgaruvchilaridan yaratadi. Mavjud foydalanuvchilarga TEGMAYDI —
     parol faqat yangi yaratilganda o'rnatiladi.
  3. O'yin kontenti (Soz) bo'sh bo'lsa — games/fixtures/oyinlar.json yuklaydi.
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
                user = User(
                    username=username,
                    role=User.Role.ADMIN,
                    markaz=markaz,
                    is_superuser=True,
                    is_staff=True,
                )
                user.set_password(parol)
                user.save()
                self.stdout.write(f"Owner yaratildi: {username}")
            else:
                self.stdout.write(
                    "OWNER_USERNAME/OWNER_PAROL berilmagan — owner yaratilmadi"
                )

        if Soz.objects.exists():
            self.stdout.write(f"O'yin kontenti mavjud: {Soz.objects.count()} so'z")
        else:
            call_command("loaddata", "oyinlar")
            self.stdout.write(f"O'yin kontenti yuklandi: {Soz.objects.count()} so'z")
