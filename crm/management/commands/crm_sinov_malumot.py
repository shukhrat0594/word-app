"""Sinov ma'lumoti — ikki qatlamda.

Shuhrat (2026-09-16): "saytdan olishi kerak bo'lgan ma'lumotlarni CRM dan
o'chirib tashlab saytdan oladigan qil, test uchun ma'lumot kamlik qilsa
saytga qo'sh shu ma'lumotlarni".

Shunga ko'ra buyruq ATAYLAB ikkiga bo'lingan:

  1. SAYT QATLAMI — o'qituvchilar, talabalar, guruhlar, a'zoliklar,
     davomat. Bular LMS'ning O'Z modellari va oddiy sayt ma'lumoti
     ko'rinishida yaratiladi: haqiqiy nomlar, "[Sinov]" kabi belgisiz.
     CRM ularni hech qayerdan nusxalamaydi — bevosita LMS'dan o'qiydi.

  2. CRM QATLAMI — faqat CRM'ning o'z tushunchalari: filial, xona, kurs
     narxi, guruh moliyasi, dars jadvali, hisob, to'lov.

Ya'ni CRM'da guruh yoki talabaning nusxasi YO'Q — u saytdagi guruhga
`OneToOne` kengaytma qo'shadi, xolos.

    python manage.py crm_sinov_malumot
    python manage.py crm_sinov_malumot --tozala

`--tozala` aynan shu buyruq yaratganini o'chiradi: guruhlar nomi
ro'yxat bo'yicha, talabalar `username` prefiksi bo'yicha topiladi.
"""

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from academics.models import Davomat, Guruh, GuruhAzoligi
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
    Xona,
)

# Tozalash uchun belgi. Foydalanuvchiga KO'RINMAYDI: ekranda ism-familiya
# chiqadi, `username` esa faqat ichki identifikator.
BELGI_USER = "demo_"

OQITUVCHILAR = [
    ("Isroil", "Zohidjonov"),
    ("Sevinch", "Bahtiyorova"),
    ("Shahnoza", "Hamzayeva"),
]

# (guruh nomi, DARAJA nomi, filial indeksi, hafta kunlari, vaqt, guruh narxi)
#
# Daraja nomi ATAYLAB guruh nomiga MOS: "IELTS ertalabki" guruhining
# darajasi "Beginner" bo'lib chiqsa, ekranda qarama-qarshilikdek
# ko'rinadi va admin ma'lumotga ishonmay qoladi.
GURUHLAR = [
    ("IELTS ertalabki 09:00", "IELTS", 0, [1, 3, 5], ("09:00", "10:30"), None),
    ("IELTS kechki 18:00", "IELTS", 0, [0, 2, 4], ("18:00", "19:30"), None),
    ("Beginner kunduzgi 14:00", "Beginner", 1, [1, 3, 5], ("14:00", "15:30"), None),
    # Guruh narxi kurs narxini BEKOR QILADI — uch qavatli narx
    # ishlayotgani ko'rinsin.
    ("Intermediate kechki 16:00", "Intermediate", 1, [0, 2, 4], ("16:00", "17:30"),
     Decimal("520000")),
    # Elementary darajasi ATAYLAB narxsiz qoldiriladi -> Bosh sahifadagi
    # "sozlanmagan guruh" ogohlantirishi ishlayotgani ko'rinadi.
    ("Elementary ertalabki 10:00", "Elementary", 2, [1, 3], ("10:00", "11:30"), None),
]
GURUH_NOMLARI = [nomi for nomi, *_ in GURUHLAR]

# Kurs (daraja) narxlari. "Elementary" ro'yxatda YO'Q — ataylab.
KURS_NARXLARI = {
    "IELTS": Decimal("660000"),
    "Beginner": Decimal("400000"),
    "Intermediate": Decimal("450000"),
}

FILIALLAR = [
    ("Utmost Gor-Park", "Gorkiy parki yonida", "+998 71 200 00 01"),
    ("Utmost Chilonzor", "Chilonzor 9-kvartal", "+998 71 200 00 02"),
    ("Utmost Yunusobod", "Yunusobod 4-mavze", "+998 71 200 00 03"),
]

