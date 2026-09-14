// Hisobotlar — oylar kesimida dinamika.
//
// Moliya → Hisobot tabidan FARQI: u bitta oyni guruhlar kesimida
// ko'rsatadi ("shu oyda kim qarzdor"), bu esa bir necha oyni yonma-yon
// ("yig'ilish yaxshilanyaptimi"). Ikkalasi boshqa savolga javob beradi,
// shuning uchun alohida.

import { useState } from "react";

import { apiFayluniYuklab } from "../api.js";
import { useFilial } from "../filialContext.jsx";
import { oyNomi, oyQiymati, pul } from "../format.js";
import { useI18n } from "../i18n.jsx";
import { sorovSatri, useSorov } from "../soragich.js";

const ORALIQLAR = [6, 12, 24];

/** Yig'ilish foizi bo'yicha rang — 90%+ yaxshi, 70%+ o'rtacha, pastda yomon. */
function foizSinfi(foiz) {
  if (foiz >= 90) return "rang-tolandi";
  if (foiz >= 70) return "rang-qisman";
  return "rang-qarzdor";
}

export default function Hisobotlar() {
  const { t, til } = useI18n();
  const { tanlangan } = useFilial();
  const [oylar, setOylar] = useState(12);

  const { malumot, yuklanmoqda, xato } = useSorov(
    "/api/crm/hisobot/dinamika/" + sorovSatri({ oylar, filial: tanlangan })
  );
  const qatorlar = malumot || [];

  // Eng katta "hisoblangan" — ustunchalar shunga nisbatan chiziladi.
  const eng = Math.max(1, ...qatorlar.map((q) => Number(q.hisoblangan || 0)));

  const jami = qatorlar.reduce(
    (yigindi, q) => ({
      hisoblangan: yigindi.hisoblangan + Number(q.hisoblangan || 0),
      olingan: yigindi.olingan + Number(q.olingan || 0),
      chegirma: yigindi.chegirma + Number(q.chegirma || 0),
      qarz: yigindi.qarz + Number(q.qarz || 0),
    }),
    { hisoblangan: 0, olingan: 0, chegirma: 0, qarz: 0 }
  );
  const jamiFoiz = jami.hisoblangan
    ? Math.round((jami.olingan / jami.hisoblangan) * 1000) / 10
    : 0;

  return (
    <section>
      <h1>{t("hisobotlar")}</h1>

      <div className="filtrlar">
        {ORALIQLAR.map((x) => (
          <button
            key={x}
            type="button"
            className={oylar === x ? "tab faol" : "tab"}
            onClick={() => setOylar(x)}
          >
            {x} {t("oy")}
          </button>
        ))}
        <button
          className="tugma tugma-sokin"
          type="button"
          onClick={() => apiFayluniYuklab("/api/crm/eksport/" + sorovSatri({ filial: tanlangan }))}
        >
          ⬇ Excel
        </button>
      </div>

      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      <div className="karta jadval-oram">
        <table>
          <thead>
            <tr>
              <th>{t("qaysi_oy")}</th>
              <th className="ongga">{t("talabalar")}</th>
              <th className="ongga">{t("hisoblangan")}</th>
              <th className="ongga">{t("olingan_pul")}</th>
              <th className="ongga">{t("chegirma")}</th>
              <th className="ongga">{t("qarz")}</th>
              <th className="ongga">{t("yigilish")}</th>
              <th>{/* ustuncha */}</th>
            </tr>
          </thead>
          <tbody>
            {qatorlar.map((q) => (
              <tr key={String(q.oy)}>
                <td>{oyNomi(oyQiymati(q.oy), til)}</td>
                <td className="ongga">{q.talabalar}</td>
                <td className="ongga">{pul(q.hisoblangan)}</td>
                <td className="ongga"><b>{pul(q.olingan)}</b></td>
                <td className="ongga">{pul(q.chegirma)}</td>
                <td className="ongga rang-qarzdor">{pul(q.qarz)}</td>
                <td className={`ongga ${foizSinfi(q.yigilish_foizi)}`}>
                  <b>{q.yigilish_foizi}%</b>
                </td>
                <td className="ustuncha-katak">
                  {/* Oddiy ustuncha: kutubxonasiz, chunki bitta
                      grafik uchun CRM bundle'iga recharts qo'shish
                      arzimaydi (u LMS'da bor, lekin import qilmaymiz). */}
                  <span className="ustuncha-fon">
                    <span
                      className="ustuncha-hisoblangan"
                      style={{ width: `${(Number(q.hisoblangan) / eng) * 100}%` }}
                    >
                      <span
                        className="ustuncha-olingan"
                        style={{
                          width: q.hisoblangan
                            ? `${(Number(q.olingan) / Number(q.hisoblangan)) * 100}%`
                            : "0%",
                        }}
                      />
                    </span>
                  </span>
                </td>
              </tr>
            ))}
            {!yuklanmoqda && qatorlar.length === 0 && (
              <tr><td colSpan={8} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
          {qatorlar.length > 0 && (
            <tfoot>
              <tr>
                <td colSpan={2}><b>{t("jami")}</b></td>
                <td className="ongga"><b>{pul(jami.hisoblangan)}</b></td>
                <td className="ongga"><b>{pul(jami.olingan)}</b></td>
                <td className="ongga">{pul(jami.chegirma)}</td>
                <td className="ongga rang-qarzdor"><b>{pul(jami.qarz)}</b></td>
                <td className={`ongga ${foizSinfi(jamiFoiz)}`}><b>{jamiFoiz}%</b></td>
                <td />
              </tr>
            </tfoot>
          )}
        </table>
      </div>

      <p className="kichik">{t("hisobot_izoh")}</p>
    </section>
  );
}
