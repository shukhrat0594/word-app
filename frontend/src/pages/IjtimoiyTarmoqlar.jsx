import { useEffect, useState } from "react";
import { api, apiForm } from "../api";
import IjtimoiyIkon from "../components/IjtimoiyIkonlar";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";

// Tartib va yorliqlar backend bilan bir xil (accounts.Markaz.IJTIMOIY_MAYDONLAR).
export const TARMOQLAR = [
  { kalit: "telegram", nomi: "Telegram", namuna: "t.me/utmost" },
  { kalit: "instagram", nomi: "Instagram", namuna: "instagram.com/utmost" },
  { kalit: "youtube", nomi: "YouTube", namuna: "youtube.com/@utmost" },
  { kalit: "facebook", nomi: "Facebook", namuna: "facebook.com/utmost" },
];

/** Admin/owner uchun — markazning ijtimoiy tarmoq havolalari (2026-07-27).
 * Havolasi kiritilganlari saytning pastki panelida ko'rinadi, bo'sh
 * qoldirilganlari umuman chiqmaydi. */
export default function IjtimoiyTarmoqlar() {
  const { t } = useI18n();
  const { profil, yangila } = useProfil();
  const [qiymatlar, setQiymatlar] = useState(null);
  const [ochiq, setOchiq] = useState(true);
  const [xato, setXato] = useState("");
  const [xabar, setXabar] = useState("");
  const [band, setBand] = useState(false);

  useEffect(() => {
    api("/api/markaz-sozlama/")
      .then((m) => setQiymatlar(m.ijtimoiy || {}))
      .catch((e) => {
        setQiymatlar({});
        setXato(e.data?.detail || t("xato_yuz_berdi"));
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function saqla() {
    setXato("");
    setXabar("");
    setBand(true);
    try {
      // Backend MultiPartParser kutadi (logo yuklash uchun) — shuning uchun
      // FormData bilan yuboriladi.
      const fd = new FormData();
      TARMOQLAR.forEach(({ kalit }) => fd.append(kalit, qiymatlar[kalit] || ""));
      const m = await apiForm("/api/markaz-sozlama/", { method: "PATCH", formData: fd });
      setQiymatlar(m.ijtimoiy || {});
      setXabar(t("saqlandi"));
      // Pastki panel darhol yangilanishi uchun profilni qayta o'qiymiz
      if (yangila) yangila();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  const boshqaruvMi = profil?.is_owner || profil?.role === "admin";
  if (!boshqaruvMi) return <div className="karta">{t("faqat_admin")}</div>;
  if (!qiymatlar) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  const toldirilgan = TARMOQLAR.filter(({ kalit }) => (qiymatlar[kalit] || "").trim()).length;

  return (
    <div className="karta">
      <h3
        style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}
        onClick={() => setOchiq((v) => !v)}
      >
        <span>{ochiq ? "▾" : "▸"}</span>
        {t("nav_ijtimoiy")}
        <span className="chip bor">{toldirilgan}/{TARMOQLAR.length}</span>
      </h3>

      {ochiq && (
        <>
          <p className="izoh" style={{ marginTop: 0 }}>{t("ijtimoiy_izoh")}</p>
          <div style={{ display: "grid", gap: 10, maxWidth: 560 }}>
            {TARMOQLAR.map(({ kalit, nomi, namuna }) => (
              <div key={kalit} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span
                  style={{ width: 130, fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 8 }}
                >
                  <IjtimoiyIkon kalit={kalit} /> {nomi}
                </span>
                <input
                  style={{ flex: 1, minWidth: 0 }}
                  placeholder={namuna}
                  value={qiymatlar[kalit] || ""}
                  onChange={(e) => setQiymatlar({ ...qiymatlar, [kalit]: e.target.value })}
                />
              </div>
            ))}
          </div>
          <button className="tugma" style={{ marginTop: 14 }} onClick={saqla} disabled={band}>
            {t("saqlash")}
          </button>
          {xato && <div className="xato-xabar" style={{ marginTop: 10 }}>{xato}</div>}
          {xabar && <div className="izoh" style={{ marginTop: 10 }}>{xabar}</div>}
        </>
      )}
    </div>
  );
}
