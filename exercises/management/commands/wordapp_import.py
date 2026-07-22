"""word-app-backup'dagi tayyor IELTS kontentini (Reading/Listening/Writing/
Speaking) import qiladi (10-faza, 2026-07-19).

Idempotent DB yozuvlari bo'yicha: nomi+bo'lim+tur bo'yicha mavjud Mashq bor
bo'lsa qayta yaratilmaydi. Audio fayllar esa HAR safar qayta nusxalanadi —
Render bepul rejasida disk har deploy'da tozalanadi, shuning uchun DB
qatori mavjud bo'lsa ham fayl badanini qayta tiklash kerak.

Manba: exercises/import_data/{reading,listening,writing,speaking}.json +
exercises/import_data/audio/*.mp3 (word-app-backup'dan ko'chirilgan,
D:\\shuk\\Проекты\\claude ai\\word-app-backup).
"""

import json

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from accounts.models import Markaz
from exercises.models import Bolim, Mashq, Tur

IMPORT_DIR = settings.BASE_DIR / "exercises" / "import_data"

# word-app formatidagi exercise turi -> LMS Tur enum (eng yaqin mos keluvchi)
READING_TUR = {
    "multiple-choice": Tur.MULTIPLE_CHOICE,
    "true-false-notgiven": Tur.TFNG,
    "yes-no-notgiven": Tur.TFNG,  # Tur enum'da alohida yo'q, TFNG'ga mos
    "matching-headings": Tur.MATCHING_HEADINGS,
}
LISTENING_TUR = {
    "multiple-choice": Tur.MULTIPLE_CHOICE,
    "matching": Tur.MATCHING,
    "form-completion": Tur.FILL_BLANKS,  # Tur enum'da alohida yo'q
    "short-answer": Tur.SHORT_ANSWER,
}
TUR_NOM = {
    Tur.MULTIPLE_CHOICE: "Multiple Choice",
    Tur.TFNG: "True/False/Not Given",
    Tur.MATCHING_HEADINGS: "Matching Headings",
    Tur.MATCHING: "Matching",
    Tur.FILL_BLANKS: "Form Completion",
    Tur.SHORT_ANSWER: "Short Answer",
}


def savol_reading(tip, ex):
    if tip == "multiple-choice":
        return [{"savol": ex["question"], "variantlar": ex["options"], "togri": ex["correct"]}]
    if tip in ("true-false-notgiven", "yes-no-notgiven"):
        variantlar = ["True", "False", "Not Given"] if tip == "true-false-notgiven" else ["Yes", "No", "Not Given"]
        return [{"savol": ex["statement"], "variantlar": variantlar, "togri": ex["correct"]}]
    if tip == "matching-headings":
        return [
            {"savol": f"Paragraf {harf}", "variantlar": ex["headings"], "togri": togri}
            for harf, togri in ex["correctMapping"].items()
        ]
    raise ValueError(f"Noma'lum reading exercise turi: {tip}")


def savol_listening(tip, ex):
    if tip == "multiple-choice":
        return [{"savol": ex["question"], "variantlar": ex["options"], "togri": ex["correct"]}]
    if tip == "matching":
        return [
            {"savol": item, "variantlar": ex["options"], "togri": ex["correctMapping"][item]}
            for item in ex["items"]
        ]
    if tip == "form-completion":
        return [{"savol": f["label"], "variantlar": [], "togri": f["answer"]} for f in ex["fields"]]
    if tip == "short-answer":
        return [{"savol": q["question"], "variantlar": [], "togri": q["answer"]} for q in ex["questions"]]
    raise ValueError(f"Noma'lum listening exercise turi: {tip}")


