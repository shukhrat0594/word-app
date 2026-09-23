// Bosh sahifa — joriy oy sarhisobi va ogohlantirishlar.
//
// Ogohlantirishlar ATAYLAB eng tepada: narxi yoki jadvali yo'q guruhga
// hisob OCHILMAYDI, ya'ni u jimgina pul yo'qotadi. Admin buni o'zi
// sezmasligi kerak — tizim aytib turishi kerak.

import { useState } from "react";
import { Link } from "react-router-dom";

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
const KORSATKICHLAR = [
  ["faol_lidlar", "🎯", "/lidlar"],
  ["guruhlar", "📚", "/guruhlar"],
  ["qolgan_qarz", "⚠️", "/moliya?tab=qarzdorlar", "pul"],
  ["qarzdorlar", "🔻", "/talabalar"],
  ["tolovi_yaqin", "⏰", "/moliya?tab=qarzdorlar"],
  ["faol_talabalar", "👤", "/talabalar"],
  ["jami_guruhdagi", "👥", "/talabalar"],
  ["sinov_darsida", "🧪", "/talabalar"],
  ["ketganlar", "🚪", null],
  ["oqituvchilar", "🧑‍🏫", "/xodimlar"],
  ["muzlatilgan", "❄️", "/talabalar"],
  ["yangi_lidlar_bugun", "🆕", "/lidlar"],
  ["yangi_guruhga_qabul", "⏳", "/lidlar"],
];

// Vaqti kelgan eslatmalar (video 09:05-09:26: "28-sanada soat 2 da
// eslatsin"). Faqat O'Z yozgan eslatmalari; bo'lmasa bo'lim ko'rinmaydi.
function VaqtiKelganEslatmalar() {
  const { t } = useI18n();
  const { malumot } = useSorov("/api/crm/eslatmalar/muddatli/");
  const royxat = malumot || [];
  if (!royxat.length) return null;
  return (
    <div className="karta">
      <h2>⏰ {t("vaqti_kelgan_eslatmalar")} <span className="kichik">({royxat.length})</span></h2>
      <ul className="qarzdor-royxat">
        {royxat.map((e) => (
          <li key={e.id}>
            <span>
              {e.lid_id && <Link className="havola" to="/lidlar">🎯 {e.lid}</Link>}
              {e.talaba_id && <Link className="havola" to={`/talabalar?talaba=${e.talaba_id}`}>👤 {e.talaba}</Link>}
              {e.guruh_id && <Link className="havola" to={`/guruhlar?guruh=${e.guruh_id}`}>📚 {e.guruh}</Link>}
              <span className="kichik">{e.matn}</span>
            </span>
            <span className={e.otgan ? "rang-qarzdor" : "rang-qisman"}>
              {new Date(e.eslatish_vaqti).toLocaleString(undefined, { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

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
  const ogohlar = useSorov(ruxsat("guruhlar") ? "/api/crm/ogohlantirishlar/" : null);
  // Qarzdorlar — bosh sahifada (2026-09-17, admin talabi). Joriy oyning
  // to'lanmagan hisoblari, eng katta qoldiq tepada.
  const qarzdorlar = useSorov(ruxsat("moliya") ? "/api/crm/hisoblar/" + sorovSatri({ oy, filial: tanlangan }) : null);

  const jami = hisobot.malumot?.jami;
  const ogohRoyxati = ogohlar.malumot || [];
  const qarzdorRoyxati = (qarzdorlar.malumot || [])
    .filter((h) => h.holat !== "tolandi")
    .sort((a, b) => Number(b.qoldiq) - Number(a.qoldiq));

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

      {ruxsat("moliya") && (
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
      )}

      {ruxsat("guruhlar") && (
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
      )}
    </section>
  );
}
