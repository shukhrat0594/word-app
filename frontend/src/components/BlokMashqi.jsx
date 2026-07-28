import { useEffect, useRef, useState } from "react";
import { api, apiBlobUrl } from "../api";
import { useI18n } from "../i18n";
import { IMLO_OFF } from "../imlo";

/** Blok formatidagi darslik sahifasi (2026-07-28).
 *
 * Eski ko'rinishdan farqi: sahifa RASM emas — u qaytadan quriladi.
 * Matn haqiqiy HTML matni (o'tkir, tanlanadi, mobilda o'qiladi),
 * suratlar esa sahifadan kesib olingan alohida fayllar.
 *
 * Bo'sh joylar bloklarda faqat `savol_idx` bilan turadi (javob EMAS) —
 * javoblar serverda qoladi, ya'ni talaba F12 bosib ko'ra olmaydi.
 * "erkin" bo'sh joylar (talaba o'z ismini yozadi) baholanmaydi, lekin
 * input baribir ko'rsatiladi. */

/** Audio — KICHIK TUGMA (2026-07-28 talabi: "audio to'liq turmasligi
 * kerak, shunga audio tugmasi bo'lsin"). Har audio o'z topshirig'i
 * yonida turadi, hammasi yon panelda uyilib emas. */
function AudioTugma({ url, raqam }) {
  const audioRef = useRef(null);
  const [chalinmoqda, setChalinmoqda] = useState(false);

  useEffect(() => {
    const a = audioRef.current;
    if (!a) return undefined;
    const tugadi = () => setChalinmoqda(false);
    a.addEventListener("ended", tugadi);
    a.addEventListener("pause", tugadi);
    return () => {
      a.removeEventListener("ended", tugadi);
      a.removeEventListener("pause", tugadi);
    };
  }, [url]);

  function bosildi() {
    const a = audioRef.current;
    if (!a) return;
    if (chalinmoqda) {
      a.pause();
    } else {
      a.play();
      setChalinmoqda(true);
    }
  }

  return (
    <button
      type="button"
      className="blok-audio-tugma"
      onClick={bosildi}
      disabled={!url}
      title={raqam || ""}
    >
      <span aria-hidden="true">{chalinmoqda ? "⏸" : "▶"}</span>
      {raqam && <span className="blok-audio-raqam">{raqam}</span>}
      {/* controls YO'Q — yuklab olish tugmasi ham, to'liq pleyer ham
          ko'rinmasin; boshqaruv faqat shu tugmada. */}
      <audio ref={audioRef} src={url || undefined} preload="none" />
    </button>
  );
}

function Bolaklar({ bolaklar, javoblar, javobniQoy, natija }) {
  return (
    <>
      {bolaklar.map((b, k) => {
        if (!b.bosh_joy) return <span key={k}>{b.matn}</span>;
        if (b.erkin) {
          // Baholanmaydi (to'g'ri javob yo'q) — lekin talaba yozadi.
          return <input key={k} {...IMLO_OFF} className="blok-bosh-joy erkin" />;
        }
        const i = b.savol_idx;
        const holat = natija ? (natija.natijalar[i] ? "togri" : "notogri") : "";
        return (
          <input
            key={k}
            {...IMLO_OFF}
            className={`blok-bosh-joy ${holat}`}
            value={javoblar[i] || ""}
            disabled={!!natija}
            onChange={(e) => javobniQoy(i, e.target.value)}
          />
        );
      })}
    </>
  );
}