ISMLAR = [
    ("Aziz", "Qodirov"), ("Malika", "Yusupova"), ("Jasur", "Rahimov"),
    ("Dilnoza", "Karimova"), ("Sardor", "Tursunov"), ("Nigora", "Alimova"),
    ("Bekzod", "Sharipov"), ("Zilola", "Nazarova"), ("Otabek", "Ismoilov"),
    ("Madina", "Sobirova"), ("Rustam", "Xolmatov"), ("Shahnoza", "Umarova"),
    ("Farrux", "Ergashev"), ("Kamola", "Toshpulatova"), ("Javohir", "Mirzayev"),
    ("Sevara", "Qosimova"), ("Ulugbek", "Saidov"), ("Nodira", "Abdullayeva"),
    ("Temur", "Yoqubov"), ("Gulnora", "Rashidova"),
]


class Command(BaseCommand):
    help = (
        "Saytga sinov ma'lumotini qo'shadi (guruh, talaba, o'qituvchi, "
        "davomat) va ustiga CRM sozlamalarini yozadi"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--tozala", action="store_true",
            help="Shu buyruq yaratgan ma'lumotni o'chiradi",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["tozala"]:
            return self._tozala()
        return self._yarat()

    # ── Tozalash ────────────────────────────────────────────────────

    def _tozala(self):
        guruhlar = Guruh.objects.filter(name__in=GURUH_NOMLARI)
        odamlar = User.objects.filter(username__startswith=BELGI_USER)

        # `Hisob`/`Tolov` da FK `SET_NULL` — talaba o'chsa ham yozuv
        # qolardi. Sinov ma'lumotini tozalashda ularni ATAYLAB aniq
        # o'chiramiz, aks holda "yetim" pul qatorlari to'planib qolardi.
        Tolov.objects.filter(guruh__in=guruhlar).delete()
        Hisob.objects.filter(guruh__in=guruhlar).delete()
        Davomat.objects.filter(guruh__in=guruhlar).delete()

        guruh_soni, odam_soni = guruhlar.count(), odamlar.count()
        guruhlar.delete()
        odamlar.delete()
        xona_soni, _ = Xona.objects.filter(
            filial__nomi__in=[f[0] for f in FILIALLAR]
        ).delete()
        filial_soni, _ = Filial.objects.filter(
            nomi__in=[f[0] for f in FILIALLAR]
        ).delete()

        self.stdout.write(self.style.SUCCESS(
            f"Tozalandi: {guruh_soni} guruh, {odam_soni} foydalanuvchi, "
            f"{filial_soni} filial, {xona_soni} xona yozuvi"
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

        # ── 1-qatlam: SAYT ma'lumoti ────────────────────────────────
        oqituvchilar = self._oqituvchilar(markaz)
        talabalar = self._talabalar(markaz)
        guruhlar = self._guruhlar(markaz, darajalar, oqituvchilar, bugun)
        self._azoliklar(guruhlar, talabalar)

        # ── 2-qatlam: CRM sozlamalari ───────────────────────────────
        Sozlama.objects.update_or_create(
            pk=Sozlama.objects.values_list("pk", flat=True).first(),
            defaults={"boshlangich_oy": mantiq.oy_boshi(bugun - timedelta(days=70))},
        )
        filiallar = self._filiallar(markaz)
        xonalar = self._xonalar(filiallar)
        self._narxlar(darajalar)
        self._guruh_moliyasi(guruhlar, filiallar, xonalar, bugun)
        self._azolik_moliyasi(guruhlar, bugun)

        # Davomat SAYT ma'lumoti, lekin u DARS JADVALIGA tayanadi (qaysi
        # kunlarda dars bo'lgan) — shuning uchun jadval yaratilgandan
        # KEYIN to'ldiriladi.
        davomat_soni = self._davomat(guruhlar, bugun)

        natija = mantiq.hisoblarni_generatsiya_qil()
        self._tolovlar(guruhlar)

        self.stdout.write(self.style.SUCCESS(
            f"SAYTGA qo'shildi: {len(oqituvchilar)} o'qituvchi, {len(talabalar)} talaba, "
            f"{len(guruhlar)} guruh, {davomat_soni} davomat yozuvi.\n"
            f"CRM sozlamalari: {len(filiallar)} filial, "
            f"{sum(len(v) for v in xonalar.values())} xona, "
            f"{natija['yaratildi']} hisob.\n"
            f"Bitta guruh ATAYLAB narxsiz — Bosh sahifadagi ogohlantirish "
            f"ishlayotgani ko'rinsin.\n"
            f"Tozalash: python manage.py crm_sinov_malumot --tozala"
        ))

    # ── 1-qatlam: sayt ──────────────────────────────────────────────

    def _darajalar(self, markaz):
        """Kurslar daraxtining uchinchi qatlami: {nomi: tugun}.

        Nom bo'yicha lug'at — guruh darajasi nomiga mos berilishi uchun
        (indeks bo'yicha bersak "IELTS" guruhi "Beginner" darajasiga
        tushib qolardi).
        """
        fanlar = KursTugun.objects.filter(
            markaz=markaz, parent__parent__isnull=True, parent__isnull=False
        )
        return {
            d.nomi: d
            for d in KursTugun.objects.filter(parent__in=fanlar).order_by(
                "parent__tartib", "tartib", "id"
            )
        }

    def _oqituvchilar(self, markaz):
        natija = []
        for i, (ism, familiya) in enumerate(OQITUVCHILAR, start=1):
            user, _ = User.objects.get_or_create(
                username=f"{BELGI_USER}oqituvchi{i}",
                defaults={
                    "first_name": ism, "last_name": familiya,
                    "role": User.Role.TEACHER, "markaz": markaz,
                    "telefon": f"+998 90 {900 + i:03d} 10 10",
                },
            )
            natija.append(user)
        return natija

    def _talabalar(self, markaz):
        natija = []
        for i, (ism, familiya) in enumerate(ISMLAR, start=1):
            user, _ = User.objects.get_or_create(
                username=f"{BELGI_USER}talaba{i:02d}",
                defaults={
                    "first_name": ism, "last_name": familiya,
                    "role": User.Role.STUDENT, "markaz": markaz,
                    "telefon": f"+998 90 {100 + i:03d} {10 + i:02d} {20 + i:02d}",
                    "ota_ona_telefon": f"+998 91 {200 + i:03d} {30 + i:02d} {40 + i:02d}",
                },
            )
            natija.append(user)
        return natija

    def _guruhlar(self, markaz, darajalar, oqituvchilar, bugun):
        natija = []
        for i, (nomi, daraja_nomi, _filial_i, _kunlar, _vaqt, _narx) in enumerate(GURUHLAR):
            daraja = darajalar.get(daraja_nomi)
            if daraja is None:
                self.stdout.write(self.style.WARNING(
                    f"Daraja topilmadi: {daraja_nomi} — {nomi} darajasiz qoladi"
                ))
            guruh, _ = Guruh.objects.get_or_create(
                name=nomi,
                markaz=markaz,
                defaults={
                    "daraja": daraja,
                    "fan": daraja.parent if daraja else None,
                    # O'qituvchi — SAYT ma'lumoti. CRM uni faqat
                    # ko'rsatadi, tahrirlamaydi.
                    "oqituvchi": oqituvchilar[i % len(oqituvchilar)],
                },
            )
            natija.append(guruh)
        return natija

    def _azoliklar(self, guruhlar, talabalar):
        for i, talaba in enumerate(talabalar):
            GuruhAzoligi.objects.get_or_create(
                guruh=guruhlar[i % len(guruhlar)], talaba=talaba
            )

    def _davomat(self, guruhlar, bugun):
        """Joriy oyning O'TGAN dars kunlariga davomat.

        Davomat — SAYT ma'lumoti: uni o'qituvchi LMS'da belgilaydi. Bu
        yerda faqat sinov uchun to'ldiriladi.
        """
        oy = mantiq.oy_boshi(bugun)
        soni = 0
        for guruh in guruhlar:
            kunlar = [k for k in mantiq.oylik_dars_kunlari(guruh, oy) if k <= bugun]
            for i, talaba in enumerate(guruh.talabalar.all()):
                for j, kun in enumerate(kunlar):
                    # Har 7-si kelmagan — jadval bir xil yashil bo'lib
                    # qolmasin, ranglar ko'rinsin.
                    holat = (
                        Davomat.Holat.KELMADI if (i + j) % 7 == 0 else Davomat.Holat.KELDI
                    )
                    _, yangi = Davomat.objects.get_or_create(
                        sana=kun, guruh=guruh, talaba=talaba, defaults={"holat": holat}
                    )
                    soni += int(yangi)
        return soni

    # ── 2-qatlam: CRM ───────────────────────────────────────────────

    def _filiallar(self, markaz):
        return [
            Filial.objects.get_or_create(
                markaz=markaz, nomi=nomi,
                defaults={"manzil": manzil, "telefon": telefon},
            )[0]
            for nomi, manzil, telefon in FILIALLAR
        ]

    def _xonalar(self, filiallar):
        """Har filialda 4 ta xona — setka bo'sh ko'rinmasligi uchun."""
        return {
            filial.id: [
                Xona.objects.get_or_create(
                    filial=filial, nomi=f"{i}-xona",
                    defaults={"tartib": i, "sigimi": 10 + i},
                )[0]
                for i in range(1, 5)
            ]
            for filial in filiallar
        }

    def _narxlar(self, darajalar):
        """Narx DARAJAGA osiladi — guruhga emas (TZ 3.2).

        `KURS_NARXLARI` da yo'q darajalar (masalan "Elementary") narxsiz
        qoladi: o'sha guruh Bosh sahifadagi ogohlantirishlar ro'yxatiga
        tushadi va tizim pul yo'qotishni aytib turgani ko'rinadi.
        """
        for nomi, narx in KURS_NARXLARI.items():
            daraja = darajalar.get(nomi)
            if daraja is not None:
                KursNarxi.objects.update_or_create(daraja=daraja, defaults={"narx": narx})

        for nomi, daraja in darajalar.items():
            if nomi not in KURS_NARXLARI:
                KursNarxi.objects.filter(daraja=daraja).delete()

    def _guruh_moliyasi(self, guruhlar, filiallar, xonalar, bugun):
        for i, (guruh, (_nomi, _daraja_nomi, filial_i, kunlar, vaqt, narx)) in enumerate(
            zip(guruhlar, GURUHLAR)
        ):
            filial = filiallar[filial_i]
            # Oxirgi guruh oy O'RTASIDA ochilgan — proporsional hisob
            # ko'rinib tursin.
            boshlanish = (
                bugun.replace(day=min(bugun.day, 16))
                if i == len(GURUHLAR) - 1
                else mantiq.oy_boshi(bugun - timedelta(days=100))
            )
            GuruhMoliya.objects.update_or_create(
                guruh=guruh,
                defaults={"filial": filial, "narx": narx, "boshlanish_sana": boshlanish},
            )
            DarsJadvali.objects.filter(guruh=guruh).delete()
            filial_xonalari = xonalar[filial.id]
            xona = filial_xonalari[i % len(filial_xonalari)]
            for kun in kunlar:
                DarsJadvali.objects.create(
                    guruh=guruh, hafta_kuni=kun, xona=xona,
                    boshlanish_vaqti=vaqt[0], tugash_vaqti=vaqt[1],
                )

    def _azolik_moliyasi(self, guruhlar, bugun):
        """A'zolikning CRM tomoni: holat va boshlanish sanasi."""
        holatlar = (
            [AzolikMoliya.Holat.FAOL] * 7
            + [AzolikMoliya.Holat.SINOV, AzolikMoliya.Holat.MUZLATILGAN]
        )
        i = 0
        for guruh in guruhlar:
            for azolik in GuruhAzoligi.objects.filter(guruh=guruh).order_by("id"):
                # Har uchinchi talaba oy O'RTASIDA qo'shilgan —
                # proporsional summa ro'yxatda ko'rinib tursin.
                boshlanish = (
                    bugun.replace(day=min(bugun.day, 12))
                    if i % 3 == 0
                    else mantiq.oy_boshi(bugun - timedelta(days=100))
                )
                AzolikMoliya.objects.update_or_create(
                    azolik=azolik,
                    defaults={
                        "holat": holatlar[i % len(holatlar)],
                        "boshlanish_sana": boshlanish,
                        # Birinchi talabaga INDIVIDUAL narx — uch qavatli
                        # narxning uchinchisi (aka-uka chegirmasi kabi)
                        # ishlayotgani ko'rinsin.
                        "narx": Decimal("350000") if i == 0 else None,
                        "oxirgi_hisob_oy": None,
                    },
                )
                i += 1

    def _tolovlar(self, guruhlar):
        """Uch xil holat ko'rinsin: to'liq to'langan, qisman, umuman yo'q."""
        hisoblar = list(Hisob.objects.filter(guruh__in=guruhlar).order_by("id"))
        for i, hisob in enumerate(hisoblar):
            if i % 3 == 0:
                summa = hisob.summa
            elif i % 3 == 1:
                summa = (hisob.summa / 2).quantize(Decimal("1"))
            else:
                continue

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
