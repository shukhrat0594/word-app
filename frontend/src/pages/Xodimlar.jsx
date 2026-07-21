import { useEffect, useState } from "react";
import { api, apiForm } from "../api";
import { useI18n } from "../i18n";

const BOSH_FORMA = { ism: "", username: "", parol: "" };

export default function Xodimlar() {
  const { t } = useI18n();
  const [oqituvchilar, setOqituvchilar] = useState(null);
  const [forma, setForma] = useState(BOSH_FORMA);
  const [xato, setXato] = useState("");
  const [xabar, setXabar] = useState("");
  const [band, setBand] = useState(false);
  const [excelNatija, setExcelNatija] = useState(null);
  const [excelYuklanmoqda, setExcelYuklanmoqda] = useState(false);

  function yukla() {
    api("/api/xodimlar/").then(setOqituvchilar).catch(() => {});
  }

  useEffect(() => {
    yukla();
  }, []);

  async function yarat() {
    setXato("");
    setXabar("");
    if (!forma.username.trim() || !forma.parol.trim()) {
      setXato(t("xato_yuz_berdi"));
      return;
    }
    setBand(true);
    try {
      await api("/api/xodimlar/", { method: "POST", body: forma });
      setForma(BOSH_FORMA);
      setXabar(t("saqlandi"));
      yukla();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  async function excelYukla(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setExcelNatija(null);
    setExcelYuklanmoqda(true);
    try {
      const fd = new FormData();
      fd.append("excel_fayl", fayl);
      const res = await apiForm("/api/xodimlar/excel-import/", { method: "POST", formData: fd });
      setExcelNatija(res);
      yukla();
    } catch (e2) {
      setExcelNatija({ yaratildi: [], xatolar: [{ xato: e2.data?.detail || t("xato_yuz_berdi") }] });
    } finally {
      setExcelYuklanmoqda(false);
    }
  }

  if (!oqituvchilar) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <>
      <div className="karta">
        <h3>{t("yangi_oqituvchi")}</h3>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <input
            style={{ maxWidth: 160 }}
            placeholder={t("ism")}
            value={forma.ism}
            onChange={(e) => setForma({ ...forma, ism: e.target.value })}
          />
          <input
            style={{ maxWidth: 160 }}
            placeholder={t("login")}
            value={forma.username}
            onChange={(e) => setForma({ ...forma, username: e.target.value })}
          />
          <input
            style={{ maxWidth: 160 }}
            type="password"
            placeholder={t("parol")}
            value={forma.parol}
            onChange={(e) => setForma({ ...forma, parol: e.target.value })}
          />
          <button className="tugma" onClick={yarat} disabled={band}>
            {t("yaratish")}
          </button>
        </div>
        {xato && <div className="xato-xabar" style={{ marginTop: 10 }}>{xato}</div>}
        {xabar && <div className="izoh" style={{ marginTop: 10 }}>{xabar}</div>}
      </div>

      <div className="karta" style={{ marginTop: 16 }}>
        <h3>{t("excel_orqali_kiritish")}</h3>
        <p className="izoh" style={{ marginTop: 0 }}>{t("excel_izoh")}</p>
        <input type="file" accept=".xlsx" onChange={excelYukla} disabled={excelYuklanmoqda} />
        {excelNatija && (
          <div style={{ marginTop: 12 }}>
            {excelNatija.yaratildi.length > 0 && (
              <>
                <div className="izoh">{t("excel_yaratildi")}: {excelNatija.yaratildi.length}</div>
                <div className="xato-xabar" style={{ background: "none", color: "inherit", padding: 0 }}>
                  {t("excel_parol_eslatma")}
                </div>
                <div style={{ display: "grid", gap: 4, marginTop: 6 }}>
                  {excelNatija.yaratildi.map((y) => (
                    <div key={y.id} className="izoh">{y.ism} — {y.login}</div>
                  ))}
                </div>
              </>
            )}
            {excelNatija.xatolar.length > 0 && (
              <div style={{ marginTop: 10 }}>
                {excelNatija.xatolar.map((x, i) => (
                  <div key={i} className="xato-xabar">
                    {x.qator ? `${t("qator")} ${x.qator}: ` : ""}{x.xato}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="karta" style={{ marginTop: 16 }}>
        <h3>{t("nav_xodimlar")}</h3>
        {oqituvchilar.length === 0 && <span className="izoh">{t("oqituvchi_yoq")}</span>}
        {oqituvchilar.map((o) => (
          <div className="tarix-el" key={o.id}>
            <span>{o.ism}</span>
            <span className="izoh">{o.username}</span>
          </div>
        ))}
      </div>
    </>
  );
}
