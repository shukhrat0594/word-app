import { useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";

export default function Profil() {
  const { t } = useI18n();
  const { profil, yangila } = useProfil();
  const [eskiParol, setEskiParol] = useState("");
  const [yangiParol, setYangiParol] = useState("");
  const [xato, setXato] = useState("");
  const [xabar, setXabar] = useState("");
  const [band, setBand] = useState(false);

  async function ozgartir() {
    setXato("");
    setXabar("");
    setBand(true);
    try {
      await api("/api/profil/parol/", {
        method: "POST",
        body: { eski_parol: eskiParol, yangi_parol: yangiParol },
      });
      setXabar(t("parol_yangilandi"));
      setEskiParol("");
      setYangiParol("");
      yangila();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  if (!profil) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <>
      <div className="karta">
        <h3>{t("profil_malumot")}</h3>
        <div style={{ display: "grid", gap: 8 }}>
          <div>
            <span className="izoh">{t("ism")}: </span>
            {profil.ism}
          </div>
          <div>
            <span className="izoh">{t("login")}: </span>
            {profil.username}
          </div>
          <div>
            <span className="izoh">{t("rol")}: </span>
            {profil.role}
          </div>
          {profil.markaz && (
            <div>
              <span className="izoh">{t("markaz_nomi")}: </span>
              {profil.markaz.name}
            </div>
          )}
        </div>
      </div>

      <div className="karta" style={{ marginTop: 16 }}>
        <h3>{t("parolni_ozgartirish")}</h3>
        <p className="izoh">{t("birinchi_marta_izoh")}</p>
        <div style={{ display: "grid", gap: 14, maxWidth: 320 }}>
          <input
            type="password"
            placeholder={t("joriy_parol")}
            value={eskiParol}
            onChange={(e) => setEskiParol(e.target.value)}
          />
          <input
            type="password"
            placeholder={t("yangi_parol")}
            value={yangiParol}
            onChange={(e) => setYangiParol(e.target.value)}
          />
          {xato && <div className="xato-xabar">{xato}</div>}
          {xabar && <div className="izoh">{xabar}</div>}
          <button className="tugma" onClick={ozgartir} disabled={band}>
            {t("saqlash")}
          </button>
        </div>
      </div>
    </>
  );
}
