// Kirgan foydalanuvchi — butun CRM bo'ylab kerak bo'ladigan yagona
// ma'lumot (kim ekani, owner'mi). `App.jsx` uni bir marta so'raydi va
// shu yerda tarqatadi — har komponent qaytadan `/api/profil/` ga
// so'rov yubormasligi uchun.

import { createContext, useContext } from "react";

const ProfilContext = createContext(null);

export function ProfilProvider({ profil, children }) {
  return <ProfilContext.Provider value={profil}>{children}</ProfilContext.Provider>;
}

export function useProfil() {
  return useContext(ProfilContext);
}

/** Filialga bog'langanmi (2026-09-23): `true` — faqat o'z filiallari
 *  ko'rinadi, markaz sozlamalari (kurs narxi, filiallar) faqat o'qish uchun. */
export function useCheklangan() {
  const profil = useContext(ProfilContext);
  return Array.isArray(profil?.filiallar);
}

/** Ruxsat bormi: `useRuxsat()("lidlar.excel")`. Backend baribir
 *  tekshiradi — bu faqat tugmani yashirish uchun. */
export function useRuxsat() {
  const profil = useContext(ProfilContext);
  const toplam = new Set(profil?.ruxsatlar || []);
  return (kalit) => toplam.has(kalit);
}
