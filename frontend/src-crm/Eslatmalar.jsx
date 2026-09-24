// Eslatmalar — guruh, talaba yoki lid haqidagi erkin izohlar.
//
// SoffCRM'dagi "ESLATMALAR" tabi. Bu — LMS'da ham, CRM'da ham bo'lmagan
// yagona narsa edi: adminning kundalik ishida kerak ("onasi 15-sentabrda
// to'layman dedi").

import { useState } from "react";

import { api } from "./api.js";
import { useI18n } from "./i18n.jsx";
import { sorovSatri, useSorov } from "./soragich.js";

function vaqtMatni(qiymat) {
  if (!qiymat) return "";
  const d = new Date(qiymat);
  const ikki = (n) => String(n).padStart(2, "0");
  return `${ikki(d.getDate())}.${ikki(d.getMonth() + 1)}.${d.getFullYear()} ${ikki(d.getHours())}:${ikki(d.getMinutes())}`;
}

function mahalliyVaqt(qiymat) {
  const d = new Date(qiymat);
  const ikki = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${ikki(d.getMonth() + 1)}-${ikki(d.getDate())}T${ikki(d.getHours())}:${ikki(d.getMinutes())}`;
}

export default function Eslatmalar({ guruhId, talabaId, lidId, profilId, eslatishVaqti = false }) {
  const { t } = useI18n();
  const [matn, setMatn] = useState("");
  // Eslatish vaqti (lidlar uchun, 2026-09-23): "23.09 kuni keladi".
  const [vaqtQ, setVaqtQ] = useState("");
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  const yol = "/api/crm/eslatmalar/" + sorovSatri({ guruh: guruhId, talaba: talabaId, lid: lidId });
  const { malumot, yuklanmoqda, yangila } = useSorov(yol);
  const eslatmalar = malumot || [];

  async function qosh() {
    if (!matn.trim()) return;
    setXato("");
    setBand(true);
    try {
      await api("/api/crm/eslatmalar/", {
        method: "POST",
        body: {
          guruh_id: guruhId ?? null, talaba_id: talabaId ?? null, lid_id: lidId ?? null, matn,
          eslatish_vaqti: vaqtQ || null,
        },
      });
      setMatn("");
      setVaqtQ("");
      yangila();
    } catch (e) {
      setXato(e.message || "Xato");
    } finally {
      setBand(false);
    }
  }

  // Tahrirlash (video 09:05, "Eslatmani tahrirlash") — faqat o'zinikini.
  const [tahrir, setTahrir] = useState(null); // {id, matn, vaqt}

  async function tahrirSaqla() {
    setXato("");
    try {
      await api(`/api/crm/eslatmalar/${tahrir.id}/`, {
        method: "PATCH",
        body: { matn: tahrir.matn, eslatish_vaqti: tahrir.vaqt || null },
      });
      setTahrir(null);
      yangila();
    } catch (e) {
      setXato(e.message || "Xato");
    }
  }

  async function ochir(id) {
    try {
      await api(`/api/crm/eslatmalar/${id}/`, { method: "DELETE" });
      yangila();
    } catch (e) {
      setXato(e.message || "Xato");
    }
  }

  return (
    <div className="eslatmalar">
      <div className="eslatma-yozish">
        <textarea
          rows={2}
          value={matn}
          onChange={(e) => setMatn(e.target.value)}
          placeholder={t("eslatma_placeholder")}
          maxLength={2000}
          // Ctrl+Enter — qo'l klaviaturadan uzilmasin.
          onKeyDown={(e) => (e.ctrlKey || e.metaKey) && e.key === "Enter" && qosh()}
        />
        {eslatishVaqti && (
          <input type="datetime-local" value={vaqtQ} onChange={(e) => setVaqtQ(e.target.value)}
                 aria-label={t("eslatish_vaqti")} title={t("eslatish_vaqti")} />
        )}
        <button className="tugma" type="button" onClick={qosh} disabled={band || !matn.trim()}>
          {t("qoshish")}
        </button>
      </div>

      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      {!yuklanmoqda && eslatmalar.length === 0 && (
        <p className="kichik">{t("eslatma_yoq")}</p>
      )}

      <ul className="eslatma-royxat">
        {eslatmalar.map((e) => (
          <li key={e.id}>
            {tahrir?.id === e.id ? (
              <div className="eslatma-yozish">
                <textarea rows={2} value={tahrir.matn} maxLength={2000}
                          onChange={(ev) => setTahrir((x) => ({ ...x, matn: ev.target.value }))} />
                <input type="datetime-local" value={tahrir.vaqt} aria-label={t("eslatish_vaqti")}
                       onChange={(ev) => setTahrir((x) => ({ ...x, vaqt: ev.target.value }))} />
                <button className="tugma" type="button" onClick={tahrirSaqla} disabled={!tahrir.matn.trim()}>
                  {t("saqlash")}
                </button>
                <button className="tugma tugma-sokin" type="button" onClick={() => setTahrir(null)}>✕</button>
              </div>
            ) : (
            <div className="eslatma-matn">{e.matn}</div>
            )}
            {e.eslatish_vaqti && <div className="kichik">⏰ {vaqtMatni(e.eslatish_vaqti)}</div>}
            <div className="eslatma-past">
              <span className="kichik">
                {e.kim || "—"} · {vaqtMatni(e.vaqt)}
              </span>
              {/* O'chirish tugmasi faqat O'Z eslatmasida ko'rinadi.
                  Owner boshqanikini ham o'chira oladi (backend shunga
                  ruxsat beradi), lekin tugma ko'rsatilmaydi — hamkasb
                  izohini tasodifan yo'q qilib qo'ymasin. */}
              {e.kim_id === profilId && (
                <span>
                  <button className="havola" type="button" onClick={() => setTahrir({
                    id: e.id, matn: e.matn,
                    // <input type=datetime-local> mahalliy vaqtni "YYYY-MM-DDTHH:MM" ko'rinishida kutadi.
                    vaqt: e.eslatish_vaqti ? mahalliyVaqt(e.eslatish_vaqti) : "",
                  })}>
                    {t("tahrirlash")}
                  </button>{" "}
                  <button className="havola" type="button" onClick={() => ochir(e.id)}>
                    {t("ochirish")}
                  </button>
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
