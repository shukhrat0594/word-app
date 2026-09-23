// Lidlar (video-TZ, 2026-09-23) — SoffCRM "Lidlar" kanbani.
//
// Ustunlar — erkin bo'limlar ("New leads", "Beginner", "Rus tili"...).
// Bo'limsiz lidlar birinchi "Yangi lidlar" ustunida. Kartochkani
// sudrab boshqa ustunga tashlash mumkin. Lid guruhga qo'shilganda undan
// talaba yaratiladi va lid arxivga o'tadi (backend: `LidGuruhgaView`).

import { useState } from "react";

import { api } from "../api.js";
import Eslatmalar from "../Eslatmalar.jsx";
import { useFilial } from "../filialContext.jsx";
import { sana, vaqt } from "../format.js";
import { useI18n } from "../i18n.jsx";
import { useProfil, useRuxsat } from "../profilContext.jsx";
import { sorovSatri, useSorov } from "../soragich.js";

const MANBALAR = ["Instagram", "Telegram", "Tavsiya", "Oldin o'qigan", "Banner", "Flayer", "Google", "Boshqa"];
const HOLATLAR = ["yangi", "boglanildi", "sinov", "kelmadi", "oylayapti", "yoqotilgan"];
const KUNLAR = ["toq", "juft", "har_kuni", "boshqa"];

// ── Lid formasi (yaratish va tahrir) ────────────────────────────────

