import { useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";

/** Owner uchun — "Ko'rish rejimi" (View As), 2026-07-29 talabi: owner
 * saytni tekshirayotganda har safar chiqib boshqa test-foydalanuvchidan
 * qayta kirmasligi uchun. TO'LIQ simulyatsiya — tanlangач butun ilova
 * (backend ham) owner'ni HAQIQATAN shu rol deb ko'radi (tafsilot:
 * accounts/authentication.py).
 *
 * Tanlovdan keyin BUTUN SAHIFA qayta yuklanadi (`location.reload()`) —
 * faqat profilni qayta so'rash yetarli emas, chunki ko'p sahifa (Kurslar
 * daraxti, foydalanuvchilar ro'yxati va h.k.) ma'lumotni faqat BIRINCHI
 * ochilishda o'qiydi; to'liq yangilash eng ishonchli yo'l. */
function KorishRejimiPaneli({ profil, t }) {
  const [band, setBand] = useState(false);
  const [xato, setXato] = useState("");

  const REJIMLAR = ["owner", "admin", "student", "oddiy"];

  async function tanla(rejim) {
    if (rejim === profil.korish_rejimi || band) return;
    setXato("");
    setBand(true);
    try {
      await api("/api/profil/korish-rejimi/", {
        method: "POST",
        body: { korish_rejimi: rejim },
      });
      window.location.reload();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
      setBand(false);
    }
  }

  return (
    <div className="karta" style={{ marginTop: 16 }}>
      <h3>{t("korish_rejimi")}</h3>
      <p className="izoh" style={{ marginTop: 0 }}>{t("korish_rejimi_izoh")}</p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {REJIMLAR.map((r) => (
          <button
            key={r}
            className={"tugma" + (profil.korish_rejimi === r ? "" : " ikkinchi")}
            onClick={() => tanla(r)}
            disabled={band}
          >
            {t(`rol_${r}`)}
          </button>
        ))}
      </div>
      {xato && <div className="xato-xabar" style={{ marginTop: 8 }}>{xato}</div>}
    </div>
  );
}

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

      {/* 2026-07-29: faqat HAQIQIY owner ko'radi (`asl_owner_mi` —
          simulyatsiyadan mustaqil, aks holda owner "Ko'rish rejimi"ga
          o'tgach o'zini qaytarib bo'lmay qolardi). */}
      {profil.asl_owner_mi && <KorishRejimiPaneli profil={profil} t={t} />}

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
