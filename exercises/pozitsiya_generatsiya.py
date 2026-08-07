"""Saqlangan Map/Diagram/Plan rasmidan savol pozitsiyalarini AI orqali
QAYTA aniqlash (2026-08-05, foydalanuvchi talabi: "bazada saqlangan
rasmdan qayta tekshirib yuklasin").

`courses.blok_generatsiya`dagi to'r-asosli usuldan (`tor_chiz`) qayta
foydalaniladi — o'sha yerda batafsil izohlangan sabab bilan: LLM
koordinatani ko'z bilan chamalaganda ±3-5% xato beradi, rasmga
pronumerlangan to'r chizilsa model chiziqni O'QIYDI va xato deyarli
nolga tushadi."""

from assessment.providers import ProviderXatosi
from courses.blok_generatsiya import tor_chiz

POZITSIYA_PROMPT = (
    "Sizga IELTS Reading yoki Listening testining Map/Diagram/Plan "
    "Labelling rasmi beriladi. Rasm ustiga PRONUMERLANGAN TO'R "
    "chizilgan: chiziqlar har 5 foizda, chetlarida 0 dan 100 gacha "
    "raqamlar.\n\n"
    "Sizga pastda RAQAMLANGAN savollar ro'yxati beriladi — har biri "
    "shu rasmdagi ANIQ bir bo'sh joy/labelga tegishli. HAR bir savol "
    "uchun, uning rasmdagi ENG MOS joyini TO'R RAQAMLARIGA qarab "
    "(chamalamasdan, chiziqni o'qib) aniqlang.\n\n"
    "FAQAT quyidagi JSON qaytaring:\n"
    '{"pozitsiyalar": [{"raqam": 1, "x": 42, "y": 63}, ...]}\n\n'
    "\"x\"/\"y\" — rasmning chap-yuqori burchagidan boshlab, bo'sh "
    "joy/label markazining rasm eniga/bo'yiga nisbatan foizi (0-100). "
    "Har savol uchun ANIQ BITTA pozitsiya bering. Agar biror savolning "
    "rasmga aloqasi yo'q deb hisoblasangiz (masalan matn ichidagi "
    "savol) — shu raqamni ro'yxatga umuman qo'shmang."
)


def pozitsiyalarni_aniqla(provider, rasm_bytes, savollar):
    """`savollar` — [{"raqam": int, "savol": str}, ...] (1dan boshlab).

    Qaytaradi: (pozitsiyalar_dict, xato) — biri None bo'ladi.
    `pozitsiyalar_dict` — {raqam(int): {"x": float, "y": float}}."""
    torli = tor_chiz(rasm_bytes)
    savollar_matni = "\n".join(f"{s['raqam']}. {s['savol']}" for s in savollar)
    try:
        javob = provider.generate_json(
            POZITSIYA_PROMPT,
            f"Savollar:\n{savollar_matni}",
            torli, "image/jpeg",
        )
    except ProviderXatosi as e:
        return None, str(e)
    except Exception as e:  # noqa: BLE001 — kutilmagan AI/rasm xatosi
        return None, f"{type(e).__name__}: {e}"

    natija = javob.get("natija") or {}
    xom = natija.get("pozitsiyalar") or []
    pozitsiyalar = {}
    for p in xom:
        try:
            raqam = int(p["raqam"])
            x, y = float(p["x"]), float(p["y"])
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= x <= 100 and 0 <= y <= 100:
            pozitsiyalar[raqam] = {"x": x, "y": y}
    if not pozitsiyalar:
        return None, "AI hech qanday pozitsiya topa olmadi"
    return pozitsiyalar, None
