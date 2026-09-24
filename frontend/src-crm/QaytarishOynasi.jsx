// Pul qaytarish oynasi.
//
// Umumiy komponent: ham Moliya → Qarzdorlar jadvalidan, ham talaba
// kartasidan chaqiriladi. Ikki nusxa bo'lsa, biriga qo'shilgan tekshiruv
// ikkinchisida unutilib qolardi — pul harakatida bu qimmat.

import { useState } from "react";

import { api } from "./api.js";
import { pul } from "./format.js";
import { useI18n } from "./i18n.jsx";
import UsulTanlash from "./TolovUsuli.jsx";

export default function QaytarishOynasi({ talabaId, talabaIsmi, guruhId, guruhNomi, balans, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const [summa, setSumma] = useState("");
  const [sana, setSana] = useState(new Date().toISOString().slice(0, 10));
  const [usul, setUsul] = useState("naqd");
  const [izoh, setIzoh] = useState("");
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  async function yubor() {
    if (!(Number(summa) > 0)) {
      setXato(t("summa_kerak"));
      return;
    }
    setXato("");
    setBand(true);
    try {
      // `qaytarish` ATAYLAB oyga bog'lanmaydi (`oy`/`hisob_id`
      // yuborilmaydi) — u umumiy hisob-kitob, bitta oyning holatini
      // o'zgartirmaydi, faqat balansdan chiqadi.
      await api("/api/crm/tolov/", {
        method: "POST",
        body: {
          talaba_id: talabaId,
          guruh_id: guruhId,
          summa: String(summa),
          turi: "qaytarish",
          sana,
          usul,
          izoh,
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
        <h2>{t("pul_qaytarish")}</h2>
        <p className="kichik">{talabaIsmi} · {guruhNomi}</p>

        {balans !== undefined && balans !== null && (
          <div className="qator">
            <span className="kichik">{t("balans")}</span>
            <b>{pul(balans)}</b>
          </div>
        )}

        <label>
          {t("summa")}
          <input type="number" min="0" step="1000" value={summa}
                 onChange={(e) => setSumma(e.target.value)} autoFocus />
        </label>
        <UsulTanlash qiymat={usul} onChange={setUsul} />
        <label>
          {t("sana")}
          <input type="date" value={sana} onChange={(e) => setSana(e.target.value)} />
        </label>
        <label>
          {t("izoh")}
          <input value={izoh} onChange={(e) => setIzoh(e.target.value)} maxLength={300} />
        </label>

        <p className="kichik">{t("qaytarish_izoh")}</p>
        {xato && <div className="xato">{xato}</div>}

        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
          <button className="tugma" type="button" onClick={yubor} disabled={band}>{t("saqlash")}</button>
        </div>
      </div>
    </div>
  );
}
