import { useEffect, useState } from "react";
import { api, apiBlobUrl } from "../api";
import { useI18n } from "../i18n";

/** Reading/Listening mashqlari — ro'yxat, ochish, javob berish, avtomatik ball. */
export default function MashqBank({ bolim }) {
  const { t } = useI18n();
  const [royxat, setRoyxat] = useState([]);
  const [tanlangan, setTanlangan] = useState(null);
  const [javoblar, setJavoblar] = useState({});
  const [natija, setNatija] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [rasmUrl, setRasmUrl] = useState(null);
  const [xato, setXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);

  useEffect(() => {
    setTanlangan(null);
    setNatija(null);
    api(`/api/mashqlar/?bolim=${bolim}`).then(setRoyxat).catch(() => {});
  }, [bolim]);

  async function ochish(id) {
    setXato("");
    setNatija(null);
    setJavoblar({});
    setAudioUrl(null);
    setRasmUrl(null);
    const m = await api(`/api/mashqlar/${id}/`);
    setTanlangan(m);
    if (m.audio_url) {
      apiBlobUrl(m.audio_url).then(setAudioUrl).catch(() => {});
    }
    if (m.rasm_url) {
      apiBlobUrl(m.rasm_url).then(setRasmUrl).catch(() => {});
    }
  }

  function javobniQoy(i, qiymat) {
    setJavoblar((prev) => ({ ...prev, [i]: qiymat }));
  }

  async function yuborish() {
    setYuklanmoqda(true);
    setXato("");
    try {
      const tartib = tanlangan.savollar.map((_, i) => javoblar[i] || "");
      const res = await api(`/api/mashqlar/${tanlangan.id}/yechish/`, {
        method: "POST",
        body: { javoblar: tartib },
      });
      setNatija(res);
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  if (!tanlangan) {
    return (
      <div className="karta">
        {royxat.length === 0 && <span className="izoh">{t("mashq_royxati_boshi")}</span>}
        {royxat.map((m) => (
          <div key={m.id} className="mashq-royxat-el" onClick={() => ochish(m.id)}>
            <span>{m.name}</span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
        <button className="tugma ikkinchi" onClick={() => setTanlangan(null)}>
          {t("ortga")}
        </button>
      </div>
      <div className="karta">
        <h3>{tanlangan.name}</h3>
        {bolim === "listening" && (
          audioUrl ? (
            <audio controls src={audioUrl} style={{ width: "100%", marginBottom: 18 }} />
          ) : (
            <span className="izoh">{t("audio_yuklanmoqda")}</span>
          )
        )}
        {bolim !== "listening" && tanlangan.matn && (
          <div className="mashq-passage">{tanlangan.matn}</div>
        )}
        {rasmUrl && (
          <img src={rasmUrl} alt="" style={{ maxWidth: "100%", marginBottom: 18, borderRadius: 8 }} />
        )}

        {tanlangan.savollar.map((s, i) => (
          <div className="savol-blok" key={i}>
            <div className="savol-matni">
              {i + 1}. {s.savol}
              {natija && (
                <span className={`natija-belgi ${natija.natijalar[i] ? "togri" : "notogri"}`}>
                  {natija.natijalar[i] ? "✓" : "✗"}
                </span>
              )}
            </div>
            {s.variantlar && s.variantlar.length > 0 ? (
              s.variantlar.map((v) => (
                <label className="variant-qator" key={v}>
                  <input
                    type="radio"
                    name={`savol-${i}`}
                    disabled={!!natija}
                    checked={javoblar[i] === v}
                    onChange={() => javobniQoy(i, v)}
                  />
                  {v}
                </label>
              ))
            ) : (
              <input
                type="text"
                placeholder={t("javob_yozing")}
                disabled={!!natija}
                value={javoblar[i] || ""}
                onChange={(e) => javobniQoy(i, e.target.value)}
              />
            )}
          </div>
        ))}

        {!natija ? (
          <button className="tugma katta" style={{ marginTop: 14 }} onClick={yuborish} disabled={yuklanmoqda}>
            {yuklanmoqda ? t("tekshirilmoqda") : t("javoblarni_yuborish")}
          </button>
        ) : (
          <div className="umumiy-band" style={{ marginTop: 14 }}>
            <span className="u-ball">
              {natija.ball}/{natija.jami}
            </span>
            <div className="u-izoh">{t("natijangiz")}</div>
          </div>
        )}
        {xato && (
          <div className="xato-xabar" style={{ marginTop: 10 }}>
            {xato}
          </div>
        )}
      </div>
    </>
  );
}
