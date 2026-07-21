import { useEffect, useState } from "react";
import { api, apiBlobUrl } from "../api";
import { haqiqiyMatnniOl } from "../haqiqiyMatn";
import { useI18n } from "../i18n";
import { standartVaqt } from "../imtihonVaqt";
import { vaqtFormat } from "./ImtihonOtish";
import { Natija as SpeakingNatija } from "./Speaking";
import { Natija as WritingNatija } from "./Writing";

const TASK_NOMI = { task1: "Task 1", task2: "Task 2", part1: "Part 1", part2: "Part 2", part3: "Part 3" };

/** "IELTS testlari"dagi Writing/Speaking — R/L bilan bir xil manba
 * (`ImtihonTest`/`TestQismi`, admin/owner qo'shadi) va bir xil uslub:
 * taymer, ortga/tekshirish tasdiq dialoglari, beforeunload ogohlantirish.
 * Mavjud "Mashqlar" bo'limidagi (AI-import, hammaga ochiq) Writing/
 * Speaking'ga MUSTAQIL — 2026-07-21'da ataylab ajratildi. Bitta test —
 * Task1+Task2 (yoki Part1/2/3) BIRGA, haqiqiy IELTS sessiyasi kabi. */
export default function ImtihonYozGap({ bolim }) {
  const { t } = useI18n();
  const [royxat, setRoyxat] = useState(null);
  const [test, setTest] = useState(null);
  const [rasmUrllar, setRasmUrllar] = useState({});
  const [faolQism, setFaolQism] = useState(0);
  const [javoblar, setJavoblar] = useState({});
  const [natijalar, setNatijalar] = useState(null);
  const [umumiyBand, setUmumiyBand] = useState(null);
  const [xato, setXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [soniya, setSoniya] = useState(0);
  const [teskariMi, setTeskariMi] = useState(false);

  useEffect(() => {
    setTest(null);
    setNatijalar(null);
    setRoyxat(null);
    api(`/api/imtihon/testlar/?bolim=${bolim}`).then(setRoyxat).catch(() => {});
  }, [bolim]);

  useEffect(() => {
    if (!test || natijalar) return;
    const idT = setInterval(() => setSoniya((s) => s + 1), 1000);
    return () => clearInterval(idT);
  }, [test, natijalar]);

  useEffect(() => {
    function chiqishdanOldin(e) {
      if (!test || natijalar) return;
      e.preventDefault();
      e.returnValue = "";
    }
    window.addEventListener("beforeunload", chiqishdanOldin);
    return () => window.removeEventListener("beforeunload", chiqishdanOldin);
  }, [test, natijalar]);

  async function testniOch(id) {
    const t2 = await api(`/api/imtihon/testlar/${id}/`);
    setTest(t2);
    setJavoblar({});
    setNatijalar(null);
    setUmumiyBand(null);
    setXato("");
    setSoniya(0);
    setTeskariMi(false);
    setFaolQism(0);

    const rasmlar = {};
    for (const qism of t2.qismlar) {
      if (qism.rasm_url) {
        rasmlar[qism.id] = await apiBlobUrl(qism.rasm_url).catch(() => null);
      }
    }
    setRasmUrllar(rasmlar);
  }

  function javobniQoy(qismId, qiymat) {
    setJavoblar((prev) => ({ ...prev, [qismId]: qiymat }));
  }

  function ortgaQaytish() {
    if (!natijalar && !window.confirm(t("imtihon_ortga_tasdiq"))) return;
    setTest(null);
  }

  async function tekshir() {
    setXato("");
    for (const qism of test.qismlar) {
      const m = (javoblar[qism.id] || "").trim();
      if (m.split(/\s+/).filter(Boolean).length < 20) {
        setXato(`"${qism.sarlavha || TASK_NOMI[qism.tur]}" — ${t("matn_qisqa")}`);
        return;
      }
    }
    if (!window.confirm(t("imtihon_yakunlash_tasdiq"))) return;

    setYuklanmoqda(true);
    try {
      const res = await api(`/api/imtihon/testlar/${test.id}/yozgap-tekshirish/`, {
        method: "POST",
        body: { javoblar },
      });
      setNatijalar(res.natijalar);
      setUmumiyBand(res.umumiy_band);
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  const NatijaKomponenti = bolim === "writing" ? WritingNatija : SpeakingNatija;

  if (test) {
    const jamiVaqt = test.qismlar.reduce((s, q) => s + standartVaqt(bolim, q.tur), 0);
    const korsatilganVaqt = teskariMi ? Math.max(0, jamiVaqt - soniya) : soniya;
    const qism = test.qismlar[faolQism];
    const sozSoni = (javoblar[qism.id] || "").trim()
      ? javoblar[qism.id].trim().split(/\s+/).length
      : 0;

    return (
      <div>
        <div className="imtihon-asboblar">
          <button className="tugma ikkinchi" onClick={ortgaQaytish}>
            {t("ortga")}
          </button>
          <span
            className="imtihon-taymer"
            title={t("imtihon_taymer_almashtir")}
            onClick={() => setTeskariMi((v) => !v)}
          >
            ⏱ {vaqtFormat(korsatilganVaqt)}
          </span>
        </div>

        <h3 style={{ margin: "10px 0" }}>{test.name}</h3>

        <div className="tab-guruh" style={{ marginBottom: 12 }}>
          {test.qismlar.map((q, i) => (
            <button key={q.id} className={faolQism === i ? "aktiv" : ""} onClick={() => setFaolQism(i)}>
              {q.sarlavha || TASK_NOMI[q.tur] || `#${q.tartib}`}
              {natijalar && " ✓"}
            </button>
          ))}
        </div>

        {natijalar ? (
          <>
            {umumiyBand != null && (
              <div className="karta" style={{ marginBottom: 14 }}>
                <strong>{t("band_ball")}: {umumiyBand}</strong>
              </div>
            )}
            <div className="karta" style={{ marginBottom: 14 }}>
              <h4>{qism.sarlavha || TASK_NOMI[qism.tur]}</h4>
              <div className="mashq-passage">{haqiqiyMatnniOl(qism.matn)}</div>
              {rasmUrllar[qism.id] && (
                <img src={rasmUrllar[qism.id]} alt="" style={{ maxWidth: "100%", marginTop: 10 }} />
              )}
            </div>
            {natijalar.find((n) => n.qism_id === qism.id) && (
              <NatijaKomponenti natija={natijalar.find((n) => n.qism_id === qism.id).natija} />
            )}
          </>
        ) : (
          <>
            <div className="karta" style={{ marginBottom: 14 }}>
              <div className="mashq-passage">{haqiqiyMatnniOl(qism.matn)}</div>
              {rasmUrllar[qism.id] && (
                <img src={rasmUrllar[qism.id]} alt="" style={{ maxWidth: "100%", marginTop: 10 }} />
              )}
            </div>
            <div className="karta">
              <textarea
                value={javoblar[qism.id] || ""}
                onChange={(e) => javobniQoy(qism.id, e.target.value)}
                placeholder={bolim === "writing" ? t("insho_placeholder") : t("javob_placeholder")}
              />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
                <span className="izoh">
                  {sozSoni} {t("soz")}
                </span>
                <button className="tugma katta" onClick={tekshir} disabled={yuklanmoqda}>
                  {yuklanmoqda ? t("tekshirilmoqda") : t("tekshirish")}
                </button>
              </div>
              {xato && <div className="xato-xabar" style={{ marginTop: 10 }}>{xato}</div>}
            </div>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="karta">
      {royxat === null && <div className="yuklanmoqda">{t("yuklanmoqda")}</div>}
      {royxat && royxat.length === 0 && <span className="izoh">{t("imtihon_royxati_boshi")}</span>}
      {royxat && royxat.map((r) => (
        <div key={r.id} className="mashq-royxat-el" onClick={() => testniOch(r.id)}>
          <span>{r.name}</span>
        </div>
      ))}
    </div>
  );
}
