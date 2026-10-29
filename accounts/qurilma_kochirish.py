"""Eski qurilmalar ro'yxatini (`User.qurilmalar`, `QurilmaSorovi`) 2-tizimga ko'chirish
(2026-10-29). Migratsiya 0033 va `qurilmalarni_kochir` buyrug'i ishlatadi, shuning
uchun modellar parametr bilan beriladi (migratsiyada — tarixiy modellar).

Qayta ishga tushirilsa xavfsiz: 2-tizimda bor brauzer ID'lari qayta qo'shilmaydi.
Kutilayotgan so'rovlar faqat birinchi ko'chirishda olinadi (`sorovlar=True`) — aks
holda admin hal qilgan so'rov keyingi ko'chirishda qaytib kelardi."""

import secrets
from datetime import datetime

from django.utils import timezone


def _vaqt(qiymat, zaxira):
    try:
        v = datetime.fromisoformat(qiymat)
    except (TypeError, ValueError):
        return zaxira
    return v if timezone.is_aware(v) else timezone.make_aware(v)


def _brauzerlar(d):
    """Eski yozuvning brauzerlari (2026-10-26 gacha yozilgan bitta brauzerli shakl ham)."""
    royxat = [b for b in d.get("brauzerlar") or [] if isinstance(b, dict) and b.get("id")]
    if not royxat and d.get("id"):
        belgilar = d.get("belgilar") or {}
        royxat = [{"id": d["id"], "brauzer": belgilar.get("brauzer", ""), "belgilar": belgilar,
                   "qoshilgan": d.get("qoshilgan"), "oxirgi": d.get("oxirgi")}]
    return royxat


def _nom(belgilar):
    qismlar = [(belgilar or {}).get(k) for k in ("tizim", "model")]
    return " · ".join(q for q in qismlar if q) or "Noma'lum qurilma"


def _qurilma(Qurilma, user_id, holat, belgilar, **qolgan):
    belgilar = belgilar if isinstance(belgilar, dict) else {}
    return Qurilma.objects.create(
        foydalanuvchi_id=user_id, holat=holat, nom=qolgan.pop("nom", "") or _nom(belgilar),
        tizim=str(belgilar.get("tizim", ""))[:20], modeli=str(belgilar.get("model", ""))[:60],
        belgilar=belgilar, **qolgan,
    )


def kochir(User, Qurilma, BrauzerEslatmasi, QurilmaSorovi, sorovlar=False, hozir=None):
    """Qaytaradi: {"qurilma": n, "brauzer": n, "sorov": n, "blok": n} — nechta qo'shildi."""
    hozir = hozir or timezone.now()
    bor = set(BrauzerEslatmasi.objects.values_list("foydalanuvchi_id", "qid"))
    sanoq = {"qurilma": 0, "brauzer": 0, "sorov": 0, "blok": 0}

    def eslatma(q, b):
        BrauzerEslatmasi.objects.create(
            qurilma=q, foydalanuvchi_id=q.foydalanuvchi_id, qid=b["id"][:64],
            brauzer=str(b.get("brauzer") or "")[:40], belgilar=b.get("belgilar") or {},
            yaratilgan=_vaqt(b.get("qoshilgan"), hozir), oxirgi=_vaqt(b.get("oxirgi"), hozir),
        )
        bor.add((q.foydalanuvchi_id, b["id"][:64]))
        sanoq["brauzer"] += 1

    for user_id, royxat in User.objects.values_list("id", "qurilmalar"):
        for d in royxat or []:
            if not isinstance(d, dict):
                continue
            brauzerlar = [b for b in _brauzerlar(d) if (user_id, b["id"][:64]) not in bor]
            if not brauzerlar:
                continue
            belgilar = d.get("belgilar") or brauzerlar[-1].get("belgilar") or {}
            q = _qurilma(
                Qurilma, user_id, "ruxsat", belgilar, nom=str(d.get("nom") or "")[:120],
                k=str(d.get("k") or secrets.token_hex(6))[:32],
                yaratilgan=_vaqt(d.get("qoshilgan"), hozir), oxirgi=_vaqt(d.get("oxirgi"), hozir),
            )
            sanoq["qurilma"] += 1
            for b in brauzerlar:
                eslatma(q, b)

    holatlar = ["blok", "kutilmoqda"] if sorovlar else ["blok"]
    for s in QurilmaSorovi.objects.filter(holat__in=holatlar).order_by("id"):
        if (s.foydalanuvchi_id, s.qid) in bor:
            continue
        blok = s.holat == "blok"
        q = _qurilma(
            Qurilma, s.foydalanuvchi_id, "blok" if blok else "kutilmoqda", s.belgilar,
            urinishlar=s.urinishlar, yaratilgan=s.yaratilgan or hozir, oxirgi=s.oxirgi_urinish or hozir,
            hal_qildi_id=s.hal_qildi_id if blok else None, hal_vaqti=s.hal_vaqti if blok else None,
        )
        sanoq["blok" if blok else "sorov"] += 1
        eslatma(q, {"id": s.qid, "brauzer": (s.belgilar or {}).get("brauzer", ""), "belgilar": s.belgilar,
                    "qoshilgan": None, "oxirgi": None})
    return sanoq
