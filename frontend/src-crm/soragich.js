// API so'rovi uchun kichik hook — yuklanish/xato holatini bir joyda
// boshqaradi, har sahifada takrorlanmasligi uchun.

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "./api.js";

/**
 * @param yol   API manzili (null bo'lsa so'rov yuborilmaydi)
 * @returns {{malumot, yuklanmoqda, xato, yangila}}
 */
export function useSorov(yol) {
  const [malumot, setMalumot] = useState(null);
  const [yuklanmoqda, setYuklanmoqda] = useState(Boolean(yol));
  const [xato, setXato] = useState("");
  // Sahifa tez almashtirilsa, ESKI so'rovning javobi kechikib kelib
  // yangisini bosib ketishi mumkin — shuning uchun har so'rovga raqam
  // beramiz va faqat oxirgisining javobini qabul qilamiz.
  const navbat = useRef(0);

  const yangila = useCallback(async () => {
    if (!yol) {
      setMalumot(null);
      setYuklanmoqda(false);
      return;
    }
    const men = ++navbat.current;
    setYuklanmoqda(true);
    setXato("");
    try {
      const javob = await api(yol);
      if (men === navbat.current) setMalumot(javob);
    } catch (e) {
      if (men === navbat.current) setXato(e.message || "Xato");
    } finally {
      if (men === navbat.current) setYuklanmoqda(false);
    }
  }, [yol]);

  useEffect(() => {
    yangila();
  }, [yangila]);

  return { malumot, yuklanmoqda, xato, yangila };
}

/** Filtr obyektidan so'rov satri: {oy: "2026-09", guruh: ""} -> "?oy=2026-09" */
export function sorovSatri(filtrlar) {
  const parametrlar = new URLSearchParams();
  for (const [kalit, qiymat] of Object.entries(filtrlar)) {
    if (qiymat !== "" && qiymat !== null && qiymat !== undefined) {
      parametrlar.set(kalit, String(qiymat));
    }
  }
  const satr = parametrlar.toString();
  return satr ? `?${satr}` : "";
}
