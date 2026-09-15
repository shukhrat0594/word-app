// Guruh kartasining ichki tablari: A'zolar · Davomat · Natijalar.
//
// Davomat va Natijalar FAQAT O'QISH uchun. Ular LMS'da hosil bo'ladi
// (o'qituvchi davomat belgilaydi, talaba mashq yechadi) — CRM ularni
// faqat ko'rsatadi. Ikki joyda belgilash ikki xil raqam degani bo'lardi,
// va farq chiqqanda qaysi biri to'g'ri ekani bilinmay qolardi.

import { useState } from "react";

import Eslatmalar from "./Eslatmalar.jsx";
import { joriyOy, oyNomi, sana, siljit } from "./format.js";
import { useProfil } from "./profilContext.jsx";
import { useI18n } from "./i18n.jsx";
import { sorovSatri, useSorov } from "./soragich.js";

// ── Davomat ─────────────────────────────────────────────────────────

function Davomat({ guruhId }) {
  const { t, til } = useI18n();
  const [oy, setOy] = useState(joriyOy());
  const { malumot, yuklanmoqda, xato } = useSorov(
    `/api/crm/guruhlar/${guruhId}/davomat/` + sorovSatri({ oy })
  );

  const sanalar = malumot?.sanalar || [];
  const talabalar = malumot?.talabalar || [];

  return (
    <>
      <div className="filtrlar">
        <div className="oy-tanlash">
          <button className="tugma tugma-sokin" type="button" onClick={() => setOy(siljit(oy, -1))}>‹</button>
          <b>{oyNomi(oy, til)}</b>
          <button className="tugma tugma-sokin" type="button" onClick={() => setOy(siljit(oy, 1))}>›</button>
        </div>
        <span className="belgi">{t("faqat_oqish")}</span>
      </div>

      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      {!yuklanmoqda && sanalar.length === 0 && (
        <p className="kichik">{t("davomat_yoq")}</p>
      )}

      {sanalar.length > 0 && (
        <div className="jadval-oram">
          <table>
            <thead>
              <tr>
                <th>{t("talaba")}</th>
                {sanalar.map((s) => (
                  <th key={s} className="markazga" title={sana(s)}>
                    {String(s).slice(8, 10)}
                  </th>
                ))}
                <th className="ongga">{t("keldi")}</th>
                <th className="ongga">{t("kelmadi")}</th>
              </tr>
            </thead>
            <tbody>
              {talabalar.map((x) => (
                <tr key={x.id}>
                  <td>{x.ism}</td>
                  {x.kunlar.map((holat, i) => (
                    <td key={sanalar[i]} className="markazga">
                      {holat === "keldi" && <span className="davomat-keldi">✓</span>}
                      {holat === "kelmadi" && <span className="davomat-kelmadi">✕</span>}
                      {!holat && <span className="davomat-yoq">·</span>}
                    </td>
                  ))}
                  <td className="ongga rang-tolandi">{x.keldi}</td>
                  <td className="ongga rang-qarzdor">{x.kelmadi}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

// ── Natijalar ───────────────────────────────────────────────────────

/** Foizni rangga bog'laydi — 80%+ yaxshi, 60%+ o'rtacha, pastda yomon. */
function foizSinfi(foiz) {
  if (foiz === null || foiz === undefined) return "";
  if (foiz >= 80) return "rang-tolandi";
  if (foiz >= 60) return "rang-qisman";
  return "rang-qarzdor";
}

function Natijalar({ guruhId }) {
  const { t } = useI18n();
  const { malumot, yuklanmoqda, xato } = useSorov(
    `/api/crm/guruhlar/${guruhId}/natijalar/`
  );
  const talabalar = malumot?.talabalar || [];

  return (
    <>
      <div className="filtrlar">
        <span className="belgi">{t("faqat_oqish")}</span>
        <span className="kichik">{t("natija_izoh")}</span>
      </div>

      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      <div className="jadval-oram">
        <table>
          <thead>
            <tr>
              <th>{t("talaba")}</th>
              <th className="ongga">Writing</th>
              <th className="ongga">Speaking</th>
              <th className="ongga">Listening</th>
              <th className="ongga">Reading</th>
              <th className="ongga">{t("mashqlar")}</th>
              <th className="ongga">{t("davomat")}</th>
            </tr>
          </thead>
          <tbody>
            {talabalar.map((x) => (
              <tr key={x.id}>
                <td>{x.ism}</td>
                <td className="ongga">
                  {x.writing_band ?? "—"}
                  {x.writing_soni > 0 && <i className="soni"> ×{x.writing_soni}</i>}
                </td>
                <td className="ongga">
                  {x.speaking_band ?? "—"}
                  {x.speaking_soni > 0 && <i className="soni"> ×{x.speaking_soni}</i>}
                </td>
                <td className={`ongga ${foizSinfi(x.listening_foiz)}`}>
                  {x.listening_foiz !== null ? `${x.listening_foiz}%` : "—"}
                </td>
                <td className={`ongga ${foizSinfi(x.reading_foiz)}`}>
                  {x.reading_foiz !== null ? `${x.reading_foiz}%` : "—"}
                </td>
                <td className="ongga">{x.mashq_soni}</td>
                <td className={`ongga ${foizSinfi(x.davomat_foizi)}`}>
                  {x.davomat_foizi !== null ? `${x.davomat_foizi}%` : "—"}
                  {x.keldi + x.kelmadi > 0 && (
                    <i className="soni"> {x.keldi}/{x.keldi + x.kelmadi}</i>
                  )}
                </td>
              </tr>
            ))}
            {!yuklanmoqda && talabalar.length === 0 && (
              <tr><td colSpan={7} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ── Tablar ──────────────────────────────────────────────────────────

const TABLAR = ["azolar", "davomat", "natijalar", "eslatmalar"];

export default function GuruhTablari({ guruhId, Azolar }) {
  const { t } = useI18n();
  const profil = useProfil();
  const [tab, setTab] = useState("azolar");

  return (
    <div className="guruh-tablari">
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

      {/* A'zolar tabi TAHRIRLANADI (holat, sana, narx) — u CRM'ning
          o'z ma'lumoti. Qolgan ikkitasi faqat o'qish. */}
      {tab === "azolar" && <Azolar />}
      {tab === "davomat" && <Davomat guruhId={guruhId} />}
      {tab === "natijalar" && <Natijalar guruhId={guruhId} />}
      {tab === "eslatmalar" && <Eslatmalar guruhId={guruhId} profilId={profil?.id} />}
    </div>
  );
}
