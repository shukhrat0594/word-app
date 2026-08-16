import { useEffect, useState } from "react";
import { api, apiForm } from "../api";
import Avatar from "../components/Avatar";
import NatijalarRoyxati from "../components/NatijalarRoyxati";
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

  // Tartib: eng yuqori huquqdan eng pastga. "parent" 2026-08-09 da
  // qo'shildi — qiymatlari `User.KorishRejimi` bilan bir xil bo'lishi
  // shart (backend shu ro'yxat bo'yicha tekshiradi).
  const REJIMLAR = ["owner", "admin", "teacher", "student", "parent", "oddiy"];

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
  const [rasmBand, setRasmBand] = useState(false);
  const [rasmXato, setRasmXato] = useState("");

  // 2026-08-14: profil tahrirlash formasi — ism + bio/maqsad/sabab
  // (ochiq) + telefon/tugilgan_sana (shaxsiy, faqat admin/owner ko'radi
  // — bu yerda "o'zi" ko'rgani uchun muammo emas). `profil` async
  // kelgani uchun useEffect bilan formani to'ldiramiz.
  const [forma, setForma] = useState(null);
  const [formaBand, setFormaBand] = useState(false);
  const [formaXato, setFormaXato] = useState("");
  const [formaXabar, setFormaXabar] = useState("");

  useEffect(() => {
    if (profil && !forma) {
      setForma({
        ism: profil.ism === profil.username ? "" : profil.ism,
        bio: profil.bio || "",
        telefon: profil.telefon || "",
        ota_ona_telefon: profil.ota_ona_telefon || "",
        tugilgan_sana: profil.tugilgan_sana || "",
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profil]);

  async function formaniSaqla() {
    setFormaXato("");
    setFormaXabar("");
    if (!forma.ism.trim()) {
      setFormaXato(t("ism_bosh_bolmasin"));
      return;
    }
    setFormaBand(true);
    try {
      await api("/api/profil/tahrirlash/", { method: "POST", body: forma });
      setFormaXabar(t("saqlandi"));
      await yangila();
    } catch (e) {
      setFormaXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setFormaBand(false);
    }
  }

  async function rasmniYukla(fayl) {
    setRasmXato("");
    setRasmBand(true);
    try {
      const fd = new FormData();
      fd.append("rasm", fayl);
      await apiForm(`/api/foydalanuvchilar/${profil.id}/rasm/`, { method: "POST", formData: fd });
      await yangila();
    } catch (e) {
      setRasmXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setRasmBand(false);
    }
  }

  async function rasmniOchir() {
    setRasmXato("");
    setRasmBand(true);
    try {
      await api(`/api/foydalanuvchilar/${profil.id}/rasm/`, { method: "DELETE" });
      await yangila();
    } catch (e) {
      setRasmXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setRasmBand(false);
    }
  }

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
      {/* 2026-08-16, foydalanuvchi talabi: "Ko'rish rejimi" owner uchun
          eng tez-tez ishlatiladigan panel — profil sahifasining ENG
          TEPASIGA chiqarildi (avval pastda, parol o'zgartirishdan keyin
          edi). */}
      {profil.asl_owner_mi && <KorishRejimiPaneli profil={profil} t={t} />}

      <div className="karta" style={{ marginTop: profil.asl_owner_mi ? 16 : 0 }}>
        <h3>{t("profil_malumot")}</h3>
        {/* 2026-08-09: har foydalanuvchi O'Z profil rasmini shu yerdan
            qo'yadi (owner boshqalarnikini "Foydalanuvchilar" sahifasida
            qo'ya oladi). Rasm R2'da yopiq turadi, shuning uchun
            autentifikatsiyalangan endpointdan keladi. */}
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 14 }}>
          <Avatar rasmUrl={profil.rasm_url} olcham={72} />
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <label className="tugma ikkinchi" style={{ cursor: "pointer" }}>
              {rasmBand ? t("yuklanmoqda") : t("rasm_yuklash")}
              <input
                type="file"
                accept="image/*"
                style={{ display: "none" }}
                disabled={rasmBand}
                onChange={(e) => {
                  const f = e.target.files[0];
                  e.target.value = "";
                  if (f) rasmniYukla(f);
                }}
              />
            </label>
            {profil.rasm_url && (
              <button className="tugma ikkinchi" onClick={rasmniOchir} disabled={rasmBand}>
                {t("rasmni_ochirish")}
              </button>
            )}
          </div>
        </div>
        {rasmXato && <div className="xato-xabar">{rasmXato}</div>}
        <div style={{ display: "grid", gap: 8 }}>
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

      {forma && (
        <div className="karta" style={{ marginTop: 16 }}>
          <h3>{t("profil_tahrirlash")}</h3>
          <div style={{ display: "grid", gap: 14, maxWidth: 420 }}>
            <label>
              <span className="izoh">{t("ism")}</span>
              <input
                value={forma.ism}
                onChange={(e) => setForma((f) => ({ ...f, ism: e.target.value }))}
                placeholder={t("ism")}
              />
            </label>
            <label>
              <span className="izoh">{t("profil_bio")}</span>
              <textarea
                rows={3}
                maxLength={500}
                value={forma.bio}
                onChange={(e) => setForma((f) => ({ ...f, bio: e.target.value }))}
                placeholder={t("profil_bio_placeholder")}
                style={{ width: "100%" }}
              />
            </label>
            <label>
              <span className="izoh">{t("profil_telefon")}</span>
              <input
                value={forma.telefon}
                onChange={(e) => setForma((f) => ({ ...f, telefon: e.target.value }))}
                placeholder="+998 90 123 45 67"
              />
            </label>
            <label>
              <span className="izoh">{t("profil_ota_ona_telefon")}</span>
              <input
                value={forma.ota_ona_telefon}
                onChange={(e) => setForma((f) => ({ ...f, ota_ona_telefon: e.target.value }))}
                placeholder="+998 90 123 45 67"
              />
            </label>
            <label>
              <span className="izoh">{t("profil_tugilgan_sana")}</span>
              <input
                type="date"
                value={forma.tugilgan_sana}
                onChange={(e) => setForma((f) => ({ ...f, tugilgan_sana: e.target.value }))}
              />
            </label>
            {formaXato && <div className="xato-xabar">{formaXato}</div>}
            {formaXabar && <div className="izoh">{formaXabar}</div>}
            <button className="tugma" onClick={formaniSaqla} disabled={formaBand}>
              {formaBand ? t("yuklanmoqda") : t("saqlash")}
            </button>
          </div>
        </div>
      )}

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

      {/* 2026-08-15: avval alohida "Tarix" paneli edi, endi shu yerda —
          foydalanuvchi o'z natijalarini profilida ko'radi. Admin/
          o'qituvchi boshqa talaba uchun ochadigani bilan AYNAN BIR XIL
          komponent (`Talabalar.jsx`da ham shu ishlatiladi). */}
      {profil && (
        <div className="karta">
          <h3>{t("mening_tarixim")}</h3>
          <NatijalarRoyxati talabaId={profil.id} />
        </div>
      )}
    </>
  );
}
