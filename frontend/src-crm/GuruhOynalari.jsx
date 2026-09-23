// Guruh boshqaruvi oynalari (video-TZ, 2026-09-23): guruh qo'shish /
// tahrirlash, guruhga o'quvchi qo'shish (qo'lda, yangi o'quvchi, Excel),
// chegirmalar va darsni ko'chirish. CRM endi guruhning ASOSIY joyi.

import { useState } from "react";

import { api, apiFaylYubor, apiFayluniYuklab } from "./api.js";
import { useFilial } from "./filialContext.jsx";
import { oyNomi, pul, sana } from "./format.js";
import { useI18n } from "./i18n.jsx";
import { useRuxsat } from "./profilContext.jsx";
import { sorovSatri, useSorov } from "./soragich.js";

const KUN_KALITLARI = [
  "kun_dushanba", "kun_seshanba", "kun_chorshanba",
  "kun_payshanba", "kun_juma", "kun_shanba", "kun_yakshanba",
];
// SoffCRM'dagi "Hafta kunlari" tayyor variantlari.
const HAFTA_SHABLONLARI = { toq: [0, 2, 4], juft: [1, 3, 5], har_kuni: [0, 1, 2, 3, 4, 5] };

const bugun = () => new Date().toISOString().slice(0, 10);

// ── Guruh qo'shish / tahrirlash ─────────────────────────────────────

