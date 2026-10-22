"""Bitta Listening yozuvi qismlarga alohida NUSXA bo'lib saqlangan testlarni
tuzatadi (2026-10-22, Shuhrat: "mavjud test ham shunaqa ishlasin").

2026-10-22 gacha ZIP yuklash/import bitta audioni har qismga alohida saqlardi
(Django nusxa nomiga `_<7 belgi>` qo'shadi). Frontend audio pleerini fayl
nomiga bog'laydi (`ImtihonOtish.jsx`, `key=` izohi) — nomlar har xil bo'lgani
uchun keyingi qismga o'tilganda audio to'xtardi. Bu migratsiya shunday
testlarda hamma qismni birinchi nusxaga ulaydi; kod tuzatishi —
`exercises/views.py: _fayllarni_taqsimla`, `ImtihonImportView`.

Nusxa deb faqat ikkala belgi mos kelsa hisoblanadi: nom `_xxxxxxx` qo'shimchasiz
bir xil VA hajm baytigacha bir xil (hajm faylni yuklamasdan so'raladi). Hamma
audio qism bitta faylning nusxasi bo'lmasa (masalan har bo'limning o'z yozuvi)
— test o'zgarmaydi. Ortiqcha nusxalar o'chirilmaydi: ularni admin "Media
tozalash" orqali o'chiradi."""

import re

from django.db import migrations

_NUSXA_QOSHIMCHASI = re.compile(r"_[A-Za-z0-9]{7}(\.[^./]+)$")


def asosiy_nom(nom):
    return _NUSXA_QOSHIMCHASI.sub(r"\1", nom)


def nusxalarni_birlashtir(qismlar, hajm):
    """`qismlar` — audio'li qismlar (tartib bo'yicha), `hajm(nom)` -> int yoki None.
    Hammasi bitta faylning nusxasi bo'lsa — birinchisiga ulaydi (saqlamaydi).
    Qaytaradi: o'zgargan qismlar."""
    nomlar = [q.audio_fayl.name for q in qismlar]
    if len(set(nomlar)) < 2 or len({asosiy_nom(n) for n in nomlar}) != 1:
        return []
    hajmlar = {hajm(n) for n in set(nomlar)}
    if len(hajmlar) != 1 or None in hajmlar:
        return []
    ozgargan = []
    for q in qismlar[1:]:
        if q.audio_fayl.name != nomlar[0]:
            q.audio_fayl = nomlar[0]
            ozgargan.append(q)
    return ozgargan


def birlashtir(apps, schema_editor):
    from django.core.files.storage import default_storage

    TestQismi = apps.get_model("exercises", "TestQismi")

    def hajm(nom):
        try:
            return default_storage.size(nom)
        except Exception:  # noqa: BLE001 — fayl yo'q/omborga ulanib bo'lmadi: shu test o'zgarmaydi
            return None

    audio_li = TestQismi.objects.exclude(audio_fayl="").exclude(audio_fayl__isnull=True)
    for test_id in audio_li.values_list("test_id", flat=True).distinct():
        qismlar = list(audio_li.filter(test_id=test_id).order_by("tartib", "id"))
        for q in nusxalarni_birlashtir(qismlar, hajm):
            q.save(update_fields=["audio_fayl"])


class Migration(migrations.Migration):

    dependencies = [
        ("exercises", "0016_delete_limittopup"),
    ]

    operations = [
        migrations.RunPython(birlashtir, migrations.RunPython.noop),
    ]
