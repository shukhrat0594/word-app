import { useEffect, useState } from "react";
import { api, apiBlobUrl, apiForm } from "../api";
import {
  FlashcardOyini,
  JuftiniTopOyini,
  SpeedQuizOyini,
  UnscrambleOyini,
} from "../components/SozOyinlari";
import { useI18n } from "../i18n";
import { IMLO_OFF } from "../imlo";
import { useProfil } from "../profilContext";

// 2026-07-27: admin darslikdagi rasmli mashqni qo'lda JSON'ga o'girish
// o'rniga, shu promtni ChatGPT/Claude/Gemini kabi AI'ga (skrinshot bilan
// birga) beradi — AI "pozitsiya" koordinatalarini rasmning o'zidan
// aniqlab, tayyor JSON qaytaradi. Bu — FLAT (Unit'siz) bo'limlar uchun
// (masalan Elementary...Upper-Intermediate, IELTS Textbooks qismlari) —
// bitta bo'lim, bitta mashq to'plami. Beginner Unit'lari uchun esa
// UCHTA bo'lim (Mashqlar+Grammar reference+Wordlist) bitta so'rovda
// yuklanadi — pastdagi `AI_PROMT_UNIT`ga qarang.
const AI_PROMT = `Men senga o'quv darsligi (masalan Headway) sahifasidan bitta mashqning skrinshotini va/yoki matnini beraman. Sen shu materialni quyidagi JSON formatiga o'girib ber — natija FAQAT valid JSON MASSIV bo'lsin (kvadrat qavs bilan boshlanib tugasin), hech qanday izoh, sarlavha yoki markdown belgisi (masalan \`\`\`json) qo'shma, faqat sof JSON matni qaytar.

Format — massiv ichida har bir mashq shu ko'rinishda:
[
  {
    "matn": "Mashq topshirig'i/sarlavhasi (ixtiyoriy, bo'lmasa bo'sh qoldir)",
    "savollar": [
      {
        "savol": "Savol yoki band nomi",
        "variantlar": ["variant1", "variant2"] (ixtiyoriy — ochiq javobli bo'lsa bo'sh massiv []),
        "togri": "To'g'ri javob (yoki bir nechta qabul qilinadigan javob bo'lsa massiv, masalan [\\"3\\", \\"three\\"])",
        "pozitsiya": {"x": 0-100, "y": 0-100} (ixtiyoriy — FAQAT sizga rasm (skrinshot) ilova qilingan bo'lsa va shu savolning bo'sh joyi/raqami rasmda aniq ko'rinib tursa qo'sh: rasmning chap-yuqori burchagidan boshlab, bo'sh joy markazining rasm eniga nisbatan foizini "x", bo'yiga nisbatan foizini "y" qilib yoz. Rasm berilmagan yoki savol oddiy matn ro'yxati bo'lsa (rasmga bog'liq bo'lmagan) — bu maydonni umuman yozma)
      }
    ]
  }
]

Qoidalar:
- Agar sizga rasm (skrinshot) berilgan bo'lsa va mashqda bir nechta bo'sh joy/raqamlangan band rasmning turli nuqtalarida bo'lsa — HAR BIRIGA "pozitsiya" qo'shing, shunda talaba javobni rasmning aynan o'sha nuqtasida yoza oladi (masalan "rasmdagi narsalarni sanab yoz" turidagi mashqlar)
- Agar mashq oddiy savol-javob ro'yxati bo'lsa (rasmga bog'liq bo'lmagan matn/gap to'ldirish) — "pozitsiya"ni umuman yozmang, savol oddiy ro'yxatda chiqadi
- Bir nechta mashq bo'lsa, massivga har birini alohida obyekt qilib qo'shing (bitta mashq bo'lsa ham, bitta elementli massiv qaytaring — obyektning o'zini emas)
- "rasm" va "audio" maydonlarini HECH QACHON JSON'ga qo'shmang — ular saytda alohida (fayl sifatida, mashq yaratilgandan keyin) biriktiriladi, siz (AI) haqiqiy fayl yarata olmaysiz

Natijani shu JSON massiv ko'rinishida qaytar, boshqa hech narsa yozma. Quyida mashq materiali (matn va/yoki tasvirlangan rasm):

[BU YERGA MASHQ MATNINI JOYLASHTIRING YOKI SKRINSHOTNI ILOVA QILING]`;

