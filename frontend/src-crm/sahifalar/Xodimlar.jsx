// Xodimlar va rollar (video-TZ, 2026-09-23) — SoffCRM "Sozlamalar ->
// Xodimlar": lavozim tablari, "Xodim qo'shish" oynasi (filial, rol,
// foiz ulushi, oylik) va "Yangi rol yaratish" (ruxsatlar daraxti).

import { useState } from "react";

import { api, apiFayluniYuklab } from "../api.js";
import { useFilial } from "../filialContext.jsx";
import { oyNomi, pul, sana } from "../format.js";
import { useI18n } from "../i18n.jsx";
import { useProfil, useRuxsat } from "../profilContext.jsx";
import { sorovSatri, useSorov } from "../soragich.js";

const LAVOZIMLAR = ["admin", "ceo", "oqituvchi", "support", "kassir", "marketolog", "watcher", "boshqa"];

// ── Parol ko'rsatish (bir marta) ────────────────────────────────────

function ParolXabari({ malumot, onYopish }) {
  const { t } = useI18n();
  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna">
        <h2>{malumot.ism}</h2>
        <p className="kichik">{t("login_parol_eslatma")}</p>
        <div className="qator"><span className="kichik">{t("login")}</span><code>{malumot.username}</code></div>
        <div className="qator"><span className="kichik">{t("parol")}</span><code>{malumot.parol}</code></div>
        <div className="oyna-tugmalar">
          <button className="tugma" type="button" onClick={onYopish}>{t("yopish")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Xodim oynasi ────────────────────────────────────────────────────

function XodimOynasi({ xodim, rollar, onYopish, onSaqlandi, onYangiRol }) {
  const { t } = useI18n();
  const profil = useProfil();
  const ruxsat = useRuxsat();
  // Oylik/ulush yashirin bo'lsa (`null`) — ular formada ko'rinmaydi va
  // YUBORILMAYDI: aks holda bo'sh qiymat oylikni 0 ga tushirardi.
  const oylikKorinadi = ruxsat("xodimlar.oylik");
  // Maxsus rolni faqat rollarni boshqaradigan beradi (backend ham tekshiradi).
  const rolBeradi = ruxsat("sozlamalar.rollar");
  const { filiallar } = useFilial();
  const [f, setF] = useState(() => ({
    ism: xodim?.ism || "",
    telefon: xodim?.telefon || "+998",
    tugilgan_sana: xodim?.tugilgan_sana || "",
    ishga_olingan_sana: xodim?.ishga_olingan_sana || new Date().toISOString().slice(0, 10),
    filial_id: xodim?.filial_id ?? "",
    lavozim: xodim?.lavozim || "oqituvchi",
    rol_id: xodim?.rol_id ?? "",
    foiz_ulushi: xodim?.foiz_ulushi ?? 0,
    oylik: xodim?.oylik ?? "",
    jins: xodim?.jins || "erkak",
    login: "",
    parol: "",
  }));
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);
  const qiymat = (k) => ({ value: f[k] ?? "", onChange: (e) => setF((x) => ({ ...x, [k]: e.target.value })) });
  // Administrator/CEO'ni faqat owner beradi (backend ham tekshiradi).
  const lavozimlar = LAVOZIMLAR.filter((l) => profil?.is_owner || !["admin", "ceo"].includes(l) || l === xodim?.lavozim);

  async function saqla() {
    setXato("");
    setBand(true);
    try {
      const body = { ...f, rol_id: f.rol_id || null, filial_id: f.filial_id || null };
      if (!oylikKorinadi) {
        delete body.oylik;
        delete body.foiz_ulushi;
      }
      if (!rolBeradi) delete body.rol_id;
      if (xodim) {
        delete body.login;
        if (!body.parol) delete body.parol;
      }
      const javob = await api(xodim ? `/api/crm/xodimlar/${xodim.id}/` : "/api/crm/xodimlar/", {
        method: xodim ? "PATCH" : "POST",
        body,
      });
      onSaqlandi(javob);
    } catch (e) {
      setXato(e.message);
    } finally {
      setBand(false);
    }
  }

  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna oyna-keng">
        <h2>{xodim ? t("xodim_tahrirlash") : t("xodim_qoshish")}</h2>
        <label>{t("ism_familiya")}<input {...qiymat("ism")} autoFocus /></label>
        <div className="ikki-ustun">
          <label>{t("telefon")}<input {...qiymat("telefon")} /></label>
          <label>{t("tugilgan_sana")}<input type="date" {...qiymat("tugilgan_sana")} /></label>
        </div>
        <div className="ikki-ustun">
          <label>{t("ishga_olingan_sana")}<input type="date" {...qiymat("ishga_olingan_sana")} /></label>
          <label>{t("filial")}
            <select {...qiymat("filial_id")}>
              <option value="">—</option>
              {filiallar.map((x) => <option key={x.id} value={x.id}>{x.nomi}</option>)}
            </select>
          </label>
        </div>
        <div className="ikki-ustun">
          <label>{t("lavozim")}
            <select {...qiymat("lavozim")}>
              {lavozimlar.map((l) => <option key={l} value={l}>{t(`lavozim_${l}`)}</option>)}
            </select>
          </label>
          <label>{t("rol")}
            <select value={f.rol_id ?? ""} disabled={!rolBeradi} onChange={(e) => {
              if (e.target.value === "__yangi") { onYangiRol(); return; }
              setF((x) => ({ ...x, rol_id: e.target.value }));
            }}>
              <option value="">{t("lavozim_boyicha")}</option>
              {/* Lavozim rollari bu ro'yxatda yo'q — ular lavozimning o'zi bilan keladi. */}
              {rollar.filter((r) => r.faol && !r.lavozim).map((r) => <option key={r.id} value={r.id}>{r.nomi}</option>)}
              {rolBeradi && <option value="__yangi">+ {t("yangi_rol_yaratish")}</option>}
            </select>
          </label>
        </div>
        {oylikKorinadi && (
          <div className="ikki-ustun">
            <label>{t("foiz_ulushi")} (%)<input type="number" min="0" max="100" {...qiymat("foiz_ulushi")} /></label>
            <label>{t("oylik_ish_haqi")}<input type="number" min="0" step="100000" {...qiymat("oylik")} /></label>
          </div>
        )}
        <fieldset className="radio-qator">
          <legend className="kichik">{t("jinsi")}</legend>
          {["erkak", "ayol"].map((j) => (
            <label key={j} className="yonma">
              <input type="radio" name="jins" checked={f.jins === j} onChange={() => setF((x) => ({ ...x, jins: j }))} />
              {t(`jins_${j}`)}
            </label>
          ))}
        </fieldset>
        {!xodim && (
          <div className="ikki-ustun">
            <label>{t("login")}<input {...qiymat("login")} placeholder={t("avtomatik")} /></label>
            <label>{t("parol")}<input {...qiymat("parol")} placeholder={t("avtomatik")} /></label>
          </div>
        )}
        {xodim && (
          <label>{t("yangi_parol")}<input {...qiymat("parol")} placeholder={t("ozgarmasin_bosh")} /></label>
        )}
        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
          <button className="tugma" type="button" onClick={saqla} disabled={band}>{t("saqlash")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Rol oynasi (ruxsatlar daraxti) ──────────────────────────────────

function RolOynasi({ rol, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const profil = useProfil();
  const daraxt = profil?.ruxsat_daraxti || [];
  // Tizim roli (lavozim: kassir, marketolog...) — faqat ruxsatlari tahrirlanadi.
  const tizim = Boolean(rol?.lavozim);
  const [nomi, setNomi] = useState(rol?.nomi || "");
  const [faol, setFaol] = useState(rol?.faol ?? true);
  const [tanlangan, setTanlangan] = useState(() => new Set(rol?.ruxsatlar || []));
  const [ochiq, setOchiq] = useState(null);
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  function almashtir(kalitlar, yoq) {
    const yangi = new Set(tanlangan);
    kalitlar.forEach((k) => (yoq ? yangi.add(k) : yangi.delete(k)));
    setTanlangan(yangi);
  }

  async function saqla() {
    setXato("");
    setBand(true);
    try {
      await api(rol ? `/api/crm/rollar/${rol.id}/` : "/api/crm/rollar/", {
        method: rol ? "PATCH" : "POST",
        body: tizim ? { ruxsatlar: [...tanlangan] } : { nomi, faol, ruxsatlar: [...tanlangan] },
      });
      onSaqlandi();
      onYopish();
    } catch (e) {
      setXato(e.message);
    } finally {
      setBand(false);
    }
  }

  const komponentSoni = daraxt.reduce((s, b) => s + b.bolalar.filter((x) => tanlangan.has(x.kalit)).length, 0);
  const bolimSoni = daraxt.filter((b) => b.bolalar.some((x) => tanlangan.has(x.kalit)) || tanlangan.has(b.kalit)).length;

  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna oyna-keng">
        <h2>{rol ? t("rolni_tahrirlash") : t("yangi_rol_yaratish")}</h2>
        {tizim && <p className="kichik">{t("lavozim_roli_izoh")}</p>}
        <div className="ikki-ustun">
          <label>{t("rol_nomi")}<input value={nomi} onChange={(e) => setNomi(e.target.value)} autoFocus disabled={tizim} /></label>
          <label className="yonma">
            <input type="checkbox" checked={faol} onChange={(e) => setFaol(e.target.checked)} disabled={tizim} /> {t("faol")}
          </label>
        </div>
        <h3>{t("joriy_ruxsatlar")}</h3>
        <div className="ruxsat-daraxt">
          {daraxt.map((b) => {
            const bolaKalitlari = b.bolalar.map((x) => x.kalit);
            const nechta = bolaKalitlari.filter((k) => tanlangan.has(k)).length;
            const hammasi = nechta === bolaKalitlari.length && tanlangan.has(b.kalit);
            return (
              <div key={b.kalit} className="ruxsat-bolim">
                <div className="ruxsat-bolim-bosh">
                  <label className="yonma">
                    <input type="checkbox" checked={hammasi}
                           ref={(el) => { if (el) el.indeterminate = nechta > 0 && !hammasi; }}
                           onChange={(e) => almashtir([b.kalit, ...bolaKalitlari], e.target.checked)} />
                    <b>{b.nomi}</b>
                  </label>
                  <span className="kichik">{nechta} {t("ta_korinadi")}</span>
                  <button className="havola" type="button" onClick={() => setOchiq(ochiq === b.kalit ? null : b.kalit)}>
                    {ochiq === b.kalit ? "▾" : "▸"}
                  </button>
                </div>
                {ochiq === b.kalit && (
                  <div className="ruxsat-bolalar">
                    {b.bolalar.map((x) => (
                      <label key={x.kalit} className="yonma">
                        <input type="checkbox" checked={tanlangan.has(x.kalit)}
                               onChange={(e) => almashtir([x.kalit, ...(e.target.checked ? [b.kalit] : [])], e.target.checked)} />
                        {x.nomi}
                      </label>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        <p className="kichik">{t("jami")}: {bolimSoni} {t("ta_bolim")}, {komponentSoni} {t("ta_komponent")}</p>
        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
          <button className="tugma" type="button" onClick={saqla} disabled={band || !nomi.trim()}>{t("saqlash")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Xodimlar davomati (SoffCRM "XODIMLAR DAVOMATI") ────────────────

const XD_HOLATLAR = [null, "keldi", "kechikdi", "kelmadi", "sababli"];
const XD_BELGI = { keldi: "✓", kechikdi: "⏰", kelmadi: "✕", sababli: "◐" };

function XodimlarDavomati() {
  const { t, til } = useI18n();
  const ruxsat = useRuxsat();
  const [oy, setOy] = useState(() => new Date().toISOString().slice(0, 7));
  const { malumot, xato, yangila } = useSorov("/api/crm/xodimlar/davomat/" + sorovSatri({ oy }));
  const [xatoQ, setXatoQ] = useState("");
  const bugun = new Date().toISOString().slice(0, 10);
  const tahrirlaydi = ruxsat("xodimlar.tahrirlash");

  function siljit(qadam) {
    const [y, o] = oy.split("-").map(Number);
    const d = new Date(y, o - 1 + qadam, 1);
    setOy(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  }

  async function belgila(xodimId, kun, joriy) {
    const keyingi = XD_HOLATLAR[(XD_HOLATLAR.indexOf(joriy?.holat ?? null) + 1) % XD_HOLATLAR.length];
    setXatoQ("");
    try {
      await api("/api/crm/xodimlar/davomat/", { method: "POST", body: { xodim_id: xodimId, sana: kun, holat: keyingi } });
      yangila();
    } catch (e) {
      setXatoQ(e.message);
    }
  }

  const kunlar = malumot?.kunlar || [];
  return (
    <div className="karta">
      <div className="karta-sarlavha">
        <h2>{t("xodimlar_davomati")}</h2>
        <div className="oy-tanlash">
          <button className="tugma tugma-sokin" type="button" onClick={() => siljit(-1)}>‹</button>
          <b>{oyNomi(oy, til)}</b>
          <button className="tugma tugma-sokin" type="button" onClick={() => siljit(1)}>›</button>
        </div>
      </div>
      <p className="kichik">✓ {t("xd_keldi")} · ⏰ {t("xd_kechikdi")} · ✕ {t("xd_kelmadi")} · ◐ {t("xd_sababli")}</p>
      {(xato || xatoQ) && <div className="xato">{xato || xatoQ}</div>}
      <div className="jadval-oram">
        <table className="davomat-jadval">
          <thead>
            <tr>
              <th>{t("ism_familiya")}</th>
              {kunlar.map((k) => <th key={k} className="markazga">{String(k).slice(8, 10)}</th>)}
              <th className="ongga">✓</th><th className="ongga">⏰</th><th className="ongga">✕</th>
            </tr>
          </thead>
          <tbody>
            {(malumot?.xodimlar || []).map((x) => (
              <tr key={x.id}>
                <td className="nowrap">{x.ism}</td>
                {x.kunlar.map((q, i) => (
                  <td key={kunlar[i]} className="markazga">
                    <button type="button" className={`davomat-katak davomat-${q?.holat === "kechikdi" ? "sababli" : q?.holat || "yoq"}`}
                            disabled={!tahrirlaydi || kunlar[i] > bugun} onClick={() => belgila(x.id, kunlar[i], q)}>
                      {XD_BELGI[q?.holat] || "·"}
                    </button>
                  </td>
                ))}
                <td className="ongga rang-tolandi">{x.jami.keldi || 0}</td>
                <td className="ongga rang-qisman">{x.jami.kechikdi || 0}</td>
                <td className="ongga rang-qarzdor">{x.jami.kelmadi || 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Sahifa ──────────────────────────────────────────────────────────

export default function Xodimlar() {
  const { t } = useI18n();
  const ruxsat = useRuxsat();
  const [lavozim, setLavozim] = useState("");
  const [arxiv, setArxiv] = useState(false);
  const [qidiruv, setQidiruv] = useState("");
  const [tahrir, setTahrir] = useState(undefined); // undefined yopiq, null yangi, obyekt tahrir
  const [rolOyna, setRolOyna] = useState(undefined);
  const [parol, setParol] = useState(null);
  const [davomatKorsin, setDavomatKorsin] = useState(false);
  const [amalXato, setAmalXato] = useState("");
  const profil = useProfil();
  // Boshqa xodimning parolini faqat owner yoki administrator tiklaydi (backend ham).
  const parolTiklaydi = profil?.is_owner || profil?.role === "admin";

  const sorov = useSorov("/api/crm/xodimlar/" + sorovSatri({ lavozim, arxiv: arxiv ? 1 : "", q: qidiruv }));
  const rollar = useSorov("/api/crm/rollar/");
  const xodimlar = sorov.malumot?.xodimlar || [];
  const soni = sorov.malumot?.soni || {};

  async function faolAlmashtir(x) {
    setAmalXato("");
    try {
      await api(`/api/crm/xodimlar/${x.id}/`, { method: "PATCH", body: { faol: !x.faol } });
      sorov.yangila();
    } catch (e) {
      setAmalXato(e.message);
    }
  }

  async function parolTiklash(x) {
    if (!window.confirm(t("parol_tiklash_tasdiq"))) return;
    setAmalXato("");
    try {
      const javob = await api(`/api/crm/xodimlar/${x.id}/`, { method: "PATCH", body: { parol_tiklash: 1 } });
      setParol(javob);
    } catch (e) {
      setAmalXato(e.message);
    }
  }

  return (
    <section>
      <div className="karta-sarlavha">
        <h1>{t("xodimlar")}</h1>
        <div className="tezkor-amallar">
          <button className="tugma tugma-sokin" type="button"
                  onClick={() => apiFayluniYuklab("/api/crm/xodimlar/eksport/" + sorovSatri({ arxiv: arxiv ? 1 : "" }))}>
            ⬇ Excel
          </button>
          <button className={davomatKorsin ? "tugma" : "tugma tugma-sokin"} type="button" onClick={() => setDavomatKorsin(!davomatKorsin)}>
            📅 {t("xodimlar_davomati")}
          </button>
          {ruxsat("sozlamalar.rollar") && (
            <button className="tugma tugma-sokin" type="button" onClick={() => setRolOyna(null)}>+ {t("yangi_rol_yaratish")}</button>
          )}
          {ruxsat("xodimlar.qoshish") && (
            <button className="tugma" type="button" onClick={() => setTahrir(null)}>+ {t("yangi_qoshish")}</button>
          )}
        </div>
      </div>

      <div className="tablar">
        <button type="button" className={!lavozim ? "tab faol" : "tab"} onClick={() => setLavozim("")}>
          {t("barchasi")} — {sorov.malumot?.jami ?? 0}
        </button>
        {LAVOZIMLAR.map((l) => (
          <button key={l} type="button" className={lavozim === l ? "tab faol" : "tab"} onClick={() => setLavozim(l)}>
            {t(`lavozim_${l}`)} — {soni[l] || 0}
          </button>
        ))}
      </div>

      <div className="filtrlar">
        <input placeholder={t("xodim_qidirish")} value={qidiruv} onChange={(e) => setQidiruv(e.target.value)} />
        <label className="yonma">
          <input type="checkbox" checked={arxiv} onChange={(e) => setArxiv(e.target.checked)} /> {t("arxiv")}
        </label>
      </div>

      {(sorov.xato || amalXato) && <div className="xato">{sorov.xato || amalXato}</div>}
      <div className="karta jadval-oram">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>{t("ism_familiya")}</th>
              <th>{t("telefon")}</th>
              <th className="ongga">{t("doimiy_oylik")}</th>
              <th className="ongga">{t("foiz_ulushi")}</th>
              <th>{t("kasbi")}</th>
              <th>{t("filial")}</th>
              <th>{t("ishga_olingan_sana")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {xodimlar.map((x, i) => (
              <tr key={x.id} className={x.faol ? "" : "qator-sokin"}>
                <td>{i + 1}</td>
                <td>{x.ism}<div className="kichik">{x.username}</div></td>
                <td>{x.telefon || "—"}</td>
                <td className="ongga">{x.oylik === null ? "•••" : `${pul(x.oylik)} UZS`}</td>
                <td className="ongga">{x.foiz_ulushi === null ? "•••" : `${Number(x.foiz_ulushi)} %`}</td>
                <td>{t(`lavozim_${x.lavozim}`)}{x.rol ? <div className="kichik">{x.rol}</div> : null}</td>
                <td>{x.filial || "—"}</td>
                <td className="nowrap">{sana(x.ishga_olingan_sana)}</td>
                <td className="amallar">
                  {ruxsat("xodimlar.tahrirlash") && (
                    <>
                      <button className="havola" type="button" title={t("tahrirlash")} onClick={() => setTahrir(x)}>✎</button>
                      {parolTiklaydi && (
                        <button className="havola" type="button" title={t("parol_tiklash")} onClick={() => parolTiklash(x)}>🔑</button>
                      )}
                      <button className="havola" type="button" onClick={() => faolAlmashtir(x)}>
                        {x.faol ? t("arxivlash") : t("faollashtirish")}
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {!sorov.yuklanmoqda && xodimlar.length === 0 && (
              <tr><td colSpan={9} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {davomatKorsin && <XodimlarDavomati />}

      <div className="karta">
        <h2>{t("rollar")}</h2>
        <table>
          <thead>
            <tr><th>{t("rol_nomi")}</th><th>{t("holat")}</th><th className="ongga">{t("xodimlar")}</th><th className="ongga">{t("ruxsatlar_soni")}</th><th /></tr>
          </thead>
          <tbody>
            {(rollar.malumot || []).map((r) => (
              <tr key={r.id}>
                <td>{r.nomi}{r.lavozim && <span className="belgi"> {t("lavozim_roli")}</span>}</td>
                <td>{r.faol ? t("faol") : t("nofaol")}</td>
                <td className="ongga">{r.xodimlar_soni ?? 0}</td>
                <td className="ongga">{r.ruxsatlar.length}</td>
                <td className="amallar">
                  {ruxsat("sozlamalar.rollar") && (
                    <button className="havola" type="button" onClick={() => setRolOyna(r)}>✎</button>
                  )}
                </td>
              </tr>
            ))}
            {(rollar.malumot || []).length === 0 && (
              <tr><td colSpan={5} className="bosh">{t("rol_yoq_izoh")}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {tahrir !== undefined && (
        <XodimOynasi
          xodim={tahrir}
          rollar={rollar.malumot || []}
          onYopish={() => setTahrir(undefined)}
          onYangiRol={() => setRolOyna(null)}
          onSaqlandi={(javob) => {
            setTahrir(undefined);
            sorov.yangila();
            if (javob?.parol) setParol(javob);
          }}
        />
      )}
      {rolOyna !== undefined && (
        <RolOynasi rol={rolOyna} onYopish={() => setRolOyna(undefined)} onSaqlandi={rollar.yangila} />
      )}
      {parol && <ParolXabari malumot={parol} onYopish={() => setParol(null)} />}
    </section>
  );
}
