// Narxlar — kurs (daraja) darajasidagi oylik narxlar.
//
// Narx ATAYLAB guruhda emas, KURSDA (darajada) turadi: IELTS 660 000
// bir marta kiritiladi va o'sha darajaning barcha guruhlari uni oladi.
// Guruhga yoki alohida talabaga boshqacha narx kerak bo'lsa — Guruhlar
// sahifasidan bekor qilinadi.

import { useState } from "react";

import { api } from "../api.js";
import { useI18n } from "../i18n.jsx";
import { useCheklangan } from "../profilContext.jsx";
import { useSorov } from "../soragich.js";

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
  const { malumot, yuklanmoqda, xato, yangila } = useSorov("/api/crm/kurs-narxlari/");
  const qatorlar = malumot || [];
  const belgilangan = qatorlar.filter((q) => q.narx != null).length;

  return (
    <section>
      <h1>{t("kurs_narxlari")}</h1>
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
    </section>
  );
}
