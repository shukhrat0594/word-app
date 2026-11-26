import { useEffect, useRef, useState } from "react";
import { apiForm } from "../api";
import { useI18n } from "../i18n";
import { IMLO_OFF } from "../imlo";

// TZ 727: darajalar (kod backend TRAINER_DARAJALAR bilan bir xil) va tahlil tillari.
const DARAJALAR = [
  ["A1", "Beginner"],
  ["A2", "Elementary"],
  ["B1", "Pre-Intermediate"],
  ["B2", "Intermediate"],
  ["C1", "Upper-Intermediate"],
  ["CEFR", "CEFR"], // TZ 767
  ["IELTS", "IELTS"], // TZ 733
];
// TZ 767: bitta umumiy prompt — barcha darajalarda (IELTS ham) uchala til,
// IELTS'ning maqsadli ball / rejim tanlovlari olib tashlandi (promptda
// chegara qat'iy: Band 7.5+).
const TILLAR = [
  ["uz", "O'zbekcha"],
  ["ru", "Русский"],
  ["en", "English"],
];

/** AI Speaking Trainer (2026-10-20, TZ 421) — murabbiy bilan suhbat.
 * Talaba avval darajasi va tahlil tilini tanlaydi (TZ 727), AI savol
 * beradi, talaba ovoz (yoki matn) bilan javob beradi, tahlil tanlangan
 * tilda keladi. Suhbat tarixi faqat
 * shu sahifada saqlanadi — har so'rovda backendga to'liq yuboriladi
 * (`/api/speaking/trainer/`). */
