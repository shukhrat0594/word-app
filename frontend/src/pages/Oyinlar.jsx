import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";

const DARAJALAR = ["A1", "A2", "B1", "B2", "C1", "idiom"];

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function JuftiniTopOyini({ sozlar, t, onQaytaOynash, onBoshqaDaraja }) {
  const [kartalar, setKartalar] = useState([]);
  const [ochiq, setOchiq] = useState([]);
  const [topilgan, setTopilgan] = useState([]);
  const [harakat, setHarakat] = useState(0);
  const [band, setBand] = useState(false);

  useEffect(() => {
    const juftlar = sozlar.flatMap((s) => [
      { kalit: `en-${s.id}`, sozId: s.id, matn: s.en },
      { kalit: `uz-${s.id}`, sozId: s.id, matn: s.uz },
    ]);
    setKartalar(shuffle(juftlar));
    setOchiq([]);
    setTopilgan([]);
    setHarakat(0);
  }, [sozlar]);

  function bosildi(kalit) {
    if (band || ochiq.includes(kalit) || topilgan.includes(kalit)) return;
    const yangiOchiq = [...ochiq, kalit];
    setOchiq(yangiOchiq);

    if (yangiOchiq.length === 2) {
      setHarakat((h) => h + 1);
      const [a, b] = yangiOchiq.map((k) => kartalar.find((c) => c.kalit === k));
      if (a.sozId === b.sozId) {
        setTopilgan((t2) => [...t2, ...yangiOchiq]);
        setOchiq([]);
      } else {
        setBand(true);
        setTimeout(() => {
          setOchiq([]);
          setBand(false);
        }, 800);
      }
    }
  }

  const tugadi = topilgan.length === kartalar.length && kartalar.length > 0;

  return (
    <div className="karta">
      {tugadi ? (
        <div style={{ textAlign: "center", padding: "20px 0" }}>
          <h3>{t("tabriklaymiz")}</h3>
          <p className="izoh">
            {t("harakat_soni")}: {harakat}
          </p>
          <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
            <button className="tugma" onClick={onQaytaOynash}>
              {t("qayta_oynash")}
            </button>
            <button className="tugma ikkinchi" onClick={onBoshqaDaraja}>
              {t("boshqa_daraja")}
            </button>
          </div>
        </div>
      ) : (
        <>
          <p className="izoh" style={{ marginBottom: 12 }}>
            {t("harakat_soni")}: {harakat}
          </p>
          <div className="oyin-grid">
            {kartalar.map((k) => {
              const ochilganmi = ochiq.includes(k.kalit) || topilgan.includes(k.kalit);
              return (
                <button
                  key={k.kalit}
                  className={
                    "oyin-karta" +
                    (ochilganmi ? " ochiq" : "") +
                    (topilgan.includes(k.kalit) ? " topilgan" : "")
                  }
                  onClick={() => bosildi(k.kalit)}
                >
                  {ochilganmi ? k.matn : "?"}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

function FlashcardOyini({ sozlar, t, onBoshqaDaraja }) {
  const [i, setI] = useState(0);
  const [ochiq, setOchiq] = useState(false);

  const soz = sozlar[i];

  function keyingi() {
    setOchiq(false);
    setI((x) => Math.min(x + 1, sozlar.length - 1));
  }
  function oldingi() {
    setOchiq(false);
    setI((x) => Math.max(x - 1, 0));
  }

  if (!soz) return null;

  return (
    <div className="karta" style={{ textAlign: "center" }}>
      <p className="izoh">
        {i + 1} / {sozlar.length}
      </p>
      <div className="flashcard-sahna">
        <div
          className={"flashcard" + (ochiq ? " aylangan" : "")}
          onClick={() => setOchiq(!ochiq)}
        >
          <div className="flashcard-old">{soz.en}</div>
          <div className="flashcard-orqa">
            <div style={{ fontWeight: 700, fontSize: 20 }}>{soz.uz}</div>
            {soz.turkum && <div className="izoh">{soz.turkum}</div>}
            {soz.misol && <div className="izoh" style={{ marginTop: 8 }}>{soz.misol}</div>}
          </div>
        </div>
      </div>
      <p className="izoh">{t("aylantirish")}</p>
      <div style={{ display: "flex", gap: 10, justifyContent: "center", marginTop: 12 }}>
        <button className="tugma ikkinchi" onClick={oldingi} disabled={i === 0}>
          {t("oldingi")}
        </button>
        <button className="tugma" onClick={keyingi} disabled={i === sozlar.length - 1}>
          {t("keyingi")}
        </button>
      </div>
      {i === sozlar.length - 1 && (
        <button className="tugma ikkinchi" style={{ marginTop: 12 }} onClick={onBoshqaDaraja}>
          {t("boshqa_daraja")}
        </button>
      )}
    </div>
  );
}

function SpeedQuizOyini({ sozlar, t, onQaytaOynash, onBoshqaDaraja }) {
  const SONIYA = 10;
  const [i, setI] = useState(0);
  const [variantlar, setVariantlar] = useState([]);
  const [tanlangan, setTanlangan] = useState(null);
  const [ball, setBall] = useState(0);
  const [qoldi, setQoldi] = useState(SONIYA);

  const soz = sozlar[i];
  const tugadi = i >= sozlar.length;

  useEffect(() => {
    if (tugadi) return;
    const notogrilar = shuffle(
      sozlar.filter((s) => s.id !== soz.id).map((s) => s.uz)
    ).slice(0, 3);
    setVariantlar(shuffle([soz.uz, ...notogrilar]));
    setTanlangan(null);
    setQoldi(SONIYA);
  }, [i]);

  useEffect(() => {
    if (tugadi || tanlangan) return;
    if (qoldi <= 0) {
      setTanlangan("");
      return;
    }
    const timer = setTimeout(() => setQoldi((q) => q - 1), 1000);
    return () => clearTimeout(timer);
  }, [qoldi, tanlangan, tugadi]);

  function javobBer(variant) {
    if (tanlangan) return;
    setTanlangan(variant);
    if (variant === soz.uz) setBall((b) => b + 1);
  }

  function keyingi() {
    setI((x) => x + 1);
  }

  if (tugadi) {
    return (
      <div className="karta" style={{ textAlign: "center", padding: "20px 0" }}>
        <h3>{t("tabriklaymiz")}</h3>
        <p className="izoh">
          {ball} / {sozlar.length}
        </p>
        <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
          <button className="tugma" onClick={onQaytaOynash}>
            {t("qayta_oynash")}
          </button>
          <button className="tugma ikkinchi" onClick={onBoshqaDaraja}>
            {t("boshqa_daraja")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="karta">
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <span className="izoh">
          {i + 1} / {sozlar.length}
        </span>
        <span className="chip bor">{t("toplangan_ball")}: {ball}</span>
        <span className={"chip " + (qoldi <= 3 ? "tugadi" : "bor")}>{qoldi}s</span>
      </div>
      <h3 style={{ marginTop: 10 }}>{soz.en}</h3>
      <div style={{ display: "grid", gap: 10, maxWidth: 360 }}>
        {variantlar.map((v) => {
          let qoshimcha = "";
          if (tanlangan) {
            if (v === soz.uz) qoshimcha = " variant-togri";
            else if (v === tanlangan) qoshimcha = " variant-notogri";
          }
          return (
            <button
              key={v}
              className={"tugma ikkinchi" + qoshimcha}
              onClick={() => javobBer(v)}
              disabled={!!tanlangan}
            >
              {v}
            </button>
          );
        })}
      </div>
      {tanlangan !== null && (
        <button className="tugma" style={{ marginTop: 16 }} onClick={keyingi}>
          {t("keyingi")}
        </button>
      )}
    </div>
  );
}

function harflargaBol(soz) {
  let aralash;
  do {
    aralash = shuffle(soz.split(""));
  } while (aralash.join("") === soz && soz.length > 1);
  return aralash;
}

function UnscrambleOyini({ sozlar, t, onQaytaOynash, onBoshqaDaraja }) {
  const [i, setI] = useState(0);
  const [harflar, setHarflar] = useState([]);
  const [tanlangan, setTanlangan] = useState([]);
  const [natija, setNatija] = useState(null);
  const [ball, setBall] = useState(0);
  const [koʻrsatma, setKorsatma] = useState(false);

  const soz = sozlar[i];
  const tugadi = i >= sozlar.length;

  useEffect(() => {
    if (tugadi) return;
    setHarflar(harflargaBol(soz.en.toLowerCase()));
    setTanlangan([]);
    setNatija(null);
    setKorsatma(false);
  }, [i]);

  function harfBos(idx) {
    if (natija) return;
    setTanlangan((t2) => [...t2, harflar[idx]]);
    setHarflar((h) => h.filter((_, hi) => hi !== idx));
  }

  function tozala() {
    if (natija) return;
    setHarflar(shuffle([...harflar, ...tanlangan]));
    setTanlangan([]);
  }

  function tekshir() {
    const togrimi = tanlangan.join("") === soz.en.toLowerCase();
    setNatija(togrimi);
    if (togrimi) setBall((b) => b + 1);
  }

  function keyingi() {
    setI((x) => x + 1);
  }

  if (tugadi) {
    return (
      <div className="karta" style={{ textAlign: "center", padding: "20px 0" }}>
        <h3>{t("tabriklaymiz")}</h3>
        <p className="izoh">
          {ball} / {sozlar.length}
        </p>
        <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
          <button className="tugma" onClick={onQaytaOynash}>
            {t("qayta_oynash")}
          </button>
          <button className="tugma ikkinchi" onClick={onBoshqaDaraja}>
            {t("boshqa_daraja")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="karta" style={{ textAlign: "center" }}>
      <p className="izoh">
        {i + 1} / {sozlar.length} · {t("toplangan_ball")}: {ball}
      </p>
      <div className="unscramble-javob">
        {tanlangan.map((h, idx) => (
          <span key={idx} className="unscramble-harf tanlangan">
            {h}
          </span>
        ))}
        {tanlangan.length === 0 && <span className="izoh">{t("harflarni_bosing")}</span>}
      </div>
      <div className="unscramble-harflar">
        {harflar.map((h, idx) => (
          <button key={idx} className="unscramble-harf" onClick={() => harfBos(idx)}>
            {h}
          </button>
        ))}
      </div>
      {koʻrsatma && <p className="izoh">{soz.uz}</p>}
      {natija !== null && (
        <p className={natija ? "izoh" : "xato-xabar"}>
          {natija ? t("togri_javob") : soz.en}
        </p>
      )}
      <div style={{ display: "flex", gap: 10, justifyContent: "center", marginTop: 12 }}>
        {!natija && (
          <>
            <button className="tugma ikkinchi" onClick={tozala} disabled={tanlangan.length === 0}>
              {t("tozalash")}
            </button>
            <button className="tugma ikkinchi" onClick={() => setKorsatma(true)}>
              {t("korsatma")}
            </button>
            <button
              className="tugma"
              onClick={tekshir}
              disabled={harflar.length > 0 || !!natija}
            >
              {t("tekshir")}
            </button>
          </>
        )}
        {natija !== null && (
          <button className="tugma" onClick={keyingi}>
            {t("keyingi")}
          </button>
        )}
      </div>
    </div>
  );
}

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
      <div className="karta" style={{ textAlign: "center", padding: "20px 0" }}>
        <h3>{t("tabriklaymiz")}</h3>
        <p className="izoh">
          {togriSoni} / {savollar.length}
        </p>
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
    const SONI = { juftini_top: 6, flashcard: 12, speed_quiz: 8, unscramble: 8 };
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
          ["grammatika", "grammatika_oyin"],
        ].map(([kalit, nomKaliti]) => (
          <button
            key={kalit}
            className={turi === kalit ? "aktiv" : ""}
            onClick={() => {
              setTuri(kalit);
              setBoshlandi(false);
            }}
          >
            {t(nomKaliti)}
          </button>
        ))}
      </div>

      {!boshlandi && turi !== "grammatika" && (
        <div className="karta">
          <h3>{t("daraja")}</h3>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <select value={daraja} onChange={(e) => setDaraja(e.target.value)}>
              {DARAJALAR.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
            <button className="tugma" onClick={oyinniBoshla}>
              {t("boshlash")}
            </button>
          </div>
        </div>
      )}

      {!boshlandi && turi === "grammatika" && (
        <div className="karta">
          <h3>{t("mavzu")}</h3>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <select value={mavzu} onChange={(e) => setMavzu(e.target.value)}>
              {(mavzular || []).map((m) => (
                <option key={m.mavzu} value={m.mavzu}>
                  {m.mavzu} ({m.soni})
                </option>
              ))}
            </select>
            <button className="tugma" onClick={oyinniBoshla} disabled={!mavzu}>
              {t("boshlash")}
            </button>
          </div>
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
