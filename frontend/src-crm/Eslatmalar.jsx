// Eslatmalar — guruh yoki talaba haqidagi erkin izohlar.
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

export default function Eslatmalar({ guruhId, talabaId, profilId }) {
  const { t } = useI18n();
  const [matn, setMatn] = useState("");
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  const yol = "/api/crm/eslatmalar/" + sorovSatri({ guruh: guruhId, talaba: talabaId });
  const { malumot, yuklanmoqda, yangila } = useSorov(yol);
  const eslatmalar = malumot || [];

  async function qosh() {
    if (!matn.trim()) return;
    setXato("");
    setBand(true);
    try {
      await api("/api/crm/eslatmalar/", {
        method: "POST",
        body: { guruh_id: guruhId ?? null, talaba_id: talabaId ?? null, matn },
      });
      setMatn("");
      yangila();
    } catch (e) {
      setXato(e.message || "Xato");
    } finally {
      setBand(false);
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
            <div className="eslatma-matn">{e.matn}</div>
            <div className="eslatma-past">
              <span className="kichik">
                {e.kim || "—"} · {vaqtMatni(e.vaqt)}
              </span>
              {/* O'chirish tugmasi faqat O'Z eslatmasida ko'rinadi.
                  Owner boshqanikini ham o'chira oladi (backend shunga
                  ruxsat beradi), lekin tugma ko'rsatilmaydi — hamkasb
                  izohini tasodifan yo'q qilib qo'ymasin. */}
              {e.kim_id === profilId && (
                <button className="havola" type="button" onClick={() => ochir(e.id)}>
                  {t("ochirish")}
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
