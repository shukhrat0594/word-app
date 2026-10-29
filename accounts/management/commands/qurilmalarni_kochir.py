"""Eski qurilmalar ro'yxatini 2-tizimga qayta ko'chirish (2026-10-29).

Kerak bo'ladigan yagona holat: eski versiyaga qaytilib, keyin yana yangisiga o'tilsa —
oraliqda eski tizimda qo'shilgan qurilmalar va bloklar yangi tizimga ham o'tsin.
Qayta ishga tushirish xavfsiz: bor brauzer ID'lari qayta qo'shilmaydi, kutilayotgan
so'rovlar olinmaydi (`accounts/qurilma_kochirish.py`)."""

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import BrauzerEslatmasi, Qurilma, QurilmaSorovi, User
from accounts.qurilma_kochirish import kochir


class Command(BaseCommand):
    help = "Eski qurilmalar ro'yxatini (User.qurilmalar, bloklar) 2-tizimga qayta ko'chiradi"

    def handle(self, *args, **options):
        with transaction.atomic():
            sanoq = kochir(User, Qurilma, BrauzerEslatmasi, QurilmaSorovi)
        self.stdout.write(
            f"Qo'shildi: qurilma {sanoq['qurilma']}, brauzer {sanoq['brauzer']}, blok {sanoq['blok']}"
        )
