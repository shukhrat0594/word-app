import { useEffect, useRef, useState } from "react";
import { api, apiBlobUrl, apiForm } from "../api";
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
function SavolTahrirQatori({ savol, oz, t }) {
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
      <textarea
        rows={2}
        placeholder={t("imtihon_savol_matni")}
        value={savol.savol || ""}
        onChange={(e) => maydonOz({ savol: e.target.value })}
      />
      <div style={{ display: "flex", gap: 6 }}>
        <input
          style={{ flex: 2 }}
          placeholder={t("imtihon_variantlar_izoh")}
          value={(savol.variantlar || []).join(", ")}
          onChange={(e) =>
            maydonOz({
              variantlar: e.target.value.split(",").map((v) => v.trim()).filter(Boolean),
            })
          }
        />
        <input
          style={{ flex: 1 }}
          placeholder={t("imtihon_togri_javob")}
          value={togriMatni}
          onChange={(e) => {
            const qism = e.target.value.split(",").map((v) => v.trim()).filter(Boolean);
            maydonOz({ togri: Array.isArray(savol.togri) ? qism : e.target.value });
          }}
        />
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

function MashqTolaTahrir({ test, manba, onYopish, onSaqlandi }) {
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
        maxsus_format_matn: q.maxsus_format ? JSON.stringify(q.maxsus_format, null, 2) : "",
      };
    }
    return boshlangich;
  });
  const [saqlanmoqdaId, setSaqlanmoqdaId] = useState(null);
  const [xato, setXato] = useState("");

  function qismOz(qismId, patch) {
    setQismHolat((prev) => ({ ...prev, [qismId]: { ...prev[qismId], ...patch } }));
  }
  function savolOz(qismId, savolIdx, yangiSavol) {
    const h = qismHolat[qismId];
    const yangi = [...h.savollar];
    yangi[savolIdx] = yangiSavol;
    qismOz(qismId, { savollar: yangi });
  }

  async function qismniSaqla(q) {
    const h = qismHolat[q.id];
    setXato("");
    setSaqlanmoqdaId(q.id);
    try {
      let maxsusFormat = q.maxsus_format;
      if (h.maxsus_format_matn.trim()) {
        try {
          maxsusFormat = JSON.parse(h.maxsus_format_matn);
        } catch {
          setXato(t("imtihon_maxsus_format_json_xato"));
          setSaqlanmoqdaId(null);
          return;
        }
      } else {
        maxsusFormat = null;
      }
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

        <div className="izoh">{t("imtihon_tola_ochish_izoh")}</div>
        <div style={{ border: "1px solid var(--chiziq)", borderRadius: 8, overflow: "hidden", maxHeight: "45vh", overflowY: "auto" }}>
          <ImtihonOtish bolim={test.bolim} manba={manba} testId={test.id} />
        </div>

        {xato && <div className="xato-xabar">{xato}</div>}

        <div style={{ display: "grid", gap: 16 }}>
          {test.qismlar.map((q) => {
            const h = qismHolat[q.id];
            return (
              <div key={q.id} style={{ border: "1px solid var(--chiziq)", borderRadius: 8, padding: 10 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
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
                  {h.savollar.map((s, si) => (
                    <SavolTahrirQatori
                      key={si}
                      savol={s}
                      oz={(yangi) => savolOz(q.id, si, yangi)}
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
  const [yangiPapka, setYangiPapka] = useState("");
  const [ochiqPapkalar, setOchiqPapkalar] = useState({});
  // AI generatsiya (2026-08-02, foydalanuvchi talabi) — faqat "AI
  // mashqlari" (manba="ai") sahifasida, faqat 4 haqiqiy bo'lim uchun
  // (Mock/Hammasi'da yo'q — qaysi turni yaratish noaniq bo'lardi).
  const [band, setBand] = useState(BAND_GURUHLAR[0]);
  const [generatsiyaBormoqda, setGeneratsiyaBormoqda] = useState(false);
  // "Hammasi" rejimida qaysi bo'lim hozir generatsiya qilinayotgani
  // (progress ko'rsatish uchun) — bitta bo'lim rejimida ishlatilmaydi.
  const [generatsiyaBolimi, setGeneratsiyaBolimi] = useState("");

  function yukla(bolim) {
    api(`/api/imtihon/testlar-boshqaruv/?manba=${manba}${bolim ? `&bolim=${bolim}` : ""}`)
      .then(setRoyxat)
      .catch(() => {});
    api(`/api/imtihon/papkalar/?manba=${manba}${bolim ? `&bolim=${bolim}` : ""}`)
      .then(setPapkalar)
      .catch(() => {});
  }

  useEffect(() => {
    yukla(filtrBolim);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtrBolim, manba]);

  async function papkaYarat() {
    const nomi = yangiPapka.trim();
    if (!nomi || !filtrBolim) return;
    try {
      await api("/api/imtihon/papkalar/", {
        method: "POST",
        body: { nomi, bolim: filtrBolim, manba },
      });
      setYangiPapka("");
      yukla(filtrBolim);
    } catch (e) {
      setJsonXato(e.data?.detail || t("xato_yuz_berdi"));
    }
  }

  async function papkaOchir(id) {
    if (!window.confirm(t("imtihon_papka_ochirish_tasdiq"))) return;
    try {
      await api(`/api/imtihon/papkalar/${id}/`, { method: "DELETE" });
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
      await api("/api/imtihon/mashq-generatsiya/", {
        method: "POST",
        body: { bolim: filtrBolim, band },
      });
      yukla(filtrBolim);
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

        {/* Papkalar (2026-08-01) — har bo'lim uchun alohida, shuning uchun
            "Hammasi" filtrida yaratib bo'lmaydi (qaysi bo'limga tegishli
            ekani noaniq bo'lardi). */}
        <div style={{ marginBottom: 14, padding: 10, background: "var(--sirt-2)", borderRadius: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <strong style={{ fontSize: 14 }}>{t("imtihon_papkalar")}</strong>
            {filtrBolim ? (
              <>
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
              </>
            ) : (
              <span className="izoh">{t("imtihon_papka_bolim_tanlang")}</span>
            )}
          </div>
          {papkalar.length > 0 && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
              {papkalar.map((p) => (
                <span
                  key={p.id}
                  style={{
                    display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 10px",
                    border: "1px solid var(--chiziq)", borderRadius: 20, background: "var(--sirt)",
                    fontSize: 13,
                  }}
                >
                  📁 {p.nomi}
                  <span className="izoh">
                    ({royxat?.filter((x) => x.papka === p.id).length || 0})
                  </span>
                  <button
                    type="button"
                    onClick={() => papkaOchir(p.id)}
                    title={t("ochirish")}
                    style={{
                      border: "none", background: "none", color: "#d33", cursor: "pointer",
                      fontSize: 15, lineHeight: 1, padding: 0,
                    }}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {!royxat ? (
          <div className="yuklanmoqda">{t("yuklanmoqda")}</div>
        ) : royxat.length === 0 ? (
          <span className="izoh">{t("imtihon_royxat_boshi")}</span>
        ) : (
          <div style={{ display: "grid", gap: 8 }}>
            {/* Papkalar bo'yicha guruhlangan (2026-08-01) — talaba
                tomonidagi ro'yxat bilan bir xil accordion ko'rinish.
                Papkasiz testlar ro'yxat oxirida, tekis. */}
            {papkalar
              .filter((p) => royxat.some((r) => r.papka === p.id))
              .map((p) => (
                <div key={p.id} style={{ border: "1px solid var(--chiziq)", borderRadius: 8, overflow: "hidden" }}>
                  <div
                    className="imtihon-papka-sarlavha"
                    style={{ padding: "8px 10px" }}
                    onClick={() => setOchiqPapkalar((v) => ({ ...v, [p.id]: !v[p.id] }))}
                  >
                    <span>{ochiqPapkalar[p.id] ? "▾" : "▸"} 📁 {p.nomi}</span>
                    <span className="izoh">{royxat.filter((r) => r.papka === p.id).length}</span>
                  </div>
                  {ochiqPapkalar[p.id] && (
                    <div style={{ display: "grid", gap: 8, padding: "0 8px 8px" }}>
                      {royxat.filter((r) => r.papka === p.id).map((test) => testKartasi(test))}
                    </div>
                  )}
                </div>
              ))}
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
        onSaqlandi={() => {
          yukla(filtrBolim);
          setTolaOchilgan(null);
        }}
      />
    )}
    </>
  );

  function testKartasi(test) {
    return (
              <div key={test.id} style={{ padding: 8, border: "1px solid var(--chiziq)", borderRadius: 8 }}>
                <div className="davomat-qator" style={{ borderBottom: "none", padding: 0 }}>
                  <span>
                    <strong
                      style={{ cursor: "pointer", textDecoration: "underline dotted" }}
                      title={t("imtihon_tola_ochish")}
                      onClick={() => setTolaOchilgan(test)}
                    >
                      {test.name}
                    </strong>{" "}
                    <span className="izoh">
                      {t(`mashq_bolim_${test.bolim}`)} · {test.qismlar.length} {t("imtihon_qism_soni")}
                      {" · "}
                      {test.yaratuvchi || t("imtihon_yaratuvchi_nomalum")}
                      {" · "}
                      {new Date(test.created_at).toLocaleString()}
                    </span>
                  </span>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    {/* Papkaga ko'chirish — faqat shu testning bo'limiga
                        tegishli papkalar ko'rsatiladi (backend ham
                        boshqa bo'lim papkasini rad qiladi). */}
                    {papkalar.some((p) => p.bolim === test.bolim) && (
                      <select
                        value={test.papka || ""}
                        onChange={(e) => papkagaKochir(test.id, e.target.value)}
                        title={t("imtihon_papkaga_kochir")}
                        style={{ maxWidth: 170 }}
                      >
                        <option value="">{t("imtihon_papkasiz")}</option>
                        {papkalar
                          .filter((p) => p.bolim === test.bolim)
                          .map((p) => (
                            <option key={p.id} value={p.id}>📁 {p.nomi}</option>
                          ))}
                      </select>
                    )}
                    <button
                      className="tugma ikkinchi"
                      onClick={() => {
                        setTahrirlanayotgan((v) => (v === test.id ? null : test.id));
                        setNomiTahrirlash(test.name);
                      }}
                    >
                      {tahrirlanayotgan === test.id ? t("yopish") : t("tahrirlash")}
                    </button>
                    <button className="tugma ikkinchi" style={{ color: "#d33" }} onClick={() => ochir(test.id)}>
                      {t("ochirish")}
                    </button>
                  </div>
                </div>
                {tahrirlanayotgan === test.id && (
                  <>
                    <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 8 }}>
                      <input
                        value={nomiTahrirlash}
                        onChange={(e) => setNomiTahrirlash(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && nominiSaqla(test.id)}
                        style={{ maxWidth: 320 }}
                      />
                      <button
                        type="button"
                        className="tugma"
                        onClick={() => nominiSaqla(test.id)}
                        disabled={!nomiTahrirlash.trim() || nomiTahrirlash.trim() === test.name}
                      >
                        {t("saqlash")}
                      </button>
                    </div>
                    {test.bolim === "listening" && (
                      <div style={{ marginTop: 8, display: "grid", gap: 6 }}>
                        {test.qismlar.some((q) => !q.audio_url) && (
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span className="izoh" style={{ minWidth: 90 }}>{t("imtihon_audio_hammasiga")}</span>
                            <input
                              type="file"
                              accept="audio/*"
                              title={t("imtihon_audio_hammasiga_izoh")}
                              style={{ maxWidth: 160 }}
                              onChange={(e) => hammasigaAudioBiriktir(test, e.target.files[0])}
                            />
                          </div>
                        )}
                        {test.qismlar.map((q) => (
                          <div key={q.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span className="izoh" style={{ minWidth: 90 }}>{q.sarlavha || `#${q.tartib}`}</span>
                            {q.audio_url ? (
                              <span className="izoh">🎧</span>
                            ) : (
                              <>
                                <span className="izoh">{t("imtihon_audio_yoq")}</span>
                                <input
                                  type="file"
                                  accept="audio/*"
                                  title={t("imtihon_audio_biriktir")}
                                  style={{ maxWidth: 160 }}
                                  onChange={(e) => audioBiriktir(q.id, e.target.files[0])}
                                />
                              </>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    <div style={{ marginTop: 8, display: "grid", gap: 6 }}>
                      {test.qismlar.map((q) => (
                        <div key={q.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span className="izoh" style={{ minWidth: 90 }}>{q.sarlavha || `#${q.tartib}`}</span>
                          {q.rasm_url ? (
                            <span className="izoh">🖼️</span>
                          ) : (
                            <>
                              <span className="izoh">{t("imtihon_rasm_yoq")}</span>
                              <input
                                type="file"
                                accept="image/*"
                                title={t("imtihon_rasm_biriktir")}
                                style={{ maxWidth: 160 }}
                                onChange={(e) => rasmBiriktir(q.id, e.target.files[0])}
                              />
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
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
