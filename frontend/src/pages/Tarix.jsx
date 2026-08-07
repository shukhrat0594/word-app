import NatijalarRoyxati from "../components/NatijalarRoyxati";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";

// 2026-08-05, foydalanuvchi talabi: talaba endi FAQAT Writing/Speaking
// emas, BARCHA (Reading/Listening/Kurslar) natijalarini ham shu yerda
// ko'radi — render mantig'i `NatijalarRoyxati`ga ko'chirildi (owner/
// teacher Talabalar.jsx'dan xuddi shu komponentni boshqa talaba uchun
// ochadi, kod takrorlanmaydi).
export default function Tarix() {
  const { t } = useI18n();
  const { profil } = useProfil();

  if (!profil) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <div className="karta">
      <h3>{t("mening_tarixim")}</h3>
      <NatijalarRoyxati talabaId={profil.id} />
    </div>
  );
}
