// Talabalar (TZ 6.5) — ro'yxat va talaba kartasi.

import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import Eslatmalar from "../Eslatmalar.jsx";
import { useFilial } from "../filialContext.jsx";
import { useProfil } from "../profilContext.jsx";
import { balansMatn, balansSinfi, joriyOy, oyNomi, pul, sana, siljit, vaqt } from "../format.js";
import { api, apiFaylYubor, apiFayluniYuklab } from "../api.js";
import { useI18n } from "../i18n.jsx";
import { sorovSatri, useSorov } from "../soragich.js";
import { TalabaQoshishOynasi } from "../GuruhOynalari.jsx";
import { useRuxsat } from "../profilContext.jsx";
import QaytarishOynasi from "../QaytarishOynasi.jsx";
import TolovOynasi from "../TolovOynasi.jsx";
import UsulTanlash from "../TolovUsuli.jsx";

const KUN_KALITLARI = [
  "kun_dushanba", "kun_seshanba", "kun_chorshanba",
  "kun_payshanba", "kun_juma", "kun_shanba", "kun_yakshanba",
];

// ── Darslar taqvimi ─────────────────────────────────────────────────

// Video (12:50): katak rangi — to'lov holati; burchakdagi belgi —
// davomat; ustiga olib borilsa "Holat / Davomat / Baho". Katakni bosish
// davomatni almashtiradi (keldi -> kelmadi -> bo'sh), o'ng tugma —
// "sababli". Yozuv o'sha guruh davomatiga tushadi (bitta manba).
const DAVOMAT_KETMA = [null, "keldi", "kelmadi"];

