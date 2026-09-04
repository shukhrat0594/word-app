import { useEffect, useState } from "react";
import { api } from "../api";
import {
  FlashcardOyini,
  JuftiniTopOyini,
  SpeedQuizOyini,
  TugunlarOyini,
  UnscrambleOyini,
} from "../components/SozOyinlari";
import { useI18n } from "../i18n";

const DARAJALAR = ["A1", "A2", "B1", "B2", "C1", "idiom"];

// 2026-09-04, foydalanuvchi qarori: "Tugunlar" o'yinida Idioms darajasi
// ko'rsatilmaydi — idiomlar ko'p so'zli iboralar ("food for thought"), har
// katakka bitta harf tushadigan to'rga ular umuman joylanmaydi.
const TUGUNLARGA_YARAMAYDIGAN_DARAJA = "idiom";

// Ko'rinadigan nom — "idiom" ma'lumot bazasidagi qiymat (Soz.Daraja.IDIOM),
// talabaga esa "Idioms" deb ko'rsatiladi (2026-07-27 talabi).
const DARAJA_NOMI = { idiom: "Idioms" };

function GrammatikaOyini({ savollar, t, onQaytaOynash, onBoshqaMavzu }) {
  const [i, setI] = useState(0);
  const [tanlangan, setTanlangan] = useState(null);
  const [natija, setNatija] = useState(null);
  const [togriSoni, setTogriSoni] = useState(0);
  const [band, setBand] = useState(false);

  const savol = savollar[i];
  const tugadi = i >= savollar.length;

  async function javobBer(variant) {
    if (natija) return;
    setTanlangan(variant);
    setBand(true);
    try {
      const res = await api("/api/oyinlar/grammatika/tekshirish/", {
        method: "POST",
        body: { javoblar: [{ id: savol.id, javob: variant }] },
      });
      const n = res.natijalar[0];
      setNatija(n);
      if (n.togrimi) setTogriSoni((s) => s + 1);
    } finally {
      setBand(false);
    }
  }

  function keyingiSavol() {
    setTanlangan(null);
    setNatija(null);
    setI((x) => x + 1);
  }

  if (tugadi) {
    return (
      <div className="karta oyin-natija" style={{ textAlign: "center", padding: "20px 0" }}>
        <h3>{t("tabriklaymiz")}</h3>
        <div className="oyin-ball">
          {togriSoni} / {savollar.length}
        </div>
        <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
          <button className="tugma" onClick={onQaytaOynash}>
            {t("qayta_oynash")}
          </button>
          <button className="tugma ikkinchi" onClick={onBoshqaMavzu}>
            {t("boshqa_mavzu")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="karta">
      <p className="izoh">
        {i + 1} / {savollar.length}
      </p>
      <h3>{savol.savol}</h3>
      <div style={{ display: "grid", gap: 10, maxWidth: 360 }}>
        {savol.variantlar.map((v) => {
          let qoshimcha = "";
          if (natija) {
            if (v === natija.togri_javob) qoshimcha = " variant-togri";
            else if (v === tanlangan) qoshimcha = " variant-notogri";
          }
          return (
            <button
              key={v}
              className={"tugma ikkinchi" + qoshimcha}
              onClick={() => javobBer(v)}
              disabled={band || !!natija}
            >
              {v}
            </button>
          );
        })}
      </div>
      {natija && (
        <button className="tugma" style={{ marginTop: 16 }} onClick={keyingiSavol}>
          {t("keyingi")}
        </button>
      )}
    </div>
  );
}

export default function Oyinlar() {
  const { t } = useI18n();
  const [turi, setTuri] = useState("juftini_top");
  const [daraja, setDaraja] = useState("A1");
  const [mavzular, setMavzular] = useState(null);
  const [mavzu, setMavzu] = useState("");
  const [sozlar, setSozlar] = useState(null);
  const [savollar, setSavollar] = useState(null);
  const [boshlandi, setBoshlandi] = useState(false);

  useEffect(() => {
    if (turi === "grammatika" && !mavzular) {
      api("/api/oyinlar/grammatika-mavzulari/")
        .then((qs) => {
          setMavzular(qs);
          if (qs.length > 0) setMavzu(qs[0].mavzu);
        })
        .catch(() => {});
    }
  }, [turi, mavzular]);

  function oyinniBoshla() {
    setBoshlandi(true);
    if (turi === "grammatika") {
      setSavollar(null);
      api(`/api/oyinlar/grammatika/?mavzu=${mavzu}&soni=10`)
        .then(setSavollar)
        .catch(() => setSavollar([]));
      return;
    }
    setSozlar(null);
    // `tugunlar` uchun ko'proq so'raladi: to'rga faqat 3-9 harfli, bo'shliqsiz
    // so'zlar tushadi, ularning bir qismi to'rga sig'masligi ham mumkin.
    const SONI = { juftini_top: 6, flashcard: 12, speed_quiz: 8, unscramble: 8, tugunlar: 14 };
    api(`/api/oyinlar/sozlar/?daraja=${daraja}&soni=${SONI[turi] || 8}`)
      .then(setSozlar)
      .catch(() => setSozlar([]));
  }

  function ortga() {
    setBoshlandi(false);
    setSozlar(null);
    setSavollar(null);
  }

  return (
    <>
      <div className="tab-guruh">
        {[
          ["juftini_top", "juftini_top"],
          ["flashcard", "flashcard_oyin"],
          ["speed_quiz", "speed_quiz_oyin"],
          ["unscramble", "unscramble_oyin"],
          ["tugunlar", "tugunlar_oyin"],
          ["grammatika", "grammatika_oyin"],
        ].map(([kalit, nomKaliti]) => (
          <button
            key={kalit}
            className={turi === kalit ? "aktiv" : ""}
            onClick={() => {
              setTuri(kalit);
              setBoshlandi(false);
              if (kalit === "tugunlar" && daraja === TUGUNLARGA_YARAMAYDIGAN_DARAJA) {
                setDaraja(DARAJALAR[0]);
              }
            }}
          >
            {t(nomKaliti)}
          </button>
        ))}
      </div>

      {!boshlandi && turi !== "grammatika" && (
        <div className="karta">
          <h3>{t("daraja")}</h3>
          {/* 2026-07-27: avval ochiladigan <select> edi — talaba darajalarni
              ko'rmasdi, menyuni ochishi kerak edi. Endi hammasi ko'rinib
              turadi va bosib tanlanadi. */}
          <div className="tanlov-royxat">
            {DARAJALAR.filter(
              (d) => !(turi === "tugunlar" && d === TUGUNLARGA_YARAMAYDIGAN_DARAJA)
            ).map((d) => (
              <button
                key={d}
                className={"tanlov-tugma" + (daraja === d ? " aktiv" : "")}
                onClick={() => setDaraja(d)}
              >
                {DARAJA_NOMI[d] || d}
              </button>
            ))}
          </div>
          <button className="tugma" style={{ marginTop: 14 }} onClick={oyinniBoshla}>
            {t("boshlash")}
          </button>
        </div>
      )}

      {!boshlandi && turi === "grammatika" && (
        <div className="karta">
          <h3>{t("mavzu")}</h3>
          {/* Daraja ro'yxati bilan bir xil naqsh ("qolganlarida ham" talabi) —
              savol soni avvalgidek qavs ichida ko'rsatiladi. */}
          <div className="tanlov-royxat">
            {(mavzular || []).map((m) => (
              <button
                key={m.mavzu}
                className={"tanlov-tugma" + (mavzu === m.mavzu ? " aktiv" : "")}
                onClick={() => setMavzu(m.mavzu)}
              >
                {m.mavzu} <span className="tanlov-soni">{m.soni}</span>
              </button>
            ))}
          </div>
          <button
            className="tugma"
            style={{ marginTop: 14 }}
            onClick={oyinniBoshla}
            disabled={!mavzu}
          >
            {t("boshlash")}
          </button>
        </div>
      )}

      {boshlandi && turi !== "grammatika" && !sozlar && (
        <div className="yuklanmoqda">{t("sozlar_yuklanmoqda")}</div>
      )}
      {boshlandi && turi === "grammatika" && !savollar && (
        <div className="yuklanmoqda">{t("sozlar_yuklanmoqda")}</div>
      )}

      {boshlandi && sozlar && sozlar.length > 0 && turi === "juftini_top" && (
        <JuftiniTopOyini sozlar={sozlar} t={t} onQaytaOynash={oyinniBoshla} onBoshqaDaraja={ortga} />
      )}

      {boshlandi && sozlar && sozlar.length > 0 && turi === "flashcard" && (
        <FlashcardOyini sozlar={sozlar} t={t} onBoshqaDaraja={ortga} />
      )}

      {boshlandi && sozlar && sozlar.length > 0 && turi === "speed_quiz" && (
        <SpeedQuizOyini sozlar={sozlar} t={t} onQaytaOynash={oyinniBoshla} onBoshqaDaraja={ortga} />
      )}

      {boshlandi && sozlar && sozlar.length > 0 && turi === "unscramble" && (
        <UnscrambleOyini sozlar={sozlar} t={t} onQaytaOynash={oyinniBoshla} onBoshqaDaraja={ortga} />
      )}

      {boshlandi && sozlar && sozlar.length > 0 && turi === "tugunlar" && (
        <TugunlarOyini sozlar={sozlar} t={t} onQaytaOynash={oyinniBoshla} onBoshqaDaraja={ortga} />
      )}

      {boshlandi && savollar && savollar.length > 0 && turi === "grammatika" && (
        <GrammatikaOyini
          savollar={savollar}
          t={t}
          onQaytaOynash={oyinniBoshla}
          onBoshqaMavzu={ortga}
        />
      )}
    </>
  );
}
