"""Excel (.xlsx) orqali foydalanuvchi (talaba/xodim) ommaviy kiritish.

Format — birinchi qator sarlavha (o'tkazib yuboriladi), keyingi har bir
qatorda: A=ism, B=login, C=parol. Boshqa ustunlar e'tiborga olinmaydi.
"""

import openpyxl
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError


def qatorlarni_oqi(fayl):
    """Yuklangan .xlsx fayldan {ism, login, parol} lug'atlari ro'yxatini
    qaytaradi (birinchi — sarlavha — qator o'tkazib yuboriladi). Bo'sh
    qatorlar tashlab ketiladi."""
    workbook = openpyxl.load_workbook(fayl, read_only=True, data_only=True)
    sheet = workbook.active
    qatorlar = []
    for i, row in enumerate(sheet.iter_rows(values_only=True)):
        if i == 0:
            continue
        if not row or not any(row):
            continue
        ism = str(row[0]).strip() if len(row) > 0 and row[0] is not None else ""
        login = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
        parol = str(row[2]).strip() if len(row) > 2 and row[2] is not None else ""
        qatorlar.append({"qator": i + 1, "ism": ism, "login": login, "parol": parol})
    return qatorlar


def foydalanuvchilarni_yarat(qatorlar, *, role, markaz_id, User):
    """Har bir qator uchun User yaratadi. Xato bo'lgan qatorlar o'tkazib
    yuboriladi (login band, parol zaif, maydon bo'sh va h.k.) — muvaffaqiyatli
    yaratilganlar va xatolar ro'yxati alohida qaytariladi."""
    yaratilganlar = []
    xatolar = []
    for q in qatorlar:
        if not q["ism"] or not q["login"] or not q["parol"]:
            xatolar.append({"qator": q["qator"], "xato": "ism/login/parol to'ldirilmagan"})
            continue
        if User.objects.filter(username=q["login"]).exists():
            xatolar.append({"qator": q["qator"], "xato": f"login \"{q['login']}\" allaqachon band"})
            continue
        try:
            validate_password(q["parol"])
        except DjangoValidationError as e:
            xatolar.append({"qator": q["qator"], "xato": " ".join(e.messages)})
            continue

        user = User(username=q["login"], first_name=q["ism"], role=role, markaz_id=markaz_id)
        user.set_password(q["parol"])
        user.save()
        yaratilganlar.append({"id": user.id, "ism": q["ism"], "login": q["login"]})
    return yaratilganlar, xatolar
