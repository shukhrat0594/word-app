// To'lov kiritish oynasi (TZ 4.5).
//
// ASOSIY QOIDA: kam summa kiritilsa, qoldiq SUKUT BO'YICHA QARZ bo'lib
// qoladi. Uni yopish uchun admin ALOHIDA «Chegirma» tugmasini bosishi
// kerak — aks holda admin adashib kam yozib yuborsa, pul indamay
// yo'qolardi va buni hech kim sezmasdi.

import { useState } from "react";

import { api } from "./api.js";
import { pul } from "./format.js";
import { useI18n } from "./i18n.jsx";

export default function TolovOynasi({ hisob, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const [summa, setSumma] = useState(String(hisob.qoldiq ?? hisob.summa ?? ""));
  const [sana, setSana] = useState(new Date().toISOString().slice(0, 10));
  const [izoh, setIzoh] = useState("");
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);
  // Saqlangandan KEYIN qoladigan qarz — chegirma tugmasi shunga qaraydi.
  const [qolgan, setQolgan] = useState(null);

  const kiritilgan = Number(summa || 0);
  const qoldiq = Number(hisob.qoldiq ?? 0);
  const kam = kiritilgan > 0 && kiritilgan < qoldiq;
  const kop = kiritilgan > qoldiq;

  async function yubor(turi, miqdor) {
    setXato("");
    setBand(true);
    try {
      await api("/api/crm/tolov/", {
        method: "POST",
        body: {
          talaba_id: hisob.talaba_id,
          guruh_id: hisob.guruh_id,
          hisob_id: hisob.id,
          summa: String(miqdor),
          turi,
          sana,
          izoh,
        },
      });
      return true;
    } catch (e) {
      setXato(e.message || "Xato");
      return false;
    } finally {
      setBand(false);
    }
  }

  async function saqla() {
    if (!(kiritilgan > 0)) {
      setXato(t("summa_kerak"));
      return;
    }
    if (!(await yubor("tolov", kiritilgan))) return;

    if (kam) {
      // Oynani YOPMAYMIZ: admin chegirma qilish yoki qilmaslik haqida
      // ongli qaror qabul qilishi kerak.
      setQolgan(qoldiq - kiritilgan);
      onSaqlandi({ yopmasdan: true });
    } else {
      onSaqlandi({});
      onYopish();
    }
  }

  async function chegirmaQil() {
    if (!(await yubor("chegirma", qolgan))) return;
    onSaqlandi({});
    onYopish();
  }

  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna">
        <h2>{t("tolov_qilish")}</h2>
        <p className="kichik">
          {hisob.talaba} · {hisob.guruh} · {String(hisob.oy).slice(0, 7)}
        </p>

        <div className="qator">
          <span className="kichik">{t("hisoblangan")}</span>
          <b>{pul(hisob.summa)}</b>
        </div>
        <div className="qator">
          <span className="kichik">{t("qoldiq")}</span>
          <b>{pul(qoldiq)}</b>
        </div>

        {qolgan === null ? (
          <>
            <label>
              {t("tolangan_summa")}
              <input
                type="number"
                min="0"
                step="1000"
                value={summa}
                onChange={(e) => setSumma(e.target.value)}
                autoFocus
              />
            </label>
            <label>
              {t("sana")}
              <input type="date" value={sana} onChange={(e) => setSana(e.target.value)} />
            </label>
            <label>
              {t("izoh")}
              <input value={izoh} onChange={(e) => setIzoh(e.target.value)} maxLength={300} />
            </label>

            {kam && <div className="ogohlantirish">{t("kam_summa_ogoh")}</div>}
            {kop && (
              <div className="ogohlantirish">
                {t("kop_summa_ogoh")} {pul(kiritilgan - qoldiq)}
              </div>
            )}
            {xato && <div className="xato">{xato}</div>}

            <div className="oyna-tugmalar">
              <button className="tugma tugma-sokin" type="button" onClick={onYopish}>
                {t("bekor")}
              </button>
              <button className="tugma" type="button" onClick={saqla} disabled={band}>
                {t("saqlash")}
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="ogohlantirish">
              {t("qarz_qoldi")}: <b>{pul(qolgan)}</b>
            </div>
            <p className="kichik">{t("chegirma_izoh")}</p>
            {xato && <div className="xato">{xato}</div>}
            <div className="oyna-tugmalar">
              <button className="tugma tugma-sokin" type="button" onClick={onYopish}>
                {t("qarz_qoldirish")}
              </button>
              <button className="tugma" type="button" onClick={chegirmaQil} disabled={band}>
                {t("chegirma_qilish")} ({pul(qolgan)})
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
