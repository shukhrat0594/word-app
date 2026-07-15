import datetime

from django.conf import settings
from django.db import models

# "AI Tarifi" paketi (B9): ikkita fixed tanlov, muddat narxga ta'sir qilmaydi.
# To'lov 2-fazada (Payme/Click) — hozircha xarid to'lovsiz yoziladi (test rejimi).
PAKETLAR = {
    "5x5": {"w": 5, "s": 5, "narx": 7000},
    "10x10": {"w": 10, "s": 10, "narx": 14000},
}
MUDDATLAR = (3, 5, 7)


class PaketXarid(models.Model):
    """Talabaning bitta paket xaridi va undagi qoldiq."""

    talaba = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="paket_xaridlar",
    )
    paket_turi = models.CharField(
        max_length=10, choices=[(k, k) for k in PAKETLAR]
    )
    muddat_kun = models.PositiveIntegerField(choices=[(d, f"{d} kun") for d in MUDDATLAR])
    narx = models.PositiveIntegerField()
    w_jami = models.PositiveIntegerField()
    s_jami = models.PositiveIntegerField()
    w_ishlatilgan = models.PositiveIntegerField(default=0)
    s_ishlatilgan = models.PositiveIntegerField(default=0)
    boshlanish = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Paket xaridlari"
        ordering = ["-created_at"]

    @property
    def tugash_sanasi(self):
        return self.boshlanish + datetime.timedelta(days=self.muddat_kun)

    @property
    def w_qolgan(self):
        return self.w_jami - self.w_ishlatilgan

    @property
    def s_qolgan(self):
        return self.s_jami - self.s_ishlatilgan

    @property
    def aktivmi(self):
        return (
            datetime.date.today() <= self.tugash_sanasi
            and (self.w_qolgan > 0 or self.s_qolgan > 0)
        )

    @classmethod
    def xarid_qil(cls, talaba, paket_turi, muddat_kun):
        paket = PAKETLAR[paket_turi]
        return cls.objects.create(
            talaba=talaba,
            paket_turi=paket_turi,
            muddat_kun=muddat_kun,
            narx=paket["narx"],
            w_jami=paket["w"],
            s_jami=paket["s"],
        )

    def __str__(self):
        return (
            f"{self.talaba} — {self.paket_turi} ({self.muddat_kun} kun) — "
            f"W {self.w_ishlatilgan}/{self.w_jami}, S {self.s_ishlatilgan}/{self.s_jami}"
        )


def aktiv_paket(talaba, xizmat):
    """Talabaning aktiv paketi (xizmat: 'w' yoki 's' bo'yicha qoldiq bilan)."""
    bugun = datetime.date.today()
    for p in PaketXarid.objects.filter(talaba=talaba).order_by("created_at"):
        if bugun <= p.tugash_sanasi:
            if xizmat == "w" and p.w_qolgan > 0:
                return p
            if xizmat == "s" and p.s_qolgan > 0:
                return p
    return None


def paketdan_ishlat(talaba, xizmat):
    """Aktiv paketdan bitta birlik yechadi. Paket bo'lmasa None (alohida to'lov).

    Qaytaradi: yangilangan PaketXarid yoki None.
    """
    p = aktiv_paket(talaba, xizmat)
    if p is None:
        return None
    if xizmat == "w":
        p.w_ishlatilgan += 1
        p.save(update_fields=["w_ishlatilgan"])
    else:
        p.s_ishlatilgan += 1
        p.save(update_fields=["s_ishlatilgan"])
    return p
