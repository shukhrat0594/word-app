import { useEffect, useRef, useState } from "react";
import { api, apiBlobUrl, apiFayluniYuklab, apiForm } from "../api";
import { AUDIO_HIMOYA, faqatBittaAudioIjro } from "../audio";
import BlokMashqi from "../components/BlokMashqi";
import BlokTasdiqlash from "../components/BlokTasdiqlash";
import {
  FlashcardOyini,
  JuftiniTopOyini,
  SpeedQuizOyini,
  UnscrambleOyini,
} from "../components/SozOyinlari";
import { useI18n } from "../i18n";
import { IMLO_OFF } from "../imlo";
import { useProfil } from "../profilContext";

// 2026-07-27: admin darslikdagi rasmli mashqni qo'lda JSON'ga o'girish
// o'rniga, shu promtni ChatGPT/Claude/Gemini kabi AI'ga (skrinshot bilan
// birga) beradi — AI "pozitsiya" koordinatalarini rasmning o'zidan
// aniqlab, tayyor JSON qaytaradi. Bu — FLAT (Unit'siz) bo'limlar uchun
// (masalan Elementary...Upper-Intermediate, IELTS Textbooks qismlari) —
// bitta bo'lim, bitta mashq to'plami. Beginner Unit'lari uchun esa
// UCHTA bo'lim (Mashqlar+Grammar reference+Wordlist) bitta so'rovda
// yuklanadi — pastdagi `AI_PROMT_UNIT`ga qarang.
const AI_PROMT = `Men senga o'quv darsligi (masalan Headway) sahifasidan bitta mashqning skrinshotini va/yoki matnini beraman. Sen shu materialni quyidagi JSON formatiga o'girib ber — natija FAQAT valid JSON MASSIV bo'lsin (kvadrat qavs bilan boshlanib tugasin), hech qanday izoh, sarlavha yoki markdown belgisi (masalan \`\`\`json) qo'shma, faqat sof JSON matni qaytar.

Format — massiv ichida har bir mashq shu ko'rinishda:
[
  {
    "matn": "Mashq topshirig'i/sarlavhasi (ixtiyoriy, bo'lmasa bo'sh qoldir)",
    "savollar": [
      {
        "savol": "Savol yoki band nomi",
        "variantlar": ["variant1", "variant2"] (ixtiyoriy — ochiq javobli bo'lsa bo'sh massiv []),
        "togri": "To'g'ri javob (yoki bir nechta qabul qilinadigan javob bo'lsa massiv, masalan [\\"3\\", \\"three\\"])",
        "pozitsiya": {"x": 0-100, "y": 0-100} (ixtiyoriy — FAQAT sizga rasm (skrinshot) ilova qilingan bo'lsa va shu savolning bo'sh joyi/raqami rasmda aniq ko'rinib tursa qo'sh: rasmning chap-yuqori burchagidan boshlab, bo'sh joy markazining rasm eniga nisbatan foizini "x", bo'yiga nisbatan foizini "y" qilib yoz. Rasm berilmagan yoki savol oddiy matn ro'yxati bo'lsa (rasmga bog'liq bo'lmagan) — bu maydonni umuman yozma)
      }
    ]
  }
]

Qoidalar:
- Agar sizga rasm (skrinshot) berilgan bo'lsa va mashqda bir nechta bo'sh joy/raqamlangan band rasmning turli nuqtalarida bo'lsa — HAR BIRIGA "pozitsiya" qo'shing, shunda talaba javobni rasmning aynan o'sha nuqtasida yoza oladi (masalan "rasmdagi narsalarni sanab yoz" turidagi mashqlar)
- Agar mashq oddiy savol-javob ro'yxati bo'lsa (rasmga bog'liq bo'lmagan matn/gap to'ldirish) — "pozitsiya"ni umuman yozmang, savol oddiy ro'yxatda chiqadi
- Bir nechta mashq bo'lsa, massivga har birini alohida obyekt qilib qo'shing (bitta mashq bo'lsa ham, bitta elementli massiv qaytaring — obyektning o'zini emas)
- "rasm" va "audio" maydonlarini HECH QACHON JSON'ga qo'shmang — ular saytda alohida (fayl sifatida, mashq yaratilgandan keyin) biriktiriladi, siz (AI) haqiqiy fayl yarata olmaysiz

Natijani shu JSON massiv ko'rinishida qaytar, boshqa hech narsa yozma. Quyida mashq materiali (matn va/yoki tasvirlangan rasm):

[BU YERGA MASHQ MATNINI JOYLASHTIRING YOKI SKRINSHOTNI ILOVA QILING]`;

/** Butun oynani qoplaydigan "band" indikatori (2026-09-03, foydalanuvchi
 * talabi: "kurslar yuklanayotgan payt — SB, WB, Unit yoki butun daraja —
 * oynadagi hech qaysi tugma va bo'limlarga o'tish bosilmasin").
 *
 * `.blok-yuklash-qoplama` — `position: fixed; inset: 0; z-index: 10000`,
 * ya'ni yon paneldagi navigatsiyani ham qoplaydi (sahifadagi eng katta
 * boshqa z-index — 300). Shu sababli alohida "bloklash" mexanizmi
 * kerak emas: qoplama chizilgan zahoti barcha bosishlar unga tushadi.
 *
 * Avval bu faqat ZIP orqali mashq yuklashda bor edi (2026-07-29) — endi
 * uzoq davom etadigan BARCHA kurs amallarida ishlatiladi. */
function BandQoplamasi({ matn }) {
  const { t } = useI18n();
  return (
    <div className="blok-yuklash-qoplama">
      <div className="blok-yuklash-karta">
        <div className="blok-yuklash-spinner" aria-hidden="true" />
        <div style={{ fontWeight: 700 }}>{matn || t("yuklanmoqda")}</div>
        <div className="izoh">{t("kurs_band_ogohlantirish")}</div>
      </div>
    </div>
  );
}

/** Rasm ustiga to'g'ridan-to'g'ri joylashtiriladigan savollar (masalan
 * "nechta narsa bor?" turidagi mashqlar) — savolda "pozitsiya":
 * {"x": 0-100, "y": 0-100} bo'lsa, oddiy ro'yxatda emas, aynan shu nuqtada
 * kichik input sifatida ko'rsatiladi (2026-07-27).
 *
 * IELTS testlaridagi (`ImtihonOtish.jsx: RasmSavollari`) bilan bir xil
 * mexanizm va bir xil CSS klassi (`imtihon-rasm-input`) — nomi "imtihon"
 * bo'lsa ham, klass sof vizual (pozitsiyalangan input), imtihonga xos
 * mantiq yo'q, shuning uchun bu yerda ham xavfsiz qayta ishlatiladi. */
function RasmMashqi({ rasmUrl, savollar, idxlar, javoblar, javobniQoy, natija }) {
  return (
    <div style={{ position: "relative", display: "inline-block", maxWidth: "100%", marginBottom: 8 }}>
      <img src={rasmUrl} alt="" style={{ maxWidth: "100%", display: "block" }} />
      {savollar.map((s, k) => {
        const i = idxlar[k];
        const holat = natija ? (natija.natijalar[i] ? "togri" : "notogri") : "";
        return (
          <input
            key={i}
            {...IMLO_OFF}
            className={`imtihon-rasm-input ${holat}`}
            // 2026-08-07: "kenglik" (rasm kengligiga nisbatan foiz) —
            // rasm-fon rejimida AI bo'sh joyning CHAP va O'NG chetini
            // beradi, ya'ni input aynan chizilgan chiziqni to'liq
            // yopishi mumkin. Eski (2026-07-27) kontentda bu maydon
            // yo'q — u holda CSS'dagi qat'iy en ishlaydi.
            style={{
              left: `${s.pozitsiya.x}%`,
              top: `${s.pozitsiya.y}%`,
              ...(s.pozitsiya.kenglik ? { width: `${s.pozitsiya.kenglik}%` } : {}),
            }}
            disabled={!!natija}
            value={javoblar[i] || ""}
            onChange={(e) => javobniQoy(i, e.target.value)}
            placeholder={`${i + 1}`}
          />
        );
      })}
    </div>
  );
}

/** Talaba uchun — bitta mashqqa javob yozish va natija ko'rish.
 * `raqam` (2026-07-27) — "raqamlangan mashqlar" talabi bo'yicha har bir
 * mashq tartib raqami bilan ko'rsatiladi. */
