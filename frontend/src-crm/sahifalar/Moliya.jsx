// Moliya — uchta tab: Qarzdorlar, To'lovlar, Hisobot (TZ 6.3).

import { useState } from "react";

import { apiFayluniYuklab } from "../api.js";
import { useFilial } from "../filialContext.jsx";
import { balansMatn, balansSinfi, joriyOy, oyNomi, pul, sana, siljit } from "../format.js";
import { useI18n } from "../i18n.jsx";
import { sorovSatri, useSorov } from "../soragich.js";
import HisobQoshishOynasi from "../HisobQoshishOynasi.jsx";
import QaytarishOynasi from "../QaytarishOynasi.jsx";
import TolovOynasi from "../TolovOynasi.jsx";

const TABLAR = ["qarzdorlar", "tolovlar", "hisobot"];

function OyTanlash({ oy, setOy }) {
  const { til } = useI18n();
  return (
    <div className="oy-tanlash">
      <button className="tugma tugma-sokin" type="button" onClick={() => setOy(siljit(oy, -1))}>
        ‹
      </button>
      <b>{oyNomi(oy, til)}</b>
      <button className="tugma tugma-sokin" type="button" onClick={() => setOy(siljit(oy, 1))}>
        ›
      </button>
    </div>
  );
}

function Holat({ qiymat }) {
  const { t } = useI18n();
  return <span className={`holat holat-${qiymat}`}>{t(`holat_${qiymat}`)}</span>;
}

// ── Qarzdorlar ──────────────────────────────────────────────────────

