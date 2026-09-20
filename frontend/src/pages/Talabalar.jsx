import { useEffect, useMemo, useState } from "react";
import { api, apiForm } from "../api";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";
import NatijalarRoyxati from "../components/NatijalarRoyxati";
import { PanelTanlovi, ProfilRasmi, QurilmaTiklashTugmasi, QurilmaLimitiBoshqaruv } from "./Foydalanuvchilar";

// 2026-09-17 (admin talabi): yaratishda qo'shimcha ma'lumot ham kiritiladi.
// Kiritilgan maydonlar talabaga qulflanadi (`admin_maydonlari`).
const BOSH_FORMA = {
  ism: "", login: "", parol: "",
  telefon: "", ota_ona_telefon: "", ota_ona_ismi: "", tugilgan_sana: "", manba: "", izoh: "",
  // 2026-09-20 (admin talabi): yaratishda darhol guruhga qo'shish mumkin —
  // "Talaba guruhga biriktirilmaydi" degan alohida qadamga hojat qolmaydi.
  guruh_id: "",
};

// SoffCRM'dagi "Manba" variantlari (2026-09-20, admin skrinshoti). Erkin
// matn ham qoladi (<datalist>) — ro'yxatda yo'q manba kiritilsa ham
// ishlaydi, keyingi safar taklif etiladi (mavjud talabalar manbasidan).
const MANBA_KALITLARI = [
  "manba_instagram", "manba_telegram", "manba_tavsiya", "manba_oldin_oqigan",
  "manba_banner", "manba_flayer", "manba_chatgpt", "manba_google",
];

// Admin/owner tahrirlaydigan maydonlar — TalabaKartasi formasi.
const TAHRIR_MAYDONLARI = ["ism", "telefon", "ota_ona_telefon", "ota_ona_ismi", "tugilgan_sana", "manba", "izoh"];

/** Talaba kartasi (2026-09-17, admin talabi): ismga bosilganda natijalar
 *  emas, to'liq ma'lumot — telefon, ota-ona, tug'ilgan sana, manba, izoh,
 *  guruhi. Admin/owner shu yerda tahrirlaydi (`PATCH /api/talabalar/<id>/`).
 *  To'lov tarixi CRM'da — havola bilan (LMS CRM kodini import qilmaydi). */
