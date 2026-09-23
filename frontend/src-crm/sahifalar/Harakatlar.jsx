// Harakatlar tarixi (video 00:30: Sozlamalar -> "Harakatlar tarixi") —
// CRM'dagi o'zgarishlar jurnali: kim, qachon, nimani o'zgartirdi.
// Faqat o'qish; manba — mavjud audit ilovasi (`audit.FaoliyatYozuvi`).

import { useState } from "react";

import { vaqt } from "../format.js";
import { useI18n } from "../i18n.jsx";
import { sorovSatri, useSorov } from "../soragich.js";

function ozgarishMatni(ozgarishlar) {
  if (!ozgarishlar || typeof ozgarishlar !== "object") return "";
  return Object.entries(ozgarishlar)
    .map(([k, v]) => (v && typeof v === "object" && "yangi" in v ? `${k}: ${v.eski ?? "—"} → ${v.yangi ?? "—"}` : k))
    .join("; ");
}

export default function Harakatlar() {
  const { t } = useI18n();
  const [qidiruv, setQidiruv] = useState("");
  const [dan, setDan] = useState("");
  const [gacha, setGacha] = useState("");
  const { malumot, yuklanmoqda, xato } = useSorov("/api/crm/harakatlar/" + sorovSatri({ q: qidiruv, dan, gacha }));

  return (
    <section>
      <h1>{t("harakatlar_tarixi")}</h1>
      <div className="filtrlar">
        <input placeholder={t("qidiruv")} value={qidiruv} onChange={(e) => setQidiruv(e.target.value)} />
        <label className="yonma">{t("dan")}<input type="date" value={dan} onChange={(e) => setDan(e.target.value)} /></label>
        <label className="yonma">{t("gacha")}<input type="date" value={gacha} onChange={(e) => setGacha(e.target.value)} /></label>
      </div>
      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && !malumot && <p className="kichik">{t("yuklanmoqda")}</p>}
      <div className="karta jadval-oram">
        <table>
          <thead>
            <tr><th>{t("vaqt")}</th><th>{t("kim")}</th><th>{t("harakat")}</th><th>{t("turi")}</th><th>{t("obyekt")}</th><th>{t("ozgarishlar")}</th></tr>
          </thead>
          <tbody>
            {(malumot || []).map((x) => (
              <tr key={x.id}>
                <td className="nowrap">{vaqt(x.vaqt)}</td>
                <td>{x.kim || "—"}</td>
                <td>{x.harakat}</td>
                <td>{x.turi}</td>
                <td>{x.nomi || "—"}</td>
                <td className="kichik">{ozgarishMatni(x.ozgarishlar) || "—"}</td>
              </tr>
            ))}
            {!yuklanmoqda && (malumot || []).length === 0 && (
              <tr><td colSpan={6} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
