import { useEffect, useState } from "react";
import { api } from "../api";
import Avatar from "../components/Avatar";
import { panelTanloviOl } from "../components/Layout";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";

const ROLLAR = ["owner", "admin", "teacher", "student", "parent", "oddiy"];

/** Ota-onaga farzand(lar) biriktirish (2026-08-09). Bitta ota-onada bir
 * nechta farzand bo'lishi mumkin, lekin bitta bola FAQAT bitta
 * ota-onaga — shuning uchun boshqa ota-onaga biriktirilgan talaba
 * ro'yxatda ko'rinadi, lekin BELGILAB BO'LMAYDI (backend ham 400
 * qaytaradi, bu faqat oldindan tushuntirish). */
function FarzandTanlovi({ user, talabalar, saqlash, t }) {
  const [ochiq, setOchiq] = useState(false);
  const joriy = (user.farzandlar || []).map((f) => f.id);

  function boshqar(id, belgilanganmi) {
    saqlash(user.id, belgilanganmi ? joriy.filter((x) => x !== id) : [...joriy, id]);
  }

  return (
    <span style={{ position: "relative" }}>
      <button type="button" className="tugma ikkinchi kichik" onClick={() => setOchiq((v) => !v)}>
        👪 {t("farzandlar_biriktirish")}{joriy.length ? ` (${joriy.length})` : ""}
      </button>
      {ochiq && (
        <div
          style={{
            position: "absolute", zIndex: 25, top: "100%", right: 0, marginTop: 4,
            background: "var(--sirt)", border: "1px solid var(--chiziq)", borderRadius: 8,
            padding: 10, display: "grid", gap: 4, minWidth: 260, maxHeight: 300,
            overflowY: "auto", boxShadow: "var(--soya)",
          }}
        >
          <div className="izoh" style={{ marginBottom: 4 }}>{t("farzand_tanlash_izoh")}</div>
          {talabalar.length === 0 && <span className="izoh">{t("talaba_yoq")}</span>}
          {talabalar.map((s) => {
            const belgilanganmi = joriy.includes(s.id);
            // Boshqa ota-onada band — bu yerda belgilab bo'lmaydi.
            const band = !belgilanganmi && s.ota_ona_id != null;
            return (
              <label
                key={s.id}
                style={{ display: "flex", alignItems: "center", gap: 6, opacity: band ? 0.45 : 1 }}
                title={band ? t("farzand_tanlash_izoh") : ""}
              >
                <input
                  type="checkbox"
                  checked={belgilanganmi}
                  disabled={band}
                  onChange={() => boshqar(s.id, belgilanganmi)}
                />
                {s.ism}
              </label>
            );
          })}
        </div>
      )}
    </span>
  );
}

/** Profil rasmi — kichik avatar, ustiga bosilganda O'CHIRISH oynasi
 * (2026-08-09). `Talabalar` va `Xodimlar` sahifalarida ham ishlatiladi
 * (`PanelTanlovi` kabi shu fayldan eksport qilinadi).
 *
 * Avval bu yerda YUKLASH tugmasi bor edi (owner/admin boshqa odamga rasm
 * qo'yardi) — foydalanuvchi qarori bilan olib tashlandi: rasmni faqat
 * egasi qo'yadi. Lekin MODERATSIYA qoldi: nomaqbul rasm qo'yilsa
 * owner/admin uni olib tashlashi kerak. Shu sababli sabab MAJBURIY —
 * u egasiga "Ogohlantirish" bildirishnomasi bo'lib boradi (backend:
 * `FoydalanuvchiRasmView.delete`), aks holda rasm jimgina yo'qolib,
 * odam nima uchun ekanini bilmasdi.
 *
 * `ochir` BERILMASA rasm faqat ko'rsatiladi — "Talabalar" sahifasini
 * o'qituvchi ham ko'radi, unda esa o'chirish huquqi YO'Q (backend 403
 * qaytaradi), ya'ni tugma ko'rsatilsa ishlamaydigan tugma bo'lardi. */