// 2026-07-27 (2-marta): Beginner Unit'lari uchun BITTA promt — mashqlar va
// Vocabulary (Grammar reference + Wordlist BIR sahifada, birlashtirilgan)
// BIR YO'LA generatsiya qilinadi, chunki yuklash ham Unit darajasida
// BITTA tugma bilan bo'ladi (foydalanuvchi talabi). ESKAT: eng qulay yo'l
// — "ZIP orqali yuklash" (pastda, avtomatik, Answer key'ni ham hisobga
// oladi) — bu qo'lda-JSON promti FAQAT zaxira/qo'shimcha kiritish uchun.
const AI_PROMT_UNIT = `Men senga o'quv darsligi (masalan Headway) darsligidan BITTA Unit materialini beraman — mashqlar (skrinshot va/yoki matn) va Vocabulary (Grammar reference + Wordlist, darslikda BIR sahifada birga keladi) sahifalari, alohida-alohida yoki birga bo'lishi mumkin. Sen shu materialni quyidagi JSON formatiga o'girib ber — natija FAQAT valid JSON OBYEKT bo'lsin (jingalak qavs bilan boshlanib tugasin), hech qanday izoh, sarlavha yoki markdown belgisi (masalan \`\`\`json) qo'shma, faqat sof JSON matni qaytar.

Format:
{
  "mashqlar": [
    {
      "matn": "Mashq topshirig'i/sarlavhasi (ixtiyoriy, bo'lmasa bo'sh qoldir)",
      "savollar": [
        {
          "savol": "Savol yoki band nomi",
          "variantlar": ["variant1", "variant2"] (ixtiyoriy — ochiq javobli bo'lsa bo'sh massiv []),
          "togri": "To'g'ri javob (yoki bir nechta qabul qilinadigan javob bo'lsa massiv, masalan [\\"3\\", \\"three\\"])",
          "pozitsiya": {"x": 0-100, "y": 0-100} (ixtiyoriy — FAQAT sizga rasm (skrinshot) ilova qilingan bo'lsa va shu savolning bo'sh joyi/raqami rasmda aniq ko'rinib tursa qo'sh: rasmning chap-yuqori burchagidan boshlab, bo'sh joy markazining rasm eniga nisbatan foizini "x", bo'yiga nisbatan foizini "y" qilib yoz — piksel EMAS, foiz. Rasm berilmagan yoki savol oddiy matn ro'yxati bo'lsa — bu maydonni umuman yozma)
        }
      ]
    }
  ],
  "vocabulary_matn": "Ushbu Unit'da o'rgatiladigan grammatika mavzusining qisqa, tushunarli xulosasi (bir necha jumla, kerak bo'lsa 1-2 misol bilan)",
  "wordlist": [
    {"en": "so'z", "uz": "tarjimasi", "turkum": "so'z turkumi (ixtiyoriy, masalan 'ot', 'fe'l')", "misol": "ingliz tilida namuna gap (ixtiyoriy)"}
  ]
}

Qoidalar:
- "mashqlar": agar sizga rasm (skrinshot) berilgan bo'lsa va mashqda bir nechta bo'sh joy/raqamlangan band rasmning turli nuqtalarida bo'lsa — HAR BIRIGA "pozitsiya" qo'shing. Oddiy savol-javob ro'yxati bo'lsa (rasmga bog'liq bo'lmagan) — "pozitsiya"ni umuman yozmang.
- "vocabulary_matn": agar sizga Unit oxiridagi grammatika xulosa beti berilgan bo'lsa, uni qisqa va tushunarli qilib qayta yozing (so'zma-so'z ko'chirish shart emas, mazmunini saqlab qisqartiring). Berilmagan bo'lsa, shu Unit'da o'rgatilayotgan asosiy grammatik qoidani o'zingiz bir necha jumlada tushuntiring.
- "wordlist": sizga berilgan materialda Unit oxiridagi so'zlar ro'yxati (Word list) bo'lsa, HAMMASINI shu ko'rinishda kiriting, bittasini ham tashlab ketmang.
- Agar sizga faqat BITTA qismga oid material berilgan bo'lsa (masalan faqat mashqlar, Vocabulary/Wordlist YO'Q) — natijada FAQAT shu maydonni yozing, boshqalarini JSON'ga umuman qo'shmang (bo'sh massiv/matn ham yozmang, maydonning o'zini tashlab ketasiz)
- "rasm" va "audio" maydonlarini HECH QACHON JSON'ga qo'shmang — ular saytda alohida (fayl sifatida, mashq yaratilgandan keyin) biriktiriladi, siz (AI) haqiqiy fayl yarata olmaysiz

Natijani shu JSON obyekt ko'rinishida qaytar, boshqa hech narsa yozma. Quyida Unit materiali (matn va/yoki tasvirlangan rasmlar):

[BU YERGA UNIT MATERIALINI JOYLASHTIRING YOKI SKRINSHOTLARNI ILOVA QILING]`;

/** Rasm ustiga to'g'ridan-to'g'ri joylashtiriladigan savollar (masalan
 * "nechta narsa bor?" turidagi mashqlar) — savolda "pozitsiya":
 * {"x": 0-100, "y": 0-100} bo'lsa, oddiy ro'yxatda emas, aynan shu nuqtada
 * kichik input sifatida ko'rsatiladi (2026-07-27).
 *
 * IELTS testlaridagi (`ImtihonOtish.jsx: RasmSavollari`) bilan bir xil
 * mexanizm va bir xil CSS klassi (`imtihon-rasm-input`) — nomi "imtihon"
 * bo'lsa ham, klass sof vizual (pozitsiyalangan input), imtihonga xos
 * mantiq yo'q, shuning uchun bu yerda ham xavfsiz qayta ishlatiladi. */
function RasmMashqi({ rasmUrl, savollar, idxlar, javoblar, javobniQoy, natija }) {
  return (
    <div style={{ position: "relative", display: "inline-block", maxWidth: "100%", marginBottom: 8 }}>
      <img src={rasmUrl} alt="" style={{ maxWidth: "100%", display: "block" }} />
      {savollar.map((s, k) => {
        const i = idxlar[k];
        const holat = natija ? (natija.natijalar[i] ? "togri" : "notogri") : "";
        return (
          <input
            key={i}
            {...IMLO_OFF}
            className={`imtihon-rasm-input ${holat}`}
            style={{ left: `${s.pozitsiya.x}%`, top: `${s.pozitsiya.y}%` }}
            disabled={!!natija}
            value={javoblar[i] || ""}
            onChange={(e) => javobniQoy(i, e.target.value)}
            placeholder={`${i + 1}`}
          />
        );
      })}
    </div>
  );
}

/** Talaba uchun — bitta mashqqa javob yozish va natija ko'rish.
 * `raqam` (2026-07-27) — "raqamlangan mashqlar" talabi bo'yicha har bir
 * mashq tartib raqami bilan ko'rsatiladi. */
