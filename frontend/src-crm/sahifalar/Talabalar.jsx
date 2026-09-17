// Talabalar (TZ 6.5) — ro'yxat va talaba kartasi.

import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import Eslatmalar from "../Eslatmalar.jsx";
import { useFilial } from "../filialContext.jsx";
import { useProfil } from "../profilContext.jsx";
import { balansMatn, balansSinfi, pul, sana, vaqt } from "../format.js";
import { api, apiFayluniYuklab } from "../api.js";
import { useI18n } from "../i18n.jsx";
import { sorovSatri, useSorov } from "../soragich.js";
import QaytarishOynasi from "../QaytarishOynasi.jsx";
import TolovOynasi from "../TolovOynasi.jsx";

const KUN_KALITLARI = [
  "kun_dushanba", "kun_seshanba", "kun_chorshanba",
  "kun_payshanba", "kun_juma", "kun_shanba", "kun_yakshanba",
];

// ── Darslar taqvimi ─────────────────────────────────────────────────

function Taqvim({ kunlar }) {
  const { t } = useI18n();
  if (!kunlar?.length) return <p className="kichik">{t("yozuv_yoq")}</p>;
  // Legenda ATAYLAB bor: rangli kataklar o'z-o'zidan tushunarli emas,
  // ayniqsa kulrang "kutilayotgan" — u qarz emas, hali kelmagan oy.
  const legenda = ["tolandi", "qisman", "qarzdor", "kutilayotgan"];

  return (
    <>
      <div className="taqvim">
        {kunlar.map((k) => (
          <span key={k.sana} className={`taqvim-kun holat-${k.holat}`} title={sana(k.sana)}>
            {String(k.sana).slice(8, 10)}
          </span>
        ))}
      </div>
      <div className="taqvim-legenda">
        {legenda.map((h) => (
          <span key={h}>
            <i className={`legenda-nuqta holat-${h}`} /> {t(`holat_${h}`)}
          </span>
        ))}
      </div>
    </>
  );
}

/** Bitta ko'rsatkich kartasi. Ma'lumot yo'q bo'lsa "—" chiqadi va
 *  rang berilmaydi — 0% deb ko'rsatish "yomon natija" degan yolg'on
 *  taassurot berardi. */
function Natija({ sarlavha, qiymat, foiz = false, sof = false, izoh = null }) {
  const bor = qiymat !== null && qiymat !== undefined;
  const sinf = !bor || sof ? "" : foizSinfi(foiz ? qiymat : qiymat * 10);
  return (
    <div className="katak">
      <span className="kichik">{sarlavha}</span>
      <b className={sinf}>
        {bor ? `${qiymat}${foiz ? "%" : ""}` : "—"}
      </b>
      {izoh && <span className="kichik">{izoh}</span>}
    </div>
  );
}

/** 80%+ yaxshi, 60%+ o'rtacha, pastda yomon. */
function foizSinfi(foiz) {
  if (foiz === null || foiz === undefined) return "";
  if (foiz >= 80) return "rang-tolandi";
  if (foiz >= 60) return "rang-qisman";
  return "rang-qarzdor";
}

// ── To'lovni tahrirlash oynasi (SoffCRM'dagi qalam) ────────────────

