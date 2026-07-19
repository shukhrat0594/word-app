import { useEffect, useRef, useState } from "react";
import { api, apiBlobUrl } from "../api";
import { useI18n } from "../i18n";

function vaqtFormat(soniya) {
  const m = Math.floor(soniya / 60)
    .toString()
    .padStart(2, "0");
  const s = (soniya % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

/** Cambridge-uslubidagi to'liq IELTS testi — ro'yxat, uzluksiz test rejimi, yagona natija. */
export default function ImtihonOtish({ bolim }) {
  const { t } = useI18n();
  const [royxat, setRoyxat] = useState([]);
  const [test, setTest] = useState(null);
  const [audioUrllar, setAudioUrllar] = useState({});
  const [javoblar, setJavoblar] = useState({});
  const [natija, setNatija] = useState(null);
  const [xato, setXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [fokus, setFokus] = useState(false);
  const [masshtab, setMasshtab] = useState(100);
  const [soniya, setSoniya] = useState(0);
  const taymerRef = useRef(null);

  useEffect(() => {
    setTest(null);
    setNatija(null);
    api(`/api/imtihon/testlar/?bolim=${bolim}`).then(setRoyxat).catch(() => {});
  }, [bolim]);

  useEffect(() => {
    if (!test || natija) {
      clearInterval(taymerRef.current);
      return;
    }
    taymerRef.current = setInterval(() => setSoniya((s) => s + 1), 1000);
    return () => clearInterval(taymerRef.current);
  }, [test, natija]);

  async function ochish(id) {
    setXato("");
    setNatija(null);
    setJavoblar({});
    setSoniya(0);
    setFokus(false);
    setMasshtab(100);
    const t2 = await api(`/api/imtihon/testlar/${id}/`);
    setTest(t2);
    const urllar = {};
    for (const qism of t2.qismlar) {
      if (qism.audio_url) {
        urllar[qism.id] = await apiBlobUrl(qism.audio_url).catch(() => null);
      }
    }
    setAudioUrllar(urllar);
  }

  function javobniQoy(i, qiymat) {
    setJavoblar((prev) => ({ ...prev, [i]: qiymat }));
  }

  async function yuborish() {
    setYuklanmoqda(true);
    setXato("");
    try {
      const barchaSavollar = test.qismlar.flatMap((q) => q.savollar);
      const tartib = barchaSavollar.map((_, i) => javoblar[i] || "");
      const res = await api(`/api/imtihon/testlar/${test.id}/yechish/`, {
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

  function savolgaOt(i) {
    document.getElementById(`imtihon-savol-${i}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  if (!test) {
    return (
      <div className="karta">
        {royxat.length === 0 && <span className="izoh">{t("imtihon_royxati_boshi")}</span>}
        {royxat.map((r) => (
          <div key={r.id} className="mashq-royxat-el" onClick={() => ochish(r.id)}>
            <span>{r.name}</span>
          </div>
        ))}
      </div>
    );
  }

  let raqam = 0;
  const jamiSavollar = test.qismlar.reduce((s, q) => s + q.savollar.length, 0);

  const mazmun = (
    <div style={{ fontSize: `${masshtab}%` }}>
      <div className="imtihon-asboblar">
        <button className="tugma ikkinchi" onClick={() => setTest(null)}>
          {t("ortga")}
        </button>
        <span className="imtihon-taymer">⏱ {vaqtFormat(soniya)}</span>
        <button className="tugma ikkinchi" onClick={() => setFokus((v) => !v)}>
          {fokus ? t("fokusdan_chiqish") : t("fokus_rejimi")}
        </button>
        <div className="imtihon-zoom">
          <button onClick={() => setMasshtab((m) => Math.max(80, m - 10))}>-</button>
          <span className="izoh">{masshtab}%</span>
          <button onClick={() => setMasshtab((m) => Math.min(140, m + 10))}>+</button>
        </div>
      </div>

      {!natija && (
        <div className="imtihon-palitra">
          {Array.from({ length: jamiSavollar }, (_, i) => (
            <button
              key={i}
              className={javoblar[i] ? "javob-berilgan" : ""}
              onClick={() => savolgaOt(i)}
              type="button"
            >
              {i + 1}
            </button>
          ))}
        </div>
      )}

      <div className="karta">
        <h3>{test.name}</h3>
        {test.qismlar.map((qism) => {
          const boshlangichRaqam = raqam;
          raqam += qism.savollar.length;
          return (
            <div key={qism.id}>
              <div className="imtihon-qism-sarlavha">{qism.sarlavha}</div>
              {qism.yoriqnoma && <div className="imtihon-yoriqnoma">{qism.yoriqnoma}</div>}
              {bolim === "listening" ? (
                audioUrllar[qism.id] ? (
                  <audio controls src={audioUrllar[qism.id]} style={{ width: "100%", marginBottom: 14 }} />
                ) : (
                  <span className="izoh">{t("audio_yuklanmoqda")}</span>
                )
              ) : (
                qism.matn && <div className="mashq-passage">{qism.matn}</div>
              )}

              {qism.savollar.map((s, idx) => {
                const i = boshlangichRaqam + idx;
                return (
                  <div className="savol-blok" id={`imtihon-savol-${i}`} key={i}>
                    {s.guruh_boshi && <div className="imtihon-guruh-sarlavha">{s.guruh_boshi}</div>}
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
                            name={`imtihon-savol-${i}`}
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
                );
              })}
            </div>
          );
        })}

        {!natija ? (
          <button className="tugma katta" style={{ marginTop: 14 }} onClick={yuborish} disabled={yuklanmoqda}>
            {yuklanmoqda ? t("tekshirilmoqda") : t("imtihon_topshirish")}
          </button>
        ) : (
          <div className="umumiy-band" style={{ marginTop: 14 }}>
            <span className="u-ball">{natija.band != null ? Number(natija.band).toFixed(1) : "—"}</span>
            <div>
              <div style={{ fontWeight: 700 }}>{t("band_ball")}</div>
              <div className="u-izoh">
                {t("xom_ball")}: {natija.ball}/{natija.jami}
              </div>
            </div>
          </div>
        )}
        {xato && (
          <div className="xato-xabar" style={{ marginTop: 10 }}>
            {xato}
          </div>
        )}
      </div>
    </div>
  );

  return fokus ? <div className="imtihon-fokus-ustma">{mazmun}</div> : mazmun;
}
