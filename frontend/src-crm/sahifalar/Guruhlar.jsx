// Guruhlar (TZ 6.4) — LMS'dagi guruhlar + CRM sozlamalari.
//
// Guruhning O'ZI (nomi, o'qituvchi, talabalar tarkibi) bu yerdan
// TAHRIRLANMAYDI: u LMS'ning ishi. Ikki joyda tahrirlash chalkashlik
// keltiradi va qaysi biri to'g'ri ekani bilinmay qoladi.

import { Fragment, useState } from "react";

import { api } from "../api.js";
import GuruhTablari from "../GuruhTablari.jsx";
import { useFilial } from "../filialContext.jsx";
import { balansMatn, balansSinfi, pul, sana } from "../format.js";
import { useI18n } from "../i18n.jsx";
import { sorovSatri, useSorov } from "../soragich.js";

const HAFTA = ["Du", "Se", "Chor", "Pay", "Ju", "Sha", "Yak"];

function NarxManbasi({ manba }) {
  const { t } = useI18n();
  if (!manba) return <span className="belgi rang-qarzdor">{t("narx_yoq")}</span>;
  const nomlar = { kurs: "narx_kursdan", guruh: "narx_guruhdan", talaba: "narx_talabadan" };
  return <span className="belgi">{t(nomlar[manba])}</span>;
}

// ── Guruh sozlamalari oynasi ────────────────────────────────────────