export function GuruhOynasi({ guruh, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const { filiallar, tanlangan } = useFilial();
  const kurslar = useSorov("/api/crm/kurs-narxlari/");
  // `tanlov=1` — hamma o'qituvchi (filialidan qat'i nazar, qaror 2026-09-23).
  const oqituvchilar = useSorov("/api/crm/xodimlar/?lavozim=oqituvchi&tanlov=1");
  const tahrir = Boolean(guruh);
  const [f, setF] = useState(() => ({
    nomi: guruh?.nomi || "",
    daraja_id: guruh?.daraja?.id ?? "",
    filial_id: guruh?.filial?.id ?? tanlangan ?? "",
    narx: guruh?.narx_guruhga ?? "",
    boshlanish_sana: guruh?.boshlanish_sana || bugun(),
    tugash_sana: guruh?.tugash_sana || "",
    baholash_tizimi: guruh?.baholash_tizimi || "",
  }));
  const [shablon, setShablon] = useState("toq");
  const [jadval, setJadval] = useState(() =>
    guruh?.jadval?.length
      ? guruh.jadval.map((j) => ({ ...j }))
      : HAFTA_SHABLONLARI.toq.map((k) => ({ hafta_kuni: k, boshlanish_vaqti: "14:00", tugash_vaqti: "15:30", xona_id: null }))
  );
  const [oqit, setOqit] = useState(() =>
    guruh?.oqituvchilar?.length
      ? guruh.oqituvchilar.map((o) => ({
          oqituvchi_id: o.oqituvchi_id, turi: o.turi, foiz: o.foiz ?? "",
          ulush_turi: o.ulush_turi || "foiz", dars_haqi: o.dars_haqi ?? "",
        }))
      : [{ oqituvchi_id: "", turi: "asosiy", foiz: "", ulush_turi: "foiz", dars_haqi: "" }]
  );
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);
  const xonalar = useSorov(f.filial_id ? `/api/crm/xonalar/?faqat_faol=1&filial=${f.filial_id}` : null);
  const qiymat = (k) => ({ value: f[k] ?? "", onChange: (e) => setF((x) => ({ ...x, [k]: e.target.value })) });

  function shablonTanla(nom) {
    setShablon(nom);
    if (nom === "boshqa") return;
    const namuna = jadval[0] || { boshlanish_vaqti: "14:00", tugash_vaqti: "15:30", xona_id: null };
    setJadval(HAFTA_SHABLONLARI[nom].map((k) => ({ ...namuna, hafta_kuni: k })));
  }

  function bandOzgartir(i, maydon, q) {
    setJadval((eski) => eski.map((b, j) => (i === j ? { ...b, [maydon]: q } : b)));
  }

  // Birinchi kunning vaqti va xonasini qolganlarga ham ko'chirish
  // (SoffCRM'dagi "nusxa" belgisi).
  function hammagaNusxa() {
    const [birinchi] = jadval;
    if (!birinchi) return;
    setJadval((eski) => eski.map((b) => ({ ...b, boshlanish_vaqti: birinchi.boshlanish_vaqti,
      tugash_vaqti: birinchi.tugash_vaqti, xona_id: birinchi.xona_id })));
  }

  async function saqla() {
    setXato("");
    setBand(true);
    const oqituvchilarRoyxati = oqit.filter((o) => o.oqituvchi_id).map((o) => ({
      ...o, foiz: o.foiz === "" ? null : o.foiz, dars_haqi: o.dars_haqi === "" ? null : o.dars_haqi,
    }));
    try {
      if (tahrir) {
        await api(`/api/crm/guruhlar/${guruh.id}/boshqaruv/`, {
          method: "PATCH",
          body: { nomi: f.nomi, daraja_id: f.daraja_id || null, oqituvchilar: oqituvchilarRoyxati },
        });
        await api(`/api/crm/guruhlar/${guruh.id}/moliya/`, {
          method: "PATCH",
          body: { filial_id: f.filial_id || null, narx: f.narx === "" ? null : String(f.narx),
                  boshlanish_sana: f.boshlanish_sana || null, tugash_sana: f.tugash_sana || null,
                  baholash_tizimi: f.baholash_tizimi },
        });
        await api(`/api/crm/guruhlar/${guruh.id}/jadval/`, { method: "PUT", body: { jadval } });
      } else {
        await api("/api/crm/guruh-yaratish/", {
          method: "POST",
          body: { ...f, filial_id: f.filial_id || null, daraja_id: f.daraja_id || null, jadval,
                  oqituvchilar: oqituvchilarRoyxati },
        });
      }
      onSaqlandi();
      onYopish();
    } catch (e) {
      setXato(e.message);
    } finally {
      setBand(false);
    }
  }

  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna oyna-keng">
        <h2>{tahrir ? t("guruhni_tahrirlash") : t("guruh_qoshish")}</h2>
        <label>{t("guruh_nomi")}<input {...qiymat("nomi")} autoFocus /></label>
        <div className="ikki-ustun">
          <label>{t("kurs")}
            <select {...qiymat("daraja_id")}>
              <option value="">—</option>
              {(kurslar.malumot || []).map((k) => (
                <option key={k.daraja_id} value={k.daraja_id}>
                  {k.fan ? `${k.fan} — ` : ""}{k.daraja}{k.narx ? ` (${pul(k.narx)})` : ""}
                </option>
              ))}
            </select>
          </label>
          <label>{t("filial")}
            <select {...qiymat("filial_id")}>
              <option value="">—</option>
              {filiallar.map((x) => <option key={x.id} value={x.id}>{x.nomi}</option>)}
            </select>
          </label>
        </div>
        <div className="ikki-ustun">
          <label>{t("boshlanish_sana")}<input type="date" {...qiymat("boshlanish_sana")} /></label>
          <label>{t("tugash_sana")}<input type="date" {...qiymat("tugash_sana")} /></label>
        </div>
        <div className="ikki-ustun">
          <label>{t("narx")} ({t("narx_guruhdan")}, {t("ixtiyoriy")})
            <input type="number" min="0" step="1000" {...qiymat("narx")} placeholder={t("kurs_narxi_olinadi")} />
          </label>
          <label>{t("baholash_tizimi")} ({t("ixtiyoriy")})
            <select {...qiymat("baholash_tizimi")}>
              <option value="">{t("baholanmaydi")}</option>
              <option value="5">1–5</option>
              <option value="10">1–10</option>
              <option value="100">0–100</option>
            </select>
          </label>
        </div>

        <h3>{t("dars_vaqtlari")} <span className="belgi">{jadval.length} {t("kun")}</span></h3>
        <div className="tablar">
          {["toq", "juft", "har_kuni", "boshqa"].map((x) => (
            <button key={x} type="button" className={shablon === x ? "tab faol" : "tab"} onClick={() => shablonTanla(x)}>
              {t(`kunlar_${x}`)}
            </button>
          ))}
        </div>
        {jadval.map((b, i) => (
          <div key={i} className="jadval-qator">
            <select value={b.hafta_kuni} onChange={(e) => bandOzgartir(i, "hafta_kuni", Number(e.target.value))}>
              {KUN_KALITLARI.map((k, n) => <option key={k} value={n}>{t(k)}</option>)}
            </select>
            <input type="time" value={b.boshlanish_vaqti} onChange={(e) => bandOzgartir(i, "boshlanish_vaqti", e.target.value)} />
            <input type="time" value={b.tugash_vaqti} onChange={(e) => bandOzgartir(i, "tugash_vaqti", e.target.value)} />
            <select value={b.xona_id ?? ""} onChange={(e) => bandOzgartir(i, "xona_id", e.target.value || null)}>
              <option value="">{t("xonasiz")}</option>
              {(xonalar.malumot || []).map((x) => <option key={x.id} value={x.id}>{x.nomi}</option>)}
            </select>
            <button className="tugma tugma-sokin kichik-tugma" type="button"
                    onClick={() => setJadval((eski) => eski.filter((_, j) => j !== i))}>✕</button>
          </div>
        ))}
        <div className="tezkor-amallar">
          <button className="tugma tugma-sokin kichik-tugma" type="button"
                  onClick={() => { setShablon("boshqa"); setJadval((e) => [...e, { hafta_kuni: 0, boshlanish_vaqti: "14:00", tugash_vaqti: "15:30", xona_id: null }]); }}>
            + {t("kun_qoshish")}
          </button>
          <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={hammagaNusxa}>
            ⧉ {t("vaqtni_hammaga")}
          </button>
        </div>

        <h3>{t("oqituvchilar_va_ulushlar")} <span className="kichik">({t("maksimal_3")})</span></h3>
        {oqit.map((o, i) => (
          <div key={i} className="jadval-qator">
            <select value={o.oqituvchi_id} onChange={(e) => setOqit((x) => x.map((y, j) => (i === j ? { ...y, oqituvchi_id: e.target.value } : y)))}>
              <option value="">{t("oqituvchi")}</option>
              {(oqituvchilar.malumot?.xodimlar || []).map((x) => <option key={x.id} value={x.id}>{x.ism}</option>)}
            </select>
            <select value={o.turi} onChange={(e) => setOqit((x) => x.map((y, j) => (i === j ? { ...y, turi: e.target.value } : y)))}>
              <option value="asosiy">{t("asosiy")}</option>
              <option value="yordamchi">{t("yordamchi")}</option>
            </select>
            <select value={o.ulush_turi} aria-label={t("ulush_turi")}
                    onChange={(e) => setOqit((x) => x.map((y, j) => (i === j ? { ...y, ulush_turi: e.target.value } : y)))}>
              <option value="foiz">{t("ulush_foiz")}</option>
              <option value="dars">{t("ulush_dars")}</option>
            </select>
            {o.ulush_turi === "dars" ? (
              <input type="number" min="0" step="1000" placeholder={t("dars_haqi")} value={o.dars_haqi}
                     onChange={(e) => setOqit((x) => x.map((y, j) => (i === j ? { ...y, dars_haqi: e.target.value } : y)))} />
            ) : (
              <input type="number" min="0" max="100" placeholder={t("foiz")} value={o.foiz}
                     onChange={(e) => setOqit((x) => x.map((y, j) => (i === j ? { ...y, foiz: e.target.value } : y)))} />
            )}
            <button className="tugma tugma-sokin kichik-tugma" type="button"
                    onClick={() => setOqit((x) => x.filter((_, j) => j !== i))}>✕</button>
          </div>
        ))}
        {oqit.length < 3 && (
          <button className="tugma tugma-sokin kichik-tugma" type="button"
                  onClick={() => setOqit((x) => [...x, { oqituvchi_id: "", turi: "yordamchi", foiz: "", ulush_turi: "foiz", dars_haqi: "" }])}>
            + {t("oqituvchi_qoshish")}
          </button>
        )}

        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
          <button className="tugma" type="button" onClick={saqla} disabled={band || !f.nomi.trim()}>{t("saqlash")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Guruhga o'quvchi qo'shish ───────────────────────────────────────

function LoginRoyxati({ royxat }) {
  const { t } = useI18n();
  const parolli = royxat.filter((x) => x.parol);
  if (!parolli.length) return null;
  return (
    <>
      <p className="kichik">{t("login_parol_eslatma")}</p>
      <ul className="login-royxat">
        {parolli.map((x) => (
          <li key={x.username}><b>{x.ism}</b> — <code>{x.username}</code> / <code>{x.parol}</code></li>
        ))}
      </ul>
    </>
  );
}

export function TalabaQoshishOynasi({ guruh, tanlanganTalaba = null, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const [rejim, setRejim] = useState("qolda");
  const [qidiruv, setQidiruv] = useState("");
  const [tanlangan, setTanlangan] = useState(tanlanganTalaba);
  const [sanaQ, setSanaQ] = useState(bugun());
  const [holat, setHolat] = useState("faol");
  const [alohidaNarx, setAlohidaNarx] = useState(false);
  const [narx, setNarx] = useState("");
  const [izoh, setIzoh] = useState("");
  const [yangi, setYangi] = useState({ ism: "", telefon: "+998", ota_ona_telefon: "", tugilgan_sana: "", jins: "erkak" });
  const [fayl, setFayl] = useState(null);
  const [natija, setNatija] = useState(null);
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);
  const topilganlar = useSorov(qidiruv.trim().length >= 2 ? "/api/crm/talaba-qidiruv/" + sorovSatri({ q: qidiruv }) : null);

  async function saqla() {
    setXato("");
    setBand(true);
    try {
      const umumiy = { sana: sanaQ, holat, narx: alohidaNarx && narx !== "" ? narx : null, izoh };
      if (rejim === "qolda") {
        await api(`/api/crm/guruhlar/${guruh.id}/talabalar/`, { method: "POST", body: { ...umumiy, talaba_id: tanlangan.id } });
        onSaqlandi();
        onYopish();
      } else if (rejim === "yangi") {
        const javob = await api("/api/crm/talaba-yaratish/", {
          method: "POST",
          body: { ...yangi, guruh_id: guruh.id, boshlanish_sana: sanaQ, holat, narx: umumiy.narx },
        });
        onSaqlandi();
        setNatija([{ ism: javob.ism, username: javob.username, parol: javob.parol }]);
      } else {
        const fd = new FormData();
        fd.append("excel_fayl", fayl);
        fd.append("sana", sanaQ);
        fd.append("holat", holat);
        const javob = await apiFaylYubor(`/api/crm/guruhlar/${guruh.id}/talabalar/`, fd);
        onSaqlandi();
        setNatija(javob.qoshildi);
        if (javob.xatolar?.length) setXato(javob.xatolar.map((x) => `${x.qator}: ${x.xato}`).join("; "));
      }
    } catch (e) {
      setXato(e.message);
    } finally {
      setBand(false);
    }
  }

  const tayyor = rejim === "qolda" ? Boolean(tanlangan) : rejim === "yangi" ? yangi.ism.trim() : Boolean(fayl);

  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna oyna-keng">
        <h2>{t("guruhga_oquvchi_qoshish")}</h2>
        <p className="kichik">{guruh.nomi}</p>
        {natija ? (
          <>
            <p>✅ {t("qoshildi")}: {natija.length}</p>
            <LoginRoyxati royxat={natija} />
            {xato && <div className="xato">{xato}</div>}
            <div className="oyna-tugmalar">
              <button className="tugma" type="button" onClick={onYopish}>{t("yopish")}</button>
            </div>
          </>
        ) : (
          <>
            <div className="tablar">
              {["qolda", "yangi", "excel"].map((x) => (
                <button key={x} type="button" className={rejim === x ? "tab faol" : "tab"} onClick={() => setRejim(x)}>
                  {t(`qoshish_${x}`)}
                </button>
              ))}
            </div>

            {rejim === "qolda" && (
              <>
                <input placeholder={t("oquvchini_qidiring")} value={qidiruv} autoFocus
                       onChange={(e) => { setQidiruv(e.target.value); setTanlangan(null); }} />
                {tanlangan ? (
                  <p>✔ <b>{tanlangan.ism}</b> <span className="kichik">{tanlangan.telefon}</span></p>
                ) : (
                  <ul className="qidiruv-natija">
                    {(topilganlar.malumot || []).map((x) => (
                      <li key={x.id}>
                        <button className="havola" type="button" onClick={() => setTanlangan(x)}>
                          {x.ism} <span className="kichik">{x.telefon || x.username}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}

            {rejim === "yangi" && (
              <>
                <label>{t("ism_familiya")}<input value={yangi.ism} autoFocus onChange={(e) => setYangi((x) => ({ ...x, ism: e.target.value }))} /></label>
                <div className="ikki-ustun">
                  <label>{t("telefon")}<input value={yangi.telefon} onChange={(e) => setYangi((x) => ({ ...x, telefon: e.target.value }))} /></label>
                  <label>{t("ota_ona_telefon")}<input value={yangi.ota_ona_telefon} onChange={(e) => setYangi((x) => ({ ...x, ota_ona_telefon: e.target.value }))} /></label>
                </div>
                <div className="ikki-ustun">
                  <label>{t("tugilgan_sana")}<input type="date" value={yangi.tugilgan_sana} onChange={(e) => setYangi((x) => ({ ...x, tugilgan_sana: e.target.value }))} /></label>
                  <label>{t("jinsi")}
                    <select value={yangi.jins} onChange={(e) => setYangi((x) => ({ ...x, jins: e.target.value }))}>
                      <option value="erkak">{t("jins_erkak")}</option>
                      <option value="ayol">{t("jins_ayol")}</option>
                    </select>
                  </label>
                </div>
              </>
            )}

            {rejim === "excel" && (
              <>
                <p className="kichik">{t("excel_format_guruh")}</p>
                <input type="file" accept=".xlsx" onChange={(e) => setFayl(e.target.files?.[0] || null)} />
              </>
            )}

            <div className="ikki-ustun">
              <label>{t("guruhga_qoshilish_sanasi")}<input type="date" value={sanaQ} onChange={(e) => setSanaQ(e.target.value)} /></label>
              <label>{t("holat")}
                <select value={holat} onChange={(e) => setHolat(e.target.value)}>
                  <option value="faol">{t("holat_faol")}</option>
                  <option value="sinov">{t("holat_sinov")}</option>
                </select>
              </label>
            </div>
            {rejim !== "excel" && (
              <>
                <label className="yonma">
                  <input type="checkbox" checked={alohidaNarx} onChange={(e) => setAlohidaNarx(e.target.checked)} />
                  {t("alohida_narx_kiritish")}
                </label>
                {alohidaNarx && (
                  <input type="number" min="0" step="1000" value={narx} onChange={(e) => setNarx(e.target.value)}
                         placeholder={guruh.narx ? String(guruh.narx) : ""} />
                )}
              </>
            )}
            {rejim === "qolda" && (
              <label>{t("izoh")}<textarea rows={2} value={izoh} onChange={(e) => setIzoh(e.target.value)} /></label>
            )}
            {xato && <div className="xato">{xato}</div>}
            <div className="oyna-tugmalar">
              <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
              <button className="tugma" type="button" onClick={saqla} disabled={band || !tayyor}>{t("saqlash")}</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ── Davomat (tahrirlanadigan) ───────────────────────────────────────

const HOLAT_BELGI = { keldi: "✓", kelmadi: "✕", sababli: "◐" };
const HOLAT_KETMA = [null, "keldi", "kelmadi", "sababli"];

export function DavomatJadvali({ guruhId }) {
  const { t, til } = useI18n();
  const ruxsat = useRuxsat();
  const [oy, setOy] = useState(() => new Date().toISOString().slice(0, 7));
  const { malumot, yuklanmoqda, xato, yangila } = useSorov(`/api/crm/guruhlar/${guruhId}/davomat/` + sorovSatri({ oy }));
  // Dars mavzulari (SoffCRM "Mavzular" qatori).
  const mavzular = useSorov(`/api/crm/guruhlar/${guruhId}/mavzular/` + sorovSatri({ oy }));
  const [xatoQ, setXatoQ] = useState("");
  const [kochirish, setKochirish] = useState(null);
  const tahrirlaydi = ruxsat("guruhlar.davomat");
  const bugunSana = new Date().toISOString().slice(0, 10);

  async function mavzuYoz(sanaQ) {
    const eski = mavzular.malumot?.[sanaQ] || "";
    const yangi = window.prompt(`${sana(sanaQ)} — ${t("dars_mavzusi")}`, eski);
    if (yangi === null || yangi === eski) return;
    await api(`/api/crm/guruhlar/${guruhId}/mavzular/`, { method: "POST", body: { sana: sanaQ, mavzu: yangi } });
    mavzular.yangila();
  }

  async function hammasiKeldi(sanaQ) {
    setXatoQ("");
    try {
      await api(`/api/crm/guruhlar/${guruhId}/davomat/hammasi/`, { method: "POST", body: { sana: sanaQ } });
      yangila();
    } catch (e) {
      setXatoQ(e.message);
    }
  }

  function siljit(qadam) {
    const [y, o] = oy.split("-").map(Number);
    const d = new Date(y, o - 1 + qadam, 1);
    setOy(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  }

  async function belgila(talaba, kun) {
    if (!tahrirlaydi || kun.qulf || kun.kelajak) return;
    const keyingi = HOLAT_KETMA[(HOLAT_KETMA.indexOf(kun.holat) + 1) % HOLAT_KETMA.length];
    let izoh = kun.izoh || "";
    if (keyingi === "sababli") {
      const javob = window.prompt(t("sabab_izoh"), izoh);
      if (javob === null) return;
      izoh = javob;
    }
    setXatoQ("");
    try {
      await api(`/api/crm/guruhlar/${guruhId}/davomat/`, {
        method: "POST",
        body: { talaba_id: talaba.id, sana: kun.sana, holat: keyingi, izoh },
      });
      yangila();
    } catch (e) {
      setXatoQ(e.message);
    }
  }

  const sanalar = malumot?.sanalar || [];
  const talabalar = malumot?.talabalar || [];
  const ozgarishlar = malumot?.ozgarishlar || [];

  return (
    <>
      <div className="filtrlar">
        <div className="oy-tanlash">
          <button className="tugma tugma-sokin" type="button" onClick={() => siljit(-1)}>‹</button>
          <b>{oyNomi(oy, til)}</b>
          <button className="tugma tugma-sokin" type="button" onClick={() => siljit(1)}>›</button>
        </div>
        {tahrirlaydi && <span className="kichik">{t("davomat_bosish_izoh")}</span>}
        {ruxsat("guruhlar.dars_kochirish") && (
          <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={() => setKochirish({ turi: "qoshimcha" })}>
            + {t("qoshimcha_dars")}
          </button>
        )}
        <button className="tugma tugma-sokin kichik-tugma" type="button"
                onClick={() => apiFayluniYuklab(`/api/crm/guruhlar/${guruhId}/davomat/eksport/` + sorovSatri({ oy })).catch((e) => setXatoQ(e.message))}>
          ⬇ Excel
        </button>
      </div>
      {(xato || xatoQ) && <div className="xato">{xato || xatoQ}</div>}
      {yuklanmoqda && !malumot && <p className="kichik">{t("yuklanmoqda")}</p>}
      {sanalar.length === 0 && !yuklanmoqda && <p className="kichik">{t("davomat_yoq")}</p>}
      {sanalar.length > 0 && (
        <div className="jadval-oram">
          <table className="davomat-jadval">
            <thead>
              <tr className="mavzu-qator">
                <th className="kichik">{t("mavzular")}</th>
                {sanalar.map((s) => (
                  <th key={s} className="markazga">
                    <button type="button" className="havola kichik" title={mavzular.malumot?.[s] || t("dars_mavzusi")}
                            disabled={!tahrirlaydi} onClick={() => mavzuYoz(s)}>
                      {mavzular.malumot?.[s] ? "📘" : "＋"}
                    </button>
                    {tahrirlaydi && s <= bugunSana && (
                      <button type="button" className="havola kichik" title={t("hammasi_keldi")} onClick={() => hammasiKeldi(s)}>✓✓</button>
                    )}
                  </th>
                ))}
                <th />
                <th />
              </tr>
              <tr>
                <th>{t("talaba")}</th>
                {sanalar.map((s) => {
                  const oz = ozgarishlar.find((o) => o.yangi_sana === s);
                  return (
                    <th key={s} className="markazga" title={sana(s) + (oz ? ` · ${oz.turi_nomi}` : "")}>
                      {ruxsat("guruhlar.dars_kochirish") ? (
                        <button className="havola" type="button" onClick={() => setKochirish({ turi: "kochirish", asl_sana: s })}>
                          {String(s).slice(8, 10)}
                        </button>
                      ) : String(s).slice(8, 10)}
                      {oz && <sup>*</sup>}
                    </th>
                  );
                })}
                <th className="ongga">{t("keldi")}</th>
                <th className="ongga">{t("kelmadi")}</th>
              </tr>
            </thead>
            <tbody>
              {talabalar.map((x) => (
                <tr key={x.id}>
                  <td>{x.ism}</td>
                  {x.kunlar.map((k) => (
                    <td key={k.sana} className="markazga">
                      <button
                        type="button"
                        className={`davomat-katak davomat-${k.holat || "yoq"}${k.qulf ? " qulf" : ""}`}
                        disabled={!tahrirlaydi || k.qulf || k.kelajak}
                        title={k.qulf ? t("hali_qoshilmagan") : k.izoh || sana(k.sana)}
                        onClick={() => belgila(x, k)}
                      >
                        {k.qulf ? "🔒" : HOLAT_BELGI[k.holat] || "·"}
                      </button>
                    </td>
                  ))}
                  <td className="ongga rang-tolandi">{x.keldi}</td>
                  <td className="ongga rang-qarzdor">{x.kelmadi}{x.sababli ? ` (+${x.sababli})` : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {ozgarishlar.length > 0 && (
        <ul className="kichik ozgarish-royxat">
          {ozgarishlar.map((o) => (
            <li key={o.id}>
              {o.turi_nomi}: {o.asl_sana ? sana(o.asl_sana) : ""}{o.asl_sana && o.yangi_sana ? " → " : ""}
              {o.yangi_sana ? sana(o.yangi_sana) : ""}{o.boshlanish_vaqti ? ` ${o.boshlanish_vaqti}` : ""}
              {o.izoh ? ` — ${o.izoh}` : ""}
              {ruxsat("guruhlar.dars_kochirish") && (
                <button className="havola rang-qarzdor" type="button" onClick={async () => {
                  setXatoQ("");
                  try {
                    await api(`/api/crm/dars-ozgarishlari/${o.id}/`, { method: "DELETE" });
                    yangila();
                    mavzular.yangila();
                  } catch (e) {
                    setXatoQ(e.message);
                  }
                }}> ✕</button>
              )}
            </li>
          ))}
        </ul>
      )}
      {kochirish && (
        <DarsKochirishOynasi guruhId={guruhId} boshlangich={kochirish}
                             onYopish={() => setKochirish(null)}
                             onSaqlandi={() => { yangila(); mavzular.yangila(); }} />
      )}
    </>
  );
}

// ── Darsni ko'chirish / qo'shimcha dars / bekor qilish ──────────────

function DarsKochirishOynasi({ guruhId, boshlangich, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const [f, setF] = useState({
    turi: boshlangich.turi, asl_sana: boshlangich.asl_sana || "", yangi_sana: "",
    boshlanish_vaqti: "", tugash_vaqti: "", izoh: "",
  });
  const [xato, setXato] = useState("");
  const qiymat = (k) => ({ value: f[k], onChange: (e) => setF((x) => ({ ...x, [k]: e.target.value })) });

  async function saqla() {
    setXato("");
    try {
      await api(`/api/crm/guruhlar/${guruhId}/dars-ozgarishlari/`, { method: "POST", body: f });
      onSaqlandi();
      onYopish();
    } catch (e) {
      setXato(e.message);
    }
  }

  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna">
        <h2>{t("darsni_kochirish")}</h2>
        {f.asl_sana && <p className="kichik">{sana(f.asl_sana)} {t("dagi_dars")}</p>}
        <p className="ogohlantirish kichik">{t("kochirish_izoh")}</p>
        <label>{t("turi")}
          <select {...qiymat("turi")}>
            <option value="kochirish">{t("dars_kochirildi")}</option>
            <option value="bekor">{t("dars_bekor")}</option>
            <option value="qoshimcha">{t("qoshimcha_dars")}</option>
          </select>
        </label>
        {f.turi !== "qoshimcha" && <label>{t("asl_sana")}<input type="date" {...qiymat("asl_sana")} /></label>}
        {f.turi !== "bekor" && (
          <>
            {/* Ko'chirishda o'tgan kun tanlanmaydi (backend ham tekshiradi). */}
            <label>{t("yangi_sana")}
              <input type="date" {...qiymat("yangi_sana")} min={f.turi === "kochirish" ? bugun() : undefined} />
            </label>
            <p className="kichik">{t("kochirish_sana_izoh")}</p>
            <div className="ikki-ustun">
              <label>{t("boshlanish_vaqti")}<input type="time" {...qiymat("boshlanish_vaqti")} /></label>
              <label>{t("tugash_vaqti")}<input type="time" {...qiymat("tugash_vaqti")} /></label>
            </div>
          </>
        )}
        <label>{t("izoh")}<input {...qiymat("izoh")} /></label>
        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
          <button className="tugma" type="button" onClick={saqla}>{t("saqlash")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Chegirmalar ─────────────────────────────────────────────────────

export function Chegirmalar({ guruhId, onOzgardi }) {
  const { t, til } = useI18n();
  const ruxsat = useRuxsat();
  const { malumot, yuklanmoqda, xato, yangila } = useSorov(`/api/crm/guruhlar/${guruhId}/chegirmalar/`);
  const [oyna, setOyna] = useState(null);
  // Chegirma uch xil kiritiladi (video 28:05): yangi narx, summada (ayiriladi), foizda.
  const [rejim, setRejim] = useState("summada");
  const [f, setF] = useState({ qiymat: "", boshlanish_oy: new Date().toISOString().slice(0, 7), oylar_soni: 1, izoh: "" });
  const [xatoQ, setXatoQ] = useState("");

  async function saqla() {
    setXatoQ("");
    try {
      const kalit = { narx: "narx", summada: "chegirma_summasi", foizda: "foiz" }[rejim];
      await api(`/api/crm/guruhlar/${guruhId}/chegirmalar/`, {
        method: "POST",
        body: {
          [kalit]: f.qiymat, boshlanish_oy: f.boshlanish_oy, oylar_soni: f.oylar_soni, izoh: f.izoh,
          azolik_moliya_id: oyna.azolik_moliya_id,
        },
      });
      setOyna(null);
      yangila();
      onOzgardi?.();
    } catch (e) {
      setXatoQ(e.message);
    }
  }

  async function ochir(id) {
    if (!window.confirm(t("chegirma_ochirish_tasdiq"))) return;
    setXatoQ("");
    try {
      await api(`/api/crm/chegirmalar/${id}/`, { method: "DELETE" });
      yangila();
      onOzgardi?.();
    } catch (e) {
      setXatoQ(e.message);
    }
  }

  if (yuklanmoqda && !malumot) return <p className="kichik">{t("yuklanmoqda")}</p>;
  return (
    <div className="jadval-oram">
      {(xato || (!oyna && xatoQ)) && <div className="xato">{xato || xatoQ}</div>}
      <table>
        <thead>
          <tr>
            <th>{t("talaba")}</th>
            <th className="ongga">{t("qolgan_chegirma")}</th>
            <th>{t("berilgan_sana")}</th>
            <th>{t("yaratgan_xodim")}</th>
            <th>{t("izoh")}</th>
            <th className="ongga">{t("chegirmadagi_narx")}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {(malumot || []).map((x) => {
            const faol = x.chegirmalar.filter((c) => c.doimiy || c.qolgan_oylar > 0);
            const c = faol[0];
            return (
              <tr key={x.azolik_moliya_id}>
                <td>{x.talaba}</td>
                <td className="ongga">{c ? (c.doimiy ? t("doimiy") : `${c.qolgan_oylar} ${t("oy")}`) : t("yoq")}</td>
                <td>{c ? `${oyNomi(String(c.boshlanish_oy).slice(0, 7), til)} → ${c.doimiy ? "∞" : oyNomi(String(c.oxirgi_oy).slice(0, 7), til)}` : "—"}</td>
                <td>{c?.kim || "—"}</td>
                <td>{c?.izoh || "—"}</td>
                <td className="ongga">{c ? `${pul(c.narx)} (${x.narx ? Math.round((1 - c.narx / x.narx) * 100) : 0}%)` : "—"}</td>
                <td className="amallar">
                  {ruxsat("guruhlar.chegirma") && (
                    <>
                      <button className="havola" type="button" title={t("chegirma_berish")} onClick={() => setOyna(x)}>＋</button>
                      {c && <button className="havola rang-qarzdor" type="button" onClick={() => ochir(c.id)}>🗑</button>}
                    </>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {oyna && (
        <div className="oyna-fon" role="dialog" aria-modal="true">
          <div className="karta oyna">
            <h2>{t("chegirma_berish")}</h2>
            <p className="kichik">{oyna.talaba} · {t("odatiy_narx")}: {pul(oyna.narx)}</p>
            <div className="tablar">
              {["summada", "foizda", "narx"].map((r) => (
                <button key={r} type="button" className={rejim === r ? "tab faol" : "tab"} onClick={() => setRejim(r)}>
                  {t(`chegirma_${r}`)}
                </button>
              ))}
            </div>
            <label>
              {rejim === "foizda" ? t("chegirma_foizi") : rejim === "summada" ? t("chegirma_summasi") : `${t("chegirmadagi_narx")} (${t("nol_tekin")})`}
              <input type="number" min="0" max={rejim === "foizda" ? 100 : undefined} step={rejim === "foizda" ? 1 : 1000}
                     value={f.qiymat} onChange={(e) => setF((x) => ({ ...x, qiymat: e.target.value }))} autoFocus />
            </label>
            {f.qiymat !== "" && oyna.narx && (
              <p className="kichik">
                {t("chegirmadagi_narx")}: <b>{pul(
                  rejim === "foizda" ? oyna.narx * (100 - Number(f.qiymat)) / 100
                    : rejim === "summada" ? oyna.narx - Number(f.qiymat) : Number(f.qiymat)
                )}</b>
              </p>
            )}
            <div className="ikki-ustun">
              <label>{t("qaysi_oydan")}<input type="month" value={f.boshlanish_oy} onChange={(e) => setF((x) => ({ ...x, boshlanish_oy: e.target.value }))} /></label>
              <label>{t("necha_oy")} ({t("nol_doimiy")})<input type="number" min="0" max="24" value={f.oylar_soni} onChange={(e) => setF((x) => ({ ...x, oylar_soni: e.target.value }))} /></label>
            </div>
            <label>{t("izoh")}<input value={f.izoh} onChange={(e) => setF((x) => ({ ...x, izoh: e.target.value }))} /></label>
            {xatoQ && <div className="xato">{xatoQ}</div>}
            <div className="oyna-tugmalar">
              <button className="tugma tugma-sokin" type="button" onClick={() => setOyna(null)}>{t("bekor")}</button>
              <button className="tugma" type="button" onClick={saqla} disabled={f.qiymat === ""}>{t("saqlash")}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Baholar (SoffCRM "BAHO" tabi) ───────────────────────────────────

export function Baholar({ guruhId }) {
  const { t, til } = useI18n();
  const ruxsat = useRuxsat();
  const [oy, setOy] = useState(() => new Date().toISOString().slice(0, 7));
  const { malumot, yuklanmoqda, xato, yangila } = useSorov(`/api/crm/guruhlar/${guruhId}/baholar/` + sorovSatri({ oy }));
  const [xatoQ, setXatoQ] = useState("");
  const tahrirlaydi = ruxsat("guruhlar.davomat");

  function siljit(qadam) {
    const [y, o] = oy.split("-").map(Number);
    const d = new Date(y, o - 1 + qadam, 1);
    setOy(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  }

  async function saqla(talabaId, sanaQ, ball) {
    setXatoQ("");
    try {
      await api(`/api/crm/guruhlar/${guruhId}/baholar/`, { method: "POST", body: { talaba_id: talabaId, sana: sanaQ, ball } });
      yangila();
    } catch (e) {
      setXatoQ(e.message);
    }
  }

  if (yuklanmoqda && !malumot) return <p className="kichik">{t("yuklanmoqda")}</p>;
  const sanalar = malumot?.sanalar || [];
  const tizim = malumot?.tizim;
  return (
    <>
      <div className="filtrlar">
        <div className="oy-tanlash">
          <button className="tugma tugma-sokin" type="button" onClick={() => siljit(-1)}>‹</button>
          <b>{oyNomi(oy, til)}</b>
          <button className="tugma tugma-sokin" type="button" onClick={() => siljit(1)}>›</button>
        </div>
        {tizim && <span className="belgi">{t("baholash_tizimi")}: {tizim === "100" ? "0–100" : `1–${tizim}`}</span>}
      </div>
      {(xato || xatoQ) && <div className="xato">{xato || xatoQ}</div>}
      {!tizim ? (
        <p className="kichik">{t("baholash_yoq_izoh")}</p>
      ) : (
        <div className="jadval-oram">
          <table className="davomat-jadval">
            <thead>
              <tr>
                <th>{t("talaba")}</th>
                {sanalar.map((s) => <th key={s} className="markazga" title={sana(s)}>{String(s).slice(8, 10)}</th>)}
                <th className="ongga">{t("ortacha")}</th>
              </tr>
            </thead>
            <tbody>
              {(malumot?.talabalar || []).map((x) => (
                <tr key={x.id}>
                  <td>{x.ism}</td>
                  {x.baholar.map((b, i) => (
                    <td key={sanalar[i]} className="markazga">
                      <input
                        className="baho-katak"
                        type="number"
                        min={tizim === "100" ? 0 : 1}
                        max={tizim}
                        defaultValue={b ?? ""}
                        disabled={!tahrirlaydi}
                        aria-label={`${x.ism} ${sana(sanalar[i])}`}
                        onBlur={(e) => {
                          const yangi = e.target.value;
                          if (String(yangi) !== String(b ?? "")) saqla(x.id, sanalar[i], yangi === "" ? null : yangi);
                        }}
                      />
                    </td>
                  ))}
                  <td className="ongga"><b>{x.ortacha ?? "—"}</b></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
