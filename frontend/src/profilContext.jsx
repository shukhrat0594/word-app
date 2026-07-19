import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, tokenOl } from "./api";

const ProfilContext = createContext(null);

// Profil (parol_bormi, markaz, rol va h.k.) butun ilova bo'ylab bitta joyda
// saqlanadi — shuning uchun masalan Profil sahifasida parol qo'yilganda
// Layout'dagi ogohlantirish banner ham darhol (sahifani yangilamasdan) yo'qoladi.
export function ProfilProvider({ children }) {
  const [profil, setProfil] = useState(null);

  const yangila = useCallback(() => {
    if (!tokenOl()) return Promise.resolve();
    return api("/api/profil/").then(setProfil).catch(() => {});
  }, []);

  useEffect(() => {
    yangila();
  }, [yangila]);

  return (
    <ProfilContext.Provider value={{ profil, yangila }}>
      {children}
    </ProfilContext.Provider>
  );
}

export const useProfil = () => useContext(ProfilContext);
