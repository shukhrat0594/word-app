// Talabalar (TZ 6.5) — ro'yxat va talaba kartasi.

import { useState } from "react";

import { api } from "../api.js";
import { useFilial } from "../filialContext.jsx";
import { balansMatn, balansSinfi, pul, sana } from "../format.js";
import { useI18n } from "../i18n.jsx";
import { sorovSatri, useSorov } from "../soragich.js";
import TolovOynasi from "../TolovOynasi.jsx";

const HAFTA = ["Du", "Se", "Chor", "Pay", "Ju", "Sha", "Yak"];

// ── Pul qaytarish oynasi ────────────────────────────────────────────

function QaytarishOynasi({ talaba, guruh, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const [summa, setSumma] = useState("");
  const [sanaQiymat, setSana] = useState(new Date().toISOString().slice(0, 10));
  const [izoh, setIzoh] = useState("");
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  async function yubor() {
    if (!(Number(summa) > 0)) {
      setXato(t("summa_kerak"));
      return;
    }
    setBand(true);
    try {
      // `qaytarish` ATAYLAB oyga bog'lanmaydi — u umumiy hisob-kitob,
      // oy holatini o'zgartirmaydi, faqat balansdan chiqadi.
      await api("/api/crm/tolov/", {
        method: "POST",
        body: {
          talaba_id: talaba.id,
          guruh_id: guruh.guruh_id,
          summa: String(summa),
          turi: "qaytarish",
          sana: sanaQiymat,
          izoh,
        },
      });
      onSaqlandi();
      onYopish();
    } catch (e) {
      setXato(e.message || "Xato");
    } finally {
      setBand(false);
    }
  }

  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna">
        <h2>{t("pul_qaytarish")}</h2>
        <p className="kichik">{talaba.ism} · {guruh.guruh}</p>

        <label>
          {t("summa")}
          <input type="number" min="0" step="1000" value={summa}
                 onChange={(e) => setSumma(e.target.value)} autoFocus />
        </label>
        <label>
          {t("sana")}
          <input type="date" value={sanaQiymat} onChange={(e) => setSana(e.target.value)} />
        </label>
        <label>
          {t("izoh")}
          <input value={izoh} onChange={(e) => setIzoh(e.target.value)} maxLength={300} />
        </label>

        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
          <button className="tugma" type="button" onClick={yubor} disabled={band}>{t("saqlash")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Darslar taqvimi ─────────────────────────────────────────────────

function Taqvim({ kunlar }) {
  const { t } = useI18n();
  if (!kunlar?.length) return <p className="kichik">{t("yozuv_yoq")}</p>;
  return (
    <div className="taqvim">
      {kunlar.map((k) => (
        <span key={k.sana} className={`taqvim-kun holat-${k.holat}`} title={sana(k.sana)}>
          {String(k.sana).slice(8, 10)}
        </span>
      ))}
    </div>
  );
}

// ── Talaba kartasi ──────────────────────────────────────────────────

function Karta({ talabaId, onOrqaga }) {
  const { t } = useI18n();
  const { malumot, yuklanmoqda, xato, yangila } = useSorov(`/api/crm/talaba/${talabaId}/`);
  const [tolovHisobi, setTolovHisobi] = useState(null);
  const [qaytarishGuruhi, setQaytarishGuruhi] = useState(null);

  if (yuklanmoqda) return <p className="kichik">{t("yuklanmoqda")}</p>;
  if (xato) return <div className="xato">{xato}</div>;
  if (!malumot) return null;

  const talaba = malumot;

  return (
    <section>
      <button className="havola" type="button" onClick={onOrqaga}>← {t("talabalar")}</button>
      <h1>{talaba.ism}</h1>

      <div className="karta">
        <div className="qator">
          <span className="kichik">{t("telefon")}</span>
          <span>{talaba.telefon || "—"}</span>
        </div>
        <div className="qator">
          <span className="kichik">{t("ota_ona_telefon")}</span>
          <span>{talaba.ota_ona_telefon || "—"}</span>
        </div>
        <div className="qator">
          <span className="kichik">{t("umumiy_balans")}</span>
          <b className={balansSinfi(talaba.balans_jami)}>{balansMatn(talaba.balans_jami)}</b>
        </div>
      </div>

      {talaba.guruhlar.map((g) => (
        <div className="karta" key={g.id}>
          <div className="karta-sarlavha">
            <div>
              <h2>{g.guruh}</h2>
              <p className="kichik">
                {g.jadval.map((j) => `${HAFTA[j.hafta_kuni]} ${j.boshlanish_vaqti}`).join(", ") || "—"}
                {" · "}{t(`holat_${g.holat}`)}
                {" · "}{g.narx ? pul(g.narx) : "—"}
              </p>
            </div>
            <b className={balansSinfi(g.balans)}>{balansMatn(g.balans)}</b>
          </div>

          <h3>{t("darslar_taqvimi")}</h3>
          <Taqvim kunlar={g.darslar_taqvimi} />

          <div className="oyna-tugmalar">
            <button className="tugma tugma-sokin" type="button"
                    onClick={() => setQaytarishGuruhi(g)}>
              {t("pul_qaytarish")}
            </button>
          </div>
        </div>
      ))}

      <div className="karta">
        <h2>{t("tolov_tarixi")}</h2>
        <div className="jadval-oram">
          <table>
            <thead>
              <tr>
                <th>{t("sana")}</th>
                <th>{t("qaysi_oy")}</th>
                <th>{t("turi")}</th>
                <th className="ongga">{t("summa")}</th>
                <th>{t("guruh")}</th>
                <th>{t("izoh")}</th>
              </tr>
            </thead>
            <tbody>
              {talaba.tolovlar.map((x) => (
                <tr key={x.id}>
                  <td>{sana(x.sana)}</td>
                  <td>{x.oy ? String(x.oy).slice(0, 7) : "—"}</td>
                  <td>{x.turi_nomi}</td>
                  <td className={`ongga ${x.turi === "qaytarish" ? "rang-qarzdor" : ""}`}>
                    {x.turi === "qaytarish" ? "−" : ""}{pul(x.summa)}
                  </td>
                  <td>{x.guruh}</td>
                  <td>{x.izoh}</td>
                </tr>
              ))}
              {talaba.tolovlar.length === 0 && (
                <tr><td colSpan={6} className="bosh">{t("yozuv_yoq")}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="karta">
        <h2>{t("hisoblangan")}</h2>
        <div className="jadval-oram">
          <table>
            <thead>
              <tr>
                <th>{t("qaysi_oy")}</th>
                <th>{t("guruh")}</th>
                <th className="ongga">{t("summa")}</th>
                <th className="ongga">{t("tolangan")}</th>
                <th className="ongga">{t("qoldiq")}</th>
                <th>{t("holat")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {talaba.hisoblar.map((h) => (
                <tr key={h.id}>
                  <td>{String(h.oy).slice(0, 7)}</td>
                  <td>{h.guruh}</td>
                  <td className="ongga">{pul(h.summa)}</td>
                  <td className="ongga">{pul(h.tolangan)}</td>
                  <td className="ongga">{pul(h.qoldiq)}</td>
                  <td><span className={`holat holat-${h.holat}`}>{t(`holat_${h.holat}`)}</span></td>
                  <td>
                    {h.holat !== "tolandi" && (
                      <button className="tugma kichik-tugma" type="button"
                              onClick={() => setTolovHisobi({ ...h, talaba: talaba.ism })}>
                        {t("tolov_qilish")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {talaba.hisoblar.length === 0 && (
                <tr><td colSpan={7} className="bosh">{t("yozuv_yoq")}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {tolovHisobi && (
        <TolovOynasi
          hisob={tolovHisobi}
          onYopish={() => setTolovHisobi(null)}
          onSaqlandi={({ yopmasdan }) => {
            yangila();
            if (!yopmasdan) setTolovHisobi(null);
          }}
        />
      )}
      {qaytarishGuruhi && (
        <QaytarishOynasi
          talaba={talaba}
          guruh={qaytarishGuruhi}
          onYopish={() => setQaytarishGuruhi(null)}
          onSaqlandi={yangila}
        />
      )}
    </section>
  );
}

// ── Sahifa ──────────────────────────────────────────────────────────

export default function Talabalar() {
  const { t } = useI18n();
  const { tanlangan } = useFilial();
  const [qidiruv, setQidiruv] = useState("");
  const [ochilgan, setOchilgan] = useState(null);

  // Talabalar ro'yxati hisoblar jadvalidan yig'iladi: CRM'da talaba
  // MOLIYAVIY tomondan qiziq, ya'ni hisobi bo'lganlar. Hisobsiz
  // talabalar Guruhlar sahifasidagi a'zolar ro'yxatida ko'rinadi.
  const { malumot, yuklanmoqda, xato } = useSorov(
    "/api/crm/hisoblar/" + sorovSatri({ filial: tanlangan, q: qidiruv })
  );

  if (ochilgan) return <Karta talabaId={ochilgan} onOrqaga={() => setOchilgan(null)} />;

  const qatorlar = malumot || [];
  const talabalar = new Map();
  for (const q of qatorlar) {
    if (!q.talaba_id) continue;
    if (!talabalar.has(q.talaba_id)) {
      talabalar.set(q.talaba_id, {
        id: q.talaba_id, ism: q.talaba, balans: q.balans, guruhlar: new Set(),
      });
    }
    talabalar.get(q.talaba_id).guruhlar.add(q.guruh);
  }
  const royxat = [...talabalar.values()].sort((a, b) => a.ism.localeCompare(b.ism));

  return (
    <section>
      <h1>{t("talabalar")}</h1>

      <div className="filtrlar">
        <input placeholder={t("qidiruv")} value={qidiruv} onChange={(e) => setQidiruv(e.target.value)} />
      </div>

      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      <div className="karta jadval-oram">
        <table>
          <thead>
            <tr>
              <th>{t("talaba")}</th>
              <th>{t("guruhlar")}</th>
              <th className="ongga">{t("balans")}</th>
            </tr>
          </thead>
          <tbody>
            {royxat.map((x) => (
              <tr key={x.id}>
                <td>
                  <button className="havola" type="button" onClick={() => setOchilgan(x.id)}>
                    {x.ism}
                  </button>
                </td>
                <td>{[...x.guruhlar].join(", ")}</td>
                <td className={`ongga ${balansSinfi(x.balans)}`}>{balansMatn(x.balans)}</td>
              </tr>
            ))}
            {!yuklanmoqda && royxat.length === 0 && (
              <tr><td colSpan={3} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
