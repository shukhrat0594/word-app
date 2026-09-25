// Alohida guruh sahifasi — `/guruhlar/:id` (video-TZ 2026-09-25).
//
// Admin: "Jadvaldan guruh bosilganda SoffCRM'dagidek ko'rinishda bo'lsa,
// o'qituvchi uchun ham qulay bo'lardi." Avval jadvaldagi blok guruhlar
// RO'YXATINI ochib, kerakli guruhni pastda yoyib qo'yardi.
//
// Tuzilishi SoffCRM'dagidek: chapda guruh ma'lumoti va tezkor tugmalar,
// o'ngda davomat (oylar bo'yicha) va boshqa tablar, pastda o'quvchilar.

import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api.js";
import GuruhAzolari, { NarxManbasi } from "../GuruhAzolari.jsx";
import { GuruhOynasi, TalabaQoshishOynasi } from "../GuruhOynalari.jsx";
import GuruhTablari from "../GuruhTablari.jsx";
import { pul, sana } from "../format.js";
import { useI18n } from "../i18n.jsx";
import { useRuxsat } from "../profilContext.jsx";
import { useSorov } from "../soragich.js";

const KUNLAR = [
  "kun_dushanba", "kun_seshanba", "kun_chorshanba",
  "kun_payshanba", "kun_juma", "kun_shanba", "kun_yakshanba",
];

// A'zolar pastda doim ochiq — tablar orasida takrorlanmaydi.
const TABLAR = ["davomat", "baholar", "natijalar", "chegirmalar", "eslatmalar"];

function Maydon({ nomi, children }) {
  return (
    <div className="qator">
      <span className="kichik">{nomi}</span>
      <span>{children}</span>
    </div>
  );
}

export default function GuruhSahifasi() {
  const { id } = useParams();
  const guruhId = Number(id);
  const { t } = useI18n();
  const ruxsat = useRuxsat();
  const { malumot: g, yuklanmoqda, xato, yangila } = useSorov(`/api/crm/guruhlar/${guruhId}/boshqaruv/`);
  const [tahrir, setTahrir] = useState(false);
  const [qoshish, setQoshish] = useState(false);
  const [tabBuyrugi, setTabBuyrugi] = useState({ tab: undefined, n: 0 });
  const [azolarKaliti, setAzolarKaliti] = useState(0);
  const [amalXato, setAmalXato] = useState("");

  async function arxivla() {
    if (!window.confirm(g.faol ? t("guruh_arxivlash_tasdiq") : t("guruh_tiklash_tasdiq"))) return;
    setAmalXato("");
    try {
      await api(`/api/crm/guruhlar/${guruhId}/boshqaruv/`, { method: "PATCH", body: { faol: !g.faol } });
      yangila();
    } catch (e) {
      setAmalXato(e.message);
    }
  }

  if (yuklanmoqda && !g) return <p className="kichik">{t("yuklanmoqda")}</p>;
  if (xato) return <div className="xato">{xato}</div>;
  if (!g) return null;

  const oqituvchilar = g.oqituvchilar?.length
    ? g.oqituvchilar.map((o) => `${o.ism}${o.turi === "yordamchi" ? ` (${t("support_ustoz")})` : ""}`)
    : g.oqituvchi ? [g.oqituvchi] : [];

  return (
    <section>
      <Link className="havola" to="/guruhlar">← {t("guruhlar")}</Link>

      <div className="guruh-sahifa">
        {/* ── Chap ustun: guruh ma'lumoti ───────────────────────── */}
        <div className="karta guruh-malumot">
          <h1>{g.nomi} {!g.faol && <span className="holat holat-kutilayotgan">{t("arxiv")}</span>}</h1>
          <p className="kichik">👥 {t("talabalar_soni")}: <b>{g.talaba_soni}</b></p>

          {!g.sozlangan && (
            <p className="ogohlantirish">⚠ {t("guruh_sozlanmagan_izoh")}</p>
          )}

          <Maydon nomi={t("kurs")}>{g.daraja?.nomi || "—"}</Maydon>
          {g.baholash_tizimi && <Maydon nomi={t("baholash_tizimi")}>{g.baholash_tizimi}</Maydon>}

          <div>
            <span className="kichik">{t("dars_kunlari")}</span>
            {g.jadval.length ? (
              <table className="ixcham">
                <tbody>
                  {g.jadval.map((j, i) => (
                    <tr key={i}>
                      <td>{t(KUNLAR[j.hafta_kuni])}</td>
                      <td className="nowrap">{j.boshlanish_vaqti}–{j.tugash_vaqti}</td>
                      <td className="ongga">{j.xona || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p><span className="belgi rang-qarzdor">{t("sozlanmagan")}</span></p>
            )}
          </div>

          <div>
            <span className="kichik">{t("dars_beruvchi_oqituvchilar")}</span>
            {oqituvchilar.length ? oqituvchilar.map((o) => <div key={o}>🎓 {o}</div>) : <div>—</div>}
          </div>

          <Maydon nomi={t("kurs_davomiyligi")}>
            {g.boshlanish_sana || g.tugash_sana ? `${sana(g.boshlanish_sana)} – ${sana(g.tugash_sana)}` : "—"}
          </Maydon>
          <Maydon nomi={t("filial")}>{g.filial?.nomi || "—"}</Maydon>
          <Maydon nomi={t("narx")}>
            {g.narx ? `${pul(g.narx)} so'm` : "—"} <NarxManbasi manba={g.narx_manbasi} />
          </Maydon>

          {amalXato && <div className="xato">{amalXato}</div>}
          <div className="tezkor-amallar">
            {ruxsat("guruhlar.tahrirlash") && (
              <button className="tugma kichik-tugma" type="button" onClick={() => setTahrir(true)}>✎ {t("tahrirlash")}</button>
            )}
            {ruxsat("guruhlar.talaba_qoshish") && g.faol && (
              <button className="tugma kichik-tugma" type="button" onClick={() => setQoshish(true)}>
                ➕ {t("guruhga_oquvchi_qoshish")}
              </button>
            )}
            <button className="tugma tugma-sokin kichik-tugma" type="button"
                    onClick={() => setTabBuyrugi((x) => ({ tab: "eslatmalar", n: x.n + 1 }))}>
              📝 {t("eslatma_yozish")}
            </button>
            {ruxsat("guruhlar.tahrirlash") && (
              <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={arxivla}>
                🗄 {g.faol ? t("arxivlash") : t("arxivdan_chiqarish")}
              </button>
            )}
          </div>
        </div>

        {/* ── O'ng ustun: davomat va boshqa tablar ─────────────── */}
        <div className="karta guruh-tablar-karta">
          <GuruhTablari
            guruhId={guruhId}
            tablar={TABLAR}
            boshlangichTab={tabBuyrugi.tab}
            tabKaliti={tabBuyrugi.n}
            onOzgardi={yangila}
          />
        </div>
      </div>

      {/* ── Pastda: o'quvchilar ─────────────────────────────────── */}
      <div className="karta">
        <h2>{t("oquvchilar")}</h2>
        <GuruhAzolari key={azolarKaliti} guruhId={guruhId} guruhNomi={g.nomi} onOzgardi={yangila} />
      </div>

      {tahrir && (
        <GuruhOynasi guruh={g} onYopish={() => setTahrir(false)} onSaqlandi={yangila} />
      )}
      {qoshish && (
        <TalabaQoshishOynasi guruh={g} onYopish={() => setQoshish(false)}
                             onSaqlandi={() => { yangila(); setAzolarKaliti((k) => k + 1); }} />
      )}
    </section>
  );
}
