// To'lov usuli tanlovi (video-TZ, 2026-09-23: SoffCRM to'lov oynasidagi
// "Naqd / Click" tugmalari). Backend: `crm.models.Tolov.Usul`.

import { useI18n } from "./i18n.jsx";

// Video (21:15): Naqd, Click, Karta orqali, Yagona QR-kod, Perechisleniye, Voucher.
const USULLAR = ["naqd", "karta", "click", "payme", "qr", "otkazma", "voucher"];

export default function UsulTanlash({ qiymat, onChange }) {
  const { t } = useI18n();
  return (
    <div className="usul-tanlash" role="radiogroup" aria-label={t("tolov_usuli")}>
      {USULLAR.map((u) => (
        <button
          key={u}
          type="button"
          role="radio"
          aria-checked={qiymat === u}
          className={qiymat === u ? "tab faol" : "tab"}
          onClick={() => onChange(u)}
        >
          {t(`usul_${u}`)}
        </button>
      ))}
    </div>
  );
}
