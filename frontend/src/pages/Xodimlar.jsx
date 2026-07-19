import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";

const BOSH_FORMA = { ism: "", username: "", parol: "" };

export default function Xodimlar() {
  const { t } = useI18n();
  const [oqituvchilar, setOqituvchilar] = useState(null);
  const [forma, setForma] = useState(BOSH_FORMA);
  const [xato, setXato] = useState("");
  const [xabar, setXabar] = useState("");
  const [band, setBand] = useState(false);

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
