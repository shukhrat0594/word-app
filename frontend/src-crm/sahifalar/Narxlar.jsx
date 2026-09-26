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

function NarxQatori({ qator, onSaqlandi }) {
  const { t } = useI18n();
  const [narx, setNarx] = useState(qator.narx ?? "");
  const [holat, setHolat] = useState("");
  // Kurs narxi butun markazga ta'sir qiladi — filialga bog'langan xodim faqat ko'radi.
  const cheklangan = useCheklangan();

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

  return (
    <tr>
      <td>{qator.fan || "—"}</td>
      <td><b>{qator.daraja}</b></td>
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
      <td>
        {!cheklangan && (
          <button className="tugma kichik-tugma" type="button" onClick={saqla}>
            {t("saqlash")}
          </button>
        )}{" "}
        <span className="kichik">{holat}</span>
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