export function ProfilRasmi({ user, ochir, t }) {
  const [ochiq, setOchiq] = useState(false);
  const [izoh, setIzoh] = useState("");
  const [band, setBand] = useState(false);

  if (!user.rasm_url || !ochir) {
    return <Avatar rasmUrl={user.rasm_url} olcham={34} sarlavha={user.ism} />;
  }

  async function tasdiqla() {
    if (!izoh.trim()) return;
    setBand(true);
    try {
      await ochir(user.id, izoh.trim());
      setOchiq(false);
      setIzoh("");
    } finally {
      setBand(false);
    }
  }

  return (
    <span style={{ position: "relative", flexShrink: 0 }}>
      <button
        type="button"
        onClick={() => setOchiq((v) => !v)}
        title={t("rasmni_ochirish")}
        style={{ padding: 0, border: "none", background: "none", cursor: "pointer", display: "block" }}
      >
        <Avatar rasmUrl={user.rasm_url} olcham={34} sarlavha={user.ism} />
      </button>
      {ochiq && (
        <div
          style={{
            position: "absolute", top: "100%", left: 0, marginTop: 6, width: 280,
            background: "var(--sirt)", border: "1px solid var(--chiziq)",
            borderRadius: 10, padding: 10, zIndex: 1200,
            boxShadow: "0 6px 24px rgba(0,0,0,0.25)",
          }}
        >
          <strong style={{ display: "block", marginBottom: 4 }}>{t("rasm_ochirish_sababi")}</strong>
          <div className="izoh" style={{ marginBottom: 6 }}>{t("rasm_ochirish_sababi_izoh")}</div>
          <textarea
            rows={3}
            value={izoh}
            onChange={(e) => setIzoh(e.target.value)}
            style={{ width: "100%", marginBottom: 6 }}
          />
          <div style={{ display: "flex", gap: 6 }}>
            <button
              className="tugma kichik"
              onClick={tasdiqla}
              disabled={band || !izoh.trim()}
              title={izoh.trim() ? undefined : t("rasm_ochirish_sababi_shart")}
            >
              {t("rasmni_ochirish")}
            </button>
            <button
              className="tugma ikkinchi kichik"
              onClick={() => { setOchiq(false); setIzoh(""); }}
              disabled={band}
            >
              {t("kurs_blok_bekor_qilish")}
            </button>
          </div>
        </div>
      )}
    </span>
  );
}

/** "Qurilmani tiklash" (2026-08-12) — owner/admin uchun, `ProfilRasmi`
 * bilan bir xil naqsh (majburiy sabab, kichik popup). Faqat
 * `user.qurilma_bormi` bo'lsa va owner bo'lmasa ko'rinadi (owner'da
 * cheklov umuman yo'q, tugma ko'rsatishning ma'nosi yo'q). */
export function QurilmaTiklashTugmasi({ user, tiklash, t }) {
  const [ochiq, setOchiq] = useState(false);
  const [izoh, setIzoh] = useState("");
  const [band, setBand] = useState(false);

  if (!tiklash || user.is_owner || !user.qurilma_bormi) return null;

  async function tasdiqla() {
    if (!izoh.trim()) return;
    setBand(true);
    try {
      await tiklash(user.id, izoh.trim());
      setOchiq(false);
      setIzoh("");
    } finally {
      setBand(false);
    }
  }

  return (
    <span style={{ position: "relative" }}>
      <button type="button" className="tugma ikkinchi kichik" onClick={() => setOchiq((v) => !v)}>
        {t("qurilma_tiklash")}
      </button>
      {ochiq && (
        <div
          style={{
            position: "absolute", top: "100%", left: 0, marginTop: 6, width: 280,
            background: "var(--sirt)", border: "1px solid var(--chiziq)",
            borderRadius: 10, padding: 10, zIndex: 1200,
            boxShadow: "0 6px 24px rgba(0,0,0,0.25)",
          }}
        >
          <strong style={{ display: "block", marginBottom: 4 }}>{t("qurilma_tiklash")}</strong>
          <div className="izoh" style={{ marginBottom: 6 }}>{t("qurilma_tiklash_izoh_soralmoqda")}</div>
          <textarea
            rows={3}
            value={izoh}
            onChange={(e) => setIzoh(e.target.value)}
            style={{ width: "100%", marginBottom: 6 }}
          />
          <div style={{ display: "flex", gap: 6 }}>
            <button
              className="tugma kichik"
              onClick={tasdiqla}
              disabled={band || !izoh.trim()}
              title={izoh.trim() ? undefined : t("rasm_ochirish_sababi_shart")}
            >
              {t("qurilma_tiklash")}
            </button>
            <button
              className="tugma ikkinchi kichik"
              onClick={() => { setOchiq(false); setIzoh(""); }}
              disabled={band}
            >
              {t("kurs_blok_bekor_qilish")}
            </button>
          </div>
        </div>
      )}
    </span>
  );
}

