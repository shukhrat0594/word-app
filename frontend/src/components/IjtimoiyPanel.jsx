import { useEffect, useState } from "react";
import { api } from "../api";
import IjtimoiyIkon from "./IjtimoiyIkonlar";

// Tartib va nomlar backend bilan bir xil (accounts.Markaz.IJTIMOIY_MAYDONLAR).
const IJTIMOIY = [
  { kalit: "telegram", nomi: "Telegram" },
  { kalit: "instagram", nomi: "Instagram" },
  { kalit: "youtube", nomi: "YouTube" },
  { kalit: "facebook", nomi: "Facebook" },
];

/** Saytning pastki paneli — markazning ijtimoiy tarmoqlari (2026-07-27).
 *
 * HAMMAGA ko'rinadi: tizimga kirgan foydalanuvchiga ham, kirish ekranidagi
 * mehmonga ham. Shuning uchun ma'lumot ikki manbadan olinishi mumkin:
 *   * `havolalar` prop berilsa — profildan (Layout shundan foydalanadi;
 *     admin havolani saqlagach panel darhol yangilanadi, chunki profil
 *     qayta o'qiladi);
 *   * berilmasa — ochiq `/api/ijtimoiy/` endpointidan (Login sahifasi,
 *     u yerda profil yo'q).
 *
 * Panel DOIM EKRANDA turadi (`position: sticky`) va FAQAT BELGILARDAN
 * iborat — na sarlavha, na tarmoq nomi yoziladi. Nomi `title`/`aria-label`
 * da qoladi. Birorta havola kiritilmagan bo'lsa panel umuman chiqmaydi.
 */
export default function IjtimoiyPanel({ havolalar }) {
  const [olingan, setOlingan] = useState(null);

  useEffect(() => {
    if (havolalar) return; // profildan keldi — qo'shimcha so'rov shart emas
    let bekor = false;
    api("/api/ijtimoiy/")
      .then((d) => !bekor && setOlingan(d || {}))
      .catch(() => !bekor && setOlingan({}));
    return () => {
      bekor = true;
    };
  }, [havolalar]);

  const manba = havolalar || olingan || {};
  const bor = IJTIMOIY.filter((x) => manba[x.kalit]);
  if (bor.length === 0) return null;

  return (
    <footer className="ijtimoiy-panel">
      <div className="ijtimoiy-havolalar">
        {bor.map((x) => (
          <a
            key={x.kalit}
            href={manba[x.kalit]}
            target="_blank"
            rel="noopener noreferrer"
            title={x.nomi}
            aria-label={x.nomi}
          >
            <IjtimoiyIkon kalit={x.kalit} olcham={20} />
          </a>
        ))}
      </div>
    </footer>
  );
}
