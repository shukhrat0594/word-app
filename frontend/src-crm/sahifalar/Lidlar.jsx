// Lidlar (video-TZ, 2026-09-23) — SoffCRM "Lidlar" kanbani.
//
// Ustunlar — erkin bo'limlar ("New leads", "Beginner", "Rus tili"...).
// Bo'limsiz lidlar birinchi "Yangi lidlar" ustunida. Kartochkani
// sudrab boshqa ustunga tashlash mumkin. Lid guruhga qo'shilganda undan
// talaba yaratiladi va lid arxivga o'tadi (backend: `LidGuruhgaView`).

import { useState } from "react";

import { api, apiFayluniYuklab } from "../api.js";
import Eslatmalar from "../Eslatmalar.jsx";
import { useFilial } from "../filialContext.jsx";
import { sana, vaqt } from "../format.js";
import { useI18n } from "../i18n.jsx";
import { SababOynasi } from "../OquvchiAmallari.jsx";
import { useCheklangan, useProfil, useRuxsat } from "../profilContext.jsx";
import { sorovSatri, useSorov } from "../soragich.js";

// SoffCRM "Manba" ro'yxati (video 06:15). Ro'yxatda yo'q manba ham
// yozilishi mumkin (datalist) — SoffCRM'dagi "Yangi yaratish +".
const MANBALAR = [
  "Instagram", "Telegram", "Tavsiya", "Oldin o'zimizda o'qigan", "Banner", "Flayer", "ChatGPT",
  "Google", "Yandex karta", "Boshqa",
];
const HOLATLAR = ["yangi", "boglanildi", "boglana_olmadi", "sinov", "kelmadi", "oylayapti", "yoqotilgan"];
const HARORATLAR = ["issiq", "iliq", "sovuq"];
// Arxivlash sabablari — SoffCRM'dagi ro'yxat (video-TZ 2026-09-25);
// "Boshqa sabab"da izoh majburiy (backend ham tekshiradi).
const ARXIV_SABABLARI = ["kelmadi", "raqobatchi", "boshqa_filial", "boshqa"];

/** Tug'ilgan sanadan yosh ("28 yosh") — SoffCRM formasidagi "Yoshi". */
function yosh(tugilgan) {
  if (!tugilgan) return "";
  const b = new Date();
  const d = new Date(tugilgan);
  let y = b.getFullYear() - d.getFullYear();
  if (b.getMonth() < d.getMonth() || (b.getMonth() === d.getMonth() && b.getDate() < d.getDate())) y -= 1;
  return y >= 0 ? y : "";
}
const KUNLAR = ["toq", "juft", "har_kuni", "boshqa"];

// ── Lid formasi (yaratish va tahrir) ────────────────────────────────

function LidForma({ lid, bolimlar, onSaqla, onBekor, band, xato }) {
  const { t } = useI18n();
  const { filiallar, tanlangan } = useFilial();
  // `tanlov=1` — hamma o'qituvchi (filialidan qat'i nazar, qaror 2026-09-23).
  const oqituvchilar = useSorov("/api/crm/xodimlar/?lavozim=oqituvchi&tanlov=1");
  const kurslar = useSorov("/api/crm/kurs-narxlari/");
  // "Dars vaqtini tanlang" — mavjud guruhlar boshlanish vaqtlari (video 07:20).
  const guruhlar = useSorov("/api/crm/guruhlar/");
  const vaqtlar = [...new Set((guruhlar.malumot || []).flatMap((g) => g.jadval.map((j) => j.boshlanish_vaqti)))].sort();
  const [f, setF] = useState(() => ({
    ism: lid?.ism || "",
    telefon: lid?.telefon || "+998",
    qoshimcha_telefon: lid?.qoshimcha_telefon || "",
    qoshimcha_ism: lid?.qoshimcha_ism || "",
    tugilgan_sana: lid?.tugilgan_sana || "",
    manba: lid?.manba || "",
    bolim_id: lid?.bolim_id ?? "",
    holat: lid?.holat || "yangi",
    harorat: lid?.harorat || "",
    filial_id: lid?.filial_id ?? tanlangan ?? "",
    kurs_id: lid?.kurs_id ?? "",
    oqituvchi_id: lid?.oqituvchi_id ?? "",
    qulay_vaqt: lid?.qulay_vaqt || "",
    kunlar: lid?.kunlar || "",
    izoh: lid?.izoh || "",
  }));
  const qiymat = (k) => ({ value: f[k], onChange: (e) => setF((x) => ({ ...x, [k]: e.target.value })) });

  return (
    <>
      <label>{t("ism_familiya")}<input {...qiymat("ism")} autoFocus /></label>
      <div className="ikki-ustun">
        <label>{t("telefon")}<input {...qiymat("telefon")} /></label>
        <label>
          {t("tugilgan_sana")}{f.tugilgan_sana && ` · ${yosh(f.tugilgan_sana)} ${t("yosh")}`}
          <input type="date" {...qiymat("tugilgan_sana")} />
        </label>
      </div>
      <div className="ikki-ustun">
        <label>{t("qoshimcha_telefon")}<input {...qiymat("qoshimcha_telefon")} /></label>
        <label>{t("kimning_raqami")}<input {...qiymat("qoshimcha_ism")} placeholder={t("masalan_oyisi")} /></label>
      </div>
      <div className="ikki-ustun">
        <label>{t("bolim")}
          <select {...qiymat("bolim_id")}>
            <option value="">{t("yangi_lidlar")}</option>
            {bolimlar.map((b) => <option key={b.id} value={b.id}>{b.nomi}</option>)}
          </select>
        </label>
        <label>{t("holat")}
          <select {...qiymat("holat")}>
            {HOLATLAR.map((h) => <option key={h} value={h}>{t(`lid_${h}`)}</option>)}
          </select>
        </label>
      </div>
      <label>{t("harorat")}
        <select {...qiymat("harorat")}>
          <option value="">—</option>
          {HARORATLAR.map((h) => <option key={h} value={h}>{t(`harorat_${h}`)}</option>)}
        </select>
      </label>
      <div className="ikki-ustun">
        <label>{t("manba")}
          <input list="lid-manbalar" {...qiymat("manba")} />
          <datalist id="lid-manbalar">{MANBALAR.map((m) => <option key={m} value={m} />)}</datalist>
        </label>
        <label>{t("filial")}
          <select {...qiymat("filial_id")}>
            <option value="">—</option>
            {filiallar.map((x) => <option key={x.id} value={x.id}>{x.nomi}</option>)}
          </select>
        </label>
      </div>
      <div className="ikki-ustun">
        <label>{t("kurs")}
          <select {...qiymat("kurs_id")}>
            <option value="">—</option>
            {(kurslar.malumot || []).map((k) => (
              <option key={k.daraja_id} value={k.daraja_id}>{k.fan ? `${k.fan} — ` : ""}{k.daraja}</option>
            ))}
          </select>
        </label>
        <label>{t("oqituvchi")}
          <select {...qiymat("oqituvchi_id")}>
            <option value="">—</option>
            {(oqituvchilar.malumot?.xodimlar || []).map((o) => <option key={o.id} value={o.id}>{o.ism}</option>)}
          </select>
        </label>
      </div>
      <div className="ikki-ustun">
        <label>{t("qulay_vaqt")}
          <input list="lid-vaqtlar" {...qiymat("qulay_vaqt")} placeholder="18:30" />
          <datalist id="lid-vaqtlar">{vaqtlar.map((v) => <option key={v} value={v} />)}</datalist>
        </label>
        <label>{t("kunlar")}
          <select {...qiymat("kunlar")}>
            <option value="">—</option>
            {KUNLAR.map((k) => <option key={k} value={k}>{t(`kunlar_${k}`)}</option>)}
          </select>
        </label>
      </div>
      <label>{t("izoh")}<input {...qiymat("izoh")} /></label>
      {xato && <div className="xato">{xato}</div>}
      <div className="oyna-tugmalar">
        <button className="tugma tugma-sokin" type="button" onClick={onBekor}>{t("bekor")}</button>
        <button className="tugma" type="button" disabled={band} onClick={() => onSaqla(f)}>{t("saqlash")}</button>
      </div>
    </>
  );
}

