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