function LidForma({ lid, bolimlar, onSaqla, onBekor, band, xato }) {
  const { t } = useI18n();
  const { filiallar, tanlangan } = useFilial();
  const oqituvchilar = useSorov("/api/crm/xodimlar/?lavozim=oqituvchi");
  const kurslar = useSorov("/api/crm/kurs-narxlari/");
  const [f, setF] = useState(() => ({
    ism: lid?.ism || "",
    telefon: lid?.telefon || "+998",
    qoshimcha_telefon: lid?.qoshimcha_telefon || "",
    qoshimcha_ism: lid?.qoshimcha_ism || "",
    tugilgan_sana: lid?.tugilgan_sana || "",
    manba: lid?.manba || "",
    bolim_id: lid?.bolim_id ?? "",
    holat: lid?.holat || "yangi",
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
        <label>{t("tugilgan_sana")}<input type="date" {...qiymat("tugilgan_sana")} /></label>
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
        <label>{t("qulay_vaqt")}<input type="time" {...qiymat("qulay_vaqt")} /></label>
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

export function GuruhgaQoshishOynasi({ lidIdlar, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const { tanlangan } = useFilial();
  const guruhlar = useSorov("/api/crm/guruhlar/" + sorovSatri({ filial: tanlangan }));
  const [guruhId, setGuruhId] = useState("");
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
            <label>{t("guruh")}
              <select value={guruhId} onChange={(e) => setGuruhId(e.target.value)}>
                <option value="">{t("tanlang")}</option>
                {(guruhlar.malumot || []).map((g) => (
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

function LidKartasi({ lidId, bolimlar, onYopish, onOzgardi }) {
  const { t } = useI18n();
  const profil = useProfil();
  const ruxsat = useRuxsat();
  const { malumot: lid, yuklanmoqda, yangila } = useSorov(`/api/crm/lidlar/${lidId}/`);
  const [tab, setTab] = useState("malumot");
  const [tahrir, setTahrir] = useState(false);
  const [guruhga, setGuruhga] = useState(false);
  const [band, setBand] = useState(false);
  const [xato, setXato] = useState("");

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
    await api(`/api/crm/lidlar/${lidId}/`, { method: "DELETE" });
    onOzgardi();
    onYopish();
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
                {ruxsat("lidlar.guruhga") && !lid.talaba_id && (
                  <button className="tugma kichik-tugma" type="button" onClick={() => setGuruhga(true)}>
                    👥 {t("guruhga_qoshish")}
                  </button>
                )}
                {ruxsat("lidlar.ochirish") && (
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
                <div className="qator"><span className="kichik">{t("tugilgan_sana")}</span><span>{sana(lid.tugilgan_sana)}</span></div>
                <div className="qator"><span className="kichik">{t("manba")}</span><span>{lid.manba || "—"}</span></div>
                <div className="qator"><span className="kichik">{t("kurs")}</span><span>{lid.kurs || "—"}</span></div>
                <div className="qator"><span className="kichik">{t("oqituvchi")}</span><span>{lid.oqituvchi || "—"}</span></div>
                <div className="qator">
                  <span className="kichik">{t("qulay_vaqt")}</span>
                  <span>{lid.qulay_vaqt || "—"}{lid.kunlar ? ` · ${t(`kunlar_${lid.kunlar}`)}` : ""}</span>
                </div>
                <div className="qator"><span className="kichik">{t("izoh")}</span><span>{lid.izoh || "—"}</span></div>
                <div className="qator"><span className="kichik">{t("kim_qoshdi")}</span><span>{lid.kim_qoshdi || "—"} · {vaqt(lid.vaqt)}</span></div>
                {lid.takrorlar?.length > 0 && (
                  <p className="ogohlantirish">⚠ {t("takror_raqam")}: {lid.takrorlar.map((x) => x.ism).join(", ")}</p>
                )}
                {xato && <div className="xato">{xato}</div>}
                <div className="oyna-tugmalar">
                  {ruxsat("lidlar.arxiv") && (
                    <button className="tugma tugma-sokin" type="button" disabled={band}
                            onClick={() => ozgartir({ arxiv: !lid.arxiv })}>
                      {lid.arxiv ? t("arxivdan_chiqarish") : t("arxivlash")}
                    </button>
                  )}
                  {ruxsat("lidlar.qora_royxat") && (
                    <button className="tugma tugma-sokin" type="button" disabled={band}
                            onClick={() => ozgartir({ qora_royxat: !lid.qora_royxat })}>
                      {lid.qora_royxat ? t("qora_royxatdan_chiqarish") : t("qora_royxatga")}
                    </button>
                  )}
                  {ruxsat("lidlar.tahrirlash") && (
                    <button className="tugma" type="button" onClick={() => setTahrir(true)}>✎ {t("tahrirlash")}</button>
                  )}
                </div>
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
      {guruhga && lid && (
        <GuruhgaQoshishOynasi lidIdlar={[lid.id]} onYopish={() => { setGuruhga(false); onYopish(); }}
                              onSaqlandi={onOzgardi} />
      )}
    </div>
  );
}

// ── Kanban ustuni ───────────────────────────────────────────────────

function Ustun({ bolim, lidlar, tanlangan, setTanlangan, onOch, onTashla, onYangi, onNom, onOchir, ruxsat }) {
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
        {bolim && ruxsat("lidlar.bolim") && (
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
            draggable
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
  const [tanlanganLar, setTanlanganLar] = useState(new Set());
  const [guruhga, setGuruhga] = useState(false);

  const bolimlar = useSorov("/api/crm/lid-bolimlar/" + sorovSatri({ filial }));
  const lidlar = useSorov(
    "/api/crm/lidlar/" +
      sorovSatri({ filial, q: qidiruv, manba, arxiv: rejim === "arxiv" ? 1 : "", qora_royxat: rejim === "qora_royxat" ? 1 : "" })
  );
  const bolimRoyxati = bolimlar.malumot || [];
  const lidRoyxati = lidlar.malumot || [];

  function yangilaHammasi() {
    lidlar.yangila();
    bolimlar.yangila();
  }

  async function tashla(lidId, bolimId) {
    const lid = lidRoyxati.find((x) => x.id === lidId);
    if (!lid || lid.bolim_id === bolimId) return;
    await api(`/api/crm/lidlar/${lidId}/`, { method: "PATCH", body: { bolim_id: bolimId } });
    yangilaHammasi();
  }

  async function bolimYarat() {
    const nomi = window.prompt(t("bolim_nomi"));
    if (!nomi) return;
    await api("/api/crm/lid-bolimlar/", { method: "POST", body: { nomi, filial_id: null } });
    bolimlar.yangila();
  }

  async function bolimNom(b) {
    const nomi = window.prompt(t("bolim_nomi"), b.nomi);
    if (!nomi || nomi === b.nomi) return;
    await api(`/api/crm/lid-bolimlar/${b.id}/`, { method: "PATCH", body: { nomi } });
    bolimlar.yangila();
  }

  async function bolimOchir(b) {
    if (!window.confirm(t("bolim_ochirish_tasdiq"))) return;
    await api(`/api/crm/lid-bolimlar/${b.id}/`, { method: "DELETE" });
    yangilaHammasi();
  }

  const ustunlar = [null, ...bolimRoyxati];

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
          {ruxsat("lidlar.bolim") && (
            <button className="tugma tugma-sokin" type="button" onClick={bolimYarat}>+ {t("bolim_yaratish")}</button>
          )}
          {ruxsat("lidlar.qoshish") && (
            <button className="tugma" type="button" onClick={() => setYangi(null)}>+ {t("yangi_lid")}</button>
          )}
        </div>
      </div>

      <div className="filtrlar">
        <input placeholder={t("qidiruv")} value={qidiruv} onChange={(e) => setQidiruv(e.target.value)} />
        <select value={manba} onChange={(e) => setManba(e.target.value)} aria-label={t("manba")}>
          <option value="">{t("manba")}: {t("hammasi")}</option>
          {MANBALAR.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <select value={rejim} onChange={(e) => setRejim(e.target.value)} aria-label={t("holat")}>
          <option value="">{t("faol_lidlar")}</option>
          <option value="arxiv">{t("arxiv")}</option>
          <option value="qora_royxat">{t("qora_royxat")}</option>
        </select>
        <span className="kichik">{t("jami")}: {lidRoyxati.length}</span>
      </div>

      {(lidlar.xato || bolimlar.xato) && <div className="xato">{lidlar.xato || bolimlar.xato}</div>}

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
            ruxsat={ruxsat}
          />
        ))}
      </div>

      {yangi !== undefined && (
        <YangiLidOynasi bolimlar={bolimRoyxati} bolimId={yangi} onYopish={() => setYangi(undefined)}
                        onSaqlandi={yangilaHammasi} />
      )}
      {ochiq && (
        <LidKartasi lidId={ochiq} bolimlar={bolimRoyxati} onYopish={() => setOchiq(null)} onOzgardi={yangilaHammasi} />
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
