import { useState } from "react";
import { api } from "../api";
import { TURLAR } from "../components/NamunaMavzular";
import { useI18n } from "../i18n";
import { IMLO_OFF } from "../imlo";

// Yagona model (assessment/providers.py: GEMINI_MODEL) — Writing.jsx/
// Speaking.jsx bilan bir xil kalit.
const MODEL_KALITI = "flash_lite";

// Rasm hajmi chegarasi: base64 ~33% kattalashadi, ya'ni 5 MB fayl ~6.7 MB
// so'rovga aylanadi. Bundan kattasi AI'ga ham keraksiz — grafik/diagramma
// odatda bir necha yuz kilobayt.
const MAX_RASM_BAYT = 5 * 1024 * 1024;

const RUXSAT_MIME = ["image/png", "image/jpeg", "image/webp"];

/** "O'z mavzuyim" — talaba tayyor mavzular ro'yxatidan tanlamaydi, o'zi
 * xohlagan mavzuni kiritib javobini AI'ga tekshirtiradi (2026-07-27 talabi).
 *
 * Ikki joyda ishlatiladi (dublikat kod yozilmasligi uchun bitta komponent):
 *   1. Mashqlar > IELTS > Writing/Speaking — uchinchi tab
 *   2. IELTS testlari > Writing/Speaking — "O'z mavzuyim" tab
 *
 * `NatijaKomponenti` prop orqali beriladi (import qilinmaydi): Writing.jsx
 * bu komponentni o'zi import qiladi, teskari import qilsak aylanma
 * bog'liqlik (circular import) paydo bo'lardi.
 *
 * Backendga yangi endpoint kerak emas — mavjud `/api/writing/tekshirish/`
 * va `/api/speaking/matn/` `savol_matni`ni erkin qabul qiladi.
 */
export default function OzMavzum({ bolim, NatijaKomponenti }) {
  const { t } = useI18n();
  const turlar = TURLAR[bolim] || [];
  const [tur, setTur] = useState(turlar[0]?.tur);
  const [mavzu, setMavzu] = useState("");
  const [javob, setJavob] = useState("");
  const [rasmB64, setRasmB64] = useState(null); // toza base64 (data: prefiksisiz)
  const [rasmMime, setRasmMime] = useState(null);
  const [rasmUrl, setRasmUrl] = useState(null); // ko'rsatish uchun data URL
  const [natija, setNatija] = useState(null);
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [xato, setXato] = useState("");

  const sozSoni = javob.trim() ? javob.trim().split(/\s+/).length : 0;
  // Rasm faqat Writing Task 1 uchun ma'noli (grafik/diagramma tavsifi).
  // Speaking endpointi rasm qabul qilmaydi.
  const rasmMumkin = bolim === "writing" && tur === "task1";

  function rasmniTozala() {
    setRasmB64(null);
    setRasmMime(null);
    setRasmUrl(null);
  }

  function rasmniTanla(e) {
    const fayl = e.target.files?.[0];
    if (!fayl) return;
    setXato("");
    if (fayl.size > MAX_RASM_BAYT) {
      setXato(t("oz_rasm_katta"));
      e.target.value = "";
      return;
    }
    const oquvchi = new FileReader();
    oquvchi.onload = () => {
      const url = String(oquvchi.result);
      setRasmUrl(url);
      setRasmB64(url.slice(url.indexOf(",") + 1));
      setRasmMime(RUXSAT_MIME.includes(fayl.type) ? fayl.type : "image/png");
    };
    oquvchi.readAsDataURL(fayl);
  }

  async function tekshir() {
    setXato("");
    if (!mavzu.trim()) {
      setXato(t("oz_mavzu_kerak"));
      return;
    }
    if (sozSoni < 20) {
      setXato(t("matn_qisqa"));
      return;
    }
    setYuklanmoqda(true);
    try {
      const yol = bolim === "writing" ? "/api/writing/tekshirish/" : "/api/speaking/matn/";
      const body = { matn: javob, savol_matni: mavzu, tur, model: MODEL_KALITI };
      if (rasmMumkin && rasmB64) {
        body.grafik_rasm = rasmB64;
        body.grafik_mime = rasmMime;
      }
      const res = await api(yol, { method: "POST", body });
      setNatija(res.natijalar?.[0]?.natija || null);
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  function yangidan() {
    setNatija(null);
    setJavob("");
    setMavzu("");
    rasmniTozala();
    setXato("");
  }

  if (natija) {
    return (
      <>
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
          <button className="tugma ikkinchi" onClick={yangidan}>
            {t("yangi_tekshiruv")}
          </button>
        </div>
        <div className="karta" style={{ marginBottom: 14 }}>
          <h3>{t("mavzu")}</h3>
          <div className="mashq-passage">{mavzu}</div>
          {rasmUrl && (
            <img src={rasmUrl} alt="" style={{ maxWidth: "100%", marginTop: 10 }} />
          )}
        </div>
        <NatijaKomponenti natija={natija} />
      </>
    );
  }

  return (
    <>
      <div className="karta" style={{ marginBottom: 14 }}>
        <h3>{t("oz_mavzum")}</h3>
        <div className="izoh" style={{ marginBottom: 12 }}>
          {t("oz_mavzum_izoh")}
        </div>

        <div className="tanlov-royxat">
          {turlar.map((tt) => (
            <button
              key={tt.tur}
              className={"tanlov-tugma" + (tur === tt.tur ? " aktiv" : "")}
              onClick={() => {
                setTur(tt.tur);
                if (tt.tur !== "task1") rasmniTozala();
              }}
            >
              {t(tt.kalit)}
            </button>
          ))}
        </div>

        <textarea
          {...IMLO_OFF}
          rows={4}
          value={mavzu}
          onChange={(e) => setMavzu(e.target.value)}
          placeholder={t("oz_mavzu_placeholder")}
          style={{ marginTop: 14 }}
        />

        {rasmMumkin && (
          <div style={{ marginTop: 10 }}>
            <label className="izoh" style={{ display: "block", marginBottom: 4 }}>
              {t("oz_rasm")}
            </label>
            <input type="file" accept="image/png,image/jpeg,image/webp" onChange={rasmniTanla} />
            <div className="izoh" style={{ marginTop: 4 }}>{t("oz_rasm_izoh")}</div>
            {rasmUrl && (
              <div style={{ marginTop: 8 }}>
                <img src={rasmUrl} alt="" style={{ maxWidth: "100%", borderRadius: 8 }} />
                <button
                  className="tugma ikkinchi"
                  style={{ marginTop: 6 }}
                  onClick={rasmniTozala}
                >
                  {t("oz_rasm_olib_tashlash")}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="karta">
        <textarea
          {...IMLO_OFF}
          value={javob}
          onChange={(e) => setJavob(e.target.value)}
          placeholder={bolim === "writing" ? t("insho_placeholder") : t("javob_placeholder")}
        />
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: 12,
            gap: 8,
            flexWrap: "wrap",
          }}
        >
          <span className="izoh">
            {sozSoni} {t("soz")}
          </span>
          <button className="tugma katta" onClick={tekshir} disabled={yuklanmoqda}>
            {yuklanmoqda ? t("tekshirilmoqda") : t("tekshirish")}
          </button>
        </div>
        {xato && (
          <div className="xato-xabar" style={{ marginTop: 10 }}>
            {xato}
          </div>
        )}
      </div>
    </>
  );
}
