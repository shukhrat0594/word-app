import { useEffect, useRef, useState } from "react";
import { api, apiBlobUrl, apiFayluniYuklab, apiForm } from "../api";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";
import ImtihonMock from "./ImtihonMock";
import ImtihonOtish, { vaqtFormat } from "./ImtihonOtish";
import ImtihonYozGap from "./ImtihonYozGap";

// Backend `exercises/mashq_generatsiya.py`dagi BAND_GURUHLAR bilan bir xil.
const BAND_GURUHLAR = ["5-6", "6.5-7.5", "8-9"];

const AI_PROMT = `Men senga to'liq IELTS Reading yoki Listening testi (masalan Cambridge IELTS kitobidan) matnini/transkriptini beraman. Sen shu materialni quyidagi JSON formatiga o'girib ber — natija FAQAT valid JSON obyekt bo'lsin, hech qanday izoh, sarlavha yoki markdown belgisi (masalan \`\`\`json) qo'shma, faqat sof JSON matni qaytar.

Format:
{
  "name": "Testning to'liq nomi (masalan 'Cambridge IELTS 21 Academic Reading Test 4')",
  "bolim": "reading" | "listening",
  "korinish": "private" | "public",
  "qismlar": [
    {
      "tartib": 1,
      "sarlavha": "Passage 1" (reading) yoki "Part 1" (listening),
      "yoriqnoma": "You should spend about 20 minutes on Questions 1-13, which are based on Reading Passage 1 below.",
      "matn": "Reading uchun passage matni to'liq shu yerga. Listening uchun bo'sh qoldir (\"\") — audio alohida yuklanadi.",
      "rasm": "fayl_nomi.png" (ixtiyoriy — faqat ZIP orqali yuklashda ishlaydi: shu nomdagi rasm fayl arxivning o'zida bo'lishi kerak, Map/Diagram Labelling uchun. Oddiy JSON yuklashda bu maydonni yozma, keyin qo'lda biriktiriladi),
      "savollar": [
        {
          "savol": "Savol yoki band matni",
          "tur": "quyidagi ro'yxatdan",
          "variantlar": ["variant1", "variant2"],
          "togri": "To'g'ri javob (yoki bir nechta qabul qilinadigan javob bo'lsa — massiv, masalan [\"20%\", \"twenty percent\"])",
          "guruh_boshi": "Questions 1-7" (ixtiyoriy, savollar guruhi boshida sarlavha ko'rsatish uchun, faqat guruhning birinchi savolida yoz, qolganida bo'sh qoldir),
          "pozitsiya": {"x": 0-100, "y": 0-100} (ixtiyoriy — FAQAT sizga shu qismning rasmi (Map/Diagram Labelling yoki jadval rasmi) ilova qilingan bo'lsa va shu savolning bo'sh joyi/labeli rasmda aniq ko'rinib tursa qo'sh: rasmning chap-yuqori burchagidan boshlab, bo'sh joy/label markazining rasm eniga nisbatan foizini "x", bo'yiga nisbatan foizini "y" qilib yoz. Rasm berilmagan yoki savol matn ichida bo'lsa (rasmga bog'liq bo'lmagan) — bu maydonni umuman yozma.
        }
      ],
      "maxsus_format": {"tur": "jadval" | "oqim", "sarlavha": "...", "ustunlar": [...], "qatorlar": [[...]]} yoki {"tur": "oqim", "sarlavha": "...", "qadamlar": [...]} (ixtiyoriy — pastdagi "Table/Note/Summary/Flow-chart Completion" qoidasiga qarang)
    }
  ]
}

Qoidalar:
- "bolim" = "reading" bo'lsa "tur": multiple_choice, tfng, matching_headings, matching, fill_blanks, short_answer
- "bolim" = "listening" bo'lsa "tur": multiple_choice, fill_blanks, matching, map_labelling, short_answer
- True/False/Not Given tipidagi savollarda "variantlar": ["True", "False", "Not Given"]
- Ochiq javobli (fill_blanks/short_answer, forma to'ldirish kabi — masalan "Guest name:") savollarda "variantlar"ni bo'sh massiv [] qoldir
- **"So'z banki bilan bo'sh joy to'ldirish" (Summary/Note Completion with a word list)** — bitta oqim matn ichida bir nechta bo'sh joy va umumiy variantlar banki bo'lsa: har bir bo'sh joy uchun ALOHIDA savol yoz (tur="fill_blanks"), "savol" maydoniga o'sha bo'sh joygacha bo'lgan matn parchasini yoz (masalan birinchisi "The city of Delhi has a", ikkinchisi "and as you walk through its streets you hear people speaking a variety of languages. Some of them have spent their entire life in Delhi, while others are"), va HAMMASIGA BIR XIL "variantlar" ro'yxatini (butun so'z banki, masalan 8-10 ta variant) qo'y — frontend bularni avtomatik bitta oqim+bank qilib birlashtiradi (ketma-ket kelishi va variantlar bir xil bo'lishi shart)
- Savollar RAQAMLANMAYDI (masalan "1. ..." deb yozma) — raqamlash frontend'da avtomatik, uzluksiz barcha qismlar bo'yicha qo'yiladi
- "tartib" — qismning testdagi tartib raqami (1,2,3,4...), butun testda uzluksiz savol raqamlash shu tartib bo'yicha hisoblanadi
- Har bir qismdagi savollar soni real testdagi kabi bo'lsin (masalan Reading har passage uchun ~13-14 ta, Listening har part uchun ~10 ta)
- "korinish": aniq ko'rsatilmagan bo'lsa "private" qo'y
- Agar sizga Map/Diagram Labelling yoki jadval-rasm biriktirilgan bo'lsa — shu rasmga tegishli har bir savolga "pozitsiya" qo'shing (yuqoridagi formatga qarang), shunda talaba javobni rasmning aynan o'sha nuqtasida yoza oladi
- **Table/Note/Summary/Flow-chart Completion (rasmsiz, asl kitobdagi jadval/blok-sxema ko'rinishida)** — agar savol turi haqiqiy JADVAL (ustun-qatorlar) yoki FLOW-CHART (ketma-ket bloklar, o'qlar bilan) bo'lsa, "pozitsiya" o'rniga shu qismga "maxsus_format" qo'shing:
  - Jadval uchun: {"tur": "jadval", "sarlavha": "JADVAL NOMI", "ustunlar": ["Ustun1", "Ustun2", ...], "qatorlar": [["katak matni {{5}} bilan", "ikkinchi katak", ...], ...]} — har bir qator massiv, har bir element bitta katak matni
  - Flow-chart uchun: {"tur": "oqim", "sarlavha": "SXEMA NOMI", "qadamlar": ["1-qadam matni {{26}} bilan", "2-qadam matni {{27}} bilan", ...]} — har bir qadam alohida quti bo'lib, orasida o'q chiziladi
  - {{n}} — o'sha bo'sh joyning testdagi UMUMIY (butun test bo'yicha uzluksiz, "tartib"lar hisobga olingan holda) savol raqami, masalan 26-savol uchun {{26}} — bu raqam "savollar" massividagi mos savolning ORDER'iga aynan mos kelishi SHART
  - Bu holatda ham "savollar" massivini ODATDAGIDEK, HAR BIR bo'sh joy uchun alohida yozing (tur="fill_blanks" yoki mos tur, "togri" bilan) — "maxsus_format" faqat KO'RINISH uchun, javob tekshirish baribir "savollar"dan olinadi, ikkalasi bir-biriga zid bo'lmasligi kerak (bir xil son va tartibda)
  - Oddiy (jadval/sxema shakli bo'lmagan, faqat uzluksiz matn+bo'sh joy) Note/Summary Completion uchun ("So'z banki" qoidasiga to'g'ri kelmasa, ya'ni umumiy variantlar banki YO'Q bo'lsa) — {"tur": "matn", "sarlavha": "SARLAVHA (ixtiyoriy)", "matn": "to'liq matn, bo'sh joylar {{31}} kabi, qatorlar orasida \\n, ro'yxat/bullet uchun matn boshida \"- \""} — bu ham asl kitobdagi ko'rinishni saqlaydi va HAR BIR bo'sh joy raqamlanadi
- map_labelling turida "variantlar" (A-I harflar) yozsangiz ham, frontend ularni tanlov (radio) sifatida EMAS, oddiy qisqa matn input sifatida ko'rsatadi (asl kitobda ham talaba faqat bitta harf yozadi) — shuning uchun "variantlar" majburiy emas, xohlasangiz hujjatlashtirish uchun qoldirishingiz mumkin

Natijani shu JSON obyekt ko'rinishida qaytar, boshqa hech narsa yozma. Quyida test materiali:

[BU YERGA TEST MATNI/TRANSKRIPTINI JOYLASHTIRING]`;

const AI_PROMT_YOZGAP = `Men senga IELTS Writing yoki Speaking test materialini beraman. Sen shu materialni quyidagi JSON formatiga o'girib ber — natija FAQAT valid JSON obyekt bo'lsin, hech qanday izoh yoki markdown belgisi qo'shma.

Format:
{
  "name": "Testning nomi (masalan 'Writing Test — University Education')",
  "bolim": "writing" | "speaking",
  "korinish": "private" | "public",
  "qismlar": [
    {"tartib": 1, "tur": "task1", "sarlavha": "Task 1", "matn": "Task 1 topshirig'i to'liq shu yerga"},
    {"tartib": 2, "tur": "task2", "sarlavha": "Task 2", "matn": "Task 2 mavzusi to'liq shu yerga"}
  ]
}

Qoidalar:
- "bolim"="writing" bo'lsa qismlarda "tur": task1, task2 (ikkalasi ham bo'lishi shart)
- "bolim"="speaking" bo'lsa qismlarda "tur": part1, part2, part3 (barchasi bo'lishi shart)
- Writing Task 1'da grafik/jadval bo'lsa, uni matn ichida tavsiflab yoz (masalan jadval qiymatlarini matn shaklida) — agar rasm fayli bo'lsa, ZIP orqali yuklaganda "rasm": "fayl_nomi.png" qo'sh
- "korinish": aniq ko'rsatilmagan bo'lsa "private" qo'y

Natijani shu JSON obyekt ko'rinishida qaytar. Quyida test materiali:

[BU YERGA TEST MATERIALINI JOYLASHTIRING]`;

const YOZGAP_TURLAR = {
  writing: [
    { tur: "task1", label: "Task 1" },
    { tur: "task2", label: "Task 2" },
  ],
  speaking: [
    { tur: "part1", label: "Part 1" },
    { tur: "part2", label: "Part 2" },
    { tur: "part3", label: "Part 3" },
  ],
};

/** Writing/Speaking uchun mashq qo'shish — 2 usul: qo'lda (matn+rasm har
 * qism uchun) yoki fayl yuklash (JSON bitta test, yoki ZIP — bitta/bir
 * nechta test, papka bo'yicha). `bolim` yuqori "Kiritish paneli"dagi
 * tab'dan keladi. */
