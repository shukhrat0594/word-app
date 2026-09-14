// Moliya sahifasi. Hozircha zagotovka — mazmuni keyingi qadamda
// (TZ 6.3-6.5). Marshrutlash shu bosqichda tekshiriladi.

import { useI18n } from "../i18n.jsx";

export default function Moliya() {
  const { t } = useI18n();
  return (
    <section className="karta">
      <h1>{t("moliya")}</h1>
      <p className="kichik">Tez kunda</p>
    </section>
  );
}
