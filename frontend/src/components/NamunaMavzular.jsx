import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";

/** Writing/Speaking uchun tayyor namuna mavzular banki — o'qish uchun, tekshiruvsiz. */
export default function NamunaMavzular({ bolim }) {
  const { t } = useI18n();
  const [ochiq, setOchiq] = useState(false);
  const [royxat, setRoyxat] = useState([]);
  const [tanlangan, setTanlangan] = useState(null);

  useEffect(() => {
    if (ochiq && royxat.length === 0) {
      api(`/api/mashqlar/?bolim=${bolim}`).then(setRoyxat).catch(() => {});
    }
  }, [ochiq, bolim, royxat.length]);

  async function ochish(id) {
    const m = await api(`/api/mashqlar/${id}/`);
    setTanlangan(m);
  }

  return (
    <div className="karta" style={{ marginTop: 18 }}>
      <h3 style={{ cursor: "pointer" }} onClick={() => setOchiq((v) => !v)}>
        {t("namuna_mavzular")} {ochiq ? "▲" : "▼"}
      </h3>

      {ochiq && !tanlangan && (
        <>
          {royxat.length === 0 && <span className="izoh">{t("namuna_royxat_boshi")}</span>}
          {royxat.map((m) => (
            <div key={m.id} className="mashq-royxat-el" onClick={() => ochish(m.id)}>
              <span>{m.name}</span>
            </div>
          ))}
        </>
      )}

      {ochiq && tanlangan && (
        <>
          <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
            <button className="tugma ikkinchi" onClick={() => setTanlangan(null)}>
              {t("namuna_yopish")}
            </button>
          </div>
          <div className="mashq-passage">{tanlangan.matn}</div>
          {tanlangan.namuna_javob && (
            <>
              <h3 style={{ marginTop: 16 }}>{t("mashq_namuna_javob")}</h3>
              <div className="mashq-passage">{tanlangan.namuna_javob}</div>
            </>
          )}
        </>
      )}
    </div>
  );
}
