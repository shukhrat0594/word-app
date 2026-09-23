// Guruh kartasining ichki tablari: A'zolar · Davomat · Natijalar ·
// Chegirmalar · Eslatmalar.
//
// Davomat 2026-09-23 dan (video-TZ) CRM'dan ham BELGILANADI — yozuv
// o'sha LMS jadvaliga tushadi, ya'ni o'qituvchi ham, admin ham bitta
// yozuvni ko'radi. Natijalar FAQAT O'QISH: mashqlar saytda yechiladi.

import { useEffect, useState } from "react";

import Eslatmalar from "./Eslatmalar.jsx";
import { Baholar, Chegirmalar, DavomatJadvali } from "./GuruhOynalari.jsx";
import { useProfil } from "./profilContext.jsx";
import { useI18n } from "./i18n.jsx";
import { useSorov } from "./soragich.js";

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

const TABLAR = ["azolar", "davomat", "baholar", "natijalar", "chegirmalar", "eslatmalar"];

export default function GuruhTablari({ guruhId, Azolar, boshlangichTab, tabKaliti = 0, onOzgardi }) {
  const { t } = useI18n();
  const profil = useProfil();
  const [tab, setTab] = useState(boshlangichTab || "azolar");
  // Tashqaridan (tezkor amallar) tab o'zgartirilsa — shunga o'tamiz.
  useEffect(() => {
    if (boshlangichTab) setTab(boshlangichTab);
  }, [boshlangichTab, tabKaliti]);

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

      {tab === "azolar" && <Azolar />}
      {tab === "davomat" && <DavomatJadvali guruhId={guruhId} />}
      {tab === "baholar" && <Baholar guruhId={guruhId} />}
      {tab === "chegirmalar" && <Chegirmalar guruhId={guruhId} onOzgardi={onOzgardi} />}
      {tab === "natijalar" && <Natijalar guruhId={guruhId} />}
      {tab === "eslatmalar" && <Eslatmalar guruhId={guruhId} profilId={profil?.id} />}
    </div>
  );
}
