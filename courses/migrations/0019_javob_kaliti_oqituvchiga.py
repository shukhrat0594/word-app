"""Pre-Intermediate: javob kaliti bloklarini `oqituvchi_uchun` deb belgilaydi.

2026-09-07, Shuxrat tekshiruvi (talaba sifatida ko'rib chiqilgan). Pre-Intermediate
kontenti quyilganda Teacher's Guide'ning "Answers" bloklari mashq OSTIGA oddiy
matn bloki qilib ko'chirilgan edi — talaba mashqni yechmasdan turib javobni
o'qiy olardi. Boshqa darajalarda (Beginner/Elementary/Intermediate/Upper) bu
naqsh UMUMAN yo'q (0 blok), shuning uchun migratsiya faqat Pre-Intermediate
shoxiga tegadi.

Blok O'CHIRILMAYDI — o'qituvchi darsda ishlatishi uchun kerak. Faqat belgi
qo'yiladi, `_kurs_mashq_talaba_dict` esa shu belgili bloklarni talaba javobidan
filtrlaydi.

MUHIM xavfsizlik sharti: ichida `savol_idx` yoki `bosh_joy` bo'lgan blok HECH
QACHON belgilanmaydi. Sabab — "Javob: ___" ko'rinishidagi HAQIQIY mashq
maydonlari ham "Javob:" bilan boshlanadi (masalan Unit 5 WB mashq 5, Unit 11 WB
mashq 9, Unit 7 WB mashq 2). Ularni yashirish talabaning javob yozadigan
joyini yo'q qilardi va ball hisobini buzardi.
"""

import re

from django.db import migrations

BOSH = re.compile(
    r"^\s*("
    r"javob(lar)?\s*(kaliti)?\s*:"
    r"|to'g'ri javob(lar)?\s*:"
    r"|barcha to'g'ri[^:\n]*:"
    r"|mumkin(li)? javob(lar)?\s*:"
    r"|namunaviy javob[^:\n]*:"
    r"|noto'g'ri[^:\n]*(tuzatilgan|tuzatish)[^:\n]*:"
    r"|group [a-z][^:\n]*javoblari\s*:"
    r"|shifokor yana nima deydi\s*:"
    r"|millati va kasbi\s*:"
    r"|eslatma\s*:"
    # DIQQAT: "Suhbat matni:" ATAYLAB yo'q — u javob kaliti EMAS, mashqning
    # O'Z MATNI (variantlari ochiq turgan suhbat). Uni yashirish mashqni
    # yechib bo'lmaydigan qilib qo'yardi (Unit 4 WB REVIEW).
    r"|\d+-mashq javob(lar)?i\s*[—–-]"
    r"|boshqa mumkin bo'lgan javoblar\s*:"
    r")",
    re.I,
)

# Sarlavhasiz javoblar — "Savol? – Javob." shaklida yozilgani uchun yuqoridagi
# naqshga tushmaydi. Umumiy regex bilan olib bo'lmaydi: kitobdagi NAMUNA
# pufakchalari ham xuddi shu shaklda ("What did João find? — A tiny, sick
# penguin.") va ular talabaga KERAK. Shuning uchun aniq ro'yxat.
QOSHIMCHA_MATNLAR = {
    "Chloe nimadan qo'rqadi? – Speaking in front of lots of people.",
    "Nega ular maktabda turli sinflarda o'qishgan? – Because they did different subjects.",
}


def _birinchi_matn(obj):
    """Blok ichidagi BIRINCHI `matn` qiymati (chuqurlikda ham izlaydi)."""
    if isinstance(obj, dict):
        if isinstance(obj.get("matn"), str):
            return obj["matn"]
        for qiymat in obj.values():
            topildi = _birinchi_matn(qiymat)
            if topildi is not None:
                return topildi
    elif isinstance(obj, list):
        for qiymat in obj:
            topildi = _birinchi_matn(qiymat)
            if topildi is not None:
                return topildi
    return None


def _inputli(blok):
    """Blokda talaba to'ldiradigan maydon bormi."""
    if isinstance(blok, dict):
        if "savol_idx" in blok or "bosh_joy" in blok:
            return True
        return any(_inputli(v) for v in blok.values())
    if isinstance(blok, list):
        return any(_inputli(v) for v in blok)
    return False


def _pre_intermediate_mashqlari(KursTugun, KursMashq):
    darajalar = list(KursTugun.objects.filter(kalit="pre_intermediate").values_list("id", flat=True))
    if not darajalar:
        return KursMashq.objects.none()
    tugunlar = set()
    qatlam = darajalar
    for _ in range(4):  # daraja > unit > bo'lim > (ehtimoliy ichki tugun)
        qatlam = list(
            KursTugun.objects.filter(parent_id__in=qatlam).values_list("id", flat=True)
        )
        if not qatlam:
            break
        tugunlar.update(qatlam)
    return KursMashq.objects.filter(tugun_id__in=tugunlar)


def belgila(apps, schema_editor):
    KursTugun = apps.get_model("courses", "KursTugun")
    KursMashq = apps.get_model("courses", "KursMashq")
    for mashq in _pre_intermediate_mashqlari(KursTugun, KursMashq):
        ozgardi = False
        for blok in mashq.bloklar or []:
            if not isinstance(blok, dict) or blok.get("oqituvchi_uchun"):
                continue
            matn = _birinchi_matn(blok)
            if not matn or _inputli(blok):
                continue
            if not BOSH.match(matn) and matn.strip() not in QOSHIMCHA_MATNLAR:
                continue
            blok["oqituvchi_uchun"] = True
            ozgardi = True
        if ozgardi:
            mashq.save(update_fields=["bloklar"])


def bekor_qil(apps, schema_editor):
    KursTugun = apps.get_model("courses", "KursTugun")
    KursMashq = apps.get_model("courses", "KursMashq")
    for mashq in _pre_intermediate_mashqlari(KursTugun, KursMashq):
        ozgardi = False
        for blok in mashq.bloklar or []:
            if isinstance(blok, dict) and blok.pop("oqituvchi_uchun", None) is not None:
                ozgardi = True
        if ozgardi:
            mashq.save(update_fields=["bloklar"])


class Migration(migrations.Migration):

    dependencies = [("courses", "0018_kurssoz_ru")]

    operations = [migrations.RunPython(belgila, bekor_qil)]
