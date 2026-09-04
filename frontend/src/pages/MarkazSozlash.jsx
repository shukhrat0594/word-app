import { useEffect, useRef, useState } from "react";
import { api, apiFayluniYuklab, apiForm, mediaManzil } from "../api";
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

/** Markaz sozlamalari (2026-08-15) — avval ikkita alohida sahifa
 * ("Markaz sozlash" — logo/rang, "Ijtimoiy tarmoqlar") edi, bittaga
 * birlashtirildi + Backup bo'limi qo'shildi. Faqat OWNER ko'radi
 * (Layout.jsx). Backup — faqat baza (dumpdata/loaddata), R2 fayllarga
 * tegilmaydi (ikkala server bir xil R2 bucket'ga ulangan, fayl
 * manzillari baza orqali avtomatik to'g'ri ishlaydi). */
export default function MarkazSozlash() {
  const { t } = useI18n();
  const { yangila } = useProfil();
  const [markaz, setMarkaz] = useState(null);
  const [nom, setNom] = useState("");
  const [rang, setRang] = useState("#FFD400");
  const [logoFayl, setLogoFayl] = useState(null);
  const [ijtimoiy, setIjtimoiy] = useState({});
  const [xabar, setXabar] = useState("");
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  const [backupBand, setBackupBand] = useState(false);
  const [backupXato, setBackupXato] = useState("");
  const [backupXabar, setBackupXabar] = useState("");
  const [tanlanganFayl, setTanlanganFayl] = useState("");
  const tiklashFaylRef = useRef(null);

  function faylniTozala() {
    if (tiklashFaylRef.current) tiklashFaylRef.current.value = "";
    setTanlanganFayl("");
    setBackupXato("");
    setBackupXabar("");
  }

  // 2026-08-15: Railway ko'chirish davrida eski (Render) saytga adashib
  // kirishning oldini olish uchun — yoqilsa OWNER'dan boshqa hech kim
  // kira olmaydi (backend: `accounts.views.SaytHolatiView`/`XodimLoginView`).
  // Avtomatik kunlik zaxira (2026-09-03) — sozlamalar `/api/markaz-sozlama/`
  // dan keladi, ro'yxat esa `/api/zaxiralar/` dan.
  const [zaxiraAvtomatik, setZaxiraAvtomatik] = useState(false);
  const [zaxiraVaqti, setZaxiraVaqti] = useState("03:00");
  const [zaxiraKun, setZaxiraKun] = useState(7);
  const [zaxiralar, setZaxiralar] = useState([]);
  const [zaxiraBand, setZaxiraBand] = useState(false);
  const [zaxiraXato, setZaxiraXato] = useState("");
  const [zaxiraXabar, setZaxiraXabar] = useState("");

  const [kirishCheklangan, setKirishCheklangan] = useState(false);
  const [aktivFoydalanuvchilar, setAktivFoydalanuvchilar] = useState(0);
  const [cheklovBand, setCheklovBand] = useState(false);
  const [cheklovXato, setCheklovXato] = useState("");

  useEffect(() => {
    api("/api/markaz-sozlama/").then((m) => {
      setNom(m.name || "");
      setMarkaz(m);
      setRang(m.brend_rang);
      setIjtimoiy(m.ijtimoiy || {});
      setZaxiraAvtomatik(!!m.zaxira_avtomatik);
      setZaxiraVaqti(m.zaxira_vaqti || "03:00");
      setZaxiraKun(m.zaxira_saqlash_kuni ?? 7);
    }).catch(() => {});
    saytHolatiniYukla();
    zaxiralarniYukla();
  }, []);

  function saytHolatiniYukla() {
    return api("/api/sayt-holati/")
      .then((r) => {
        setKirishCheklangan(r.kirish_cheklangan);
        setAktivFoydalanuvchilar(r.aktiv_foydalanuvchilar || 0);
      })
      .catch(() => {});
  }

  async function kirishCheklovniOzgartir(yangiQiymat) {
    // 2026-08-15 talabi: yoqishdan oldin — hozir tizimda ishlayotgan
    // foydalanuvchilar bo'lsa ogohlantirish (ular DARHOL chiqarib
    // yuboriladi, chunki cheklov har so'rovda tekshiriladi).
    if (yangiQiymat) {
      const holat = await api("/api/sayt-holati/").catch(() => null);
      const soni = holat?.aktiv_foydalanuvchilar ?? aktivFoydalanuvchilar;
      setAktivFoydalanuvchilar(soni);
      const savol = soni > 0
        ? `${t("aktiv_foydalanuvchilar_ogoh").replace("{n}", soni)}\n\n${t("kirishni_cheklash_tasdiq")}`
        : t("kirishni_cheklash_tasdiq");
      if (!window.confirm(savol)) return;
    }

    setCheklovXato("");
    setCheklovBand(true);
    try {
      const r = await api("/api/sayt-holati/", {
        method: "PATCH",
        body: { kirish_cheklangan: yangiQiymat },
      });
      setKirishCheklangan(r.kirish_cheklangan);
      await saytHolatiniYukla();
    } catch (e) {
      setCheklovXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setCheklovBand(false);
    }
  }

  function zaxiralarniYukla() {
    return api("/api/zaxiralar/").then(setZaxiralar).catch(() => {});
  }

  /** Zaxira sozlamalarini saqlaydi. Alohida (umumiy "Saqlash" emas) —
   * shunda logo/ijtimoiy havolalar qayta yuborilmaydi va bu bo'lim
   * mustaqil ishlaydi. */
  async function zaxiraSozlamaSaqla() {
    setZaxiraXato("");
    setZaxiraXabar("");
    setZaxiraBand(true);
    try {
      const fd = new FormData();
      fd.append("zaxira_avtomatik", zaxiraAvtomatik ? "1" : "0");
      fd.append("zaxira_vaqti", zaxiraVaqti);
      fd.append("zaxira_saqlash_kuni", String(zaxiraKun));
      const m = await apiForm("/api/markaz-sozlama/", { method: "PATCH", formData: fd });
      setZaxiraAvtomatik(!!m.zaxira_avtomatik);
      setZaxiraVaqti(m.zaxira_vaqti || "03:00");
      setZaxiraKun(m.zaxira_saqlash_kuni ?? 7);
      setZaxiraXabar(t("saqlandi"));
    } catch (e) {
      setZaxiraXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setZaxiraBand(false);
    }
  }

  async function zaxiraHozirOl() {
    setZaxiraXato("");
    setZaxiraXabar("");
    setZaxiraBand(true);
    try {
      await api("/api/zaxiralar/", { method: "POST", body: {} });
      await zaxiralarniYukla();
      setZaxiraXabar(t("zaxira_olindi"));
    } catch (e) {
      setZaxiraXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setZaxiraBand(false);
    }
  }

  async function zaxiraYuklabOl(id) {
    setZaxiraXato("");
    setZaxiraBand(true);
    try {
      await apiFayluniYuklab(`/api/zaxiralar/${id}/yuklab-olish/`);
      // Yuklab olingani serverda belgilandi — ro'yxatni va tepadagi
      // tasmani yangilash uchun qayta o'qiymiz.
      await zaxiralarniYukla();
      if (yangila) yangila();
    } catch (e) {
      setZaxiraXato(e.data?.detail || e.message || t("xato_yuz_berdi"));
    } finally {
      setZaxiraBand(false);
    }
  }

  async function saqla() {
    setXato("");
    setXabar("");
    setBand(true);
    try {
      const fd = new FormData();
      fd.append("name", nom.trim());
      fd.append("brend_rang", rang);
      if (logoFayl) fd.append("logo", logoFayl);
      TARMOQLAR.forEach(({ kalit }) => fd.append(kalit, ijtimoiy[kalit] || ""));
      const m = await apiForm("/api/markaz-sozlama/", { method: "PATCH", formData: fd });
      setMarkaz(m);
      setNom(m.name || "");
      setLogoFayl(null);
      setIjtimoiy(m.ijtimoiy || {});
      setXabar(t("saqlandi"));
      // Pastki panel (ijtimoiy havolalar) darhol yangilanishi uchun.
      if (yangila) yangila();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  async function backupYuklabOl() {
    setBackupXato("");
    setBackupXabar("");
    setBackupBand(true);
    try {
      await apiFayluniYuklab("/api/backup/yuklab-olish/");
      setBackupXabar(t("backup_yuklandi"));
    } catch (e) {
      setBackupXato(e.message || t("xato_yuz_berdi"));
    } finally {
      setBackupBand(false);
    }
  }

  async function backupdanTiklash() {
    const fayl = tiklashFaylRef.current?.files?.[0];
    if (!fayl) {
      setBackupXato(t("backup_fayl_tanlanmagan"));
      return;
    }
    if (!window.confirm(t("backup_tiklash_tasdiq"))) return;

    setBackupXato("");
    setBackupXabar("");
    setBackupBand(true);
    try {
      const fd = new FormData();
      fd.append("fayl", fayl);
      fd.append("tasdiqlash", "HA");
      const res = await apiForm("/api/backup/tiklash/", { method: "POST", formData: fd });
      setBackupXabar(res.detail || t("backup_tiklandi"));
      if (tiklashFaylRef.current) tiklashFaylRef.current.value = "";
      setTanlanganFayl("");
    } catch (e) {
      setBackupXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setBackupBand(false);
    }
  }

  if (!markaz) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <div style={{ display: "grid", gap: 20, maxWidth: 560 }}>
      <div className="karta">
        <h3>{markaz.name}</h3>
        <p className="izoh">{t("markaz_sozlama_izoh")}</p>

        <div style={{ display: "grid", gap: 16, marginTop: 4 }}>
          {/* 2026-08-18, foydalanuvchi talabi: markaz nomi shu yerdan
              o'zgartiriladi — u brauzer tab sarlavhasida, tepa panelda,
              profilda va login ekranida ko'rinadi. */}
          <div>
            <div className="izoh" style={{ marginBottom: 6 }}>{t("markaz_nomi")}</div>
            <input
              type="text"
              value={nom}
              maxLength={200}
              onChange={(e) => setNom(e.target.value)}
              style={{ width: "100%" }}
            />
          </div>

          <div>
            <div className="izoh" style={{ marginBottom: 6 }}>{t("logo")}</div>
            {markaz.logo_url && (
              <img
                src={mediaManzil(markaz.logo_url)}
                alt={markaz.name}
                style={{ height: 48, marginBottom: 8, display: "block" }}
              />
            )}
            <input type="file" accept="image/*" onChange={(e) => setLogoFayl(e.target.files[0])} />
          </div>

          <div>
            <div className="izoh" style={{ marginBottom: 6 }}>{t("brend_rangi")}</div>
            <input
              type="color"
              value={rang}
              onChange={(e) => setRang(e.target.value)}
              style={{ width: 60, height: 40, padding: 2 }}
            />
          </div>

          <div>
            <div className="izoh" style={{ marginBottom: 6 }}>{t("nav_ijtimoiy")}</div>
            <div style={{ display: "grid", gap: 10 }}>
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
                    value={ijtimoiy[kalit] || ""}
                    onChange={(e) => setIjtimoiy({ ...ijtimoiy, [kalit]: e.target.value })}
                  />
                </div>
              ))}
            </div>
          </div>

          {xato && <div className="xato-xabar">{xato}</div>}
          {xabar && <div className="izoh">{xabar}</div>}
          <button className="tugma" onClick={saqla} disabled={band}>
            {t("saqlash")}
          </button>
        </div>
      </div>

      <div className="karta">
        <h3>{t("kirish_cheklovi_sarlavha")}</h3>
        <p className="izoh">{t("kirish_cheklovi_izoh")}</p>

        <div style={{ display: "grid", gap: 10, marginTop: 4 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span className={`chip ${kirishCheklangan ? "tugadi" : "bor"}`}>
              {kirishCheklangan ? t("kirish_cheklangan_holat") : t("kirish_ochiq_holat")}
            </span>
            {!kirishCheklangan && aktivFoydalanuvchilar > 0 && (
              <span className="izoh">
                {t("aktiv_foydalanuvchilar_ogoh").replace("{n}", aktivFoydalanuvchilar)}
              </span>
            )}
          </div>
          {kirishCheklangan ? (
            <button
              className="tugma"
              onClick={() => kirishCheklovniOzgartir(false)}
              disabled={cheklovBand}
              style={{ width: "fit-content" }}
            >
              {t("cheklovni_olib_tashlash")}
            </button>
          ) : (
            <button
              className="tugma xavfli"
              onClick={() => kirishCheklovniOzgartir(true)}
              disabled={cheklovBand}
              style={{ width: "fit-content" }}
            >
              {t("kirishni_cheklash")}
            </button>
          )}
          {cheklovXato && <div className="xato-xabar">{cheklovXato}</div>}
        </div>
      </div>

      {/* Avtomatik kunlik zaxira (2026-09-03, foydalanuvchi talabi) —
          faqat BAZA, R2'ga saqlanadi. Media uchun alohida "To'liq
          zaxira" rejada. */}
      <div className="karta">
        <h3>{t("zaxira_sarlavha")}</h3>
        <p className="izoh">{t("zaxira_izoh")}</p>

        <div style={{ display: "grid", gap: 12, marginTop: 4 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input
              type="checkbox"
              checked={zaxiraAvtomatik}
              onChange={(e) => setZaxiraAvtomatik(e.target.checked)}
              disabled={zaxiraBand}
            />
            {t("zaxira_yoqish")}
          </label>

          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
            <label style={{ display: "grid", gap: 4 }}>
              <span className="izoh">{t("zaxira_vaqti")}</span>
              <input
                type="time"
                value={zaxiraVaqti}
                onChange={(e) => setZaxiraVaqti(e.target.value)}
                disabled={zaxiraBand || !zaxiraAvtomatik}
                style={{ maxWidth: 120 }}
              />
            </label>
            <label style={{ display: "grid", gap: 4 }}>
              <span className="izoh">{t("zaxira_saqlash_kuni")}</span>
              <input
                type="number"
                min="1"
                max="365"
                value={zaxiraKun}
                onChange={(e) => setZaxiraKun(e.target.value)}
                disabled={zaxiraBand}
                style={{ maxWidth: 100 }}
              />
            </label>
            <button className="tugma" onClick={zaxiraSozlamaSaqla} disabled={zaxiraBand}>
              {t("saqlash")}
            </button>
            <button className="tugma ikkinchi" onClick={zaxiraHozirOl} disabled={zaxiraBand}>
              {t("zaxira_hozir_ol")}
            </button>
          </div>

          <div className="izoh">{t("zaxira_muddat_izoh")}</div>

          {zaxiralar.length > 0 && (
            <div style={{ display: "grid", gap: 6 }}>
              {zaxiralar.map((z) => (
                <div
                  key={z.id}
                  style={{
                    display: "flex", alignItems: "center", gap: 10,
                    flexWrap: "wrap", borderTop: "1px solid var(--chiziq)", paddingTop: 6,
                  }}
                >
                  <strong style={{ minWidth: 96 }}>{z.sana}</strong>
                  <span className="izoh">
                    {z.turi === "qolda" ? t("zaxira_qolda") : t("zaxira_avtomatik_belgi")}
                  </span>
                  <span className="izoh">{(z.hajm / 1e6).toFixed(2)} MB</span>
                  {z.xato ? (
                    <span className="xato-xabar">{z.xato}</span>
                  ) : (
                    <>
                      <span className="izoh">
                        {z.yuklab_olindi ? `✓ ${t("zaxira_yuklab_olingan")}` : `⚠ ${t("zaxira_yuklanmagan")}`}
                      </span>
                      <button
                        type="button"
                        className="tugma ikkinchi kichik"
                        onClick={() => zaxiraYuklabOl(z.id)}
                        disabled={zaxiraBand || !z.fayl_bor}
                      >
                        {t("backup_yuklab_olish")}
                      </button>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}

          {zaxiraXato && <div className="xato-xabar">{zaxiraXato}</div>}
          {zaxiraXabar && <div className="izoh">{zaxiraXabar}</div>}
        </div>
      </div>

      <div className="karta">
        <h3>{t("backup_sarlavha")}</h3>
        <p className="izoh">{t("backup_izoh")}</p>

        <div style={{ display: "grid", gap: 14, marginTop: 4 }}>
          <div>
            <button className="tugma" onClick={backupYuklabOl} disabled={backupBand}>
              {t("backup_yuklab_olish")}
            </button>
          </div>

          <div>
            <div className="izoh" style={{ marginBottom: 6 }}>{t("backup_tiklash")}</div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <input
                type="file"
                accept=".zip"
                ref={tiklashFaylRef}
                onChange={(e) => setTanlanganFayl(e.target.files?.[0]?.name || "")}
              />
              {tanlanganFayl && (
                <button
                  type="button"
                  className="tugma ikkinchi"
                  onClick={faylniTozala}
                  disabled={backupBand}
                >
                  {t("faylni_ochirish")}
                </button>
              )}
              <button className="tugma xavfli" onClick={backupdanTiklash} disabled={backupBand}>
                {t("backup_tiklash")}
              </button>
            </div>
          </div>

          {backupXato && <div className="xato-xabar">{backupXato}</div>}
          {backupXabar && <div className="izoh">{backupXabar}</div>}
        </div>
      </div>
    </div>
  );
}
