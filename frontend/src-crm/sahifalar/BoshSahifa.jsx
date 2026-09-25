// Bosh sahifa — joriy oy sarhisobi.
//
// Video-TZ (2026-09-25): "Qarzdorlar" ro'yxati va "Ogohlantirishlar"
// bloklari OLIB TASHLANDI — qarzdorlar "Qarzdorlar" kartochkasidan
// ochiladi, sozlanmagan guruhlar esa Guruhlar sahifasida ko'rsatiladi.
// Ogohlantirishdagi "saytda guruhdan chiqarilgan" yozuvi boshqa guruhga
// ko'chirilgan o'quvchini ham shunday deb ko'rsatib, adashtirardi.

import { useState } from "react";
import { Link } from "react-router-dom";

import { VaqtiKelganEslatmalar } from "../EslatmaXabarlari.jsx";
import { useFilial } from "../filialContext.jsx";
import JadvalSetka from "../JadvalSetka.jsx";
import { joriyOy, oyNomi, pul } from "../format.js";
import { useI18n } from "../i18n.jsx";
import { useRuxsat } from "../profilContext.jsx";
import { sorovSatri, useSorov } from "../soragich.js";

function Katak({ sarlavha, qiymat, sinf, ikon, havola }) {
  const ichi = (
    <>
      <span className="kichik">{ikon ? `${ikon} ` : ""}{sarlavha}</span>
      <b className={sinf}>{qiymat}</b>
    </>
  );
  return havola ? <Link className="katak katak-havola" to={havola}>{ichi}</Link> : <div className="katak">{ichi}</div>;
}

// SoffCRM bosh sahifasidagi 12 ta kartochka (video-TZ, 2026-09-23).
// Raqamlar ATAYLAB boshida yashirin ("Raqamlarni ko'rish"): bosh sahifa
// ko'pincha qabulxona ekranida ochiq turadi, pul raqamlari begona
// ko'zga tushmasin. Tanlov shu brauzerda eslab qolinadi.
//
// Kartochka bosilganda ro'yxat DARHOL shu filtr bilan ochiladi (video-TZ
// 2026-09-25): "Qarzdorlar" — faqat qarzdor o'quvchilar (avval Moliya'ga
// o'tib, to'laganlar ham chiqardi), "Sinov darsida" — sinovdagilar,
// "Shu oy ketganlar" — ketish hisoboti.
const KORSATKICHLAR = [
  ["faol_lidlar", "🎯", "/lidlar"],
  ["guruhlar", "📚", "/guruhlar"],
  ["qolgan_qarz", "⚠️", "/talabalar?filtr=qarzdor", "pul"],
  ["qarzdorlar", "🔻", "/talabalar?filtr=qarzdor"],
  ["tolovi_yaqin", "⏰", "/moliya?tab=qarzdorlar"],
  ["faol_talabalar", "👤", "/talabalar?holat=faol"],
  ["jami_guruhdagi", "👥", "/talabalar"],
  ["sinov_darsida", "🧪", "/talabalar?holat=sinov"],
  ["ketganlar", "🚪", "/hisobotlar?tab=ketganlar"],
  ["oqituvchilar", "🧑‍🏫", "/xodimlar"],
  ["muzlatilgan", "❄️", "/talabalar?holat=muzlatilgan"],
  ["yangi_lidlar_bugun", "🆕", "/lidlar"],
  ["yangi_guruhga_qabul", "⏳", "/lidlar"],
];

function yashirinOl() {
  try {
    return localStorage.getItem("crm_raqamlar_ochiq") !== "1";
  } catch {
    return true;
  }
}

