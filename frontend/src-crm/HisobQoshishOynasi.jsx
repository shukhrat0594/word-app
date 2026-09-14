// Qo'lda hisob qo'shish — BOSHLANG'ICH (eski) qarzlar uchun (TZ 4.7).
//
// Tizim yoqilgan kunda ba'zi talabalarning eski qarzi bo'ladi. Avtomatik
// generatsiya `Sozlama.boshlangich_oy`dan oldinga o'tmaydi, shuning uchun
// eski qarz aynan shu yo'l bilan kiritiladi. Yaratilgach u oddiy
// hisobdek ishlaydi — to'lash ham, chegirma bilan yopish ham mumkin.

import { useEffect, useState } from "react";

import { api } from "./api.js";
import { siljit, joriyOy } from "./format.js";
import { useI18n } from "./i18n.jsx";
import { useSorov } from "./soragich.js";

export default function HisobQoshishOynasi({ onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const [guruhId, setGuruhId] = useState("");
  const [talabaId, setTalabaId] = useState("");
  // Standart — O'TGAN oy: bu oyni tizim o'zi ochadi, qo'lda kiritish
  // odatda undan oldingi qarz uchun kerak bo'ladi.
  const [oy, setOy] = useState(siljit(joriyOy(), -1));
  const [summa, setSumma] = useState("");
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  const guruhlar = useSorov("/api/crm/guruhlar/");
  const azolar = useSorov(guruhId ? `/api/crm/guruhlar/${guruhId}/azoliklar/` : null);

  // Guruh almashsa, eski talaba tanlovi boshqa guruhga tegishli bo'lib
  // qolmasligi kerak.
  useEffect(() => {
    setTalabaId("");
  }, [guruhId]);

  async function yubor() {
    if (!guruhId || !talabaId) {
      setXato(t("guruh_talaba_kerak"));
      return;
    }
    if (!(Number(summa) > 0)) {
      setXato(t("summa_kerak"));
      return;
    }
    setXato("");
    setBand(true);
    try {
      await api("/api/crm/hisoblar/", {
        method: "POST",
        body: { talaba_id: talabaId, guruh_id: guruhId, oy, summa: String(summa) },
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
        <h2>{t("qolda_hisob")}</h2>
        <p className="kichik">{t("qolda_hisob_izoh")}</p>

        <label>
          {t("guruh")}
          <select value={guruhId} onChange={(e) => setGuruhId(e.target.value)}>
            <option value="">—</option>
            {(guruhlar.malumot || []).map((g) => (
              <option key={g.id} value={g.id}>{g.nomi}</option>
            ))}
          </select>
        </label>

        <label>
          {t("talaba")}
          <select
            value={talabaId}
            onChange={(e) => setTalabaId(e.target.value)}
            disabled={!guruhId || azolar.yuklanmoqda}
          >
            <option value="">{azolar.yuklanmoqda ? t("yuklanmoqda") : "—"}</option>
            {(azolar.malumot || []).map((a) => (
              <option key={a.id} value={a.talaba_id}>{a.talaba}</option>
            ))}
          </select>
        </label>

        <label>
          {t("qaysi_oy")}
          <input type="month" value={oy} onChange={(e) => setOy(e.target.value)} />
        </label>

        <label>
          {t("summa")}
          <input type="number" min="0" step="1000" value={summa}
                 onChange={(e) => setSumma(e.target.value)} />
        </label>

        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
          <button className="tugma" type="button" onClick={yubor} disabled={band}>{t("saqlash")}</button>
        </div>
      </div>
    </div>
  );
}
