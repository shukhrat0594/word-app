// Guruhlar (TZ 6.4; video-TZ 2026-09-23) — guruhlarning ASOSIY joyi.
//
// 2026-09-23 dan guruh CRM'da yaratiladi va tahrirlanadi (nom, kurs,
// o'qituvchilar, jadval, tarkib). Saytda faqat o'qituvchi ishi qoladi
// (davomat, mashqlar) — ma'lumot baribir bitta jadvalda.

import { Fragment, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api } from "../api.js";
import { GuruhOynasi, TalabaQoshishOynasi } from "../GuruhOynalari.jsx";
import GuruhTablari from "../GuruhTablari.jsx";
import { useRuxsat } from "../profilContext.jsx";
import { useFilial } from "../filialContext.jsx";
import { balansMatn, balansSinfi, pul, sana } from "../format.js";
import { useI18n } from "../i18n.jsx";
import { sorovSatri, useSorov } from "../soragich.js";

const HAFTA = ["Du", "Se", "Chor", "Pay", "Ju", "Sha", "Yak"];
const bugun = () => new Date().toISOString().slice(0, 10);

function NarxManbasi({ manba }) {
  const { t } = useI18n();
  if (!manba) return <span className="belgi rang-qarzdor">{t("narx_yoq")}</span>;
  const nomlar = { kurs: "narx_kursdan", guruh: "narx_guruhdan", talaba: "narx_talabadan" };
  return <span className="belgi">{t(nomlar[manba])}</span>;
}

// ── A'zolar ro'yxati ────────────────────────────────────────────────