/** "Qurilma limiti" boshqaruvi (2026-08-13, foydalanuvchi talabi) —
 * FAQAT owner uchun (adminga keyinchalik berilishi mumkin, hozircha
 * yo'q). Standart 1 — necha ta qurilmadan bir vaqtda kirish mumkinligi.
 * Limit oshirilsa, bloklangan foydalanuvchi HECH QANDAY qo'shimcha
 * harakatsiz, keyingi login urinishida avtomatik kiradi
 * (`_qurilma_tekshir` backend'da). */
export function QurilmaLimitiBoshqaruv({ user, ozgartir, t }) {
  const [band, setBand] = useState(false);

  if (user.is_owner || user.qurilma_limiti === undefined) return null;

  async function ozgar(yangi) {
    if (yangi < 1 || band) return;
    setBand(true);
    try {
      await ozgartir(user.id, yangi);
    } finally {
      setBand(false);
    }
  }

  return (
    <span
      style={{ display: "flex", alignItems: "center", gap: 4 }}
      title={t("qurilma_limiti_izoh")}
    >
      <span className="izoh">{t("qurilma_limiti")}:</span>
      <button
        type="button"
        className="tugma ikkinchi kichik"
        onClick={() => ozgar(user.qurilma_limiti - 1)}
        disabled={band || user.qurilma_limiti <= 1}
      >
        −
      </button>
      <strong>{user.qurilmalar_soni ?? 0}/{user.qurilma_limiti}</strong>
      <button
        type="button"
        className="tugma ikkinchi kichik"
        onClick={() => ozgar(user.qurilma_limiti + 1)}
        disabled={band}
      >
        +
      </button>
    </span>
  );
}

/** Rolga QO'SHIMCHA "ko'rinadigan panellar" checkbox ro'yxati
 * (2026-08-05) — owner istalgan foydalanuvchi uchun, admin faqat
 * talabalar uchun ko'radi (`PatchYoli` orqali chaqiruvchi belgilaydi).
 * `null` (yoki bo'sh) = cheklovsiz (rolning HAMMA paneli ko'rinadi).
 *
 * 2026-08-09: ro'yxat endi FOYDALANUVCHI ROLIGA qarab chiqadi
 * (`panelTanloviOl`). Avval global 13 panel chiqardi — rolidan qat'i
 * nazar. Natijada masalan ota-onaga "Kurslar"ni belgilash mumkin edi,
 * lekin ta'siri YO'Q edi: menyu rol jadvali bilan kesishtiriladi, ota-ona
 * rolida esa u panel umuman yo'q. Ya'ni galochka yolg'on gapirardi.
 *
 * "Bosh sahifa" va "Profil" ro'yxatda chiqmaydi — ular har doim
 * ko'rinadi (`MAJBURIY_PANELLAR`). */
