"""Pre-Intermediate kontent tuzatishlarini qo'lda qayta qo'llash.

Migratsiya 0020 buni deploy'da avtomatik bajaradi. Bu buyruq — qayta
urug'lantirgandan (`headway_pre_intermediate_*`) keyin uchun: seed fayllari
kontentni ESKI holida yozadi, tuzatishlar esa migratsiyada qolgani uchun
qayta qo'llanmaydi.

    python manage.py pre_intermediate_tuzat

Idempotent: qayta yugurtirish xavfsiz.
"""

from django.core.management.base import BaseCommand

from courses.grammar_spot_tuzatish import tuzat as gs_tuzat
from courses.models import KursMashq, KursTugun
from courses.pre_intermediate_tuzatish import tuzat


class Command(BaseCommand):
    help = "Pre-Intermediate mashq turlari tuzatishlarini qo'llaydi (idempotent)"

    def handle(self, *args, **options):
        for izoh, bajarildi in tuzat(KursTugun, KursMashq):
            belgi = "qo'llandi" if bajarildi else "allaqachon joyida"
            self.stdout.write(f"  {izoh}: {belgi}")
        self.stdout.write("  GRAMMAR SPOT javoblari:")
        for izoh, bajarildi in gs_tuzat(KursTugun, KursMashq):
            belgi = "qo'llandi" if bajarildi else "allaqachon joyida"
            self.stdout.write(f"    {izoh}: {belgi}")
