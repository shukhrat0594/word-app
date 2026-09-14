// Bosh sahifa — joriy oy sarhisobi va ogohlantirishlar.
//
// Ogohlantirishlar ATAYLAB eng tepada: narxi yoki jadvali yo'q guruhga
// hisob OCHILMAYDI, ya'ni u jimgina pul yo'qotadi. Admin buni o'zi
// sezmasligi kerak — tizim aytib turishi kerak.

import { useFilial } from "../filialContext.jsx";
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

  const jami = hisobot.malumot?.jami;
  const ogohRoyxati = ogohlar.malumot || [];

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
