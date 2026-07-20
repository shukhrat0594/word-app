import { useEffect, useState } from "react";
import { api, apiForm } from "../api";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";
import ImtihonOtish from "./ImtihonOtish";
import ImtihonYozGap from "./ImtihonYozGap";

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
      "savollar": [
        {
          "savol": "Savol yoki band matni",
          "tur": "quyidagi ro'yxatdan",
          "variantlar": ["variant1", "variant2"],
          "togri": "To'g'ri javob",
          "guruh_boshi": "Questions 1-7" (ixtiyoriy, savollar guruhi boshida sarlavha ko'rsatish uchun, faqat guruhning birinchi savolida yoz, qolganida bo'sh qoldir)
        }
      ]
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

Natijani shu JSON obyekt ko'rinishida qaytar, boshqa hech narsa yozma. Quyida test materiali:

[BU YERGA TEST MATNI/TRANSKRIPTINI JOYLASHTIRING]`;

/** Faqat admin/owner uchun — test yaratish/o'chirish/audio biriktirish. */
function AdminBoshqaruv() {
  const { t } = useI18n();
  const [royxat, setRoyxat] = useState(null);
  const [filtrBolim, setFiltrBolim] = useState("");
  const [jsonXato, setJsonXato] = useState("");
  const [saqlanmoqda, setSaqlanmoqda] = useState(false);
  const [promtKorinadi, setPromtKorinadi] = useState(false);
  const [nusxalandi, setNusxalandi] = useState(false);

  function promtNusxala() {
    navigator.clipboard?.writeText(AI_PROMT).then(() => {
      setNusxalandi(true);
      setTimeout(() => setNusxalandi(false), 2000);
    });
  }

  function yukla(bolim) {
    api(`/api/imtihon/testlar-boshqaruv/${bolim ? `?bolim=${bolim}` : ""}`)
      .then(setRoyxat)
      .catch(() => {});
  }

  useEffect(() => {
    yukla(filtrBolim);
  }, [filtrBolim]);

  async function jsonYukla(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setJsonXato("");
    setSaqlanmoqda(true);
    try {
      const matn = await fayl.text();
      const data = JSON.parse(matn);
      await api("/api/imtihon/testlar-boshqaruv/", { method: "POST", body: data });
      yukla(filtrBolim);
    } catch (err) {
      setJsonXato(err.data?.detail || t("imtihon_json_xato"));
    } finally {
      setSaqlanmoqda(false);
    }
  }

  async function qismgaAudioYukla(qismId, fayl) {
    const fd = new FormData();
    fd.append("audio_fayl", fayl);
    await apiForm(`/api/imtihon/qism-boshqaruv/${qismId}/`, { method: "PATCH", formData: fd });
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
    } catch {
      // sokin
    }
  }

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <div className="karta">
        <h3>{t("imtihon_json_yuklash")}</h3>
        <p className="izoh" style={{ marginTop: 0 }}>{t("imtihon_json_izoh")}</p>
        <input type="file" accept="application/json" onChange={jsonYukla} disabled={saqlanmoqda} />
        {jsonXato && <div className="xato-xabar" style={{ marginTop: 8 }}>{jsonXato}</div>}

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
        </div>
        {!royxat ? (
          <div className="yuklanmoqda">{t("yuklanmoqda")}</div>
        ) : royxat.length === 0 ? (
          <span className="izoh">{t("imtihon_royxat_boshi")}</span>
        ) : (
          <div style={{ display: "grid", gap: 8 }}>
            {royxat.map((test) => (
              <div key={test.id} style={{ padding: 8, border: "1px solid var(--chiziq)", borderRadius: 8 }}>
                <div className="davomat-qator" style={{ borderBottom: "none", padding: 0 }}>
                  <span>
                    <strong>{test.name}</strong>{" "}
                    <span className="izoh">
                      {t(`mashq_bolim_${test.bolim}`)} · {test.qismlar.length} {t("imtihon_qism_soni")}
                    </span>
                  </span>
                  <button className="tugma ikkinchi" style={{ color: "#d33" }} onClick={() => ochir(test.id)}>
                    {t("ochirish")}
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
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** "IELTS testlari" — yagona sahifa: admin/owner uchun boshqaruv (yuqorida,
 * agar ruxsati bo'lsa) + talaba/admin/owner uchun yechish (pastda, hammaga). */
export default function ImtihonBoshqarish() {
  const { t } = useI18n();
  const { profil } = useProfil();
  const adminMi = profil?.is_owner || profil?.role === "admin";
  const [bolim, setBolim] = useState("writing");

  return (
    <div style={{ display: "grid", gap: 20 }}>
      {adminMi && <AdminBoshqaruv />}

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
        </div>
        {(bolim === "writing" || bolim === "speaking") && <ImtihonYozGap bolim={bolim} />}
        {(bolim === "reading" || bolim === "listening") && <ImtihonOtish bolim={bolim} />}
      </div>
    </div>
  );
}