function TalabaKartasi({ talaba, boshqaruvMi, t, onYopish, onSaqlandi, onNatijalar }) {
  const [forma, setForma] = useState(() =>
    Object.fromEntries(TAHRIR_MAYDONLARI.map((m) => [m, talaba[m] || ""]))
  );
  const [band, setBand] = useState(false);
  const [xato, setXato] = useState("");
  const [xabar, setXabar] = useState("");

  async function saqla() {
    setXato("");
    setXabar("");
    setBand(true);
    try {
      const yangi = await api(`/api/talabalar/${talaba.id}/`, { method: "PATCH", body: forma });
      setXabar(t("talaba_saqlandi"));
      onSaqlandi(yangi);
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  const maydon = (kalit, tarjima, turi = "text", royxatId = null) => (
    <label key={kalit}>
      <span className="izoh">{tarjima}</span>
      {boshqaruvMi ? (
        <input
          type={turi}
          value={forma[kalit]}
          onChange={(e) => setForma((f) => ({ ...f, [kalit]: e.target.value }))}
          list={royxatId || undefined}
        />
      ) : (
        <div>{talaba[kalit] || "—"}</div>
      )}
    </label>
  );

  return (
    <div className="blok-yuklash-qoplama" onClick={onYopish}>
      <div className="blok-tasdiq-karta" style={{ maxWidth: 560 }} onClick={(e) => e.stopPropagation()}>
        <div className="blok-tasdiq-sarlavha-qator">
          <strong>{talaba.ism}</strong>
          <span style={{ display: "flex", gap: 8 }}>
            <button className="tugma ikkinchi kichik" onClick={onNatijalar}>{t("natijalar_tugma")}</button>
            {import.meta.env.VITE_CRM === "1" && boshqaruvMi && (
              <a className="tugma ikkinchi kichik" href={`/crm/talabalar?talaba=${talaba.id}`}>
                💰 {t("crmda_ochish")}
              </a>
            )}
            <button className="tugma ikkinchi kichik" onClick={onYopish}>{t("yopish")}</button>
          </span>
        </div>
        <div style={{ display: "grid", gap: 12, marginTop: 12 }}>
          <div>
            <span className="izoh">{t("login")}: </span>{talaba.username}
          </div>
          <div>
            <span className="izoh">{t("talaba_guruhi")}: </span>
            {talaba.guruhlar?.length ? talaba.guruhlar.map((g) => g.nomi).join(", ") : "—"}
          </div>
          {maydon("ism", t("ism"))}
          {maydon("telefon", t("profil_telefon"))}
          {maydon("ota_ona_telefon", t("profil_ota_ona_telefon"))}
          {maydon("ota_ona_ismi", t("profil_ota_ona_ismi"))}
          {maydon("tugilgan_sana", t("profil_tugilgan_sana"), "date")}
          {maydon("manba", t("talaba_manba"), "text", "manba-variantlari-karta")}
          <datalist id="manba-variantlari-karta">
            {MANBA_KALITLARI.map((k) => (
              <option key={k} value={t(k)} />
            ))}
          </datalist>
          {maydon("izoh", t("talaba_izoh"))}
          {xato && <div className="xato-xabar">{xato}</div>}
          {xabar && <div className="izoh">{xabar}</div>}
          {boshqaruvMi && (
            <button className="tugma" onClick={saqla} disabled={band}>
              {band ? t("yuklanmoqda") : t("saqlash")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

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
  // 2026-09-17: ismga bosilganda endi talaba KARTASI ochiladi (ma'lumot +
  // tahrirlash), natijalar undagi alohida tugma orqali.
  const [kartaTalaba, setKartaTalaba] = useState(null);
  // 2026-09-20 (admin talabi): "Yangi talaba" formasida darhol guruhga
  // qo'shish uchun guruhlar ro'yxati kerak.
  const [guruhlar, setGuruhlar] = useState([]);

  function yukla(arxiv = arxivKorish) {
    api(`/api/talabalar/${arxiv ? "?arxiv=1" : ""}`).then(setTalabalar).catch(() => {});
  }

  useEffect(() => {
    yukla(arxivKorish);
  }, [arxivKorish]);

  useEffect(() => {
    if (boshqaruvMi) {
      api("/api/guruhlar/").then(setGuruhlar).catch(() => setGuruhlar([]));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [boshqaruvMi]);

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

  /** "Qurilma limiti" o'zgartirish — faqat owner. */
  async function qurilmaLimitOzgartir(id, limit) {
    setXato("");
    try {
      await api(`/api/foydalanuvchilar/${id}/qurilma-limit/`, { method: "POST", body: { limit } });
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
      // 2026-09-20 (admin talabi): guruh tanlangan bo'lsa DARHOL qo'shiladi
      // — talaba yaratish bilan bitta qadam. `talaba_idlar` guruhning
      // BUTUN a'zolik ro'yxatini almashtiradi (`_azolarni_saqla`), shuning
      // uchun mavjudlarni o'qib, ustiga yangi talabani qo'shamiz.
      if (forma.guruh_id) {
        try {
          const guruh = await api(`/api/guruhlar/${forma.guruh_id}/`);
          const idlar = [...guruh.talabalar.map((tl) => tl.id), yangi.id];
          await api(`/api/guruhlar/${forma.guruh_id}/`, {
            method: "PATCH",
            body: { talaba_idlar: idlar },
          });
        } catch {
          // Talaba baribir yaratildi — guruhga qo'shish muvaffaqiyatsiz
          // bo'lsa ham xabar shuni aytadi, admin "Guruhlar" bo'limidan
          // qo'lda qo'sha oladi (eski yo'l hamon ishlaydi).
          setXabar(`${t("talaba_qoshildi")}: ${yangi.ism} — ${yangi.username} (${t("guruhga_qoshish_xato")})`);
          setForma(BOSH_FORMA);
          yukla();
          return;
        }
      }
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

  // 2026-08-25, foydalanuvchi talabi: ro'yxat guruh bo'yicha "papka"larga
  // bo'linadi — adashib ketmaslik uchun bittalab flat ro'yxat o'rniga.
  // Talaba bir nechta guruhga a'zo bo'lsa — har biriga chiqadi (`Guruh.
  // talabalar` M2M). Guruhi yo'q talabalar "Guruhsiz" bo'limida, oxirida.
  const guruhlangan = useMemo(() => {
    if (!talabalar) return [];
    const xarita = new Map();
    const guruhsiz = [];
    for (const tl of talabalar) {
      if (!tl.guruhlar || tl.guruhlar.length === 0) {
        guruhsiz.push(tl);
        continue;
      }
      for (const g of tl.guruhlar) {
        if (!xarita.has(g.id)) xarita.set(g.id, { id: g.id, nomi: g.nomi, talabalar: [] });
        xarita.get(g.id).talabalar.push(tl);
      }
    }
    const royxat = [...xarita.values()].sort((a, b) => a.nomi.localeCompare(b.nomi));
    if (guruhsiz.length > 0) royxat.push({ id: "guruhsiz", nomi: t("guruhsiz"), talabalar: guruhsiz });
    return royxat;
  }, [talabalar, t]);

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
            <input
              style={{ maxWidth: 160 }}
              placeholder={t("profil_telefon")}
              value={forma.telefon}
              onChange={(e) => setForma({ ...forma, telefon: e.target.value })}
            />
            <input
              style={{ maxWidth: 160 }}
              placeholder={t("profil_ota_ona_telefon")}
              value={forma.ota_ona_telefon}
              onChange={(e) => setForma({ ...forma, ota_ona_telefon: e.target.value })}
            />
            <input
              style={{ maxWidth: 160 }}
              placeholder={t("profil_ota_ona_ismi")}
              value={forma.ota_ona_ismi}
              onChange={(e) => setForma({ ...forma, ota_ona_ismi: e.target.value })}
            />
            <input
              style={{ maxWidth: 160 }}
              type="date"
              title={t("profil_tugilgan_sana")}
              value={forma.tugilgan_sana}
              onChange={(e) => setForma({ ...forma, tugilgan_sana: e.target.value })}
            />
            <input
              style={{ maxWidth: 160 }}
              placeholder={t("talaba_manba")}
              value={forma.manba}
              onChange={(e) => setForma({ ...forma, manba: e.target.value })}
              list="manba-variantlari-yangi"
            />
            <datalist id="manba-variantlari-yangi">
              {MANBA_KALITLARI.map((k) => (
                <option key={k} value={t(k)} />
              ))}
            </datalist>
            <select
              style={{ maxWidth: 220 }}
              value={forma.guruh_id}
              onChange={(e) => setForma({ ...forma, guruh_id: e.target.value })}
              title={t("yangi_talaba_guruhi")}
            >
              <option value="">{t("guruh_tanlanmagan")}</option>
              {guruhlar.map((g) => (
                <option key={g.id} value={g.id}>{g.name}</option>
              ))}
            </select>
            <input
              style={{ maxWidth: 220 }}
              placeholder={t("talaba_izoh")}
              value={forma.izoh}
              onChange={(e) => setForma({ ...forma, izoh: e.target.value })}
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
        {guruhlangan.map((g) => (
          <details className="guruh-papka" key={g.id} open>
            <summary className="guruh-papka-sarlavha">
              {g.nomi} <span className="izoh">({g.talabalar.length})</span>
            </summary>
            {g.talabalar.map((tl) => (
              <div className="tarix-el" key={tl.id}>
                <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  {/* Rasm ALOHIDA turadi — ismga bosilganda natijalar oynasi
                      ochiladi, rasmga bosilganda esa o'chirish oynasi; ikkisi
                      bir joyda bo'lsa bosish bir-biriga tushib ketardi. */}
                  <ProfilRasmi user={tl} ochir={boshqaruvMi ? rasmOchir : undefined} t={t} />
                  <span
                    style={{ display: "flex", gap: 8, cursor: "pointer", alignItems: "center" }}
                    onClick={() => setKartaTalaba(tl)}
                    title={t("talaba_malumoti")}
                  >
                    <span>{tl.ism}</span>
                    <span className="izoh">{tl.username}</span>
                  </span>
                </span>
                {boshqaruvMi && (
                  <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <PanelTanlovi user={tl} saqlash={panellarSaqla} t={t} />
                    <QurilmaTiklashTugmasi user={tl} tiklash={qurilmaTiklash} t={t} />
                    {profil?.is_owner && (
                      <QurilmaLimitiBoshqaruv user={tl} ozgartir={qurilmaLimitOzgartir} t={t} />
                    )}
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
          </details>
        ))}
      </div>

      {kartaTalaba && (
        <TalabaKartasi
          talaba={kartaTalaba}
          boshqaruvMi={boshqaruvMi}
          t={t}
          onYopish={() => setKartaTalaba(null)}
          onNatijalar={() => { setNatijaTalaba(kartaTalaba); setKartaTalaba(null); }}
          onSaqlandi={(yangi) => {
            setKartaTalaba((k) => ({ ...k, ...yangi }));
            setTalabalar((r) => r.map((x) => (x.id === yangi.id ? { ...x, ...yangi } : x)));
          }}
        />
      )}

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
