"""Sinov ma'lumoti — CRM'ni haqiqiy sonlar bilan ko'rish uchun.

Foydalanuvchi qarori (2026-09-14): prod zaxirasi EMAS, o'ylab topilgan
ma'lumot. Haqiqiy odamlarning ismi ishlatilmaydi.

Barcha yaratilgan yozuvlar BELGI bilan nomlanadi (`crm_sinov_` /
`[Sinov]`), shuning uchun `--tozala` aynan o'zi yaratganini o'chiradi va
haqiqiy ma'lumotga tegmaydi.

    python manage.py crm_sinov_malumot
    python manage.py crm_sinov_malumot --tozala
"""

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from academics.models import Guruh, GuruhAzoligi
from accounts.models import Markaz, User
from courses.models import KursTugun
from crm import mantiq
from crm.models import (
    AzolikMoliya,
    DarsJadvali,
    Filial,
    GuruhMoliya,
    Hisob,
    KursNarxi,
    Sozlama,
    Tolov,
)

BELGI_USER = "crm_sinov_"
BELGI_GURUH = "[Sinov] "

FILIALLAR = [
    ("Utmost Gor-Park", "Gorkiy parki yonida", "+998 71 200 00 01"),
    ("Utmost Chilonzor", "Chilonzor 9-kvartal", "+998 71 200 00 02"),
    ("Utmost Yunusobod", "Yunusobod 4-mavze", "+998 71 200 00 03"),
]

# (guruh nomi, filial indeksi, hafta kunlari, vaqt, narx bekor qilinsinmi)
# Nomlar ATAYLAB darajaga bog'liq emas ("IELTS guruhi" kabi): daraja
# aylanma tarzda beriladi, ya'ni nom bilan daraja mos kelmay qolardi va
# ekranda qarama-qarshilikdek ko'rinardi.
GURUHLAR = [
    ("Ertalabki A", 0, [1, 3, 5], ("09:00", "10:30"), None),
    ("Kechki A", 0, [0, 2, 4], ("18:00", "19:30"), None),
    ("Kunduzgi B", 1, [1, 3, 5], ("14:00", "15:30"), None),
    ("Kechki B", 1, [0, 2, 4], ("16:00", "17:30"), Decimal("520000")),
    ("Ertalabki C", 2, [1, 3], ("10:00", "11:30"), None),
]

ISMLAR = [
    "Aziz Qodirov", "Malika Yusupova", "Jasur Rahimov", "Dilnoza Karimova",
    "Sardor Tursunov", "Nigora Alimova", "Bekzod Sharipov", "Zilola Nazarova",
    "Otabek Ismoilov", "Madina Sobirova", "Rustam Xolmatov", "Shahnoza Umarova",
    "Farrux Ergashev", "Kamola Toshpulatova", "Javohir Mirzayev", "Sevara Qosimova",
    "Ulugbek Saidov", "Nodira Abdullayeva", "Temur Yoqubov", "Gulnora Rashidova",
]


