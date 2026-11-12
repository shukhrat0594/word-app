import { useEffect, useRef, useState } from "react";
import { useI18n } from "../i18n";
import { IMLO_OFF } from "../imlo";
import { DARAJALAR } from "../listeningMatnlar";

const TEZLIKLAR = [0.7, 0.85, 1];

/** Taqqoslash uchun so'z: kichik harf, tinish belgilarisiz, egri apostrof
 * to'g'risiga almashtirilgan ("Don’t," == "don't"). */
function sozTozala(s) {
  return s
    .toLowerCase()
    .replace(/[’‘`]/g, "'")
    .replace(/[^a-z0-9']/g, "");
}

function sozlarga(matn) {
  return matn.split(/\s+/).map(sozTozala).filter(Boolean);
}

/** Har bir to'g'ri so'z uchun: talaba shu o'rinda to'g'ri yozdimi.
 * Joyma-joy taqqoslanadi (dailydictation'dagidek oddiy usul) — so'z
 * tushib qolsa, undan keyingilari ham xato ko'rinadi, bu talabaga
 * "qayerdan adashganini" ko'rsatadi. */
export function gapniTekshir(asl, yozilgan) {
  const togri = asl.split(/\s+/).filter(Boolean);
  const yozSozlar = sozlarga(yozilgan);
  return togri.map((soz, i) => ({ soz, mos: sozTozala(soz) === (yozSozlar[i] ?? null) }));
}

/** Listening trainer (2026-11-12, TZ 712) — diktant: gap ovoz bilan
 * o'qiladi, talaba eshitganini yozadi va tekshiradi. Ovozni brauzer
 * o'qiydi (speechSynthesis), backend so'rovi yo'q, natija saqlanmaydi. */
export default function ListeningTrainer() {
  const { t } = useI18n();
  const ovozBor = typeof window !== "undefined" && "speechSynthesis" in window;
  const [darajaI, setDarajaI] = useState(0);
  const [darsI, setDarsI] = useState(null);
  const [gapI, setGapI] = useState(0);
  const [matn, setMatn] = useState("");
  const [natija, setNatija] = useState(null);
  const [ochildi, setOchildi] = useState(false);
  const [tezlik, setTezlik] = useState(0.85);
  const [ovozlar, setOvozlar] = useState([]);
  const inputRef = useRef(null);

  const daraja = DARAJALAR[darajaI];
  const dars = darsI === null ? null : daraja.darslar[darsI];
  const gap = dars ? dars.gaplar[gapI] : "";

  // Brauzer ovozlar ro'yxatini kech yuklaydi (Chrome) — tayyor bo'lganda olamiz.
  useEffect(() => {
    if (!ovozBor) return undefined;
    const ol = () => setOvozlar(window.speechSynthesis.getVoices());
    ol();
    window.speechSynthesis.addEventListener("voiceschanged", ol);
    return () => {
      window.speechSynthesis.removeEventListener("voiceschanged", ol);
      window.speechSynthesis.cancel();
    };
  }, [ovozBor]);

  function oqi(s = gap) {
    if (!ovozBor || !s) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(s);
    u.lang = "en-US";
    const ovoz =
      ovozlar.find((v) => v.lang === "en-US") || ovozlar.find((v) => v.lang?.startsWith("en"));
    if (ovoz) u.voice = ovoz;
    u.rate = tezlik;
    window.speechSynthesis.speak(u);
    inputRef.current?.focus();
  }

  function gapgaOt(i) {
    setGapI(i);
    setMatn("");
    setNatija(null);
    setOchildi(false);
    if (dars) oqi(dars.gaplar[i]);
  }

  function darsniOch(i) {
    setDarsI(i);
    setGapI(0);
    setMatn("");
    setNatija(null);
    setOchildi(false);
  }

  function tekshir() {
    if (!matn.trim()) return;
    setNatija(gapniTekshir(gap, matn));
  }

  const hammasiTogri = natija && natija.every((x) => x.mos);
  const oxirgiGap = dars && gapI === dars.gaplar.length - 1;

  if (!dars) {
    return (
      <div className="karta">
        <h3>🎧 {t("nav_listening_trainer")}</h3>
        <p className="izoh" style={{ marginTop: 0 }}>{t("listening_izoh")}</p>
        {!ovozBor && <div className="xato-xabar" style={{ marginBottom: 10 }}>{t("listening_ovoz_yoq")}</div>}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
          {DARAJALAR.map((d, i) => (
            <button
              key={d.kalit}
              className={"tugma kichik" + (i === darajaI ? "" : " ikkinchi")}
              onClick={() => setDarajaI(i)}
            >
              {d.nom}
            </button>
          ))}
        </div>
        <div style={{ display: "grid", gap: 8 }}>
          {daraja.darslar.map((d, i) => (
            <button
              key={d.nom}
              className="tugma ikkinchi"
              style={{ textAlign: "left" }}
              onClick={() => darsniOch(i)}
            >
              {i + 1}. {d.nom} <span className="izoh">({d.gaplar.length} {t("listening_gap")})</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="karta">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <h3 style={{ margin: 0 }}>🎧 {daraja.kalit} · {dars.nom}</h3>
        <button className="tugma ikkinchi kichik" onClick={() => setDarsI(null)}>
          ← {t("listening_darslar")}
        </button>
      </div>
      <p className="izoh">
        {t("listening_gap_raqami")} {gapI + 1} / {dars.gaplar.length}
      </p>
      {!ovozBor && <div className="xato-xabar" style={{ marginBottom: 10 }}>{t("listening_ovoz_yoq")}</div>}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 10 }}>
        <button className="tugma" onClick={() => oqi()} disabled={!ovozBor}>
          ▶ {t("listening_eshitish")}
        </button>
        <label className="izoh">{t("listening_tezlik")}:</label>
        <select value={tezlik} onChange={(e) => setTezlik(Number(e.target.value))}>
          {TEZLIKLAR.map((x) => (
            <option key={x} value={x}>{x}x</option>
          ))}
        </select>
      </div>
      <textarea
        {...IMLO_OFF}
        ref={inputRef}
        rows={2}
        maxLength={500}
        style={{ width: "100%" }}
        value={matn}
        onChange={(e) => {
          setMatn(e.target.value);
          setNatija(null);
        }}
        onKeyDown={(e) => {
          // Enter — tekshirish, Ctrl (yoki Cmd) — gapni qayta eshitish.
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            tekshir();
          } else if (e.key === "Control" || e.key === "Meta") {
            oqi();
          }
        }}
        placeholder={t("listening_yozing")}
      />
      <p className="izoh" style={{ marginTop: 4 }}>{t("listening_klavish")}</p>
      {natija && (
        <div style={{ margin: "10px 0", fontSize: 18, lineHeight: 1.6 }}>
          {natija.map((x, i) => (
            <span
              key={i}
              style={{ color: x.mos ? "var(--yaxshi)" : "var(--xato)", marginRight: 6 }}
            >
              {x.mos || ochildi ? x.soz : "*".repeat(Math.max(3, sozTozala(x.soz).length))}
            </span>
          ))}
          {hammasiTogri && <div style={{ color: "var(--yaxshi)", fontWeight: 700 }}>✓ {t("listening_togri")}</div>}
        </div>
      )}
      {ochildi && !natija && (
        <div style={{ margin: "10px 0", fontSize: 18 }}>{gap}</div>
      )}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
        <button className="tugma" disabled={!matn.trim()} onClick={tekshir}>
          {t("listening_tekshirish")}
        </button>
        <button className="tugma ikkinchi" onClick={() => setOchildi(true)}>
          {t("listening_korsatish")}
        </button>
        <button className="tugma ikkinchi" disabled={gapI === 0} onClick={() => gapgaOt(gapI - 1)}>
          ← {t("listening_oldingi")}
        </button>
        {oxirgiGap ? (
          <button className="tugma ikkinchi" onClick={() => setDarsI(null)}>
            ✓ {t("listening_tugatish")}
          </button>
        ) : (
          <button className="tugma ikkinchi" onClick={() => gapgaOt(gapI + 1)}>
            {t("listening_keyingi")} →
          </button>
        )}
      </div>
    </div>
  );
}
