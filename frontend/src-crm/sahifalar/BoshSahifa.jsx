// Bosh sahifa — joriy oy sarhisobi va ogohlantirishlar.
//
// Ogohlantirishlar ATAYLAB eng tepada: narxi yoki jadvali yo'q guruhga
// hisob OCHILMAYDI, ya'ni u jimgina pul yo'qotadi. Admin buni o'zi
// sezmasligi kerak — tizim aytib turishi kerak.

import { Link } from "react-router-dom";

import { useFilial } from "../filialContext.jsx";
import JadvalSetka from "../JadvalSetka.jsx";
import { joriyOy, oyNomi, pul } from "../format.js";
import { useI18n } from "../i18n.jsx";
import { sorovSatri, useSorov } from "../soragich.js";

function Katak({ sarlavha, qiymat, sinf }) {
  return (
    <div className="katak">
      <span className="kichik">{sarlavha}</span>
      <b className={sinf}>{qiymat}</b>
    </div>
  );
}

export default function BoshSahifa() {
  const { t, til } = useI18n();
  const { tanlangan } = useFilial();
  const oy = joriyOy();

  const hisobot = useSorov("/api/crm/hisobot/" + sorovSatri({ oy, filial: tanlangan }));
  const ogohlar = useSorov("/api/crm/ogohlantirishlar/");
  // Qarzdorlar — bosh sahifada (2026-09-17, admin talabi). Joriy oyning
  // to'lanmagan hisoblari, eng katta qoldiq tepada.
  const qarzdorlar = useSorov("/api/crm/hisoblar/" + sorovSatri({ oy, filial: tanlangan }));

  const jami = hisobot.malumot?.jami;
  const ogohRoyxati = ogohlar.malumot || [];
  const qarzdorRoyxati = (qarzdorlar.malumot || [])
    .filter((h) => h.holat !== "tolandi")
    .sort((a, b) => Number(b.qoldiq) - Number(a.qoldiq));

  return (
    <section>
      <h1>{oyNomi(oy, til)}</h1>

      {hisobot.xato && <div className="xato">{hisobot.xato}</div>}

      <div className="kataklar">
        <Katak sarlavha={t("hisoblangan")} qiymat={pul(jami?.hisoblangan)} />
        <Katak sarlavha={t("olingan_pul")} qiymat={pul(jami?.olingan)} sinf="rang-tolandi" />
        <Katak sarlavha={t("chegirma")} qiymat={pul(jami?.chegirma)} />
        <Katak sarlavha={t("qarz")} qiymat={pul(jami?.qarz)} sinf="rang-qarzdor" />
        <Katak sarlavha={t("yigilish")} qiymat={`${jami?.yigilish_foizi ?? 0}%`} />
      </div>

      {/* Haftalik setka — SoffCRM'ning bosh sahifasidagi ko'rinish.
          Moliya kataklari tepada qoladi: 1-bosqich MOLIYA haqida va
          admin birinchi qaraydigan raqam aynan qarz. */}
      <div className="karta">
        <h2>{t("dars_jadvali")}</h2>
        <JadvalSetka />
      </div>

      <div className="karta">
        <div className="karta-sarlavha">
          <h2>{t("qarzdorlar_royxati")} <span className="kichik">({qarzdorRoyxati.length})</span></h2>
          <Link className="havola" to="/moliya?tab=qarzdorlar">{t("hammasini_korish")} →</Link>
        </div>
        {qarzdorlar.yuklanmoqda ? (
          <p className="kichik">{t("yuklanmoqda")}</p>
        ) : qarzdorRoyxati.length === 0 ? (
          <p className="kichik">✅ {t("yozuv_yoq")}</p>
        ) : (
          <ul className="qarzdor-royxat">
            {qarzdorRoyxati.slice(0, 10).map((h) => (
              <li key={h.id}>
                <span>
                  <Link className="havola" to={`/talabalar?talaba=${h.talaba_id}`}>{h.talaba}</Link>
                  <span className="kichik">{h.guruh}{h.filial ? ` · ${h.filial}` : ""}</span>
                </span>
                <span className="ongga">
                  <b className="rang-qarzdor">{pul(h.qoldiq)}</b>
                  <span className={`holat holat-${h.holat}`} style={{ marginInlineStart: 8 }}>{t(`holat_${h.holat}`)}</span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="karta">
        <h2>{t("ogohlantirishlar")}</h2>
        {/* Yuklanayotganda "hammasi joyida" DEYILMAYDI: bu pul haqidagi
            ogohlantirish, yolg'on tasalli bermasligi kerak. */}
        {ogohlar.yuklanmoqda ? (
          <p className="kichik">{t("yuklanmoqda")}</p>
        ) : ogohRoyxati.length === 0 ? (
          <p className="kichik">✅ {t("ogohlantirish_yoq")}</p>
        ) : (
          <>
            <p className="kichik">{t("ogohlantirish_izoh")}</p>
            <ul className="ogoh-royxat">
              {ogohRoyxati.map((o) => (
                <li key={o.guruh_id}>
                  <b>{o.guruh}</b> ({o.talaba_soni} {t("talabalar_soni").toLowerCase()}) —{" "}
                  <span className="rang-qarzdor">{o.sabablar.join(", ")}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </section>
  );
}
