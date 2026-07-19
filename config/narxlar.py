"""Yagona narx manbai.

Barcha AI tekshiruv va paket narxlari FAQAT shu yerda belgilanadi. Narx
o'zgarsa — shu faylni tahrirlash kifoya: backend (paketlar, API javoblari)
va frontend (`GET /api/narxlar/` orqali) hammasi shu yerdan o'qiydi. Kodning
boshqa joyiga narxni qattiq yozib qo'ymang (hardcode qilmang).
"""

WRITING_TEZKOR = 600  # Writing — Tezkor tahlil (Gemini), so'm
SPEAKING_MATN = 600  # Speaking — Matn rejimi (Gemini, audio yo'q), so'm
SPEAKING_TEZKOR = 1000  # Speaking — Tezkor tahlil (Azure+Gemini, audio), so'm

PAKET_CHEGIRMA = 0.125  # "AI Tarifi" paketidagi chegirma (12.5%)


def paket_narx(w_soni, s_soni):
    """Standalone narxdan PAKET_CHEGIRMA ayirib, paket narxini hisoblaydi."""
    standalone = w_soni * WRITING_TEZKOR + s_soni * SPEAKING_TEZKOR
    return round(standalone * (1 - PAKET_CHEGIRMA))
