import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";

const BOSH_FORMA = { id: null, name: "", oqituvchi_id: "", talaba_idlar: [] };

export default function Guruhlar() {
  const { t } = useI18n();
  const [guruhlar, setGuruhlar] = useState([]);
  const [azolar, setAzolar] = useState(null);
  const [forma, setForma] = useState(null);
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  function guruhlarniYukla() {
    api("/api/guruhlar/").then(setGuruhlar).catch(() => {});
  }

  useEffect(() => {
    guruhlarniYukla();
    // Owner markazga biriktirilmagan bo'lishi mumkin — bu holda 400 keladi,
    // sahifa "yuklanmoqda"da abadiy qolmasligi uchun bo'sh ro'yxat bilan davom etamiz.
    api("/api/markaz-azolari/")
      .then(setAzolar)
      .catch(() => setAzolar({ oqituvchilar: [], talabalar: [] }));
  }, []);

  async function guruhniOch(id) {
    setXato("");
    try {
      const g = await api(`/api/guruhlar/${id}/`);
      setForma({
        id: g.id,
        name: g.name,
        oqituvchi_id: g.oqituvchi?.id || "",
        talaba_idlar: g.talabalar.map((t2) => t2.id),
      });
    } catch {
      setXato(t("xato_yuz_berdi"));
    }
  }

  function talabaBelgila(id) {
    setForma((f) => ({
      ...f,
      talaba_idlar: f.talaba_idlar.includes(id)
        ? f.talaba_idlar.filter((x) => x !== id)
        : [...f.talaba_idlar, id],
    }));
  }

  async function saqla() {
    setXato("");
    if (!forma.name.trim()) {
      setXato(t("guruh_nomi"));
      return;
    }
    setBand(true);
    const body = {
      name: forma.name,
      oqituvchi_id: forma.oqituvchi_id || null,
      talaba_idlar: forma.talaba_idlar,
    };
    try {
      if (forma.id) {
        await api(`/api/guruhlar/${forma.id}/`, { method: "PATCH", body });
      } else {
        await api("/api/guruhlar/", { method: "POST", body });
      }
      setForma(null);
      guruhlarniYukla();
    } catch {
      setXato(t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  if (!azolar) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <>
      {!forma && (
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button className="tugma" onClick={() => setForma(BOSH_FORMA)}>
            {t("yangi_guruh")}
          </button>
        </div>
      )}

      {forma && (
        <div className="karta">
          <h3>{forma.id ? forma.name : t("yangi_guruh")}</h3>
          <div style={{ display: "grid", gap: 14 }}>
            <input
              placeholder={t("guruh_nomi")}
              value={forma.name}
              onChange={(e) => setForma({ ...forma, name: e.target.value })}
            />
            <div>
              <div className="izoh" style={{ marginBottom: 6 }}>{t("oqituvchi")}</div>
              <select
                value={forma.oqituvchi_id}
                onChange={(e) => setForma({ ...forma, oqituvchi_id: e.target.value })}
              >
                <option value="">— {t("tanlanmagan")} —</option>
                {azolar.oqituvchilar.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.ism}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <div className="izoh" style={{ marginBottom: 6 }}>{t("talabalar")}</div>
              <div className="azo-royxat">
                {azolar.talabalar.map((tl) => (
                  <label className="azo-qator" key={tl.id}>
                    <input
                      type="checkbox"
                      checked={forma.talaba_idlar.includes(tl.id)}
                      onChange={() => talabaBelgila(tl.id)}
                    />
                    {tl.ism}
                  </label>
                ))}
              </div>
            </div>
            {xato && <div className="xato-xabar">{xato}</div>}
            <div style={{ display: "flex", gap: 10 }}>
              <button className="tugma" onClick={saqla} disabled={band}>
                {forma.id ? t("saqlash") : t("yaratish")}
              </button>
              <button className="tugma ikkinchi" onClick={() => setForma(null)}>
                {t("ortga")}
              </button>
            </div>
          </div>
        </div>
      )}

      {!forma && (
        <div style={{ display: "grid", gap: 12, marginTop: 12 }}>
          {guruhlar.length === 0 && <span className="izoh">{t("guruh_yoq")}</span>}
          {guruhlar.map((g) => (
            <div className="guruh-karta" key={g.id} onClick={() => guruhniOch(g.id)}>
              <div className="g-mal">
                <div className="g-nomi">{g.name}</div>
                <div className="g-info">
                  {g.oqituvchi ? g.oqituvchi.ism : `— ${t("tanlanmagan")} —`} ·{" "}
                  {g.talaba_soni} {t("talabalar").toLowerCase()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
