import { useEffect, useState } from "react";
import { api, apiForm } from "../api";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";

/** Talabalar ro'yxati. Owner/admin — o'z markazidagi barcha talabalar +
 * Excel orqali ommaviy kiritish. O'qituvchi — faqat o'z guruhlaridagi
 * talabalar, faqat o'qish (kiritish yo'q). */
export default function Talabalar() {
  const { t } = useI18n();
  const { profil } = useProfil();
  const boshqaruvMi = profil?.is_owner || profil?.role === "admin";
  const [talabalar, setTalabalar] = useState(null);
  const [excelNatija, setExcelNatija] = useState(null);
  const [excelYuklanmoqda, setExcelYuklanmoqda] = useState(false);

  function yukla() {
    api("/api/talabalar/").then(setTalabalar).catch(() => {});
  }

  useEffect(() => {
    yukla();
  }, []);

  async function excelYukla(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setExcelNatija(null);
    setExcelYuklanmoqda(true);
    try {
      const fd = new FormData();
      fd.append("excel_fayl", fayl);
      const res = await apiForm("/api/talabalar/excel-import/", { method: "POST", formData: fd });
      setExcelNatija(res);
      yukla();
    } catch (e2) {
      setExcelNatija({ yaratildi: [], xatolar: [{ xato: e2.data?.detail || t("xato_yuz_berdi") }] });
    } finally {
      setExcelYuklanmoqda(false);
    }
  }

  if (!talabalar) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <>
      {boshqaruvMi && (
        <div className="karta">
          <h3>{t("excel_orqali_kiritish")}</h3>
          <p className="izoh" style={{ marginTop: 0 }}>{t("excel_izoh")}</p>
          <input type="file" accept=".xlsx" onChange={excelYukla} disabled={excelYuklanmoqda} />
          {excelNatija && (
            <div style={{ marginTop: 12 }}>
              {excelNatija.yaratildi.length > 0 && (
                <>
                  <div className="izoh">{t("excel_yaratildi")}: {excelNatija.yaratildi.length}</div>
                  <div className="xato-xabar" style={{ background: "none", color: "inherit", padding: 0 }}>
                    {t("excel_parol_eslatma")}
                  </div>
                  <div style={{ display: "grid", gap: 4, marginTop: 6 }}>
                    {excelNatija.yaratildi.map((y) => (
                      <div key={y.id} className="izoh">{y.ism} — {y.login}</div>
                    ))}
                  </div>
                </>
              )}
              {excelNatija.xatolar.length > 0 && (
                <div style={{ marginTop: 10 }}>
                  {excelNatija.xatolar.map((x, i) => (
                    <div key={i} className="xato-xabar">
                      {x.qator ? `${t("qator")} ${x.qator}: ` : ""}{x.xato}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="karta" style={{ marginTop: boshqaruvMi ? 16 : 0 }}>
        <h3>{t("nav_talabalar")}</h3>
        {talabalar.length === 0 && <span className="izoh">{t("talaba_yoq")}</span>}
        {talabalar.map((tl) => (
          <div className="tarix-el" key={tl.id}>
            <span>{tl.ism}</span>
            <span className="izoh">{tl.username}</span>
          </div>
        ))}
      </div>
    </>
  );
}