function Korsatkichlar({ filial }) {
  const { t } = useI18n();
  const { malumot, xato } = useSorov("/api/crm/korsatkichlar/" + sorovSatri({ filial }));
  const [yashirin, setYashirinAsl] = useState(yashirinOl);
  function setYashirin(q) {
    setYashirinAsl(q);
    try {
      localStorage.setItem("crm_raqamlar_ochiq", q ? "0" : "1");
    } catch {
      // saqlanmasa ham ishlayveradi
    }
  }
  const qiymat = (k, tur) => {
    const q = malumot?.[k];
    if (q === null || q === undefined) return null;
    if (yashirin) return "•••";
    return tur === "pul" ? pul(q) : q;
  };
  return (
    <div className="karta">
      <div className="karta-sarlavha">
        <h2>{t("umumiy_holat")}</h2>
        <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={() => setYashirin(!yashirin)}>
          👁 {yashirin ? t("raqamlarni_korish") : t("raqamlarni_yashirish")}
        </button>
      </div>
      {xato && <div className="xato">{xato}</div>}
      <div className="kataklar">
        {KORSATKICHLAR.map(([k, ikon, havola, tur]) => {
          const q = qiymat(k, tur);
          if (q === null) return null;
          return <Katak key={k} sarlavha={t(`k_${k}`)} qiymat={q} ikon={ikon} havola={havola} />;
        })}
      </div>
      {malumot?.markaz_foydaliligi !== null && malumot?.markaz_foydaliligi !== undefined && (
        <p className={`foydalilik ${malumot.markaz_foydaliligi >= 0 ? "rang-tolandi" : "rang-qarzdor"}`}>
          {t("markaz_foydaliligi")}: <b>{yashirin ? "•••" : `${malumot.markaz_foydaliligi}%`}</b>
          <span className="kichik"> — {t("foydalilik_izoh")}</span>
        </p>
      )}
    </div>
  );
}

export default function BoshSahifa() {
  const { t, til } = useI18n();
  const { tanlangan } = useFilial();
  const ruxsat = useRuxsat();
  // Moliya bloki oyi (video 24:08: "Yilni / Oyni tanlang").
  const [oy, setOy] = useState(joriyOy());

  // Har bo'lim o'z ruxsatiga bo'ysunadi (video-TZ): kassir moliyani,
  // marketolog faqat lid sonlarini ko'radi. Ruxsatsiz so'rov yuborilmaydi.
  const hisobot = useSorov(ruxsat("hisobotlar") ? "/api/crm/hisobot/" + sorovSatri({ oy, filial: tanlangan }) : null);

  const jami = hisobot.malumot?.jami;

  return (
    <section>
      <h1>{oyNomi(joriyOy(), til)}</h1>

      {/* Umumiy holat — SoffCRM'dagi 12 ta kartochka. */}
      <Korsatkichlar filial={tanlangan} />

      <VaqtiKelganEslatmalar />

      {/* Moliya — alohida bo'lim (2026-09-20, admin talabi). */}
      {ruxsat("hisobotlar") && (
      <div className="karta">
        <div className="karta-sarlavha">
          <h2>{t("moliya_xulosasi")} — {oyNomi(oy, til)}</h2>
          <input type="month" value={oy} onChange={(e) => e.target.value && setOy(e.target.value)} aria-label={t("oy")} />
        </div>
        {hisobot.xato && <div className="xato">{hisobot.xato}</div>}
        <div className="kataklar">
          <Katak sarlavha={t("hisoblangan")} qiymat={pul(jami?.hisoblangan)} />
          <Katak sarlavha={t("olingan_pul")} qiymat={pul(jami?.olingan)} sinf="rang-tolandi" />
          <Katak sarlavha={t("chegirma")} qiymat={pul(jami?.chegirma)} />
          <Katak sarlavha={t("qarz")} qiymat={pul(jami?.qarz)} sinf="rang-qarzdor" />
          <Katak sarlavha={t("yigilish")} qiymat={`${jami?.yigilish_foizi ?? 0}%`} />
        </div>
      </div>
      )}

      {/* Haftalik setka — SoffCRM'ning bosh sahifasidagi ko'rinish.
          Moliya kataklari tepada qoladi: 1-bosqich MOLIYA haqida va
          admin birinchi qaraydigan raqam aynan qarz. */}
      {ruxsat("bosh_sahifa.dars_jadvali") && (
        <div className="karta">
          <h2>{t("dars_jadvali")}</h2>
          <JadvalSetka />
        </div>
      )}
    </section>
  );
}