function Blok({ blok, rasmUrllar, audioUrllar, javoblar, javobniQoy, natija }) {
  const audio = blok.audio_raqam ? audioUrllar[blok.audio_raqam] : null;
  const audioTugma = blok.audio_raqam ? (
    <AudioTugma url={audio} raqam={blok.audio_raqam} />
  ) : null;

  switch (blok.tur) {
    case "sarlavha":
      return <h3 className="blok-sarlavha">{blok.matn}</h3>;
    case "bolim_sarlavha":
      return <h4 className="blok-bolim">{blok.matn}</h4>;
    case "rasm": {
      const url = rasmUrllar[blok.rasm_idx];
      return url ? <img className="blok-rasm" src={url} alt={blok.izoh || ""} /> : null;
    }
    case "korsatma":
      return (
        <div className="blok-korsatma">
          {blok.raqam && <span className="blok-raqam">{blok.raqam}</span>}
          {audioTugma}
          <span>{blok.matn}</span>
        </div>
      );
    case "dialog":
      return (
        <div className="blok-dialog">
          {audioTugma}
          {(blok.qatorlar || []).map((q, k) => (
            <div key={k} className="blok-dialog-qator">
              <span className="blok-dialog-kim">{q.kim}</span>
              <span>{q.gap}</span>
            </div>
          ))}
        </div>
      );
    case "grammar_spot":
      return (
        <div className="blok-gs">
          <div className="blok-gs-bosh">{blok.sarlavha || "GRAMMAR SPOT"}</div>
          <div className="blok-gs-tan">
            {(blok.qatorlar || []).map((q, k) => (
              <div key={k}>{typeof q === "string" ? q : q.matn}</div>
            ))}
          </div>
        </div>
      );
    case "pufakcha":
      return <div className="blok-pufakcha">{blok.matn}</div>;
    case "mashq":
      return (
        <div className="blok-mashq">
          {audioTugma}
          <Bolaklar
            bolaklar={blok.bolaklar || []}
            javoblar={javoblar}
            javobniQoy={javobniQoy}
            natija={natija}
          />
        </div>
      );
    default:
      return blok.matn ? <div className="blok-matn">{blok.matn}</div> : null;
  }
}

export default function BlokMashqi({ mashq, raqam }) {
  const { t } = useI18n();
  const [javoblar, setJavoblar] = useState(() => mashq.savollar.map(() => ""));
  const [natija, setNatija] = useState(null);
  const [rasmUrllar, setRasmUrllar] = useState({});
  const [audioUrllar, setAudioUrllar] = useState({});
  const [tayyor, setTayyor] = useState(false);
  const [yuborilmoqda, setYuborilmoqda] = useState(false);
  const [xato, setXato] = useState("");

  // Rasm va audiolar autentifikatsiyalangan endpointdan olinadi
  // (`apiBlobUrl`) — xom /media/ orqali emas, ya'ni havolani tashqi
  // odamga berib bo'lmaydi.
  useEffect(() => {
    let bekor = false;
    const rasmlar = mashq.blok_rasmlari || [];
    const audiolar = mashq.audiolar || [];
    Promise.all([
      ...rasmlar.map((r) => apiBlobUrl(r.url).then((u) => ["r", r.idx, u]).catch(() => null)),
      ...audiolar.map((a) => apiBlobUrl(a.url).then((u) => ["a", a.raqam, u]).catch(() => null)),
    ]).then((natijalar) => {
      if (bekor) return;
      const r = {};
      const a = {};
      natijalar.forEach((x) => {
        if (!x) return;
        if (x[0] === "r") r[x[1]] = x[2];
        else a[x[1]] = x[2];
      });
      setRasmUrllar(r);
      setAudioUrllar(a);
      setTayyor(true);
    });
    return () => {
      bekor = true;
    };
  }, [mashq.blok_rasmlari, mashq.audiolar]);

  function javobniQoy(idx, qiymat) {
    setJavoblar((j) => j.map((x, i) => (i === idx ? qiymat : x)));
  }

  async function tekshir() {
    setXato("");
    setYuborilmoqda(true);
    try {
      setNatija(
        await api(`/api/kurslar/mashq/${mashq.id}/yechish/`, {
          method: "POST",
          body: { javoblar },
        }),
      );
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuborilmoqda(false);
    }
  }

  return (
    <div className="blok-sahifa">
      {raqam != null && (
        <div className="blok-raqam-sarlavha">
          {t("kurs_mashq")} {raqam}
        </div>
      )}
      {!tayyor ? (
        <div className="izoh">{t("yuklanmoqda")}</div>
      ) : (
        <>
          {(mashq.bloklar || []).map((b, k) => (
            <Blok
              key={k}
              blok={b}
              rasmUrllar={rasmUrllar}
              audioUrllar={audioUrllar}
              javoblar={javoblar}
              javobniQoy={javobniQoy}
              natija={natija}
            />
          ))}
          {mashq.savollar.length > 0 &&
            (!natija ? (
              <button className="tugma ikkinchi" onClick={tekshir} disabled={yuborilmoqda}>
                {yuborilmoqda ? t("tekshirilmoqda") : t("tekshirish")}
              </button>
            ) : (
              <div className="izoh">
                {t("band_ball")}: {natija.ball}/{natija.jami}
              </div>
            ))}
          {xato && <div className="xato-xabar">{xato}</div>}
        </>
      )}
    </div>
  );
}