function TolovTahrirOynasi({ tolov, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const [summa, setSumma] = useState(String(Number(tolov.summa)));
  const [sanaQ, setSanaQ] = useState(String(tolov.sana).slice(0, 10));
  const [izoh, setIzoh] = useState(tolov.izoh || "");
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  async function saqla() {
    setXato("");
    setBand(true);
    try {
      await api(`/api/crm/tolov/${tolov.id}/`, {
        method: "PATCH",
        body: { summa, sana: sanaQ, izoh },
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
      <div className="karta oyna">
        <h2>{t("tolov_tahrirlash")}</h2>
        <p className="kichik">{tolov.turi_nomi} · {tolov.guruh} · {tolov.oy ? String(tolov.oy).slice(0, 7) : "—"}</p>
        <label>
          {t("summa")}
          <input type="number" min="0" step="1000" value={summa} onChange={(e) => setSumma(e.target.value)} />
        </label>
        <label>
          {t("sana")}
          <input type="date" value={sanaQ} onChange={(e) => setSanaQ(e.target.value)} />
        </label>
        <label>
          {t("izoh")}
          <input type="text" value={izoh} onChange={(e) => setIzoh(e.target.value)} />
        </label>
        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
          <button className="tugma" type="button" onClick={saqla} disabled={band}>{t("saqlash")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Talaba ma'lumotini tahrirlash (LMS API orqali) ──────────────────
//
// CRM saytga o'zi YOZMAYDI — LMS'ning `PATCH /api/talabalar/<id>/`
// endpointini chaqiradi (LMS Talabalar kartasi bilan aynan bir xil).
// Ma'lumot bitta joyda, admin kiritgani talabaga qulflanadi (LMS qoidasi).

const TAHRIR_MAYDONLARI = [
  ["ism", "talaba", "text"],
  ["telefon", "telefon", "text"],
  ["ota_ona_telefon", "ota_ona_telefon", "text"],
  ["tugilgan_sana", "tugilgan_sana", "date"],
  ["manba", "manba", "text"],
  ["izoh", "izoh_talaba", "text"],
];

function TalabaTahrirOynasi({ talaba, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const [forma, setForma] = useState(() => ({
    ism: talaba.ism || "",
    telefon: talaba.telefon || "",
    ota_ona_telefon: talaba.ota_ona_telefon || "",
    tugilgan_sana: talaba.tugilgan_sana || "",
    manba: talaba.manba || "",
    izoh: talaba.izoh || "",
  }));
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  async function saqla() {
    setXato("");
    setBand(true);
    try {
      await api(`/api/talabalar/${talaba.id}/`, { method: "PATCH", body: forma });
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
      <div className="karta oyna">
        <h2>{t("talaba_tahrirlash")}</h2>
        <p className="kichik">{t("saytga_yoziladi")}</p>
        {TAHRIR_MAYDONLARI.map(([kalit, tarjima, turi]) => (
          <label key={kalit}>
            {t(tarjima)}
            <input type={turi} value={forma[kalit]}
                   onChange={(e) => setForma((f) => ({ ...f, [kalit]: e.target.value }))} />
          </label>
        ))}
        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
          <button className="tugma" type="button" onClick={saqla} disabled={band}>{t("saqlash")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Talaba kartasi ──────────────────────────────────────────────────

function Karta({ talabaId, onOrqaga }) {
  const { t } = useI18n();
  const profil = useProfil();
  const { malumot, yuklanmoqda, xato, yangila } = useSorov(`/api/crm/talaba/${talabaId}/`);
  const [tolovHisobi, setTolovHisobi] = useState(null);
  const [qaytarishGuruhi, setQaytarishGuruhi] = useState(null);
  const [tahrirTolovi, setTahrirTolovi] = useState(null);
  const [tahrir, setTahrir] = useState(false);

  // To'lov tarixi — SoffCRM'dagidek BITTA ro'yxat: to'lovlar va
  // hisob-fakturalar ("Qarzdorlik") birga, guruh va sana filtri bilan.
  const [tarixGuruh, setTarixGuruh] = useState("");
  const [tarixSana, setTarixSana] = useState("");
  const tarix = useSorov(
    "/api/crm/tolov/" +
      sorovSatri({ talaba: talabaId, hisoblar: 1, guruh: tarixGuruh, dan: tarixSana, gacha: tarixSana })
  );
  const tarixQatorlari = tarix.malumot || [];

  function yangilaHammasi() {
    yangila();
    tarix.yangila();
  }

  async function tolovniOchir(id) {
    if (!window.confirm(t("tolov_ochirish_tasdiq"))) return;
    await api(`/api/crm/tolov/${id}/`, { method: "DELETE" });
    yangilaHammasi();
  }

  if (yuklanmoqda) return <p className="kichik">{t("yuklanmoqda")}</p>;
  if (xato) return <div className="xato">{xato}</div>;
  if (!malumot) return null;

  const talaba = malumot;

  return (
    <section>
      <button className="havola" type="button" onClick={onOrqaga}>← {t("talabalar")}</button>
      <div className="karta-sarlavha">
        <h1>{talaba.ism}</h1>
        {/* Tahrirlash — LMS'ning `PATCH /api/talabalar/<id>/` orqali
            (2026-09-17, Shuhrat: "CRM'da tahrirlansa LMS'ga yozilsin"). */}
        <button className="tugma tugma-sokin" type="button" onClick={() => setTahrir(true)}>
          ✎ {t("talaba_tahrirlash")}
        </button>
      </div>

      {/* Sayt ma'lumoti — LMS Talabalar kartasi bilan bir xil maydonlar. */}
      <div className="karta">
        <div className="qator">
          <span className="kichik">{t("login")}</span>
          <span>{talaba.username}</span>
        </div>
        <div className="qator">
          <span className="kichik">{t("telefon")}</span>
          <span>{talaba.telefon || "—"}</span>
        </div>
        <div className="qator">
          <span className="kichik">{t("ota_ona_telefon")}</span>
          <span>{talaba.ota_ona_telefon || "—"}</span>
        </div>
        <div className="qator">
          <span className="kichik">{t("tugilgan_sana")}</span>
          <span>{sana(talaba.tugilgan_sana)}</span>
        </div>
        <div className="qator">
          <span className="kichik">{t("manba")}</span>
          <span>{talaba.manba || "—"}</span>
        </div>
        <div className="qator">
          <span className="kichik">{t("izoh_talaba")}</span>
          <span>{talaba.izoh || "—"}</span>
        </div>
        <div className="qator">
          <span className="kichik">{t("umumiy_balans")}</span>
          <b className={balansSinfi(talaba.balans_jami)}>{balansMatn(talaba.balans_jami)}</b>
        </div>
      </div>

      {tahrir && (
        <TalabaTahrirOynasi talaba={talaba} onYopish={() => setTahrir(false)} onSaqlandi={yangila} />
      )}

      {/* Umumiy o'quv natijasi — LMS'da hosil bo'ladi, bu yerda faqat
          ko'rsatiladi (SoffCRM kartasidagi "Baho" o'rnida, lekin bitta
          son emas, to'rt ko'nikma bo'yicha). */}
      <div className="karta">
        <div className="karta-sarlavha">
          <h2>{t("tab_natijalar")}</h2>
          <span className="belgi">{t("faqat_oqish")}</span>
        </div>
        <div className="kataklar">
          <Natija sarlavha="Writing" qiymat={talaba.natijalar?.writing_band} />
          <Natija sarlavha="Speaking" qiymat={talaba.natijalar?.speaking_band} />
          <Natija sarlavha="Listening" qiymat={talaba.natijalar?.listening_foiz} foiz />
          <Natija sarlavha="Reading" qiymat={talaba.natijalar?.reading_foiz} foiz />
          <Natija sarlavha={t("mashqlar")} qiymat={talaba.natijalar?.mashq_soni} sof />
          <Natija
            sarlavha={t("davomat")}
            qiymat={talaba.natijalar?.davomat_foizi}
            foiz
            izoh={
              talaba.natijalar && talaba.natijalar.keldi + talaba.natijalar.kelmadi > 0
                ? `${talaba.natijalar.keldi}/${talaba.natijalar.keldi + talaba.natijalar.kelmadi}`
                : null
            }
          />
        </div>
      </div>

      {talaba.guruhlar.map((g) => {
        // Dars vaqti — barcha kunlarda bir xil bo'lsa bitta, bo'lmasa ro'yxat.
        const vaqtlar = [...new Set(g.jadval.map((j) => `${j.boshlanish_vaqti}-${j.tugash_vaqti}`))];
        return (
        <div className="karta" key={g.id}>
          {/* SoffCRM guruh kartasi: balans + holat tepada, keyin
              o'qituvchi, dars vaqti, kunlar, sanalar, keyingi to'lov/narx. */}
          <div className="karta-sarlavha">
            <div>
              <h2>{g.guruh}</h2>
              {g.oqituvchi && <p className="kichik">🎓 {g.oqituvchi}</p>}
            </div>
            <div className="ongga">
              <b className={balansSinfi(g.balans)}>{balansMatn(g.balans)}</b>
              <div><span className={`holat holat-${g.holat === "faol" ? "tolandi" : "kutilayotgan"}`}>{t(`holat_${g.holat}`)}</span></div>
            </div>
          </div>

          <div className="guruh-blok-maydonlar">
            <div>
              <span className="kichik">{t("dars_vaqti")}</span>
              {vaqtlar.length ? vaqtlar.join(", ") : "—"}
            </div>
            <div>
              <span className="kichik">{t("dars_kunlari")}</span>
              <div className="kun-chiplar">
                {g.jadval.length
                  ? [...new Set(g.jadval.map((j) => j.hafta_kuni))].map((k) => (
                      <span key={k} className="kun-chip">{t(KUN_KALITLARI[k])}</span>
                    ))
                  : "—"}
              </div>
            </div>
            <div>
              <span className="kichik">{t("boshlangan_sana")}</span>
              <span className="rang-tolandi">📅</span> {sana(g.boshlanish_sana)}
            </div>
            <div>
              <span className="kichik">{t("ochiriladigan_sana")}</span>
              <span className="rang-qarzdor">📅</span> {sana(g.tugash_sana)}
            </div>
            <div>
              <span className="kichik">{t("keyingi_tolov_sanasi")}</span>
              🕒 {sana(g.keyingi_tolov)}
            </div>
            <div>
              <span className="kichik">{t("tolov_narxi")}</span>
              <b className="rang-tolandi">{g.narx ? `${pul(g.narx)} so'm` : "—"}</b>
            </div>
          </div>

          <h3>{t("darslar_taqvimi")}</h3>
          <Taqvim kunlar={g.darslar_taqvimi} />

          <div className="oyna-tugmalar">
            <button className="tugma tugma-sokin" type="button"
                    onClick={() => setQaytarishGuruhi(g)}>
              {t("pul_qaytarish")}
            </button>
          </div>
        </div>
        );
      })}

      <div className="karta">
        <h2>{t("tab_eslatmalar")}</h2>
        <Eslatmalar talabaId={talaba.id} profilId={profil?.id} />
      </div>

      {/* To'lov tarixi — SoffCRM'dagidek BITTA jadval: to'lovlar va
          hisob-fakturalar ("Qarzdorlik") birga, ID / yaratilgan vaqt /
          amallar ustunlari, Excel, guruh va sana filtri bilan.
          Qarzdorlik qatorida "To'lov qilish", to'lov qatorida
          tahrirlash/o'chirish (faqat owner — backend ham tekshiradi). */}
      <div className="karta">
        <div className="karta-sarlavha">
          <h2>{t("tolov_tarixi")}</h2>
          <div className="filtrlar">
            <button className="tugma tugma-sokin kichik-tugma" type="button"
                    onClick={() => apiFayluniYuklab("/api/crm/eksport/" + sorovSatri({ talaba: talaba.id }))}>
              ⬇ Excel
            </button>
            <select value={tarixGuruh} onChange={(e) => setTarixGuruh(e.target.value)}>
              <option value="">{t("barcha_guruhlar")}</option>
              {talaba.guruhlar.map((g) => (
                <option key={g.guruh_id} value={g.guruh_id}>{g.guruh}</option>
              ))}
            </select>
            <label className="yonma">
              {t("tolov_sanasi")}
              <input type="date" value={tarixSana} onChange={(e) => setTarixSana(e.target.value)} />
            </label>
          </div>
        </div>
        {tarix.xato && <div className="xato">{tarix.xato}</div>}
        <div className="jadval-oram">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>{t("sana")}</th>
                <th>{t("qaysi_oy")}</th>
                <th>{t("turi")}</th>
                <th className="ongga">{t("summa")}</th>
                <th>{t("guruh")}</th>
                <th>{t("izoh")}</th>
                <th>{t("kim")}</th>
                <th>{t("yaratilgan_vaqt")}</th>
                <th>{t("amallar")}</th>
              </tr>
            </thead>
            <tbody>
              {tarixQatorlari.map((x) => {
                const hisobQatori = x.turi === "hisob";
                const hisob = hisobQatori ? talaba.hisoblar.find((h) => h.id === x.hisob_id) : null;
                return (
                  <tr key={x.id} className={hisobQatori ? "qator-hisob" : ""}>
                    <td>{x.id}</td>
                    <td className="nowrap">{sana(x.sana)}</td>
                    <td>{x.oy ? String(x.oy).slice(0, 7) : "—"}</td>
                    <td>
                      {hisobQatori
                        ? <span className={`holat holat-${x.holat}`}>{t(`holat_${x.holat}`)}</span>
                        : <span className={`holat ${x.turi === "tolov" ? "holat-tolandi" : "holat-kutilayotgan"}`}>{x.turi_nomi}</span>}
                    </td>
                    <td className={`ongga ${x.turi === "qaytarish" ? "rang-qarzdor" : ""}`}>
                      {x.turi === "qaytarish" ? "−" : ""}{pul(x.summa)}
                    </td>
                    <td>{x.guruh}</td>
                    <td>{x.izoh || "—"}</td>
                    <td>{x.kim || "—"}</td>
                    <td className="nowrap">{vaqt(x.vaqt)}</td>
                    <td className="amallar">
                      {hisobQatori && hisob && hisob.holat !== "tolandi" && (
                        <button className="tugma kichik-tugma" type="button"
                                onClick={() => setTolovHisobi({ ...hisob, talaba: talaba.ism })}>
                          {t("tolov_qilish")}
                        </button>
                      )}
                      {!hisobQatori && profil?.is_owner && (
                        <>
                          <button className="havola" type="button" title={t("tahrirlash")}
                                  onClick={() => setTahrirTolovi(x)}>✎</button>
                          <button className="havola rang-qarzdor" type="button" title={t("ochirish")}
                                  onClick={() => tolovniOchir(x.id)}>🗑</button>
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
              {!tarix.yuklanmoqda && tarixQatorlari.length === 0 && (
                <tr><td colSpan={10} className="bosh">{t("yozuv_yoq")}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {tolovHisobi && (
        <TolovOynasi
          hisob={tolovHisobi}
          onYopish={() => setTolovHisobi(null)}
          onSaqlandi={({ yopmasdan }) => {
            yangilaHammasi();
            if (!yopmasdan) setTolovHisobi(null);
          }}
        />
      )}
      {tahrirTolovi && (
        <TolovTahrirOynasi
          tolov={tahrirTolovi}
          onYopish={() => setTahrirTolovi(null)}
          onSaqlandi={yangilaHammasi}
        />
      )}
      {qaytarishGuruhi && (
        <QaytarishOynasi
          talabaId={talaba.id}
          talabaIsmi={talaba.ism}
          guruhId={qaytarishGuruhi.guruh_id}
          guruhNomi={qaytarishGuruhi.guruh}
          balans={qaytarishGuruhi.balans}
          onYopish={() => setQaytarishGuruhi(null)}
          onSaqlandi={yangilaHammasi}
        />
      )}
    </section>
  );
}

// ── Sahifa ──────────────────────────────────────────────────────────

export default function Talabalar() {
  const { t } = useI18n();
  const { tanlangan } = useFilial();
  const [qidiruv, setQidiruv] = useState("");
  const [holat, setHolat] = useState("");
  // `?talaba=ID` — LMS Talabalar kartasidagi "CRM'da ochish" va bosh
  // sahifadagi qarzdorlar ro'yxatidan kelganda karta darhol ochiladi.
  const [params, setParams] = useSearchParams();
  const [ochilgan, setOchilganAsl] = useState(() => Number(params.get("talaba")) || null);
  useEffect(() => {
    const id = Number(params.get("talaba"));
    if (id) setOchilganAsl(id);
  }, [params]);
  const setOchilgan = (id) => {
    setOchilganAsl(id);
    if (!id && params.get("talaba")) setParams({});
  };
  const [menyu, setMenyu] = useState(null);
  const [qaytarish, setQaytarish] = useState(null);

  // Ro'yxat `Hisob`dan EMAS, a'zoliklardan yig'iladi: sinov va
  // muzlatilgan talabaga hisob ochilmaydi, lekin ular ham ko'rinishi
  // kerak — aks holda admin ularni topa olmaydi va holatini
  // o'zgartira olmaydi.
  const { malumot, yuklanmoqda, xato, yangila } = useSorov(
    "/api/crm/talabalar/" + sorovSatri({ filial: tanlangan, q: qidiruv, holat })
  );

  // Holat SoffCRM'dagidek ro'yxatdan ham o'zgaradi (guruh kartasiga
  // kirmasdan). Backend `AzolikView` chiqish/muzlatishda joriy oyni
  // qayta hisoblaydi — bu yerda faqat chaqiriladi.
  async function holatOzgartir(azolikMoliyaId, yangiHolat) {
    await api(`/api/crm/azoliklar/${azolikMoliyaId}/`, { method: "PATCH", body: { holat: yangiHolat } });
    yangila();
  }

  if (ochilgan) return <Karta talabaId={ochilgan} onOrqaga={() => setOchilgan(null)} />;

  const royxat = malumot || [];

  return (
    <section>
      <h1>{t("talabalar")}</h1>

      <div className="filtrlar">
        <input placeholder={t("qidiruv")} value={qidiruv} onChange={(e) => setQidiruv(e.target.value)} />
        <select value={holat} onChange={(e) => setHolat(e.target.value)}>
          <option value="">{t("barcha_holatlar")}</option>
          {["sinov", "faol", "muzlatilgan"].map((h) => (
            <option key={h} value={h}>{t(`holat_${h}`)}</option>
          ))}
        </select>
        <span className="kichik">{royxat.length}</span>
      </div>

      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      <div className="karta jadval-oram">
        <table>
          <thead>
            <tr>
              <th>{t("talaba")}</th>
              <th>{t("telefon")}</th>
              <th>{t("guruhlar")} / {t("holat")}</th>
              <th className="ongga">{t("balans")}</th>
              <th className="ongga">{t("harakatlar")}</th>
            </tr>
          </thead>
          <tbody>
            {royxat.map((x) => (
              <tr key={x.id}>
                <td>
                  <button className="havola" type="button" onClick={() => setOchilgan(x.id)}>
                    {x.ism}
                  </button>
                </td>
                <td>{x.telefon || "—"}</td>
                <td>
                  {x.guruhlar.map((g) => (
                    <span key={g.azolik_moliya_id} className="guruh-belgi">
                      {g.guruh}
                      <select
                        value={g.holat}
                        className={g.holat === "faol" ? "rang-tolandi" : "rang-qarzdor"}
                        onChange={(e) => holatOzgartir(g.azolik_moliya_id, e.target.value)}
                      >
                        {["sinov", "faol", "muzlatilgan"].map((h) => (
                          <option key={h} value={h}>{t(`holat_${h}`)}</option>
                        ))}
                      </select>
                    </span>
                  ))}
                </td>
                <td className={`ongga ${balansSinfi(x.balans)}`}>{balansMatn(x.balans)}</td>
                <td className="ongga">
                  {/* ⋮ menyu — SoffCRM'dagi "Harakatlar" ustuni. */}
                  <span className="harakat-oram">
                    <button className="tugma tugma-sokin kichik-tugma" type="button"
                            aria-label={t("harakatlar")}
                            onClick={() => setMenyu(menyu === x.id ? null : x.id)}>
                      ⋮
                    </button>
                    {menyu === x.id && (
                      <div className="harakat-menyu" onMouseLeave={() => setMenyu(null)}>
                        <button type="button" onClick={() => { setMenyu(null); setOchilgan(x.id); }}>
                          📄 {t("kartani_ochish")}
                        </button>
                        <button type="button" onClick={() => { setMenyu(null); setOchilgan(x.id); }}>
                          💵 {t("tolov_qilish")}
                        </button>
                        {x.guruhlar.map((g) => (
                          <button key={g.azolik_moliya_id} type="button"
                                  onClick={() => { setMenyu(null); setQaytarish({ talaba: x, guruh: g }); }}>
                            ↩ {t("pul_qaytarish")} — {g.guruh}
                          </button>
                        ))}
                      </div>
                    )}
                  </span>
                </td>
              </tr>
            ))}
            {!yuklanmoqda && royxat.length === 0 && (
              <tr><td colSpan={5} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {qaytarish && (
        <QaytarishOynasi
          talabaId={qaytarish.talaba.id}
          talabaIsmi={qaytarish.talaba.ism}
          guruhId={qaytarish.guruh.guruh_id}
          guruhNomi={qaytarish.guruh.guruh}
          balans={qaytarish.talaba.balans}
          onYopish={() => setQaytarish(null)}
          onSaqlandi={yangila}
        />
      )}
    </section>
  );
}
