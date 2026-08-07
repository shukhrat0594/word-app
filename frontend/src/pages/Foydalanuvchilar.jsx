import { useEffect, useState } from "react";
import { api } from "../api";
import { PANEL_TANLOV } from "../components/Layout";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";

const ROLLAR = ["owner", "admin", "teacher", "student", "oddiy"];

/** Rolga QO'SHIMCHA "ko'rinadigan panellar" checkbox ro'yxati
 * (2026-08-05) — owner istalgan foydalanuvchi uchun, admin faqat
 * talabalar uchun ko'radi (`PatchYoli` orqali chaqiruvchi belgilaydi).
 * `null` (yoki bo'sh) = cheklovsiz (standart, rol bo'yicha). */
export function PanelTanlovi({ user, saqlash, t }) {
  const [ochiq, setOchiq] = useState(false);
  const joriy = user.korinadigan_panellar;

  function boshqar(yol, belgilanganmi) {
    const hozirgi = joriy && joriy.length > 0 ? joriy : PANEL_TANLOV.map((p) => p.yol);
    const yangi = belgilanganmi ? hozirgi.filter((y) => y !== yol) : [...hozirgi, yol];
    saqlash(user.id, yangi.length === PANEL_TANLOV.length ? null : yangi);
  }

  return (
    <span style={{ position: "relative" }}>
      <button type="button" className="tugma ikkinchi kichik" onClick={() => setOchiq((v) => !v)}>
        {t("panel_ruxsati")} {joriy && joriy.length > 0 ? `(${joriy.length})` : ""}
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
          {PANEL_TANLOV.map((p) => {
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

  async function rolOzgartir(id, rol) {
    try {
      await api(`/api/foydalanuvchilar/${id}/rol/`, { method: "PATCH", body: { rol } });
      yukla();
    } catch (e) {
      setXabar((x) => ({ ...x, [id]: e.data?.detail || t("xato_yuz_berdi") }));
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
    <div className="karta">
      <h3>{t("nav_foydalanuvchilar")}</h3>

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
            <span>
              <strong>{u.ism}</strong>{" "}
              <span className="izoh">
                {u.username} · {u.is_owner ? t("rol_owner") : t(`rol_${u.role}`)}
                {u.markaz ? ` · ${u.markaz}` : ""} ·{" "}
                {u.parol_bormi ? t("parol_bor_holat") : t("parol_yoq_holat")}
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
              {u.id !== profil?.id && (
                <select
                  value={u.is_owner ? "owner" : u.role}
                  onChange={(e) => rolOzgartir(u.id, e.target.value)}
                >
                  {ROLLAR.map((r) => (
                    <option key={r} value={r}>
                      {t(`rol_${r}`)}
                    </option>
                  ))}
                </select>
              )}
              {!u.is_owner && u.id !== profil?.id && (
                <PanelTanlovi user={u} saqlash={panellarSaqla} t={t} />
              )}
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
  );
}