class Command(BaseCommand):
    help = "word-app-backup'dan IELTS kontentini import qiladi (idempotent)"

    def handle(self, *args, **options):
        markaz = Markaz.objects.first()
        if not markaz:
            self.stdout.write(self.style.ERROR("Markaz topilmadi — avval prod_boshlangich ishga tushsin"))
            return

        yaratildi = 0
        yaratildi += self._import_reading(markaz)
        yaratildi += self._import_listening(markaz)
        yaratildi += self._import_writing(markaz)
        yaratildi += self._import_speaking(markaz)
        self.stdout.write(self.style.SUCCESS(f"wordapp_import: jami {yaratildi} yangi mashq yaratildi"))

    def _bor_yoki_yarat(self, markaz, name, bolim, tur, **maydonlar):
        mashq = Mashq.objects.filter(markaz=markaz, name=name, bolim=bolim, tur=tur).first()
        if mashq:
            return mashq, False
        mashq = Mashq(
            markaz=markaz, name=name, bolim=bolim, tur=tur, korinish="public",
            sun_iy_intellekt_yaratgan=True, **maydonlar,
        )
        mashq.full_clean()
        mashq.save()
        return mashq, True

    def _import_reading(self, markaz):
        data = json.loads((IMPORT_DIR / "reading.json").read_text(encoding="utf-8"))
        soni = 0
        for passage in data:
            matn = "\n\n".join(f"{p['letter']}) {p['text']}" for p in passage["paragraphs"])
            # Tur bo'yicha guruhlaymiz (raw type emas) — true-false-notgiven
            # va yes-no-notgiven ikkalasi ham Tur.TFNG'ga tushadi, aks holda
            # bir xil nomli ikkita Mashq hosil bo'lib, ikkinchisi
            # "allaqachon bor" deb chalkashtirib o'tkazib yuboriladi.
            guruhlar = {}
            for ex in passage["exercises"]:
                tur = READING_TUR[ex["type"]]
                guruhlar.setdefault(tur, []).append(ex)
            for tur, exlar in guruhlar.items():
                savollar = []
                for ex in exlar:
                    savollar.extend(savol_reading(ex["type"], ex))
                name = f"[{passage['level']}] {passage['title']} — {TUR_NOM[tur]}"
                _, yangi = self._bor_yoki_yarat(
                    markaz, name, Bolim.READING, tur, matn=matn, savollar=savollar
                )
                soni += int(yangi)
        return soni

    def _import_listening(self, markaz):
        data = json.loads((IMPORT_DIR / "listening.json").read_text(encoding="utf-8"))
        soni = 0
        for item in data:
            nisbiy_yol = self._audio_nusxala(item["id"])
            if not nisbiy_yol:
                continue
            tur = LISTENING_TUR[item["type"]]
            savollar = []
            for ex in item["exercises"]:
                savollar.extend(savol_listening(item["type"], ex))
            name = f"[{item['level']}] {item['title']}"
            mashq, yangi = self._bor_yoki_yarat(
                markaz, name, Bolim.LISTENING, tur,
                matn=item["transcript"], savollar=savollar, audio_fayl=nisbiy_yol,
            )
            if not yangi and mashq.audio_fayl.name != nisbiy_yol:
                mashq.audio_fayl.name = nisbiy_yol
                mashq.save(update_fields=["audio_fayl"])
            soni += int(yangi)
        return soni

    def _audio_nusxala(self, item_id):
        """Audio faylni HAR doim manbadan qayta nusxalaydi (ephemeral disk
        himoyasi — Render bepul rejasida disk har deploy'da tozalanadi).

        Gemini TTS orqali qayta yozilgan dialoglar .wav, asl word-app-backup
        fayllari .mp3 — avval .wav'ni qidiradi (2026-07-20)."""
        for kengaytma in (".wav", ".mp3"):
            fayl_nomi = f"{item_id}{kengaytma}"
            manba = IMPORT_DIR / "audio" / fayl_nomi
            if manba.exists():
                nisbiy_yol = f"mashqlar/audio/{fayl_nomi}"
                if default_storage.exists(nisbiy_yol):
                    default_storage.delete(nisbiy_yol)
                default_storage.save(nisbiy_yol, ContentFile(manba.read_bytes()))
                return nisbiy_yol
        self.stdout.write(self.style.WARNING(f"Audio topilmadi: {item_id}"))
        return None

    def _import_writing(self, markaz):
        data = json.loads((IMPORT_DIR / "writing.json").read_text(encoding="utf-8"))
        soni = 0
        for item in data:
            matn = item["prompt"]
            if item.get("structure"):
                matn += "\n\n[Struktura]\n" + "\n".join(item["structure"])
            if item.get("phrases"):
                matn += "\n\n[Foydali iboralar]\n" + ", ".join(item["phrases"])
            if item.get("chart"):
                matn += "\n\n[Grafik SVG manba kodi]\n" + item["chart"]
            name = f"Writing — {item['category']}"
            tur = Tur.TASK1 if item.get("chart") else Tur.TASK2
            _, yangi = self._bor_yoki_yarat(
                markaz, name, Bolim.WRITING, tur, matn=matn, namuna_javob=item.get("sample_answer", "")
            )
            soni += int(yangi)
        return soni

    def _import_speaking(self, markaz):
        data = json.loads((IMPORT_DIR / "speaking.json").read_text(encoding="utf-8"))
        soni = 0
        for item in data.get("part1", []):
            matn = f"Mavzu: {item['topic']}\n\n" + "\n".join(
                f"{i + 1}. {q['question']}" for i, q in enumerate(item["questions"])
            )
            namuna = "\n\n".join(
                f"{i + 1}. {q['sample_answer']}" for i, q in enumerate(item["questions"])
            )
            if item.get("phrases"):
                namuna += "\n\n[Foydali iboralar]\n" + ", ".join(item["phrases"])
            name = f"Speaking Part 1 — {item['category']}"
            _, yangi = self._bor_yoki_yarat(
                markaz, name, Bolim.SPEAKING, Tur.PART1, matn=matn, namuna_javob=namuna
            )
            soni += int(yangi)

        for item in data.get("part2_3", []):
            matn = item["cue_card"]
            if item.get("structure"):
                matn += "\n\n[Struktura]\n" + "\n".join(item["structure"])
            matn += "\n\n[Part 3 savollari]\n" + "\n".join(
                f"- {q['question']}" for q in item.get("part3_questions", [])
            )
            namuna = item.get("sample_answer", "")
            if item.get("phrases"):
                namuna += "\n\n[Foydali iboralar]\n" + ", ".join(item["phrases"])
            if item.get("part3_questions"):
                namuna += "\n\n[Part 3 namuna javoblari]\n" + "\n\n".join(
                    f"{q['question']}\n{q['sample_answer']}" for q in item["part3_questions"]
                )
            name = f"Speaking Part 2/3 — {item['category']}"
            _, yangi = self._bor_yoki_yarat(
                markaz, name, Bolim.SPEAKING, Tur.PART2, matn=matn, namuna_javob=namuna
            )
            soni += int(yangi)
        return soni