export function PanelTanlovi({ user, saqlash, t }) {
  const [ochiq, setOchiq] = useState(false);
  const joriy = user.korinadigan_panellar;
  const tanlov = panelTanloviOl(user.role, user.is_owner);

  function boshqar(yol, belgilanganmi) {
    const hozirgi = joriy && joriy.length > 0 ? joriy : tanlov.map((p) => p.yol);
    const yangi = belgilanganmi ? hozirgi.filter((y) => y !== yol) : [...hozirgi, yol];
    // Hammasi belgilangan bo'lsa `null` saqlanadi ("cheklovsiz"). Solishtirish
    // ROLNING panel soni bo'yicha — global son bo'yicha emas, aks holda
    // masalan o'qituvchida (6 panel) "hammasi" holatiga hech qachon
    // yetib bo'lmasdi va ro'yxat abadiy "cheklangan" bo'lib turardi.
    saqlash(user.id, yangi.length === tanlov.length ? null : yangi);
  }

  // Rolida sozlanadigan panel bo'lmasa (masalan ota-ona — unda faqat
  // "Bosh sahifa" bor) tugma umuman chiqmaydi: bosishdan foyda yo'q.
  if (tanlov.length === 0) return null;

  return (
    <span style={{ position: "relative" }}>
      <button type="button" className="tugma ikkinchi kichik" onClick={() => setOchiq((v) => !v)}>
        {t("panel_ruxsati")} {joriy && joriy.length > 0 ? `(${joriy.length}/${tanlov.length})` : ""}
      </button>
      {ochiq && (
        <div
          style={{
            // z-index 25: pastdagi "ijtimoiy-panel" (sticky, z-index:20)dan
            // yuqorida chiqishi kerak (2026-08-07, foydalanuvchi topgan bug
            // — dropdown ro'yxati sticky panel ostida yashirinib qolgan edi).
            position: "absolute", zIndex: 25, top: "100%", left: 0, marginTop: 4,
            background: "var(--sirt)", border: "1px solid var(--chiziq)", borderRadius: 8,
            padding: 10, display: "grid", gap: 4, minWidth: 220, boxShadow: "var(--soya)",
          }}
        >
          {tanlov.map((p) => {
            const belgilanganmi = !joriy || joriy.length === 0 || joriy.includes(p.yol);
            return (
              <label key={p.yol} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <input
                  type="checkbox"
                  checked={belgilanganmi}
                  onChange={() => boshqar(p.yol, belgilanganmi)}
                />
                {t(p.kalit)}
              </label>
            );
          })}
        </div>
      )}
    </span>
  );
}

/** "Aktiv foydalanuvchilar" — hozir ochiq seansi bor odamlar
 * (2026-09-03, foydalanuvchi talabi). Faqat owner ko'radi.
 *
 * SEANS = server tomonda amaldagi kalit. Muhim farq: bu "hozir saytda
 * turgan" degani EMAS. Shuning uchun `oxirgi_faollik` ham ko'rsatiladi —
 * seans ochiq, lekin odam uzoq ko'rinmagan bo'lsa, bu QOLIB KETGAN
 * seans va uni yopish mumkin.
 */
