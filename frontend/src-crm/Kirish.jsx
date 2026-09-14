// CRM kirish oynasi.
//
// LMS'ga allaqachon kirgan admin bu oynani KO'RMAYDI: ikkala ilova bir
// xil origin'da, token localStorage'da umumiy (`api.js` izohiga qara).
// Oyna faqat token umuman yo'q yoki eskirgan bo'lsa chiqadi.

import { useState } from "react";

import { api, qurilmaIdOl, tokenlarniSaqla } from "./api.js";
import { useI18n } from "./i18n.jsx";

export default function Kirish({ onKirdi }) {
  const { t } = useI18n();
  const [login, setLogin] = useState("");
  const [parol, setParol] = useState("");
  const [xato, setXato] = useState("");
  const [yuborilmoqda, setYuborilmoqda] = useState(false);

  async function yubor(e) {
    e.preventDefault();
    setXato("");
    setYuborilmoqda(true);
    try {
      const javob = await api("/api/token/", {
        method: "POST",
        // `qurilma_id` — hisobni bo'lishmaslik nazorati uchun, LMS bilan
        // bir xil kalit (`accounts.views.XodimLoginView`).
        body: { username: login, password: parol, qurilma_id: qurilmaIdOl() },
      });
      tokenlarniSaqla(javob);
      await onKirdi();
    } catch (err) {
      setXato(err.message || "Xato");
    } finally {
      setYuborilmoqda(false);
    }
  }

  return (
    <div className="markaz-ekran">
      <form className="karta kirish-karta" onSubmit={yubor}>
        <h1>{t("crm")}</h1>
        <p className="kichik">Utmost Academy</p>

        <label>
          {t("login")}
          <input
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
        </label>

        <label>
          {t("parol")}
          <input
            type="password"
            value={parol}
            onChange={(e) => setParol(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        {xato && <div className="xato">{xato}</div>}

        <button className="tugma" type="submit" disabled={yuborilmoqda}>
          {yuborilmoqda ? t("kirilmoqda") : t("kirish_tugma")}
        </button>
      </form>
    </div>
  );
}