function SozlashOynasi({ guruh, filiallar, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const [filialId, setFilialId] = useState(guruh.filial?.id || "");
  const [narx, setNarx] = useState(guruh.narx_guruhga ?? "");
  const [boshlanish, setBoshlanish] = useState(guruh.boshlanish_sana || "");
  const [tugash, setTugash] = useState(guruh.tugash_sana || "");
  const [jadval, setJadval] = useState(
    guruh.jadval.length
      ? guruh.jadval.map((j) => ({ ...j }))
      : [{ hafta_kuni: 0, boshlanish_vaqti: "14:00", tugash_vaqti: "15:30" }]
  );
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);
  // Xonalar TANLANGAN filialga qarab filtrlanadi: boshqa filialning
  // xonasini tanlash mantiqsiz bo'lardi.
  const xonalar = useSorov(filialId ? `/api/crm/xonalar/${"?faqat_faol=1&filial="}${filialId}` : null);

  function bandOzgartir(i, maydon, qiymat) {
    setJadval((eski) => eski.map((b, j) => (i === j ? { ...b, [maydon]: qiymat } : b)));
  }

  async function saqla() {
    setXato("");
    setBand(true);
    try {
      await api(`/api/crm/guruhlar/${guruh.id}/moliya/`, {
        method: "PATCH",
        body: {
          filial_id: filialId || null,
          narx: narx === "" ? null : String(narx),
          boshlanish_sana: boshlanish || null,
          tugash_sana: tugash || null,
        },
      });
      await api(`/api/crm/guruhlar/${guruh.id}/jadval/`, {
        method: "PUT",
        body: { jadval },
      });
      onSaqlandi();
      onYopish();
    } catch (e) {
      setXato(e.message || "Xato");
    } finally {
      setBand(false);
    }
  }

  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna oyna-keng">
        <h2>{guruh.nomi}</h2>
        <p className="kichik">
          {guruh.daraja?.nomi || "—"} · {guruh.oqituvchi || "—"}
        </p>

        <label>
          {t("filial")}
          <select value={filialId} onChange={(e) => setFilialId(e.target.value)}>
            <option value="">—</option>
            {filiallar.map((f) => (
              <option key={f.id} value={f.id}>{f.nomi}</option>
            ))}
          </select>
        </label>

        <label>
          {t("narx")} ({t("narx_guruhdan")})
          <input
            type="number"
            min="0"
            step="1000"
            value={narx}
            onChange={(e) => setNarx(e.target.value)}
            placeholder={guruh.narx ? String(guruh.narx) : ""}
          />
        </label>
        {/* Narx qayerdan kelayotgani KO'RSATILADI: aks holda admin
            kurs narxini o'zgartirib, nega bu guruhda ishlamaganini
            tushunmaydi. */}
        <p className="kichik">
          {t("hisoblangan")}: <b>{guruh.narx ? pul(guruh.narx) : "—"}</b>{" "}
          <NarxManbasi manba={guruh.narx_manbasi} />
        </p>

        <div className="ikki-ustun">
          <label>
            {t("boshlanish_sana")}
            <input type="date" value={boshlanish} onChange={(e) => setBoshlanish(e.target.value)} />
          </label>
          <label>
            {t("tugash_sana")}
            <input type="date" value={tugash} onChange={(e) => setTugash(e.target.value)} />
          </label>
        </div>

        <h3>{t("dars_kunlari")}</h3>
        {jadval.map((band_, i) => (
          <div key={i} className="jadval-qator">
            <select
              value={band_.hafta_kuni}
              onChange={(e) => bandOzgartir(i, "hafta_kuni", Number(e.target.value))}
            >
              {HAFTA.map((nomi, k) => (
                <option key={k} value={k}>{nomi}</option>
              ))}
            </select>
            <input
              type="time"
              value={band_.boshlanish_vaqti}
              onChange={(e) => bandOzgartir(i, "boshlanish_vaqti", e.target.value)}
            />
            <input
              type="time"
              value={band_.tugash_vaqti}
              onChange={(e) => bandOzgartir(i, "tugash_vaqti", e.target.value)}
            />
            <select
              value={band_.xona_id ?? ""}
              onChange={(e) => bandOzgartir(i, "xona_id", e.target.value || null)}
            >
              <option value="">{t("xonasiz")}</option>
              {(xonalar.malumot || []).map((x) => (
                <option key={x.id} value={x.id}>{x.nomi}</option>
              ))}
            </select>
            <button
              className="tugma tugma-sokin kichik-tugma"
              type="button"
              onClick={() => setJadval((eski) => eski.filter((_, j) => j !== i))}
            >
              ✕
            </button>
          </div>
        ))}
        <button
          className="tugma tugma-sokin kichik-tugma"
          type="button"
          onClick={() =>
            setJadval((eski) => [
              ...eski,
              { hafta_kuni: 0, boshlanish_vaqti: "14:00", tugash_vaqti: "15:30", xona_id: null },
            ])
          }
        >
          + {t("qoshish")}
        </button>

        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>
            {t("bekor")}
          </button>
          <button className="tugma" type="button" onClick={saqla} disabled={band}>
            {t("saqlash")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── A'zolar ro'yxati ────────────────────────────────────────────────

function Azolar({ guruhId, onOzgardi }) {
  const { t } = useI18n();
  const { malumot, yuklanmoqda, yangila } = useSorov(`/api/crm/guruhlar/${guruhId}/azoliklar/`);
  // Arxivdagilar standart bo'yicha YASHIRIN (SoffCRM'dagidek): ular
  // guruhda o'qimaydi, ro'yxatni to'ldirib admin chalg'itardi.
  const [arxivKorsat, setArxivKorsat] = useState(false);
  // Qidiruv va tartiblash — mijoz tomonida: guruhda 4-8 kishi, server
  // so'rovi shart emas. SoffCRM'da ham shu ikkisi ro'yxat tepasida.
  const [qidiruv, setQidiruv] = useState("");
  const [tartib, setTartib] = useState("ism");
  const hammasi = malumot || [];
  const arxivSoni = hammasi.filter((a) => a.holat === "arxiv").length;
  const HOLAT_TARTIBI = { faol: 0, sinov: 1, muzlatilgan: 2, arxiv: 3 };
  const azolar = (arxivKorsat ? hammasi : hammasi.filter((a) => a.holat !== "arxiv"))
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
                  {["sinov", "faol", "muzlatilgan", "arxiv"].map((h) => (
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
            </tr>
          ))}
          {azolar.length === 0 && (
            <tr><td colSpan={6} className="bosh">{t("yozuv_yoq")}</td></tr>
          )}
        </tbody>
      </table>
      {arxivSoni > 0 && (
        <p className="ongga">
          <button className="havola rang-qarzdor" type="button"
                  onClick={() => setArxivKorsat((x) => !x)}>
            {arxivKorsat ? t("arxivdagilarni_yashirish") : `${t("arxivdagilarni_korish")} (${arxivSoni})`}
          </button>
        </p>
      )}
    </div>
  );
}

// ── Sahifa ──────────────────────────────────────────────────────────

export default function Guruhlar() {
  const { t } = useI18n();
  const { tanlangan, filiallar } = useFilial();
  const [qidiruv, setQidiruv] = useState("");
  const [sozlanayotgan, setSozlanayotgan] = useState(null);
  const [ochilgan, setOchilgan] = useState(null);
  // Tezkor amal tugmasi qaysi tabni ochishini aytadi; `n` — bir xil tab
  // qayta bosilganda ham ishlashi uchun o'sib boruvchi raqam.
  const [tabBuyrugi, setTabBuyrugiAsl] = useState(null);
  const setTabBuyrugi = (b) => setTabBuyrugiAsl((eski) => ({ ...b, n: (eski?.n || 0) + 1 }));

  const { malumot, yuklanmoqda, xato, yangila } = useSorov(
    "/api/crm/guruhlar/" + sorovSatri({ filial: tanlangan, q: qidiruv })
  );
  const guruhlar = malumot || [];

  return (
    <section>
      <h1>{t("guruhlar")}</h1>

      <div className="filtrlar">
        <input placeholder={t("qidiruv")} value={qidiruv} onChange={(e) => setQidiruv(e.target.value)} />
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
                    <button className="tugma kichik-tugma" type="button" onClick={() => setSozlanayotgan(g)}>
                      {t("sozlash")}
                    </button>
                  </td>
                </tr>
                {ochilgan === g.id && (
                  <tr>
                    <td colSpan={9} className="ichki">
                      {/* Tezkor amallar — SoffCRM kartasidagi ikonkalar qatori.
                          "Talaba qo'shish" SAYTGA olib boradi: guruh tarkibi
                          LMS ishi, ikki joyda tahrirlash chalkashlik. */}
                      <div className="tezkor-amallar">
                        <button className="tugma kichik-tugma" type="button" onClick={() => setSozlanayotgan(g)}>
                          ⚙ {t("sozlash")}
                        </button>
                        <a className="tugma tugma-sokin kichik-tugma" href="/guruhlar">
                          ➕ {t("talaba_qoshish_lms")}
                        </a>
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

      {sozlanayotgan && (
        <SozlashOynasi
          guruh={sozlanayotgan}
          filiallar={filiallar}
          onYopish={() => setSozlanayotgan(null)}
          onSaqlandi={yangila}
        />
      )}
    </section>
  );
}