function TalabaMashqi({ mashq, raqam }) {
  const { t } = useI18n();
  const [javoblar, setJavoblar] = useState(mashq.savollar.map(() => ""));
  const [natija, setNatija] = useState(null);
  const [rasmUrl, setRasmUrl] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [audioUrllar, setAudioUrllar] = useState([]);
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [xato, setXato] = useState("");

  useEffect(() => {
    if (mashq.rasm_url) {
      apiBlobUrl(mashq.rasm_url).then(setRasmUrl).catch(() => {});
    }
  }, [mashq.rasm_url]);

  useEffect(() => {
    if (mashq.audio_url) {
      apiBlobUrl(mashq.audio_url).then(setAudioUrl).catch(() => {});
    }
  }, [mashq.audio_url]);

  // Bitta mashqqa BIR NECHTA audio biriktirilgan bo'lishi mumkin
  // (2026-07-27, foydalanuvchi talabi — bitta sahifada bir nechta
  // Listening bandi bo'lsa, hammasi yon panelda ro'yxat, talaba
  // keraklisini play qiladi).
  useEffect(() => {
    if (!mashq.audiolar || mashq.audiolar.length === 0) return;
    Promise.all(mashq.audiolar.map((a) => apiBlobUrl(a.url).then((url) => ({ ...a, url }))))
      .then(setAudioUrllar)
      .catch(() => {});
  }, [mashq.audiolar]);

  function javobniQoy(idx, qiymat) {
    setJavoblar((j) => j.map((x, i) => (i === idx ? qiymat : x)));
  }

  async function tekshir() {
    setXato("");
    setYuklanmoqda(true);
    try {
      const res = await api(`/api/kurslar/mashq/${mashq.id}/yechish/`, {
        method: "POST",
        body: { javoblar },
      });
      setNatija(res);
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  // Rasm ustida ko'rsatiladigan savollar ("pozitsiya" bor) va qolgan
  // oddiy savollar alohida ajratiladi — asl indeksi (javoblar massividagi
  // o'rni) saqlanib qoladi.
  const rasmIdxlari = [];
  const rasmSavollari = [];
  const oddiySavollar = [];
  mashq.savollar.forEach((s, i) => {
    if (s.pozitsiya && rasmUrl) {
      rasmIdxlari.push(i);
      rasmSavollari.push(s);
    } else {
      oddiySavollar.push([s, i]);
    }
  });

  return (
    <div style={{ border: "1px solid var(--chiziq)", borderRadius: 8, padding: 10, marginBottom: 8 }}>
      {raqam != null && (
        <div style={{ fontWeight: 700, marginBottom: 6 }}>
          {t("kurs_mashq")} {raqam}
        </div>
      )}
      {mashq.matn && <div style={{ marginBottom: 8 }}>{mashq.matn}</div>}
      {rasmSavollari.length > 0 ? (
        <RasmMashqi
          rasmUrl={rasmUrl}
          savollar={rasmSavollari}
          idxlar={rasmIdxlari}
          javoblar={javoblar}
          javobniQoy={javobniQoy}
          natija={natija}
        />
      ) : (
        rasmUrl && <img src={rasmUrl} alt="" style={{ maxWidth: "100%", marginBottom: 8 }} />
      )}
      {audioUrl && <audio controls src={audioUrl} style={{ width: "100%", marginBottom: 8 }} />}
      {audioUrllar.length > 0 && (
        <div style={{ display: "grid", gap: 6, marginBottom: 8, padding: 8, background: "var(--sirt-2)", borderRadius: 6 }}>
          <span className="izoh">{t("kurs_audiolar_royxati")}</span>
          {audioUrllar.map((a) => (
            <div key={a.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {a.raqam && <span className="izoh" style={{ minWidth: 44 }}>{a.raqam}</span>}
              <audio controls src={a.url} style={{ width: "100%" }} />
            </div>
          ))}
        </div>
      )}
      {oddiySavollar.map(([s, i]) => (
        <div key={i} style={{ marginBottom: 6 }}>
          <div className="izoh">{s.savol}</div>
          {s.variantlar && s.variantlar.length > 0 ? (
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              {s.variantlar.map((v) => (
                <label key={v} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <input
                    type="radio"
                    name={`mashq-${mashq.id}-${i}`}
                    checked={javoblar[i] === v}
                    disabled={!!natija}
                    onChange={() => javobniQoy(i, v)}
                  />
                  {v}
                </label>
              ))}
            </div>
          ) : (
            <input
              {...IMLO_OFF}
              value={javoblar[i]}
              disabled={!!natija}
              onChange={(e) => javobniQoy(i, e.target.value)}
              style={{ maxWidth: 260 }}
            />
          )}
          {natija && (
            <span style={{ marginLeft: 8 }}>{natija.natijalar[i] ? "✓" : "✗"}</span>
          )}
        </div>
      ))}
      {!natija ? (
        <button className="tugma ikkinchi" onClick={tekshir} disabled={yuklanmoqda}>
          {yuklanmoqda ? t("tekshirilmoqda") : t("tekshirish")}
        </button>
      ) : (
        <div className="izoh">
          {t("band_ball")}: {natija.ball}/{natija.jami}
        </div>
      )}
      {xato && <div className="xato-xabar">{xato}</div>}
    </div>
  );
}

/** Admin/owner uchun — bitta tugunning mashqlarini boshqarish (ro'yxat,
 * o'chirish, rasm/audio biriktirish). `jsonKiritishKorinadi=false`
 * (2026-07-27) — Beginner Unit'lari ichidagi "Mashqlar" bo'limida JSON
 * orqali qo'shish endi Unit darajasida (AdminUnitKiritish) bo'ladi, bu
 * yerda faqat ro'yxat+fayl biriktirish qoladi. Boshqa (flat) bo'limlar
 * uchun avvalgidek JSON+AI promt ko'rinadi. */
function AdminMashqBoshqaruv({ tugunId, jsonKiritishKorinadi = true }) {
  const { t } = useI18n();
  const [royxat, setRoyxat] = useState(null);
  const [jsonMatn, setJsonMatn] = useState('[\n  {"matn": "", "savollar": [{"savol": "...", "togri": "..."}]}\n]');
  const [xato, setXato] = useState("");
  const [saqlanmoqda, setSaqlanmoqda] = useState(false);
  const [audioZipXato, setAudioZipXato] = useState("");
  const [audioZipYuklanmoqda, setAudioZipYuklanmoqda] = useState(false);
  const [promtKorinadi, setPromtKorinadi] = useState(false);
  const [nusxalandi, setNusxalandi] = useState(false);

  function promtNusxala() {
    navigator.clipboard?.writeText(AI_PROMT).then(() => {
      setNusxalandi(true);
      setTimeout(() => setNusxalandi(false), 2000);
    });
  }

  function yukla() {
    api(`/api/kurslar/${tugunId}/mashq-boshqaruv/`).then(setRoyxat).catch(() => {});
  }

  useEffect(() => {
    yukla();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tugunId]);

  async function qoshish() {
    setXato("");
    let mashqlar;
    try {
      mashqlar = JSON.parse(jsonMatn);
    } catch {
      setXato(t("kurs_json_xato"));
      return;
    }
    setSaqlanmoqda(true);
    try {
      await api(`/api/kurslar/${tugunId}/mashq-boshqaruv/`, { method: "POST", body: { mashqlar } });
      yukla();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setSaqlanmoqda(false);
    }
  }

  async function ochir(id) {
    if (!window.confirm(t("kurs_mashq_ochirish_tasdiq"))) return;
    await api(`/api/kurslar/mashq/${id}/`, { method: "DELETE" }).catch(() => {});
    yukla();
  }

  async function rasmYukla(id, e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    const fd = new FormData();
    fd.append("rasm", fayl);
    await apiForm(`/api/kurslar/mashq/${id}/rasm-boshqaruv/`, { method: "PATCH", formData: fd }).catch(() => {});
    yukla();
  }

  async function audioZipYukla(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setAudioZipXato("");
    setAudioZipYuklanmoqda(true);
    try {
      const fd = new FormData();
      fd.append("zip_fayl", fayl);
      await apiForm(`/api/kurslar/${tugunId}/audio-zip/`, { method: "POST", formData: fd });
      yukla();
    } catch (e2) {
      setAudioZipXato(e2.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setAudioZipYuklanmoqda(false);
    }
  }

  return (
    <div>
      {royxat && royxat.length > 0 && (
        <div style={{ display: "grid", gap: 6, marginBottom: 10 }}>
          {royxat.map((m) => (
            <div key={m.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="izoh">
                #{m.tartib} — {m.matn ? m.matn.slice(0, 40) : ""} ({m.savollar.length} {t("kurs_savol")})
                {m.rasm_url ? " 🖼️" : ""}
                {m.audio_url ? " 🔊" : ""}
                {m.audiolar?.length ? ` 🔊×${m.audiolar.length}` : ""}
              </span>
              <input type="file" accept="image/*" onChange={(e) => rasmYukla(m.id, e)} style={{ maxWidth: 140 }} />
              <button className="tugma ikkinchi" style={{ color: "#d33" }} onClick={() => ochir(m.id)}>
                {t("ochirish")}
              </button>
            </div>
          ))}
        </div>
      )}
      {royxat && royxat.length > 0 && (
        <div style={{ marginBottom: 10 }}>
          <label className="izoh" style={{ display: "block", marginBottom: 4 }}>
            {t("kurs_audio_zip_yuklash")}
          </label>
          <input type="file" accept=".zip" onChange={audioZipYukla} disabled={audioZipYuklanmoqda} />
          {audioZipXato && <span className="xato-xabar" style={{ marginLeft: 8 }}>{audioZipXato}</span>}
        </div>
      )}
      {!jsonKiritishKorinadi ? (
        (!royxat || royxat.length === 0) && <div className="izoh">{t("kurs_mashq_yoq")}</div>
      ) : (
        <>
          <div style={{ marginBottom: 8 }}>
            <button className="tugma ikkinchi" onClick={() => setPromtKorinadi((v) => !v)}>
              {promtKorinadi ? t("mashq_promt_yashirish") : t("mashq_promt_korsatish")}
            </button>
            {promtKorinadi && (
              <div style={{ marginTop: 8 }}>
                <p className="izoh" style={{ marginTop: 0 }}>{t("kurs_mashq_promt_izoh")}</p>
                <textarea
                  readOnly
                  rows={8}
                  value={AI_PROMT}
                  style={{ width: "100%", fontFamily: "monospace", fontSize: 11 }}
                />
                <button className="tugma ikkinchi" style={{ marginTop: 6 }} onClick={promtNusxala}>
                  {nusxalandi ? t("nusxalandi") : t("nusxalash")}
                </button>
              </div>
            )}
          </div>
          <textarea
            rows={6}
            value={jsonMatn}
            onChange={(e) => setJsonMatn(e.target.value)}
            style={{ width: "100%", fontFamily: "monospace", fontSize: 12 }}
          />
          <div style={{ marginTop: 6 }}>
            <button className="tugma ikkinchi" onClick={qoshish} disabled={saqlanmoqda}>
              {t("kurs_mashq_qoshish")}
            </button>
            {xato && <span className="xato-xabar" style={{ marginLeft: 8 }}>{xato}</span>}
          </div>
        </>
      )}
    </div>
  );
}

/** Mashqlar paneli — talaba uchun yechish, admin uchun boshqarish. */
function MashqPaneli({ tugunId, talabaMi, jsonKiritishKorinadi = true }) {
  const { t } = useI18n();
  const [mashqlar, setMashqlar] = useState(null);
  const [xato, setXato] = useState("");

  useEffect(() => {
    if (!talabaMi) return;
    api(`/api/kurslar/${tugunId}/mashqlar/`)
      .then(setMashqlar)
      .catch((e) => setXato(e.data?.detail || t("xato_yuz_berdi")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tugunId, talabaMi]);

  if (!talabaMi) {
    return <AdminMashqBoshqaruv tugunId={tugunId} jsonKiritishKorinadi={jsonKiritishKorinadi} />;
  }

  if (xato) return <div className="xato-xabar">{xato}</div>;
  if (!mashqlar) return <div className="izoh">{t("yuklanmoqda")}</div>;
  if (mashqlar.length === 0) return <div className="izoh">{t("kurs_mashq_yoq")}</div>;

  return (
    <div>
      {mashqlar.map((m, idx) => (
        <TalabaMashqi key={m.id} mashq={m} raqam={idx + 1} />
      ))}
    </div>
  );
}

/** So'zlarni tarjima kiritib mashq qilish (2026-07-27, foydalanuvchi
 * talabi — "kitobdagidek" so'z ro'parasida javob yozadigan joy bo'lsin).
 * Tekshirish MIJOZ tomonida (backend so'rovi shart emas) — chunki `uz`
 * tarjimasi allaqachon `/sozlar/` javobida keladi (o'yinlar ham xuddi
 * shu ma'lumotdan foydalanadi), shuning uchun bu yerda yashirishning
 * ma'nosi yo'q. */
function SozlarniYozishMashqi({ sozlar }) {
  const { t } = useI18n();
  const [javoblar, setJavoblar] = useState(() => sozlar.map(() => ""));
  const [tekshirilganmi, setTekshirilganmi] = useState(false);

  function javobniQoy(i, qiymat) {
    setJavoblar((j) => j.map((x, idx) => (idx === i ? qiymat : x)));
  }

  function togriMi(i) {
    return javoblar[i].trim().toLowerCase() === sozlar[i].uz.trim().toLowerCase();
  }

  return (
    <div style={{ display: "grid", gap: 6, marginBottom: 14, maxWidth: 420 }}>
      {sozlar.map((s, i) => (
        <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontWeight: 600, minWidth: 100 }}>{s.en}</span>
          <input
            {...IMLO_OFF}
            value={javoblar[i]}
            disabled={tekshirilganmi}
            onChange={(e) => javobniQoy(i, e.target.value)}
            style={{ flex: 1 }}
          />
          {tekshirilganmi && (
            <span style={togriMi(i) ? { color: "var(--yaxshi)" } : { color: "var(--xato)" }}>
              {togriMi(i) ? "✓" : `✗ ${s.uz}`}
            </span>
          )}
        </div>
      ))}
      <button className="tugma ikkinchi" onClick={() => setTekshirilganmi(true)} disabled={tekshirilganmi}>
        {t("tekshirish")}
      </button>
    </div>
  );
}

/** "Vocabulary" bo'limi ko'rinishi (2026-07-27, ikkinchi marta qayta
 * ishlab chiqildi) — Grammar reference + Wordlist BIRLASHTIRILGAN
 * (darslikda BIR sahifada birga keladi): grammatika qisqa xulosasi
 * (bo'lsa) + so'zlarni tarjima yozib mashq qilish + O'yinlar bo'limidagi
 * 4 ta so'z o'yini, FAQAT shu Unit so'zlari bilan. Grammatika testi bu
 * yerga kirmaydi — u gap-asosidagi savollarga ishlaydi, so'z juftlariga
 * bog'liq emas. */
function VocabularyKorinishi({ tugunId, matn }) {
  const { t } = useI18n();
  const [sozlar, setSozlar] = useState(null);
  const [oyin, setOyin] = useState(null);
  const [oyinKey, setOyinKey] = useState(0);

  useEffect(() => {
    api(`/api/kurslar/${tugunId}/sozlar/`).then(setSozlar).catch(() => setSozlar([]));
  }, [tugunId]);

  if (!sozlar) return <div className="izoh">{t("yuklanmoqda")}</div>;

  if (oyin) {
    // `key={oyinKey}` — "qayta o'ynash" bosilganda komponent qayta
    // MOUNT bo'lib, ichki holat (ball, joriy savol) toza boshlanadi;
    // Oyinlar.jsx'da bu API'dan yangi tasodifiy so'zlar olib erishilardi,
    // bu yerda so'zlar ro'yxati Unit bo'yicha FIKS, shuning uchun shart emas.
    const qaytaOynash = () => setOyinKey((k) => k + 1);
    const orqaga = () => setOyin(null);
    const Komponent = {
      juftini_top: JuftiniTopOyini,
      flashcard: FlashcardOyini,
      speed_quiz: SpeedQuizOyini,
      unscramble: UnscrambleOyini,
    }[oyin];
    return (
      <Komponent
        key={oyinKey}
        sozlar={sozlar}
        t={t}
        onQaytaOynash={qaytaOynash}
        onBoshqaDaraja={orqaga}
      />
    );
  }

  return (
    <div>
      {matn && (
        <div className="mashq-passage" style={{ whiteSpace: "pre-wrap", marginBottom: 12 }}>
          {matn}
        </div>
      )}
      {sozlar.length === 0 ? (
        <div className="izoh">{t("kurs_wordlist_yoq")}</div>
      ) : (
        <>
          <SozlarniYozishMashqi sozlar={sozlar} />
          <div className="tanlov-royxat">
            <button className="tanlov-tugma" onClick={() => setOyin("juftini_top")}>
              {t("juftini_top")}
            </button>
            <button className="tanlov-tugma" onClick={() => setOyin("flashcard")}>
              {t("flashcard_oyin")}
            </button>
            <button className="tanlov-tugma" onClick={() => setOyin("speed_quiz")}>
              {t("speed_quiz_oyin")}
            </button>
            <button className="tanlov-tugma" onClick={() => setOyin("unscramble")}>
              {t("unscramble_oyin")}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

/** Admin/owner uchun — bitta Unit'ning IKKALA bo'limini (Mashqlar,
 * Vocabulary) BITTA harakatda yuklash (2026-07-27, foydalanuvchi talabi —
 * "unit uchun bitta tugma bo'lsin"). */
function AdminUnitKiritish({ unitId, royxatniYangila }) {
  const { t } = useI18n();
  const [ochiq, setOchiq] = useState(false);
  const [promtKorinadi, setPromtKorinadi] = useState(false);
  const [nusxalandi, setNusxalandi] = useState(false);
  const [jsonMatn, setJsonMatn] = useState(
    '{\n  "mashqlar": [],\n  "vocabulary_matn": "",\n  "wordlist": []\n}'
  );
  const [xato, setXato] = useState("");
  const [xabar, setXabar] = useState("");
  const [saqlanmoqda, setSaqlanmoqda] = useState(false);
  const [zipXato, setZipXato] = useState("");
  const [zipXabar, setZipXabar] = useState("");
  const [zipYuklanmoqda, setZipYuklanmoqda] = useState(false);

  function promtNusxala() {
    navigator.clipboard?.writeText(AI_PROMT_UNIT).then(() => {
      setNusxalandi(true);
      setTimeout(() => setNusxalandi(false), 2000);
    });
  }

  async function yuklash() {
    setXato("");
    setXabar("");
    let tana;
    try {
      tana = JSON.parse(jsonMatn);
    } catch {
      setXato(t("kurs_json_xato"));
      return;
    }
    setSaqlanmoqda(true);
    try {
      const res = await api(`/api/kurslar/${unitId}/unit-yuklash/`, { method: "POST", body: tana });
      const qismlar = [];
      if (res.mashqlar_soni) qismlar.push(`${res.mashqlar_soni} ${t("kurs_natija_mashq")}`);
      if (res.wordlist_soni) qismlar.push(`${res.wordlist_soni} ${t("kurs_natija_soz")}`);
      if (res.vocabulary_matn_qoshildi) qismlar.push(t("kurs_natija_grammar"));
      setXabar(qismlar.join(", "));
      royxatniYangila();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setSaqlanmoqda(false);
    }
  }

  async function zipYukla(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setZipXato("");
    setZipXabar("");
    setZipYuklanmoqda(true);
    try {
      const fd = new FormData();
      fd.append("zip_fayl", fayl);
      const res = await apiForm(`/api/kurslar/${unitId}/zip-yuklash/`, { method: "POST", formData: fd });
      const qismlar = [
        `${res.muvaffaqiyatli_sahifalar}/${res.jami_sahifa} ${t("kurs_zip_sahifa")}`,
        `${res.yaratilgan_mashqlar} ${t("kurs_natija_mashq")}`,
      ];
      if (res.wordlist_soni) qismlar.push(`${res.wordlist_soni} ${t("kurs_natija_soz")}`);
      if (res.vocabulary_matn_qoshildi) qismlar.push(t("kurs_natija_grammar"));
      if (res.moslangan_audio_soni) qismlar.push(`${res.moslangan_audio_soni} ${t("kurs_zip_audio")}`);
      let xabarMatni = qismlar.join(", ");
      if (res.xato_sahifalar?.length) {
        xabarMatni += ` — ⚠ ${res.xato_sahifalar.length} ${t("kurs_zip_xato_sahifa")}: ${res.xato_sahifalar
          .map((x) => `#${x.sahifa}`)
          .join(", ")}`;
      }
      if (res.moslanmagan_audio?.length) {
        xabarMatni += ` — ⚠ ${t("kurs_zip_moslanmagan_audio")}: ${res.moslanmagan_audio.join(", ")}`;
      }
      setZipXabar(xabarMatni);
      royxatniYangila();
    } catch (e2) {
      setZipXato(e2.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setZipYuklanmoqda(false);
    }
  }

  return (
    <div style={{ marginTop: 4, marginBottom: 6 }} onClick={(e) => e.stopPropagation()}>
      <button className="tugma ikkinchi" onClick={() => setOchiq((v) => !v)}>
        {ochiq ? t("yopish") : t("kurs_unit_yuklash")}
      </button>
      {ochiq && (
        <div style={{ marginTop: 8, maxWidth: 640 }}>
          <div style={{ marginBottom: 10, paddingBottom: 10, borderBottom: "1px solid var(--chiziq)" }}>
            <label className="izoh" style={{ display: "block", marginBottom: 4 }}>
              {t("kurs_zip_yuklash_izoh")}
            </label>
            <input type="file" accept=".zip" onChange={zipYukla} disabled={zipYuklanmoqda} />
            {zipYuklanmoqda && <span className="izoh" style={{ marginLeft: 8 }}>{t("kurs_zip_ishlanmoqda")}</span>}
            {zipXato && <div className="xato-xabar" style={{ marginTop: 4 }}>{zipXato}</div>}
            {zipXabar && <div className="izoh" style={{ marginTop: 4 }}>✓ {zipXabar}</div>}
          </div>
          <button className="tugma ikkinchi" onClick={() => setPromtKorinadi((v) => !v)}>
            {promtKorinadi ? t("mashq_promt_yashirish") : t("mashq_promt_korsatish")}
          </button>
          {promtKorinadi && (
            <div style={{ marginTop: 8 }}>
              <p className="izoh" style={{ marginTop: 0 }}>{t("kurs_unit_promt_izoh")}</p>
              <textarea
                readOnly
                rows={8}
                value={AI_PROMT_UNIT}
                style={{ width: "100%", fontFamily: "monospace", fontSize: 11 }}
              />
              <button className="tugma ikkinchi" style={{ marginTop: 6 }} onClick={promtNusxala}>
                {nusxalandi ? t("nusxalandi") : t("nusxalash")}
              </button>
            </div>
          )}
          <textarea
            rows={8}
            value={jsonMatn}
            onChange={(e) => setJsonMatn(e.target.value)}
            style={{ width: "100%", fontFamily: "monospace", fontSize: 12, marginTop: 8 }}
          />
          <div style={{ marginTop: 6 }}>
            <button className="tugma ikkinchi" onClick={yuklash} disabled={saqlanmoqda}>
              {t("kurs_unit_yuklash_qil")}
            </button>
            {xato && <span className="xato-xabar" style={{ marginLeft: 8 }}>{xato}</span>}
            {xabar && <span className="izoh" style={{ marginLeft: 8 }}>✓ {xabar}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

/** Bitta tugun — akkordeon (agar children bo'lsa) yoki oxirgi qatlam
 * (fayl + mashqlar + tugallandimi belgisi + admin uchun boshqaruv).
 *
 * `ichkariUnitMi` (2026-07-27) — shu tugunning BEVOSITA ota-tuguni Unit
 * (`unit_darsi=True`) bo'lsa true. Shu bo'lsa, nomi bo'yicha ("Mashqlar" /
 * "Vocabulary") maxsus ko'rinish tanlanadi — boshqa (flat) bo'limlar
 * avvalgidek fayl+mashq ko'rinishida qoladi. */
function Tugun({ tugun, chuqurlik, adminMi, talabaMi, royxatniYangila, ichkariUnitMi, ochiqmi, onOchish }) {
  const { t } = useI18n();
  // Akkordeon (2026-07-27, foydalanuvchi talabi — "qolgan qismlar
  // halaqit qilyabdi") — shu tugunning FARZANDLARI orasida bir vaqtda
  // faqat BITTASI ochiq turadi: ID saqlanadi (`ochiqBolaId`), farzandning
  // o'zi ochiqligi esa OTA orqali (`ochiqmi`/`onOchish`) boshqariladi —
  // shu tugunning o'zi qanday ochilgani esa YUQORIDAGI ota tomonidan.
  const [ochiqBolaId, setOchiqBolaId] = useState(null);
  const [mashqOchiq, setMashqOchiq] = useState(false);
  const [faylXato, setFaylXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [tugallandimi, setTugallandimi] = useState(tugun.tugallandimi);

  const otstup = 14 + chuqurlik * 20;
  const unitBolimi = ichkariUnitMi ? tugun.nomi : null;

  if (tugun.tez_kunda) {
    return (
      <div
        className="kurs-qator"
        style={{ paddingLeft: otstup, display: "flex", alignItems: "center", gap: 8, opacity: 0.55 }}
      >
        <span>{tugun.ikonka}</span>
        <span>{tugun.nomi}</span>
        <span className="izoh">— {t("tez_orada")}</span>
      </div>
    );
  }

  if (tugun.qulflangan) {
    return (
      <div
        className="kurs-qator"
        style={{ paddingLeft: otstup, display: "flex", alignItems: "center", gap: 8, opacity: 0.5 }}
      >
        <span>🔒</span>
        <span>{tugun.nomi}</span>
        <span className="izoh">— {t("kurs_qulflangan")}</span>
      </div>
    );
  }

  if (tugun.oxirgi_qatlammi) {
    // ==== Beginner Unit'iga xos 2 bo'lim — maxsus ko'rinish ====
    if (unitBolimi === "Vocabulary") {
      return (
        <div
          className="kurs-qator kurs-qator-oxirgi"
          style={{ paddingLeft: otstup, display: "block" }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: mashqOchiq ? 8 : 0 }}>
            <span>{tugun.ikonka}</span>
            <span style={{ fontWeight: 600 }}>{tugun.nomi}</span>
            <button className="tugma ikkinchi" onClick={() => setMashqOchiq((v) => !v)}>
              {mashqOchiq
                ? t("yopish")
                : `${t("kurs_ochish")}${tugun.sozlar_soni ? ` (${tugun.sozlar_soni} ${t("kurs_soz")})` : ""}`}
            </button>
          </div>
          {mashqOchiq && <VocabularyKorinishi tugunId={tugun.id} matn={tugun.matn} />}
        </div>
      );
    }

    if (unitBolimi === "Mashqlar") {
      return (
        <div
          className="kurs-qator kurs-qator-oxirgi"
          style={{ paddingLeft: otstup, display: "block" }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: mashqOchiq ? 8 : 0 }}>
            <span>{tugun.ikonka}</span>
            <span style={{ fontWeight: 600 }}>{tugun.nomi}</span>
            <button className="tugma ikkinchi" onClick={() => setMashqOchiq((v) => !v)}>
              {mashqOchiq
                ? t("yopish")
                : `${t("kurs_ochish")}${tugun.mashqlar_soni ? ` (${tugun.mashqlar_soni})` : ""}`}
            </button>
          </div>
          {mashqOchiq && (
            <MashqPaneli tugunId={tugun.id} talabaMi={talabaMi} jsonKiritishKorinadi={false} />
          )}
        </div>
      );
    }

    // ==== Generik (flat) bo'limlar — avvalgidek fayl+mashq ko'rinishi ====
    async function faylniOch() {
      if (!tugun.fayl_url) return;
      const url = await apiBlobUrl(tugun.fayl_url).catch(() => null);
      if (url) window.open(url, "_blank");
    }

    async function faylYukla(e) {
      const fayl = e.target.files[0];
      e.target.value = "";
      if (!fayl) return;
      setFaylXato("");
      setYuklanmoqda(true);
      try {
        const fd = new FormData();
        fd.append("fayl", fayl);
        await apiForm(`/api/kurslar/${tugun.id}/fayl-boshqaruv/`, { method: "PATCH", formData: fd });
        royxatniYangila();
      } catch (e2) {
        setFaylXato(e2.data?.detail || t("xato_yuz_berdi"));
      } finally {
        setYuklanmoqda(false);
      }
    }

    async function tugallandiBelgila() {
      const res = await api(`/api/kurslar/${tugun.id}/tugallandi/`, { method: "POST" }).catch(() => null);
      if (res) setTugallandimi(res.tugallandimi);
    }

    return (
      <div>
        <div
          className="kurs-qator kurs-qator-oxirgi"
          style={{ paddingLeft: otstup, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}
        >
          <span>{tugun.ikonka}</span>
          <span>{tugun.nomi}</span>
          {tugun.fayl_url ? (
            <button className="tugma ikkinchi" onClick={faylniOch}>
              {t("kurs_faylni_ochish")}
            </button>
          ) : (
            <span className="izoh">{t("kurs_fayl_yoq")}</span>
          )}
          {talabaMi && tugun.fayl_url && (
            <button
              className="tugma ikkinchi"
              style={tugallandimi ? { background: "var(--komir)", color: "var(--sariq)" } : undefined}
              onClick={tugallandiBelgila}
            >
              {tugallandimi ? `✓ ${t("kurs_tugallandi")}` : t("kurs_tugallandim")}
            </button>
          )}
          {adminMi && (
            <>
              <input type="file" onChange={faylYukla} disabled={yuklanmoqda} style={{ maxWidth: 200 }} />
              {faylXato && <span className="xato-xabar">{faylXato}</span>}
            </>
          )}
          {(adminMi || tugun.mashqlar_soni) && (
            <button className="tugma ikkinchi" onClick={() => setMashqOchiq((v) => !v)}>
              {mashqOchiq
                ? t("yopish")
                : `${t("kurs_mashqlar")}${tugun.mashqlar_soni ? ` (${tugun.mashqlar_soni})` : ""}`}
            </button>
          )}
        </div>
        {mashqOchiq && (
          <div style={{ paddingLeft: otstup, marginTop: 6 }}>
            <MashqPaneli tugunId={tugun.id} talabaMi={talabaMi} />
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <div
        className="kurs-qator kurs-qator-branch"
        style={{ paddingLeft: otstup, display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}
        onClick={onOchish}
      >
        <span>{ochiqmi ? "▾" : "▸"}</span>
        <span>{tugun.ikonka}</span>
        <span style={{ fontWeight: chuqurlik < 2 ? 700 : 500 }}>{tugun.nomi}</span>
      </div>
      {/* Unit uchun yagona yuklash tugmasi (2026-07-27) — sarlavha
          qatoridan tashqarida, aks holda bosilganda akkordeon ham
          ochilib/yopilib ketardi (`stopPropagation` shu yerda ishlamaydi,
          chunki tugma alohida qatorda). */}
      {adminMi && tugun.unit_darsi && (
        <div style={{ paddingLeft: otstup + 18 }}>
          <AdminUnitKiritish unitId={tugun.id} royxatniYangila={royxatniYangila} />
        </div>
      )}
      {ochiqmi && (
        <div>
          {tugun.children.map((b) => (
            <Tugun
              key={b.id}
              tugun={b}
              chuqurlik={chuqurlik + 1}
              adminMi={adminMi}
              talabaMi={talabaMi}
              royxatniYangila={royxatniYangila}
              ichkariUnitMi={tugun.unit_darsi}
              ochiqmi={ochiqBolaId === b.id}
              onOchish={() => setOchiqBolaId((joriy) => (joriy === b.id ? null : b.id))}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/** "Kurslar" bo'limi — ko'p bosqichli iyerarxik menyu (Kurs > Daraja >
 * Unit/Bo'lim > Mashq turi). Talaba/admin/owner/o'qituvchi ko'radi, "oddiy
 * foydalanuvchi" ko'rmaydi. Tuzilma qattiq (kurslar_urugla buyrug'i orqali
 * bir martalik yaratiladi) — admin oxirgi qatlamga fayl/mashq biriktiradi.
 * Unit'lar (masalan darslik bo'limlari) ketma-ket ochiladi — talaba uchun
 * keyingisi oldingisining BARCHA bo'limlaridagi mashqlardan jami 60%+
 * ball olmaguncha qulflangan (🔒) bo'lib ko'rsatiladi. */
export default function Kurslar() {
  const { t } = useI18n();
  const { profil } = useProfil();
  const adminMi = profil?.is_owner || profil?.role === "admin";
  const talabaMi = profil?.role === "student";
  const [daraxt, setDaraxt] = useState(null);
  // Akkordeon (2026-07-27) — ildiz darajasida (Rus tili/Matematika/Ingliz
  // tili/CEFR) ham bir vaqtda faqat bittasi ochiq turishi uchun; birinchi
  // yuklashda "tez kunda" bo'lmagan birinchi bo'lim (hozircha — Ingliz
  // tili) avtomatik ochiq boshlanadi, avvalgi ko'rinishni saqlab qolish
  // uchun (qayta yuklashda tanlov o'chib qolmasin — `royxatniYangila`
  // ko'p marta chaqiriladi).
  const [ochiqIldizId, setOchiqIldizId] = useState(null);

  function yukla() {
    api("/api/kurslar/daraxt/").then((d) => {
      setDaraxt(d);
      setOchiqIldizId((joriy) => joriy ?? d.children.find((c) => !c.tez_kunda)?.id ?? null);
    }).catch(() => {});
  }

  useEffect(() => {
    yukla();
  }, []);

  if (!daraxt) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <div className="karta">
      <h3>{t("nav_kurslar")}</h3>
      {daraxt.children.map((tugun) => (
        <Tugun
          key={tugun.id}
          tugun={tugun}
          chuqurlik={0}
          adminMi={adminMi}
          talabaMi={talabaMi}
          royxatniYangila={yukla}
          ichkariUnitMi={false}
          ochiqmi={ochiqIldizId === tugun.id}
          onOchish={() => setOchiqIldizId((joriy) => (joriy === tugun.id ? null : tugun.id))}
        />
      ))}
    </div>
  );
}