function YozGapKiritish({ bolim, manba, qismgaFaylYukla, royxatniYangila }) {
  const { t } = useI18n();
  const [usul, setUsul] = useState("qolda");
  const [nomi, setNomi] = useState("");
  const [qismlar, setQismlar] = useState({});
  const [xato, setXato] = useState("");
  const [saqlanmoqda, setSaqlanmoqda] = useState(false);
  const [promtKorinadi, setPromtKorinadi] = useState(false);
  const [nusxalandi, setNusxalandi] = useState(false);

  useEffect(() => {
    setNomi("");
    setQismlar({});
    setXato("");
  }, [bolim]);

  function promtNusxala() {
    navigator.clipboard?.writeText(AI_PROMT_YOZGAP).then(() => {
      setNusxalandi(true);
      setTimeout(() => setNusxalandi(false), 2000);
    });
  }

  function qismniYangila(tur, maydon, qiymat) {
    setQismlar((q) => ({ ...q, [tur]: { ...q[tur], [maydon]: qiymat } }));
  }

  async function qoldaYuborish(e) {
    e.preventDefault();
    setXato("");
    const turlar = YOZGAP_TURLAR[bolim];
    if (!nomi.trim()) {
      setXato(t("imtihon_nomi") + " majburiy");
      return;
    }
    for (const { tur, label } of turlar) {
      if (!(qismlar[tur]?.matn || "").trim()) {
        setXato(`"${label}" matni majburiy`);
        return;
      }
    }
    setSaqlanmoqda(true);
    try {
      const data = {
        name: nomi,
        bolim,
        korinish: "private",
        qismlar: turlar.map(({ tur, label }, i) => ({
          tartib: i + 1,
          tur,
          sarlavha: label,
          matn: qismlar[tur].matn,
        })),
      };
      const yaratildi = await api("/api/imtihon/testlar-boshqaruv/", {
        method: "POST",
        body: { ...data, manba },
      });
      for (const q of yaratildi.qismlar) {
        const rasmFayl = qismlar[q.tur]?.rasm;
        if (rasmFayl) {
          await qismgaFaylYukla(q.id, "rasm", rasmFayl);
        }
      }
      setNomi("");
      setQismlar({});
      royxatniYangila();
    } catch (err) {
      setXato(err.data?.detail || t("imtihon_json_xato"));
    } finally {
      setSaqlanmoqda(false);
    }
  }

  async function jsonYukla(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setXato("");
    setSaqlanmoqda(true);
    try {
      const matn = await fayl.text();
      await api("/api/imtihon/testlar-boshqaruv/", {
        method: "POST",
        body: { ...JSON.parse(matn), manba },
      });
      royxatniYangila();
    } catch (err) {
      setXato(err.data?.detail || t("imtihon_json_xato"));
    } finally {
      setSaqlanmoqda(false);
    }
  }

  async function pdfYukla(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setXato("");
    setSaqlanmoqda(true);
    try {
      const fd = new FormData();
      fd.append("pdf_fayl", fayl);
      fd.append("manba", manba);
      fd.append("bolim", bolim);
      fd.append("name", nomi.trim());
      await apiForm("/api/imtihon/testlar-boshqaruv-pdf/", { method: "POST", formData: fd });
      setNomi("");
      royxatniYangila();
    } catch (err) {
      setXato(
        err.data?.detail
          || (err.status ? `${t("imtihon_json_xato")} (HTTP ${err.status})` : t("imtihon_json_xato")),
      );
    } finally {
      setSaqlanmoqda(false);
    }
  }

  async function zipYukla(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setXato("");
    setSaqlanmoqda(true);
    try {
      const fd = new FormData();
      fd.append("zip_fayl", fayl);
      fd.append("manba", manba);
      await apiForm("/api/imtihon/testlar-boshqaruv-zip/", { method: "POST", formData: fd });
      royxatniYangila();
    } catch (err) {
      setXato(err.data?.detail || t("imtihon_json_xato"));
    } finally {
      setSaqlanmoqda(false);
    }
  }

  return (
    <div>
      <div className="tab-guruh" style={{ marginBottom: 14 }}>
        <button className={usul === "qolda" ? "aktiv" : ""} onClick={() => setUsul("qolda")}>
          {t("imtihon_qolda_kiritish")}
        </button>
        <button className={usul === "json" ? "aktiv" : ""} onClick={() => setUsul("json")}>
          {t("imtihon_json_yuklash")}
        </button>
        <button className={usul === "zip" ? "aktiv" : ""} onClick={() => setUsul("zip")}>
          {t("imtihon_zip_yuklash")}
        </button>
        <button className={usul === "pdf" ? "aktiv" : ""} onClick={() => setUsul("pdf")}>
          {t("imtihon_pdf_yuklash")}
        </button>
      </div>

      {usul === "pdf" && (
        <div>
          <p className="izoh" style={{ marginTop: 0 }}>{t("imtihon_pdf_yozgap_izoh")}</p>
          <input
            placeholder={t("imtihon_nomi") + " (" + t("imtihon_ixtiyoriy") + ")"}
            value={nomi}
            onChange={(e) => setNomi(e.target.value)}
            style={{ marginBottom: 10, width: "100%" }}
            disabled={saqlanmoqda}
          />
          <input type="file" accept="application/pdf,.pdf" onChange={pdfYukla} disabled={saqlanmoqda} />
          {saqlanmoqda && <div className="izoh" style={{ marginTop: 8 }}>{t("imtihon_pdf_yuklanmoqda")}</div>}
          {xato && <div className="xato-xabar" style={{ marginTop: 8 }}>{xato}</div>}
        </div>
      )}

      {usul === "qolda" && (
        <form onSubmit={qoldaYuborish} style={{ display: "grid", gap: 10 }}>
          <input
            placeholder={t("imtihon_nomi")}
            value={nomi}
            onChange={(e) => setNomi(e.target.value)}
          />
          {YOZGAP_TURLAR[bolim].map(({ tur, label }) => (
            <div key={tur} style={{ border: "1px solid var(--chiziq)", borderRadius: 8, padding: 10 }}>
              <strong>{label}</strong>
              <textarea
                rows={4}
                style={{ width: "100%", marginTop: 6 }}
                placeholder={t("imtihon_qism_matni")}
                value={qismlar[tur]?.matn || ""}
                onChange={(e) => qismniYangila(tur, "matn", e.target.value)}
              />
              <div style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 8 }}>
                <span className="izoh">{t("imtihon_rasm_biriktir")}</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => qismniYangila(tur, "rasm", e.target.files[0])}
                />
              </div>
            </div>
          ))}
          <button className="tugma" disabled={saqlanmoqda}>{t("saqlash")}</button>
          {xato && <div className="xato-xabar">{xato}</div>}
        </form>
      )}

      {(usul === "json" || usul === "zip") && (
        <div>
          {usul === "json" ? (
            <>
              <p className="izoh" style={{ marginTop: 0 }}>{t("imtihon_json_izoh")}</p>
              <input type="file" accept="application/json" onChange={jsonYukla} disabled={saqlanmoqda} />
            </>
          ) : (
            <>
              <p className="izoh" style={{ marginTop: 0 }}>{t("imtihon_zip_izoh")}</p>
              <input type="file" accept=".zip" onChange={zipYukla} disabled={saqlanmoqda} />
            </>
          )}

          {xato && <div className="xato-xabar" style={{ marginTop: 8 }}>{xato}</div>}

          <div style={{ marginTop: 14 }}>
            <button type="button" className="tugma ikkinchi" onClick={() => setPromtKorinadi((v) => !v)}>
              {promtKorinadi ? t("imtihon_promt_yashirish") : t("imtihon_promt_korsatish")}
            </button>
            {promtKorinadi && (
              <div style={{ marginTop: 10 }}>
                <textarea
                  readOnly
                  rows={14}
                  value={AI_PROMT_YOZGAP}
                  onClick={(e) => e.target.select()}
                  style={{ width: "100%", fontFamily: "monospace", fontSize: 12.5 }}
                />
                <button type="button" className="tugma" onClick={promtNusxala} style={{ marginTop: 8 }}>
                  {nusxalandi ? t("nusxalandi") : t("nusxalash")}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/** Reading/Listening uchun mashq qo'shish — FAQAT ZIP orqali (bitta yoki
 * bir nechta test, papka bo'yicha). Savollar strukturasi murakkab
 * (guruhlar, so'z banki va h.k.) bo'lgani uchun qo'lda kiritish yo'q —
 * AI-promt yordamchisi bilan JSON tayyorlanadi, ZIP'ga solinadi. */
/** PDF yuklash oynasi (2026-07-31 talabi).
 *
 * Nega alohida oyna: AI test nomini ham, savol oraliqlarini ham o'zi
 * taxmin qilardi — natijada nom noto'g'ri chiqdi va 40 o'rniga 38 savol
 * yaratildi. Endi ikkalasini ADMIN kiritadi, ya'ni taxmin qoladigan joy
 * yo'q: backend har qismdan AYNAN shuncha savol kutadi, kam chiqsa
 * o'sha qismni qayta so'raydi.
 *
 * Oraliqlar ketma-ket: 1-qismning oxiri kiritilsa, 2-qismning boshi
 * avtomatik "oxiri + 1" bo'ladi (3-qism ham shunday) — admin faqat
 * oxirgi raqamlarni yozadi.
 *
 * Yuklash paytida oyna butun ekranni qoplaydi va yopilmaydi — bu ataylab:
 * jarayon 2-3 daqiqa davom etadi va yarim yo'lda boshqa amal qilinsa
 * chala test qolib ketardi. */
function PdfYuklashOynasi({ bolim, manba, yopish, tugadi }) {
  const { t } = useI18n();
  // Reading — 3 passage, Listening — 4 part (IELTS standarti).
  const qismSoni = bolim === "listening" ? 4 : 3;
  const [nom, setNom] = useState("");
  // IELTS standarti — Reading/Listening ikkisi ham JAMI 40 savoldan iborat,
  // shuning uchun oxirgi qismning oxiri 40 deb oldindan to'ldiriladi (admin
  // xohlasa o'zgartirishi mumkin, faqat qulaylik uchun).
  const [oraliqlar, setOraliqlar] = useState(() =>
    Array.from({ length: qismSoni }, (_, i) => ({
      boshi: i === 0 ? "1" : "",
      oxiri: i === qismSoni - 1 ? "40" : "",
    })),
  );
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [otganSoniya, setOtganSoniya] = useState(0);
  const [xato, setXato] = useState("");
  // AI natijasini yopishdan oldin ko'rib/nusxalab olish uchun (diagnostika,
  // 2026-08-01 talabi) — muvaffaqiyatli yuklashdan keyin darhol yopilmaydi.
  const [natijaJson, setNatijaJson] = useState(null);
  const [nusxalandi, setNusxalandi] = useState(false);

  function jsonNusxala() {
    navigator.clipboard?.writeText(JSON.stringify(natijaJson, null, 2)).then(() => {
      setNusxalandi(true);
      setTimeout(() => setNusxalandi(false), 2000);
    });
  }

  useEffect(() => {
    if (!yuklanmoqda) return undefined;
    const boshlandi = Date.now();
    setOtganSoniya(0);
    const taymer = setInterval(() => setOtganSoniya(Math.floor((Date.now() - boshlandi) / 1000)), 1000);
    return () => clearInterval(taymer);
  }, [yuklanmoqda]);

  // Bir maydon o'zgarsa — keyingi qismlarning boshi zanjir bo'ylab
  // qayta hisoblanadi (oxiri + 1).
  function qiymatniQoy(idx, maydon, qiymat) {
    setOraliqlar((eski) => {
      const yangi = eski.map((o, i) => (i === idx ? { ...o, [maydon]: qiymat } : { ...o }));
      for (let i = 0; i < yangi.length - 1; i += 1) {
        const oxiri = Number(yangi[i].oxiri);
        yangi[i + 1].boshi = Number.isInteger(oxiri) && oxiri > 0 ? String(oxiri + 1) : "";
      }
      return yangi;
    });
  }

  const toldirilgan =
    nom.trim().length > 0
    && oraliqlar.every((o) => {
      const b = Number(o.boshi);
      const x = Number(o.oxiri);
      return Number.isInteger(b) && Number.isInteger(x) && b > 0 && x >= b;
    });

  const jamiSavol = toldirilgan
    ? Number(oraliqlar[oraliqlar.length - 1].oxiri) - Number(oraliqlar[0].boshi) + 1
    : 0;

  // Jarayon haqida taxminiy bosqich xabari (2026-08-01 talabi). Backend
  // BITTA sinxron so'rov (real progress-endpoint yo'q), shuning uchun
  // bu HAQIQIY server holati emas — qism sonidan va o'rtacha vaqtdan
  // kelib chiqib TAXMIN qilinadi. Shu sabab "taxminan" deb ochiq
  // yoziladi, aldash bo'lmasin.
  const REJA_TAXMIN_SONIYA = 12; // 1-bosqich: reja (kichik so'rov)
  const QISM_TAXMIN_SONIYA = 35; // har passage ~1 AI chaqiruvi
  function bosqichXabari() {
    if (otganSoniya < REJA_TAXMIN_SONIYA) {
      return t("imtihon_pdf_bosqich_reja");
    }
    const oShu = otganSoniya - REJA_TAXMIN_SONIYA;
    const qismIdx = Math.min(oraliqlar.length - 1, Math.floor(oShu / QISM_TAXMIN_SONIYA));
    return t("imtihon_pdf_bosqich_qism")
      .replace("{n}", qismIdx + 1)
      .replace("{jami}", oraliqlar.length);
  }

  async function faylTanlandi(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setXato("");
    setYuklanmoqda(true);
    try {
      const fd = new FormData();
      fd.append("pdf_fayl", fayl);
      fd.append("manba", manba);
      fd.append("bolim", bolim);
      fd.append("name", nom.trim());
      fd.append(
        "qismlar",
        JSON.stringify(oraliqlar.map((o) => ({ boshi: Number(o.boshi), oxiri: Number(o.oxiri) }))),
      );
      const natija = await apiForm("/api/imtihon/testlar-boshqaruv-pdf/", { method: "POST", formData: fd });
      setYuklanmoqda(false);
      setNatijaJson(natija);
    } catch (err) {
      // `detail` bo'lmasa — javob DRF'dan emas (proxy/gunicorn uzgan).
      // Statusni ko'rsatamiz, aks holda sabab umuman bilinmaydi.
      setXato(
        err.data?.detail
          || (err.status ? `${t("imtihon_json_xato")} (HTTP ${err.status})` : t("imtihon_json_xato")),
      );
      setYuklanmoqda(false);
    }
  }

  return (
    <div className="blok-yuklash-qoplama">
      {/* `blok-yuklash-karta` sukut bo'yicha 320px va markazga tortadi —
          bu forma uchun to'g'ri kelmaydi, shuning uchun kengaytirib,
          chapga tekislaymiz. */}
      <div
        className="blok-yuklash-karta"
        style={{
          width: "min(460px, calc(100vw - 32px))",
          maxHeight: "calc(100vh - 32px)",
          overflowY: "auto",
          justifyItems: "stretch",
          textAlign: "left",
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: 10 }}>{t("imtihon_pdf_oyna_sarlavha")}</div>

        {natijaJson ? (
          <div>
            <div className="izoh" style={{ marginBottom: 10 }}>
              {t("imtihon_pdf_tayyor")}: <strong>{natijaJson.name}</strong>
            </div>
            {natijaJson.xatolar?.length > 0 && (
              <div className="xato-xabar" style={{ marginBottom: 10 }}>
                {natijaJson.xatolar.join("; ")}
              </div>
            )}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button type="button" className="tugma ikkinchi" onClick={jsonNusxala}>
                {nusxalandi ? t("nusxalandi") : t("imtihon_pdf_json_nusxala")}
              </button>
              <button
                type="button"
                className="tugma"
                onClick={() => tugadi(natijaJson.xatolar || [])}
              >
                {t("yopish")}
              </button>
            </div>
          </div>
        ) : yuklanmoqda ? (
          <div style={{ display: "grid", justifyItems: "center", gap: 6, textAlign: "center" }}>
            <div className="blok-yuklash-spinner" aria-hidden="true" />
            <div className="izoh" style={{ marginTop: 8 }}>{t("imtihon_pdf_yuklanmoqda")}</div>
            <div className="izoh">{t("kurs_blok_otgan_vaqt")}: {vaqtFormat(otganSoniya)}</div>
            <div style={{ fontWeight: 600, marginTop: 4 }}>{bosqichXabari()}</div>
            <div className="izoh" style={{ marginTop: 6 }}>{t("imtihon_pdf_kutish_izoh")}</div>
          </div>
        ) : (
          <>
            <label className="izoh" style={{ display: "block", marginBottom: 4 }}>
              {t("imtihon_nomi")}
            </label>
            <input
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              placeholder="Cambridge IELTS 21 Reading Test 4"
              style={{ width: "100%", marginBottom: 12 }}
            />

            <div className="izoh" style={{ marginBottom: 6 }}>{t("imtihon_pdf_oraliq_izoh")}</div>
            {oraliqlar.map((o, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                <span className="izoh" style={{ minWidth: 78 }}>
                  {bolim === "listening" ? `Part ${i + 1}` : `Passage ${i + 1}`}
                </span>
                <input
                  type="number"
                  min="1"
                  value={o.boshi}
                  onChange={(e) => qiymatniQoy(i, "boshi", e.target.value)}
                  // 1-qismdan keyingilari avtomatik hisoblanadi.
                  readOnly={i > 0}
                  style={{ width: 64 }}
                />
                <span className="izoh">—</span>
                <input
                  type="number"
                  min="1"
                  value={o.oxiri}
                  onChange={(e) => qiymatniQoy(i, "oxiri", e.target.value)}
                  style={{ width: 64 }}
                />
              </div>
            ))}
            {toldirilgan && (
              <div className="izoh" style={{ marginTop: 4 }}>
                {t("imtihon_pdf_jami_savol")}: <strong>{jamiSavol}</strong>
              </div>
            )}

            <div style={{ marginTop: 14, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              {toldirilgan ? (
                <label className="tugma" style={{ cursor: "pointer" }}>
                  {t("imtihon_pdf_yuklash")}
                  <input
                    type="file"
                    accept="application/pdf,.pdf"
                    onChange={faylTanlandi}
                    style={{ display: "none" }}
                  />
                </label>
              ) : (
                <button type="button" className="tugma" disabled title={t("imtihon_pdf_avval_toldiring")}>
                  {t("imtihon_pdf_yuklash")}
                </button>
              )}
              <button type="button" className="tugma ikkinchi" onClick={yopish}>
                {t("kurs_blok_bekor_qilish")}
              </button>
            </div>
            {!toldirilgan && (
              <div className="izoh" style={{ marginTop: 6 }}>{t("imtihon_pdf_avval_toldiring")}</div>
            )}
          </>
        )}

        {xato && <div className="xato-xabar" style={{ marginTop: 10 }}>{xato}</div>}
      </div>
    </div>
  );
}

function RLKiritish({ bolim, manba, royxatniYangila }) {
  const { t } = useI18n();
  const [xato, setXato] = useState("");
  const [saqlanmoqda, setSaqlanmoqda] = useState(false);
  const [promtKorinadi, setPromtKorinadi] = useState(false);
  const [nusxalandi, setNusxalandi] = useState(false);
  // 2026-07-31: PDF'dan to'g'ridan-to'g'ri yuklash. ZIP'dan farqi —
  // JSON'ni tashqi AI emas, PDF'ni o'zi ko'rgan Claude tayyorlaydi, shu
  // sababli passage chegaralari chalkashmaydi.
  const [pdfOynasi, setPdfOynasi] = useState(false);

  function promtNusxala() {
    navigator.clipboard?.writeText(AI_PROMT).then(() => {
      setNusxalandi(true);
      setTimeout(() => setNusxalandi(false), 2000);
    });
  }

  async function zipYukla(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setXato("");
    setSaqlanmoqda(true);
    try {
      const fd = new FormData();
      fd.append("zip_fayl", fayl);
      fd.append("manba", manba);
      await apiForm("/api/imtihon/testlar-boshqaruv-zip/", { method: "POST", formData: fd });
      royxatniYangila();
    } catch (err) {
      setXato(err.data?.detail || t("imtihon_json_xato"));
    } finally {
      setSaqlanmoqda(false);
    }
  }

  function pdfTugadi(xatolar) {
    setPdfOynasi(false);
    royxatniYangila();
    // Test yaratildi, lekin ba'zi qismlar chala bo'lishi mumkin — buni
    // JIM qoldirmaymiz (avval "faqat bir qismi yuklandi" degan
    // tushunarsiz holat shundan kelib chiqqandi).
    setXato(xatolar.length ? `${t("imtihon_pdf_qisman")}: ${xatolar.join("; ")}` : "");
  }

  return (
    <div>
      <p className="izoh" style={{ marginTop: 0 }}>{t("imtihon_zip_izoh")}</p>
      <input type="file" accept=".zip" onChange={zipYukla} disabled={saqlanmoqda} />

      <div style={{ marginTop: 14, paddingTop: 12, borderTop: "1px solid var(--chiziq)" }}>
        <p className="izoh" style={{ marginTop: 0 }}>{t("imtihon_pdf_izoh")}</p>
        <button type="button" className="tugma" onClick={() => { setXato(""); setPdfOynasi(true); }}>
          {t("imtihon_pdf_yuklash")}
        </button>
      </div>

      {pdfOynasi && (
        <PdfYuklashOynasi
          bolim={bolim}
          manba={manba}
          yopish={() => setPdfOynasi(false)}
          tugadi={pdfTugadi}
        />
      )}

      {xato && <div className="xato-xabar" style={{ marginTop: 8 }}>{xato}</div>}

      <div style={{ marginTop: 14 }}>
        <button type="button" className="tugma ikkinchi" onClick={() => setPromtKorinadi((v) => !v)}>
          {promtKorinadi ? t("imtihon_promt_yashirish") : t("imtihon_promt_korsatish")}
        </button>
        {promtKorinadi && (
          <div style={{ marginTop: 10 }}>
            <p className="izoh" style={{ marginTop: 0 }}>{t("imtihon_promt_izoh")}</p>
            <textarea
              readOnly
              rows={16}
              value={AI_PROMT}
              onClick={(e) => e.target.select()}
              style={{ width: "100%", fontFamily: "monospace", fontSize: 12.5 }}
            />
            <button type="button" className="tugma" onClick={promtNusxala} style={{ marginTop: 8 }}>
              {nusxalandi ? t("nusxalandi") : t("nusxalash")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/** Yuqori panel — Writing/Speaking/Reading/Listening tab'lari, har biri
 * o'z kiritish usuliga ega (W/S: qo'lda/fayl, R/L: faqat ZIP). */
function KiritishPanel({ manba, qismgaFaylYukla, royxatniYangila }) {
  const { t } = useI18n();
  const [bolim, setBolim] = useState("writing");

  return (
    <div className="karta">
      <h3>{t("imtihon_kiritish_paneli")}</h3>
      <div className="tab-guruh" style={{ marginBottom: 14 }}>
        <button className={bolim === "writing" ? "aktiv" : ""} onClick={() => setBolim("writing")}>
          {t("mashq_bolim_writing")}
        </button>
        <button className={bolim === "speaking" ? "aktiv" : ""} onClick={() => setBolim("speaking")}>
          {t("mashq_bolim_speaking")}
        </button>
        <button className={bolim === "reading" ? "aktiv" : ""} onClick={() => setBolim("reading")}>
          {t("reading_bolimi")}
        </button>
        <button className={bolim === "listening" ? "aktiv" : ""} onClick={() => setBolim("listening")}>
          {t("listening_bolimi")}
        </button>
      </div>
      {bolim === "writing" || bolim === "speaking" ? (
        <YozGapKiritish
          bolim={bolim}
          manba={manba}
          qismgaFaylYukla={qismgaFaylYukla}
          royxatniYangila={royxatniYangila}
        />
      ) : (
        <RLKiritish bolim={bolim} manba={manba} royxatniYangila={royxatniYangila} />
      )}
    </div>
  );
}

/** Bitta savolning barcha matn maydonlarini (guruh_boshi/guruh_korsatma/
 * savol/variantlar/togri) tahrirlaydigan qator (2026-08-05, foydalanuvchi
 * talabi: "matnni qo'lda tahrirlash imkoni bo'lsin"). `pozitsiya`
 * (Map/Diagram Labelling koordinatasi) BU YERDA tahrirlanmaydi — alohida
 * AI-yordamli bosqich sifatida rejalashtirilgan (hozircha o'zgarishsiz
 * saqlanadi). */
/** Ro'yxat maydonlari (variantlar, ko'p javobli "togri") uchun XOM
 * matnni saqlaydigan input (2026-08-08).
 *
 * NEGA KERAK — foydalanuvchi xatosi: "vergul qo'yib bo'lmayabdi probel
 * ham". Avval qiymat har bosishda `split -> trim -> filter -> join`
 * aylanishidan o'tardi. Natijada vergul yozilishi bilan bo'sh element
 * hosil bo'lib `filter(Boolean)` uni yo'q qilardi, oxiridagi probelni
 * esa `trim()` yeb qo'yardi — ya'ni bu belgilarni KIRITIB BO'LMASDI.
 *
 * Yechim: ko'ringan matn LOKAL holatda xom saqlanadi (foydalanuvchi
 * nima yozsa — o'sha turadi), massivga ajratish esa faqat YUQORIGA
 * uzatilayotganda bajariladi. */
export function RoyxatMaydoni({ qiymat, ajratgich, ozgardi, ...qolgan }) {
  const [xom, setXom] = useState(qiymat);
  // Tashqaridan (masalan "Guruhga qo'llash" tugmasi yoki boshqa savolga
  // o'tilganda) qiymat o'zgarsa moslashtiramiz — lekin foydalanuvchi
  // yozayotgan matnni buzmasdan.
  const oxirgiTashqiRef = useRef(qiymat);
  // 2026-08-11 BUG TUZATILDI: "Enter bosib yangi qator qo'shib bo'lmayapti"
  // (foydalanuvchi topib berdi). Sabab: pastdagi `onChange` `ozgardi()`ga
  // filtrlangan massiv beradi — `filter(Boolean)` BO'SH qatorlarni olib
  // tashlaydi. Enter bosilganda xom matnda YANGI BO'SH qator paydo bo'ladi,
  // lekin filtrlangach parent'ga qaytgan qiymat o'sha bo'sh qatorsiz —
  // ya'ni BIZNING O'ZIMIZNING chaqiruvimizdan qaytgan `qiymat` prop matn
  // ko'rinishida ESKI holat bilan bir xil bo'lib chiqadi. Ba'zi render
  // holatlarida bu "tashqaridan chinakam o'zgargan" deb noto'g'ri
  // talqin qilinib, endigina kiritilgan bo'sh qatorni ORQAGA QAYTARIB
  // YUBORARDI. Yechim: OQIB kelgan o'zgarish O'ZIMIZNING onChange'imizdan
  // ekanini alohida bayroq bilan belgilaymiz — shunda faqat CHINAKAM
  // tashqi o'zgarish (masalan guruhga qo'llash) `xom`ni qayta yozadi.
  const ozChaqiruvimizRef = useRef(false);
  if (qiymat !== oxirgiTashqiRef.current) {
    oxirgiTashqiRef.current = qiymat;
    if (ozChaqiruvimizRef.current) {
      ozChaqiruvimizRef.current = false;
    } else if (qiymat !== xom) {
      setXom(qiymat);
    }
  }
  return (
    <textarea
      {...qolgan}
      value={xom}
      onChange={(e) => {
        setXom(e.target.value);
        ozChaqiruvimizRef.current = true;
        ozgardi(e.target.value.split(ajratgich).map((v) => v.trim()).filter(Boolean));
      }}
    />
  );
}

/** Qism ichiga SOF MATNLI qo'shimcha qutilar qo'shish va ularni
 * savollar orasida SUDRAB joylashtirish (2026-08-08, foydalanuvchi
 * talabi: "qo'shimcha quti qo'shib ichiga text kiritish, va qayerda
 * turishini belgilash imkoni kerak").
 *
 * Saqlanishi: `TestQismi.maxsus_format` ichida `{tur:"izoh", sarlavha,
 * matn, joy}` ko'rinishida. `joy` — savol INDEKSIGA nisbatan o'rin
 * (13.5 = 14-savoldan oldin). Talaba tomonida shu qiymat bo'yicha
 * saralanadi (`ImtihonOtish: blokJoyi`).
 *
 * `maxsus_format` tarixan BITTA obyekt edi; izoh qutisi qo'shilganda u
 * RO'YXATga aylanadi. Eski jadval/oqim bloklari o'zgarishsiz saqlanadi
 * — ular bu yerda tahrirlanmaydi (murakkab tuzilma, JSON maydonida
 * qoladi), faqat tartibda ko'rinadi. */
function IzohQutilari({ savollar, boshIdx, bloklar, ozgardi, t }) {
  const [sudralayotgan, setSudralayotgan] = useState(null);

  // Savollar ham, qutilar ham bitta tartiblangan ro'yxatga qo'shiladi —
  // admin qutini AYNAN qaysi savollar orasiga qo'yayotganini ko'rib
  // turadi.
  //
  // `kalit` — savolning BUTUN TEST bo'yicha indeksi: `boshIdx` (oldingi
  // qismlardagi savollar soni) + shu qismdagi o'rni. AYNAN shu hisob
  // talaba tomonida ham ishlatiladi (`ImtihonOtish: bloklarGaAjrat`,
  // `blok.idx = boshIdx + k`).
  //
  // 2026-08-08, foydalanuvchi topgan bug: avval bu yerda `raqam - 1`
  // ishlatilardi. `raqam` esa AI generatsiyasida O'CHIRILADI
  // (`mashq_generatsiya`: `s.pop("raqam")`), ya'ni ko'p testda u umuman
  // yo'q. U holda hisob 0 dan boshlanib ketardi va Passage 2 (14-21
  // savollar) uchun quti "hamma savoldan keyin" qo'yilsa ham, talaba
  // ko'rinishida 14-savoldan OLDIN chiqib qolardi — ikki tomon turli
  // koordinatada ishlagani uchun.
  const elementlar = [
    ...savollar.map((s, i) => ({
      turi: "savol",
      kalit: boshIdx + i,
      matn: `${boshIdx + i + 1}. ${(s.savol || "").slice(0, 60)}`,
    })),
    // `Number(...)` NaN qaytaradi (null emas), shuning uchun `??` bu
    // yerda ishlamaydi — aniq tekshiruv kerak, aks holda NaN saralashni
    // buzardi.
    ...bloklar.map((b, i) => {
      const j = Number(b.joy);
      return { turi: "quti", kalit: Number.isFinite(j) ? j : -0.5, blokIdx: i, blok: b };
    }),
  ].sort((a, b) => a.kalit - b.kalit);

  /** Qutini `nishonIdx` o'rniga ko'chiradi. Yangi `joy` — o'sha
   * o'rindagi qo'shni elementlar kalitining O'RTASI. Kasr son ataylab:
   * savol indekslari butun, orasiga tushish uchun kasr kerak. */
  function qutiniKochir(blokIdx, nishonIdx) {
    const boshqalar = elementlar.filter((e) => !(e.turi === "quti" && e.blokIdx === blokIdx));
    const chegaralangan = Math.max(0, Math.min(boshqalar.length, nishonIdx));
    const oldingi = boshqalar[chegaralangan - 1];
    const keyingi = boshqalar[chegaralangan];
    let yangiJoy;
    if (!oldingi) yangiJoy = (keyingi ? keyingi.kalit : 0) - 0.5;
    else if (!keyingi) yangiJoy = oldingi.kalit + 0.5;
    else yangiJoy = (oldingi.kalit + keyingi.kalit) / 2;
    ozgardi((joriy) => joriy.map((b, i) => (i === blokIdx ? { ...b, joy: yangiJoy } : b)));
  }

  function tashlandi(nishonIdx) {
    if (sudralayotgan == null) return;
    qutiniKochir(sudralayotgan, nishonIdx);
    setSudralayotgan(null);
  }

  /** ↑/↓ tugmalari — sudrashning ISHONCHLI alternativasi (2026-08-08,
   * foydalanuvchi: "men xoxlagan joyga o'tkaza olmadim, faqat mashq
   * boshida bo'lib qoldi"). HTML5 sudrash injiq: tashlash joyi
   * aniq bo'lmasa yoki brauzer boshqacha ishlasa hech narsa bo'lmaydi.
   * Tugma har doim ishlaydi. */
  function bittaQadam(blokIdx, yonalish) {
    const joriyIdx = elementlar.findIndex((e) => e.turi === "quti" && e.blokIdx === blokIdx);
    if (joriyIdx < 0) return;
    // Ro'yxatdan o'zini olib tashlaganda indeks bir pasayadi, shuning
    // uchun yuqoriga siljish -1, pastga siljish +1 emas: pastga
    // o'tishda o'zining bo'sh o'rni ham hisobga olinadi.
    qutiniKochir(blokIdx, yonalish < 0 ? joriyIdx - 1 : joriyIdx + 1);
  }

  function qutiOz(i, patch) {
    ozgardi(bloklar.map((b, k) => (k === i ? { ...b, ...patch } : b)));
  }

  return (
    <div style={{ border: "1px dashed var(--chiziq)", borderRadius: 8, padding: 8 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <strong className="izoh">{t("imtihon_izoh_qutilari")}</strong>
        <button
          className="tugma ikkinchi kichik"
          style={{ marginLeft: "auto" }}
          onClick={() =>
            ozgardi((joriy) => [
              ...joriy,
              // Yangi quti SHU QISM boshida paydo bo'ladi. `boshIdx - 0.5`
              // — birinchi savoldan sal oldin (talaba tomonidagi standart
              // bilan bir xil: `ImtihonOtish: blokJoyi`).
              { tur: "izoh", sarlavha: "", matn: "", joy: boshIdx - 0.5 },
            ])
          }
        >
          ➕ {t("imtihon_quti_qoshish")}
        </button>
      </div>
      {bloklar.length === 0 ? (
        <div className="izoh">{t("imtihon_quti_yoq")}</div>
      ) : (
        // `maxHeight` + `overflowY` — Reading'da 40 savol bo'lishi mumkin,
        // ular butun tahrir oynasini egallab ketmasin.
        <div style={{ display: "grid", gap: 3, maxHeight: 320, overflowY: "auto" }}>
          {elementlar.map((e, i) => (
            <div
              key={e.turi === "quti" ? `q${e.blokIdx}` : `s${e.kalit}`}
              onDragEnter={(ev) => ev.preventDefault()}
              onDragOver={(ev) => {
                ev.preventDefault();
                ev.dataTransfer.dropEffect = "move";
              }}
              onDrop={(ev) => {
                ev.preventDefault();
                tashlandi(i);
              }}
              style={{
                padding: e.turi === "quti" ? 6 : "2px 6px",
                borderRadius: 6,
                border: e.turi === "quti" ? "1px solid var(--sariq-toq)" : "none",
                background: e.turi === "quti" ? "var(--sirt-2)" : "transparent",
                opacity: e.turi === "savol" ? 0.55 : 1,
                // 2026-08-08, foydalanuvchi talabi: "tugmalar tepada
                // qolib ketmasin, panelni pastga qilganda ham ko'rinib
                // tursin". Quti qatori aylantirilganda ro'yxat tepasiga
                // YOPISHIB qoladi — ⤒/↑/↓/⤓ tugmalari har doim qo'l
                // ostida bo'ladi. Savol qatorlari oddiy aylanadi.
                ...(e.turi === "quti"
                  ? { position: "sticky", top: 0, zIndex: 2 }
                  : {}),
              }}
            >
              {e.turi === "savol" ? (
                <span className="izoh">{e.matn}</span>
              ) : (
                <div style={{ display: "grid", gap: 4 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    {/* Sudrash: `setData` SHART — usiz Firefox va ba'zi
                        brauzerlar sudrashni umuman boshlamaydi. */}
                    <span
                      draggable
                      onDragStart={(ev) => {
                        ev.dataTransfer.setData("text/plain", String(e.blokIdx));
                        ev.dataTransfer.effectAllowed = "move";
                        setSudralayotgan(e.blokIdx);
                      }}
                      onDragEnd={() => setSudralayotgan(null)}
                      style={{ cursor: "grab", userSelect: "none" }}
                      title={t("imtihon_quti_sudrash")}
                    >
                      ⠿
                    </span>
                    {/* Sudrashning ishonchli alternativasi. ⤒/⤓ — eng
                        ko'p kerak bo'ladigan ikki holat: quti mashq
                        BOSHIDA yoki (masalan Matching variantlari kabi)
                        hamma savoldan KEYIN turishi. 40 savolli qismda
                        ↓ ni 40 marta bosish ma'nosiz. */}
                    <button
                      className="tugma ikkinchi kichik"
                      onClick={() => qutiniKochir(e.blokIdx, 0)}
                      disabled={i === 0}
                      title={t("imtihon_quti_eng_tepaga")}
                    >
                      ⤒
                    </button>
                    <button
                      className="tugma ikkinchi kichik"
                      onClick={() => bittaQadam(e.blokIdx, -1)}
                      disabled={i === 0}
                      title={t("imtihon_quti_yuqoriga")}
                    >
                      ↑
                    </button>
                    <button
                      className="tugma ikkinchi kichik"
                      onClick={() => bittaQadam(e.blokIdx, 1)}
                      disabled={i === elementlar.length - 1}
                      title={t("imtihon_quti_pastga")}
                    >
                      ↓
                    </button>
                    <button
                      className="tugma ikkinchi kichik"
                      onClick={() => qutiniKochir(e.blokIdx, elementlar.length)}
                      disabled={i === elementlar.length - 1}
                      title={t("imtihon_quti_eng_pastga")}
                    >
                      ⤓
                    </button>
                    <input
                      style={{ flex: 1 }}
                      placeholder={t("imtihon_quti_sarlavha")}
                      value={e.blok.sarlavha || ""}
                      onChange={(ev) => qutiOz(e.blokIdx, { sarlavha: ev.target.value })}
                    />
                    <button
                      className="tugma ikkinchi kichik"
                      style={{ color: "#d33" }}
                      onClick={() => ozgardi(bloklar.filter((_, k) => k !== e.blokIdx))}
                    >
                      {t("ochirish")}
                    </button>
                  </div>
                  <textarea
                    rows={3}
                    placeholder={t("imtihon_quti_matn")}
                    value={e.blok.matn || ""}
                    onChange={(ev) => qutiOz(e.blokIdx, { matn: ev.target.value })}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Savol turlari (2026-08-08, foydalanuvchi talabi: "mashq turini ham
// almashtirsa bo'ladigan qil"). Avval `tur` UMUMAN ko'rinmasdi, holbuki
// talaba tomonida ko'rinish AYNAN shunga qarab tanlanadi — masalan
// variantlar qutisi faqat matching/matching_headings'da chiqadi, so'z
// banki esa fill_blanks'da. Noto'g'ri tur qo'yilgan savolni tuzatib
// bo'lmasdi.
//
// Ro'yxat `pdf_generatsiya`/`mashq_generatsiya` promtlaridagi ruxsat
// etilgan qiymatlar bilan BIR XIL — frontend faqat shularni taniydi.
const SAVOL_TURLARI = [
  "multiple_choice",
  "tfng",
  "matching",
  "matching_headings",
  "fill_blanks",
  "short_answer",
  "map_labelling",
];

function SavolTahrirQatori({ savol, oz, hammagaQoll, t }) {
  function maydonOz(patch) {
    oz({ ...savol, ...patch });
  }
  const togriMatni = Array.isArray(savol.togri) ? savol.togri.join(", ") : savol.togri || "";
  return (
    <div style={{ display: "grid", gap: 4, padding: "8px 0", borderTop: "1px solid var(--chiziq)" }}>
      <div style={{ display: "flex", gap: 6 }}>
        <input
          className="izoh"
          style={{ flex: 1 }}
          placeholder={t("imtihon_guruh_sarlavha")}
          value={savol.guruh_boshi || ""}
          onChange={(e) => maydonOz({ guruh_boshi: e.target.value })}
        />
        <input
          className="izoh"
          style={{ flex: 2 }}
          placeholder={t("imtihon_guruh_korsatma")}
          value={savol.guruh_korsatma || ""}
          onChange={(e) => maydonOz({ guruh_korsatma: e.target.value })}
        />
      </div>
      <div style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
        <textarea
          style={{ flex: 1 }}
          rows={2}
          placeholder={t("imtihon_savol_matni")}
          value={savol.savol || ""}
          onChange={(e) => maydonOz({ savol: e.target.value })}
        />
        <select
          value={SAVOL_TURLARI.includes(savol.tur) ? savol.tur : ""}
          onChange={(e) => maydonOz({ tur: e.target.value })}
          title={t("imtihon_savol_turi")}
          style={{ maxWidth: 170 }}
        >
          {/* Notanish/bo'sh tur — eski testlarda uchraydi. Ro'yxatda
              ko'rsatiladi, lekin tanlab bo'lmaydi (faqat almashtirish). */}
          {!SAVOL_TURLARI.includes(savol.tur) && (
            <option value="">{savol.tur ? `? ${savol.tur}` : t("imtihon_savol_turi")}</option>
          )}
          {SAVOL_TURLARI.map((x) => (
            <option key={x} value={x}>
              {t(`imtihon_tur_${x}`)}
            </option>
          ))}
        </select>
      </div>
      <div style={{ display: "flex", gap: 6 }}>
        {/* 2026-08-08: avval bu bitta qatorli input edi va variantlar
            VERGUL bilan ajratilardi. "List of Headings" sarlavhalarida
            esa vergul bo'ladi ("A surprising discovery, made by
            accident") — bunday variant ikkiga bo'linib ketardi va
            ro'yxatni qo'lda tuzatib bo'lmasdi. Endi HAR VARIANT
            ALOHIDA QATORDA. */}
        <div style={{ flex: 2, display: "grid", gap: 3 }}>
          <RoyxatMaydoni
            rows={3}
            placeholder={t("imtihon_variantlar_izoh")}
            qiymat={(savol.variantlar || []).join("\n")}
            ajratgich={"\n"}
            ozgardi={(royxat) => maydonOz({ variantlar: royxat })}
          />
          {/* 2026-08-08: matching/matching_headings turida variantlar
              quti talabaga FAQAT guruhdagi hamma savolda AYNAN bir xil
              ro'yxat turganda ko'rsatiladi (ImtihonOtish: savollar shu
              shart bo'yicha guruhlanadi). Har savolga qo'lda ko'chirish
              zerikarli — shu tugma bir bosishda qo'llaydi. */}
          {hammagaQoll && (savol.variantlar || []).length > 1 && (
            <button
              className="tugma ikkinchi kichik"
              onClick={() => hammagaQoll(savol.variantlar)}
              title={t("imtihon_guruhga_qollash_izoh")}
            >
              {t("imtihon_guruhga_qollash")}
            </button>
          )}
        </div>
        {/* "togri" bitta matn ham (odatiy holat), massiv ham bo'lishi
            mumkin (bir savolga bir nechta qabul qilinadigan javob).
            Massiv bo'lsa — xuddi variantlar kabi, har javob alohida
            qatorda; oddiy matn bo'lsa erkin yoziladi. */}
        {/* 2026-08-15: avval `togri` oddiy MATN bo'lsa bir qatorli
            `<input>` chiqardi va uni ko'p-javobli (massiv) rejimga
            o'tkazishning HECH QANDAY yo'li yo'q edi — admin Enter bosa
            olmasdi va ikkita javobni bitta qatorga tire bilan yozishga
            majbur bo'lardi ("Jupiter-Saturn"). Endi yonida almashtirish
            tugmasi bor. */}
        <div style={{ flex: 1, display: "grid", gap: 3 }}>
          {Array.isArray(savol.togri) ? (
            <RoyxatMaydoni
              rows={3}
              placeholder={t("imtihon_togri_javob")}
              qiymat={savol.togri.join("\n")}
              ajratgich={"\n"}
              ozgardi={(royxat) => maydonOz({ togri: royxat })}
            />
          ) : (
            <input
              placeholder={t("imtihon_togri_javob")}
              value={togriMatni}
              onChange={(e) => maydonOz({ togri: e.target.value })}
            />
          )}
          <button
            className="tugma ikkinchi kichik"
            title={t("imtihon_kop_javob_izoh")}
            onClick={() =>
              maydonOz({
                togri: Array.isArray(savol.togri)
                  ? savol.togri.filter(Boolean).join(", ")
                  : String(togriMatni || "").split(/\s*,\s*/).filter(Boolean),
              })
            }
          >
            {Array.isArray(savol.togri) ? t("imtihon_bitta_javob") : t("imtihon_kop_javob")}
          </button>
        </div>
      </div>
    </div>
  );
}

/** Bitta testni TO'LIQ ochadigan tahrirlash oynasi (2026-08-05,
 * foydalanuvchi talabi: "mashq imtixondagidek to'liq ochilsin, matnni
 * qo'lda tahrirlash imkoni bo'lsin"). Yuqorida haqiqiy imtihon
 * ko'rinishi (`ImtihonOtish`, faqat KO'RISH uchun — o'zgarishsiz qayta
 * ishlatiladi), pastda har qism uchun tahrirlanadigan matn/savol
 * maydonlari (backend: `TestQismiFayllarBoshqaruvView.patch`, endi
 * matn/savollarni ham qabul qiladi). */
/** B-BOSQICH (2026-08-05): shu qismda ALLAQACHON saqlangan rasmdan AI
 * orqali savol pozitsiyalarini QAYTA aniqlab beradi — taklifni rasm
 * ustida marker sifatida ko'rsatadi (admin sudrab to'g'irlashi mumkin,
 * xuddi Kurslar rasm-quti tahrirlagichi kabi), "Qo'llash" bosilgandan
 * keyingina savollarga yoziladi (hali serverga saqlanmagan — buni
 * mavjud "Saqlash" tugmasi bajaradi). AI TAXMIN qiladi, ODAM tasdiqlaydi. */
function PozitsiyaAniqlagich({ qism, savollar, savollarniOzgartir, t }) {
  const [rasmUrl, setRasmUrl] = useState(null);
  const [taklif, setTaklif] = useState(null);
  const [band, setBand] = useState(false);
  const [xato, setXato] = useState("");
  const konteynerRef = useRef(null);
  const surinishRef = useRef(null);

  useEffect(() => {
    let url = null;
    let bekorQilindi = false;
    apiBlobUrl(qism.rasm_url).then((u) => {
      if (bekorQilindi) {
        URL.revokeObjectURL(u);
        return;
      }
      url = u;
      setRasmUrl(u);
    }).catch(() => {});
    return () => {
      bekorQilindi = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [qism.rasm_url]);

  async function aniqla() {
    setBand(true);
    setXato("");
    setTaklif(null);
    try {
      const res = await api(`/api/imtihon/qism-boshqaruv/${qism.id}/pozitsiya-aniqla/`, { method: "POST" });
      setTaklif(res.pozitsiyalar);
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  function davomEttir(e) {
    const s = surinishRef.current;
    if (!s || !konteynerRef.current) return;
    const rect = konteynerRef.current.getBoundingClientRect();
    const dx = ((e.clientX - s.boshX) / rect.width) * 100;
    const dy = ((e.clientY - s.boshY) / rect.height) * 100;
    setTaklif((prev) => ({
      ...prev,
      [s.raqam]: {
        x: Math.max(0, Math.min(100, s.boshQiymat.x + dx)),
        y: Math.max(0, Math.min(100, s.boshQiymat.y + dy)),
      },
    }));
  }
  function toxtat() {
    surinishRef.current = null;
    window.removeEventListener("mousemove", davomEttir);
    window.removeEventListener("mouseup", toxtat);
  }
  function boshlash(e, raqam) {
    e.preventDefault();
    surinishRef.current = { raqam, boshX: e.clientX, boshY: e.clientY, boshQiymat: { ...taklif[raqam] } };
    window.addEventListener("mousemove", davomEttir);
    window.addEventListener("mouseup", toxtat);
  }

  function qollash() {
    const yangi = savollar.map((s, i) => {
      const p = taklif[String(i + 1)];
      return p ? { ...s, pozitsiya: { x: Math.round(p.x), y: Math.round(p.y) } } : s;
    });
    savollarniOzgartir(yangi);
    setTaklif(null);
  }

  return (
    <div style={{ border: "1px dashed var(--chiziq)", borderRadius: 8, padding: 8 }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <button type="button" className="tugma ikkinchi kichik" onClick={aniqla} disabled={band}>
          {band ? t("yuklanmoqda") : t("imtihon_pozitsiya_aniqla")}
        </button>
        {xato && <span className="xato-xabar">{xato}</span>}
      </div>
      {taklif && rasmUrl && (
        <>
          <div className="izoh" style={{ margin: "6px 0" }}>{t("imtihon_pozitsiya_izoh")}</div>
          <div ref={konteynerRef} style={{ position: "relative", maxWidth: 480, userSelect: "none" }}>
            <img src={rasmUrl} alt="" style={{ width: "100%", display: "block", borderRadius: 6 }} draggable={false} />
            {Object.entries(taklif).map(([raqam, p]) => (
              <div
                key={raqam}
                onMouseDown={(e) => boshlash(e, raqam)}
                style={{
                  position: "absolute", left: `${p.x}%`, top: `${p.y}%`,
                  transform: "translate(-50%, -50%)", width: 20, height: 20, borderRadius: "50%",
                  background: "#2b8aef", color: "#fff", display: "flex", alignItems: "center",
                  justifyContent: "center", fontSize: 11, fontWeight: 700, cursor: "move",
                  border: "2px solid #fff",
                }}
              >
                {raqam}
              </div>
            ))}
          </div>
          <button type="button" className="tugma kichik" style={{ marginTop: 6 }} onClick={qollash}>
            {t("imtihon_pozitsiya_qollash")}
          </button>
        </>
      )}
    </div>
  );
}

/** `maxsus_format` bitta obyekt ham, ro'yxat ham bo'lishi mumkin
 * (2026-08-08) — hamma joyda ro'yxat sifatida ishlaymiz.
 * `ImtihonOtish.maxsusBloklarniOl` bilan bir xil qoida. */
function maxsusRoyxati(format) {
  if (!format) return [];
  return Array.isArray(format) ? format.filter(Boolean) : [format];
}

/** 2026-08-11 ("Javobsiz savollar hisoboti"): boshqa sahifadan (masalan
 * `JavobsizSavollarHisoboti.jsx`) ham ochish uchun eksport qilindi — u
 * ro'yxatni oldindan yuklamaydi, faqat topilgan savol qatorini
 * ko'rsatadi, shuning uchun `MashqTolaTahrir`ni to'g'ridan-to'g'ri
 * ishlatadi (yangi tahrirlash komponenti YOZILMAYDI). */
export function MashqTolaTahrir({ test, manba, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  // qismHolat[qismId] = {sarlavha, yoriqnoma, matn, savollar} — lokal
  // tahrir nusxasi, faqat "Saqlash" bosilganda serverga yuboriladi.
  const [qismHolat, setQismHolat] = useState(() => {
    const boshlangich = {};
    for (const q of test.qismlar) {
      boshlangich[q.id] = {
        sarlavha: q.sarlavha || "",
        yoriqnoma: q.yoriqnoma || "",
        matn: q.matn || "",
        savollar: q.savollar || [],
        // 2026-08-08: `maxsus_format` endi ro'yxat ham bo'lishi mumkin.
        // Sof matnli "izoh" qutilari ALOHIDA, qulay UI bilan
        // tahrirlanadi; qolgan (jadval/oqim/matn) bloklar avvalgidek
        // JSON maydonida qoladi — ular murakkab tuzilma.
        izoh_bloklar: maxsusRoyxati(q.maxsus_format).filter((b) => b.tur === "izoh"),
        maxsus_format_matn: (() => {
          const qolgan = maxsusRoyxati(q.maxsus_format).filter((b) => b.tur !== "izoh");
          if (!qolgan.length) return "";
          return JSON.stringify(qolgan.length === 1 ? qolgan[0] : qolgan, null, 2);
        })(),
      };
    }
    return boshlangich;
  });
  const [saqlanmoqdaId, setSaqlanmoqdaId] = useState(null);
  const [xato, setXato] = useState("");
  // 2026-08-08, foydalanuvchi talabi: "hamma sectionlarni bittada emas,
  // har qismini alohida tahrirlash imkonini qilib ber. mashq ustiga
  // bosganda qismlar chiqsin, qaysi qismini bossa shuni tahrirlash
  // oynasi chiqsin". Avval barcha qismlar (Reading'da 40 savol) bitta
  // uzun ro'yxatda ochilardi va kerakli joyni topish qiyin edi.
  //
  // null = qismlar RO'YXATI, aks holda o'sha qismning tahrir oynasi.
  const [tanlanganQismId, setTanlanganQismId] = useState(null);
  // Saqlanmagan o'zgarish bor qismlar — ro'yxatda belgilanadi va
  // ro'yxatga qaytishda ogohlantiriladi (aks holda tahrir bilinmay
  // yo'qolib ketardi).
  const [ozgarganlar, setOzgarganlar] = useState({});

  // `patch` obyekt ham, funksiya ham bo'lishi mumkin. Funksiya shakli
  // kerak, chunki aks holda ketma-ket ikki chaqiruv (masalan tez ikki
  // marta "Quti qo'shish" bosilsa) BIR XIL eski holatni o'qib, faqat
  // oxirgisi saqlanib qolardi — "stale closure".
  /** Qismning BIRINCHI savoli butun test bo'yicha nechanchi ekani.
   * Talaba tomonidagi hisob bilan AYNAN bir xil (`ImtihonOtish`:
   * har qism uchun oldingi qismlar savollari sanab boriladi) — quti
   * joyi ikkala tomonda bir xil ma'noni bildirishi uchun SHART. */
  function qismBoshIdx(qismId) {
    let n = 0;
    for (const q of test.qismlar) {
      if (q.id === qismId) return n;
      n += (qismHolat[q.id]?.savollar || q.savollar || []).length;
    }
    return 0;
  }

  function qismOz(qismId, patch) {
    setQismHolat((prev) => {
      const joriy = prev[qismId];
      const yangi = typeof patch === "function" ? patch(joriy) : patch;
      return { ...prev, [qismId]: { ...joriy, ...yangi } };
    });
    setOzgarganlar((prev) => ({ ...prev, [qismId]: true }));
  }

  function qismlarRoyxatigaQayt() {
    if (ozgarganlar[tanlanganQismId] && !window.confirm(t("imtihon_saqlanmagan_ogohlantirish"))) {
      return;
    }
    setTanlanganQismId(null);
    setXato("");
  }
  function savolOz(qismId, savolIdx, yangiSavol) {
    qismOz(qismId, (joriy) => {
      const yangi = [...joriy.savollar];
      yangi[savolIdx] = yangiSavol;
      return { savollar: yangi };
    });
  }

  /** Variantlar ro'yxatini shu savol atrofidagi KETMA-KET, BIR XIL
   * turdagi savollar guruhiga qo'llaydi (2026-08-08).
   *
   * Nega kerak: talaba tomonida matching/matching_headings savollari
   * bitta blokka faqat variantlari AYNAN bir xil bo'lganda birlashadi
   * va shundagina variantlar qutisi (A/B/C ro'yxati) pastda
   * ko'rsatiladi. Bitta savolga yozib qo'yish yetarli emas.
   *
   * Guruh chegarasi — `tur` o'zgarganda tugaydi. Butun qismga emas,
   * aynan shu guruhga qo'llanadi: bitta qismda ikkita alohida
   * moslashtirish topshirig'i (masalan 14-17 va 22-26) bo'lishi
   * mumkin va ular BOSHQA ro'yxatga ega. */
  function variantlarniGuruhgaQoll(qismId, savolIdx, variantlar) {
    qismOz(qismId, (joriy) => {
      const savollar = joriy.savollar;
      const tur = savollar[savolIdx]?.tur;
      let bosh = savolIdx;
      let oxir = savolIdx;
      while (bosh > 0 && savollar[bosh - 1]?.tur === tur) bosh -= 1;
      while (oxir < savollar.length - 1 && savollar[oxir + 1]?.tur === tur) oxir += 1;
      return {
        savollar: savollar.map((s, i) =>
          i >= bosh && i <= oxir ? { ...s, variantlar: [...variantlar] } : s
        ),
      };
    });
  }

  async function qismniSaqla(q) {
    const h = qismHolat[q.id];
    setXato("");
    setSaqlanmoqdaId(q.id);
    try {
      // JSON maydonidagi (jadval/oqim/matn) bloklar + alohida UI'da
      // tahrirlangan izoh qutilari BITTA ro'yxatga birlashtiriladi.
      let qolganBloklar = [];
      if (h.maxsus_format_matn.trim()) {
        try {
          qolganBloklar = maxsusRoyxati(JSON.parse(h.maxsus_format_matn));
        } catch {
          setXato(t("imtihon_maxsus_format_json_xato"));
          setSaqlanmoqdaId(null);
          return;
        }
      }
      const izohlar = (h.izoh_bloklar || []).filter((b) => (b.matn || "").trim() || (b.sarlavha || "").trim());
      const hammasi = [...qolganBloklar, ...izohlar];
      // Bitta blok bo'lsa ESKI shaklda (obyekt) saqlaymiz — mavjud
      // kontent bilan farqsiz qolsin.
      let maxsusFormat = null;
      if (hammasi.length === 1) maxsusFormat = hammasi[0];
      else if (hammasi.length > 1) maxsusFormat = hammasi;
      await api(`/api/imtihon/qism-boshqaruv/${q.id}/`, {
        method: "PATCH",
        body: {
          sarlavha: h.sarlavha,
          yoriqnoma: h.yoriqnoma,
          matn: h.matn,
          savollar: h.savollar,
          maxsus_format: maxsusFormat,
        },
      });
      setOzgarganlar((prev) => ({ ...prev, [q.id]: false }));
      onSaqlandi();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setSaqlanmoqdaId(null);
    }
  }

  return (
    <div className="blok-yuklash-qoplama">
      <div className="blok-tasdiq-karta" style={{ maxWidth: 1000 }}>
        <div className="blok-tasdiq-sarlavha-qator">
          <strong>{test.name}</strong>
          <button className="tugma ikkinchi kichik" onClick={onYopish}>{t("yopish")}</button>
        </div>

        {/* QISMLAR RO'YXATI — test ochilganda birinchi shu ko'rinadi.
            To'liq imtihon ko'rinishi (ImtihonOtish) ham faqat shu yerda:
            bitta qismni tahrirlashda u kerak emas va joyni egallaydi. */}
        {tanlanganQismId == null && (
          <>
            <div className="izoh">{t("imtihon_tola_ochish_izoh")}</div>
            <div style={{ border: "1px solid var(--chiziq)", borderRadius: 8, overflow: "hidden", maxHeight: "45vh", overflowY: "auto" }}>
              <ImtihonOtish bolim={test.bolim} manba={manba} testId={test.id} />
            </div>
            <div className="izoh" style={{ marginTop: 10 }}>{t("imtihon_qismni_tanlang")}</div>
            <div style={{ display: "grid", gap: 6 }}>
              {test.qismlar.map((q) => (
                <button
                  key={q.id}
                  className="tugma ikkinchi"
                  style={{ textAlign: "left", display: "flex", alignItems: "center", gap: 8 }}
                  onClick={() => { setTanlanganQismId(q.id); setXato(""); }}
                >
                  <strong>{q.sarlavha || `#${q.tartib}`}</strong>
                  <span className="izoh">
                    {(qismHolat[q.id]?.savollar || []).length} {t("imtihon_savol_soni")}
                    {q.rasm_url ? " · 🖼️" : ""}
                    {q.audio_url ? " · 🔊" : ""}
                  </span>
                  {ozgarganlar[q.id] && (
                    <span style={{ color: "var(--xato)", marginLeft: "auto" }}>
                      ● {t("imtihon_saqlanmagan")}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </>
        )}

        {xato && <div className="xato-xabar">{xato}</div>}

        <div style={{ display: "grid", gap: 16 }}>
          {test.qismlar.filter((q) => q.id === tanlanganQismId).map((q) => {
            const h = qismHolat[q.id];
            return (
              <div key={q.id} style={{ border: "1px solid var(--chiziq)", borderRadius: 8, padding: 10 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
                  <button className="tugma ikkinchi kichik" onClick={qismlarRoyxatigaQayt}>
                    ← {t("imtihon_qismlarga_qaytish")}
                  </button>
                  <strong>{q.sarlavha || `#${q.tartib}`}</strong>
                  <button
                    className="tugma kichik"
                    style={{ marginLeft: "auto" }}
                    onClick={() => qismniSaqla(q)}
                    disabled={saqlanmoqdaId === q.id}
                  >
                    {saqlanmoqdaId === q.id ? t("saqlanmoqda") : t("saqlash")}
                  </button>
                </div>
                <div style={{ display: "grid", gap: 6 }}>
                  <input
                    placeholder={t("imtihon_qism_sarlavha")}
                    value={h.sarlavha}
                    onChange={(e) => qismOz(q.id, { sarlavha: e.target.value })}
                  />
                  <input
                    placeholder={t("imtihon_qism_yoriqnoma")}
                    value={h.yoriqnoma}
                    onChange={(e) => qismOz(q.id, { yoriqnoma: e.target.value })}
                  />
                  {(q.tur || h.matn) !== undefined && (
                    <textarea
                      rows={4}
                      placeholder={t("imtihon_qism_matn")}
                      value={h.matn}
                      onChange={(e) => qismOz(q.id, { matn: e.target.value })}
                    />
                  )}
                  {q.rasm_url && (
                    <PozitsiyaAniqlagich
                      qism={q}
                      savollar={h.savollar}
                      savollarniOzgartir={(yangi) => qismOz(q.id, { savollar: yangi })}
                      t={t}
                    />
                  )}
                  <IzohQutilari
                    savollar={h.savollar}
                    boshIdx={qismBoshIdx(q.id)}
                    bloklar={h.izoh_bloklar || []}
                    ozgardi={(yangi) =>
                      qismOz(q.id, (joriy) => ({
                        izoh_bloklar:
                          typeof yangi === "function" ? yangi(joriy.izoh_bloklar || []) : yangi,
                      }))
                    }
                    t={t}
                  />
                  {h.savollar.map((s, si) => (
                    <SavolTahrirQatori
                      key={si}
                      savol={s}
                      oz={(yangi) => savolOz(q.id, si, yangi)}
                      // 2026-08-08: avval bu faqat matching/
                      // matching_headings turida berilardi va
                      // foydalanuvchi tugmani umuman topa olmadi —
                      // eski testlarda `tur` boshqa qiymat bo'lishi
                      // mumkin, uni ko'rish/o'zgartirish esa qiyin.
                      // Cheklov keraksiz: umumiy variantlar ro'yxati
                      // "so'z banki" (fill_blanks) uchun ham AYNAN
                      // shunday kerak. Guruh baribir `tur` bo'yicha
                      // ajratiladi, ya'ni begona savolga tegmaydi.
                      hammagaQoll={(variantlar) => variantlarniGuruhgaQoll(q.id, si, variantlar)}
                      t={t}
                    />
                  ))}
                  {(q.maxsus_format || h.maxsus_format_matn) && (
                    <div>
                      <div className="izoh" style={{ marginBottom: 4 }}>
                        {t("imtihon_maxsus_format_izoh")}
                      </div>
                      <textarea
                        rows={5}
                        style={{ fontFamily: "monospace", fontSize: 12 }}
                        value={h.maxsus_format_matn}
                        onChange={(e) => qismOz(q.id, { maxsus_format_matn: e.target.value })}
                      />
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/** Faqat admin/owner uchun — test yaratish/o'chirish/tahrirlash. */
function AdminBoshqaruv({ manba, onOchirildi }) {
  const { t } = useI18n();
  const [royxat, setRoyxat] = useState(null);
  // 2026-08-05, foydalanuvchi talabi: test/mashq nomiga bosilganda
  // imtixondagidek TO'LIQ ochilib, matnni qo'lda tahrirlash imkoni
  // bo'lsin — shu oyna uchun holat.
  const [tolaOchilgan, setTolaOchilgan] = useState(null);
  const [filtrBolim, setFiltrBolim] = useState("");
  const [jsonXato, setJsonXato] = useState("");
  const [tahrirlanayotgan, setTahrirlanayotgan] = useState(null);
  const [nomiTahrirlash, setNomiTahrirlash] = useState("");
  // Papkalar (2026-08-01) — TEKIS, har bo'lim uchun alohida. Papka
  // yaratish uchun bo'lim tanlangan bo'lishi shart ("Hammasi" filtrida
  // qaysi bo'limga tegishli ekani noaniq bo'lardi).
  const [papkalar, setPapkalar] = useState([]);
  // 2026-08-12: backend papkalarni tekis (parent-child tartibsiz)
  // qaytaradi — dropdown'da ichki papkalar o'z otasidan uzoqda,
  // boshqa otalarning bolalari bilan aralashib chiqib turardi (masalan
  // "Test 1 (Listening bor)" ostida qaysi ota papkaga tegishli ekani
  // ko'rinmasdi). Bu yerda HAR bir ota'dan keyin DARHOL o'z bolalarini
  // joylashtirib chiqamiz — ierarxiya faqat tartib orqali ko'rinadi
  // (alohida "daraxt" komponent qurish shart emas).
  const papkalarTartiblangan = (() => {
    const otalar = papkalar.filter((p) => !p.parent);
    const natija = [];
    otalar.forEach((ota) => {
      natija.push(ota);
      papkalar.filter((p) => p.parent === ota.id).forEach((b) => natija.push(b));
    });
    return natija;
  })();
  const [yangiPapka, setYangiPapka] = useState("");
  const [ochiqPapkalar, setOchiqPapkalar] = useState({});
  // 2026-08-11 kech: 2-darajali (ichki) papka qo'shish — foydalanuvchi
  // talabi ("papkalarni ichiga yana papka qo'shish"). `ichkiQoshishOchiq`
  // — qaysi 1-darajali papka ostida "ichki papka qo'shish" inputi ochiq
  // (bir vaqtda faqat bittasi).
  const [ichkiQoshishOchiq, setIchkiQoshishOchiq] = useState(null);
  const [yangiIchkiPapka, setYangiIchkiPapka] = useState("");
  // 2026-08-10, foydalanuvchi talabi: papka nomini tahrirlash — backend
  // (`TestPapkaDetailView.patch`) allaqachon bor edi, faqat UI yo'q edi.
  const [papkaTahrirlanayotgan, setPapkaTahrirlanayotgan] = useState(null);
  const [papkaNomiTahrir, setPapkaNomiTahrir] = useState("");
  // Eksport/import (2026-09-03) — `toqnashuv` nom band bo'lganda ochiladigan
  // so'rov oynasi holati: {fayl, mavjud, nom}.
  // O'chirish tasdig'i (2026-09-03) — brauzer `confirm`i o'rniga saytning
  // o'z "Ha/Yo'q" oynasi. Qiymati — o'chirilayotgan papka obyekti.
  const [ochirilmoqchi, setOchirilmoqchi] = useState(null);
  const [eksportBandId, setEksportBandId] = useState(null);
  const [importBand, setImportBand] = useState(false);
  const [importXato, setImportXato] = useState("");
  const [toqnashuv, setToqnashuv] = useState(null);
  // AI generatsiya (2026-08-02, foydalanuvchi talabi) — faqat "AI
  // mashqlari" (manba="ai") sahifasida, faqat 4 haqiqiy bo'lim uchun
  // (Mock/Hammasi'da yo'q — qaysi turni yaratish noaniq bo'lardi).
  const [band, setBand] = useState(BAND_GURUHLAR[0]);
  const [generatsiyaBormoqda, setGeneratsiyaBormoqda] = useState(false);
  const [davomEttirilayotganId, setDavomEttirilayotganId] = useState(null);
  // "Hammasi" rejimida qaysi bo'lim hozir generatsiya qilinayotgani
  // (progress ko'rsatish uchun) — bitta bo'lim rejimida ishlatilmaydi.
  const [generatsiyaBolimi, setGeneratsiyaBolimi] = useState("");

  function yukla(bolim) {
    api(`/api/imtihon/testlar-boshqaruv/?manba=${manba}${bolim ? `&bolim=${bolim}` : ""}`)
      .then(setRoyxat)
      .catch(() => {});
    // 2026-08-11: papkalar endi bo'limga BOG'LANMAGAN — bitta papka
    // Reading/Listening/Writing/Speaking testlarini birga saqlaydi
    // ("Cambridge 17 Test 1" kabi to'plam). Shuning uchun `&bolim=` YO'Q —
    // har doim shu manbadagi BARCHA papkalar so'raladi. Joriy bo'limda
    // faqat mos testlari bor papkalar ko'rinishi pastdagi render'da
    // `royxat` (bo'lim bo'yicha filtrlangan) bilan kesishtirish orqali
    // ta'minlanadi — alohida backend so'rovi kerak emas.
    api(`/api/imtihon/papkalar/?manba=${manba}`)
      .then(setPapkalar)
      .catch(() => {});
  }

  useEffect(() => {
    yukla(filtrBolim);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtrBolim, manba]);

  async function papkaYarat() {
    const nomi = yangiPapka.trim();
    // 2026-08-11: `filtrBolim` shart EMAS — papka endi bo'limga
    // bog'lanmagan, "Hammasi" tabida ham yaratish mumkin.
    if (!nomi) return;
    try {
      await api("/api/imtihon/papkalar/", {
        method: "POST",
        body: { nomi, manba },
      });
      setYangiPapka("");
      yukla(filtrBolim);
    } catch (e) {
      setJsonXato(e.data?.detail || t("xato_yuz_berdi"));
    }
  }

  // 2026-08-11 kech: ichki (2-darajali) papka yaratish — faqat 1-darajali
  // papka ostida ko'rsatiladigan tugma orqali chaqiriladi, `parentId`
  // shu 1-darajali papka id'si.
  async function ichkiPapkaYarat(parentId) {
    const nomi = yangiIchkiPapka.trim();
    if (!nomi) return;
    try {
      await api("/api/imtihon/papkalar/", {
        method: "POST",
        body: { nomi, manba, parent: parentId },
      });
      setYangiIchkiPapka("");
      setIchkiQoshishOchiq(null);
      yukla(filtrBolim);
    } catch (e) {
      setJsonXato(e.data?.detail || t("xato_yuz_berdi"));
    }
  }

  /** 2026-09-03: tasdiq brauzerning `confirm` oynasi orqali EMAS,
   * saytning o'z "Ha/Yo'q" oynasi orqali so'raladi (foydalanuvchi
   * talabi) — shuning uchun bu funksiya endi faqat o'chiradi. */
  async function papkaOchir(id) {
    try {
      await api(`/api/imtihon/papkalar/${id}/`, { method: "DELETE" });
      setOchirilmoqchi(null);
      yukla(filtrBolim);
    } catch (e) {
      setJsonXato(e.data?.detail || t("xato_yuz_berdi"));
      setOchirilmoqchi(null);
    }
  }

  async function papkaNominiSaqla(id) {
    const nomi = papkaNomiTahrir.trim();
    if (!nomi) return;
    try {
      await api(`/api/imtihon/papkalar/${id}/`, { method: "PATCH", body: { nomi } });
      setPapkaTahrirlanayotgan(null);
      yukla(filtrBolim);
    } catch (e) {
      setJsonXato(e.data?.detail || t("xato_yuz_berdi"));
    }
  }

  async function papkagaKochir(testId, papkaId) {
    try {
      await api(`/api/imtihon/testlar-boshqaruv/${testId}/`, {
        method: "PATCH",
        body: { papka: papkaId || null },
      });
      yukla(filtrBolim);
    } catch (e) {
      setJsonXato(e.data?.detail || t("xato_yuz_berdi"));
    }
  }

  async function generatsiyaQil() {
    if (!filtrBolim || filtrBolim === "mock") return;
    setGeneratsiyaBormoqda(true);
    setJsonXato("");
    try {
      const d = await api("/api/imtihon/mashq-generatsiya/", {
        method: "POST",
        body: { bolim: filtrBolim, band },
      });
      yukla(filtrBolim);
      // 2026-08-08: Listening o'rtada uzilsa test QISMAN saqlanadi —
      // xato ko'rsatiladi, lekin ish yo'qolmaydi, ro'yxatda "Davom
      // ettirish" tugmasi chiqadi.
      if (d?.chala_xato) setJsonXato(d.chala_xato);
    } catch (e) {
      setJsonXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setGeneratsiyaBormoqda(false);
    }
  }

  // "Hammasi" filtrida — 4 turni (reading/listening/writing/speaking)
  // KETMA-KET generatsiya qiladi (2026-08-02, foydalanuvchi talabi: bitta
  // tugma, hammasi birga). Ketma-ket (parallel emas) — Listening TTS'ning
  // kunlik/daqiqalik limiti bor, bir vaqtda ko'p so'rov yuborish xavfli.
  // Birortasi xato bersa ham qolganlari davom etadi, oxirida barcha
  // xatolar birga ko'rsatiladi.
  async function hammasiniGeneratsiyaQil() {
    setGeneratsiyaBormoqda(true);
    setJsonXato("");
    const xatolar = [];
    for (const b of ["reading", "listening", "writing", "speaking"]) {
      setGeneratsiyaBolimi(b);
      try {
        await api("/api/imtihon/mashq-generatsiya/", { method: "POST", body: { bolim: b, band } });
      } catch (e) {
        xatolar.push(`${t(`mashq_bolim_${b}`) || b}: ${e.data?.detail || t("xato_yuz_berdi")}`);
      }
    }
    setGeneratsiyaBolimi("");
    setGeneratsiyaBormoqda(false);
    if (xatolar.length) setJsonXato(xatolar.join(" | "));
    yukla(filtrBolim);
  }

  async function nominiSaqla(testId) {
    const nomi = nomiTahrirlash.trim();
    if (!nomi) return;
    try {
      await api(`/api/imtihon/testlar-boshqaruv/${testId}/`, {
        method: "PATCH",
        body: { name: nomi },
      });
      yukla(filtrBolim);
    } catch (e) {
      setJsonXato(e.data?.detail || t("xato_yuz_berdi"));
    }
  }

  // AI Listening testi 4 part bo'lishi kerak. Kamroq bo'lsa — generatsiya
  // o'rtasida uzilgan (2026-08-08). Alohida bayroq/migratsiya kerak emas,
  // backendda ham aynan shu qoida (`views._chala_listening_mi`).
  function chalaListeningmi(test) {
    return manba === "ai" && test.bolim === "listening" && (test.qismlar?.length || 0) < 4;
  }

  async function listeningDavomEttir(test) {
    setJsonXato("");
    setDavomEttirilayotganId(test.id);
    try {
      const d = await api(`/api/imtihon/${test.id}/listening-davom/`, { method: "POST", body: { band } });
      yukla(filtrBolim);
      // Davom ettirishda ham uzilishi mumkin (masalan TTS limiti hali
      // ochilmagan) — u holda yana qisman saqlanadi va tugma qoladi.
      if (d.chala_xato) setJsonXato(d.chala_xato);
    } catch (e) {
      setJsonXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setDavomEttirilayotganId(null);
    }
  }

  async function qismgaFaylYukla(qismId, maydon, fayl) {
    const fd = new FormData();
    fd.append(maydon, fayl);
    await apiForm(`/api/imtihon/qism-boshqaruv/${qismId}/`, { method: "PATCH", formData: fd });
  }

  async function qismgaAudioYukla(qismId, fayl) {
    await qismgaFaylYukla(qismId, "audio_fayl", fayl);
  }

  async function rasmBiriktir(qismId, fayl) {
    if (!fayl) return;
    try {
      await qismgaFaylYukla(qismId, "rasm", fayl);
      yukla(filtrBolim);
    } catch (e) {
      setJsonXato(e.data?.detail || t("xato_yuz_berdi"));
    }
  }

  async function audioBiriktir(qismId, fayl) {
    if (!fayl) return;
    try {
      await qismgaAudioYukla(qismId, fayl);
      yukla(filtrBolim);
    } catch (e) {
      setJsonXato(e.data?.detail || t("xato_yuz_berdi"));
    }
  }

  // 2026-08-10, foydalanuvchi talabi: mavjud audio/rasmni O'CHIRISH
  // (masalan noto'g'ri fayl yuklangan bo'lsa, qayta yuklashdan oldin).
  async function qismdanFayilniOchir(qismId, maydon) {
    if (!window.confirm(t("imtihon_fayl_ochirish_tasdiq"))) return;
    try {
      await api(`/api/imtihon/qism-boshqaruv/${qismId}/?maydon=${maydon}`, { method: "DELETE" });
      yukla(filtrBolim);
    } catch (e) {
      setJsonXato(e.data?.detail || t("xato_yuz_berdi"));
    }
  }

  // Real IELTS Listening testi odatda BITTA uzluksiz audio — bo'lib
  // olish (splitting) o'rniga xuddi shu faylning o'zi barcha qismlarga
  // (Part 1-4) biriktiriladi, talaba istalgan qismda to'liq audioni
  // tinglab, kerakli joyidan pauza/seek qilib javob beradi.
  async function hammasigaAudioBiriktir(test, fayl) {
    if (!fayl) return;
    try {
      for (const q of test.qismlar) {
        await qismgaAudioYukla(q.id, fayl);
      }
      yukla(filtrBolim);
    } catch (e) {
      setJsonXato(e.data?.detail || t("xato_yuz_berdi"));
    }
  }

  // ── Eksport / import (2026-09-03, foydalanuvchi talabi: Kurslardagi
  // "Saqlash/Yuklash" IELTS testlarida ham bo'lsin). Qamrov: BITTA test =
  // BITTA ZIP (qismlari, savollari, audio va rasm fayllari bilan).
  async function eksportQil(test) {
    setEksportBandId(test.id);
    try {
      await apiFayluniYuklab(`/api/imtihon/testlar-boshqaruv/${test.id}/eksport/`);
    } catch (e) {
      setImportXato(e.message || t("xato_yuz_berdi"));
    } finally {
      setEksportBandId(null);
    }
  }

  /** ZIPni backendga yuboradi. `rejim` bo'sh bo'lsa va shu nomli test
   * allaqachon bo'lsa — backend 409 qaytaradi va biz foydalanuvchidan
   * so'raymiz (almashtirish yoki yangi nom bilan qo'shish). */
  async function importYubor(fayl, rejim = "", nom = "") {
    const fd = new FormData();
    fd.append("fayl", fayl);
    fd.append("manba", manba);
    if (rejim) fd.append("rejim", rejim);
    if (nom) fd.append("nom", nom);
    return apiForm("/api/imtihon/testlar-import/", { method: "POST", formData: fd });
  }

  async function importQil(e) {
    const fayl = e.target.files?.[0];
    e.target.value = "";
    if (!fayl) return;
    setImportXato("");
    setImportBand(true);
    try {
      await importYubor(fayl);
      yukla(filtrBolim);
    } catch (e2) {
      if (e2.status === 409 && e2.data?.holat === "nom_band") {
        // Nom band — hech narsa o'zgartirilmadi, qarorni foydalanuvchi beradi.
        setToqnashuv({
          fayl,
          mavjud: e2.data.mavjud,
          nom: e2.data.taklif_nom || "",
        });
      } else {
        setImportXato(e2.data?.detail || e2.message || t("xato_yuz_berdi"));
      }
    } finally {
      setImportBand(false);
    }
  }

  async function toqnashuvniHal(rejim) {
    if (!toqnashuv) return;
    if (rejim === "almashtir" && !window.confirm(t("imtihon_import_almashtir_tasdiq"))) return;
    const nom = rejim === "yangi" ? toqnashuv.nom.trim() : "";
    if (rejim === "yangi" && !nom) return;
    setImportXato("");
    setImportBand(true);
    try {
      await importYubor(toqnashuv.fayl, rejim, nom);
      setToqnashuv(null);
      yukla(filtrBolim);
    } catch (e2) {
      setImportXato(e2.data?.detail || e2.message || t("xato_yuz_berdi"));
    } finally {
      setImportBand(false);
    }
  }

  async function ochir(id) {
    if (!window.confirm(t("imtihon_ochirish_tasdiq"))) return;
    try {
      await api(`/api/imtihon/testlar-boshqaruv/${id}/`, { method: "DELETE" });
      yukla(filtrBolim);
      // Pastdagi test yechish oynasi shu testni ochib turgan bo'lsa —
      // yopilishi uchun xabar beramiz (2026-07-31).
      onOchirildi?.(id);
    } catch {
      // sokin
    }
  }

  return (
    <>
    <div style={{ display: "grid", gap: 20 }}>
      {manba !== "ai" && (
        <KiritishPanel
          manba={manba}
          qismgaFaylYukla={qismgaFaylYukla}
          royxatniYangila={() => yukla(filtrBolim)}
        />
      )}

      <div className="karta">
        <h3>{t("imtihon_mavjud_royxat")}</h3>
        <div className="tab-guruh" style={{ marginBottom: 12 }}>
          <button className={filtrBolim === "" ? "aktiv" : ""} onClick={() => setFiltrBolim("")}>
            {t("hammasi")}
          </button>
          <button className={filtrBolim === "reading" ? "aktiv" : ""} onClick={() => setFiltrBolim("reading")}>
            {t("reading_bolimi")}
          </button>
          <button className={filtrBolim === "listening" ? "aktiv" : ""} onClick={() => setFiltrBolim("listening")}>
            {t("listening_bolimi")}
          </button>
          <button className={filtrBolim === "writing" ? "aktiv" : ""} onClick={() => setFiltrBolim("writing")}>
            {t("mashq_bolim_writing")}
          </button>
          <button className={filtrBolim === "speaking" ? "aktiv" : ""} onClick={() => setFiltrBolim("speaking")}>
            {t("mashq_bolim_speaking")}
          </button>
        </div>

        {/* AI generatsiya (2026-08-02) — faqat "AI mashqlari" sahifasida.
            "Hammasi" filtrida — bitta tugma bilan 4 turni ketma-ket
            generatsiya qiladi (foydalanuvchi talabi). Bitta bo'lim
            tanlangan bo'lsa — faqat o'shani. Mock'da yo'q (noaniq). */}
        {manba === "ai" && filtrBolim !== "mock" && (
          <div style={{ marginBottom: 14, padding: 10, background: "var(--sirt-2)", borderRadius: 8, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <strong style={{ fontSize: 14 }}>{t("imtihon_generatsiya")}</strong>
            <select value={band} onChange={(e) => setBand(e.target.value)} disabled={generatsiyaBormoqda}>
              {BAND_GURUHLAR.map((b) => (
                <option key={b} value={b}>{t("imtihon_band")} {b}</option>
              ))}
            </select>
            {filtrBolim === "" ? (
              <button type="button" className="tugma" onClick={hammasiniGeneratsiyaQil} disabled={generatsiyaBormoqda}>
                {generatsiyaBormoqda
                  ? `${t("imtihon_generatsiya_bormoqda")} (${t(`mashq_bolim_${generatsiyaBolimi}`) || generatsiyaBolimi})`
                  : t("imtihon_generatsiya_hammasi_qil")}
              </button>
            ) : (
              <button type="button" className="tugma" onClick={generatsiyaQil} disabled={generatsiyaBormoqda}>
                {generatsiyaBormoqda ? t("imtihon_generatsiya_bormoqda") : t("imtihon_generatsiya_qil")}
              </button>
            )}
            {generatsiyaBormoqda && (
              <span className="izoh">
                {(filtrBolim === "listening" || filtrBolim === "")
                  ? t("imtihon_generatsiya_listening_izoh")
                  : t("imtihon_generatsiya_izoh")}
              </span>
            )}
            {/* Generatsiya xatosi (2026-08-02 tuzatildi) — avval `jsonXato`
                holatga saqlanardi, lekin hech qayerda ko'rsatilmasdi,
                ya'ni Listening TTS limiti tugasa yoki boshqa xato bo'lsa
                talaba/admin sababini bilmay qolardi. */}
            {jsonXato && !generatsiyaBormoqda && (
              <div className="xato-xabar" style={{ width: "100%" }}>{jsonXato}</div>
            )}
          </div>
        )}

        {/* Papkalar (2026-08-01, 2026-08-11: bo'limga bog'lanmagan) — bitta
            papka barcha bo'lim testlarini birga saqlaydi (masalan
            "Cambridge 17 Test 1"), shuning uchun "Hammasi" tabida ham
            yaratish mumkin — bo'lim tanlash shart emas. */}
        <div style={{ marginBottom: 14, padding: 10, background: "var(--sirt-2)", borderRadius: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <strong style={{ fontSize: 14 }}>{t("imtihon_papkalar")}</strong>
            <input
              placeholder={t("imtihon_papka_nomi")}
              value={yangiPapka}
              onChange={(e) => setYangiPapka(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && papkaYarat()}
              style={{ maxWidth: 220 }}
            />
            <button type="button" className="tugma" onClick={papkaYarat} disabled={!yangiPapka.trim()}>
              {t("imtihon_papka_qoshish")}
            </button>
          </div>
          {/* 2026-09-03, foydalanuvchi talabi: papkalar RO'YXATI bu
              paneldan butunlay olib tashlandi — u juda uzayib ketar va
              chalkashtirar edi. Endi papkalar faqat pastdagi test
              ro'yxatida (accordion) ko'rinadi va o'sha yerda
              boshqariladi. Bu panelda faqat YANGI (1-darajali) papka
              yaratish qoldi. */}
        </div>

        {/* Import (2026-09-03) — eksport qilingan ZIPdan testni tiklash.
            Papkalar paneli uzun bo'lganda bu tugma "💾 Saqlash"dan juda
            uzoqlashib ketardi (foydalanuvchi talabi), shuning uchun endi
            aynan test ro'yxatining USTIDA turadi. */}
        <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
          {importXato && <span className="xato-xabar">{importXato}</span>}
          <label className="tugma ikkinchi" style={{ cursor: "pointer" }}>
            {importBand ? t("yuklanmoqda") : t("imtihon_import")}
            <input
              type="file"
              accept=".zip,application/zip"
              onChange={importQil}
              disabled={importBand}
              style={{ display: "none" }}
            />
          </label>
        </div>

        {!royxat ? (
          <div className="yuklanmoqda">{t("yuklanmoqda")}</div>
        ) : royxat.length === 0 ? (
          <span className="izoh">{t("imtihon_royxat_boshi")}</span>
        ) : (
          <div style={{ display: "grid", gap: 8 }}>
            {/* Papkalar bo'yicha guruhlangan (2026-08-01, 2026-08-11
                tuzatildi: ichki papka endi tashqi papka ICHIDA, alohida
                emas — foydalanuvchi topib berdi: "ichki papka kerakli
                papka ichida emas, alohida chiqyabdi"). Sabab: avval
                RO'YXAT tekis edi — faqat DIRECT test bor papkalar
                chiqardi, shuning uchun tashqi papkaning o'zida test
                bo'lmasa (hammasi ichki papkada bo'lsa) u ro'yxatdan
                BUTUNLAY tushib qolar, ichki papka esa "bosh"siz,
                mustaqil qatorday ko'rinardi. Endi HAR DOIM tashqi papka
                birinchi aylanadi, ichki papkalar ESA UNING ICHIDA
                (accordion ochilgach) ko'rinadi. Papkasiz testlar ro'yxat
                oxirida, tekis. */}
            {/* 2026-09-03, foydalanuvchi talabi: papka BOSHQARUVI endi
                aynan shu yerda — yuqoridagi "Papkalar" panelida ro'yxat
                umuman ko'rsatilmaydi. Shu sababli bu yerda TESTI YO'Q
                papkalar ham chiqadi (avval faqat testi borlari chiqardi):
                aks holda yangi yaratilgan bo'sh papkaga ichki papka
                qo'shib ham, uni o'chirib ham bo'lmasdi. */}
            {papkalar
              .filter((p) => !p.parent)
              .map((top) => {
                const ichkilar = papkalar.filter((p) => p.parent === top.id);
                const topTestlar = royxat.filter((r) => r.papka === top.id);
                const jamiSoni =
                  topTestlar.length +
                  ichkilar.reduce((s2, ich) => s2 + royxat.filter((r) => r.papka === ich.id).length, 0);
                return (
                  <div key={top.id} style={{ border: "1px solid var(--chiziq)", borderRadius: 8, overflow: "hidden" }}>
                    <div
                      className="imtihon-papka-sarlavha"
                      style={{ padding: "8px 10px" }}
                      onClick={() => setOchiqPapkalar((v) => ({ ...v, [top.id]: !v[top.id] }))}
                    >
                      {/* Testlar soni nom YONIDA (2026-09-03, foydalanuvchi
                          talabi: avval o'ng chekkada edi) — o'ng chekka
                          endi o'chirish tugmasiniki. */}
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                        <span>{ochiqPapkalar[top.id] ? "▾" : "▸"} 📁</span>
                        {papkaNomi(top)}
                        <span className="izoh">{jamiSoni}</span>
                      </span>
                      {papkaOchirishTugmasi(top)}
                    </div>
                    {ochiqPapkalar[top.id] && (
                      <div style={{ display: "grid", gap: 8, padding: "0 8px 8px" }}>
                        {topTestlar.map((test) => testKartasi(test))}
                        {ichkilar.map((ich) => {
                          const ichTestlar = royxat.filter((r) => r.papka === ich.id);
                          return (
                            <div
                              key={ich.id}
                              style={{
                                border: "1px solid var(--chiziq)", borderRadius: 8,
                                overflow: "hidden", marginLeft: 20,
                              }}
                            >
                              <div
                                className="imtihon-papka-sarlavha"
                                style={{ padding: "8px 10px" }}
                                onClick={() => setOchiqPapkalar((v) => ({ ...v, [ich.id]: !v[ich.id] }))}
                              >
                                <span style={{ display: "inline-flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                                  <span>{ochiqPapkalar[ich.id] ? "▾" : "▸"} 📂</span>
                                  {papkaNomi(ich)}
                                  <span className="izoh">{ichTestlar.length}</span>
                                </span>
                                {papkaOchirishTugmasi(ich)}
                              </div>
                              {ochiqPapkalar[ich.id] && (
                                <div style={{ display: "grid", gap: 8, padding: "0 8px 8px" }}>
                                  {ichTestlar.map((test) => testKartasi(test))}
                                </div>
                              )}
                            </div>
                          );
                        })}
                        {/* Ichki papka qo'shish — papka OCHILGANDA shu yerda
                            (2026-09-03, foydalanuvchi talabi). */}
                        {ichkiQoshishOchiq === top.id ? (
                          <div style={{ display: "flex", gap: 6, marginLeft: 20, flexWrap: "wrap" }}>
                            <input
                              placeholder={t("imtihon_papka_nomi")}
                              value={yangiIchkiPapka}
                              autoFocus
                              onChange={(e) => setYangiIchkiPapka(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") ichkiPapkaYarat(top.id);
                                if (e.key === "Escape") setIchkiQoshishOchiq(null);
                              }}
                              style={{ maxWidth: 200, fontSize: 13 }}
                            />
                            <button
                              type="button"
                              className="tugma kichik"
                              onClick={() => ichkiPapkaYarat(top.id)}
                              disabled={!yangiIchkiPapka.trim()}
                            >
                              {t("imtihon_papka_qoshish")}
                            </button>
                            <button
                              type="button"
                              className="tugma kichik ikkinchi"
                              onClick={() => setIchkiQoshishOchiq(null)}
                            >
                              {t("kurs_blok_bekor_qilish")}
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => {
                              setYangiIchkiPapka("");
                              setIchkiQoshishOchiq(top.id);
                            }}
                            title={t("imtihon_ichki_papka_qoshish")}
                            style={{
                              marginLeft: 20, width: "fit-content",
                              display: "inline-flex", alignItems: "center", gap: 6,
                              padding: "5px 12px", borderRadius: 20, cursor: "pointer",
                              border: "1px dashed var(--chiziq)", background: "transparent",
                              color: "var(--matn-sokin)", fontSize: 13,
                            }}
                          >
                            + {t("imtihon_ichki_papka")}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            {royxat.filter((test) => !test.papka).map((test) => testKartasi(test))}
          </div>
        )}
      </div>
    </div>
    {tolaOchilgan && (
      <MashqTolaTahrir
        test={tolaOchilgan}
        manba={manba}
        onYopish={() => setTolaOchilgan(null)}
        // 2026-08-08: avval saqlangach oyna butunlay YOPILARDI. Qismlar
        // alohida tahrirlanadigan bo'lgach bu noqulay — har qismdan
        // keyin testni qaytadan ochib, qismni qaytadan tanlash kerak
        // bo'lardi. Endi ro'yxat yangilanadi, oyna esa ochiq qoladi.
        onSaqlandi={() => yukla(filtrBolim)}
      />
    )}
    {/* Papkani o'chirish tasdig'i — saytning O'Z oynasi (2026-09-03,
        foydalanuvchi talabi: brauzerning `confirm` oynasi emas). */}
    {ochirilmoqchi && (
      <div className="blok-yuklash-qoplama">
        <div className="blok-tasdiq-karta" style={{ maxWidth: 420 }}>
          <div className="blok-tasdiq-sarlavha-qator">
            <strong>
              {ochirilmoqchi.parent ? "📂" : "📁"} {ochirilmoqchi.nomi}
            </strong>
          </div>
          <div style={{ marginBottom: 14 }}>{t("imtihon_papka_ochirish_tasdiq")}</div>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button
              type="button"
              className="tugma ikkinchi"
              onClick={() => setOchirilmoqchi(null)}
            >
              {t("yoq")}
            </button>
            <button
              type="button"
              className="tugma"
              style={{ background: "#d33", borderColor: "#d33", color: "#fff" }}
              onClick={() => papkaOchir(ochirilmoqchi.id)}
            >
              {t("ha")}
            </button>
          </div>
        </div>
      </div>
    )}
    {/* Import: nom to'qnashuvi (2026-09-03, foydalanuvchi qarori — jimgina
        almashtirmasdan ham, jimgina nusxa yaratmasdan ham emas, ALBATTA
        so'raladi). Bu nuqtada backend hech narsa o'zgartirmagan. */}
    {toqnashuv && (
      <div className="blok-yuklash-qoplama">
        <div className="blok-tasdiq-karta" style={{ maxWidth: 460 }}>
          <div className="blok-tasdiq-sarlavha-qator">
            <strong>{t("imtihon_import_nom_band")}</strong>
          </div>
          <div className="izoh" style={{ marginBottom: 12 }}>
            «{toqnashuv.mavjud.name}» — {t(`mashq_bolim_${toqnashuv.mavjud.bolim}`)},{" "}
            {toqnashuv.mavjud.qismlar_soni} {t("imtihon_qism_soni")}
          </div>
          <div style={{ display: "grid", gap: 10 }}>
            <button
              type="button"
              className="tugma ikkinchi"
              style={{ color: "#d33" }}
              disabled={importBand}
              onClick={() => toqnashuvniHal("almashtir")}
            >
              {t("imtihon_import_almashtir")}
            </button>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <input
                type="text"
                value={toqnashuv.nom}
                placeholder={t("imtihon_import_yangi_nom")}
                onChange={(e) => setToqnashuv((v) => ({ ...v, nom: e.target.value }))}
                style={{ flex: 1, minWidth: 180 }}
              />
              <button
                type="button"
                className="tugma"
                disabled={importBand || !toqnashuv.nom.trim()}
                onClick={() => toqnashuvniHal("yangi")}
              >
                {t("imtihon_import_yangi")}
              </button>
            </div>
            {importXato && <div className="xato-xabar">{importXato}</div>}
            <button
              type="button"
              className="tugma ikkinchi"
              disabled={importBand}
              onClick={() => {
                setToqnashuv(null);
                setImportXato("");
              }}
            >
              {t("kurs_blok_bekor_qilish")}
            </button>
          </div>
        </div>
      </div>
    )}
    </>
  );

  /** Papka nomi — bosilganda joyida tahrirlanadi (accordion ochilib
   * ketmasligi uchun hodisa to'xtatiladi). Avval bu "papka chipi"
   * ichida edi, 2026-09-03 da chiplar olib tashlangach shu yerga
   * ko'chirildi — nomni o'zgartirish imkoni yo'qolmasin. */
  function papkaNomi(p) {
    if (papkaTahrirlanayotgan === p.id) {
      return (
        <input
          type="text"
          value={papkaNomiTahrir}
          autoFocus
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => setPapkaNomiTahrir(e.target.value)}
          onKeyDown={(e) => {
            e.stopPropagation();
            if (e.key === "Enter") papkaNominiSaqla(p.id);
            if (e.key === "Escape") setPapkaTahrirlanayotgan(null);
          }}
          onBlur={() => papkaNominiSaqla(p.id)}
          style={{ maxWidth: 200, fontSize: 13 }}
        />
      );
    }
    return (
      <span
        title={t("imtihon_papka_nomini_tahrirlash")}
        onClick={(e) => {
          e.stopPropagation();
          setPapkaTahrirlanayotgan(p.id);
          setPapkaNomiTahrir(p.nomi);
        }}
      >
        {p.nomi}
      </span>
    );
  }

  /** O'chirish tugmasi — sarlavhaning O'NG chekkasida (2026-09-03,
   * foydalanuvchi talabi: avval u yerda testlar soni turardi).
   * Brauzerning o'z `confirm` oynasi EMAS — saytning o'z "Ha/Yo'q"
   * oynasi ochiladi. */
  function papkaOchirishTugmasi(p) {
    return (
      <button
        type="button"
        title={t("ochirish")}
        onClick={(e) => {
          e.stopPropagation();
          setOchirilmoqchi(p);
        }}
        style={{
          border: "none", background: "none", color: "#d33", cursor: "pointer",
          fontSize: 18, lineHeight: 1, padding: "0 4px",
        }}
      >
        ×
      </button>
    );
  }

}

/** "IELTS testlari" — yagona sahifa: admin/owner uchun boshqaruv (yuqorida,
 * agar ruxsati bo'lsa) + talaba/admin/owner uchun yechish (pastda, hammaga). */
/** Bitta komponent ikki bo'limga xizmat qiladi (2026-07-27):
 *   manba="admin" -> "IELTS testlari" (admin/owner qo'lda yuklagan testlar)
 *   manba="ai"    -> "AI mashqlari"   (to'liq AI generatsiya qilgan testlar)
 * Butun mexanizm (test yechish, mock, baholash, audio, rasm) umumiy — faqat
 * ro'yxatlar `manba` bo'yicha ajratiladi, shuning uchun kod takrorlanmaydi. */
export default function ImtihonBoshqarish({ manba = "admin" }) {
  const { t } = useI18n();
  const { profil } = useProfil();
  const adminMi = profil?.is_owner || profil?.role === "admin";
  // IELTS/CEFR — yuqori darajadagi guruh (2026-08-01). CEFR faqat "AI
  // mashqlari"da ko'rinadi va hozircha yopiq (mashqlar keyinroq
  // qo'shiladi) — shuning uchun bosilganda "tez orada" ko'rsatiladi,
  // IELTS'ning "Mavjud testlar" paneli/bo'lim tugmalari yashiriladi.
  const [guruh, setGuruh] = useState("ielts");
  const [bolim, setBolim] = useState("writing");
  // Admin yuqorida testni o'chirsa, pastdagi yechish oynasi o'sha testni
  // ochib turgan bo'lishi mumkin — id shu yerdan pastga uzatiladi.
  const [ochirilganId, setOchirilganId] = useState(null);

  return (
    <div style={{ display: "grid", gap: 20 }}>
      {manba === "ai" && (
        <div className="tab-guruh">
          <button className={guruh === "ielts" ? "aktiv" : ""} onClick={() => setGuruh("ielts")}>
            IELTS
          </button>
          <button className={guruh === "cefr" ? "aktiv" : ""} onClick={() => setGuruh("cefr")}>
            CEFR
          </button>
        </div>
      )}

      {guruh === "cefr" ? (
        <div className="karta">
          <span className="izoh">CEFR · {t("tez_orada")}</span>
        </div>
      ) : (
        <>
          {adminMi && <AdminBoshqaruv manba={manba} onOchirildi={setOchirilganId} />}

          <div>
            <div className="tab-guruh" style={{ marginBottom: 12 }}>
              <button className={bolim === "writing" ? "aktiv" : ""} onClick={() => setBolim("writing")}>
                {t("nav_writing")}
              </button>
              <button className={bolim === "speaking" ? "aktiv" : ""} onClick={() => setBolim("speaking")}>
                {t("nav_speaking")}
              </button>
              <button className={bolim === "reading" ? "aktiv" : ""} onClick={() => setBolim("reading")}>
                {t("reading_bolimi")}
              </button>
              <button className={bolim === "listening" ? "aktiv" : ""} onClick={() => setBolim("listening")}>
                {t("listening_bolimi")}
              </button>
              <button className={bolim === "mock" ? "aktiv" : ""} onClick={() => setBolim("mock")}>
                {t("mock_bolimi")}
              </button>
            </div>
            {(bolim === "writing" || bolim === "speaking") && (
              <ImtihonYozGap bolim={bolim} manba={manba} />
            )}
            {(bolim === "reading" || bolim === "listening") && (
              <ImtihonOtish bolim={bolim} manba={manba} ochirilganId={ochirilganId} />
            )}
            {bolim === "mock" && <ImtihonMock manba={manba} />}
          </div>
        </>
      )}
    </div>
  );
}
