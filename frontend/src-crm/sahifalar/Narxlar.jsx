// Narxlar — kurs (daraja) darajasidagi oylik narxlar.
//
// Narx ATAYLAB guruhda emas, KURSDA (darajada) turadi: IELTS 660 000
// bir marta kiritiladi va o'sha darajaning barcha guruhlari uni oladi.
// Guruhga yoki alohida talabaga boshqacha narx kerak bo'lsa — Guruhlar
// sahifasidan bekor qilinadi.

import { useState } from "react";

import { api } from "../api.js";
import { useI18n } from "../i18n.jsx";
import { useCheklangan, useRuxsat } from "../profilContext.jsx";
import { useSorov } from "../soragich.js";

// "Kurs qo'shish" (2026-09-26, Shuhrat): yangi kurs va narxi CRM'ning o'zidan.
// Kurs saytdagi Kurslar daraxtiga (Fan > Daraja) qo'shiladi va saytda
// "tez kunda" bo'lib turadi — darslari u yerda qo'shiladi.
function KursQoshishOynasi({ onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const fanlar = useSorov("/api/crm/kurs-fanlari/");
  const [fanId, setFanId] = useState("");
  const [yangiFan, setYangiFan] = useState("");
  const [nomi, setNomi] = useState("");
  const [narx, setNarx] = useState("");
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);
  const YANGI = "yangi";

  async function saqla() {
    setXato("");
    if (!fanId || (fanId === YANGI && !yangiFan.trim())) return setXato(t("fanni_tanlang"));
    if (!nomi.trim()) return setXato(t("kurs_nomini_yozing"));
    if (!(Number(narx) > 0)) return setXato(t("narx_kiriting"));
    setBand(true);
    try {
      await api("/api/crm/kurs-narxlari/", {
        method: "POST",
        body: {
          nomi: nomi.trim(), narx: String(narx),
          ...(fanId === YANGI ? { fan_nomi: yangiFan.trim() } : { fan_id: Number(fanId) }),
        },
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
        <h2>{t("kurs_qoshish")}</h2>
        <p className="kichik">{t("kurs_qoshish_izoh")}</p>
        <label>{t("fan")} *
          <select value={fanId} onChange={(e) => setFanId(e.target.value)} autoFocus>
            <option value="">{t("tanlang")}</option>
            {(fanlar.malumot || []).map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
            <option value={YANGI}>➕ {t("yangi_fan")}</option>
          </select>
        </label>
        {fanId === YANGI && (
          <label>{t("yangi_fan_nomi")} *
            <input value={yangiFan} onChange={(e) => setYangiFan(e.target.value)} maxLength={200} />
          </label>
        )}
        <label>{t("kurs_nomi")} *
          <input value={nomi} onChange={(e) => setNomi(e.target.value)} maxLength={200}
                 placeholder={t("kurs_nomi_namuna")} />
        </label>
        <label>{t("oylik_narx")} *
          <input type="number" min="0" step="1000" value={narx} onChange={(e) => setNarx(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && saqla()} />
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

/** O'chirishni tasdiqlash (2026-09-26, Shuhrat: "o'chirishni bosganda
 *  avval tasdiqlash kerak"). */
function OchirishTasdigi({ qator, onYopish, onTasdiq }) {
  const { t } = useI18n();
  const [band, setBand] = useState(false);
  const [xato, setXato] = useState("");

  async function tasdiqla() {
    setBand(true);
    setXato("");
    try {
      await onTasdiq();
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
        <h2>🗑 {t("kursni_ochirish")}</h2>
        <p><b>{qator.fan} — {qator.daraja}</b></p>
        <p className="kichik">{t("kursni_ochirish_izoh")}</p>
        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish} disabled={band}>{t("bekor")}</button>
          <button className="tugma tugma-xavfli" type="button" onClick={tasdiqla} disabled={band}>{t("ha_ochirish")}</button>
        </div>
      </div>
    </div>
  );
}

function NarxQatori({ qator, onSaqlandi }) {
  const { t } = useI18n();
  const [narx, setNarx] = useState(qator.narx ?? "");
  const [holat, setHolat] = useState("");
  // Kurs narxi butun markazga ta'sir qiladi — filialga bog'langan xodim faqat ko'radi.
  const cheklangan = useCheklangan();
  const ruxsat = useRuxsat();
  const boshqaradi = !cheklangan && ruxsat("sozlamalar.narxlar");
  // ✎ — kurs NOMINI tahrirlash (narx esa shu qatorda turibdi).
  const [nomi, setNomi] = useState(null);
  const [ochirish, setOchirish] = useState(false);

  async function saqla() {
    setHolat("");
    try {
      await api("/api/crm/kurs-narxlari/", {
        method: "PUT",
        body: { daraja_id: qator.daraja_id, narx: narx === "" ? null : String(narx) },
      });
      setHolat(t("saqlandi"));
      onSaqlandi();
    } catch (e) {
      setHolat(e.message || "Xato");
    }
  }

  async function nomniSaqla() {
    setHolat("");
    try {
      await api(`/api/crm/kurslar/${qator.daraja_id}/`, { method: "PATCH", body: { nomi } });
      setNomi(null);
      setHolat(t("saqlandi"));
      onSaqlandi();
    } catch (e) {
      setHolat(e.message || "Xato");
    }
  }

  return (
    <tr>
      <td>{qator.fan || "—"}</td>
      <td>
        {nomi === null ? (
          <b>{qator.daraja}</b>
        ) : (
          <span className="yonma">
            <input value={nomi} maxLength={200} autoFocus onChange={(e) => setNomi(e.target.value)}
                   onKeyDown={(e) => (e.key === "Enter" ? nomniSaqla() : e.key === "Escape" && setNomi(null))} />
            <button className="tugma kichik-tugma" type="button" onClick={nomniSaqla} disabled={!nomi.trim()}>
              {t("saqlash")}
            </button>
            <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={() => setNomi(null)}>✕</button>
          </span>
        )}
      </td>
      <td className="ongga">{qator.guruh_soni}</td>
      <td className="ongga">
        <input
          className="narx-maydon"
          type="number"
          min="0"
          step="1000"
          value={narx}
          disabled={cheklangan}
          onChange={(e) => setNarx(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && saqla()}
        />
      </td>
      <td className="nowrap">
        {!cheklangan && (
          <button className="tugma kichik-tugma" type="button" onClick={saqla}>
            {t("saqlash")}
          </button>
        )}{" "}
        {boshqaradi && nomi === null && (
          <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={() => setNomi(qator.daraja)}>
            ✎ {t("tahrirlash")}
          </button>
        )}{" "}
        {/* Darsi bor yoki guruhda ishlatilgan kurs o'chirilmaydi — sababi tugma ustida. */}
        {boshqaradi && (
          <button className="tugma tugma-sokin kichik-tugma rang-qarzdor" type="button"
                  disabled={!qator.ochirsa_boladi}
                  title={qator.ochirsa_boladi ? t("ochirish") : t("kurs_ochirilmaydi")}
                  onClick={() => setOchirish(true)}>
            🗑 {t("ochirish")}
          </button>
        )}{" "}
        <span className="kichik">{holat}</span>
        {ochirish && (
          <OchirishTasdigi
            qator={qator}
            onYopish={() => setOchirish(false)}
            onTasdiq={async () => {
              await api(`/api/crm/kurslar/${qator.daraja_id}/`, { method: "DELETE" });
              onSaqlandi();
            }}
          />
        )}
      </td>
    </tr>
  );
}

export default function Narxlar() {
  const { t } = useI18n();
  const ruxsat = useRuxsat();
  const cheklangan = useCheklangan();
  const { malumot, yuklanmoqda, xato, yangila } = useSorov("/api/crm/kurs-narxlari/");
  const qatorlar = malumot || [];
  const belgilangan = qatorlar.filter((q) => q.narx != null).length;
  const [qoshish, setQoshish] = useState(false);

  return (
    <section>
      <div className="karta-sarlavha">
        <h1>{t("kurs_narxlari")}</h1>
        {/* Kurs butun markazga tegishli — filialga bog'langan xodim qo'sha olmaydi (backend ham). */}
        {ruxsat("sozlamalar.narxlar") && !cheklangan && (
          <button className="tugma" type="button" onClick={() => setQoshish(true)}>+ {t("kurs_qoshish")}</button>
        )}
      </div>
      <p className="kichik">
        {belgilangan} / {qatorlar.length} {t("daraja").toLowerCase()}
      </p>

      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      <div className="karta jadval-oram">
        <table>
          <thead>
            <tr>
              <th>{t("fan")}</th>
              <th>{t("daraja")}</th>
              <th className="ongga">{t("guruh_soni")}</th>
              <th className="ongga">{t("narx")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {qatorlar.map((q) => (
              <NarxQatori key={q.daraja_id} qator={q} onSaqlandi={yangila} />
            ))}
            {!yuklanmoqda && qatorlar.length === 0 && (
              <tr><td colSpan={5} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {qoshish && <KursQoshishOynasi onYopish={() => setQoshish(false)} onSaqlandi={yangila} />}
    </section>
  );
}