function YangiLidOynasi({ bolimlar, bolimId, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const [band, setBand] = useState(false);
  const [xato, setXato] = useState("");

  async function saqla(f, majburan = false) {
    setBand(true);
    setXato("");
    try {
      await api("/api/crm/lidlar/", { method: "POST", body: { ...f, majburan } });
      onSaqlandi();
      onYopish();
    } catch (e) {
      // 409 — raqam qora ro'yxatda: ogohlantirib, baribir qo'shishga ruxsat.
      if (e.status === 409 && window.confirm(`${e.message}. ${t("baribir_qoshilsinmi")}`)) {
        return saqla(f, true);
      }
      setXato(e.message);
    } finally {
      setBand(false);
    }
  }

  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna oyna-keng">
        <h2>{t("yangi_lid")}</h2>
        <LidForma lid={bolimId ? { bolim_id: bolimId } : null} bolimlar={bolimlar}
                  onSaqla={saqla} onBekor={onYopish} band={band} xato={xato} />
      </div>
    </div>
  );
}

// ── Guruhga qo'shish oynasi (bitta yoki bir nechta lid) ─────────────

export function GuruhgaQoshishOynasi({ lidIdlar, standartGuruh = "", onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const { tanlangan, filiallar } = useFilial();
  // "Guruhni tezroq topish uchun filtrlar" (video 17:30): filial, ustoz, kurs.
  const [filialF, setFilialF] = useState(tanlangan || "");
  const [ustozF, setUstozF] = useState("");
  const [kursF, setKursF] = useState("");
  const guruhlar = useSorov("/api/crm/guruhlar/" + sorovSatri({ filial: filialF }));
  const hammasi = guruhlar.malumot || [];
  const royxat = hammasi.filter(
    (g) => (!ustozF || g.oqituvchi === ustozF) && (!kursF || String(g.daraja?.id) === kursF)
  );
  const [guruhId, setGuruhId] = useState(standartGuruh ? String(standartGuruh) : "");
  const [holat, setHolat] = useState("sinov");
  const [sanaQ, setSanaQ] = useState(new Date().toISOString().slice(0, 10));
  const [natija, setNatija] = useState(null);
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  async function saqla() {
    setBand(true);
    setXato("");
    try {
      const javob = await api("/api/crm/lidlar/guruhga/", {
        method: "POST",
        body: { lid_idlar: lidIdlar, guruh_id: guruhId, holat, boshlanish_sana: sanaQ },
      });
      setNatija(javob.qoshildi);
      onSaqlandi();
    } catch (e) {
      setXato(e.message);
    } finally {
      setBand(false);
    }
  }

  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna">
        <h2>{t("guruhga_qoshish")} ({lidIdlar.length})</h2>
        {natija ? (
          <>
            {/* Yangi talabalarning login/paroli FAQAT shu yerda bir marta
                ko'rsatiladi — admin yozib olib, talabaga beradi. */}
            <p className="kichik">{t("login_parol_eslatma")}</p>
            <ul className="login-royxat">
              {natija.map((x) => (
                <li key={x.talaba_id}>
                  <b>{x.ism}</b> — {t("login")}: <code>{x.username}</code>
                  {x.parol && <> · {t("parol")}: <code>{x.parol}</code></>}
                </li>
              ))}
            </ul>
            <div className="oyna-tugmalar">
              <button className="tugma" type="button" onClick={onYopish}>{t("yopish")}</button>
            </div>
          </>
        ) : (
          <>
            <div className="uch-ustun">
              <select value={filialF} onChange={(e) => setFilialF(e.target.value)} aria-label={t("filial")}>
                <option value="">{t("filial")}: {t("hammasi")}</option>
                {filiallar.map((x) => <option key={x.id} value={x.id}>{x.nomi}</option>)}
              </select>
              <select value={ustozF} onChange={(e) => setUstozF(e.target.value)} aria-label={t("oqituvchi")}>
                <option value="">{t("oqituvchi")}: {t("hammasi")}</option>
                {[...new Set(hammasi.map((g) => g.oqituvchi).filter(Boolean))].map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
              <select value={kursF} onChange={(e) => setKursF(e.target.value)} aria-label={t("kurs")}>
                <option value="">{t("kurs")}: {t("hammasi")}</option>
                {[...new Map(hammasi.filter((g) => g.daraja).map((g) => [g.daraja.id, g.daraja.nomi])).entries()].map(([id, nomi]) => (
                  <option key={id} value={id}>{nomi}</option>
                ))}
              </select>
            </div>
            <label>{t("guruh")}
              <select value={guruhId} onChange={(e) => setGuruhId(e.target.value)}>
                <option value="">{t("tanlang")}</option>
                {royxat.map((g) => (
                  <option key={g.id} value={g.id}>{g.nomi}{g.oqituvchi ? ` · ${g.oqituvchi}` : ""}</option>
                ))}
              </select>
            </label>
            <div className="ikki-ustun">
              <label>{t("holat")}
                <select value={holat} onChange={(e) => setHolat(e.target.value)}>
                  <option value="sinov">{t("holat_sinov")}</option>
                  <option value="faol">{t("holat_faol")}</option>
                </select>
              </label>
              <label>{t("qoshilgan_sana")}
                <input type="date" value={sanaQ} onChange={(e) => setSanaQ(e.target.value)} />
              </label>
            </div>
            {xato && <div className="xato">{xato}</div>}
            <div className="oyna-tugmalar">
              <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
              <button className="tugma" type="button" disabled={band || !guruhId} onClick={saqla}>{t("saqlash")}</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ── Lid kartasi ─────────────────────────────────────────────────────

function LidKartasi({ lidId, bolimlar, onYopish, onOzgardi, rejim = null }) {
  // Ustun guruhga bog'langan bo'lsa — "Guruhga qo'shish" o'sha guruhni taklif qiladi.
  const { t } = useI18n();
  const profil = useProfil();
  const ruxsat = useRuxsat();
  const { malumot: lid, yuklanmoqda, yangila } = useSorov(`/api/crm/lidlar/${lidId}/`);
  // `rejim` — kartochka menyusidan kelganda ("eslatma" / "tahrir").
  const [tab, setTab] = useState(rejim === "eslatma" ? "eslatmalar" : "malumot");
  const [tahrir, setTahrir] = useState(rejim === "tahrir");
  const [guruhga, setGuruhga] = useState(false);
  const [band, setBand] = useState(false);
  const [xato, setXato] = useState("");
  // "arxiv" / "qora" — sabab oynasi (video-TZ 2026-09-25: avval bir
  // bosishda arxivga/qora ro'yxatga ketib qolardi, sababi yozilmasdi).
  const [sababOyna, setSababOyna] = useState(null);
  // Qora ro'yxat hamma filialga ko'rinadi (2026-09-23) — lekin boshqa
  // filial lidini faqat ko'rish mumkin, o'zgartirish o'sha filialda.
  const begona = Boolean(lid?.filial_id && Array.isArray(profil?.filiallar)
                         && !profil.filiallar.includes(lid.filial_id));

  async function ozgartir(body) {
    setBand(true);
    setXato("");
    try {
      await api(`/api/crm/lidlar/${lidId}/`, { method: "PATCH", body });
      yangila();
      onOzgardi();
      setTahrir(false);
    } catch (e) {
      setXato(e.message);
    } finally {
      setBand(false);
    }
  }

  async function ochir() {
    if (!window.confirm(t("lid_ochirish_tasdiq"))) return;
    setXato("");
    try {
      await api(`/api/crm/lidlar/${lidId}/`, { method: "DELETE" });
      onOzgardi();
      onYopish();
    } catch (e) {
      setXato(e.message);
    }
  }

  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna oyna-keng lid-karta">
        <div className="karta-sarlavha">
          <h2>{t("lid_malumotlari")}</h2>
          <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={onYopish}>✕</button>
        </div>
        {yuklanmoqda || !lid ? (
          <p className="kichik">{t("yuklanmoqda")}</p>
        ) : (
          <>
            <div className="lid-bosh">
              <span className="avatar-harf">{lid.ism.slice(0, 1).toUpperCase()}</span>
              <div>
                <b>{lid.ism}</b>
                <div className="kichik">{lid.holat_nomi}{lid.qora_royxat ? ` · ${t("qora_royxat")}` : ""}</div>
              </div>
              <div className="tezkor-amallar">
                <a className="tugma tugma-sokin kichik-tugma" href={`tel:${lid.telefon}`}>📞 {t("qongiroq")}</a>
                {/* Lidlarga qaytarilgan o'quvchida `talaba_id` bor — u ham
                    guruhga qayta qo'shiladi (yangi hisob ochilmaydi). */}
                {ruxsat("lidlar.guruhga") && lid.holat !== "qoshildi" && !begona && (
                  <button className="tugma kichik-tugma" type="button" onClick={() => setGuruhga(true)}>
                    👥 {t("guruhga_qoshish")}
                  </button>
                )}
                {ruxsat("lidlar.ochirish") && !begona && (
                  <button className="tugma tugma-sokin kichik-tugma rang-qarzdor" type="button" onClick={ochir}>
                    🗑 {t("ochirish")}
                  </button>
                )}
              </div>
            </div>

            <div className="tablar">
              {["malumot", "eslatmalar", "tarix"].map((x) => (
                <button key={x} type="button" className={tab === x ? "tab faol" : "tab"} onClick={() => setTab(x)}>
                  {t(`lid_tab_${x}`)}
                </button>
              ))}
            </div>

            {tab === "malumot" && (tahrir ? (
              <LidForma lid={lid} bolimlar={bolimlar} onSaqla={ozgartir} onBekor={() => setTahrir(false)}
                        band={band} xato={xato} />
            ) : (
              <>
                <div className="qator"><span className="kichik">{t("telefon")}</span><span>{lid.telefon}</span></div>
                {lid.qoshimcha_telefon && (
                  <div className="qator">
                    <span className="kichik">{t("qoshimcha_telefon")}</span>
                    <span>{lid.qoshimcha_telefon}{lid.qoshimcha_ism ? ` (${lid.qoshimcha_ism})` : ""}</span>
                  </div>
                )}
                <div className="qator">
                  <span className="kichik">{t("tugilgan_sana")}</span>
                  <span>{sana(lid.tugilgan_sana)}{lid.tugilgan_sana ? ` · ${yosh(lid.tugilgan_sana)} ${t("yosh")}` : ""}</span>
                </div>
                {lid.harorat && (
                  <div className="qator"><span className="kichik">{t("harorat")}</span><span>{t(`harorat_${lid.harorat}`)}</span></div>
                )}
                <div className="qator"><span className="kichik">{t("manba")}</span><span>{lid.manba || "—"}</span></div>
                <div className="qator"><span className="kichik">{t("kurs")}</span><span>{lid.kurs || "—"}</span></div>
                <div className="qator"><span className="kichik">{t("oqituvchi")}</span><span>{lid.oqituvchi || "—"}</span></div>
                <div className="qator">
                  <span className="kichik">{t("qulay_vaqt")}</span>
                  <span>{lid.qulay_vaqt || "—"}{lid.kunlar ? ` · ${t(`kunlar_${lid.kunlar}`)}` : ""}</span>
                </div>
                {lid.yigilayotgan_guruh && (
                  <div className="qator">
                    <span className="kichik">{t("yigilayotgan_guruh")}</span><span>👥 {lid.yigilayotgan_guruh}</span>
                  </div>
                )}
                <div className="qator"><span className="kichik">{t("izoh")}</span><span>{lid.izoh || "—"}</span></div>
                <div className="qator"><span className="kichik">{t("kim_qoshdi")}</span><span>{lid.kim_qoshdi || "—"} · {vaqt(lid.vaqt)}</span></div>
                {lid.arxiv && lid.arxiv_sabab && (
                  <div className="qator">
                    <span className="kichik">{t("arxiv_sababi")}</span>
                    <span className="rang-qarzdor">{t(`lid_arxiv_${lid.arxiv_sabab}`)}{lid.arxiv_izoh ? ` — ${lid.arxiv_izoh}` : ""}</span>
                  </div>
                )}
                {lid.qora_royxat && lid.qora_royxat_izoh && (
                  <div className="qator">
                    <span className="kichik">{t("qora_royxat_sababi")}</span>
                    <span className="rang-qarzdor">{lid.qora_royxat_izoh}</span>
                  </div>
                )}
                {lid.takrorlar?.length > 0 && (
                  <p className="ogohlantirish">⚠ {t("takror_raqam")}: {lid.takrorlar.map((x) => x.ism).join(", ")}</p>
                )}
                {xato && <div className="xato">{xato}</div>}
                {begona && <p className="kichik">{t("begona_filial_lidi")}</p>}
                {!begona && <div className="oyna-tugmalar">
                  {ruxsat("lidlar.arxiv") && (
                    <button className="tugma tugma-sokin" type="button" disabled={band}
                            onClick={() => (lid.arxiv ? ozgartir({ arxiv: false }) : setSababOyna("arxiv"))}>
                      {lid.arxiv ? t("arxivdan_chiqarish") : t("arxivlash")}
                    </button>
                  )}
                  {ruxsat("lidlar.qora_royxat") && (
                    <button className="tugma tugma-sokin" type="button" disabled={band}
                            onClick={() => (lid.qora_royxat
                              ? window.confirm(t("qora_royxatdan_chiqarish_tasdiq")) && ozgartir({ qora_royxat: false })
                              : setSababOyna("qora"))}>
                      {lid.qora_royxat ? t("qora_royxatdan_chiqarish") : t("qora_royxatga")}
                    </button>
                  )}
                  {ruxsat("lidlar.tahrirlash") && (
                    <button className="tugma" type="button" onClick={() => setTahrir(true)}>✎ {t("tahrirlash")}</button>
                  )}
                </div>}
              </>
            ))}

            {tab === "eslatmalar" && <Eslatmalar lidId={lid.id} profilId={profil?.id} eslatishVaqti />}

            {tab === "tarix" && (
              <ul className="eslatma-royxat">
                {lid.tarix.map((x, i) => (
                  <li key={i}>
                    <div className="eslatma-matn">{x.matn}</div>
                    <div className="eslatma-past kichik">{x.kim || "—"} · {vaqt(x.vaqt)}</div>
                  </li>
                ))}
                {lid.tarix.length === 0 && <li className="kichik">{t("yozuv_yoq")}</li>}
              </ul>
            )}
          </>
        )}
      </div>
      {sababOyna === "arxiv" && lid && (
        <SababOynasi
          sarlavha={`${t("arxivlash")} — ${lid.ism}`}
          sabablar={ARXIV_SABABLARI.map((k) => [k, t(`lid_arxiv_${k}`)])}
          izohMajburiy={(sabab) => sabab === "boshqa"}
          onYopish={() => setSababOyna(null)}
          onTasdiq={async ({ sabab, izoh }) => {
            await api(`/api/crm/lidlar/${lidId}/`, {
              method: "PATCH", body: { arxiv: true, arxiv_sabab: sabab, arxiv_izoh: izoh },
            });
            yangila();
            onOzgardi();
          }}
        />
      )}
      {sababOyna === "qora" && lid && (
        <SababOynasi
          sarlavha={`${t("qora_royxatga")} — ${lid.ism}`}
          izoh={t("qora_royxat_ogohlantirish")}
          xavfli
          onYopish={() => setSababOyna(null)}
          onTasdiq={async ({ izoh }) => {
            await api(`/api/crm/lidlar/${lidId}/`, {
              method: "PATCH", body: { qora_royxat: true, qora_royxat_izoh: izoh },
            });
            yangila();
            onOzgardi();
          }}
        />
      )}
      {guruhga && lid && (
        <GuruhgaQoshishOynasi lidIdlar={[lid.id]} standartGuruh={bolimlar.find((b) => b.id === lid.bolim_id)?.guruh_id || ""}
                              onYopish={() => { setGuruhga(false); onYopish(); }}
                              onSaqlandi={onOzgardi} />
      )}
    </div>
  );
}

// ── Kanban ustuni ───────────────────────────────────────────────────

function Ustun({ bolim, lidlar, tanlangan, setTanlangan, onOch, onTashla, onYangi, onNom, onOchir, onMenyu, ruxsat }) {
  // Umumiy (filialsiz) ustunni filial xodimi o'zgartirmaydi (backend ham).
  const cheklangan = useCheklangan();
  const { t } = useI18n();
  const [ustida, setUstida] = useState(false);
  return (
    <div
      className={`kanban-ustun${ustida ? " ustida" : ""}`}
      onDragOver={(e) => { e.preventDefault(); setUstida(true); }}
      onDragLeave={() => setUstida(false)}
      onDrop={(e) => {
        e.preventDefault();
        setUstida(false);
        const id = Number(e.dataTransfer.getData("text/lid"));
        if (id) onTashla(id, bolim?.id ?? null);
      }}
    >
      <div className="kanban-sarlavha">
        <b>{bolim ? bolim.nomi : t("yangi_lidlar")}</b>
        <span className="belgi">{lidlar.length}</span>
        {bolim && ruxsat("lidlar.bolim") && !(cheklangan && !bolim.filial_id) && (
          <span className="kanban-amallar">
            <button className="havola" type="button" title={t("tahrirlash")} onClick={() => onNom(bolim)}>✎</button>
            <button className="havola rang-qarzdor" type="button" title={t("ochirish")} onClick={() => onOchir(bolim)}>🗑</button>
          </span>
        )}
      </div>
      <div className="kanban-kartalar">
        {lidlar.map((l) => (
          <div
            key={l.id}
            className="lid-kartochka"
            // Ustunga sudrash — bu lidni tahrirlash (backend ham tekshiradi).
            draggable={ruxsat("lidlar.tahrirlash")}
            onDragStart={(e) => e.dataTransfer.setData("text/lid", String(l.id))}
            // Oxirgi eslatma — SoffCRM'dagi sichqoncha ustidagi izoh.
            title={l.oxirgi_eslatma ? `${l.oxirgi_eslatma.matn}` : l.izoh || ""}
          >
            <div className="lid-kartochka-bosh">
              <input
                type="checkbox"
                checked={tanlangan.has(l.id)}
                onChange={(e) => {
                  const yangi = new Set(tanlangan);
                  if (e.target.checked) yangi.add(l.id); else yangi.delete(l.id);
                  setTanlangan(yangi);
                }}
                aria-label={l.ism}
              />
              <button className="havola" type="button" onClick={() => onOch(l.id)}>{l.ism}</button>
              <button className="havola lid-menyu-tugma" type="button" aria-label={t("harakatlar")}
                      onClick={(e) => onMenyu(l, e.currentTarget.getBoundingClientRect())}>⋯</button>
            </div>
            <div className="kichik">{l.telefon}</div>
            <div className="lid-kartochka-past">
              <span className="kichik">📅 {sana(l.vaqt)}</span>
              {l.manba && <span className="belgi">{l.manba}</span>}
              <span className={`holat holat-${l.holat === "yoqotilgan" ? "qarzdor" : l.holat === "sinov" ? "qisman" : "kutilayotgan"}`}>
                {t(`lid_${l.holat}`)}
              </span>
            </div>
            {l.oxirgi_eslatma && (
              <div className="lid-eslatma kichik">💬 {l.oxirgi_eslatma.matn}</div>
            )}
            {l.yigilayotgan_guruh && <div className="kichik">👥 {l.yigilayotgan_guruh}</div>}
          </div>
        ))}
        {lidlar.length === 0 && <p className="kichik bosh">{t("bosh_kanban")}</p>}
      </div>
      {ruxsat("lidlar.qoshish") && (
        <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={() => onYangi(bolim?.id ?? null)}>
          + {t("yangi_lid_qoshish")}
        </button>
      )}
    </div>
  );
}

// ── Lidni ko'chirish: boshqa filial / boshqa bo'lim / yig'ilayotgan guruh ─

function LidKochirishOynasi({ malumot, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const { filiallar } = useFilial();
  const { lid, turi } = malumot;
  const doskalar = useSorov(turi === "bolim" ? "/api/crm/lid-doskalar/" : null);
  const ustunlar = useSorov(turi === "bolim" ? "/api/crm/lid-bolimlar/" : null);
  const guruhlar = useSorov(turi === "yigilayotgan" ? "/api/crm/guruhlar/" : null);
  const bugun = new Date().toISOString().slice(0, 10);
  const [qiymat, setQiymat] = useState(
    turi === "filial" ? (lid.filial_id ?? "") : turi === "bolim" ? (lid.bolim_id ?? "") : (lid.yigilayotgan_guruh_id ?? "")
  );
  const [xato, setXato] = useState("");
  const maydon = { filial: "filial_id", bolim: "bolim_id", yigilayotgan: "yigilayotgan_guruh_id" }[turi];
  const doskaNomi = (id) => (doskalar.malumot?.doskalar || []).find((d) => d.id === id)?.nomi || t("umumiy_doska");
  // Yig'ilayotgan guruh — hali boshlanmagan guruhlar tepada.
  const guruhRoyxati = [...(guruhlar.malumot || [])].sort(
    (a, b) => Number((b.boshlanish_sana || "") > bugun) - Number((a.boshlanish_sana || "") > bugun)
  );

  async function saqla() {
    setXato("");
    try {
      await api(`/api/crm/lidlar/${lid.id}/`, { method: "PATCH", body: { [maydon]: qiymat || null } });
      onSaqlandi();
      onYopish();
    } catch (e) {
      setXato(e.message);
    }
  }

  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna">
        <h2>{t({ filial: "boshqa_filialga", bolim: "boshqa_bolimga", yigilayotgan: "yigilayotgan_guruhga" }[turi])}</h2>
        <p className="kichik">{lid.ism}</p>
        <select value={qiymat} onChange={(e) => setQiymat(e.target.value)} aria-label={t("tanlang")}>
          <option value="">—</option>
          {turi === "filial" && filiallar.map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
          {turi === "bolim" && (ustunlar.malumot || []).map((u) => (
            <option key={u.id} value={u.id}>{doskaNomi(u.doska_id)} → {u.nomi}</option>
          ))}
          {turi === "yigilayotgan" && guruhRoyxati.map((g) => (
            <option key={g.id} value={g.id}>
              {g.nomi}{g.boshlanish_sana && g.boshlanish_sana > bugun ? ` (${t("boshlanadi")} ${sana(g.boshlanish_sana)})` : ""}
            </option>
          ))}
        </select>
        {turi === "yigilayotgan" && <p className="kichik">{t("yigilayotgan_izoh")}</p>}
        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
          <button className="tugma" type="button" onClick={saqla}>{t("saqlash")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Ustun qo'shish (SoffCRM "Yangi bo'lim qo'shish" — nomi guruhlardan) ─

function UstunOynasi({ guruhlar, onYopish, onSaqla }) {
  const { t } = useI18n();
  const [nomi, setNomi] = useState("");
  const [guruhId, setGuruhId] = useState("");
  const [xato, setXato] = useState("");
  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna">
        <h2>{t("qoshimcha_ustun")}</h2>
        <label>{t("bolim_nomi")}
          <input list="ustun-nomlari" value={nomi} autoFocus onChange={(e) => {
            setNomi(e.target.value);
            const g = guruhlar.find((x) => x.nomi === e.target.value);
            if (g) setGuruhId(String(g.id));
          }} />
          <datalist id="ustun-nomlari">{guruhlar.map((g) => <option key={g.id} value={g.nomi} />)}</datalist>
        </label>
        <label>{t("guruhga_boglash")} ({t("ixtiyoriy")})
          <select value={guruhId} onChange={(e) => setGuruhId(e.target.value)}>
            <option value="">—</option>
            {guruhlar.map((g) => <option key={g.id} value={g.id}>{g.nomi}</option>)}
          </select>
        </label>
        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
          <button className="tugma" type="button" disabled={!nomi.trim()} onClick={async () => {
            try {
              await onSaqla(nomi.trim(), guruhId);
            } catch (e) {
              setXato(e.message);
            }
          }}>{t("saqlash")}</button>
        </div>
      </div>
    </div>
  );
}

// ── Sahifa ──────────────────────────────────────────────────────────

export default function Lidlar() {
  const { t } = useI18n();
  const ruxsat = useRuxsat();
  const { tanlangan: filial } = useFilial();
  const [qidiruv, setQidiruv] = useState("");
  const [manba, setManba] = useState("");
  const [rejim, setRejim] = useState(""); // "" | arxiv | qora_royxat
  const [yangi, setYangi] = useState(undefined); // undefined = yopiq, null/raqam = bo'lim
  const [ochiq, setOchiq] = useState(null);
  const [ochiqRejim, setOchiqRejim] = useState(null);
  // Kartochka "⋯" menyusi (video 17:24) va ko'chirish oynasi.
  const [menyu, setMenyu] = useState(null);
  const [kochirish, setKochirish] = useState(null);
  const [tanlanganLar, setTanlanganLar] = useState(new Set());
  const [guruhga, setGuruhga] = useState(false);
  // Doska (SoffCRM "Bo'lim": LEADS, LEADS uzb...). "0" — Umumiy (doskasiz
  // ustunlar va ustunsiz lidlar). Arxiv/qora ro'yxat rejimida doska
  // filtrlanmaydi — ular hamma doskalardan yig'iladi.
  const [doska, setDoska] = useState("0");
  const doskalar = useSorov("/api/crm/lid-doskalar/");
  const [ustunOyna, setUstunOyna] = useState(false);
  const guruhRoyxati = useSorov(ustunOyna ? "/api/crm/guruhlar/" : null);

  const bolimlar = useSorov("/api/crm/lid-bolimlar/" + sorovSatri({ filial, doska }));
  const filtrSatri = sorovSatri({
    filial, q: qidiruv, manba, arxiv: rejim === "arxiv" ? 1 : "", qora_royxat: rejim === "qora_royxat" ? 1 : "",
    doska: rejim ? "" : doska,
  });
  const lidlar = useSorov("/api/crm/lidlar/" + filtrSatri);
  const [eksportXato, setEksportXato] = useState("");

  // Excel — ekrandagi filtrlar bilan AYNAN shu ro'yxat.
  async function eksport() {
    setEksportXato("");
    try {
      await apiFayluniYuklab("/api/crm/lidlar/eksport/" + filtrSatri);
    } catch (e) {
      setEksportXato(e.message);
    }
  }
  const bolimRoyxati = bolimlar.malumot || [];
  const lidRoyxati = lidlar.malumot || [];

  function yangilaHammasi() {
    lidlar.yangila();
    bolimlar.yangila();
    doskalar.yangila();
  }

  async function tashla(lidId, bolimId) {
    const lid = lidRoyxati.find((x) => x.id === lidId);
    if (!lid || lid.bolim_id === bolimId) return;
    setEksportXato("");
    try {
      await api(`/api/crm/lidlar/${lidId}/`, { method: "PATCH", body: { bolim_id: bolimId } });
      yangilaHammasi();
    } catch (e) {
      setEksportXato(e.message);
    }
  }

  // "Bo'lim yaratish" — yangi DOSKA ("NEW LEADS" ustuni bilan ochiladi).
  // Doska tepada tanlangan filialniki bo'ladi (2026-09-23); "hammasi"da —
  // umumiy (filial xodimida bitta filiali bo'lsa, backend o'zi qo'yadi).
  async function doskaYarat() {
    const nomi = window.prompt(t("doska_nomi"));
    if (!nomi) return;
    setEksportXato("");
    try {
      const d = await api("/api/crm/lid-doskalar/", { method: "POST", body: { nomi, filial_id: filial || null } });
      doskalar.yangila();
      setDoska(String(d.id));
    } catch (e) {
      setEksportXato(e.message);
    }
  }

  async function doskaOchir() {
    if (doska === "0" || !window.confirm(t("doska_ochirish_tasdiq"))) return;
    setEksportXato("");
    try {
      await api(`/api/crm/lid-doskalar/${doska}/`, { method: "DELETE" });
      setDoska("0");
      yangilaHammasi();
    } catch (e) {
      setEksportXato(e.message);
    }
  }

  // "Qo'shimcha ustun qo'shish" — joriy doskada ustun; guruhga bog'lash ixtiyoriy.
  // Filial doskasida ustun doska filialini oladi (backend), umumiy doskada — tanlangan filialni.
  async function ustunYarat(nomi, guruhId) {
    await api("/api/crm/lid-bolimlar/", {
      method: "POST",
      body: {
        nomi, filial_id: doska === "0" ? filial || null : null,
        doska_id: doska === "0" ? null : doska, guruh_id: guruhId || null,
      },
    });
    setUstunOyna(false);
    bolimlar.yangila();
  }

  async function bolimNom(b) {
    const nomi = window.prompt(t("bolim_nomi"), b.nomi);
    if (!nomi || nomi === b.nomi) return;
    setEksportXato("");
    try {
      await api(`/api/crm/lid-bolimlar/${b.id}/`, { method: "PATCH", body: { nomi } });
      bolimlar.yangila();
    } catch (e) {
      setEksportXato(e.message);
    }
  }

  async function bolimOchir(b) {
    if (!window.confirm(t("bolim_ochirish_tasdiq"))) return;
    setEksportXato("");
    try {
      await api(`/api/crm/lid-bolimlar/${b.id}/`, { method: "DELETE" });
      yangilaHammasi();
    } catch (e) {
      setEksportXato(e.message);
    }
  }

  // Umumiy doskada ustunsiz lidlar uchun "Yangi lidlar" ustuni ham bor.
  const ustunlar = doska === "0" || rejim ? [null, ...bolimRoyxati] : bolimRoyxati;
  const doskaMalumot = doskalar.malumot;
  const tanlanganDoska = (doskaMalumot?.doskalar || []).find((d) => String(d.id) === doska);
  // Umumiy (filialsiz) doska/ustunni filial xodimi o'zgartirmaydi (backend ham).
  const cheklangan = useCheklangan();
  const umumiyTegilmaydi = (yozuv) => cheklangan && yozuv && !yozuv.filial_id;

  return (
    <section>
      <div className="karta-sarlavha">
        <h1>{t("lidlar")}</h1>
        <div className="tezkor-amallar">
          {tanlanganLar.size > 0 && ruxsat("lidlar.guruhga") && (
            <button className="tugma" type="button" onClick={() => setGuruhga(true)}>
              👥 {t("lidlarni_guruhga")} ({tanlanganLar.size})
            </button>
          )}
          {ruxsat("lidlar.excel") && (
            <button className="tugma tugma-sokin" type="button" onClick={eksport}>⬇ Excel</button>
          )}
          {ruxsat("lidlar.bolim") && (
            <>
              <button className="tugma tugma-sokin" type="button" onClick={doskaYarat}>+ {t("bolim_yaratish")}</button>
              <button className="tugma tugma-sokin" type="button" onClick={() => setUstunOyna(true)}>
                + {t("qoshimcha_ustun")}
              </button>
            </>
          )}
          {ruxsat("lidlar.qoshish") && (
            <button className="tugma" type="button" onClick={() => setYangi(null)}>+ {t("yangi_lid")}</button>
          )}
        </div>
      </div>

      <div className="filtrlar">
        <select value={doska} onChange={(e) => setDoska(e.target.value)} aria-label={t("doska")} disabled={Boolean(rejim)}>
          <option value="0">{t("umumiy_doska")} ({doskaMalumot?.umumiy ?? 0})</option>
          {(doskaMalumot?.doskalar || []).map((d) => (
            <option key={d.id} value={d.id}>{d.nomi} ({d.soni ?? 0})</option>
          ))}
        </select>
        {doska !== "0" && ruxsat("lidlar.bolim") && !rejim && !umumiyTegilmaydi(tanlanganDoska) && (
          <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={doskaOchir} title={t("ochirish")}>🗑</button>
        )}
        <input placeholder={t("qidiruv")} value={qidiruv} onChange={(e) => setQidiruv(e.target.value)} />
        <select value={manba} onChange={(e) => setManba(e.target.value)} aria-label={t("manba")}>
          <option value="">{t("manba")}: {t("hammasi")}</option>
          {MANBALAR.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <select value={rejim} onChange={(e) => setRejim(e.target.value)} aria-label={t("holat")}>
          <option value="">{t("faol_lidlar")}</option>
          <option value="arxiv">{t("arxiv")}</option>
          <option value="qora_royxat">{t("qora_royxat")} ({doskaMalumot?.qora_royxat ?? 0})</option>
        </select>
        <span className="kichik">{t("jami")}: {lidRoyxati.length}</span>
      </div>

      {(lidlar.xato || bolimlar.xato || eksportXato) && (
        <div className="xato">{lidlar.xato || bolimlar.xato || eksportXato}</div>
      )}

      <div className="kanban">
        {ustunlar.map((b) => (
          <Ustun
            key={b ? b.id : "yangi"}
            bolim={b}
            lidlar={lidRoyxati.filter((l) => (l.bolim_id ?? null) === (b ? b.id : null))}
            tanlangan={tanlanganLar}
            setTanlangan={setTanlanganLar}
            onOch={setOchiq}
            onTashla={tashla}
            onYangi={setYangi}
            onNom={bolimNom}
            onOchir={bolimOchir}
            onMenyu={(lid, joy) => setMenyu({ lid, joy })}
            ruxsat={ruxsat}
          />
        ))}
      </div>

      {ustunOyna && (
        <UstunOynasi guruhlar={guruhRoyxati.malumot || []} onYopish={() => setUstunOyna(false)} onSaqla={ustunYarat} />
      )}
      {yangi !== undefined && (
        <YangiLidOynasi bolimlar={bolimRoyxati} bolimId={yangi ?? bolimRoyxati[0]?.id ?? null} onYopish={() => setYangi(undefined)}
                        onSaqlandi={yangilaHammasi} />
      )}
      {ochiq && (
        <LidKartasi lidId={ochiq} bolimlar={bolimRoyxati} rejim={ochiqRejim}
                    onYopish={() => { setOchiq(null); setOchiqRejim(null); }} onOzgardi={yangilaHammasi} />
      )}
      {menyu && (
        <div className="harakat-menyu lid-menyu" style={{ top: menyu.joy.bottom + window.scrollY, left: menyu.joy.left + window.scrollX - 180 }}
             onMouseLeave={() => setMenyu(null)}>
          <button type="button" onClick={() => { setOchiqRejim("eslatma"); setOchiq(menyu.lid.id); setMenyu(null); }}>
            📝 {t("yangi_eslatma")}
          </button>
          <button type="button" disabled title={t("sms_ulanmagan")}>✉ {t("sms_yuborish")}</button>
          {ruxsat("lidlar.tahrirlash") && (
            <>
              <button type="button" onClick={() => { setKochirish({ lid: menyu.lid, turi: "filial" }); setMenyu(null); }}>
                🏢 {t("boshqa_filialga")}
              </button>
              <button type="button" onClick={() => { setKochirish({ lid: menyu.lid, turi: "bolim" }); setMenyu(null); }}>
                🗂 {t("boshqa_bolimga")}
              </button>
            </>
          )}
          {ruxsat("lidlar.guruhga") && (
            <>
              <button type="button" onClick={() => { setTanlanganLar(new Set([menyu.lid.id])); setGuruhga(true); setMenyu(null); }}>
                👥 {t("guruhga_qoshish")}
              </button>
              <button type="button" onClick={() => { setKochirish({ lid: menyu.lid, turi: "yigilayotgan" }); setMenyu(null); }}>
                ⏳ {t("yigilayotgan_guruhga")}
              </button>
            </>
          )}
          {ruxsat("lidlar.tahrirlash") && (
            <button type="button" onClick={() => { setOchiqRejim("tahrir"); setOchiq(menyu.lid.id); setMenyu(null); }}>
              ✎ {t("tahrirlash")}
            </button>
          )}
          {ruxsat("lidlar.ochirish") && (
            <button type="button" className="rang-qarzdor" onClick={async () => {
              const lid = menyu.lid;
              setMenyu(null);
              if (!window.confirm(t("lid_ochirish_tasdiq"))) return;
              setEksportXato("");
              try {
                await api(`/api/crm/lidlar/${lid.id}/`, { method: "DELETE" });
                yangilaHammasi();
              } catch (e) {
                setEksportXato(e.message);
              }
            }}>
              🗑 {t("ochirish")}
            </button>
          )}
        </div>
      )}
      {kochirish && (
        <LidKochirishOynasi malumot={kochirish} onYopish={() => setKochirish(null)} onSaqlandi={yangilaHammasi} />
      )}
      {guruhga && (
        <GuruhgaQoshishOynasi
          lidIdlar={[...tanlanganLar]}
          onYopish={() => { setGuruhga(false); setTanlanganLar(new Set()); }}
          onSaqlandi={yangilaHammasi}
        />
      )}
    </section>
  );
}