export default function SpeakingTrainer() {
  const { t } = useI18n();
  const [xabarlar, setXabarlar] = useState([]);
  const [matn, setMatn] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [xato, setXato] = useState("");
  const [yozilmoqda, setYozilmoqda] = useState(false);
  const [yozishSoniya, setYozishSoniya] = useState(0);
  const mediaRecorderRef = useRef(null);
  const bolaklarRef = useRef([]);
  const pastRef = useRef(null);
  // TZ 727: mashg'ulotdan oldin daraja va tahlil tili tanlanadi.
  const [daraja, setDaraja] = useState("");
  const [til, setTil] = useState("");
  // TZ 742 qo'shimcha (2026-11-20): sessiya urug'i — server shundan shu
  // suhbat mavzularini tanlaydi; har "Boshlash"da yangi son.
  const urugRef = useRef("");
  const tayyor = daraja && til;

  useEffect(() => {
    pastRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [xabarlar, yuklanmoqda]);

  useEffect(() => {
    if (!yozilmoqda) return undefined;
    const boshlandi = Date.now();
    setYozishSoniya(0);
    const taymer = setInterval(() => setYozishSoniya(Math.floor((Date.now() - boshlandi) / 1000)), 1000);
    return () => clearInterval(taymer);
  }, [yozilmoqda]);

  async function yubor({ tarix, audio }) {
    setXato("");
    setYuklanmoqda(true);
    try {
      const fd = new FormData();
      fd.append("xabarlar", JSON.stringify(tarix));
      fd.append("daraja", daraja);
      fd.append("til", til);
      fd.append("urug", urugRef.current);
      if (audio) fd.append("audio", audio, "yozuv.webm");
      const res = await apiForm("/api/speaking/trainer/", { method: "POST", formData: fd });
      const yangi = [...tarix];
      if (res.transkript) yangi.push({ rol: "user", matn: res.transkript });
      yangi.push({ rol: "model", matn: res.javob });
      setXabarlar(yangi);
      return true;
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
      return false;
    } finally {
      setYuklanmoqda(false);
    }
  }

  async function matnniYubor() {
    const m = matn.trim();
    if (!m || yuklanmoqda) return;
    const tarix = [...xabarlar, { rol: "user", matn: m }];
    setXabarlar(tarix);
    if (await yubor({ tarix })) setMatn("");
    else setXabarlar(xabarlar);
  }

  async function yozishBoshla() {
    setXato("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      bolaklarRef.current = [];
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) bolaklarRef.current.push(e.data);
      };
      mr.onstop = () => {
        stream.getTracks().forEach((tr) => tr.stop());
        const blob = new Blob(bolaklarRef.current, { type: mr.mimeType || "audio/webm" });
        yubor({ tarix: xabarlar, audio: blob });
      };
      mediaRecorderRef.current = mr;
      mr.start();
      setYozilmoqda(true);
    } catch {
      setXato(t("mikrofon_ruxsat_yoq"));
    }
  }

  function yozishToxtat() {
    mediaRecorderRef.current?.stop();
    setYozilmoqda(false);
  }

  const boshlangan = xabarlar.length > 0;

  return (
    <>
      <div className="karta" style={{ marginBottom: 14 }}>
        <h3>🎙 {t("nav_speaking_trainer")}</h3>
        <p className="izoh" style={{ margin: 0 }}>{t("trainer_izoh")}</p>
        {boshlangan && (
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
            <button
              className="tugma ikkinchi"
              disabled={yuklanmoqda || yozilmoqda}
              onClick={() => { setXabarlar([]); setXato(""); setMatn(""); }}
            >
              {t("trainer_yangi")}
            </button>
          </div>
        )}
      </div>

      {!boshlangan && (
        <div className="karta" style={{ marginBottom: 14 }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>{t("trainer_daraja_tanlang")}</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
            {DARAJALAR.map(([kod, nom]) => (
              <button
                key={kod}
                className={daraja === kod ? "tugma" : "tugma ikkinchi"}
                disabled={yuklanmoqda}
                onClick={() => setDaraja(kod)}
              >
                {kod === nom ? nom : `${nom} (${kod})`}
              </button>
            ))}
          </div>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>{t("trainer_til_tanlang")}</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
            {TILLAR.map(([kod, nom]) => (
              <button
                key={kod}
                className={til === kod ? "tugma" : "tugma ikkinchi"}
                disabled={yuklanmoqda}
                onClick={() => setTil(kod)}
              >
                {nom}
              </button>
            ))}
          </div>
          <button
            className="tugma katta"
            disabled={yuklanmoqda || !tayyor}
            onClick={() => {
              urugRef.current = String(Math.floor(Math.random() * 1e9));
              yubor({ tarix: [] });
            }}
          >
            {yuklanmoqda ? t("trainer_kutilmoqda") : t("trainer_boshlash")}
          </button>
        </div>
      )}

      {boshlangan && (
        <div className="karta">
          {xabarlar.map((x, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                justifyContent: x.rol === "user" ? "flex-end" : "flex-start",
                marginBottom: 10,
              }}
            >
              <div
                style={{
                  maxWidth: "85%",
                  padding: "8px 12px",
                  borderRadius: 10,
                  whiteSpace: "pre-wrap",
                  background: x.rol === "user" ? "var(--asosiy, #2b6cb0)" : "rgba(127,127,127,0.12)",
                  color: x.rol === "user" ? "#fff" : "inherit",
                }}
              >
                {x.matn}
              </div>
            </div>
          ))}
          {yuklanmoqda && <div className="izoh">{t("trainer_kutilmoqda")}</div>}
          <div ref={pastRef} />

          <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap", alignItems: "center" }}>
            {!yozilmoqda ? (
              <button className="tugma katta" disabled={yuklanmoqda} onClick={yozishBoshla}>
                🎙 {t("yozib_olish")}
              </button>
            ) : (
              <button className="tugma katta" style={{ background: "#d33", color: "#fff" }} onClick={yozishToxtat}>
                ⏹ {t("toxtatish")} ({Math.floor(yozishSoniya / 60)}:{String(yozishSoniya % 60).padStart(2, "0")})
              </button>
            )}
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
            <textarea
              {...IMLO_OFF}
              rows={2}
              style={{ flex: 1, minHeight: 0 }}
              value={matn}
              onChange={(e) => setMatn(e.target.value)}
              placeholder={t("trainer_yozing")}
              disabled={yuklanmoqda || yozilmoqda}
            />
            <button
              className="tugma"
              disabled={!matn.trim() || yuklanmoqda || yozilmoqda}
              onClick={matnniYubor}
            >
              {t("trainer_yuborish")}
            </button>
          </div>
        </div>
      )}
      {xato && <div className="xato-xabar" style={{ marginTop: 10 }}>{xato}</div>}
    </>
  );
}
