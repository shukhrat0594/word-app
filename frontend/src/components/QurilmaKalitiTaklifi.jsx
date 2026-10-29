import { useEffect, useState } from "react";
import { api, kalitQollaydimi, kalitYarat } from "../api";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";

/** «Bu qurilmani eslab qolish» (2026-10-29, qurilmalar limiti 2-tizim). Qurilma kaliti
 * yaratilsa, brauzer tarixi tozalansa ham yoki shu telefondagi boshqa brauzerdan kirsa ham
 * qurilma admin'siz tanib olinadi. Ko'rinadi: qurilmada kalit yo'q va brauzer qo'llasa.
 * «Keyinroq» — shu seans davomida yashiriladi, keyingi kirishda yana so'raladi.
 *
 * Telefonga yuboriladigan so'rov OLDINDAN olinadi (va 4 daqiqada yangilanadi): Safari kalit
 * yaratishni faqat bosish paytida, orada server javobini kutmasdan ruxsat beradi. */
const YASHIRISH_KALITI = "kalit_taklifi_yopildi";

function yashirilganmi() {
  try {
    return sessionStorage.getItem(YASHIRISH_KALITI) === "1";
  } catch {
    return false;
  }
}

export default function QurilmaKalitiTaklifi() {
  const { t } = useI18n();
  const { profil, yangila } = useProfil();
  const [qollaydi, setQollaydi] = useState(false);
  const [yopildi, setYopildi] = useState(yashirilganmi);
  const [sozlama, setSozlama] = useState(null);
  const [band, setBand] = useState(false);
  const [xabar, setXabar] = useState("");
  const korinadi = Boolean(profil?.qurilma && !profil.qurilma.kalit_bor && qollaydi && !yopildi);

  useEffect(() => {
    kalitQollaydimi().then(setQollaydi);
  }, []);

  useEffect(() => {
    if (!korinadi) return undefined;
    const ol = () => api("/api/qurilma/kalit/boshlash/", { method: "POST" }).then(setSozlama).catch(() => setSozlama(null));
    ol();
    const taymer = setInterval(ol, 4 * 60 * 1000);
    return () => clearInterval(taymer);
  }, [korinadi]);

  async function eslabQol() {
    setBand(true);
    setXabar("");
    try {
      const javob = await kalitYarat(sozlama.kalit);
      await api("/api/qurilma/kalit/saqlash/", { method: "POST", body: { chipta: sozlama.chipta, javob } });
      setXabar("ok");
      yangila();
    } catch (e) {
      setXabar(e instanceof DOMException ? t("kalit_bekor") : e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  function keyinroq() {
    try {
      sessionStorage.setItem(YASHIRISH_KALITI, "1");
    } catch {
      // sessionStorage yopiq — shu sahifa davomida yashiriladi
    }
    setYopildi(true);
  }

  if (xabar === "ok") {
    return (
      <div className="karta parol-ogohlantirish" style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <span>{t("kalit_saqlandi")}</span>
        <button type="button" className="tugma ikkinchi kichik" onClick={() => setXabar("")}>{t("yopish")}</button>
      </div>
    );
  }
  if (!korinadi) return null;
  return (
    <div className="karta parol-ogohlantirish" style={{ display: "grid", gap: 8 }}>
      <span>{t("kalit_taklif_matn")}</span>
      {xabar && <span className="xato-xabar">{xabar}</span>}
      <span style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button type="button" className="tugma kichik" onClick={eslabQol} disabled={band || !sozlama}>
          {t("kalit_taklif_tugma")}
        </button>
        <button type="button" className="tugma ikkinchi kichik" onClick={keyinroq} disabled={band}>
          {t("kalit_taklif_keyin")}
        </button>
      </span>
    </div>
  );
}
