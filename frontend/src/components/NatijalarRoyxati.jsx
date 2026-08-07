import { useEffect, useState } from "react";
import { api, mediaManzil } from "../api";
import { AUDIO_HIMOYA, faqatBittaAudioIjro } from "../audio";
import { useI18n } from "../i18n";
import { xatoniAjrat } from "../xatoUtils";

// Ko'p tilli maydon ({en,uz,ru}) yoki oddiy matn bo'lishi mumkin — React
// obyektni to'g'ridan-to'g'ri render qila olmasligi sababli (2026-08-07,
// foydalanuvchi topgan bug: "writing testini ko'rmoqchi bo'lganda ekran
// oppoq bo'lib qoldi" — sabab aynan shu, natija.errors elementlari matn
// emas, obyekt ekan) HAR doim shu funksiya orqali matnga aylantiriladi.
function matnGaAylantir(qiymat) {
  if (qiymat == null) return "";
  if (typeof qiymat === "string" || typeof qiymat === "number") return String(qiymat);
  if (typeof qiymat === "object") return qiymat.en || qiymat.uz || qiymat.ru || Object.values(qiymat).find((v) => typeof v === "string") || "";
  return "";
}

// `xato` elementi ikki xil shaklda bo'lishi mumkin: eski (matn, "xato ->
// tuzatish (sabab)") yoki hozirgi (obyekt, {xato, tuzatish, izoh}) —
// ikkalasini ham bir xil {notogri, togri, sabab} shaklga keltiradi.
function xatoElementiniAjrat(qator) {
  if (qator && typeof qator === "object") {
    return {
      notogri: matnGaAylantir(qator.xato),
      togri: matnGaAylantir(qator.tuzatish),
      sabab: matnGaAylantir(qator.izoh),
    };
  }
  return xatoniAjrat(matnGaAylantir(qator));
}

const TURI_KALIT = {
  reading: "reading_bolimi",
  listening: "listening_bolimi",
  writing: "nav_writing",
  speaking: "nav_speaking",
  kurslar: "nav_kurslar",
};

/** Bitta talabaning BARCHA mashq/test natijalari (2026-08-05) — owner
 * va teacher (Talabalar.jsx'dan modal sifatida) va talabaning o'zi
 * (Tarix.jsx'dan) bir xil komponentni ishlatadi. Writing/Speaking
 * detali `Tarix.jsx`dagi bilan BIR XIL (AI natija tuzilishi shu turga
 * xos), boshqa turlar uchun (Reading/Listening/Kurslar) — ball va
 * savol-bo'yicha to'g'ri/noto'g'ri ro'yxati. */
export default function NatijalarRoyxati({ talabaId }) {
  const { t } = useI18n();
  const [malumot, setMalumot] = useState(null);
  const [xato, setXato] = useState("");
  const [ochiqId, setOchiqId] = useState(null);

  useEffect(() => {
    setMalumot(null);
    setXato("");
    api(`/api/foydalanuvchilar/${talabaId}/natijalar/`)
      .then(setMalumot)
      .catch((e) => setXato(e.data?.detail || t("xato_yuz_berdi")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [talabaId]);

  if (xato) return <div className="xato-xabar">{xato}</div>;
  if (!malumot) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  const royxat = malumot.natijalar;

  return (
    <div>
      {royxat.length === 0 && <span className="izoh">{t("tarix_yoq")}</span>}
      {royxat.map((y) => {
        const kalit = `${y.turi}-${y.id}`;
        const ochiqmi = ochiqId === kalit;
        const yozGapMi = y.turi === "writing" || y.turi === "speaking";
        const baho = y.band ?? (y.jami ? `${y.ball}/${y.jami}` : "—");
        return (
          <div key={kalit}>
            <div className="tarix-el" onClick={() => setOchiqId(ochiqmi ? null : kalit)}>
              <span>
                <span className="chip bor" style={{ marginRight: 8 }}>
                  {t(TURI_KALIT[y.turi] || y.turi)}
                </span>
                {y.nomi} · {new Date(y.sana).toLocaleDateString()}
                {y.audio_url && " 🎙"}
              </span>
              <strong>{baho}</strong>
            </div>

            {ochiqmi && (
              <div className="karta" style={{ margin: "8px 0 16px", background: "var(--sirt-2)" }}>
                {yozGapMi ? (
                  <>
                    {y.audio_url && (
                      <audio
                        {...AUDIO_HIMOYA}
                        onPlay={(e) => faqatBittaAudioIjro(e.target)}
                        controls
                        src={mediaManzil(y.audio_url)}
                        style={{ width: "100%", marginBottom: 14 }}
                      />
                    )}
                    {y.matn && (
                      <p className="izoh" style={{ whiteSpace: "pre-wrap", marginTop: 0 }}>{y.matn}</p>
                    )}
                    <h3>{t("xatolar")} ({(y.natija || {}).errors?.length || 0})</h3>
                    {(!(y.natija || {}).errors || y.natija.errors.length === 0) && (
                      <span className="izoh">{t("xato_topilmadi")}</span>
                    )}
                    {((y.natija || {}).errors || []).map((qator, i) => {
                      const { notogri, togri, sabab } = xatoElementiniAjrat(qator);
                      return (
                        <div className="xato-el" key={i}>
                          <span className="xato-notogri">{notogri}</span>
                          {togri && <>→ <span className="xato-togri">{togri}</span></>}
                          {sabab && <span className="xato-sabab">({sabab})</span>}
                        </div>
                      );
                    })}
                    {(y.natija || {}).strengths?.length > 0 && (
                      <>
                        <h3 style={{ marginTop: 16 }}>{t("kuchli")}</h3>
                        {y.natija.strengths.map((s, i) => (
                          <div className="xato-el" key={i}>✓ {matnGaAylantir(s)}</div>
                        ))}
                      </>
                    )}
                    {(y.natija || {}).analysis && (
                      <>
                        <h3 style={{ marginTop: 16 }}>{t("tahlil")}</h3>
                        <p className="izoh" style={{ margin: 0 }}>
                          {Object.values(y.natija.analysis).map(matnGaAylantir).join(" ")}
                        </p>
                      </>
                    )}
                  </>
                ) : (
                  <>
                    <div className="izoh" style={{ marginBottom: 8 }}>
                      {t("natija")}: {y.ball}/{y.jami}
                    </div>
                    {(y.natijalar || []).map((togrimi, i) => (
                      <div key={i} className="xato-el">
                        <span className={togrimi ? "xato-togri" : "xato-notogri"}>
                          {i + 1}. {togrimi ? "✓" : "✗"}
                        </span>
                      </div>
                    ))}
                  </>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
