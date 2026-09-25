// Vaqti kelgan eslatmalar — 🔔 xabarnoma (sarlavhada) va bosh sahifa bloki
// (video-TZ 2026-09-25, SoffCRM "Xabarnomalar": "Lid (test) bo'yicha
// eslatma … lidga o'tish").
//
// Admin: "Vaqti o'tgan eslatmani bajarildi deb belgilash yoki o'chirish
// imkoniyati yo'q". Endi har birida "Bajarildi" bor — belgilangach ikkala
// joydan ham yo'qoladi. Ro'yxat BITTA (kontekstda): sarlavhada belgilansa,
// bosh sahifa ham darhol yangilanadi.

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "./api.js";
import { useI18n } from "./i18n.jsx";
import { useSorov } from "./soragich.js";

// Yangi eslatma vaqti kelganini sahifani yangilamasdan ko'rish uchun.
const YANGILASH_MS = 2 * 60 * 1000;

const EslatmaContext = createContext(null);

export function EslatmaXabarProvider({ children }) {
  const { malumot, yangila } = useSorov("/api/crm/eslatmalar/muddatli/");
  const [xato, setXato] = useState("");

  useEffect(() => {
    const id = setInterval(yangila, YANGILASH_MS);
    return () => clearInterval(id);
  }, [yangila]);

  async function bajarildi(id) {
    setXato("");
    try {
      await api(`/api/crm/eslatmalar/${id}/`, { method: "PATCH", body: { bajarildi: true } });
      yangila();
    } catch (e) {
      setXato(e.message);
    }
  }

  return (
    <EslatmaContext.Provider value={{ royxat: malumot || [], bajarildi, yangila, xato }}>
      {children}
    </EslatmaContext.Provider>
  );
}

export function useEslatmaXabarlari() {
  return useContext(EslatmaContext) || { royxat: [], bajarildi: async () => {}, yangila: () => {}, xato: "" };
}

/** Eslatma qayerga tegishli — o'sha joyga havola. */
function Manzil({ e }) {
  const { t } = useI18n();
  if (e.lid_id) return <Link className="havola" to={`/lidlar?lid=${e.lid_id}`}>🎯 {e.lid} — {t("lidga_otish")}</Link>;
  if (e.talaba_id) return <Link className="havola" to={`/talabalar?talaba=${e.talaba_id}`}>👤 {e.talaba}</Link>;
  if (e.guruh_id) return <Link className="havola" to={`/guruhlar/${e.guruh_id}`}>📚 {e.guruh}</Link>;
  return null;
}

export function EslatmaRoyxati({ royxat, onBajarildi, onOtish }) {
  const { t } = useI18n();
  return (
    <ul className="eslatma-xabarlar">
      {royxat.map((e) => (
        <li key={e.id}>
          <div className="eslatma-xabar-bosh">
            <span onClick={onOtish}><Manzil e={e} /></span>
            <span className={`kichik ${e.otgan ? "rang-qarzdor" : "rang-qisman"}`}>
              {new Date(e.eslatish_vaqti).toLocaleString(undefined, {
                day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
              })}
            </span>
          </div>
          <div className="eslatma-xabar-past">
            <span>{e.matn}</span>
            <button className="tugma kichik-tugma" type="button" onClick={() => onBajarildi(e.id)}>
              ✓ {t("bajarildi_belgi")}
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

/** Bosh sahifadagi blok — eslatma bo'lmasa ko'rinmaydi. */
export function VaqtiKelganEslatmalar() {
  const { t } = useI18n();
  const { royxat, bajarildi, xato } = useEslatmaXabarlari();
  if (!royxat.length) return null;
  return (
    <div className="karta">
      <h2>⏰ {t("vaqti_kelgan_eslatmalar")} <span className="kichik">({royxat.length})</span></h2>
      {xato && <div className="xato">{xato}</div>}
      <EslatmaRoyxati royxat={royxat} onBajarildi={bajarildi} />
    </div>
  );
}

/** Sarlavhadagi 🔔 — soni va ochiladigan ro'yxat. */
export function XabarQongirogi() {
  const { t } = useI18n();
  const { royxat, bajarildi, xato } = useEslatmaXabarlari();
  const [ochiq, setOchiq] = useState(false);
  const joy = useRef(null);

  // Tashqariga bosilsa yopiladi.
  useEffect(() => {
    if (!ochiq) return undefined;
    const yop = (ev) => { if (joy.current && !joy.current.contains(ev.target)) setOchiq(false); };
    document.addEventListener("mousedown", yop);
    return () => document.removeEventListener("mousedown", yop);
  }, [ochiq]);

  return (
    <span className="xabar-qongiroq" ref={joy}>
      <button className="tugma tugma-sokin" type="button" aria-label={t("xabarnomalar")}
              title={t("xabarnomalar")} onClick={() => setOchiq(!ochiq)}>
        🔔{royxat.length > 0 && <span className="xabar-soni">{royxat.length}</span>}
      </button>
      {ochiq && (
        <div className="xabar-panel karta">
          <h3>{t("xabarnomalar")}</h3>
          {xato && <div className="xato">{xato}</div>}
          {royxat.length === 0
            ? <p className="kichik">{t("xabarnoma_yoq")}</p>
            : <EslatmaRoyxati royxat={royxat} onBajarildi={bajarildi} onOtish={() => setOchiq(false)} />}
        </div>
      )}
    </span>
  );
}