function Azolar({ guruhId, onOzgardi }) {
  const { t } = useI18n();
  const ruxsat = useRuxsat();
  const { malumot, yuklanmoqda, yangila } = useSorov(`/api/crm/guruhlar/${guruhId}/azoliklar/`);
  // Guruhdan chiqarish (2026-09-23): endi CRM'da — chiqish sanasigacha
  // joriy oy qayta hisoblanadi, a'zolik o'chadi, pul tarixi qoladi.
  //
  // Qidiruv va tartiblash — mijoz tomonida: guruhda 4-8 kishi, server
  // so'rovi shart emas. SoffCRM'da ham shu ikkisi ro'yxat tepasida.
  const [qidiruv, setQidiruv] = useState("");
  const [tartib, setTartib] = useState("ism");
  const HOLAT_TARTIBI = { faol: 0, sinov: 1, muzlatilgan: 2, arxiv: 3 };
  const azolar = (malumot || [])
    .filter((a) => !qidiruv || `${a.talaba} ${a.telefon || ""}`.toLowerCase().includes(qidiruv.toLowerCase()))
    .sort((a, b) => {
      if (tartib === "balans") return Number(a.balans ?? 0) - Number(b.balans ?? 0);
      if (tartib === "sana") return String(a.boshlanish_sana || "").localeCompare(String(b.boshlanish_sana || ""));
      if (tartib === "holat") return HOLAT_TARTIBI[a.holat] - HOLAT_TARTIBI[b.holat];
      return String(a.talaba).localeCompare(String(b.talaba));
    });

  async function ozgartir(id, maydon, qiymat) {
    await api(`/api/crm/azoliklar/${id}/`, { method: "PATCH", body: { [maydon]: qiymat } });
    yangila();
    onOzgardi?.();
  }

  async function chiqar(a) {
    const sanaQ = window.prompt(`${a.talaba}: ${t("chiqarish_sanasi")}`, bugun());
    if (!sanaQ) return;
    await api(`/api/crm/guruhlar/${guruhId}/talabalar/?talaba=${a.talaba_id}&sana=${sanaQ}`, { method: "DELETE" });
    yangila();
    onOzgardi?.();
  }

  if (yuklanmoqda) return <p className="kichik">{t("yuklanmoqda")}</p>;

  return (
    <div className="jadval-oram">
      <div className="filtrlar">
        <input placeholder={t("qidiruv")} value={qidiruv} onChange={(e) => setQidiruv(e.target.value)} />
        <select value={tartib} onChange={(e) => setTartib(e.target.value)} aria-label={t("tartiblash")}>
          <option value="ism">{t("tartib_ism")}</option>
          <option value="balans">{t("tartib_balans")}</option>
          <option value="sana">{t("tartib_sana")}</option>
          <option value="holat">{t("tartib_holat")}</option>
        </select>
      </div>
      <table>
        <thead>
          <tr>
            <th>{t("talaba")}</th>
            <th>{t("telefon")}</th>
            <th>{t("holat")}</th>
            <th>{t("boshlanish_sana")}</th>
            <th>{t("narx")}</th>
            <th className="ongga">{t("balans")}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {azolar.map((a) => (
            <tr key={a.id}>
              <td>{a.talaba}</td>
              <td>{a.telefon || "—"}</td>
              <td>
                {/* Sinov va muzlatilgan talabaga hisob OCHILMAYDI —
                    shuning uchun holat aynan shu yerdan boshqariladi. */}
                <select value={a.holat} onChange={(e) => ozgartir(a.id, "holat", e.target.value)}>
                  {["sinov", "faol", "muzlatilgan"].map((h) => (
                    <option key={h} value={h}>{t(`holat_${h}`)}</option>
                  ))}
                </select>
              </td>
              <td>
                <input
                  type="date"
                  value={a.boshlanish_sana || ""}
                  onChange={(e) => ozgartir(a.id, "boshlanish_sana", e.target.value)}
                />
              </td>
              <td>
                {a.narx_talabaga ? pul(a.narx_talabaga) : pul(a.narx)}{" "}
                <NarxManbasi manba={a.narx_manbasi} />
              </td>
              <td className={`ongga ${balansSinfi(a.balans)}`}>{balansMatn(a.balans)}</td>
              <td>
                {ruxsat("guruhlar.talaba_qoshish") && (
                  <button className="havola rang-qarzdor" type="button" onClick={() => chiqar(a)}>
                    {t("guruhdan_chiqarish")}
                  </button>
                )}
              </td>
            </tr>
          ))}
          {azolar.length === 0 && (
            <tr><td colSpan={7} className="bosh">{t("yozuv_yoq")}</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ── Sahifa ──────────────────────────────────────────────────────────

export default function Guruhlar() {
  const { t } = useI18n();
  const ruxsat = useRuxsat();
  const { tanlangan } = useFilial();
  const [qidiruv, setQidiruv] = useState("");
  const [arxiv, setArxiv] = useState(false);
  // Video (17:24-17:37): filial, o'qituvchi, kurs bo'yicha filtr.
  // Ro'yxat kichik — mijoz tomonida filtrlanadi.
  const [oqituvchiF, setOqituvchiF] = useState("");
  const [kursF, setKursF] = useState("");
  const [kunF, setKunF] = useState("");
  // undefined — yopiq, null — yangi guruh, obyekt — tahrir.
  const [sozlanayotgan, setSozlanayotgan] = useState(undefined);
  const [talabaQoshish, setTalabaQoshish] = useState(null);
  // `?guruh=ID` — dars jadvalidagi blokdan kelganda shu guruh ochiq
  // turadi (2026-09-17).
  const [params] = useSearchParams();
  const [ochilgan, setOchilgan] = useState(() => Number(params.get("guruh")) || null);
  useEffect(() => {
    const id = Number(params.get("guruh"));
    if (id) setOchilgan(id);
  }, [params]);
  // Tezkor amal tugmasi qaysi tabni ochishini aytadi; `n` — bir xil tab
  // qayta bosilganda ham ishlashi uchun o'sib boruvchi raqam.
  const [tabBuyrugi, setTabBuyrugiAsl] = useState(null);
  const setTabBuyrugi = (b) => setTabBuyrugiAsl((eski) => ({ ...b, n: (eski?.n || 0) + 1 }));

  const { malumot, yuklanmoqda, xato, yangila } = useSorov(
    "/api/crm/guruhlar/" + sorovSatri({ filial: tanlangan, q: qidiruv, arxiv: arxiv ? 1 : "" })
  );
  const hammasi = malumot || [];
  const KUN_TOPLAMI = { toq: "0,2,4", juft: "1,3,5" };
  const guruhlar = hammasi.filter((g) => {
    if (oqituvchiF && g.oqituvchi !== oqituvchiF) return false;
    if (kursF && String(g.daraja?.id) !== kursF) return false;
    if (kunF) {
      const kunlar = [...new Set(g.jadval.map((j) => j.hafta_kuni))].sort().join(",");
      if (kunF === "boshqa" ? Object.values(KUN_TOPLAMI).includes(kunlar) : kunlar !== KUN_TOPLAMI[kunF]) return false;
    }
    return true;
  });
  const oqituvchiVariantlari = [...new Set(hammasi.map((g) => g.oqituvchi).filter(Boolean))].sort();
  const kursVariantlari = [...new Map(hammasi.filter((g) => g.daraja).map((g) => [g.daraja.id, g.daraja.nomi])).entries()];

  // Tahrir oynasi o'qituvchilar ro'yxatini ham ko'rsatadi — u guruhlar
  // ro'yxatida yo'q, shuning uchun to'liq yozuv alohida so'raladi.
  async function tahrirla(g) {
    setSozlanayotgan(await api(`/api/crm/guruhlar/${g.id}/boshqaruv/`));
  }

  async function arxivla(g) {
    if (!window.confirm(g.faol ? t("guruh_arxivlash_tasdiq") : t("guruh_tiklash_tasdiq"))) return;
    await api(`/api/crm/guruhlar/${g.id}/boshqaruv/`, { method: "PATCH", body: { faol: !g.faol } });
    yangila();
  }

  return (
    <section>
      <div className="karta-sarlavha">
        <h1>{t("guruhlar")} <span className="belgi">{guruhlar.length}</span></h1>
        {ruxsat("guruhlar.qoshish") && (
          <button className="tugma" type="button" onClick={() => setSozlanayotgan(null)}>+ {t("yangi_guruh")}</button>
        )}
      </div>

      <div className="filtrlar">
        <input placeholder={t("qidiruv")} value={qidiruv} onChange={(e) => setQidiruv(e.target.value)} />
        <select value={oqituvchiF} onChange={(e) => setOqituvchiF(e.target.value)} aria-label={t("oqituvchi")}>
          <option value="">{t("oqituvchi")}: {t("hammasi")}</option>
          {oqituvchiVariantlari.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
        <select value={kursF} onChange={(e) => setKursF(e.target.value)} aria-label={t("kurs")}>
          <option value="">{t("kurs")}: {t("hammasi")}</option>
          {kursVariantlari.map(([id, nomi]) => <option key={id} value={id}>{nomi}</option>)}
        </select>
        <select value={kunF} onChange={(e) => setKunF(e.target.value)} aria-label={t("dars_kunlari")}>
          <option value="">{t("dars_kunlari")}: {t("hammasi")}</option>
          {["toq", "juft", "boshqa"].map((k) => <option key={k} value={k}>{t(`kunlar_${k}`)}</option>)}
        </select>
        <label className="yonma">
          <input type="checkbox" checked={arxiv} onChange={(e) => setArxiv(e.target.checked)} /> {t("arxiv")}
        </label>
      </div>

      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      <div className="karta jadval-oram">
        <table>
          <thead>
            <tr>
              <th>{t("guruh")}</th>
              <th>{t("daraja")}</th>
              {/* O'qituvchi — SAYT ma'lumoti (`academics.Guruh.oqituvchi`).
                  CRM uni faqat ko'rsatadi, tahrirlamaydi. */}
              <th>{t("oqituvchi")}</th>
              <th>{t("filial")}</th>
              <th className="ongga">{t("talabalar_soni")}</th>
              <th className="ongga">{t("narx")}</th>
              <th>{t("dars_kunlari")}</th>
              {/* SoffCRM'dagi "Kurs davomiyligi: 01.12.2025 – 01.01.2027" */}
              <th>{t("kurs_davomiyligi")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {guruhlar.map((g) => (
              <Fragment key={g.id}>
                <tr className={g.sozlangan ? "" : "qator-ogoh"}>
                  <td>
                    <button className="havola" type="button"
                            onClick={() => setOchilgan(ochilgan === g.id ? null : g.id)}>
                      {ochilgan === g.id ? "▾" : "▸"} {g.nomi}
                    </button>
                  </td>
                  <td>{g.daraja?.nomi || "—"}</td>
                  <td>{g.oqituvchi || "—"}</td>
                  <td>{g.filial?.nomi || "—"}</td>
                  <td className="ongga">{g.talaba_soni}</td>
                  <td className="ongga">
                    {g.narx ? pul(g.narx) : "—"} <NarxManbasi manba={g.narx_manbasi} />
                  </td>
                  <td>
                    {g.jadval.length
                      ? g.jadval.map((j) => `${HAFTA[j.hafta_kuni]} ${j.boshlanish_vaqti}${j.xona ? ` · ${j.xona}` : ""}`).join(", ")
                      : <span className="belgi rang-qarzdor">{t("sozlanmagan")}</span>}
                  </td>
                  <td className="nowrap">
                    {g.boshlanish_sana || g.tugash_sana
                      ? `${sana(g.boshlanish_sana)} – ${sana(g.tugash_sana)}`
                      : "—"}
                  </td>
                  <td>
                    {ruxsat("guruhlar.tahrirlash") && (
                      <button className="tugma kichik-tugma" type="button" onClick={() => tahrirla(g)}>
                        {t("tahrirlash")}
                      </button>
                    )}
                  </td>
                </tr>
                {ochilgan === g.id && (
                  <tr>
                    <td colSpan={9} className="ichki">
                      {/* Tezkor amallar — SoffCRM kartasidagi ikonkalar qatori. */}
                      <div className="tezkor-amallar">
                        {ruxsat("guruhlar.tahrirlash") && (
                          <button className="tugma kichik-tugma" type="button" onClick={() => tahrirla(g)}>
                            ✎ {t("tahrirlash")}
                          </button>
                        )}
                        {ruxsat("guruhlar.talaba_qoshish") && (
                          <button className="tugma kichik-tugma" type="button" onClick={() => setTalabaQoshish(g)}>
                            ➕ {t("guruhga_oquvchi_qoshish")}
                          </button>
                        )}
                        {ruxsat("guruhlar.tahrirlash") && (
                          <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={() => arxivla(g)}>
                            🗄 {g.faol ? t("arxivlash") : t("arxivdan_chiqarish")}
                          </button>
                        )}
                        <button className="tugma tugma-sokin kichik-tugma" type="button"
                                onClick={() => setTabBuyrugi({ id: g.id, tab: "eslatmalar" })}>
                          📝 {t("eslatma_yozish")}
                        </button>
                        <button className="tugma tugma-sokin kichik-tugma" type="button"
                                onClick={() => setTabBuyrugi({ id: g.id, tab: "davomat" })}>
                          📅 {t("tab_davomat")}
                        </button>
                      </div>
                      <GuruhTablari
                        guruhId={g.id}
                        boshlangichTab={tabBuyrugi?.id === g.id ? tabBuyrugi.tab : undefined}
                        tabKaliti={tabBuyrugi?.id === g.id ? tabBuyrugi.n : 0}
                        onOzgardi={yangila}
                        Azolar={() => <Azolar guruhId={g.id} onOzgardi={yangila} />}
                      />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {!yuklanmoqda && guruhlar.length === 0 && (
              <tr><td colSpan={9} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {sozlanayotgan !== undefined && (
        <GuruhOynasi guruh={sozlanayotgan} onYopish={() => setSozlanayotgan(undefined)} onSaqlandi={yangila} />
      )}
      {talabaQoshish && (
        <TalabaQoshishOynasi guruh={talabaQoshish} onYopish={() => setTalabaQoshish(null)} onSaqlandi={yangila} />
      )}
    </section>
  );
}
