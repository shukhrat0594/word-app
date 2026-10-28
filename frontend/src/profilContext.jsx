import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, tokenOl } from "./api";

const ProfilContext = createContext(null);

// Profil (parol_bormi, markaz, rol va h.k.) butun ilova bo'ylab bitta joyda
// saqlanadi — shuning uchun masalan Profil sahifasida parol qo'yilganda
// Layout'dagi ogohlantirish banner ham darhol (sahifani yangilamasdan) yo'qoladi.
export function ProfilProvider({ children }) {
  const [profil, setProfil] = useState(null);
  // 2026-10-29: profil yuklanmasa (server xatosi, internet) — sahifa jim bo'sh qolmasin, xabar chiqsin.
  const [xato, setXato] = useState(false);

  const yangila = useCallback(() => {
    if (!tokenOl()) return Promise.resolve();
    return api("/api/profil/")
      .then((p) => {
        setProfil(p);
        setXato(false);
      })
      .catch(() => setXato(true));
  }, []);

  useEffect(() => {
    yangila();
  }, [yangila]);

  return (
    <ProfilContext.Provider value={{ profil, yangila, xato }}>
      {children}
    </ProfilContext.Provider>
  );
}

export const useProfil = () => useContext(ProfilContext);