function TalabaMashqi({ mashq, raqam, javoblarOchiq }) {
  const { t } = useI18n();
  const [javoblar, setJavoblar] = useState(
    mashq.savollar.map((s) => (javoblarOchiq ? s.togri || "" : "")),
  );
  const [natija, setNatija] = useState(null);
  const [rasmUrl, setRasmUrl] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [audioUrllar, setAudioUrllar] = useState([]);
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [xato, setXato] = useState("");
  // Yuklanish holati (2026-07-28, foydalanuvchi talabi) — rasm/audio
  // fayllar hali to'liq yuklanmagan bo'lsa, savollar UMUMAN ko'rinmaydi
  // ("Yuklanmoqda" ko'rsatiladi) — kutilmagan bo'sh rasm/audio bilan
  // savolga javob berishning oldini olish uchun.
  const [rasmYuklandi, setRasmYuklandi] = useState(!mashq.rasm_url);
  const [audioYuklandi, setAudioYuklandi] = useState(!mashq.audio_url);
  const [audiolarYuklandi, setAudiolarYuklandi] = useState(!mashq.audiolar?.length);

  useEffect(() => {
    if (mashq.rasm_url) {
      apiBlobUrl(mashq.rasm_url).then(setRasmUrl).finally(() => setRasmYuklandi(true));
    }
  }, [mashq.rasm_url]);

  useEffect(() => {
    if (mashq.audio_url) {
      apiBlobUrl(mashq.audio_url).then(setAudioUrl).finally(() => setAudioYuklandi(true));
    }
  }, [mashq.audio_url]);

  // Bitta mashqqa BIR NECHTA audio biriktirilgan bo'lishi mumkin
  // (2026-07-27, foydalanuvchi talabi — bitta sahifada bir nechta
  // Listening bandi bo'lsa, hammasi yon panelda ro'yxat, talaba
  // keraklisini play qiladi).
  useEffect(() => {
    if (!mashq.audiolar || mashq.audiolar.length === 0) return;
    Promise.all(mashq.audiolar.map((a) => apiBlobUrl(a.url).then((url) => ({ ...a, url }))))
      .then(setAudioUrllar)
      .finally(() => setAudiolarYuklandi(true));
  }, [mashq.audiolar]);

  const hammasiTayyor = rasmYuklandi && audioYuklandi && audiolarYuklandi;

  function javobniQoy(idx, qiymat) {
    setJavoblar((j) => j.map((x, i) => (i === idx ? qiymat : x)));
  }

  async function tekshir() {
    setXato("");
    setYuklanmoqda(true);
    try {
      const res = await api(`/api/kurslar/mashq/${mashq.id}/yechish/`, {
        method: "POST",
        body: { javoblar },
      });
      setNatija(res);
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  // Rasm ustida ko'rsatiladigan savollar ("pozitsiya" bor) va qolgan
  // oddiy savollar alohida ajratiladi — asl indeksi (javoblar massividagi
  // o'rni) saqlanib qoladi.
  const rasmIdxlari = [];
  const rasmSavollari = [];
  const oddiySavollar = [];
  mashq.savollar.forEach((s, i) => {
    if (s.pozitsiya && rasmUrl) {
      rasmIdxlari.push(i);
      rasmSavollari.push(s);
    } else {
      oddiySavollar.push([s, i]);
    }
  });

  const audioPanelBorMi = audioUrl || audioUrllar.length > 0;

  return (
    <div style={{ border: "1px solid var(--chiziq)", borderRadius: 8, padding: 10, marginBottom: 8 }}>
      {raqam != null && (
        <div style={{ fontWeight: 700, marginBottom: 6 }}>
          {t("kurs_mashq")} {raqam}
        </div>
      )}
      {mashq.matn && <div style={{ marginBottom: 8 }}>{mashq.matn}</div>}

      {!hammasiTayyor ? (
        <div className="izoh">{t("yuklanmoqda")}</div>
      ) : (
        <>
          {/* Audio — mashq/rasmning PASTIDA emas, O'NG TOMONIDA (2026-07-28,
              foydalanuvchi talabi). Rasm/mashq chapda (flex:1), audio(lar)
              o'ngda alohida ustun. */}
          <div style={{ display: "flex", gap: 12, alignItems: "flex-start", marginBottom: 8 }}>
            <div style={{ flex: "1 1 auto", minWidth: 0, maxWidth: "calc(100% - 232px)" }}>
              {rasmSavollari.length > 0 ? (
                <RasmMashqi
                  rasmUrl={rasmUrl}
                  savollar={rasmSavollari}
                  idxlar={rasmIdxlari}
                  javoblar={javoblar}
                  javobniQoy={javobniQoy}
                  natija={natija}
                />
              ) : (
                rasmUrl && <img src={rasmUrl} alt="" style={{ maxWidth: "100%", display: "block" }} />
              )}
            </div>
            {audioPanelBorMi && (
              <div style={{ flex: "0 0 220px", display: "grid", gap: 6, padding: 8, background: "var(--sirt-2)", borderRadius: 6 }}>
                <span className="izoh">{t("kurs_audiolar_royxati")}</span>
                {audioUrl && <audio {...AUDIO_HIMOYA} onPlay={(e) => faqatBittaAudioIjro(e.target)} controls src={audioUrl} style={{ width: "100%" }} />}
                {audioUrllar.map((a) => (
                  <div key={a.id} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    {a.raqam && <span className="izoh" style={{ minWidth: 40 }}>{a.raqam}</span>}
                    <audio {...AUDIO_HIMOYA} onPlay={(e) => faqatBittaAudioIjro(e.target)} controls src={a.url} style={{ width: "100%" }} />
                  </div>
                ))}
              </div>
            )}
          </div>

          {oddiySavollar.map(([s, i]) => (
            <div key={i} style={{ marginBottom: 6 }}>
              <div className="izoh">{s.savol}</div>
              {s.variantlar && s.variantlar.length > 0 ? (
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  {s.variantlar.map((v) => (
                    <label key={v} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <input
                        type="radio"
                        name={`mashq-${mashq.id}-${i}`}
                        checked={javoblar[i] === v}
                        disabled={!!natija}
                        onChange={() => javobniQoy(i, v)}
                      />
                      {v}
                    </label>
                  ))}
                </div>
              ) : (
                <input
                  {...IMLO_OFF}
                  value={javoblar[i]}
                  disabled={!!natija}
                  onChange={(e) => javobniQoy(i, e.target.value)}
                  style={{ maxWidth: 260 }}
                />
              )}
              {natija && (
                <span style={{ marginLeft: 8 }}>{natija.natijalar[i] ? "✓" : "✗"}</span>
              )}
            </div>
          ))}
          {!natija ? (
            // O'qituvchi ko'rinishida javoblar allaqachon ochiq —
            // Tekshirish tugmasi chiqmaydi (backend javob yuborishni
            // faqat TALABAGA ruxsat beradi).
            !javoblarOchiq && (
              <button className="tugma ikkinchi" onClick={tekshir} disabled={yuklanmoqda}>
                {yuklanmoqda ? t("tekshirilmoqda") : t("tekshirish")}
              </button>
            )
          ) : (
            <div className="izoh">
              {t("band_ball")}: {natija.ball}/{natija.jami}
            </div>
          )}
          {xato && <div className="xato-xabar">{xato}</div>}
        </>
      )}
    </div>
  );
}

/** Bir nechta mashq BITTA rasmni ulashganda (2026-08-10 da qayta
 * qurilgan) — "bitta rasm turadi, uning yonida ikkita mashq".
 *
 * MUHIM: mashqlarning MATNI (dialog, grammar-box, ko'rsatma) TO'LIQ
 * saqlanadi — har mashq o'zining odatdagi `BlokMashqi` ko'rinishida
 * chiziladi, faqat ULASHILGAN RASM ular yonida BIR MARTA turadi
 * (admin tanlagan tomonda: chap/o'ng/tepa/past).
 *
 * Avvalgi versiya (2026-08-09) mashqni "fon" ko'rinishiga o'tkazib,
 * matnni yo'qotardi — foydalanuvchi buni rad etdi. */
function RasmGuruhBlok({ guruh, boshRaqam, javoblarOchiq }) {
  const { t } = useI18n();
  const [rasmUrl, setRasmUrl] = useState(null);
  const manba = guruh[0].rasm_url;
  const tomon = guruh[0].rasm_guruhi_tomoni || "chap";

  useEffect(() => {
    let bekorQilindi = false;
    let joriy = null;
    apiBlobUrl(manba)
      .then((u) => {
        if (bekorQilindi) {
          URL.revokeObjectURL(u);
          return;
        }
        joriy = u;
        setRasmUrl(u);
      })
      .catch(() => {});
    return () => {
      bekorQilindi = true;
      if (joriy) URL.revokeObjectURL(joriy);
    };
  }, [manba]);

  if (!rasmUrl) return <div className="izoh">{t("yuklanmoqda")}</div>;

  const rasm = (
    <img
      src={rasmUrl}
      alt=""
      style={{ maxWidth: "100%", display: "block", borderRadius: 6 }}
    />
  );
  const mazmun = guruh.map((m, i) => (
    <BlokMashqi key={m.id} mashq={m} raqam={boshRaqam + i} javoblarOchiq={javoblarOchiq} />
  ));

  // Chap/o'ng — ikki ustun (rasm o'z ustunida, mashqlar ikkinchisida);
  // tepa/past — ustma-ust.
  if (tomon === "chap" || tomon === "ong") {
    // `flex-basis: 0%` SHART — `auto` bo'lsa mazmun ustunining tabiiy
    // (matn bo'yicha juda katta) eni asos qilib olinadi va ikki ustun
    // konteynerga sig'may, `wrap` tufayli USTMA-UST tushib qoladi
    // (2026-08-10, haqiqiy sinovda aynan shunday bo'ldi). `minWidth`
    // esa faqat HAQIQATAN tor ekranda (mobil) pastga tushirish uchun.
    const rasmUstuni = <div style={{ flex: "0 0 38%", minWidth: 120 }}>{rasm}</div>;
    const mazmunUstuni = <div style={{ flex: "1 1 0%", minWidth: 220 }}>{mazmun}</div>;
    return (
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start", marginBottom: 8, flexWrap: "wrap" }}>
        {tomon === "chap" ? rasmUstuni : mazmunUstuni}
        {tomon === "chap" ? mazmunUstuni : rasmUstuni}
      </div>
    );
  }
  return (
    <div style={{ marginBottom: 8 }}>
      {tomon === "tepa" && <div style={{ marginBottom: 8 }}>{rasm}</div>}
      {mazmun}
      {tomon === "past" && <div style={{ marginTop: 8 }}>{rasm}</div>}
    </div>
  );
}

/** Admin/owner uchun — bitta tugunning mashqlarini boshqarish (ro'yxat,
 * o'chirish, rasm/audio biriktirish). `jsonKiritishKorinadi=false`
 * (2026-07-27) — Beginner Unit'lari ichidagi "Mashqlar" bo'limida JSON
 * o'rniga rasm/ZIP orqali AI-mashq qo'shish (2026-07-30) ishlatiladi,
 * bu yerda faqat ro'yxat+fayl biriktirish qoladi. Boshqa (flat) bo'limlar
 * uchun avvalgidek JSON+AI promt ko'rinadi. */
/** Admin uchun — bitta mashqning to'g'ri javoblarini QO'LDA (har savol
 * uchun matn maydoni) yoki Excel (.xlsx: 1-ustun savol raqami, 2-ustun
 * javob) orqali ommaviy tahrirlash (2026-07-29 talabi). */
/** RASM-FON mashqining bo'sh joylarini rasm ustida to'g'ridan-to'g'ri
 * tahrirlash (2026-08-08).
 *
 * Nega kerak: bu rejimda tasdiqlash oynasi YO'Q (sahifa darhol
 * saqlanadi), ya'ni AI xatosini tuzatadigan yagona joy shu. Joylashuv
 * `bosh_joy_aniqlash` bilan piksel aniqligida topiladi, lekin AI
 * topolmagan bo'sh joy (masalan quti turidagi) ham, ortiqcha
 * topilgani ham bo'lishi mumkin — shuning uchun QO'SHISH va O'CHIRISH
 * ham shu yerda.
 *
 * Sudrash mexanikasi `ImtihonBoshqarish.jsx: PozitsiyaAniqlagich`
 * bilan bir xil (window'ga mousemove/mouseup) — u yerda sinalgan. */
function RasmFonTahriri({ mashq, royxatniYangila, onYopish }) {
  const { t } = useI18n();
  const [rasmUrl, setRasmUrl] = useState(null);
  const [savollar, setSavollar] = useState(() => mashq.savollar.map((s) => ({ ...s })));
  const [tanlangan, setTanlangan] = useState(null);
  const [saqlanmoqda, setSaqlanmoqda] = useState(false);
  const [xato, setXato] = useState("");
  const konteynerRef = useRef(null);
  const surinishRef = useRef(null);
  const sudralganRef = useRef(false);

  useEffect(() => {
    let url = null;
    let bekorQilindi = false;
    apiBlobUrl(mashq.rasm_url).then((u) => {
      if (bekorQilindi) {
        URL.revokeObjectURL(u);
        return;
      }
      url = u;
      setRasmUrl(u);
    }).catch(() => {});
    return () => {
      bekorQilindi = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [mashq.rasm_url]);

  function pozitsiyaniQoy(i, ozgarish) {
    setSavollar((joriy) => joriy.map((s, j) => (
      j === i ? { ...s, pozitsiya: { ...s.pozitsiya, ...ozgarish } } : s
    )));
  }

  function davomEttir(e) {
    const s = surinishRef.current;
    if (!s || !konteynerRef.current) return;
    const rect = konteynerRef.current.getBoundingClientRect();
    const dx = ((e.clientX - s.boshX) / rect.width) * 100;
    const dy = ((e.clientY - s.boshY) / rect.height) * 100;
    pozitsiyaniQoy(s.idx, {
      x: Math.max(0, Math.min(100, s.bosh.x + dx)),
      y: Math.max(0, Math.min(100, s.bosh.y + dy)),
    });
  }
  function toxtat() {
    // Sudrash tugagach sichqoncha RASM ustida qo'yib yuborilsa,
    // brauzer konteynerga `click` ham yuboradi — u holda tasodifiy
    // yangi katak qo'shilib qolardi. Shu bayroq keyingi bitta
    // `click`ni yutib yuboradi.
    if (surinishRef.current) sudralganRef.current = true;
    surinishRef.current = null;
    window.removeEventListener("mousemove", davomEttir);
    window.removeEventListener("mouseup", toxtat);
  }
  function sudrashniBoshla(e, idx) {
    e.preventDefault();
    e.stopPropagation();
    setTanlangan(idx);
    surinishRef.current = { idx, boshX: e.clientX, boshY: e.clientY, bosh: { ...savollar[idx].pozitsiya } };
    window.addEventListener("mousemove", davomEttir);
    window.addEventListener("mouseup", toxtat);
  }

  // Rasmning bo'sh joyiga bosish — AI o'tkazib yuborgan bo'sh joyni
  // qo'shish (masalan quti turidagi, u hali aniqlanmaydi).
  function rasmgaBosildi(e) {
    if (sudralganRef.current) {
      sudralganRef.current = false;
      return;
    }
    if (!konteynerRef.current) return;
    const rect = konteynerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    setSavollar((joriy) => [...joriy, {
      savol: "___", togri: "",
      pozitsiya: { x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10, kenglik: 12 },
    }]);
    setTanlangan(savollar.length);
  }

  function ochir(i) {
    setSavollar((joriy) => joriy.filter((_, j) => j !== i));
    setTanlangan(null);
  }

  async function saqlash() {
    setXato("");
    setSaqlanmoqda(true);
    try {
      await api(`/api/kurslar/mashq/${mashq.id}/`, { method: "PATCH", body: { savollar } });
      royxatniYangila();
      onYopish();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setSaqlanmoqda(false);
    }
  }

  const joriy = tanlangan != null ? savollar[tanlangan] : null;

  return (
    <div style={{ marginTop: 6, marginBottom: 10, paddingLeft: 12, borderLeft: "2px solid var(--chiziq)" }}>
      <div className="izoh" style={{ marginBottom: 6 }}>{t("kurs_rasm_fon_tahrir_izoh")}</div>
      {!rasmUrl ? (
        <div className="izoh">{t("yuklanmoqda")}</div>
      ) : (
        <div
          ref={konteynerRef}
          onClick={rasmgaBosildi}
          style={{ position: "relative", display: "inline-block", maxWidth: "100%", cursor: "crosshair" }}
        >
          <img src={rasmUrl} alt="" style={{ maxWidth: "100%", display: "block" }} />
          {savollar.map((s, i) => (
            <input
              key={i}
              {...IMLO_OFF}
              readOnly
              className={`imtihon-rasm-input ${tanlangan === i ? "togri" : ""}`}
              style={{
                left: `${s.pozitsiya?.x ?? 50}%`,
                top: `${s.pozitsiya?.y ?? 50}%`,
                ...(s.pozitsiya?.kenglik ? { width: `${s.pozitsiya.kenglik}%` } : {}),
                cursor: "move",
              }}
              value={s.togri || `${i + 1}`}
              onMouseDown={(e) => sudrashniBoshla(e, i)}
              onClick={(e) => e.stopPropagation()}
            />
          ))}
        </div>
      )}

      {joriy && (
        <div style={{ display: "grid", gap: 4, marginTop: 8, maxWidth: 560 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span className="izoh" style={{ minWidth: 60 }}>#{tanlangan + 1}</span>
            <input
              type="text"
              value={joriy.savol || ""}
              placeholder={t("kurs_rasm_fon_savol_matni")}
              onChange={(e) => {
                const v = e.target.value;
                setSavollar((j) => j.map((s, k) => (k === tanlangan ? { ...s, savol: v } : s)));
              }}
              style={{ flex: 1 }}
            />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span className="izoh" style={{ minWidth: 60 }}>{t("kurs_javoblar")}</span>
            <input
              type="text"
              value={joriy.togri || ""}
              disabled={!!joriy.erkin}
              placeholder={joriy.erkin ? t("kurs_erkin_javob_izoh") : ""}
              onChange={(e) => {
                const v = e.target.value;
                setSavollar((j) => j.map((s, k) => (k === tanlangan ? { ...s, togri: v } : s)));
              }}
              style={{ flex: 1 }}
            />
            <label className="izoh" style={{ display: "flex", alignItems: "center", gap: 4, whiteSpace: "nowrap" }}>
              <input
                type="checkbox"
                checked={!!joriy.erkin}
                onChange={(e) => {
                  const v = e.target.checked;
                  setSavollar((j) => j.map((s, k) => (k === tanlangan ? { ...s, erkin: v } : s)));
                }}
              />
              {t("kurs_erkin_javob")}
            </label>
            <button className="tugma ikkinchi kichik" style={{ color: "#d33" }} onClick={() => ochir(tanlangan)}>
              {t("ochirish")}
            </button>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span className="izoh" style={{ minWidth: 60 }}>{t("kurs_rasm_fon_kenglik")}</span>
            <input
              type="range"
              min="4"
              max="60"
              step="0.5"
              value={joriy.pozitsiya?.kenglik ?? 12}
              onChange={(e) => pozitsiyaniQoy(tanlangan, { kenglik: Number(e.target.value) })}
              style={{ flex: 1 }}
            />
            <span className="izoh">{Math.round(joriy.pozitsiya?.kenglik ?? 12)}%</span>
          </div>
        </div>
      )}

      <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 8 }}>
        <button className="tugma" onClick={saqlash} disabled={saqlanmoqda}>
          {saqlanmoqda ? t("yuklanmoqda") : t("saqlash")}
        </button>
        <button className="tugma ikkinchi" onClick={onYopish}>{t("yopish")}</button>
        <span className="izoh">{savollar.length} {t("kurs_savol")}</span>
        {xato && <span className="xato-xabar">{xato}</span>}
      </div>
    </div>
  );
}

function MashqJavoblariTahriri({ mashq, royxatniYangila }) {
  const { t } = useI18n();
  const [qiymatlar, setQiymatlar] = useState(
    () => mashq.savollar.map((s) => (Array.isArray(s.togri) ? s.togri.join(", ") : (s.togri || "")))
  );
  const [erkinlar, setErkinlar] = useState(() => mashq.savollar.map((s) => !!s.erkin));
  const [saqlanmoqda, setSaqlanmoqda] = useState(false);
  const [xato, setXato] = useState("");
  const [natija, setNatija] = useState(null);

  function natijaniKorsat(d) {
    setNatija(d);
    if (d.yangilandi) royxatniYangila();
  }

  async function saqlash() {
    setXato("");
    setSaqlanmoqda(true);
    try {
      const javoblar = qiymatlar.map((v, i) => ({ raqam: i + 1, togri: v, erkin: erkinlar[i] }));
      const d = await api(`/api/kurslar/mashq/${mashq.id}/`, { method: "PATCH", body: { javoblar } });
      natijaniKorsat(d);
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setSaqlanmoqda(false);
    }
  }

  async function excelYukla(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setXato("");
    setSaqlanmoqda(true);
    try {
      const fd = new FormData();
      fd.append("fayl", fayl);
      const d = await apiForm(`/api/kurslar/mashq/${mashq.id}/javob-excel/`, { method: "POST", formData: fd });
      natijaniKorsat(d);
    } catch (e2) {
      setXato(e2.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setSaqlanmoqda(false);
    }
  }

  return (
    <div style={{ marginTop: 6, marginBottom: 10, paddingLeft: 12, borderLeft: "2px solid var(--chegara, #ccc)" }}>
      <div style={{ display: "grid", gap: 4, marginBottom: 8 }}>
        {mashq.savollar.map((s, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="izoh" style={{ minWidth: 220 }}>
              #{i + 1} {s.savol ? `— ${s.savol.slice(0, 50)}` : ""}
            </span>
            <input
              type="text"
              value={qiymatlar[i]}
              disabled={erkinlar[i]}
              onChange={(e) => {
                const v = e.target.value;
                setQiymatlar((joriy) => joriy.map((x, j) => (j === i ? v : x)));
              }}
              placeholder={erkinlar[i] ? t("kurs_erkin_javob_izoh") : t("kurs_javob_kirit")}
              style={{ flex: 1, maxWidth: 260 }}
            />
            <label className="izoh" style={{ display: "flex", alignItems: "center", gap: 4, whiteSpace: "nowrap" }}>
              <input
                type="checkbox"
                checked={erkinlar[i]}
                onChange={(e) => {
                  const v = e.target.checked;
                  setErkinlar((joriy) => joriy.map((x, j) => (j === i ? v : x)));
                }}
              />
              {t("kurs_erkin_javob")}
            </label>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <button className="tugma ikkinchi" onClick={saqlash} disabled={saqlanmoqda}>
          {t("saqlash")}
        </button>
        <label className="izoh">{t("kurs_javob_excel_yuklash")}</label>
        <input type="file" accept=".xlsx" onChange={excelYukla} disabled={saqlanmoqda} style={{ maxWidth: 160 }} />
      </div>
      {xato && <div className="xato-xabar" style={{ marginTop: 4 }}>{xato}</div>}
      {natija && (
        <div className="izoh" style={{ marginTop: 4 }}>
          {t("kurs_javob_yangilandi")}: {natija.yangilandi}
          {natija.xatolar?.length > 0 && (
            <span style={{ color: "#d33" }}>
              {" "}— {natija.xatolar.length} {t("kurs_javob_xato")}: {natija.xatolar
                .map((x) => `#${x.raqam ?? x.qator}`)
                .join(", ")}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function AdminMashqBoshqaruv({ tugunId, jsonKiritishKorinadi = true }) {
  const { t } = useI18n();
  const [royxat, setRoyxat] = useState(null);
  const [javobOchiqId, setJavobOchiqId] = useState(null);
  const [joylashuvOchiqId, setJoylashuvOchiqId] = useState(null);
  const [jsonMatn, setJsonMatn] = useState('[\n  {"matn": "", "savollar": [{"savol": "...", "togri": "..."}]}\n]');
  const [xato, setXato] = useState("");
  const [saqlanmoqda, setSaqlanmoqda] = useState(false);
  const [promtKorinadi, setPromtKorinadi] = useState(false);
  const [nusxalandi, setNusxalandi] = useState(false);
  // 2026-07-30 talabi: yagona fayl tanlash tugmasi — rasm TANLANSA
  // bitta mashq (sinxron, tez), ZIP tanlansa ICHIDAGI HAR rasm alohida
  // mashq (2-bosqichli jarayon, katta ZIP timeout'ga tushmasligi uchun).
  // Ikkalasi ham AYNAN BIR XIL AI tahliliga tayanadi (backend'da
  // `_rasmni_mashqqa_aylantir`) — faqat "bitta martami, ko'pmi" farq.
  const [mashqXato, setMashqXato] = useState("");
  const [mashqXabar, setMashqXabar] = useState("");
  // 2026-07-30 talabi: har mashqni YANGI rasm bilan almashtirish (o'sha
  // mashqning bloklari qayta hisoblanadi, o'rni/id o'zgarmaydi).
  const [qaytaYuklanayotganId, setQaytaYuklanayotganId] = useState(null);
  const [qaytaYuklashXato, setQaytaYuklashXato] = useState("");
  // 2026-07-31 talabi: mashq yaratilgach, uning audio belgisiga (audio_raqam)
  // darslikdagi audio faylni to'g'ridan-to'g'ri biriktirish.
  // 2026-08-19, foydalanuvchi talabi: avval BITTA mashq.id bo'yicha kuzatilardi -- bitta mashqda 2 audio bo'lsa (masalan 1.3 va 1.4), 1.3'ga yuklaganda IKKALA tugma ham "Yuklanmoqda..." bo'lib qolardi (qaysi RAQAMga yuklanayotgani farqlanmasdi). Endi kalit `"${mashqId}:${raqam}"` -- faqat aynan o'sha tugma holatini ko'rsatadi.
  const [audioYuklanayotganKalit, setAudioYuklanayotganKalit] = useState(null);
  const [audioOchirilayotganKalit, setAudioOchirilayotganKalit] = useState(null);
  const [audioYuklashXato, setAudioYuklashXato] = useState("");

  // ZIP jarayoni holati (rasm-bo'yicha yuklashning ko'p-sahifali varianti).
  const [zipYuklanmoqda, setZipYuklanmoqda] = useState(false);
  const [progress, setProgress] = useState(null);
  const [otganSoniya, setOtganSoniya] = useState(0);
  const [faolJarayon, setFaolJarayon] = useState(null); // {id, ishlangan_sahifa, jami_sahifa, tasdiq_kutilmoqda}
  const [bekorQilinmoqda, setBekorQilinmoqda] = useState(false);
  // 2026-08-03: tahlil tugagach avtomatik saqlanmaydi — admin shu oynada
  // ko'rib chiqib tasdiqlaydi (rasm-quti chegaralari/matn/javoblar).
  const [tasdiqJarayonId, setTasdiqJarayonId] = useState(null);
  const toxtatishRef = useRef(false);

  function promtNusxala() {
    navigator.clipboard?.writeText(AI_PROMT).then(() => {
      setNusxalandi(true);
      setTimeout(() => setNusxalandi(false), 2000);
    });
  }

  function yukla() {
    api(`/api/kurslar/${tugunId}/mashq-boshqaruv/`).then(setRoyxat).catch(() => {});
  }

  useEffect(() => {
    yukla();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tugunId]);

  // 2026-07-29 talabi: "yuklanmagan qismini qo'lda yuklash imkoni kerak".
  // Sahifa ochilganda shu tugun uchun yarim qolgan (avtomatik qayta
  // urinishlar ham tugab ketgan) jarayon bor-yo'qligi tekshiriladi.
  useEffect(() => {
    api(`/api/kurslar/${tugunId}/blok-jarayon-holati/`)
      .then((d) => setFaolJarayon(d.faol_jarayon))
      .catch(() => {});
  }, [tugunId]);

  useEffect(() => {
    if (!zipYuklanmoqda) return undefined;
    const boshlandi = Date.now();
    setOtganSoniya(0);
    const taymer = setInterval(() => {
      setOtganSoniya(Math.floor((Date.now() - boshlandi) / 1000));
    }, 1000);
    return () => clearInterval(taymer);
  }, [zipYuklanmoqda]);

  function vaqtFormat(soniya) {
    const daq = Math.floor(soniya / 60);
    const s = soniya % 60;
    return `${daq}:${String(s).padStart(2, "0")}`;
  }

  async function jarayonniBekorQil() {
    if (!faolJarayon || !window.confirm(t("kurs_blok_bekor_qilish_tasdiq"))) return;
    setBekorQilinmoqda(true);
    try {
      await api(`/api/kurslar/${tugunId}/blok-jarayon-holati/`, { method: "DELETE" });
      setFaolJarayon(null);
    } catch {
      // e'tiborsiz qoldirilsa ham xavfsiz — "Davom ettirish" tugmasi
      // ekranda qolaveradi, admin xohlasa qayta urinishi mumkin.
    } finally {
      setBekorQilinmoqda(false);
    }
  }

  // Navbatdagi BITTA sahifani band qilib ishlaydi — xatoda qayta
  // urinadi. Bir nechta nusxasi PARALLEL chaqiriladi (backend har
  // biriga alohida sahifani atomik beradi).
  async function bittaSahifaniIshla(jid) {
    const SAHIFA_URINISHLAR = 3;
    let oxirgiXato = null;
    for (let urinish = 0; urinish < SAHIFA_URINISHLAR; urinish += 1) {
      try {
        // eslint-disable-next-line no-await-in-loop
        return await api(`/api/kurslar/blok-jarayon/${jid}/sahifa/`, { method: "POST" });
      } catch (sahifaXato) {
        oxirgiXato = sahifaXato;
        if (urinish < SAHIFA_URINISHLAR - 1) {
          // eslint-disable-next-line no-await-in-loop
          await new Promise((r) => { setTimeout(r, 5000 * (urinish + 1)); });
        }
      }
    }
    throw oxirgiXato;
  }

  async function jarayonniBajar(jid, jamiSahifa, boshlangichIshlangan) {
    toxtatishRef.current = false;
    let tugadi = false;
    let oxirgiIshlangan = boshlangichIshlangan;
    setProgress({ ishlangan: boshlangichIshlangan, jami: jamiSahifa, fayl: "" });
    while (!tugadi) {
      if (toxtatishRef.current) {
        setFaolJarayon({ id: jid, ishlangan_sahifa: oxirgiIshlangan, jami_sahifa: jamiSahifa });
        return { toxtatildi: true };
      }
      const vadalar = [];
      for (let k = 0; k < PARALLEL_SAHIFA_SONI; k += 1) vadalar.push(bittaSahifaniIshla(jid));
      // eslint-disable-next-line no-await-in-loop
      const natijalar = await Promise.allSettled(vadalar);

      const xatoli = natijalar.find((n) => n.status === "rejected");
      if (xatoli) {
        setFaolJarayon({ id: jid, ishlangan_sahifa: oxirgiIshlangan, jami_sahifa: jamiSahifa });
        throw xatoli.reason;
      }

      let ishBorEdi = false;
      for (const n of natijalar) {
        const d = n.value;
        if (d.band_qilinadigan_sahifa_qolmadi) continue;
        ishBorEdi = true;
        oxirgiIshlangan = d.ishlangan_sahifa;
        setProgress({ ishlangan: d.ishlangan_sahifa, jami: d.jami_sahifa, fayl: d.joriy_fayl });
        if (d.tugadimi) tugadi = true;
      }
      if (!ishBorEdi) tugadi = true;
    }
    // 2026-08-03: tahlil tugadi — endi bazaga avtomatik YOZILMAYDI, admin
    // BlokTasdiqlash oynasida ko'rib chiqib tasdiqlashi kerak.
    return { toxtatildi: false, tasdiqKerak: true };
  }

  function yakunXabariniQoy(yakun) {
    const qismlar = [
      `${yakun.yaratilgan_mashqlar} ${t("kurs_natija_mashq")}`,
      `${yakun.kesilgan_rasmlar} ${t("kurs_blok_rasm")}`,
    ];
    if (yakun.baholanadigan_savollar) {
      qismlar.push(`${yakun.baholanadigan_savollar} ${t("kurs_blok_savol")}`);
    }
    if (yakun.wordlist_soni) {
      qismlar.push(`${yakun.wordlist_soni} ${t("kurs_blok_wordlist_soz")}`);
    }
    let xabarMatni = qismlar.join(", ");
    if (yakun.xato_sahifalar?.length) {
      xabarMatni += ` — ⚠ ${yakun.xato_sahifalar.length} ${t("kurs_zip_xato_sahifa")}: ${yakun.xato_sahifalar
        .map((x) => x.fayl.split("/").pop())
        .join(", ")}`;
    }
    setMashqXabar(xabarMatni);
  }

  async function zipYukla(fayl) {
    setMashqXato("");
    setMashqXabar("");
    setZipYuklanmoqda(true);
    setProgress(null);
    try {
      const fd = new FormData();
      fd.append("zip_fayl", fayl);
      const boshlash = await apiForm(`/api/kurslar/${tugunId}/blok-zip/`, {
        method: "POST",
        formData: fd,
      });
      const natija = await jarayonniBajar(boshlash.jarayon_id, boshlash.jami_sahifa, 0);
      if (natija.toxtatildi) {
        setMashqXabar(t("kurs_blok_toxtatildi"));
      } else {
        setFaolJarayon({
          id: boshlash.jarayon_id, ishlangan_sahifa: boshlash.jami_sahifa,
          jami_sahifa: boshlash.jami_sahifa, tasdiq_kutilmoqda: true,
        });
        setTasdiqJarayonId(boshlash.jarayon_id);
      }
    } catch (e2) {
      setMashqXato(e2.data?.detail || t("xato_yuz_berdi"));
      if (e2.status === 409) setFaolJarayon(null);
    } finally {
      setZipYuklanmoqda(false);
      setProgress(null);
    }
  }

  async function jarayonniDavomEttir() {
    if (!faolJarayon) return;
    setMashqXato("");
    setMashqXabar("");
    setZipYuklanmoqda(true);
    setProgress(null);
    try {
      const jid = faolJarayon.id;
      const jamiSahifa = faolJarayon.jami_sahifa;
      const natija = await jarayonniBajar(jid, jamiSahifa, faolJarayon.ishlangan_sahifa);
      if (natija.toxtatildi) {
        setMashqXabar(t("kurs_blok_toxtatildi"));
      } else {
        setFaolJarayon({
          id: jid, ishlangan_sahifa: jamiSahifa, jami_sahifa: jamiSahifa, tasdiq_kutilmoqda: true,
        });
        setTasdiqJarayonId(jid);
      }
    } catch (e2) {
      setMashqXato(e2.data?.detail || t("xato_yuz_berdi"));
      if (e2.status === 409) setFaolJarayon(null);
    } finally {
      setZipYuklanmoqda(false);
      setProgress(null);
    }
  }

  // 2026-08-05, foydalanuvchi qarori: bitta rasm yuklaganda ham xuddi
  // ZIP kabi tasdiqlash oynasi chiqishi kerak (avval to'g'ridan-to'g'ri,
  // tasdiqlashsiz saqlanardi) — shuning uchun rasm ham, ZIP ham BIR XIL
  // `zipYukla` oqimiga yuboriladi (backend bitta rasmni xotirada ZIP'ga
  // o'rab, xuddi shu jarayon orqali ishlaydi).
  function faylTanlandi(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    zipYukla(fayl);
  }

  async function qoshish() {
    setXato("");
    let mashqlar;
    try {
      mashqlar = JSON.parse(jsonMatn);
    } catch {
      setXato(t("kurs_json_xato"));
      return;
    }
    setSaqlanmoqda(true);
    try {
      await api(`/api/kurslar/${tugunId}/mashq-boshqaruv/`, { method: "POST", body: { mashqlar } });
      yukla();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setSaqlanmoqda(false);
    }
  }

  async function ochir(id) {
    if (!window.confirm(t("kurs_mashq_ochirish_tasdiq"))) return;
    await api(`/api/kurslar/mashq/${id}/`, { method: "DELETE" }).catch(() => {});
    yukla();
  }

  async function rasmYukla(id, e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    const fd = new FormData();
    fd.append("rasm", fayl);
    await apiForm(`/api/kurslar/mashq/${id}/rasm-boshqaruv/`, { method: "PATCH", formData: fd }).catch(() => {});
    yukla();
  }

  async function rasmniOchir(id) {
    if (!window.confirm(t("kurs_mashq_rasmini_ochirish_tasdiq"))) return;
    await api(`/api/kurslar/mashq/${id}/rasm-boshqaruv/`, { method: "DELETE" }).catch(() => {});
    yukla();
  }

  async function mashqniQaytaYukla(id, e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    if (!window.confirm(t("kurs_mashq_qayta_yuklash_tasdiq"))) return;
    setQaytaYuklashXato("");
    setQaytaYuklanayotganId(id);
    try {
      const fd = new FormData();
      fd.append("rasm", fayl);
      await apiForm(`/api/kurslar/mashq/${id}/qayta-yuklash/`, { method: "POST", formData: fd });
      yukla();
    } catch (e2) {
      setQaytaYuklashXato(e2.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setQaytaYuklanayotganId(null);
    }
  }

  function mashqAudioRaqamlari(m) {
    const raqamlar = [];
    for (const b of m.bloklar || []) {
      if (b.audio_raqam && !raqamlar.includes(b.audio_raqam)) raqamlar.push(b.audio_raqam);
    }
    return raqamlar;
  }

  async function mashqgaAudioYukla(id, e, raqam) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    const kalit = `${id}:${raqam || ""}`;
    setAudioYuklashXato("");
    setAudioYuklanayotganKalit(kalit);
    try {
      const fd = new FormData();
      fd.append("audio", fayl);
      // 2026-08-16, foydalanuvchi talabi: bitta sahifada bir nechta
      // audio belgisi (masalan 1.1 VA 1.2) bo'lsa, admin QAYSI trekka
      // yuklayotganini aniq ko'rsatishi kerak — aks holda backend doim
      // BIRINCHI raqamga yozardi, qolgan treklar umuman yuklanmasdi.
      if (raqam) fd.append("raqam", raqam);
      const d = await apiForm(`/api/kurslar/mashq/${id}/blok-audio-yuklash/`, { method: "POST", formData: fd });
      // 2026-08-08: bu fayl markazda allaqachon bor edi — diskka yangi
      // nusxa yozilmadi, mavjudi ishlatildi. Admin qaysi mashqdan
      // olinganini bilib tursin.
      const q = d?.audio_qayta_ishlatildi;
      setMashqXabar(q ? `${t("kurs_audio_qayta_ishlatildi")} #${q.mashq_tartib}` : "");
      yukla();
    } catch (e2) {
      setAudioYuklashXato(e2.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setAudioYuklanayotganKalit(null);
    }
  }

  async function mashqdanAudioniOchir(id, raqam) {
    if (!window.confirm(t("kurs_audio_ochirish_tasdiq"))) return;
    const kalit = `${id}:${raqam || ""}`;
    setAudioYuklashXato("");
    setAudioOchirilayotganKalit(kalit);
    try {
      const soralar = raqam ? `?raqam=${encodeURIComponent(raqam)}` : "";
      await api(`/api/kurslar/mashq/${id}/blok-audio-yuklash/${soralar}`, { method: "DELETE" });
      yukla();
    } catch (e2) {
      setAudioYuklashXato(e2.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setAudioOchirilayotganKalit(null);
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 10, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <label className="tugma ikkinchi" style={{ cursor: "pointer" }}>
          {zipYuklanmoqda ? t("yuklanmoqda") : t("kurs_rasmdan_mashq_qoshish")}
          <input
            type="file"
            accept="image/*,.zip"
            onChange={faylTanlandi}
            disabled={zipYuklanmoqda}
            style={{ display: "none" }}
          />
        </label>
        {faolJarayon && !zipYuklanmoqda && (
          <>
            {faolJarayon.tasdiq_kutilmoqda ? (
              <button
                className="tugma ikkinchi kichik"
                onClick={() => setTasdiqJarayonId(faolJarayon.id)}
              >
                {t("kurs_blok_korib_chiqish")} ({faolJarayon.jami_sahifa} {t("kurs_blok_tasdiq_sahifa").toLowerCase()})
              </button>
            ) : (
              <button className="tugma ikkinchi kichik" onClick={jarayonniDavomEttir}>
                {t("kurs_blok_davom_ettirish")} ({faolJarayon.ishlangan_sahifa}/{faolJarayon.jami_sahifa})
              </button>
            )}
            <button
              className="tugma ikkinchi kichik"
              style={{ color: "#d33" }}
              onClick={jarayonniBekorQil}
              disabled={bekorQilinmoqda}
            >
              {t("kurs_blok_bekor_qilish")}
            </button>
          </>
        )}
        {mashqXato && <span className="xato-xabar">{mashqXato}</span>}
        {mashqXabar && <span className="izoh">✓ {mashqXabar}</span>}
        {qaytaYuklashXato && <span className="xato-xabar">{qaytaYuklashXato}</span>}
        {audioYuklashXato && <span className="xato-xabar">{audioYuklashXato}</span>}
      </div>
      {progress && (
        <div style={{ marginBottom: 10 }}>
          <div className="izoh">
            {t("kurs_blok_progress")} {progress.ishlangan}/{progress.jami}
            {progress.fayl ? ` — ${progress.fayl}` : ""}
          </div>
          <div style={{ height: 6, background: "var(--sirt-2)", borderRadius: 3, marginTop: 4 }}>
            <div
              style={{
                width: `${(progress.ishlangan / progress.jami) * 100}%`,
                height: "100%",
                background: "var(--sariq-toq)",
                borderRadius: 3,
                transition: "width .3s",
              }}
            />
          </div>
        </div>
      )}
      {/* 2026-07-29 talabi: "fayl yuklanib bo'lmagungacha saytda hech
          qanday amal bajarish mumkin bo'lmasin" — ZIP ko'p sahifali
          bo'lganda butun sahifani qoplaydi. */}
      {zipYuklanmoqda && (
        <div className="blok-yuklash-qoplama">
          <div className="blok-yuklash-karta">
            <div className="blok-yuklash-spinner" aria-hidden="true" />
            <div style={{ fontWeight: 700 }}>{t("kurs_blok_yuklash_band")}</div>
            <div className="izoh">{t("kurs_blok_otgan_vaqt")}: {vaqtFormat(otganSoniya)}</div>
            {progress && (
              <div className="izoh blok-yuklash-fayl" title={progress.fayl || undefined}>
                {progress.ishlangan}/{progress.jami}
                {progress.fayl ? ` — ${progress.fayl}` : ""}
              </div>
            )}
            <button
              type="button"
              className="tugma ikkinchi"
              style={{ marginTop: 10 }}
              onClick={() => {
                toxtatishRef.current = true;
                setZipYuklanmoqda(false);
              }}
            >
              {t("kurs_blok_toxtatish")}
            </button>
          </div>
        </div>
      )}
      {tasdiqJarayonId && (
        <BlokTasdiqlash
          jarayonId={tasdiqJarayonId}
          onYakunlandi={(natija) => {
            setTasdiqJarayonId(null);
            setFaolJarayon(null);
            yakunXabariniQoy(natija);
            yukla();
          }}
          onBekor={() => setTasdiqJarayonId(null)}
        />
      )}
      {royxat && royxat.length > 0 && (
        <div style={{ display: "grid", gap: 6, marginBottom: 10 }}>
          {royxat.map((m) => (
            <div key={m.id}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span className="izoh">
                  #{m.tartib} — {m.matn ? m.matn.slice(0, 40) : ""} ({m.savollar.length} {t("kurs_savol")})
                  {m.rasm_url ? " 🖼️" : ""}
                  {m.audio_url ? " 🔊" : ""}
                  {m.audiolar?.length ? ` 🔊×${m.audiolar.length}` : ""}
                  {/* AI sahifada audio belgisini ko'rgan, lekin fayl hali
                      biriktirilmagan (2026-08-07) — admin unutmasin. */}
                  {m.audio_kerak && !m.audio_url && !m.audiolar?.length ? " ⚠🔇" : ""}
                </span>
                <input type="file" accept="image/*" onChange={(e) => rasmYukla(m.id, e)} style={{ maxWidth: 140 }} />
                {m.rasm_url && (
                  <button
                    className="tugma ikkinchi"
                    style={{ color: "#d33" }}
                    onClick={() => rasmniOchir(m.id)}
                  >
                    🗑️ {t("kurs_rasm")}
                  </button>
                )}
                {m.savollar.length > 0 && (
                  <button
                    className="tugma ikkinchi"
                    onClick={() => setJavobOchiqId((joriy) => (joriy === m.id ? null : m.id))}
                  >
                    {javobOchiqId === m.id ? t("yopish") : t("kurs_javoblar")}
                  </button>
                )}
                {/* Rasm-fon mashqi (2026-08-08): fon rasmi bor, bloklar
                    yo'q. Faqat shu ko'rinishda bo'sh joylarni rasm
                    ustida surib tuzatish mantiqan to'g'ri keladi. */}
                {m.rasm_url && !m.bloklar?.length && (
                  <button
                    className="tugma ikkinchi"
                    onClick={() => setJoylashuvOchiqId((joriy) => (joriy === m.id ? null : m.id))}
                  >
                    {joylashuvOchiqId === m.id ? t("yopish") : t("kurs_rasm_fon_tahrirlash")}
                  </button>
                )}
                <label className="tugma ikkinchi" style={{ cursor: "pointer" }}>
                  {qaytaYuklanayotganId === m.id ? t("yuklanmoqda") : t("kurs_mashq_qayta_yuklash")}
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => mashqniQaytaYukla(m.id, e)}
                    disabled={qaytaYuklanayotganId === m.id}
                    style={{ display: "none" }}
                  />
                </label>
                {/* 2026-08-07: `audio_kerak` — rasm-fon rejimi uchun.
                    U yerda `bloklar` bo'sh, ya'ni `mashqAudioRaqamlari`
                    har doim bo'sh qaytaradi va tugma ko'rinmay qolardi. */}
                {(() => {
                  const raqamlar = mashqAudioRaqamlari(m);
                  const mavjudRaqamlar = new Set((m.audiolar || []).map((a) => a.raqam || ""));
                  if (raqamlar.length > 1) {
                    // Bir nechta audio belgisi bor — har biriga ALOHIDA
                    // tugma, aks holda backend doim BIRINCHI raqamga
                    // yozardi va qolgan treklar yuklanmay qolardi.
                    // 2026-08-19: holat endi mashq+RAQAM bo'yicha
                    // kuzatiladi (avval faqat mashq bo'yicha edi — bitta
                    // trekka yuklaganda IKKALA tugma ham "Yuklanmoqda..."
                    // bo'lib qolar, xato chiqsa abadiy shu holatda
                    // qotib qolardi). Fayl allaqachon biriktirilgan
                    // bo'lsa — yoniga 🗑️ o'chirish tugmasi qo'shiladi.
                    return raqamlar.map((r) => {
                      const kalit = `${m.id}:${r}`;
                      return (
                        <span key={r} style={{ display: "inline-flex", gap: 4 }}>
                          <label className="tugma ikkinchi" style={{ cursor: "pointer" }}>
                            {audioYuklanayotganKalit === kalit ? t("yuklanmoqda") : `🎵 ${r}`}
                            <input
                              type="file"
                              accept="audio/*"
                              onChange={(e) => mashqgaAudioYukla(m.id, e, r)}
                              disabled={audioYuklanayotganKalit === kalit}
                              style={{ display: "none" }}
                            />
                          </label>
                          {mavjudRaqamlar.has(r) && (
                            <button
                              type="button"
                              className="tugma ikkinchi"
                              style={{ color: "#d33" }}
                              title={t("kurs_audio_ochirish")}
                              disabled={audioOchirilayotganKalit === kalit}
                              onClick={() => mashqdanAudioniOchir(m.id, r)}
                            >
                              🗑️
                            </button>
                          )}
                        </span>
                      );
                    });
                  }
                  if (raqamlar.length === 1 || m.audio_kerak) {
                    const yagonaRaqam = raqamlar[0] || "";
                    const kalit = `${m.id}:${yagonaRaqam}`;
                    const borMi = m.audio_url || mavjudRaqamlar.has(yagonaRaqam);
                    return (
                      <span style={{ display: "inline-flex", gap: 4 }}>
                        <label className="tugma ikkinchi" style={{ cursor: "pointer" }}>
                          {audioYuklanayotganKalit === kalit ? t("yuklanmoqda") : t("kurs_mashq_audio_yuklash")}
                          <input
                            type="file"
                            accept="audio/*"
                            onChange={(e) => mashqgaAudioYukla(m.id, e, yagonaRaqam)}
                            disabled={audioYuklanayotganKalit === kalit}
                            style={{ display: "none" }}
                          />
                        </label>
                        {borMi && (
                          <button
                            type="button"
                            className="tugma ikkinchi"
                            style={{ color: "#d33" }}
                            title={t("kurs_audio_ochirish")}
                            disabled={audioOchirilayotganKalit === kalit}
                            onClick={() => mashqdanAudioniOchir(m.id, yagonaRaqam)}
                          >
                            🗑️
                          </button>
                        )}
                      </span>
                    );
                  }
                  return <span className="izoh">{t("kurs_mashq_audio_yoq")}</span>;
                })()}
                <button className="tugma ikkinchi" style={{ color: "#d33" }} onClick={() => ochir(m.id)}>
                  {t("ochirish")}
                </button>
              </div>
              {javobOchiqId === m.id && (
                <MashqJavoblariTahriri mashq={m} royxatniYangila={yukla} />
              )}
              {joylashuvOchiqId === m.id && (
                <RasmFonTahriri
                  mashq={m}
                  royxatniYangila={yukla}
                  onYopish={() => setJoylashuvOchiqId(null)}
                />
              )}
            </div>
          ))}
        </div>
      )}
      {!jsonKiritishKorinadi ? (
        (!royxat || royxat.length === 0) && <div className="izoh">{t("kurs_mashq_yoq")}</div>
      ) : (
        <>
          <div style={{ marginBottom: 8 }}>
            <button className="tugma ikkinchi" onClick={() => setPromtKorinadi((v) => !v)}>
              {promtKorinadi ? t("mashq_promt_yashirish") : t("mashq_promt_korsatish")}
            </button>
            {promtKorinadi && (
              <div style={{ marginTop: 8 }}>
                <p className="izoh" style={{ marginTop: 0 }}>{t("kurs_mashq_promt_izoh")}</p>
                <textarea
                  readOnly
                  rows={8}
                  value={AI_PROMT}
                  style={{ width: "100%", fontFamily: "monospace", fontSize: 11 }}
                />
                <button className="tugma ikkinchi" style={{ marginTop: 6 }} onClick={promtNusxala}>
                  {nusxalandi ? t("nusxalandi") : t("nusxalash")}
                </button>
              </div>
            )}
          </div>
          <textarea
            rows={6}
            value={jsonMatn}
            onChange={(e) => setJsonMatn(e.target.value)}
            style={{ width: "100%", fontFamily: "monospace", fontSize: 12 }}
          />
          <div style={{ marginTop: 6 }}>
            <button className="tugma ikkinchi" onClick={qoshish} disabled={saqlanmoqda}>
              {t("kurs_mashq_qoshish")}
            </button>
            {xato && <span className="xato-xabar" style={{ marginLeft: 8 }}>{xato}</span>}
          </div>
        </>
      )}
    </div>
  );
}

/** Mashqlar paneli — talaba uchun yechish, admin uchun boshqarish. */
/** 2026-08-18, foydalanuvchi talabi: o'qituvchi kurslardagi mashqlarni
 * O'QUVCHI KABI ko'rsin (mashq qo'shish/tahrirlash kerak emas). Avval bu
 * yerda faqat `talabaMi` tekshirilardi — o'qituvchi ADMIN paneliga
 * yuborilar, u esa backendda 403 qaytarar va xato `catch(() => {})` bilan
 * yutilib, o'qituvchiga BO'SH panel ko'rinardi. */
function MashqPaneli({ tugunId, talabaMi, oqituvchiMi, jsonKiritishKorinadi = true }) {
  const korinishMi = talabaMi || oqituvchiMi;
  const { t } = useI18n();
  const [mashqlar, setMashqlar] = useState(null);
  const [xato, setXato] = useState("");

  useEffect(() => {
    if (!korinishMi) return;
    api(`/api/kurslar/${tugunId}/mashqlar/`)
      .then(setMashqlar)
      .catch((e) => setXato(e.data?.detail || t("xato_yuz_berdi")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tugunId, korinishMi]);

  if (!korinishMi) {
    return <AdminMashqBoshqaruv tugunId={tugunId} jsonKiritishKorinadi={jsonKiritishKorinadi} />;
  }

  if (xato) return <div className="xato-xabar">{xato}</div>;
  if (!mashqlar) return <div className="izoh">{t("yuklanmoqda")}</div>;
  if (mashqlar.length === 0) return <div className="izoh">{t("kurs_mashq_yoq")}</div>;

  // 2026-07-28: `bloklar` to'ldirilgan bo'lsa — sahifa qaytadan quriladi
  // (BlokMashqi), aks holda eski ko'rinish (sahifa rasmi + ustida
  // pozitsiyalangan input'lar). Ikki format yonma-yon yashaydi, chunki
  // eski usulda yuklangan kontent bor.
  //
  // 2026-08-10: ketma-ket kelib bir xil `rasm_guruhi_id`ga ega mashqlar
  // (rasm ulashilgan) BITTA `RasmGuruhBlok`ga birlashtiriladi — rasm
  // bir marta, admin tanlagan tomonda chiqadi, mashqlarning MATNI esa
  // o'z `BlokMashqi` ko'rinishida to'liq qoladi.
  //
  // DIQQAT: bu tekshiruv `bloklar`dan OLDIN turishi SHART — ulashilgan
  // mashqlarda ham bloklar (matn) bo'ladi, aks holda ular guruhlanmay,
  // rasmsiz alohida chiqib ketardi.
  //
  // 2026-08-10, HAQIQIY SINOVDA topilgan xato: ulashilgan mashqlar
  // ro'yxatda YONMA-YON TURMASLIGI mumkin (masalan tartib 1 va 4 — biri
  // sahifa boshida, ikkinchisi oxirida). Avval faqat KETMA-KET kelganlar
  // guruhlanardi, natijada ulashilgan rasm umuman ko'rinmasdi. Endi
  // guruh a'zolari butun ro'yxatdan yig'iladi va BIRINCHISINING o'rnida
  // birga chiziladi.
  const guruhlar = new Map();
  for (const m of mashqlar) {
    if (!m.rasm_guruhi_id) continue;
    if (!guruhlar.has(m.rasm_guruhi_id)) guruhlar.set(m.rasm_guruhi_id, []);
    guruhlar.get(m.rasm_guruhi_id).push(m);
  }

  const bloklar = [];
  const chizilgan = new Set();
  let raqam = 1;
  for (const m of mashqlar) {
    if (chizilgan.has(m.id)) continue;
    const guruh = m.rasm_guruhi_id ? guruhlar.get(m.rasm_guruhi_id) : null;
    if (guruh && guruh.length > 1) {
      guruh.forEach((x) => chizilgan.add(x.id));
      bloklar.push(
        <RasmGuruhBlok
          key={`guruh-${m.rasm_guruhi_id}`}
          guruh={guruh}
          boshRaqam={raqam}
          javoblarOchiq={oqituvchiMi}
        />,
      );
      raqam += guruh.length;
      continue;
    }
    chizilgan.add(m.id);
    if (m.bloklar?.length) {
      bloklar.push(<BlokMashqi key={m.id} mashq={m} raqam={raqam} javoblarOchiq={oqituvchiMi} />);
    } else {
      bloklar.push(<TalabaMashqi key={m.id} mashq={m} raqam={raqam} javoblarOchiq={oqituvchiMi} />);
    }
    raqam += 1;
  }

  return <div>{bloklar}</div>;
}

/** So'zlarni tarjima kiritib mashq qilish (2026-07-27, foydalanuvchi
 * talabi — "kitobdagidek" so'z ro'parasida javob yozadigan joy bo'lsin).
 * Tekshirish MIJOZ tomonida (backend so'rovi shart emas) — chunki `uz`
 * tarjimasi allaqachon `/sozlar/` javobida keladi (o'yinlar ham xuddi
 * shu ma'lumotdan foydalanadi), shuning uchun bu yerda yashirishning
 * ma'nosi yo'q. */
function SozlarniYozishMashqi({ sozlar }) {
  const { t } = useI18n();
  const [javoblar, setJavoblar] = useState(() => sozlar.map(() => ""));
  const [tekshirilganmi, setTekshirilganmi] = useState(false);

  function javobniQoy(i, qiymat) {
    setJavoblar((j) => j.map((x, idx) => (idx === i ? qiymat : x)));
  }

  function togriMi(i) {
    return javoblar[i].trim().toLowerCase() === sozlar[i].uz.trim().toLowerCase();
  }

  return (
    <div style={{ display: "grid", gap: 6, marginBottom: 14, maxWidth: 420 }}>
      {sozlar.map((s, i) => (
        <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontWeight: 600, minWidth: 100 }}>{s.en}</span>
          <input
            {...IMLO_OFF}
            value={javoblar[i]}
            disabled={tekshirilganmi}
            onChange={(e) => javobniQoy(i, e.target.value)}
            style={{ flex: 1 }}
          />
          {tekshirilganmi && (
            <span style={togriMi(i) ? { color: "var(--yaxshi)" } : { color: "var(--xato)" }}>
              {togriMi(i) ? "✓" : `✗ ${s.uz}`}
            </span>
          )}
        </div>
      ))}
      <button className="tugma ikkinchi" onClick={() => setTekshirilganmi(true)} disabled={tekshirilganmi}>
        {t("tekshirish")}
      </button>
    </div>
  );
}

/** "Vocabulary" bo'limi ko'rinishi (2026-07-27, ikkinchi marta qayta
 * ishlab chiqildi) — grammatika qisqa xulosasi (bo'lsa) + so'zlarni
 * tarjima yozib mashq qilish. O'yinlar 2026-08-21'dan buyon BU YERDA
 * emas, Unit'ning alohida "Games" bo'limida (`GamesKorinishi`) — shu
 * Unit'ning aynan shu so'zlaridan foydalanadi. */
function VocabularyKorinishi({ tugunId, matn }) {
  const { t } = useI18n();
  const [sozlar, setSozlar] = useState(null);

  useEffect(() => {
    api(`/api/kurslar/${tugunId}/sozlar/`).then(setSozlar).catch(() => setSozlar([]));
  }, [tugunId]);

  if (!sozlar) return <div className="izoh">{t("yuklanmoqda")}</div>;

  return (
    <div>
      {matn && (
        <div className="mashq-passage" style={{ whiteSpace: "pre-wrap", marginBottom: 12 }}>
          {matn}
        </div>
      )}
      {sozlar.length === 0 ? (
        <div className="izoh">{t("kurs_wordlist_yoq")}</div>
      ) : (
        <SozlarniYozishMashqi sozlar={sozlar} />
      )}
    </div>
  );
}

/** "Games" bo'limi ko'rinishi (2026-08-21, foydalanuvchi talabi) —
 * O'yinlar bo'limidagi 4 ta so'z o'yini, FAQAT shu Unit'ning
 * Vocabulary'sidagi so'zlar bilan. `vocabTugunId` — birodar Vocabulary
 * tugunining id'si (bu "games" tuguni o'zi so'z saqlamaydi, o'sha
 * yerdan o'qiydi — qarang `Tugun` komponentidagi hisoblash). */
function GamesKorinishi({ vocabTugunId }) {
  const { t } = useI18n();
  const [sozlar, setSozlar] = useState(null);
  const [oyin, setOyin] = useState(null);
  const [oyinKey, setOyinKey] = useState(0);
  // 2026-08-21, foydalanuvchi talabi: "faqat shu Unit" / "barcha
  // Unitlar" (bu Unit + undan OLDINGI Unitlar) vklyuchateli.
  const [jamlanganMi, setJamlanganMi] = useState(false);

  useEffect(() => {
    if (!vocabTugunId) {
      setSozlar([]);
      return;
    }
    setSozlar(null);
    const soralgan = jamlanganMi ? `?jamlangan=1` : "";
    api(`/api/kurslar/${vocabTugunId}/sozlar/${soralgan}`).then(setSozlar).catch(() => setSozlar([]));
  }, [vocabTugunId, jamlanganMi]);

  if (!sozlar) return <div className="izoh">{t("yuklanmoqda")}</div>;

  if (oyin) {
    // `key={oyinKey}` — "qayta o'ynash" bosilganda komponent qayta
    // MOUNT bo'lib, ichki holat (ball, joriy savol) toza boshlanadi.
    const qaytaOynash = () => setOyinKey((k) => k + 1);
    const orqaga = () => setOyin(null);
    const Komponent = {
      juftini_top: JuftiniTopOyini,
      flashcard: FlashcardOyini,
      speed_quiz: SpeedQuizOyini,
      unscramble: UnscrambleOyini,
    }[oyin];
    return (
      <Komponent
        key={oyinKey}
        sozlar={sozlar}
        t={t}
        onQaytaOynash={qaytaOynash}
        onBoshqaDaraja={orqaga}
      />
    );
  }

  return (
    <div>
      <div className="tab-guruh" style={{ marginBottom: 10 }}>
        <button className={!jamlanganMi ? "aktiv" : undefined} onClick={() => setJamlanganMi(false)}>
          {t("kurs_games_shu_unit")}
        </button>
        <button className={jamlanganMi ? "aktiv" : undefined} onClick={() => setJamlanganMi(true)}>
          {t("kurs_games_barcha_unit")}
        </button>
      </div>
      {sozlar.length === 0 ? (
        <div className="izoh">{t("kurs_wordlist_yoq")}</div>
      ) : (
        <div className="tanlov-royxat">
          <button className="tanlov-tugma" onClick={() => setOyin("juftini_top")}>
            {t("juftini_top")}
          </button>
          <button className="tanlov-tugma" onClick={() => setOyin("flashcard")}>
            {t("flashcard_oyin")}
          </button>
          <button className="tanlov-tugma" onClick={() => setOyin("speed_quiz")}>
            {t("speed_quiz_oyin")}
          </button>
          <button className="tanlov-tugma" onClick={() => setOyin("unscramble")}>
            {t("unscramble_oyin")}
          </button>
        </div>
      )}
    </div>
  );
}

/** Admin/owner uchun — bitta Unit'ning IKKALA bo'limini (Mashqlar,
 * Vocabulary) BITTA harakatda ZIP orqali yuklash (2026-07-27, foydalanuvchi
 * talabi — "unit uchun bitta tugma bo'lsin"; 2026-07-28: qo'lda-JSON
 * kiritish variantI OLIB TASHLANDI, ZIP+AI yagona yo'l qoldi — u
 * ancha tezroq va endi haqiqiy ZIP bilan sinovdan o'tgan). */
// 2026-07-29da 3 edi (tezlik uchun parallel yuborish — har so'rov
// backend'da ATOMIK ravishda alohida sahifa oladi, shuning uchun
// mantiqan xavfsiz). 2026-08-03da BITTAGA tushirildi (foydalanuvchi
// talabi, o'lchangan sabab bilan): PDF sahifasini render qilish
// xotirada o'nlab MB egallaydi va 3 parallel so'rov 512 MB'lik Render
// instansini OOM'ga olib borardi — worker o'lib, frontend faqat umumiy
// "Xatolik yuz berdi"ni ko'rsatardi. Ketma-ket yuborish sekinroq, lekin
// xotira cho'qqisi 3 barobar past va yuklash oxirigacha yetadi.
const PARALLEL_SAHIFA_SONI = 1;

// 2026-07-29 talabi: "Elementary...Upper-Intermediate uchun Unit sonini
// admin belgilashi" (keyinroq Beginner ham shu ro'yxatga qo'shildi —
// qattiq kodlangan 14 ta Headway Unit'i bekor qilindi) — courses/views.py
// dagi `UNIT_YARATISH_MUMKIN_DARAJALAR` bilan BIR XIL ro'yxat bo'lishi kerak.
const UNIT_YARATISH_MUMKIN_DARAJALAR = new Set([
  "beginner", "elementary", "pre_intermediate", "intermediate", "upper_intermediate",
]);

/** Admin uchun — Elementary...Upper-Intermediate darajasida Unit soni
 * kiritib, bir martalik Unit-asosli tuzilma yaratish (2026-07-29). Daraja
 * ostida allaqachon Unit (`unit_darsi=True`) bo'lsa, bu komponent umuman
 * chiqarilmaydi (Tugun'dagi shart) — qayta bosib yuborishning oldi shu
 * yo'l bilan olinadi. */
function AdminDarajaUnitYaratish({ darajaId, royxatniYangila }) {
  const { t } = useI18n();
  const [unitSoni, setUnitSoni] = useState("10");
  const [xato, setXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);

  async function yarat() {
    const son = parseInt(unitSoni, 10);
    if (!Number.isInteger(son) || son < 1 || son > 50) {
      setXato(t("kurs_unit_soni_notogri"));
      return;
    }
    if (!window.confirm(t("kurs_unit_yaratish_tasdiq").replace("{son}", son))) return;
    setXato("");
    setYuklanmoqda(true);
    try {
      await api(`/api/kurslar/${darajaId}/daraja-unit-yaratish/`, {
        method: "POST",
        body: { unit_soni: son },
      });
      royxatniYangila();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
      {yuklanmoqda && <BandQoplamasi matn={t("kurs_unit_yaratish")} />}
      <span className="izoh">{t("kurs_unit_soni_kirit")}</span>
      <input
        type="number"
        min="1"
        max="50"
        value={unitSoni}
        onChange={(e) => setUnitSoni(e.target.value)}
        style={{ width: 70 }}
        disabled={yuklanmoqda}
      />
      <button className="tugma ikkinchi" onClick={yarat} disabled={yuklanmoqda}>
        {t("kurs_unit_yaratish")}
      </button>
      {xato && <span className="xato-xabar">{xato}</span>}
    </div>
  );
}

/** Admin uchun — Unitlar ALLAQACHON yaratilgan darajada: yana Unit
 * qo'shish (oxiriga) yoki ENG OXIRGI Unitni o'chirish (2026-07-30
 * talabi). Faqat oxirgi Unit, va faqat u BO'SH bo'lsa o'chiriladi —
 * backend buni tekshiradi, xato bo'lsa aniq xabar qaytaradi. */
function AdminUnitSoniBoshqarish({ darajaId, royxatniYangila }) {
  const { t } = useI18n();
  const [unitSoni, setUnitSoni] = useState("5");
  const [xato, setXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [ochirilmoqda, setOchirilmoqda] = useState(false);

  async function qoshish() {
    const son = parseInt(unitSoni, 10);
    if (!Number.isInteger(son) || son < 1 || son > 50) {
      setXato(t("kurs_unit_soni_notogri"));
      return;
    }
    setXato("");
    setYuklanmoqda(true);
    try {
      await api(`/api/kurslar/${darajaId}/daraja-unit-yaratish/`, {
        method: "POST",
        body: { unit_soni: son },
      });
      royxatniYangila();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  // 2026-08-10 talabi: yuqoridagi son maydonida nechi bo'lsa, OXIRIDAN
  // shuncha Unit o'chiriladi (avval har doim atigi 1 ta o'chirilardi).
  async function oxirginiOchir() {
    const son = parseInt(unitSoni, 10);
    if (!Number.isInteger(son) || son < 1 || son > 50) {
      setXato(t("kurs_unit_soni_notogri"));
      return;
    }
    if (!window.confirm(t("kurs_oxirgi_unit_ochirish_tasdiq").replace("{son}", son))) return;
    setXato("");
    setOchirilmoqda(true);
    try {
      await api(`/api/kurslar/${darajaId}/daraja-unit-yaratish/?soni=${son}`, { method: "DELETE" });
      royxatniYangila();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setOchirilmoqda(false);
    }
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
      {(yuklanmoqda || ochirilmoqda) && <BandQoplamasi />}
      <span className="izoh">{t("kurs_yana_unit_qosh")}</span>
      <input
        type="number"
        min="1"
        max="50"
        value={unitSoni}
        onChange={(e) => setUnitSoni(e.target.value)}
        style={{ width: 70 }}
        disabled={yuklanmoqda}
      />
      <button className="tugma ikkinchi kichik" onClick={qoshish} disabled={yuklanmoqda}>
        {t("kurs_unit_yaratish")}
      </button>
      <button
        className="tugma ikkinchi kichik"
        style={{ color: "#d33" }}
        onClick={oxirginiOchir}
        disabled={ochirilmoqda}
      >
        {t("kurs_oxirgi_unit_ochirish")}
      </button>
      {xato && <span className="xato-xabar">{xato}</span>}
    </div>
  );
}

/** Admin/owner uchun — bitta Unit'ning BARCHA kontentini (Mashqlar +
 * Vocabulary) BITTA tugma bilan tozalash (2026-07-28, foydalanuvchi
 * talabi — qayta yuklashdan oldin eskisini tez o'chirish uchun). */
function UnitTozalashTugmasi({ unitId, royxatniYangila }) {
  const { t } = useI18n();
  const [ochirilmoqda, setOchirilmoqda] = useState(false);

  async function tozala() {
    if (!window.confirm(t("kurs_unit_tozalash_tasdiq"))) return;
    setOchirilmoqda(true);
    try {
      await api(`/api/kurslar/${unitId}/unit-tozalash/`, { method: "POST" });
      royxatniYangila();
    } catch {
      // yukla() qayta chaqirilganda ro'yxat o'zi yangilanadi; alohida xato
      // xabari shart emas — bu kamdan-kam ishlatiladigan yordamchi amal.
    } finally {
      setOchirilmoqda(false);
    }
  }

  return (
    <>
      {ochirilmoqda && <BandQoplamasi matn={t("kurs_unit_tozalash")} />}
      <button
        className="tugma ikkinchi"
        style={{ color: "#d33" }}
        onClick={tozala}
        disabled={ochirilmoqda}
      >
        {t("kurs_unit_tozalash")}
      </button>
    </>
  );
}

/** Owner/admin uchun — bitta tugunni (masalan bitta Unit) BUTUN ichki
 * daraxti bilan (mashqlar, so'zlar, rasm/audio fayllari) ZIP qilib
 * yuklab olish va boshqa muhitga (masalan prod<->local) import qilish
 * (2026-08-16, foydalanuvchi talabi: "backup qilgandek yuklab olib,
 * boshqa bazaga yuklash"). */
function EksportImportTugmalari({ tugunId, royxatniYangila, toliq = false }) {
  const { t } = useI18n();
  const [eksportBand, setEksportBand] = useState(false);
  const [importBand, setImportBand] = useState(false);
  // Bo'lingan daraja importida — "Unit 5/12" ko'rinishidagi holat.
  const [jarayon, setJarayon] = useState(null);
  const [xato, setXato] = useState("");

  async function eksportQil() {
    setXato("");
    setEksportBand(true);
    try {
      await apiFayluniYuklab(`/api/kurslar/${tugunId}/eksport/`);
    } catch (e) {
      setXato(e.data?.detail || e.message || t("xato_yuz_berdi"));
    } finally {
      setEksportBand(false);
    }
  }

  async function importQil(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    // 2026-08-27: butun DARAJA yuklanganda mavjud kontent TO'LIQ
    // o'chirib qayta yoziladi (ZIPda yo'q Unitlar ham o'chadi) —
    // shuning uchun tasdiq matni ham boshqacha, kuchliroq.
    if (!window.confirm(t(toliq ? "kurs_daraja_import_tasdiq" : "kurs_import_tasdiq"))) return;
    setXato("");
    setImportBand(true);
    const boshlandi = Date.now();
    try {
      // 2026-09-03: butun daraja arxivi endi "ZIP ichida ZIP" (server
      // tomonida `_bolingan_eksport`) — 500 MB'ni BITTA so'rovda
      // yuborish prodda umuman ishlamasdi (Railway/gunicorn chegarasi
      // 15 daqiqa, ustiga tarmoq uzilishi). Shuning uchun tashqi ZIPni
      // BRAUZERNING O'ZI ochadi va serverga har bir Unit'ni ALOHIDA,
      // ~40 MB'lik so'rov bilan yuboradi. Eski (yassi, `data.json`
      // ildizida) arxivlar avvalgidek bitta so'rov bilan ketadi.
      const manifest = await manifestniOqi(fayl);
      if (manifest && !toliq) {
        // Bo'lingan arxiv faqat DARAJA qatorida ma'noga ega. Uni
        // masalan Unit qatorida yuklasa — Unit darajaning o'z
        // maydonlari bilan qayta yozilib, ichi butunlay buzilardi.
        throw new Error(
          `Bu butun daraja arxivi ("${manifest.daraja.nomi}") — uni Unit emas, ` +
          "darajaning o'z qatoridagi \"Yuklash\" tugmasi orqali yuklang."
        );
      }
      if (manifest) {
        await bolibYukla(fayl, manifest);
      } else {
        const fd = new FormData();
        fd.append("fayl", fayl);
        if (toliq) fd.append("toliq", "1");
        await apiForm(`/api/kurslar/${tugunId}/import/`, { method: "POST", formData: fd });
      }
      royxatniYangila();
    } catch (e2) {
      // 2026-09-03: avval har qanday nosozlik "Xatolik yuz berdi" bo'lib
      // ko'rinardi — 227 MB daraja importi uzilganda sabab (worker
      // timeout / 502 / tarmoq) umuman bilinmasdi. Endi server bergan
      // izoh bo'lmasa, hech bo'lmasa HTTP holati va o'tgan vaqt ko'rsatiladi.
      const soniya = Math.round((Date.now() - boshlandi) / 1000);
      const tafsilot = e2.data?.detail
        || (e2.status ? `HTTP ${e2.status}` : e2.message)
        || t("xato_yuz_berdi");
      setXato(`${tafsilot} (${soniya}s)${e2.bolak ? ` — ${e2.bolak}` : ""}`);
    } finally {
      setImportBand(false);
      setJarayon(null);
    }
  }

  /** Tashqi ZIPni ochib `manifest.json`ni qaytaradi; arxiv eski (yassi)
   * formatda bo'lsa `null`. */
  async function manifestniOqi(fayl) {
    const { default: JSZip } = await import("jszip");
    const zip = await JSZip.loadAsync(fayl);
    const man = zip.file("manifest.json");
    if (!man) return null;
    const manifest = JSON.parse(await man.async("string"));
    if (manifest.format !== "bolingan") return null;
    return { zip, ...manifest };
  }

  /** Darajani bo'lakma-bo'lak yuboradi: avval darajaning o'zi (shu
   * so'rovda ZIPda YO'Q eski Unit'lar ham o'chiriladi — `kalitlar`),
   * so'ng har bir Unit alohida. Uzilsa — qaysi bo'lakda uzilgani
   * xato xabarida ko'rinadi va qayta urinish xavfsiz (import
   * idempotent), shunchaki boshidan qayta yuguradi. */
  async function bolibYukla(fayl, { zip, daraja, unitlar }) {
    const jami = unitlar.length + 1;
    const yubor = async (nom, ichkiNomi, qoshimcha) => {
      const blob = await zip.file(ichkiNomi).async("blob");
      const fd = new FormData();
      fd.append("fayl", new File([blob], ichkiNomi.split("/").pop(), { type: "application/zip" }));
      fd.append("toliq", "1");
      Object.entries(qoshimcha || {}).forEach(([k, v]) => fd.append(k, v));
      try {
        await apiForm(`/api/kurslar/${tugunId}/import/`, { method: "POST", formData: fd });
      } catch (e) {
        e.bolak = nom;
        throw e;
      }
    };

    setJarayon({ joriy: 1, jami, nomi: daraja.nomi });
    await yubor(daraja.nomi, daraja.fayl, {
      kalitlar: unitlar.map((u) => u.kalit).join(","),
    });
    for (let i = 0; i < unitlar.length; i++) {
      const u = unitlar[i];
      setJarayon({ joriy: i + 2, jami, nomi: u.nomi });
      await yubor(u.nomi, u.fayl);
    }
  }

  return (
    <span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
      {/* Saqlash/yuklash butun daraja uchun bir necha daqiqa davom etishi
          mumkin (Pre-Int eksporti ~227 MB) — shu vaqt ichida oynadagi
          hech narsa bosilmasin (2026-09-03, foydalanuvchi talabi). */}
      {(eksportBand || importBand) && (
        <BandQoplamasi
          matn={
            jarayon
              ? `${t("kurs_import")} — ${jarayon.joriy}/${jarayon.jami}: ${jarayon.nomi}`
              : t(eksportBand ? "kurs_eksport" : "kurs_import")
          }
        />
      )}
      <button className="tugma ikkinchi" onClick={eksportQil} disabled={eksportBand}>
        {eksportBand ? t("yuklanmoqda") : t("kurs_eksport")}
      </button>
      <label className="tugma ikkinchi" style={{ cursor: "pointer" }}>
        {importBand ? t("yuklanmoqda") : t("kurs_import")}
        <input
          type="file"
          accept=".zip"
          onChange={importQil}
          disabled={importBand}
          style={{ display: "none" }}
        />
      </label>
      {xato && <span className="xato-xabar">{xato}</span>}
    </span>
  );
}

/** Bitta tugun — akkordeon (agar children bo'lsa) yoki oxirgi qatlam
 * (fayl + mashqlar + tugallandimi belgisi + admin uchun boshqaruv).
 *
 * `otaUnitMi` (2026-08-19, avvalgi nomi `ichkariUnitMi`) — shu
 * tugunning BEVOSITA ota-tuguni Unit (`unit_darsi=True`) bo'lsa true.
 * Shu bo'lsa, KALIT bo'yicha ("students_book"/"workbook"/"vocabulary")
 * maxsus ko'rinish tanlanadi — boshqa (flat) bo'limlar avvalgidek
 * fayl+mashq ko'rinishida qoladi. Tuzilma o'zgarishi (2026-08-19):
 * Student's Book/Workbook endi BEVOSITA "oxirgi qatlam" (mashqlar
 * ularga to'g'ridan-to'g'ri biriktiriladi, oraliq "Mashqlar" tuguni
 * yo'q), Vocabulary esa ikkala kitobga UMUMIY, Unit'ning uchinchi
 * farzandi sifatida. */
function Tugun({ tugun, chuqurlik, adminMi, talabaMi, oqituvchiMi, royxatniYangila, otaUnitMi, birodarVocabId, ochiqmi, onOchish }) {
  const { t } = useI18n();
  // Tugun nomi 3 tilda (2026-07-28) — bazadagi `nomi` o'zgarmaydi, u
  // faqat ZAXIRA: kaliti yo'q tugunlar uchun. `t()` kalit topilmasa
  // kalitning o'zini qaytargani uchun natijani tekshirib ko'ramiz.
  const nomi = (() => {
    if (!tugun.kalit) return tugun.nomi;
    const kalit = `tugun_${tugun.kalit}`;
    const tarjima = t(kalit);
    return tarjima === kalit ? tugun.nomi : tarjima;
  })();
  // Akkordeon (2026-07-27, foydalanuvchi talabi — "qolgan qismlar
  // halaqit qilyabdi") — shu tugunning FARZANDLARI orasida bir vaqtda
  // faqat BITTASI ochiq turadi: ID saqlanadi (`ochiqBolaId`), farzandning
  // o'zi ochiqligi esa OTA orqali (`ochiqmi`/`onOchish`) boshqariladi —
  // shu tugunning o'zi qanday ochilgani esa YUQORIDAGI ota tomonidan.
  const [ochiqBolaId, setOchiqBolaId] = useState(null);
  const [mashqOchiq, setMashqOchiq] = useState(false);
  const [faylXato, setFaylXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [tugallandimi, setTugallandimi] = useState(tugun.tugallandimi);

  const otstup = 14 + chuqurlik * 20;
  // Bo'lim turi KALIT bo'yicha aniqlanadi (2026-07-28) — nomi endi
  // tarjima qilingani uchun u kalit bo'la olmaydi. `otaUnitMi` — ota
  // tugun Unit (`unit_darsi=True`)mi.
  const unitBolimi = otaUnitMi ? tugun.kalit : null;
  // Kitob tuguni — yuklash/tozalash tugmalari aynan shu darajada chiqadi.
  const kitobmi = tugun.kalit === "students_book" || tugun.kalit === "workbook";

  if (tugun.tez_kunda) {
    return (
      <div
        className="kurs-qator"
        style={{ paddingLeft: otstup, display: "flex", alignItems: "center", gap: 8, opacity: 0.55 }}
      >
        <span>{tugun.ikonka}</span>
        <span>{nomi}</span>
        <span className="izoh">— {t("tez_orada")}</span>
      </div>
    );
  }

  if (tugun.qulflangan) {
    return (
      <div
        className="kurs-qator"
        style={{ paddingLeft: otstup, display: "flex", alignItems: "center", gap: 8, opacity: 0.5 }}
      >
        <span>🔒</span>
        <span>{nomi}</span>
        <span className="izoh">— {t("kurs_qulflangan")}</span>
      </div>
    );
  }

  // 2026-07-29(5): HAQIQIY BUG TOPILDI — Unit hali yaratilmagan
  // Beginner...Upper-Intermediate darajasi backend'dan FARZANDSIZ
  // qaytadi (`oxirgi_qatlammi=true`, chunki `children.length===0`),
  // shuning uchun pastdagi umumiy "oxirgi qatlam" yo'li orqali oddiy
  // fayl+mashq ko'rinishi chiqib qolardi — "Unit soni" input/tugma esa
  // FAQAT quyidagi (farzandli/branch) return blokida edi, u yerga hech
  // qachon yetib bormasdi. Shu holatni ALOHIDA, oxirgi-qatlam
  // tekshiruvidan OLDIN ushlaymiz.
  if (tugun.oxirgi_qatlammi && UNIT_YARATISH_MUMKIN_DARAJALAR.has(tugun.kalit)) {
    return (
      <div
        className="kurs-qator"
        style={{ paddingLeft: otstup, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}
      >
        <span>{tugun.ikonka}</span>
        <span style={{ fontWeight: chuqurlik < 2 ? 700 : 500 }}>{nomi}</span>
        {adminMi && (
          <AdminDarajaUnitYaratish darajaId={tugun.id} royxatniYangila={royxatniYangila} />
        )}
      </div>
    );
  }

  if (tugun.oxirgi_qatlammi) {
    // ==== Beginner Unit'iga xos 2 bo'lim — maxsus ko'rinish ====
    if (unitBolimi === "vocabulary") {
      return (
        <div className="kurs-qator kurs-qator-oxirgi" style={{ display: "block" }}>
          <div
            style={{ paddingLeft: otstup, display: "flex", alignItems: "center", gap: 10, marginBottom: mashqOchiq ? 8 : 0, cursor: "pointer" }}
            onClick={() => setMashqOchiq((v) => !v)}
          >
            <span>{mashqOchiq ? "▾" : "▸"}</span>
            <span>{tugun.ikonka}</span>
            <span style={{ fontWeight: 600 }}>
              {nomi}{tugun.sozlar_soni ? ` (${tugun.sozlar_soni} ${t("kurs_soz")})` : ""}
            </span>
          </div>
          {/* 2026-08-21, foydalanuvchi talabi: mashq/so'z KONTENTI daraxt
              chuqurligiga qarab siljimasin — mobil ekranda chuqur
              joylashgan Unit'larda (Kurslar > Ingliz tili > Beginner >
              Unit > Vocabulary) otstup yig'ilib, kontent ekrandan
              chiqib ketardi. Sarlavha qatori hali ham chuqurlikni
              ko'rsatadi, kontent esa doim kichik sobit chetdan boshlanadi. */}
          {mashqOchiq && (
            <div style={{ paddingLeft: 14 }}>
              <VocabularyKorinishi tugunId={tugun.id} matn={tugun.matn} />
            </div>
          )}
        </div>
      );
    }

    if (unitBolimi === "games") {
      // 2026-08-21, foydalanuvchi talabi: Games endi akkordeon ichida
      // emas, TO'LIQ EKRAN modalda ochiladi (kartochka/viktorina uchun
      // ko'proq joy, boshqa kontent chalg'itmaydi). `mashqOchiq` shu
      // yerda "modal ochiqmi" degani.
      return (
        <>
          <div className="kurs-qator kurs-qator-oxirgi" style={{ display: "block" }}>
            <div
              style={{ paddingLeft: otstup, display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}
              onClick={() => setMashqOchiq(true)}
            >
              <span>{tugun.ikonka}</span>
              <span style={{ fontWeight: 600 }}>{nomi}</span>
            </div>
          </div>
          {mashqOchiq && (
            <div className="oyin-modal-fon" onClick={() => setMashqOchiq(false)}>
              <div className="oyin-modal" onClick={(e) => e.stopPropagation()}>
                <div className="oyin-modal-bosh">
                  <span style={{ fontWeight: 700 }}>{nomi}</span>
                  <button
                    className="oyin-yopish"
                    onClick={() => setMashqOchiq(false)}
                    title={t("yopish")}
                    aria-label={t("yopish")}
                  >
                    ✕
                  </button>
                </div>
                <GamesKorinishi vocabTugunId={birodarVocabId} />
              </div>
            </div>
          )}
        </>
      );
    }

    if (kitobmi) {
      // 2026-08-19: Student's Book/Workbook endi BEVOSITA "oxirgi
      // qatlam" — mashqlar shu tugunga to'g'ridan-to'g'ri biriktiriladi
      // ("Mashqlar" oraliq qatlami olib tashlandi). Tozalash/Saqlash-
      // Yuklash tugmalari avval akkordeon (branch) ko'rinishida chiqardi
      // — kitob endi leaf bo'lgani uchun shu yerga ko'chirildi.
      // 2026-08-19(2), foydalanuvchi talabi: alohida "Ochish" tugmasi
      // emas, qator ustiga bosilganda ochilsin/yopilsin.
      return (
        <div className="kurs-qator kurs-qator-oxirgi" style={{ display: "block" }}>
          <div
            style={{ paddingLeft: otstup, display: "flex", alignItems: "center", gap: 10, marginBottom: mashqOchiq ? 8 : 0, cursor: "pointer" }}
            onClick={() => setMashqOchiq((v) => !v)}
          >
            <span>{mashqOchiq ? "▾" : "▸"}</span>
            <span>{tugun.ikonka}</span>
            <span style={{ fontWeight: 600 }}>
              {nomi}{tugun.mashqlar_soni ? ` (${tugun.mashqlar_soni})` : ""}
            </span>
          </div>
          {adminMi && (
            <div
              style={{ paddingLeft: otstup, display: "flex", alignItems: "flex-start", gap: 8, marginTop: 6, marginBottom: mashqOchiq ? 8 : 0, flexWrap: "wrap" }}
              onClick={(e) => e.stopPropagation()}
            >
              <UnitTozalashTugmasi unitId={tugun.id} royxatniYangila={royxatniYangila} />
              <EksportImportTugmalari tugunId={tugun.id} royxatniYangila={royxatniYangila} />
            </div>
          )}
          {/* 2026-08-21, foydalanuvchi talabi: mashq KONTENTI daraxt
              chuqurligiga qarab siljimasin (mobil ekranda chuqur
              Unit'larda otstup yig'ilib, kontent ekrandan chiqib
              ketardi) — sarlavha/admin tugmalari otstup bilan qoladi,
              kontent doim kichik sobit chetdan boshlanadi. */}
          {mashqOchiq && (
            <div style={{ paddingLeft: 14 }}>
              <MashqPaneli tugunId={tugun.id} talabaMi={talabaMi} oqituvchiMi={oqituvchiMi} jsonKiritishKorinadi={false} />
            </div>
          )}
        </div>
      );
    }

    // ==== Generik (flat) bo'limlar — avvalgidek fayl+mashq ko'rinishi ====
    async function faylniOch() {
      if (!tugun.fayl_url) return;
      const url = await apiBlobUrl(tugun.fayl_url).catch(() => null);
      if (url) window.open(url, "_blank");
    }

    async function faylYukla(e) {
      const fayl = e.target.files[0];
      e.target.value = "";
      if (!fayl) return;
      setFaylXato("");
      setYuklanmoqda(true);
      try {
        const fd = new FormData();
        fd.append("fayl", fayl);
        await apiForm(`/api/kurslar/${tugun.id}/fayl-boshqaruv/`, { method: "PATCH", formData: fd });
        royxatniYangila();
      } catch (e2) {
        setFaylXato(e2.data?.detail || t("xato_yuz_berdi"));
      } finally {
        setYuklanmoqda(false);
      }
    }

    async function tugallandiBelgila() {
      const res = await api(`/api/kurslar/${tugun.id}/tugallandi/`, { method: "POST" }).catch(() => null);
      if (res) setTugallandimi(res.tugallandimi);
    }

    return (
      <div>
        <div
          className="kurs-qator kurs-qator-oxirgi"
          style={{ paddingLeft: otstup, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}
        >
          <span>{tugun.ikonka}</span>
          <span>{nomi}</span>
          {tugun.fayl_url ? (
            <button className="tugma ikkinchi" onClick={faylniOch}>
              {t("kurs_faylni_ochish")}
            </button>
          ) : (
            <span className="izoh">{t("kurs_fayl_yoq")}</span>
          )}
          {talabaMi && tugun.fayl_url && (
            <button
              className="tugma ikkinchi"
              style={tugallandimi ? { background: "var(--komir)", color: "var(--sariq)" } : undefined}
              onClick={tugallandiBelgila}
            >
              {tugallandimi ? `✓ ${t("kurs_tugallandi")}` : t("kurs_tugallandim")}
            </button>
          )}
          {adminMi && (
            <>
              {/* Student's Book / Workbook fayli yuklanayotgan payt oynadagi
                  hech narsa bosilmasin (2026-09-03, foydalanuvchi talabi). */}
              {yuklanmoqda && <BandQoplamasi matn={tugun.nomi} />}
              <input type="file" onChange={faylYukla} disabled={yuklanmoqda} style={{ maxWidth: 200 }} />
              {faylXato && <span className="xato-xabar">{faylXato}</span>}
            </>
          )}
          {(adminMi || tugun.mashqlar_soni) && (
            <button className="tugma ikkinchi" onClick={() => setMashqOchiq((v) => !v)}>
              {mashqOchiq
                ? t("yopish")
                : `${t("kurs_mashqlar")}${tugun.mashqlar_soni ? ` (${tugun.mashqlar_soni})` : ""}`}
            </button>
          )}
        </div>
        {mashqOchiq && (
          <div style={{ paddingLeft: 14, marginTop: 6 }}>
            <MashqPaneli tugunId={tugun.id} talabaMi={talabaMi} oqituvchiMi={oqituvchiMi} />
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <div
        className="kurs-qator kurs-qator-branch"
        style={{ paddingLeft: otstup, display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}
        onClick={onOchish}
      >
        <span>{ochiqmi ? "▾" : "▸"}</span>
        <span>{tugun.ikonka}</span>
        <span style={{ fontWeight: chuqurlik < 2 ? 700 : 500 }}>{nomi}</span>
      </div>
      {ochiqmi && (
        <div>
          {/* 2026-08-19: Student's Book/Workbook uchun Tozalash/Saqlash-
              Yuklash tugmalari endi kitob leaf ko'rinishining o'zida
              (yuqorida, `kitobmi` bloki) — bu yerga kitob tuguni hech
              qachon yetib kelmaydi (u har doim "oxirgi qatlam"). */}
          {/* 2026-08-16, foydalanuvchi talabi: "faqat TANLANGAN Unit"
              eksport qilinsin — shuning uchun tugma KITOB emas, Unit'ning
              O'ZI darajasida (`tugun.unit_darsi`), bir marta chiqadi. */}
          {adminMi && tugun.unit_darsi && (
            <div style={{ paddingLeft: otstup + 18, display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 6, flexWrap: "wrap" }}>
              <EksportImportTugmalari tugunId={tugun.id} royxatniYangila={royxatniYangila} />
            </div>
          )}
          {/* 2026-08-27, foydalanuvchi talabi: endi BUTUN DARAJA
              (Beginner ... Upper-Intermediate) ham bir bosishda saqlanadi
              va qayta yuklanadi. Yuklashda `toliq` — mavjud daraja TO'LIQ
              o'chirilib, ZIPdagi holat bilan almashtiriladi (ZIPda yo'q
              Unitlar ham o'chadi), aks holda eski va yangi Unitlar
              aralashib qolardi. */}
          {adminMi && UNIT_YARATISH_MUMKIN_DARAJALAR.has(tugun.kalit) && (
            <div style={{ paddingLeft: otstup + 18, display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 6, flexWrap: "wrap" }}>
              <span className="izoh" style={{ alignSelf: "center" }}>{t("kurs_butun_daraja")}:</span>
              <EksportImportTugmalari tugunId={tugun.id} royxatniYangila={royxatniYangila} toliq />
            </div>
          )}
          {/* 2026-07-29: Elementary...Upper-Intermediate — Unit hali
              yaratilmagan bo'lsa (birorta farzandda unit_darsi=True yo'q),
              admin Unit sonini kiritib bir martalik tuzilma yaratadi. */}
          {adminMi
            && UNIT_YARATISH_MUMKIN_DARAJALAR.has(tugun.kalit)
            && !tugun.children.some((b) => b.unit_darsi) && (
            <div style={{ paddingLeft: otstup + 18, marginBottom: 6 }}>
              <AdminDarajaUnitYaratish darajaId={tugun.id} royxatniYangila={royxatniYangila} />
            </div>
          )}
          {/* 2026-07-30 talabi: Unitlar allaqachon yaratilgan bo'lsa —
              yana Unit qo'shish (oxiriga) yoki oxirgi (bo'sh) Unitni
              o'chirish imkoni. */}
          {adminMi
            && UNIT_YARATISH_MUMKIN_DARAJALAR.has(tugun.kalit)
            && tugun.children.some((b) => b.unit_darsi) && (
            <div style={{ paddingLeft: otstup + 18, marginBottom: 6 }}>
              <AdminUnitSoniBoshqarish darajaId={tugun.id} royxatniYangila={royxatniYangila} />
            </div>
          )}
          {tugun.children.map((b) => (
            <Tugun
              key={b.id}
              tugun={b}
              chuqurlik={chuqurlik + 1}
              adminMi={adminMi}
              oqituvchiMi={oqituvchiMi}
              talabaMi={talabaMi}
              royxatniYangila={royxatniYangila}
              otaUnitMi={tugun.unit_darsi}
              // 2026-08-21: "Games" tuguni o'z so'zini saqlamaydi —
              // birodar "Vocabulary" tugunidan oladi, shuning uchun
              // Unit o'zining farzandlarini chizayotganda o'sha id'ni
              // oldindan hisoblab, PASTGA uzatadi.
              birodarVocabId={tugun.unit_darsi ? tugun.children.find((c) => c.kalit === "vocabulary")?.id : undefined}
              ochiqmi={ochiqBolaId === b.id}
              onOchish={() => setOchiqBolaId((joriy) => (joriy === b.id ? null : b.id))}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/** "Kurslar" bo'limi — ko'p bosqichli iyerarxik menyu (Kurs > Daraja >
 * Unit/Bo'lim > Mashq turi). Talaba/admin/owner/o'qituvchi ko'radi, "oddiy
 * foydalanuvchi" ko'rmaydi. Tuzilma qattiq (kurslar_urugla buyrug'i orqali
 * bir martalik yaratiladi) — admin oxirgi qatlamga fayl/mashq biriktiradi.
 * Unit'lar (masalan darslik bo'limlari) ketma-ket ochiladi — talaba uchun
 * keyingisi oldingisining BARCHA bo'limlaridagi mashqlardan jami 60%+
 * ball olmaguncha qulflangan (🔒) bo'lib ko'rsatiladi. */
export default function Kurslar() {
  const { t } = useI18n();
  const { profil } = useProfil();
  const adminMi = profil?.is_owner || profil?.role === "admin";
  const talabaMi = profil?.role === "student";
  const oqituvchiMi = profil?.role === "teacher";
  const [daraxt, setDaraxt] = useState(null);
  // Akkordeon (2026-07-27) — ildiz darajasida (Rus tili/Matematika/Ingliz
  // tili/CEFR) ham bir vaqtda faqat bittasi ochiq turishi uchun; birinchi
  // yuklashda "tez kunda" bo'lmagan birinchi bo'lim (hozircha — Ingliz
  // tili) avtomatik ochiq boshlanadi, avvalgi ko'rinishni saqlab qolish
  // uchun (qayta yuklashda tanlov o'chib qolmasin — `royxatniYangila`
  // ko'p marta chaqiriladi).
  const [ochiqIldizId, setOchiqIldizId] = useState(null);

  function yukla() {
    api("/api/kurslar/daraxt/").then((d) => {
      setDaraxt(d);
      setOchiqIldizId((joriy) => joriy ?? d.children.find((c) => !c.tez_kunda)?.id ?? null);
    }).catch(() => {});
  }

  useEffect(() => {
    yukla();
  }, []);

  if (!daraxt) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <div className="karta">
      <h3>{t("nav_kurslar")}</h3>
      {daraxt.children.map((tugun) => (
        <Tugun
          key={tugun.id}
          tugun={tugun}
          chuqurlik={0}
          adminMi={adminMi}
          oqituvchiMi={oqituvchiMi}
          talabaMi={talabaMi}
          royxatniYangila={yukla}
          otaUnitMi={false}
          ochiqmi={ochiqIldizId === tugun.id}
          onOchish={() => setOchiqIldizId((joriy) => (joriy === tugun.id ? null : tugun.id))}
        />
      ))}
    </div>
  );
}
