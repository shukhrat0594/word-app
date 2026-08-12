import { useEffect, useState } from "react";
import { api, apiForm } from "../api";
import { useI18n } from "../i18n";
import { ProfilRasmi, QurilmaTiklashTugmasi } from "./Foydalanuvchilar";

const BOSH_FORMA = { ism: "", username: "", parol: "" };

export default function Xodimlar() {
  const { t } = useI18n();
  const [oqituvchilar, setOqituvchilar] = useState(null);
  const [forma, setForma] = useState(BOSH_FORMA);
  const [xato, setXato] = useState("");
  const [xabar, setXabar] = useState("");
  const [band, setBand] = useState(false);
  const [excelNatija, setExcelNatija] = useState(null);
  const [excelYuklanmoqda, setExcelYuklanmoqda] = useState(false);
  // Arxivlangan xodimlarni ko'rish (2026-08-02) — standart holatda faqat
  // faol (is_active=True) xodimlar ko'rinadi.
  const [arxivKorish, setArxivKorish] = useState(false);

  function yukla(arxiv = arxivKorish) {
    api(`/api/xodimlar/${arxiv ? "?arxiv=1" : ""}`).then(setOqituvchilar).catch(() => {});
  }

  useEffect(() => {
    yukla(arxivKorish);
  }, [arxivKorish]);

  async function arxivHolatiniOzgartir(id, yangiFaol) {
    setXato("");
    try {
      await api(`/api/xodimlar/${id}/`, { method: "PATCH", body: { faol: yangiFaol } });
      yukla();
    } catch {
      setXato(t("xato_yuz_berdi"));
    }
  }

  /** Nomaqbul profil rasmini o'chirish — sabab MAJBURIY va u xodimga
   * "Ogohlantirish" xabari bo'lib boradi (`ProfilRasmi` izohiga qarang).
   * Bu sahifaga faqat owner/admin kiradi, shuning uchun qo'shimcha rol
   * tekshiruvi shart emas. */
  async function rasmOchir(id, izoh) {
    setXato("");
    setXabar("");
    try {
      await api(`/api/foydalanuvchilar/${id}/rasm/`, { method: "DELETE", body: { izoh } });
      setXabar(t("rasm_ochirildi"));
      yukla();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    }
  }

  /** "Qurilmani tiklash" — sabab MAJBURIY, xodimga ogohlantirish
   * boradi (`QurilmaTiklashTugmasi` izohiga qarang). */
  async function qurilmaTiklash(id, izoh) {
    setXato("");
    setXabar("");
    try {
      await api(`/api/foydalanuvchilar/${id}/qurilma-tiklash/`, { method: "POST", body: { izoh } });
      setXabar(t("qurilma_tiklash_muvaffaqiyatli"));
      yukla();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    }
  }

  async function yarat() {
    setXato("");
    setXabar("");
    if (!forma.username.trim() || !forma.parol.trim()) {
      setXato(t("xato_yuz_berdi"));
      return;
    }
    setBand(true);
    try {
      await api("/api/xodimlar/", { method: "POST", body: forma });
      setForma(BOSH_FORMA);
      setXabar(t("saqlandi"));
      yukla();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  async function excelYukla(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setExcelNatija(null);
    setExcelYuklanmoqda(true);
    try {
      const fd = new FormData();
      fd.append("excel_fayl", fayl);
      const res = await apiForm("/api/xodimlar/excel-import/", { method: "POST", formData: fd });
      setExcelNatija(res);
      yukla();
    } catch (e2) {
      setExcelNatija({ yaratildi: [], xatolar: [{ xato: e2.data?.detail || t("xato_yuz_berdi") }] });
    } finally {
      setExcelYuklanmoqda(false);
    }
  }

  if (!oqituvchilar) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <>
      <div className="karta">
        <h3>{t("yangi_oqituvchi")}</h3>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <input
            style={{ maxWidth: 160 }}
            placeholder={t("ism")}
            value={forma.ism}
            onChange={(e) => setForma({ ...forma, ism: e.target.value })}
          />
          <input
            style={{ maxWidth: 160 }}
            placeholder={t("login")}
            value={forma.username}
            onChange={(e) => setForma({ ...forma, username: e.target.value })}
          />
          <input
            style={{ maxWidth: 160 }}
            type="password"
            placeholder={t("parol")}
            value={forma.parol}
            onChange={(e) => setForma({ ...forma, parol: e.target.value })}
          />
          <button className="tugma" onClick={yarat} disabled={band}>
            {t("yaratish")}
          </button>
        </div>
        {xato && <div className="xato-xabar" style={{ marginTop: 10 }}>{xato}</div>}
        {xabar && <div className="izoh" style={{ marginTop: 10 }}>{xabar}</div>}
      </div>

      <div className="karta" style={{ marginTop: 16 }}>
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

      <div className="karta" style={{ marginTop: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3>{arxivKorish ? t("arxivlangan_xodimlar") : t("nav_xodimlar")}</h3>
          <button className="tugma ikkinchi kichik" onClick={() => setArxivKorish((v) => !v)}>
            {arxivKorish ? t("faol_xodimlar") : t("arxivlangan_xodimlar")}
          </button>
        </div>
        {oqituvchilar.length === 0 && <span className="izoh">{t("oqituvchi_yoq")}</span>}
        {oqituvchilar.map((o) => (
          <div className="tarix-el" key={o.id}>
            <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <ProfilRasmi user={o} ochir={rasmOchir} t={t} />
              <span>{o.ism}</span>
              <span className="izoh">{o.username}</span>
            </span>
            <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <QurilmaTiklashTugmasi user={o} tiklash={qurilmaTiklash} t={t} />
              <button
                className="tugma ikkinchi kichik"
                onClick={() => arxivHolatiniOzgartir(o.id, arxivKorish)}
              >
                {arxivKorish ? t("faollashtirish") : t("arxivlash")}
              </button>
            </span>
          </div>
        ))}
      </div>
    </>
  );
}