function Taqvim({ kunlar, sanoq, guruhId, talabaId, onOzgardi }) {
  const { t } = useI18n();
  const ruxsat = useRuxsat();
  const [xato, setXato] = useState("");
  if (!kunlar?.length) return <p className="kichik">{t("yozuv_yoq")}</p>;
  // Legenda ATAYLAB bor: rangli kataklar o'z-o'zidan tushunarli emas,
  // ayniqsa kulrang "kutilayotgan" — u qarz emas, hali kelmagan oy.
  const legenda = ["tolandi", "qisman", "qarzdor", "kutilayotgan"];
  const belgilaydi = ruxsat("guruhlar.davomat") && guruhId;

  async function belgila(k, holat) {
    setXato("");
    try {
      await api(`/api/crm/guruhlar/${guruhId}/davomat/`, {
        method: "POST", body: { talaba_id: talabaId, sana: k.sana, holat },
      });
      onOzgardi?.();
    } catch (e) {
      setXato(e.message);
    }
  }

  return (
    <>
      {sanoq && (
        <div className="taqvim-sanoq">
          <span className="holat holat-tolandi">{t("kelgan")}: {sanoq.keldi}</span>
          <span className="holat holat-qarzdor">{t("kelmagan")}: {sanoq.kelmadi}</span>
          <span className="holat holat-qisman">{t("sababli_kelmagan")}: {sanoq.sababli}</span>
          <span className="kichik">{t("qilinmagan")}: {sanoq.qilinmagan}</span>
        </div>
      )}
      <div className="taqvim">
        {kunlar.map((k) => {
          const bosiladi = belgilaydi && !k.kelajak && !k.qulf;
          const sarlavha = [
            sana(k.sana),
            `${t("holat")}: ${t(`holat_${k.holat}`)}`,
            `${t("davomat")}: ${k.davomat ? t(`davomat_${k.davomat}`) : "—"}`,
            `${t("baho")}: ${k.baho ?? "—"}`,
            bosiladi ? t("taqvim_bosish_izoh") : "",
          ].filter(Boolean).join("\n");
          return (
            <button
              key={k.sana}
              type="button"
              className={`taqvim-kun holat-${k.holat}${k.davomat ? ` davomat-belgi-${k.davomat}` : ""}`}
              title={sarlavha}
              disabled={!bosiladi}
              onClick={() => belgila(k, DAVOMAT_KETMA[(DAVOMAT_KETMA.indexOf(k.davomat ?? null) + 1) % DAVOMAT_KETMA.length])}
              onContextMenu={(e) => {
                if (!bosiladi) return;
                e.preventDefault();
                belgila(k, k.davomat === "sababli" ? null : "sababli");
              }}
            >
              {String(k.sana).slice(8, 10)}
            </button>
          );
        })}
      </div>
      {xato && <div className="xato">{xato}</div>}
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
  const [usul, setUsul] = useState(tolov.usul || "naqd");
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  async function saqla() {
    setXato("");
    setBand(true);
    try {
      await api(`/api/crm/tolov/${tolov.id}/`, {
        method: "PATCH",
        body: { summa, sana: sanaQ, izoh, ...(["tolov", "qaytarish"].includes(tolov.turi) ? { usul } : {}) },
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
        {["tolov", "qaytarish"].includes(tolov.turi) && <UsulTanlash qiymat={usul} onChange={setUsul} />}
        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
          <button className="tugma" type="button" onClick={saqla} disabled={band}>{t("saqlash")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Qarzdorlikni tahrirlash (video 20:30) — faqat owner ─────────────

function HisobTahrirOynasi({ hisob, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const [summa, setSumma] = useState(String(Number(hisob.summa)));
  const [izoh, setIzoh] = useState(hisob.izoh || "");
  const [xato, setXato] = useState("");
  async function saqla() {
    setXato("");
    try {
      await api(`/api/crm/hisoblar/${hisob.id}/`, { method: "PATCH", body: { summa, izoh } });
      onSaqlandi();
      onYopish();
    } catch (e) {
      setXato(e.message || "Xato");
    }
  }
  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna">
        <h2>{t("qarzdorlikni_tahrirlash")}</h2>
        <p className="kichik">{hisob.guruh} · {String(hisob.oy).slice(0, 7)}</p>
        <label>{t("summa")}<input type="number" min="0" step="1000" value={summa} onChange={(e) => setSumma(e.target.value)} /></label>
        <label>{t("izoh")}<textarea rows={3} value={izoh} onChange={(e) => setIzoh(e.target.value)} maxLength={300} /></label>
        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
          <button className="tugma" type="button" onClick={saqla}>{t("saqlash")}</button>
        </div>
      </div>
    </div>
  );
}

// ── O'quvchi tarixi (SoffCRM "O'QUVCHI TARIX" tabi) ─────────────────

function TalabaTarixi({ talabaId }) {
  const { t } = useI18n();
  const { malumot, yuklanmoqda } = useSorov(`/api/crm/talaba/${talabaId}/tarix/`);
  if (yuklanmoqda && !malumot) return <p className="kichik">{t("yuklanmoqda")}</p>;
  return (
    <ul className="eslatma-royxat">
      {(malumot || []).map((v, i) => (
        <li key={i}>
          <div className="eslatma-matn"><b>{v.turi}</b>{v.matn ? ` — ${v.matn}` : ""}</div>
          <div className="eslatma-past kichik">{v.kim || "—"} · {vaqt(v.vaqt)}</div>
        </li>
      ))}
      {(malumot || []).length === 0 && <li className="kichik">{t("yozuv_yoq")}</li>}
    </ul>
  );
}

// ── Excel orqali qo'shish ───────────────────────────────────────────

function ImportOynasi({ onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const [fayl, setFayl] = useState(null);
  const [natija, setNatija] = useState(null);
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);
  async function yubor() {
    setXato("");
    setBand(true);
    try {
      const fd = new FormData();
      fd.append("excel_fayl", fayl);
      const javob = await apiFaylYubor("/api/crm/talabalar/import/", fd);
      setNatija(javob);
      onSaqlandi();
    } catch (e) {
      setXato(e.message);
    } finally {
      setBand(false);
    }
  }
  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna oyna-keng">
        <h2>{t("excel_orqali_qoshish")}</h2>
        {natija ? (
          <>
            <p>✅ {t("qoshildi")}: {natija.qoshildi.length}</p>
            {natija.qoshildi.length > 0 && (
              <>
                <p className="kichik">{t("login_parol_eslatma")}</p>
                <ul className="login-royxat">
                  {natija.qoshildi.map((x) => (
                    <li key={x.username}><b>{x.ism}</b> — <code>{x.username}</code> / <code>{x.parol}</code></li>
                  ))}
                </ul>
              </>
            )}
            {natija.xatolar.length > 0 && (
              <ul className="xato">{natija.xatolar.map((x) => <li key={x.qator}>{x.qator}: {x.xato}</li>)}</ul>
            )}
          </>
        ) : (
          <>
            <p className="kichik">{t("excel_format_talaba")}</p>
            <input type="file" accept=".xlsx" onChange={(e) => setFayl(e.target.files?.[0] || null)} />
          </>
        )}
        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("yopish")}</button>
          {!natija && <button className="tugma" type="button" disabled={!fayl || band} onClick={yubor}>{t("yuklash")}</button>}
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

// SoffCRM'dagi "Manba" variantlari (2026-09-20, admin skrinshoti).
const MANBA_KALITLARI = [
  "manba_instagram", "manba_telegram", "manba_tavsiya", "manba_oldin_oqigan",
  "manba_banner", "manba_flayer", "manba_chatgpt", "manba_google",
];

// To'rtinchi element (bo'lsa) — <input list> uchun datalist id.
const TAHRIR_MAYDONLARI = [
  ["ism", "talaba", "text"],
  ["telefon", "telefon", "text"],
  ["ota_ona_telefon", "ota_ona_telefon", "text"],
  ["ota_ona_ismi", "ota_ona_ismi", "text"],
  ["tugilgan_sana", "tugilgan_sana", "date"],
  ["manba", "manba", "text", "manba-variantlari-crm"],
  ["izoh", "izoh_talaba", "text"],
];

function TalabaTahrirOynasi({ talaba, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const [forma, setForma] = useState(() => ({
    ism: talaba.ism || "",
    telefon: talaba.telefon || "",
    ota_ona_telefon: talaba.ota_ona_telefon || "",
    ota_ona_ismi: talaba.ota_ona_ismi || "",
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
        {TAHRIR_MAYDONLARI.map(([kalit, tarjima, turi, royxatId]) => (
          <label key={kalit}>
            {t(tarjima)}
            <input type={turi} value={forma[kalit]} list={royxatId || undefined}
                   onChange={(e) => setForma((f) => ({ ...f, [kalit]: e.target.value }))} />
          </label>
        ))}
        <datalist id="manba-variantlari-crm">
          {MANBA_KALITLARI.map((k) => (
            <option key={k} value={t(k)} />
          ))}
        </datalist>
        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
          <button className="tugma" type="button" onClick={saqla} disabled={band}>{t("saqlash")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Yangi o'quvchi (video-TZ, 2026-09-23) ───────────────────────────
//
// CRM endi talabaning ASOSIY kirish joyi: shu yerda yaratiladi (saytdagi
// login/parol ham), ixtiyoriy darhol guruhga qo'shiladi. Login va parol
// bo'sh qolsa — avtomatik, javobda BIR MARTA ko'rsatiladi.

function YangiTalabaOynasi({ onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const { tanlangan } = useFilial();
  const guruhlar = useSorov("/api/crm/guruhlar/" + sorovSatri({ filial: tanlangan }));
  const [f, setF] = useState({
    ism: "", telefon: "+998", ota_ona_telefon: "", ota_ona_ismi: "", tugilgan_sana: "", jins: "erkak",
    maktab: "", manba: "", izoh: "", login: "", parol: "",
    guruh_id: "", boshlanish_sana: new Date().toISOString().slice(0, 10), holat: "faol",
  });
  const [natija, setNatija] = useState(null);
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);
  const qiymat = (k) => ({ value: f[k], onChange: (e) => setF((x) => ({ ...x, [k]: e.target.value })) });

  async function saqla() {
    setXato("");
    setBand(true);
    try {
      const javob = await api("/api/crm/talaba-yaratish/", {
        method: "POST",
        body: { ...f, guruh_id: f.guruh_id || null },
      });
      setNatija(javob);
      onSaqlandi();
    } catch (e) {
      setXato(e.message || "Xato");
    } finally {
      setBand(false);
    }
  }

  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna oyna-keng">
        <h2>{t("yangi_oquvchi")}</h2>
        {natija ? (
          <>
            <p>✅ <b>{natija.ism}</b></p>
            <p className="kichik">{t("login_parol_eslatma")}</p>
            <div className="qator"><span className="kichik">{t("login")}</span><code>{natija.username}</code></div>
            <div className="qator"><span className="kichik">{t("parol")}</span><code>{natija.parol}</code></div>
            <div className="oyna-tugmalar">
              <button className="tugma" type="button" onClick={onYopish}>{t("yopish")}</button>
            </div>
          </>
        ) : (
          <>
            <label>{t("ism_familiya")}<input {...qiymat("ism")} autoFocus /></label>
            <div className="ikki-ustun">
              <label>{t("telefon")}<input {...qiymat("telefon")} /></label>
              <label>{t("tugilgan_sana")}<input type="date" {...qiymat("tugilgan_sana")} /></label>
            </div>
            <div className="ikki-ustun">
              <label>{t("ota_ona_telefon")}<input {...qiymat("ota_ona_telefon")} /></label>
              <label>{t("ota_ona_ismi")}<input {...qiymat("ota_ona_ismi")} /></label>
            </div>
            <div className="ikki-ustun">
              <label>{t("jinsi")}
                <select {...qiymat("jins")}>
                  <option value="erkak">{t("jins_erkak")}</option>
                  <option value="ayol">{t("jins_ayol")}</option>
                </select>
              </label>
              <label>{t("maktab")}<input {...qiymat("maktab")} /></label>
            </div>
            <div className="ikki-ustun">
              <label>{t("manba")}<input {...qiymat("manba")} list="manba-variantlari-crm" /></label>
              <label>{t("izoh_talaba")}<input {...qiymat("izoh")} /></label>
            </div>
            <datalist id="manba-variantlari-crm">
              {MANBA_KALITLARI.map((k) => <option key={k} value={t(k)} />)}
            </datalist>
            <h3>{t("guruh")} <span className="kichik">({t("ixtiyoriy")})</span></h3>
            <div className="ikki-ustun">
              <label>{t("guruh")}
                <select {...qiymat("guruh_id")}>
                  <option value="">—</option>
                  {(guruhlar.malumot || []).map((g) => <option key={g.id} value={g.id}>{g.nomi}</option>)}
                </select>
              </label>
              <label>{t("holat")}
                <select {...qiymat("holat")}>
                  <option value="faol">{t("holat_faol")}</option>
                  <option value="sinov">{t("holat_sinov")}</option>
                </select>
              </label>
            </div>
            {f.guruh_id && (
              <label>{t("guruhga_qoshilish_sanasi")}<input type="date" {...qiymat("boshlanish_sana")} /></label>
            )}
            <div className="ikki-ustun">
              <label>{t("login")}<input {...qiymat("login")} placeholder={t("avtomatik")} /></label>
              <label>{t("parol")}<input {...qiymat("parol")} placeholder={t("avtomatik")} /></label>
            </div>
            {xato && <div className="xato">{xato}</div>}
            <div className="oyna-tugmalar">
              <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
              <button className="tugma" type="button" onClick={saqla} disabled={band || !f.ism.trim()}>{t("saqlash")}</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ── Beyjik (SoffCRM "Beyjik chiqarish") ─────────────────────────────
//
// Chop etiladigan kartochka: ism, ID, login, guruhlar. QR-kod YO'Q —
// loyihada QR kutubxonasi yo'q va tashqi servisga talaba ma'lumotini
// yuborish maxfiylikka zid (hisobotdagi qaror).

function beyjikChiqar(talaba, markazNomi) {
  const oyna = window.open("", "_blank", "width=420,height=600");
  if (!oyna) return;
  const xavfsiz = (m) => String(m ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const guruhlar = talaba.guruhlar.map((g) => `<li>${xavfsiz(g.guruh)}${g.oqituvchi ? ` — ${xavfsiz(g.oqituvchi)}` : ""}</li>`).join("");
  oyna.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${xavfsiz(talaba.ism)}</title>
<style>body{font-family:system-ui,sans-serif;margin:0;padding:24px}
.b{border:2px solid #4f46e5;border-radius:16px;padding:24px;width:320px;text-align:center}
.m{color:#4f46e5;font-weight:700;letter-spacing:.05em}.i{font-size:22px;font-weight:700;margin:16px 0 4px}
.id{color:#555}ul{list-style:none;padding:0;margin:12px 0 0;font-size:14px}
code{background:#f1f1f7;padding:2px 6px;border-radius:6px}@media print{button{display:none}}</style></head>
<body><div class="b"><div class="m">${xavfsiz(markazNomi || "")}</div><div class="i">${xavfsiz(talaba.ism)}</div>
<div class="id">ID: ${talaba.id} · <code>${xavfsiz(talaba.username)}</code></div><ul>${guruhlar}</ul></div>
<p><button onclick="print()">Chop etish</button></p></body></html>`);
  oyna.document.close();
}

function GuruhTanlabQoshish({ talaba, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const guruhlar = useSorov("/api/crm/guruhlar/");
  const [guruh, setGuruh] = useState(null);
  if (guruh) {
    return <TalabaQoshishOynasi guruh={guruh} tanlanganTalaba={talaba} onYopish={onYopish} onSaqlandi={onSaqlandi} />;
  }
  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna">
        <h2>{t("guruhga_qoshish")}</h2>
        <label>{t("guruh")}
          <select defaultValue="" onChange={(e) => setGuruh((guruhlar.malumot || []).find((g) => String(g.id) === e.target.value) || null)}>
            <option value="">{t("tanlang")}</option>
            {(guruhlar.malumot || []).map((g) => <option key={g.id} value={g.id}>{g.nomi}</option>)}
          </select>
        </label>
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Talaba kartasi ──────────────────────────────────────────────────

function Karta({ talabaId, onOrqaga }) {
  const { t, til } = useI18n();
  const profil = useProfil();
  const ruxsat = useRuxsat();
  // Dars taqvimi oyi (SoffCRM "Darslar taqvimi (sentyabr 2026)" ‹ ›).
  const [taqvimOy, setTaqvimOy] = useState(joriyOy());
  const { malumot, yuklanmoqda, xato, yangila } = useSorov(`/api/crm/talaba/${talabaId}/` + sorovSatri({ oy: taqvimOy }));
  const [guruhgaQoshish, setGuruhgaQoshish] = useState(false);
  const [parol, setParol] = useState(null);
  const [pastkiTab, setPastkiTab] = useState("eslatmalar");
  const [tahrirHisobi, setTahrirHisobi] = useState(null);
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

  // CRM amallari (video-TZ): qora ro'yxat, arxiv, parol tiklash, jins/maktab.
  async function crmOzgartir(body) {
    const javob = await api(`/api/crm/talaba/${talabaId}/crm/`, { method: "PATCH", body });
    if (javob.parol) setParol(javob.parol);
    yangila();
  }

  if (yuklanmoqda) return <p className="kichik">{t("yuklanmoqda")}</p>;
  if (xato) return <div className="xato">{xato}</div>;
  if (!malumot) return null;

  const talaba = malumot;

  return (
    <section>
      <button className="havola" type="button" onClick={onOrqaga}>← {t("talabalar")}</button>
      <div className="karta-sarlavha">
        <h1>
          {talaba.ism}{" "}
          {talaba.crm?.qora_royxat && <span className="holat holat-qarzdor">{t("qora_royxat")}</span>}{" "}
          {!talaba.faol && <span className="holat holat-kutilayotgan">{t("arxiv")}</span>}
        </h1>
        {/* Tahrirlash — LMS'ning `PATCH /api/talabalar/<id>/` orqali
            (2026-09-17, Shuhrat: "CRM'da tahrirlansa LMS'ga yozilsin"). */}
        <div className="tezkor-amallar">
          {ruxsat("talabalar.tahrirlash") && (
            <button className="tugma tugma-sokin" type="button" onClick={() => setTahrir(true)}>
              ✎ {t("talaba_tahrirlash")}
            </button>
          )}
          {ruxsat("guruhlar.talaba_qoshish") && (
            <button className="tugma" type="button" onClick={() => setGuruhgaQoshish(true)}>
              ➕ {t("guruhga_qoshish")}
            </button>
          )}
          <button className="tugma tugma-sokin" type="button" onClick={() => beyjikChiqar(talaba, profil?.markaz?.name)}>
            🪪 {t("beyjik_chiqarish")}
          </button>
          {ruxsat("talabalar.qora_royxat") && (
            <button className="tugma tugma-sokin" type="button" onClick={() => {
              if (talaba.crm?.qora_royxat) return crmOzgartir({ qora_royxat: false });
              const sabab = window.prompt(t("qora_royxat_sababi"));
              if (sabab !== null) crmOzgartir({ qora_royxat: true, sabab });
            }}>
              ⛔ {talaba.crm?.qora_royxat ? t("qora_royxatdan_chiqarish") : t("qora_royxatga")}
            </button>
          )}
          {ruxsat("talabalar.tahrirlash") && (
            <>
              <button className="tugma tugma-sokin" type="button"
                      onClick={() => window.confirm(t("parol_tiklash_tasdiq")) && crmOzgartir({ parol_tiklash: 1 })}>
                🔑 {t("parol_tiklash")}
              </button>
              <button className="tugma tugma-sokin" type="button"
                      onClick={() => window.confirm(talaba.faol ? t("talaba_arxiv_tasdiq") : t("talaba_tiklash_tasdiq")) && crmOzgartir({ faol: !talaba.faol })}>
                🗄 {talaba.faol ? t("arxivlash") : t("arxivdan_chiqarish")}
              </button>
            </>
          )}
        </div>
      </div>
      {parol && (
        <p className="ogohlantirish">🔑 {t("yangi_parol")}: <code>{parol}</code> — {t("login_parol_eslatma")}</p>
      )}

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
          <span className="kichik">{t("ota_ona_ismi")}</span>
          <span>{talaba.ota_ona_ismi || "—"}</span>
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
          <span className="kichik">{t("jinsi")} / {t("maktab")}</span>
          <span>
            <select value={talaba.crm?.jins || ""} onChange={(e) => crmOzgartir({ jins: e.target.value })}
                    disabled={!ruxsat("talabalar.tahrirlash")} aria-label={t("jinsi")}>
              <option value="">—</option>
              <option value="erkak">{t("jins_erkak")}</option>
              <option value="ayol">{t("jins_ayol")}</option>
            </select>{" "}
            {talaba.crm?.maktab || "—"}
          </span>
        </div>
        {talaba.crm?.qora_royxat_sabab && (
          <div className="qator">
            <span className="kichik">{t("qora_royxat_sababi")}</span>
            <span className="rang-qarzdor">{talaba.crm.qora_royxat_sabab}</span>
          </div>
        )}
        <div className="qator">
          <span className="kichik">{t("umumiy_balans")}</span>
          <b className={balansSinfi(talaba.balans_jami)}>{balansMatn(talaba.balans_jami)}</b>
        </div>
        {/* SoffCRM "Ilova holati" o'rnida — saytdan foydalanadimi. */}
        <div className="qator">
          <span className="kichik">{t("sayt_holati")}</span>
          <span className={talaba.sayt?.oxirgi_kirish ? "rang-tolandi" : "rang-qarzdor"}>
            {talaba.sayt?.oxirgi_kirish
              ? `${t("saytga_kirgan")} · ${vaqt(talaba.sayt.oxirgi_faollik || talaba.sayt.oxirgi_kirish)}`
              : t("saytga_kirmagan")}
          </span>
        </div>
        <div className="qator">
          <span className="kichik">{t("ota_ona_hisobi")}</span>
          <span>{talaba.ota_ona?.id ? `${talaba.ota_ona.ism} (${talaba.ota_ona.username})` : "—"}</span>
        </div>
        <div className="qator">
          <span className="kichik">{t("ortacha_baho")}</span>
          <b>{talaba.ortacha_baho ?? "—"}</b>
        </div>
      </div>

      {tahrir && (
        <TalabaTahrirOynasi talaba={talaba} onYopish={() => setTahrir(false)} onSaqlandi={yangila} />
      )}
      {guruhgaQoshish && (
        <GuruhTanlabQoshish talaba={talaba} onYopish={() => setGuruhgaQoshish(false)} onSaqlandi={yangila} />
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

          <div className="oy-tanlash">
            <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={() => setTaqvimOy(siljit(taqvimOy, -1))}>‹</button>
            <h3>{t("darslar_taqvimi")} ({oyNomi(taqvimOy, til)})</h3>
            <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={() => setTaqvimOy(siljit(taqvimOy, 1))}>›</button>
          </div>
          <Taqvim kunlar={g.darslar_taqvimi} sanoq={g.taqvim_sanogi} guruhId={g.guruh_id} talabaId={talaba.id}
                  onOzgardi={yangila} />

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
        <div className="tablar">
          {["eslatmalar", "tarix"].map((x) => (
            <button key={x} type="button" className={pastkiTab === x ? "tab faol" : "tab"} onClick={() => setPastkiTab(x)}>
              {t(x === "tarix" ? "oquvchi_tarixi" : "tab_eslatmalar")}
            </button>
          ))}
        </div>
        {pastkiTab === "eslatmalar" ? (
          <Eslatmalar talabaId={talaba.id} profilId={profil?.id} eslatishVaqti />
        ) : (
          <TalabaTarixi talabaId={talaba.id} />
        )}
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
                      {!hisobQatori && ["tolov", "qaytarish"].includes(x.turi) && x.usul && (
                        <span className="kichik"> · {t(`usul_${x.usul}`)}</span>
                      )}
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
                      {hisobQatori && hisob && profil?.is_owner && (
                        <button className="havola" type="button" title={t("qarzdorlikni_tahrirlash")}
                                onClick={() => setTahrirHisobi(hisob)}>✎</button>
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
      {tahrirHisobi && (
        <HisobTahrirOynasi hisob={tahrirHisobi} onYopish={() => setTahrirHisobi(null)} onSaqlandi={yangilaHammasi} />
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
  // Qo'shimcha filtr (video-TZ): qarzdorlar / qora ro'yxat / guruhsizlar.
  const [filtr, setFiltr] = useState("");
  const [yangiOyna, setYangiOyna] = useState(false);
  const [importOyna, setImportOyna] = useState(false);
  // Video (17:15): guruh, ustoz, kurs, maktab filtrlari.
  const [guruhF, setGuruhF] = useState("");
  const [ustozF, setUstozF] = useState("");
  const [kursF, setKursF] = useState("");
  const [maktabF, setMaktabF] = useState("");
  const guruhlarF = useSorov("/api/crm/guruhlar/" + sorovSatri({ filial: tanlangan }));
  const ruxsat = useRuxsat();
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
  const filtrSatri = sorovSatri({
    filial: tanlangan, q: qidiruv, holat,
    qarzdor: filtr === "qarzdor" ? 1 : "", qora_royxat: filtr === "qora_royxat" ? 1 : "",
    guruhsiz: filtr === "guruhsiz" ? 1 : "",
    guruh: guruhF, oqituvchi: ustozF, kurs: kursF, maktab: maktabF,
  });
  const { malumot, yuklanmoqda, xato, yangila } = useSorov("/api/crm/talabalar/" + filtrSatri);
  const [eksportXato, setEksportXato] = useState("");

  // Holat SoffCRM'dagidek ro'yxatdan ham o'zgaradi (guruh kartasiga
  // kirmasdan). Backend `AzolikView` chiqish/muzlatishda joriy oyni
  // qayta hisoblaydi — bu yerda faqat chaqiriladi.
  async function holatOzgartir(azolikMoliyaId, yangiHolat) {
    await api(`/api/crm/azoliklar/${azolikMoliyaId}/`, { method: "PATCH", body: { holat: yangiHolat } });
    yangila();
  }

  if (ochilgan) return <Karta talabaId={ochilgan} onOrqaga={() => setOchilgan(null)} />;

  const royxat = malumot || [];
  // "Qarzdor: 2 990 000 so'm" (video 23:50) — ro'yxatdagilar qarzi yig'indisi.
  const jamiQarz = royxat.reduce((s, x) => s + Math.min(0, Number(x.balans || 0)), 0);
  const guruhVariantlari = guruhlarF.malumot || [];

  return (
    <section>
      <div className="karta-sarlavha">
        <h1>
          {t("talabalar")} <span className="belgi">{royxat.length}</span>{" "}
          {jamiQarz < 0 && <span className="holat holat-qarzdor">{t("qarzdor")}: {pul(-jamiQarz)}</span>}
        </h1>
        <div className="tezkor-amallar">
          {ruxsat("talabalar.excel") && (
            <button className="tugma tugma-sokin" type="button"
                    onClick={() => apiFayluniYuklab("/api/crm/talabalar/eksport/" + filtrSatri).catch((e) => setEksportXato(e.message))}>
              ⬇ Excel
            </button>
          )}
          {ruxsat("talabalar.qoshish") && (
            <>
              <button className="tugma tugma-sokin" type="button" onClick={() => setImportOyna(true)}>⬆ {t("excel_orqali_qoshish")}</button>
              <button className="tugma" type="button" onClick={() => setYangiOyna(true)}>+ {t("yangi_oquvchi")}</button>
            </>
          )}
        </div>
      </div>

      <div className="filtrlar">
        <input placeholder={t("qidiruv")} value={qidiruv} onChange={(e) => setQidiruv(e.target.value)} />
        <select value={holat} onChange={(e) => setHolat(e.target.value)}>
          <option value="">{t("barcha_holatlar")}</option>
          {["sinov", "faol", "muzlatilgan"].map((h) => (
            <option key={h} value={h}>{t(`holat_${h}`)}</option>
          ))}
        </select>
        <select value={filtr} onChange={(e) => setFiltr(e.target.value)} aria-label={t("filtr")}>
          <option value="">{t("hammasi")}</option>
          <option value="qarzdor">{t("qarzdorlar")}</option>
          <option value="guruhsiz">{t("guruhsizlar")}</option>
          <option value="qora_royxat">{t("qora_royxat")}</option>
        </select>
        <select value={guruhF} onChange={(e) => setGuruhF(e.target.value)} aria-label={t("guruh")}>
          <option value="">{t("guruh")}: {t("hammasi")}</option>
          {guruhVariantlari.map((g) => <option key={g.id} value={g.id}>{g.nomi}</option>)}
        </select>
        <select value={ustozF} onChange={(e) => setUstozF(e.target.value)} aria-label={t("oqituvchi")}>
          <option value="">{t("oqituvchi")}: {t("hammasi")}</option>
          {[...new Map(guruhVariantlari.filter((g) => g.oqituvchi).map((g) => [g.oqituvchi, g])).keys()].map((o) => {
            const g = guruhVariantlari.find((x) => x.oqituvchi === o);
            return <option key={o} value={g.oqituvchi_id ?? ""}>{o}</option>;
          })}
        </select>
        <select value={kursF} onChange={(e) => setKursF(e.target.value)} aria-label={t("kurs")}>
          <option value="">{t("kurs")}: {t("hammasi")}</option>
          {[...new Map(guruhVariantlari.filter((g) => g.daraja).map((g) => [g.daraja.id, g.daraja.nomi])).entries()].map(([id, nomi]) => (
            <option key={id} value={id}>{nomi}</option>
          ))}
        </select>
        <input placeholder={t("maktab")} value={maktabF} onChange={(e) => setMaktabF(e.target.value)} style={{ maxWidth: 140 }} />
      </div>

      {(xato || eksportXato) && <div className="xato">{xato || eksportXato}</div>}
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      <div className="karta jadval-oram">
        <table>
          <thead>
            <tr>
              <th>{t("talaba")}</th>
              <th>{t("baho")}</th>
              <th>{t("keyingi_tolov_sanasi")}</th>
              <th>{t("telefon")}</th>
              <th>{t("izoh")}</th>
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
                  {x.qora_royxat && <span className="holat holat-qarzdor"> {t("qora_royxat")}</span>}
                </td>
                <td>{x.baho !== null && x.baho !== undefined ? <span className="baho-doira">{x.baho}</span> : <span className="kichik">{t("bahosi_yoq")}</span>}</td>
                <td className="nowrap">{sana(x.keyingi_tolov)}</td>
                <td>{x.telefon || "—"}</td>
                <td className="kichik">{x.izoh || "—"}</td>
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
              <tr><td colSpan={8} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {yangiOyna && <YangiTalabaOynasi onYopish={() => setYangiOyna(false)} onSaqlandi={yangila} />}
      {importOyna && <ImportOynasi onYopish={() => setImportOyna(false)} onSaqlandi={yangila} />}
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
