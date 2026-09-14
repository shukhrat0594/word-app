// Tanlangan filial — butun CRM bo'ylab umumiy holat.
//
// Tanlov `localStorage`da saqlanadi: admin odatda BITTA filialda ishlaydi
// va har sahifada qaytadan tanlash zerikarli bo'lardi.

import { createContext, useContext, useEffect, useState } from "react";

import { api } from "./api.js";

const KALIT = "crm_filial";
const HAMMASI = "";

const FilialContext = createContext(null);

export function FilialProvider({ children }) {
  const [filiallar, setFiliallar] = useState([]);
  const [tanlangan, setTanlangan] = useState(() => localStorage.getItem(KALIT) || HAMMASI);

  useEffect(() => {
    // Xato yutiladi: filiallar hali kiritilmagan bo'lsa ham CRM
    // ochilishda davom etsin — bo'sh ro'yxat "barcha filiallar" degani.
    api("/api/crm/filiallar/")
      .then((x) => setFiliallar(x?.natijalar ?? x ?? []))
      .catch(() => setFiliallar([]));
  }, []);

  useEffect(() => {
    if (tanlangan) localStorage.setItem(KALIT, tanlangan);
    else localStorage.removeItem(KALIT);
  }, [tanlangan]);

  return (
    <FilialContext.Provider value={{ filiallar, tanlangan, setTanlangan }}>
      {children}
    </FilialContext.Provider>
  );
}

export function useFilial() {
  const qiymat = useContext(FilialContext);
  if (!qiymat) throw new Error("useFilial faqat FilialProvider ichida ishlaydi");
  return qiymat;
}
