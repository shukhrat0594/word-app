// Sarlavhadagi filial almashtirgich.

import { useFilial } from "./filialContext.jsx";
import { useI18n } from "./i18n.jsx";

export default function FilialTanlash() {
  const { filiallar, tanlangan, setTanlangan } = useFilial();
  const { t } = useI18n();

  // Filial hali kiritilmagan bo'lsa — almashtirgich umuman ko'rsatilmaydi,
  // aks holda bo'sh ochiluvchi ro'yxat chalkashtiradi.
  if (filiallar.length === 0) return null;

  return (
    <select
      className="filial-tanlash"
      value={tanlangan}
      onChange={(e) => setTanlangan(e.target.value)}
      aria-label={t("hamma_filiallar")}
    >
      <option value="">{t("hamma_filiallar")}</option>
      {filiallar.map((f) => (
        <option key={f.id} value={String(f.id)}>
          {f.nomi}
        </option>
      ))}
    </select>
  );
}
