import { useEffect, useState } from "react";
import { api, apiForm } from "../api";
import { useI18n } from "../i18n";

export default function MarkazSozlash() {
  const { t } = useI18n();
  const [markaz, setMarkaz] = useState(null);
  const [rang, setRang] = useState("#FFD400");
  const [logoFayl, setLogoFayl] = useState(null);
  const [xabar, setXabar] = useState("");
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  useEffect(() => {
    api("/api/markaz-sozlama/").then((m) => {
      setMarkaz(m);
      setRang(m.brend_rang);
    }).catch(() => {});
  }, []);

  async function saqla() {
    setXato("");
    setXabar("");
    setBand(true);
    try {
      const fd = new FormData();
      fd.append("brend_rang", rang);
      if (logoFayl) fd.append("logo", logoFayl);
      const m = await apiForm("/api/markaz-sozlama/", { method: "PATCH", formData: fd });
      setMarkaz(m);
      setLogoFayl(null);
      setXabar(t("saqlandi"));
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  if (!markaz) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <div className="karta">
      <h3>{markaz.name}</h3>
      <p className="izoh">{t("markaz_sozlama_izoh")}</p>

      <div style={{ display: "grid", gap: 16, maxWidth: 360 }}>
        <div>
          <div className="izoh" style={{ marginBottom: 6 }}>{t("logo")}</div>
          {markaz.logo_url && (
            <img
              src={markaz.logo_url}
              alt={markaz.name}
              style={{ height: 48, marginBottom: 8, display: "block" }}
            />
          )}
          <input type="file" accept="image/*" onChange={(e) => setLogoFayl(e.target.files[0])} />
        </div>

        <div>
          <div className="izoh" style={{ marginBottom: 6 }}>{t("brend_rangi")}</div>
          <input
            type="color"
            value={rang}
            onChange={(e) => setRang(e.target.value)}
            style={{ width: 60, height: 40, padding: 2 }}
          />
        </div>

        {xato && <div className="xato-xabar">{xato}</div>}
        {xabar && <div className="izoh">{xabar}</div>}
        <button className="tugma" onClick={saqla} disabled={band}>
          {t("saqlash")}
        </button>
      </div>
    </div>
  );
}
