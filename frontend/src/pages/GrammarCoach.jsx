import { useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { IMLO_OFF } from "../imlo";

// Interfeys tili -> AI tushuntirish tili (backend aynan shu qiymatlarni kutadi)
const TILLAR = [
  { kalit: "Uzbek", nom: "O'zbekcha", ui: "uz" },
  { kalit: "Russian", nom: "Русский", ui: "ru" },
  { kalit: "English", nom: "English", ui: "en" },
];

/** AI Grammar Coach (2026-10-26, TZ 613) — talaba tushunmagan grammatika
 * mavzusi yoki gapni yozadi, AI tanlangan tilda qoida, misollar va
 * mini-test qaytaradi (`/api/grammar/coach/`). Natija saqlanmaydi. */
export default function GrammarCoach() {
  const { t, til: uiTil } = useI18n();
  const [matn, setMatn] = useState("");
  const [til, setTil] = useState(TILLAR.find((x) => x.ui === uiTil)?.kalit || "Uzbek");
  const [javob, setJavob] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [xato, setXato] = useState("");
  // Follow-up chat (TZ 640): tushuntirishdan keyingi savol-javoblar
  const [suhbat, setSuhbat] = useState([]);
  const [savol, setSavol] = useState("");
  // Tushuntirish olingan asl kiritma — keyin maydon tahrirlansa ham kontekst o'zgarmasin
  const [mavzu, setMavzu] = useState("");

  async function sora() {
    const m = matn.trim();
    if (!m || yuklanmoqda) return;
    setXato("");
    setYuklanmoqda(true);
    try {
      const res = await api("/api/grammar/coach/", { method: "POST", body: { matn: m, til } });
      setJavob(res.javob);
      setMavzu(m);
      setSuhbat([]);
      setSavol("");
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  async function qoshimchaSora() {
    const s = savol.trim();
    if (!s || !javob || yuklanmoqda) return;
    const kontekst = [
      `Student Input: ${mavzu}`,
      `Explanation:\n${javob}`,
      ...suhbat.map((x) => `Student: ${x.savol}\nCoach: ${x.javob}`),
    ].join("\n\n");
    setXato("");
    setYuklanmoqda(true);
    try {
      const res = await api("/api/grammar/coach/", { method: "POST", body: { matn: s, til, kontekst } });
      setSuhbat((old) => [...old, { savol: s, javob: res.javob }]);
      setSavol("");
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  return (
    <>
      <div className="karta" style={{ marginBottom: 14 }}>
        <h3>📘 {t("nav_grammar_coach")}</h3>
        <p className="izoh" style={{ marginTop: 0 }}>{t("grammar_izoh")}</p>
        <textarea
          {...IMLO_OFF}
          rows={3}
          maxLength={1000}
          style={{ width: "100%" }}
          value={matn}
          onChange={(e) => setMatn(e.target.value)}
          placeholder={t("grammar_yozing")}
          disabled={yuklanmoqda}
        />
        <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap", alignItems: "center" }}>
          <label className="izoh">{t("grammar_til")}:</label>
          <select value={til} onChange={(e) => setTil(e.target.value)} disabled={yuklanmoqda}>
            {TILLAR.map((x) => (
              <option key={x.kalit} value={x.kalit}>{x.nom}</option>
            ))}
          </select>
          <button className="tugma" disabled={!matn.trim() || yuklanmoqda} onClick={sora}>
            {yuklanmoqda ? t("trainer_kutilmoqda") : t("grammar_sorash")}
          </button>
        </div>
      </div>
      {javob && (
        <div className="karta" style={{ whiteSpace: "pre-wrap", marginBottom: 14 }}>
          {javob}
        </div>
      )}
      {suhbat.map((x, i) => (
        <div key={i} style={{ marginBottom: 14 }}>
          <div className="karta" style={{ whiteSpace: "pre-wrap", marginBottom: 8 }}>
            <b>❓ {x.savol}</b>
          </div>
          <div className="karta" style={{ whiteSpace: "pre-wrap" }}>{x.javob}</div>
        </div>
      ))}
      {xato && <div className="xato-xabar" style={{ marginBottom: 10 }}>{xato}</div>}
      {javob && (
        <div className="karta">
          <textarea
            {...IMLO_OFF}
            rows={2}
            maxLength={1000}
            style={{ width: "100%" }}
            value={savol}
            onChange={(e) => setSavol(e.target.value)}
            placeholder={t("grammar_qoshimcha_savol")}
            disabled={yuklanmoqda}
          />
          <button
            className="tugma"
            style={{ marginTop: 10 }}
            disabled={!savol.trim() || yuklanmoqda}
            onClick={qoshimchaSora}
          >
            {yuklanmoqda ? t("trainer_kutilmoqda") : t("grammar_qoshimcha_sorash")}
          </button>
        </div>
      )}
    </>
  );
}