function Qarzdorlar({ oy, setOy }) {
  const { t } = useI18n();
  const { tanlangan } = useFilial();
  const [holat, setHolat] = useState("");
  const [qidiruv, setQidiruv] = useState("");
  const [tolovHisobi, setTolovHisobi] = useState(null);
  const [qaytarishHisobi, setQaytarishHisobi] = useState(null);
  const [qolda, setQolda] = useState(false);

  const yol =
    "/api/crm/hisoblar/" + sorovSatri({ oy, filial: tanlangan, holat, q: qidiruv });
  const { malumot, yuklanmoqda, xato, yangila } = useSorov(yol);
  const qatorlar = malumot || [];

  return (
    <>
      <div className="filtrlar">
        <OyTanlash oy={oy} setOy={setOy} />
        <select value={holat} onChange={(e) => setHolat(e.target.value)}>
          <option value="">{t("barcha_holatlar")}</option>
          <option value="qarzdor">{t("holat_qarzdor")}</option>
          <option value="qisman">{t("holat_qisman")}</option>
          <option value="tolandi">{t("holat_tolandi")}</option>
        </select>
        <input
          placeholder={t("qidiruv")}
          value={qidiruv}
          onChange={(e) => setQidiruv(e.target.value)}
        />
        <button className="tugma tugma-sokin" type="button" onClick={() => setQolda(true)}>
          + {t("qolda_hisob")}
        </button>
        <button
          className="tugma tugma-sokin"
          type="button"
          onClick={() => apiFayluniYuklab("/api/crm/eksport/" + sorovSatri({ oy, filial: tanlangan, holat }))}
        >
          ⬇ Excel
        </button>
      </div>

      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      <div className="jadval-oram">
        <table>
          <thead>
            <tr>
              <th>{t("talaba")}</th>
              <th>{t("guruh")}</th>
              <th>{t("filial")}</th>
              <th className="ongga">{t("hisoblangan")}</th>
              <th className="ongga">{t("tolangan")}</th>
              <th className="ongga">{t("qoldiq")}</th>
              <th className="ongga">{t("balans")}</th>
              <th>{t("holat")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {qatorlar.map((q) => (
              <tr key={q.id}>
                <td>{q.talaba}</td>
                <td>{q.guruh}</td>
                <td>{q.filial || "—"}</td>
                <td className="ongga">
                  {pul(q.summa)}
                  {q.proporsional && <span className="belgi" title={t("proporsional_izoh")}>~</span>}
                </td>
                <td className="ongga">{pul(q.tolangan)}</td>
                <td className="ongga">{pul(q.qoldiq)}</td>
                <td className={`ongga ${balansSinfi(q.balans)}`}>{balansMatn(q.balans)}</td>
                <td><Holat qiymat={q.holat} /></td>
                <td className="amallar">
                  {q.holat !== "tolandi" && (
                    <button className="tugma kichik-tugma" type="button" onClick={() => setTolovHisobi(q)}>
                      {t("tolov_qilish")}
                    </button>
                  )}
                  <button
                    className="tugma tugma-sokin kichik-tugma"
                    type="button"
                    onClick={() => setQaytarishHisobi(q)}
                    title={t("pul_qaytarish")}
                  >
                    ↩
                  </button>
                </td>
              </tr>
            ))}
            {!yuklanmoqda && qatorlar.length === 0 && (
              <tr><td colSpan={9} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {tolovHisobi && (
        <TolovOynasi
          hisob={tolovHisobi}
          onYopish={() => setTolovHisobi(null)}
          onSaqlandi={({ yopmasdan }) => {
            yangila();
            // Chegirma tugmasi ko'rsatilayotgan bo'lsa oyna ochiq
            // qoladi, lekin jadvaldagi qiymat yangilanadi.
            if (!yopmasdan) setTolovHisobi(null);
          }}
        />
      )}
      {qaytarishHisobi && (
        <QaytarishOynasi
          talabaId={qaytarishHisobi.talaba_id}
          talabaIsmi={qaytarishHisobi.talaba}
          guruhId={qaytarishHisobi.guruh_id}
          guruhNomi={qaytarishHisobi.guruh}
          balans={qaytarishHisobi.balans}
          onYopish={() => setQaytarishHisobi(null)}
          onSaqlandi={yangila}
        />
      )}
      {qolda && (
        <HisobQoshishOynasi onYopish={() => setQolda(false)} onSaqlandi={yangila} />
      )}
    </>
  );
}

// ── To'lovlar tarixi ────────────────────────────────────────────────

function Tolovlar() {
  const { t } = useI18n();
  const [dan, setDan] = useState(`${joriyOy()}-01`);
  const [gacha, setGacha] = useState(new Date().toISOString().slice(0, 10));
  const [turi, setTuri] = useState("");
  // SoffCRM'da hisob-fakturalar ham shu ro'yxatda ko'rinadi — admin
  // ko'nikkan ko'rinish, shuning uchun standart bo'yicha yoqilgan.
  const [hisoblarBilan, setHisoblarBilan] = useState(true);

  const yol = "/api/crm/tolov/" + sorovSatri({ dan, gacha, turi, hisoblar: hisoblarBilan ? 1 : "" });
  const { malumot, yuklanmoqda, xato } = useSorov(yol);
  const qatorlar = malumot || [];

  return (
    <>
      <div className="filtrlar">
        <label className="yonma">
          {t("dan")}
          <input type="date" value={dan} onChange={(e) => setDan(e.target.value)} />
        </label>
        <label className="yonma">
          {t("gacha")}
          <input type="date" value={gacha} onChange={(e) => setGacha(e.target.value)} />
        </label>
        <select value={turi} onChange={(e) => setTuri(e.target.value)}>
          <option value="">{t("barcha_turlar")}</option>
          <option value="tolov">{t("turi_tolov")}</option>
          <option value="chegirma">{t("turi_chegirma")}</option>
          <option value="bonus">{t("turi_bonus")}</option>
          <option value="qaytarish">{t("turi_qaytarish")}</option>
        </select>
        <label className="yonma">
          <input
            type="checkbox"
            checked={hisoblarBilan}
            onChange={(e) => setHisoblarBilan(e.target.checked)}
          />
          {t("hisoblar_bilan")}
        </label>
      </div>

      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      <div className="jadval-oram">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>{t("sana")}</th>
              <th>{t("qaysi_oy")}</th>
              <th>{t("turi")}</th>
              <th className="ongga">{t("summa")}</th>
              <th>{t("talaba")}</th>
              <th>{t("guruh")}</th>
              <th>{t("izoh")}</th>
              <th>{t("kim")}</th>
            </tr>
          </thead>
          <tbody>
            {qatorlar.map((q) => (
              <tr key={q.id} className={q.turi === "hisob" ? "qator-hisob" : ""}>
                <td>{q.id}</td>
                <td>{sana(q.sana)}</td>
                <td>{q.oy ? String(q.oy).slice(0, 7) : "—"}</td>
                <td>{q.turi_nomi}</td>
                <td className={`ongga ${q.turi === "qaytarish" ? "rang-qarzdor" : ""}`}>
                  {q.turi === "qaytarish" ? "−" : ""}{pul(q.summa)}
                </td>
                <td>{q.talaba}</td>
                <td>{q.guruh}</td>
                <td>{q.izoh}</td>
                <td>{q.kim || "—"}</td>
              </tr>
            ))}
            {!yuklanmoqda && qatorlar.length === 0 && (
              <tr><td colSpan={9} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ── Hisobot ─────────────────────────────────────────────────────────

function Hisobot({ oy, setOy }) {
  const { t } = useI18n();
  const { tanlangan } = useFilial();
  const { malumot, yuklanmoqda, xato } = useSorov(
    "/api/crm/hisobot/" + sorovSatri({ oy, filial: tanlangan })
  );
  const qatorlar = malumot?.qatorlar || [];
  const jami = malumot?.jami;

  return (
    <>
      <div className="filtrlar">
        <OyTanlash oy={oy} setOy={setOy} />
      </div>

      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      <div className="jadval-oram">
        <table>
          <thead>
            <tr>
              <th>{t("filial")}</th>
              <th>{t("guruh")}</th>
              <th className="ongga">{t("talabalar")}</th>
              <th className="ongga">{t("hisoblangan")}</th>
              {/* "Olingan pul" — FAQAT haqiqiy to'lovlar. Chegirma
                  alohida ustunda, aks holda hisobot markaz olmagan
                  pulni daromad qilib ko'rsatardi. */}
              <th className="ongga">{t("olingan_pul")}</th>
              <th className="ongga">{t("chegirma")}</th>
              <th className="ongga">{t("bonus")}</th>
              <th className="ongga">{t("qaytarilgan")}</th>
              <th className="ongga">{t("qarz")}</th>
              <th className="ongga">{t("yigilish")}</th>
            </tr>
          </thead>
          <tbody>
            {qatorlar.map((q) => (
              <tr key={`${q.filial_id}-${q.guruh_id}`}>
                <td>{q.filial}</td>
                <td>{q.guruh}</td>
                <td className="ongga">{q.talaba_soni}</td>
                <td className="ongga">{pul(q.hisoblangan)}</td>
                <td className="ongga"><b>{pul(q.olingan)}</b></td>
                <td className="ongga">{pul(q.chegirma)}</td>
                <td className="ongga">{pul(q.bonus)}</td>
                <td className="ongga">{pul(q.qaytarilgan)}</td>
                <td className="ongga rang-qarzdor">{pul(q.qarz)}</td>
                <td className="ongga">{q.yigilish_foizi}%</td>
              </tr>
            ))}
            {!yuklanmoqda && qatorlar.length === 0 && (
              <tr><td colSpan={10} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
          {jami && qatorlar.length > 0 && (
            <tfoot>
              <tr>
                <td colSpan={3}><b>{t("jami")}</b></td>
                <td className="ongga"><b>{pul(jami.hisoblangan)}</b></td>
                <td className="ongga"><b>{pul(jami.olingan)}</b></td>
                <td className="ongga">{pul(jami.chegirma)}</td>
                <td className="ongga">{pul(jami.bonus)}</td>
                <td className="ongga">{pul(jami.qaytarilgan)}</td>
                <td className="ongga rang-qarzdor"><b>{pul(jami.qarz)}</b></td>
                <td className="ongga"><b>{jami.yigilish_foizi}%</b></td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </>
  );
}

// ── Sahifa ──────────────────────────────────────────────────────────

export default function Moliya() {
  const { t } = useI18n();
  const [tab, setTab] = useState("qarzdorlar");
  // Oy tanlovi Qarzdorlar va Hisobot tablari orasida UMUMIY: admin
  // odatda bitta oy ustida ishlaydi va tab almashtirganda qaytadan
  // tanlashi zerikarli bo'lardi.
  const [oy, setOy] = useState(joriyOy());

  return (
    <section>
      <h1>{t("moliya")}</h1>
      <div className="tablar">
        {TABLAR.map((x) => (
          <button
            key={x}
            type="button"
            className={tab === x ? "tab faol" : "tab"}
            onClick={() => setTab(x)}
          >
            {t(`tab_${x}`)}
          </button>
        ))}
      </div>

      <div className="karta">
        {tab === "qarzdorlar" && <Qarzdorlar oy={oy} setOy={setOy} />}
        {tab === "tolovlar" && <Tolovlar />}
        {tab === "hisobot" && <Hisobot oy={oy} setOy={setOy} />}
      </div>
    </section>
  );
}