function AktivFoydalanuvchilar({ t }) {
  const [royxat, setRoyxat] = useState(null);
  const [band, setBand] = useState(false);
  const [xato, setXato] = useState("");

  function yukla() {
    return api("/api/aktiv-foydalanuvchilar/")
      .then(setRoyxat)
      .catch((e) => {
        // Owner bo'lmasa 403 — bo'lim shunchaki ko'rsatilmaydi.
        if (e.status !== 403) setXato(e.data?.detail || t("xato_yuz_berdi"));
        setRoyxat([]);
      });
  }

  useEffect(() => {
    yukla();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function seansniYop(q) {
    if (!window.confirm(t("seans_yopish_tasdiq"))) return;
    setXato("");
    setBand(true);
    try {
      await api(`/api/aktiv-foydalanuvchilar/${q.id}/seansni-yop/`, { method: "POST", body: {} });
      await yukla();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  /** "2 daqiqa oldin" ko'rinishidagi matn + qolib ketganini belgilash. */
  function faollikMatni(vaqt) {
    if (!vaqt) return { matn: t("seans_hech_qachon"), eski: true };
    const sekund = Math.max(0, (Date.now() - new Date(vaqt).getTime()) / 1000);
    if (sekund < 120) return { matn: t("seans_hozir"), eski: false };
    if (sekund < 3600) return { matn: `${Math.round(sekund / 60)} ${t("seans_daqiqa_oldin")}`, eski: false };
    if (sekund < 86400) return { matn: `${Math.round(sekund / 3600)} ${t("seans_soat_oldin")}`, eski: false };
    return { matn: `${Math.round(sekund / 86400)} ${t("seans_kun_oldin")}`, eski: true };
  }

  if (!royxat) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;
  if (royxat.length === 0) {
    return (
      <div className="karta">
        <h3>{t("seans_sarlavha")}</h3>
        <p className="izoh">{t("seans_yoq")}</p>
      </div>
    );
  }

  return (
    <div className="karta">
      <h3>{t("seans_sarlavha")}</h3>
      <p className="izoh">{t("seans_izoh")}</p>
      <div style={{ display: "grid", gap: 6, marginTop: 4 }}>
        {royxat.map((q) => {
          const f = faollikMatni(q.oxirgi_faollik);
          return (
            <div
              key={q.id}
              style={{
                display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap",
                borderTop: "1px solid var(--chiziq)", paddingTop: 6,
              }}
            >
              <strong style={{ minWidth: 150 }}>{q.ism}</strong>
              <span className="izoh" style={{ minWidth: 110 }}>{q.login}</span>
              <span className="izoh" style={{ minWidth: 70 }}>{t(`rol_${q.rol}`)}</span>
              <span className={f.eski ? "xato-xabar" : "izoh"} style={{ minWidth: 120 }}>
                {f.eski ? "⚠ " : ""}{f.matn}
              </span>
              <span className="izoh">
                {q.seans_soni} {t("seans_soni")}
              </span>
              {q.ozim ? (
                <span className="izoh">{t("seans_ozim")}</span>
              ) : (
                <button
                  type="button"
                  className="tugma ikkinchi kichik"
                  style={{ color: "#d33" }}
                  disabled={band}
                  onClick={() => seansniYop(q)}
                >
                  {t("seans_yopish")}
                </button>
              )}
            </div>
          );
        })}
      </div>
      <div className="izoh" style={{ marginTop: 10 }}>{t("seans_kechikish_izoh")}</div>
      {xato && <div className="xato-xabar">{xato}</div>}
    </div>
  );
}

export default function Foydalanuvchilar() {
  const { t } = useI18n();
  const { profil } = useProfil();
  const [royxat, setRoyxat] = useState(null);
  const [qidiruv, setQidiruv] = useState("");
  const [parolForma, setParolForma] = useState({});
  const [xabar, setXabar] = useState({});
  const [yangi, setYangi] = useState({ username: "", parol: "", ism: "", rol: "student" });
  const [yangiXato, setYangiXato] = useState("");
  const [yangiBand, setYangiBand] = useState(false);
  // 2026-09-04, Shuxrat: "Aktiv foydalanuvchilar" ro'yxat USTIDA turardi
  // va sahifani cho'zib yuborardi. Endi ikkita vkladka: chapda ro'yxat,
  // o'ngda aktiv seanslar. Aktiv bo'limini faqat owner ko'radi.
  const [bolim, setBolim] = useState("royxat");

  function yukla(q) {
    const query = q !== undefined ? q : qidiruv;
    api(`/api/foydalanuvchilar/${query ? `?q=${encodeURIComponent(query)}` : ""}`)
      .then(setRoyxat)
      .catch(() => {});
  }

  useEffect(() => {
    yukla("");
  }, []);

  function qidir(e) {
    e.preventDefault();
    yukla(qidiruv);
  }

  async function parolOrnat(id) {
    const parol = parolForma[id] || "";
    if (!parol.trim()) return;
    try {
      await api(`/api/foydalanuvchilar/${id}/parol/`, { method: "POST", body: { parol } });
      setXabar((x) => ({ ...x, [id]: t("parol_ornatildi") }));
      setParolForma((f) => ({ ...f, [id]: "" }));
      yukla();
    } catch (e) {
      setXabar((x) => ({ ...x, [id]: e.data?.detail || t("xato_yuz_berdi") }));
    }
  }

  async function ochir(u) {
    if (!window.confirm(t("ochirish_tasdiq").replace("{nom}", u.username))) return;
    try {
      await api(`/api/foydalanuvchilar/${u.id}/ochirish/`, { method: "DELETE" });
      yukla();
    } catch (e) {
      setXabar((x) => ({ ...x, [u.id]: e.data?.detail || t("xato_yuz_berdi") }));
    }
  }

  async function panellarSaqla(id, panellar) {
    try {
      await api(`/api/foydalanuvchilar/${id}/panellar/`, { method: "PATCH", body: { panellar } });
      yukla();
    } catch (e) {
      setXabar((x) => ({ ...x, [id]: e.data?.detail || t("xato_yuz_berdi") }));
    }
  }

  async function farzandlarSaqla(id, farzandlar) {
    setXabar((x) => ({ ...x, [id]: "" }));
    try {
      await api(`/api/foydalanuvchilar/${id}/farzandlar/`, {
        method: "PATCH", body: { farzandlar },
      });
      yukla();
    } catch (e) {
      setXabar((x) => ({ ...x, [id]: e.data?.detail || t("xato_yuz_berdi") }));
    }
  }

  /** Boshqa foydalanuvchining profil rasmini o'chirish — sabab MAJBURIY,
   * u egasiga ogohlantirish bo'lib boradi (`ProfilRasmi` izohiga qarang). */
  async function rasmOchir(id, izoh) {
    setXabar((x) => ({ ...x, [id]: "" }));
    try {
      await api(`/api/foydalanuvchilar/${id}/rasm/`, { method: "DELETE", body: { izoh } });
      setXabar((x) => ({ ...x, [id]: t("rasm_ochirildi") }));
      yukla();
    } catch (e) {
      setXabar((x) => ({ ...x, [id]: e.data?.detail || t("xato_yuz_berdi") }));
    }
  }

  /** "Qurilmani tiklash" — sabab MAJBURIY, egasiga ogohlantirish
   * boradi (`QurilmaTiklashTugmasi` izohiga qarang). */
  async function qurilmaTiklash(id, izoh) {
    setXabar((x) => ({ ...x, [id]: "" }));
    try {
      await api(`/api/foydalanuvchilar/${id}/qurilma-tiklash/`, { method: "POST", body: { izoh } });
      setXabar((x) => ({ ...x, [id]: t("qurilma_tiklash_muvaffaqiyatli") }));
      yukla();
    } catch (e) {
      setXabar((x) => ({ ...x, [id]: e.data?.detail || t("xato_yuz_berdi") }));
    }
  }

  /** "Qurilma limiti" o'zgartirish — faqat owner (`QurilmaLimitiBoshqaruv`
   * izohiga qarang). */
  async function qurilmaLimitOzgartir(id, limit) {
    setXabar((x) => ({ ...x, [id]: "" }));
    try {
      await api(`/api/foydalanuvchilar/${id}/qurilma-limit/`, { method: "POST", body: { limit } });
      yukla();
    } catch (e) {
      setXabar((x) => ({ ...x, [id]: e.data?.detail || t("xato_yuz_berdi") }));
    }
  }

  async function yangiYarat(e) {
    e.preventDefault();
    setYangiXato("");
    if (!yangi.username.trim() || !yangi.parol.trim()) return;
    setYangiBand(true);
    try {
      await api("/api/foydalanuvchilar/yaratish/", { method: "POST", body: yangi });
      setYangi({ username: "", parol: "", ism: "", rol: "student" });
      yukla();
    } catch (e2) {
      setYangiXato(e2.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYangiBand(false);
    }
  }

  if (!royxat) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <div style={{ display: "grid", gap: 20 }}>
    {profil?.is_owner && (
      <div className="tab-guruh">
        <button
          className={bolim === "royxat" ? "aktiv" : undefined}
          onClick={() => setBolim("royxat")}
        >
          {t("nav_foydalanuvchilar")}
        </button>
        <button
          className={bolim === "aktiv" ? "aktiv" : undefined}
          onClick={() => setBolim("aktiv")}
        >
          {t("seans_sarlavha")}
        </button>
      </div>
    )}
    {profil?.is_owner && bolim === "aktiv" ? (
    <AktivFoydalanuvchilar t={t} />
    ) : (
    <div className="karta">
      {/* Owner'da bo'lim nomi vkladkada turadi, takrorlamaymiz. */}
      {!profil?.is_owner && <h3>{t("nav_foydalanuvchilar")}</h3>}

      <form
        onSubmit={yangiYarat}
        style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 18 }}
      >
        <input
          style={{ maxWidth: 160 }}
          placeholder={t("ism")}
          value={yangi.ism}
          onChange={(e) => setYangi((y) => ({ ...y, ism: e.target.value }))}
        />
        <input
          style={{ maxWidth: 160 }}
          placeholder="Login"
          value={yangi.username}
          onChange={(e) => setYangi((y) => ({ ...y, username: e.target.value }))}
        />
        <input
          type="password"
          style={{ maxWidth: 140 }}
          placeholder={t("parol")}
          value={yangi.parol}
          onChange={(e) => setYangi((y) => ({ ...y, parol: e.target.value }))}
        />
        <select
          value={yangi.rol}
          onChange={(e) => setYangi((y) => ({ ...y, rol: e.target.value }))}
        >
          {ROLLAR.map((r) => (
            <option key={r} value={r}>
              {t(`rol_${r}`)}
            </option>
          ))}
        </select>
        <button className="tugma" disabled={yangiBand}>
          {t("yangi_foydalanuvchi_yaratish")}
        </button>
        {yangiXato && <span className="xato-xabar">{yangiXato}</span>}
      </form>

      <form onSubmit={qidir} style={{ marginBottom: 14 }}>
        <input
          style={{ maxWidth: 280 }}
          placeholder={t("qidirish")}
          value={qidiruv}
          onChange={(e) => setQidiruv(e.target.value)}
        />
      </form>

      <div style={{ display: "grid", gap: 10 }}>
        {royxat.map((u) => (
          <div className="davomat-qator" key={u.id}>
            <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <ProfilRasmi user={u} ochir={rasmOchir} t={t} />
              <span>
                <strong>{u.ism}</strong>{" "}
                <span className="izoh">
                  {u.username} · {u.is_owner ? t("rol_owner") : t(`rol_${u.role}`)}
                  {u.markaz ? ` · ${u.markaz}` : ""} ·{" "}
                  {u.parol_bormi ? t("parol_bor_holat") : t("parol_yoq_holat")}
                  {u.role === "parent" && u.farzandlar?.length > 0 && (
                    <> · 👪 {u.farzandlar.map((f) => f.ism).join(", ")}</>
                  )}
                </span>
              </span>
            </span>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                type="password"
                style={{ maxWidth: 140 }}
                placeholder={t("parol")}
                value={parolForma[u.id] || ""}
                onChange={(e) =>
                  setParolForma((f) => ({ ...f, [u.id]: e.target.value }))
                }
              />
              <button className="tugma ikkinchi" onClick={() => parolOrnat(u.id)}>
                {t("parol_ornatish")}
              </button>
              {/* 2026-08-09 qarori: rol FAQAT yaratilayotganda tanlanadi,
                  keyin O'ZGARMAYDI. Bu yerda rol tanlash ro'yxati turardi —
                  olib tashlandi (backend ham endi rad etadi). Bitta odamga
                  ikki xil rol kerak bo'lsa, unga alohida profil ochiladi.
                  Rolning O'ZI baribir ko'rinadi — yuqorida, login yonida. */}
              {u.role === "parent" && (
                <FarzandTanlovi
                  user={u}
                  talabalar={royxat.filter((x) => x.role === "student")}
                  saqlash={farzandlarSaqla}
                  t={t}
                />
              )}
              {!u.is_owner && u.id !== profil?.id && (
                <PanelTanlovi user={u} saqlash={panellarSaqla} t={t} />
              )}
              <QurilmaTiklashTugmasi user={u} tiklash={qurilmaTiklash} t={t} />
              <QurilmaLimitiBoshqaruv user={u} ozgartir={qurilmaLimitOzgartir} t={t} />
              {!u.is_owner && u.id !== profil?.id && (
                <button
                  className="tugma ikkinchi"
                  style={{ color: "#d33" }}
                  onClick={() => ochir(u)}
                >
                  {t("ochirish")}
                </button>
              )}
              {xabar[u.id] && <span className="izoh">{xabar[u.id]}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
    )}
    </div>
  );
}
