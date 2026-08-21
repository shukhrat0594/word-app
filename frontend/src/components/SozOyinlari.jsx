import { useEffect, useState } from "react";

/** So'z-asosidagi 4 o'yin — avval `Oyinlar.jsx` ichida edi, endi bu yerga
 * chiqarilgan (2026-07-27) chunki Kurslar > Unit > Wordlist bo'limi ham
 * shu o'yinlarni (CEFR umumiy hovuzi o'rniga BITTA Unit so'zlari bilan)
 * ishlatadi — kod ikki joyda takrorlanmasligi uchun umumiy modul.
 *
 * Grammatika testi bu yerga KIRMAYDI (2026-07-27 kelishuvi) — u gap-asosidagi
 * savollarga ishlaydi, so'z juftlariga bog'liq emas, shuning uchun Wordlist
 * kontekstiga mos kelmaydi; Oyinlar.jsx'da o'zicha qoladi. */

/** O'yin davomida (natija ekranigacha) ham yopish imkoni bo'lishi
 * uchun kichik tugma (2026-08-21, foydalanuvchi talabi — avval faqat
 * natija ekranida "Boshqa daraja" bor edi, o'rtada chiqib ketish uchun
 * "Games"ga qayta bosish kerak edi). */
function YopishTugmasi({ onBoshqaDaraja, t }) {
  return (
    <button
      className="oyin-yopish"
      onClick={onBoshqaDaraja}
      title={t("yopish")}
      aria-label={t("yopish")}
    >
      ✕
    </button>
  );
}

export function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// 2026-08-21, foydalanuvchi talabi: "Barcha Unitlar" rejimida so'zlar
// soni 100+ ga yetishi mumkin — hammasi BITTA katta panelda chiqsa
// o'yin qiyin/chalkash bo'lib qolardi. Endi har turda TASODIFIY 8 ta
// so'z (16 karta = 4x4 panel) tanlanadi.
const JUFTLAR_SONI = 8;

