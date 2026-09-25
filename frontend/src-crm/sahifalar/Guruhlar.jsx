// Guruhlar (TZ 6.4; video-TZ 2026-09-23) — guruhlarning ASOSIY joyi.
//
// 2026-09-23 dan guruh CRM'da yaratiladi va tahrirlanadi (nom, kurs,
// o'qituvchilar, jadval, tarkib). Saytda faqat o'qituvchi ishi qoladi
// (davomat, mashqlar) — ma'lumot baribir bitta jadvalda.

import { Fragment, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { api, apiFayluniYuklab } from "../api.js";
import GuruhAzolari, { NarxManbasi } from "../GuruhAzolari.jsx";
import { GuruhOynasi, TalabaQoshishOynasi } from "../GuruhOynalari.jsx";
import GuruhTablari from "../GuruhTablari.jsx";
import { useRuxsat } from "../profilContext.jsx";
import { useFilial } from "../filialContext.jsx";
import { pul, sana } from "../format.js";
import { useI18n } from "../i18n.jsx";
import { sorovSatri, useSorov } from "../soragich.js";

const HAFTA = ["Du", "Se", "Chor", "Pay", "Ju", "Sha", "Yak"];

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
  // Eski havola `?guruh=ID` (eslatmalar, avvalgi xatcho'plar) — endi
  // alohida guruh sahifasiga (video-TZ 2026-09-25) yo'naltiriladi.
  const [params] = useSearchParams();
  const navigate = useNavigate();
  useEffect(() => {
    const id = Number(params.get("guruh"));
    if (id) navigate(`/guruhlar/${id}`, { replace: true });
  }, [params, navigate]);
  const [ochilgan, setOchilgan] = useState(null);
  // `?sozlanmagan=1` — bosh sahifadagi ogohlantirishdan: faqat sozlanmaganlar.
  const [sozlanmaganF, setSozlanmaganF] = useState(() => params.get("sozlanmagan") === "1");
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
    if (sozlanmaganF && g.sozlangan) return false;
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

  const [amalXato, setAmalXato] = useState("");

  async function arxivla(g) {
    if (!window.confirm(g.faol ? t("guruh_arxivlash_tasdiq") : t("guruh_tiklash_tasdiq"))) return;
    setAmalXato("");
    try {
      await api(`/api/crm/guruhlar/${g.id}/boshqaruv/`, { method: "PATCH", body: { faol: !g.faol } });
      yangila();
    } catch (e) {
      setAmalXato(e.message);
    }
  }

  return (
    <section>
      <div className="karta-sarlavha">
        <h1>{t("guruhlar")} <span className="belgi">{guruhlar.length}</span></h1>
        <div className="tezkor-amallar">
          <button className="tugma tugma-sokin" type="button"
                  onClick={() => apiFayluniYuklab("/api/crm/guruhlar/eksport/" + sorovSatri({ filial: tanlangan, arxiv: arxiv ? 1 : "" }))}>
            ⬇ Excel
          </button>
          {ruxsat("guruhlar.qoshish") && (
            <button className="tugma" type="button" onClick={() => setSozlanayotgan(null)}>+ {t("yangi_guruh")}</button>
          )}
        </div>
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
          <input type="checkbox" checked={sozlanmaganF} onChange={(e) => setSozlanmaganF(e.target.checked)} />{" "}
          {t("faqat_sozlanmagan")}
        </label>
        <label className="yonma">
          <input type="checkbox" checked={arxiv} onChange={(e) => setArxiv(e.target.checked)} /> {t("arxiv")}
        </label>
      </div>

      {(xato || amalXato) && <div className="xato">{xato || amalXato}</div>}
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
              <th>{t("support_ustoz")}</th>
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
                    {/* ▸ — shu yerda yoyish; nom — alohida guruh sahifasi. */}
                    <button className="havola" type="button" aria-label={t("yoyish")}
                            onClick={() => setOchilgan(ochilgan === g.id ? null : g.id)}>
                      {ochilgan === g.id ? "▾" : "▸"}
                    </button>{" "}
                    <Link className="havola" to={`/guruhlar/${g.id}`}>{g.nomi}</Link>
                  </td>
                  <td>{g.daraja?.nomi || "—"}</td>
                  <td>{g.oqituvchi || "—"}</td>
                  <td>{g.yordamchilar?.length ? g.yordamchilar.join(", ") : "—"}</td>
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
                    <td colSpan={10} className="ichki">
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
                        // ELEMENT uzatiladi, komponent emas: `() => <GuruhAzolari/>` har
                        // renderda yangi tur bo'lib, A'zolar holatini (qidiruv,
                        // yashirilgan ustunlar) tiklab, qayta yuklab yuborardi.
                        azolar={<GuruhAzolari guruhId={g.id} guruhNomi={g.nomi} onOzgardi={yangila} />}
                      />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {!yuklanmoqda && guruhlar.length === 0 && (
              <tr><td colSpan={10} className="bosh">{t("yozuv_yoq")}</td></tr>
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
