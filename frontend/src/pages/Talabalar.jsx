import { useEffect, useState } from "react";
import { api, apiForm } from "../api";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";
import NatijalarRoyxati from "../components/NatijalarRoyxati";
import { PanelTanlovi, ProfilRasmi, QurilmaTiklashTugmasi } from "./Foydalanuvchilar";

const BOSH_FORMA = { ism: "", login: "", parol: "" };

/** Talabalar ro'yxati. Owner/admin — o'z markazidagi barcha talabalar,
 * bittalab qo'shish (2026-07-27) va Excel orqali ommaviy kiritish.
 * O'qituvchi — faqat o'z guruhlaridagi talabalar, faqat o'qish. */
export default function Talabalar() {
  const { t } = useI18n();
  const { profil } = useProfil();
  const boshqaruvMi = profil?.is_owner || profil?.role === "admin";
  const [talabalar, setTalabalar] = useState(null);
  const [excelNatija, setExcelNatija] = useState(null);
  const [excelYuklanmoqda, setExcelYuklanmoqda] = useState(false);
  const [forma, setForma] = useState(BOSH_FORMA);
  const [xato, setXato] = useState("");
  const [xabar, setXabar] = useState("");
  const [band, setBand] = useState(false);
  // Arxivlangan talabalarni ko'rish (2026-08-02) — standart holatda faqat
  // faol (is_active=True) talabalar ko'rinadi.
  const [arxivKorish, setArxivKorish] = useState(false);
  // 2026-08-05, foydalanuvchi talabi: talaba ustiga bosilganda uning
  // barcha mashq/test natijalari (turi bo'yicha) ko'rsatiladigan oyna.
  const [natijaTalaba, setNatijaTalaba] = useState(null);

  function yukla(arxiv = arxivKorish) {
    api(`/api/talabalar/${arxiv ? "?arxiv=1" : ""}`).then(setTalabalar).catch(() => {});
  }

  useEffect(() => {
    yukla(arxivKorish);
  }, [arxivKorish]);

  async function arxivHolatiniOzgartir(id, yangiFaol) {
    setXato("");
    try {
      await api(`/api/talabalar/${id}/`, { method: "PATCH", body: { faol: yangiFaol } });
      yukla();
    } catch {
      setXato(t("xato_yuz_berdi"));
    }
  }

  async function panellarSaqla(id, panellar) {
    try {
      await api(`/api/foydalanuvchilar/${id}/panellar/`, { method: "PATCH", body: { panellar } });
      yukla();
    } catch {
      setXato(t("xato_yuz_berdi"));
    }
  }

  /** Nomaqbul profil rasmini o'chirish — sabab MAJBURIY va u talabaga
   * "Ogohlantirish" xabari bo'lib boradi (`ProfilRasmi` izohiga qarang). */
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

  /** "Qurilmani tiklash" — sabab MAJBURIY, talabaga ogohlantirish
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

  async function talabaQosh() {
    setXato("");
    setXabar("");
    if (!forma.ism.trim() || !forma.login.trim() || !forma.parol.trim()) {
      setXato(t("majburiy_maydonlar"));
      return;
    }
    setBand(true);
    try {
      const yangi = await api("/api/talabalar/", { method: "POST", body: forma });
      setForma(BOSH_FORMA);
      setXabar(`${t("talaba_qoshildi")}: ${yangi.ism} — ${yangi.username}`);
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
          <h3>{t("yangi_talaba")}</h3>
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
              value={forma.login}
              onChange={(e) => setForma({ ...forma, login: e.target.value })}
            />
            <input
              style={{ maxWidth: 160 }}
              type="password"
              placeholder={t("parol")}
              value={forma.parol}
              onChange={(e) => setForma({ ...forma, parol: e.target.value })}
            />
            <button className="tugma" onClick={talabaQosh} disabled={band}>
              {t("yaratish")}
            </button>
          </div>
          <p className="izoh" style={{ marginBottom: 0 }}>{t("talaba_guruh_eslatma")}</p>
          {xato && <div className="xato-xabar" style={{ marginTop: 10 }}>{xato}</div>}
          {xabar && <div className="izoh" style={{ marginTop: 10 }}>{xabar}</div>}
        </div>
      )}

      {boshqaruvMi && (
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
      )}

      <div className="karta" style={{ marginTop: boshqaruvMi ? 16 : 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3>{arxivKorish ? t("arxivlangan_talabalar") : t("nav_talabalar")}</h3>
          {boshqaruvMi && (
            <button className="tugma ikkinchi kichik" onClick={() => setArxivKorish((v) => !v)}>
              {arxivKorish ? t("faol_talabalar") : t("arxivlangan_talabalar")}
            </button>
          )}
        </div>
        {talabalar.length === 0 && <span className="izoh">{t("talaba_yoq")}</span>}
        {talabalar.map((tl) => (
          <div className="tarix-el" key={tl.id}>
            <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {/* Rasm ALOHIDA turadi — ismga bosilganda natijalar oynasi
                  ochiladi, rasmga bosilganda esa o'chirish oynasi; ikkisi
                  bir joyda bo'lsa bosish bir-biriga tushib ketardi. */}
              <ProfilRasmi user={tl} ochir={boshqaruvMi ? rasmOchir : undefined} t={t} />
              <span
                style={{ display: "flex", gap: 8, cursor: "pointer", alignItems: "center" }}
                onClick={() => setNatijaTalaba(tl)}
                title={t("talaba_natijalarini_kor")}
              >
                <span>{tl.ism}</span>
                <span className="izoh">{tl.username}</span>
              </span>
            </span>
            {boshqaruvMi && (
              <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <PanelTanlovi user={tl} saqlash={panellarSaqla} t={t} />
                <QurilmaTiklashTugmasi user={tl} tiklash={qurilmaTiklash} t={t} />
                <button
                  className="tugma ikkinchi kichik"
                  onClick={() => arxivHolatiniOzgartir(tl.id, arxivKorish)}
                >
                  {arxivKorish ? t("faollashtirish") : t("arxivlash")}
                </button>
              </span>
            )}
          </div>
        ))}
      </div>

      {natijaTalaba && (
        <div className="blok-yuklash-qoplama" onClick={() => setNatijaTalaba(null)}>
          <div
            className="blok-tasdiq-karta"
            style={{ maxWidth: 700 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="blok-tasdiq-sarlavha-qator">
              <strong>{natijaTalaba.ism}</strong>
              <button className="tugma ikkinchi kichik" onClick={() => setNatijaTalaba(null)}>
                {t("yopish")}
              </button>
            </div>
            <NatijalarRoyxati talabaId={natijaTalaba.id} />
          </div>
        </div>
      )}
    </>
  );
}