export function JuftiniTopOyini({ sozlar, t, onQaytaOynash, onBoshqaDaraja }) {
  const [kartalar, setKartalar] = useState([]);
  const [ochiq, setOchiq] = useState([]);
  const [topilgan, setTopilgan] = useState([]);
  const [harakat, setHarakat] = useState(0);
  const [band, setBand] = useState(false);

  useEffect(() => {
    const shuTur = shuffle(sozlar).slice(0, JUFTLAR_SONI);
    const juftlar = shuTur.flatMap((s) => [
      { kalit: `en-${s.id}`, sozId: s.id, matn: s.en },
      { kalit: `uz-${s.id}`, sozId: s.id, matn: s.uz },
    ]);
    setKartalar(shuffle(juftlar));
    setOchiq([]);
    setTopilgan([]);
    setHarakat(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        <div className="oyin-natija" style={{ textAlign: "center", padding: "20px 0" }}>
          <h3>{t("tabriklaymiz")}</h3>
          <div className="izoh">{t("harakat_soni")}</div>
          <div className="oyin-ball">{harakat}</div>
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
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <p className="izoh" style={{ margin: 0 }}>
              {t("harakat_soni")}: {harakat}
            </p>
            <YopishTugmasi onBoshqaDaraja={onBoshqaDaraja} t={t} />
          </div>
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

export function FlashcardOyini({ sozlar, t, onBoshqaDaraja }) {
  // 2026-08-21, foydalanuvchi talabi: so'zlar ketma-ketligi HAR SAFAR
  // (backenddan kelgan `tartib`) emas, tasodifiy bo'lsin — bir marta
  // (mount'da) aralashtirilib, o'yin davomida shu tartibda qoladi.
  const [tartiblanganSozlar] = useState(() => shuffle(sozlar));
  const [i, setI] = useState(0);
  const [ochiq, setOchiq] = useState(false);

  const soz = tartiblanganSozlar[i];

  function keyingi() {
    setOchiq(false);
    setI((x) => Math.min(x + 1, tartiblanganSozlar.length - 1));
  }
  function oldingi() {
    setOchiq(false);
    setI((x) => Math.max(x - 1, 0));
  }

  if (!soz) return null;

  return (
    <div className="karta" style={{ textAlign: "center" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <p className="izoh" style={{ margin: 0 }}>
          {i + 1} / {tartiblanganSozlar.length}
        </p>
        <YopishTugmasi onBoshqaDaraja={onBoshqaDaraja} t={t} />
      </div>
      <div className="flashcard-sahna">
        {/* 2026-08-21, foydalanuvchi talabi: "Keyingisi" bosilganda
            kartochka aylanib (flip animatsiyasi bilan) emas, TO'G'RIDAN-
            TO'G'RI keyingi so'zga o'tsin. `key={i}` bilan har so'zda
            butunlay YANGI DOM elementi yaratiladi — eskisi "aylangan"
            holatdan CSS `transition` orqali qaytmaydi, chunki undan
            umuman VORIS emas (o'tish animatsiyasi faqat bitta elementning
            o'zgargan holatiga tegishli, yangisiga emas). */}
        <div
          key={i}
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
        <button className="tugma" onClick={keyingi} disabled={i === tartiblanganSozlar.length - 1}>
          {t("keyingi")}
        </button>
      </div>
      {i === tartiblanganSozlar.length - 1 && (
        <button className="tugma ikkinchi" style={{ marginTop: 12 }} onClick={onBoshqaDaraja}>
          {t("boshqa_daraja")}
        </button>
      )}
    </div>
  );
}

export function SpeedQuizOyini({ sozlar, t, onQaytaOynash, onBoshqaDaraja }) {
  const SONIYA = 10;
  // 2026-08-21, foydalanuvchi talabi: so'zlar tartibi tasodifiy bo'lsin.
  const [tartiblanganSozlar] = useState(() => shuffle(sozlar));
  const [i, setI] = useState(0);
  const [variantlar, setVariantlar] = useState([]);
  const [tanlangan, setTanlangan] = useState(null);
  const [ball, setBall] = useState(0);
  const [qoldi, setQoldi] = useState(SONIYA);

  const soz = tartiblanganSozlar[i];
  const tugadi = i >= tartiblanganSozlar.length;

  useEffect(() => {
    if (tugadi) return;
    const notogrilar = shuffle(
      tartiblanganSozlar.filter((s) => s.id !== soz.id).map((s) => s.uz)
    ).slice(0, 3);
    setVariantlar(shuffle([soz.uz, ...notogrilar]));
    setTanlangan(null);
    setQoldi(SONIYA);
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  function keyingi() {
    setI((x) => x + 1);
  }

  // 2026-08-21, foydalanuvchi talabi: javob TO'G'RI bo'lsa — 2 soniyadan
  // keyin AVTOMATIK keyingi savolga o'tadi, "Keyingisi" tugmasi bu vaqtda
  // umuman ko'rsatilmaydi (chalg'itmasin). Javob NOTO'G'RI (yoki vaqt
  // tugab bo'sh qoldirilgan) bo'lsa — avtomatik o'tmaydi, talaba o'zi
  // "Keyingisi" tugmasini bosishi kerak (to'g'ri javobni ko'rib olsin).
  function javobBer(variant) {
    if (tanlangan) return;
    setTanlangan(variant);
    if (variant === soz.uz) {
      setBall((b) => b + 1);
      setTimeout(keyingi, 2000);
    }
  }

  if (tugadi) {
    return (
      <div className="karta oyin-natija" style={{ textAlign: "center", padding: "20px 0" }}>
        <h3>{t("tabriklaymiz")}</h3>
        <div className="oyin-ball">
          {ball} / {tartiblanganSozlar.length}
        </div>
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
          {i + 1} / {tartiblanganSozlar.length}
        </span>
        <span className="chip bor">{t("toplangan_ball")}: {ball}</span>
        <span className={"chip " + (qoldi <= 3 ? "tugadi" : "bor")}>{qoldi}s</span>
        <YopishTugmasi onBoshqaDaraja={onBoshqaDaraja} t={t} />
      </div>
      <div className={"oyin-taymer" + (qoldi <= 3 ? " kam" : "")}>
        <div className="oyin-taymer-ip" style={{ width: `${(qoldi / SONIYA) * 100}%` }} />
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
      {tanlangan !== null && tanlangan !== soz.uz && (
        <button className="tugma" style={{ marginTop: 16 }} onClick={keyingi}>
          {t("keyingi")}
        </button>
      )}
    </div>
  );
}

export function harflargaBol(soz) {
  let aralash;
  do {
    aralash = shuffle(soz.split(""));
  } while (aralash.join("") === soz && soz.length > 1);
  return aralash;
}

export function UnscrambleOyini({ sozlar, t, onQaytaOynash, onBoshqaDaraja }) {
  // 2026-08-21, foydalanuvchi talabi: so'zlar tartibi tasodifiy bo'lsin.
  const [tartiblanganSozlar] = useState(() => shuffle(sozlar));
  const [i, setI] = useState(0);
  const [harflar, setHarflar] = useState([]);
  const [tanlangan, setTanlangan] = useState([]);
  const [natija, setNatija] = useState(null);
  const [ball, setBall] = useState(0);
  const [koʻrsatma, setKorsatma] = useState(false);

  const soz = tartiblanganSozlar[i];
  const tugadi = i >= tartiblanganSozlar.length;

  useEffect(() => {
    if (tugadi) return;
    setHarflar(harflargaBol(soz.en.toLowerCase()));
    setTanlangan([]);
    setNatija(null);
    setKorsatma(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i]);

  // 2026-08-21, foydalanuvchi talabi: "Ko'rsatma" endi tarjimani emas,
  // BIRINCHI XATO pozitsiyadagi kerakli harfni ko'rsatadi — agar talaba
  // 1-harfni noto'g'ri tanlagan bo'lsa, xuddi 1-katak belgilanadi va
  // 1-harf ko'rsatiladi; agar 1-harf to'g'ri-yu 2-harf xato bo'lsa,
  // 2-katak belgilanadi va h.k. Harf bosgach ko'rsatma o'zi o'chadi —
  // keyingi harf uchun "Ko'rsatma" tugmasi qayta bosilishi kerak.
  const togriJavob = soz ? soz.en.toLowerCase() : "";
  let xatoPozitsiya = tanlangan.length;
  for (let idx = 0; idx < tanlangan.length; idx++) {
    if (tanlangan[idx] !== togriJavob[idx]) {
      xatoPozitsiya = idx;
      break;
    }
  }
  const keyingiKerakliHarf = koʻrsatma && togriJavob ? togriJavob[xatoPozitsiya] : null;
  const hintIndeksi =
    koʻrsatma && keyingiKerakliHarf != null
      ? harflar.findIndex((h) => h === keyingiKerakliHarf)
      : -1;
  const xatoKatakIndeksi = koʻrsatma && xatoPozitsiya < tanlangan.length ? xatoPozitsiya : -1;

  function harfBos(idx) {
    if (natija) return;
    setTanlangan((t2) => [...t2, harflar[idx]]);
    setHarflar((h) => h.filter((_, hi) => hi !== idx));
    setKorsatma(false);
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

  // 2026-08-21, foydalanuvchi talabi: javob NOTO'G'RI bo'lsa, to'g'ri
  // javobni darhol ko'rsatib qo'ymasdan, harflarni QAYTADAN aralashtirib
  // (bir xil so'z bilan) yana urinib ko'rish imkoni beriladi.
  function qaytaUrin() {
    setHarflar(harflargaBol(soz.en.toLowerCase()));
    setTanlangan([]);
    setNatija(null);
  }

  function keyingi() {
    setI((x) => x + 1);
  }

  if (tugadi) {
    return (
      <div className="karta oyin-natija" style={{ textAlign: "center", padding: "20px 0" }}>
        <h3>{t("tabriklaymiz")}</h3>
        <div className="oyin-ball">
          {ball} / {tartiblanganSozlar.length}
        </div>
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
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <YopishTugmasi onBoshqaDaraja={onBoshqaDaraja} t={t} />
      </div>
      <p className="izoh">
        {i + 1} / {tartiblanganSozlar.length} · {t("toplangan_ball")}: {ball}
      </p>
      <div className="unscramble-javob">
        {tanlangan.map((h, idx) => (
          <span
            key={idx}
            className={"unscramble-harf tanlangan" + (idx === xatoKatakIndeksi ? " unscramble-hint-xato" : "")}
          >
            {h}
          </span>
        ))}
        {tanlangan.length === 0 && <span className="izoh">{t("harflarni_bosing")}</span>}
      </div>
      <div className="unscramble-harflar">
        {harflar.map((h, idx) => (
          <button
            key={idx}
            className={"unscramble-harf" + (idx === hintIndeksi ? " unscramble-hint" : "")}
            onClick={() => harfBos(idx)}
          >
            {h}
          </button>
        ))}
      </div>
      {/* 2026-08-21, foydalanuvchi talabi: to'g'ri javobda kattaroq
          matn + animatsiya; noto'g'ri bo'lsa javob DARHOL ochib
          qo'yilmasdan, qayta urinishga taklif qilinadi. */}
      {natija === true && (
        <p className="izoh oyin-togri-xabar">{t("togri_javob")}</p>
      )}
      {natija === false && (
        <p className="xato-xabar oyin-notogri-xabar">{t("qayta_urinib_koring")}</p>
      )}
      <div style={{ display: "flex", gap: 10, justifyContent: "center", marginTop: 12 }}>
        {natija === null && (
          <>
            <button className="tugma ikkinchi" onClick={tozala} disabled={tanlangan.length === 0}>
              {t("tozalash")}
            </button>
            <button
              className={"tugma ikkinchi" + (koʻrsatma ? " aktiv" : "")}
              onClick={() => setKorsatma((v) => !v)}
            >
              {t("korsatma")}
            </button>
            <button className="tugma" onClick={tekshir} disabled={harflar.length > 0}>
              {t("tekshir")}
            </button>
          </>
        )}
        {natija === false && (
          <button className="tugma" onClick={qaytaUrin}>
            {t("qayta_urinish")}
          </button>
        )}
        {natija !== null && (
          <button className="tugma ikkinchi" onClick={keyingi}>
            {t("keyingi")}
          </button>
        )}
      </div>
    </div>
  );
}
