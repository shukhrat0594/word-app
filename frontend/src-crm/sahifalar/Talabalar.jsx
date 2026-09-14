// Talabalar (TZ 6.5) — ro'yxat va talaba kartasi.

import { useState } from "react";

import { useFilial } from "../filialContext.jsx";
import { balansMatn, balansSinfi, pul, sana } from "../format.js";
import { useI18n } from "../i18n.jsx";
import { sorovSatri, useSorov } from "../soragich.js";
import QaytarishOynasi from "../QaytarishOynasi.jsx";
import TolovOynasi from "../TolovOynasi.jsx";

const HAFTA = ["Du", "Se", "Chor", "Pay", "Ju", "Sha", "Yak"];

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
          talabaId={talaba.id}
          talabaIsmi={talaba.ism}
          guruhId={qaytarishGuruhi.guruh_id}
          guruhNomi={qaytarishGuruhi.guruh}
          balans={qaytarishGuruhi.balans}
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
  const [holat, setHolat] = useState("");
  const [ochilgan, setOchilgan] = useState(null);

  // Ro'yxat `Hisob`dan EMAS, a'zoliklardan yig'iladi: sinov va
  // muzlatilgan talabaga hisob ochilmaydi, lekin ular ham ko'rinishi
  // kerak — aks holda admin ularni topa olmaydi va holatini
  // o'zgartira olmaydi.
  const { malumot, yuklanmoqda, xato } = useSorov(
    "/api/crm/talabalar/" + sorovSatri({ filial: tanlangan, q: qidiruv, holat })
  );

  if (ochilgan) return <Karta talabaId={ochilgan} onOrqaga={() => setOchilgan(null)} />;

  const royxat = malumot || [];

  return (
    <section>
      <h1>{t("talabalar")}</h1>

      <div className="filtrlar">
        <input placeholder={t("qidiruv")} value={qidiruv} onChange={(e) => setQidiruv(e.target.value)} />
        <select value={holat} onChange={(e) => setHolat(e.target.value)}>
          <option value="">{t("barcha_holatlar")}</option>
          {["sinov", "faol", "muzlatilgan", "arxiv"].map((h) => (
            <option key={h} value={h}>{t(`holat_${h}`)}</option>
          ))}
        </select>
        <span className="kichik">{royxat.length}</span>
      </div>

      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      <div className="karta jadval-oram">
        <table>
          <thead>
            <tr>
              <th>{t("talaba")}</th>
              <th>{t("telefon")}</th>
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
                <td>{x.telefon || "—"}</td>
                <td>
                  {x.guruhlar.map((g) => (
                    <span key={g.azolik_moliya_id} className="guruh-belgi">
                      {g.guruh}
                      {g.holat !== "faol" && <i> ({t(`holat_${g.holat}`)})</i>}
                    </span>
                  ))}
                </td>
                <td className={`ongga ${balansSinfi(x.balans)}`}>{balansMatn(x.balans)}</td>
              </tr>
            ))}
            {!yuklanmoqda && royxat.length === 0 && (
              <tr><td colSpan={4} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
