"""Excel (.xlsx) orqali bitta mashqning to'g'ri javoblarini ommaviy
yangilash (2026-07-29, foydalanuvchi talabi — admin/owner javoblarni
qo'lda yoki Excel orqali kiritishi kerak).

Format — birinchi qator sarlavha (o'tkazib yuboriladi), keyingi har bir
qatorda: A=savol raqami (shu mashq ICHIDA, 1 dan boshlab), B=to'g'ri
javob. Boshqa ustunlar e'tiborga olinmaydi. `accounts/excel_import.py`
bilan bir xil naqsh."""

import openpyxl


def javob_qatorlarini_oqi(fayl):
    """Yuklangan .xlsx fayldan {qator, raqam, togri} lug'atlari ro'yxatini
    qaytaradi (birinchi — sarlavha — qator o'tkazib yuboriladi). Bo'sh
    qatorlar tashlab ketiladi. `raqam` butun songa aylanmasa — `None`."""
    workbook = openpyxl.load_workbook(fayl, read_only=True, data_only=True)
    sheet = workbook.active
    qatorlar = []
    for i, row in enumerate(sheet.iter_rows(values_only=True)):
        if i == 0:
            continue
        if not row or not any(row):
            continue
        raqam_xom = row[0] if len(row) > 0 else None
        togri_xom = row[1] if len(row) > 1 else None
        try:
            raqam = int(raqam_xom)
        except (TypeError, ValueError):
            raqam = None
        togri = str(togri_xom).strip() if togri_xom is not None else ""
        qatorlar.append({"qator": i + 1, "raqam": raqam, "togri": togri})
    return qatorlar


def javoblarni_yangila(mashq, qatorlar):
    """`qatorlar` (yuqoridagi formatda) bo'yicha `mashq.savollar[i]["togri"]`ni
    yangilaydi. Har savolga ATAYLAB alohida (bittalab) yoziladi, chunki
    noto'g'ri raqam yozilgan qator BOSHQALARGA to'sqinlik qilmasligi kerak
    (excel_import.py'dagi "xato qatorni o'tkazib, qolganini davom ettirish"
    naqshi bilan bir xil). Natija: (yangilangan_soni, xatolar_royxati)."""
    savollar = mashq.savollar
    xatolar = []
    yangilandi = 0
    for q in qatorlar:
        if q["raqam"] is None or not q["togri"]:
            xatolar.append({"qator": q["qator"], "xato": "savol raqami yoki javob bo'sh/noto'g'ri"})
            continue
        if not 1 <= q["raqam"] <= len(savollar):
            xatolar.append({
                "qator": q["qator"],
                "xato": f"savol raqami {q['raqam']} mavjud emas (mashqda {len(savollar)} ta savol bor)",
            })
            continue
        savollar[q["raqam"] - 1]["togri"] = q["togri"]
        yangilandi += 1
    mashq.savollar = savollar
    mashq.save(update_fields=["savollar"])
    return yangilandi, xatolar