class Command(BaseCommand):
    help = "CRM uchun sinov ma'lumoti yaratadi (o'ylab topilgan, haqiqiy emas)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tozala", action="store_true",
            help="Yaratilgan sinov ma'lumotini o'chiradi",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["tozala"]:
            return self._tozala()
        return self._yarat()

    # ── Tozalash ────────────────────────────────────────────────────

    def _tozala(self):
        guruhlar = Guruh.objects.filter(name__startswith=BELGI_GURUH)
        talabalar = User.objects.filter(username__startswith=BELGI_USER)

        # Hisob/Tolov `SET_NULL` bilan bog'langan, ya'ni talaba o'chsa ham
        # yozuv qoladi — sinov ma'lumotini tozalashda ularni ATAYLAB
        # aniq o'chiramiz, aks holda "yetim" qatorlar to'planib qolardi.
        Tolov.objects.filter(guruh__in=guruhlar).delete()
        Hisob.objects.filter(guruh__in=guruhlar).delete()

        guruh_soni = guruhlar.count()
        talaba_soni = talabalar.count()
        guruhlar.delete()
        talabalar.delete()
        filial_soni, _ = Filial.objects.filter(nomi__in=[f[0] for f in FILIALLAR]).delete()

        self.stdout.write(self.style.SUCCESS(
            f"Tozalandi: {guruh_soni} guruh, {talaba_soni} talaba, {filial_soni} filial yozuvi"
        ))

    # ── Yaratish ────────────────────────────────────────────────────

    def _yarat(self):
        markaz = Markaz.objects.first()
        if markaz is None:
            markaz = Markaz.objects.create(name="Utmost Academy")

        darajalar = self._darajalar(markaz)
        if not darajalar:
            self.stdout.write(self.style.ERROR(
                "Kurslar daraxtida daraja topilmadi. Avval Kurslar bo'limini to'ldiring."
            ))
            return

        bugun = timezone.localdate()
        Sozlama.objects.update_or_create(
            pk=Sozlama.objects.values_list("pk", flat=True).first(),
            defaults={"boshlangich_oy": mantiq.oy_boshi(bugun - timedelta(days=70))},
        )

        filiallar = [
            Filial.objects.get_or_create(
                markaz=markaz, nomi=nomi,
                defaults={"manzil": manzil, "telefon": telefon},
            )[0]
            for nomi, manzil, telefon in FILIALLAR
        ]

        # Narx darajaga osiladi — bitta guruhga emas (TZ 3.2).
        narxlar = [Decimal("660000"), Decimal("400000"), Decimal("480000")]
        for i, daraja in enumerate(darajalar[:3]):
            KursNarxi.objects.update_or_create(
                daraja=daraja, defaults={"narx": narxlar[i % len(narxlar)]}
            )

        talabalar = self._talabalar(markaz)
        guruhlar = self._guruhlar(markaz, darajalar, filiallar, bugun)
        self._azoliklar(guruhlar, talabalar, bugun)

        natija = mantiq.hisoblarni_generatsiya_qil()
        self._tolovlar()

        self.stdout.write(self.style.SUCCESS(
            f"Yaratildi: {len(filiallar)} filial, {len(guruhlar)} guruh, "
            f"{len(talabalar)} talaba, {natija['yaratildi']} hisob.\n"
            f"Ogohlantirish kutilgan guruhlar: 1 (narxi yo'q — ataylab).\n"
            f"Tozalash: python manage.py crm_sinov_malumot --tozala"
        ))

    def _darajalar(self, markaz):
        """Kurslar daraxtining uchinchi qatlami (Kurslar > Fan > Daraja)."""
        fanlar = KursTugun.objects.filter(
            markaz=markaz, parent__parent__isnull=True, parent__isnull=False
        )
        return list(
            KursTugun.objects.filter(parent__in=fanlar).order_by("parent__tartib", "tartib", "id")
        )

    def _talabalar(self, markaz):
        talabalar = []
        for i, ism in enumerate(ISMLAR):
            familiya_qismlari = ism.split()
            user, _ = User.objects.get_or_create(
                username=f"{BELGI_USER}{i + 1}",
                defaults={
                    "first_name": familiya_qismlari[0],
                    "last_name": familiya_qismlari[1],
                    "role": User.Role.STUDENT,
                    "markaz": markaz,
                    "telefon": f"+998 90 {100 + i:03d} {10 + i:02d} {20 + i:02d}",
                },
            )
            talabalar.append(user)
        return talabalar

    def _guruhlar(self, markaz, darajalar, filiallar, bugun):
        guruhlar = []
        for i, (nomi, filial_i, kunlar, vaqt, narx) in enumerate(GURUHLAR):
            daraja = darajalar[i % len(darajalar)]
            guruh, _ = Guruh.objects.get_or_create(
                name=f"{BELGI_GURUH}{nomi}",
                markaz=markaz,
                defaults={"daraja": daraja, "fan": daraja.parent},
            )
            # Oxirgi guruh oy O'RTASIDA ochilgan — proporsional hisob
            # ko'rinib turishi uchun.
            boshlanish = (
                bugun.replace(day=min(bugun.day, 16))
                if i == len(GURUHLAR) - 1
                else mantiq.oy_boshi(bugun - timedelta(days=100))
            )
            GuruhMoliya.objects.update_or_create(
                guruh=guruh,
                defaults={
                    "filial": filiallar[filial_i],
                    "narx": narx,
                    "boshlanish_sana": boshlanish,
                },
            )
            DarsJadvali.objects.filter(guruh=guruh).delete()
            for kun in kunlar:
                DarsJadvali.objects.create(
                    guruh=guruh, hafta_kuni=kun,
                    boshlanish_vaqti=vaqt[0], tugash_vaqti=vaqt[1],
                )
            guruhlar.append(guruh)

        # ATAYLAB bitta guruh narxsiz qoladi — Bosh sahifadagi
        # ogohlantirishlar ro'yxati ishlayotganini ko'rish uchun.
        narxsiz = guruhlar[-1]
        KursNarxi.objects.filter(daraja=narxsiz.daraja).delete()
        GuruhMoliya.objects.filter(guruh=narxsiz).update(narx=None)

        return guruhlar

    def _azoliklar(self, guruhlar, talabalar, bugun):
        """Turli sanalarda qo'shilgan, turli holatdagi a'zoliklar."""
        holatlar = (
            [AzolikMoliya.Holat.FAOL] * 7
            + [AzolikMoliya.Holat.SINOV, AzolikMoliya.Holat.MUZLATILGAN]
        )
        for i, talaba in enumerate(talabalar):
            guruh = guruhlar[i % len(guruhlar)]
            azolik, _ = GuruhAzoligi.objects.get_or_create(guruh=guruh, talaba=talaba)

            # Har uchinchi talaba oy O'RTASIDA qo'shilgan — proporsional
            # summa ro'yxatda ko'rinib tursin.
            if i % 3 == 0:
                boshlanish = bugun.replace(day=min(bugun.day, 12))
            else:
                boshlanish = mantiq.oy_boshi(bugun - timedelta(days=100))

            AzolikMoliya.objects.update_or_create(
                azolik=azolik,
                defaults={
                    "holat": holatlar[i % len(holatlar)],
                    "boshlanish_sana": boshlanish,
                    "oxirgi_hisob_oy": None,
                },
            )

    def _tolovlar(self):
        """Uch xil holat ko'rinsin: to'liq to'langan, qisman, umuman yo'q."""
        hisoblar = list(
            Hisob.objects.filter(guruh__name__startswith=BELGI_GURUH).order_by("id")
        )
        for i, hisob in enumerate(hisoblar):
            if i % 3 == 0:
                summa = hisob.summa                       # to'liq
            elif i % 3 == 1:
                summa = (hisob.summa / 2).quantize(Decimal("1"))  # qisman
            else:
                continue                                   # to'lanmagan

            Tolov.objects.create(
                talaba=hisob.talaba,
                talaba_ism=hisob.talaba_ism,
                guruh=hisob.guruh,
                guruh_nomi=hisob.guruh_nomi,
                hisob=hisob,
                sana=hisob.oy,
                summa=summa,
                turi=Tolov.Turi.TOLOV,
                izoh="Sinov ma'lumoti",
            )
            mantiq.hisobni_yangila(hisob)
