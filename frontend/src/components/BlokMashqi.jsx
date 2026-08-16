import { useEffect, useRef, useState } from "react";
import { api, apiBlobUrl } from "../api";
import { faqatBittaAudioIjro } from "../audio";
import { useI18n } from "../i18n";
import { IMLO_OFF } from "../imlo";

/** Blok formatidagi darslik sahifasi (2026-07-28, audio/tekshirish
 * qismlari 2026-07-29 da qayta ishlandi).
 *
 * Eski ko'rinishdan farqi: sahifa RASM emas — u qaytadan quriladi.
 * Matn haqiqiy HTML matni (o'tkir, tanlanadi, mobilda o'qiladi),
 * suratlar esa sahifadan kesib olingan alohida fayllar.
 *
 * Bo'sh joylar bloklarda faqat `savol_idx` bilan turadi (javob EMAS) —
 * javoblar serverda qoladi, ya'ni talaba F12 bosib ko'ra olmaydi.
 * "erkin" bo'sh joylar (talaba o'z ismini yozadi) baholanmaydi, lekin
 * input baribir ko'rsatiladi.
 *
 * AUDIO (2026-07-29 talabi): bitta sahifada BITTA umumiy <audio>
 * elementi bor (avval har tugma o'z <audio>siga ega edi). Inline
 * belgilar shu umumiy pleyerni almashtiradi/boshqaradi; sahifa pastida
 * doim ko'rinadigan (sticky) panel joriy trekni play/pause qiladi —
 * talaba pastga aylantirib ketsa ham nazorat qo'lida qoladi.
 *
 * TEKSHIRISH (2026-07-29 talabi): endi BUTUN sahifa uchun bitta tugma
 * emas — har "mashq" bloki O'Z ustida mustaqil Tekshirish tugmasiga
 * ega. Backend hamon BUTUN mashqning javoblarini qabul qiladi
 * (`/yechish/` o'zgarmagan — ball/60% qoidasi/Unit qulfi mexanizmiga
 * tegilmadi), lekin natija FAQAT o'sha blokning bo'sh joylariga
 * qo'llaniladi — boshqa bloklar tahrirlanadigan holicha qoladi. */

function AudioBelgi({ raqam, faolRaqam, ijro, tanla }) {
  const faol = raqam === faolRaqam;
  return (
    <button
      type="button"
      className="blok-audio-tugma"
      onClick={() => tanla(raqam)}
      title={raqam}
    >
      <span aria-hidden="true">{faol && ijro ? "⏸" : "▶"}</span>
      <span className="blok-audio-raqam">{raqam}</span>
    </button>
  );
}

/** Bitta rasm + uning javob maydoni (2026-08-03, "so'z banki + raqamlangan
 * rasmlar" mashqi) — "rasm_javobli" (yagona) va "rasm_javobli_grid"
 * (panjara) ikkisida ham qayta ishlatiladi. */
function RasmJavobKartasi({ url, raqam, birlik, savolIdx, javoblar, javobniQoy, blokNatija }) {
  const holat = blokNatija ? (blokNatija.natijalar[savolIdx] ? "togri" : "notogri") : "";
  return (
    <div className="blok-rasm-javobli-karta">
      {raqam && <div className="blok-rasm-javobli-raqam">{raqam}</div>}
      {url && <img className="blok-rasm" src={url} alt="" />}
      <div className="blok-rasm-javobli-javob-qatori">
        <input
          {...IMLO_OFF}
          className={`blok-bosh-joy ${holat}`}
          value={javoblar[savolIdx] || ""}
          disabled={!!blokNatija}
          onChange={(e) => javobniQoy(savolIdx, e.target.value)}
        />
        {/* 2026-08-16, foydalanuvchi talabi: kitobdagi kabi otning o'zi
            statik yozilgan, faqat SON kiritiladi (masalan "___ books"). */}
        {birlik && <span className="blok-rasm-javobli-birlik">{birlik}</span>}
      </div>
    </div>
  );
}

function Bolaklar({ bolaklar, javoblar, javobniQoy, blokNatija }) {
  return (
    <>
      {bolaklar.map((b, k) => {
        if (!b.bosh_joy) return <span key={k}>{b.matn}</span>;
        if (b.erkin) {
          // Baholanmaydi (to'g'ri javob yo'q) — lekin talaba yozadi.
          return <input key={k} {...IMLO_OFF} className="blok-bosh-joy erkin" />;
        }
        const i = b.savol_idx;
        const holat = blokNatija ? (blokNatija.natijalar[i] ? "togri" : "notogri") : "";
        return (
          <input
            key={k}
            {...IMLO_OFF}
            className={`blok-bosh-joy ${holat}`}
            value={javoblar[i] || ""}
            disabled={!!blokNatija}
            onChange={(e) => javobniQoy(i, e.target.value)}
          />
        );
      })}
    </>
  );
}

function Blok({ blok, blokIdx, rasmUrllar, faolRaqam, ijro, audioTanla, javoblar, javobniQoy, blokNatijalar, tekshir, yuborilayotganBlok, t }) {
  const audioBelgi = blok.audio_raqam ? (
    <AudioBelgi raqam={blok.audio_raqam} faolRaqam={faolRaqam} ijro={ijro} tanla={audioTanla} />
  ) : null;

  switch (blok.tur) {
    case "sarlavha":
      return <h3 className="blok-sarlavha">{blok.matn}</h3>;
    case "bolim_sarlavha":
      return <h4 className="blok-bolim">{blok.matn}</h4>;
    case "rasm": {
      const url = rasmUrllar[blok.rasm_idx];
      if (!url) return null;
      // 2026-08-05, foydalanuvchi talabi: rasm KATTA bo'lsa matn PASTDA,
      // KICHKINA bo'lsa matn O'NG TOMONDA chiqsin. Bu o'lchamni oldindan
      // BILMASDAN (server hech qanday en/bo'y yubormaydi) sof CSS
      // flex-wrap orqali hal qilinadi: rasm o'z tabiiy kengligini oladi,
      // matnga esa minimal kenglik (`min-width`) beriladi — qatorga
      // ikkalasi baravar sig'masa (ya'ni rasm katta bo'lsa), brauzer
      // matnni AVTOMATIK keyingi qatorga (pastga) tushiradi.
      //
      // 2026-08-10: admin `tomon`ni QO'LDA belgilaydi (tasdiqlash
      // oynasida). "chap"/"ong" — CSS float, ya'ni KEYINGI bloklarning
      // matni rasm atrofida oqadi (aynan kitobdagidek). "tepa" (standart)
      // va "past" — yuqoridagi avtomatik xatti-harakat (past bo'lsa blok
      // mashq oxiriga suriladi, qarang `BlokMashqi`).
      const tomon = blok.tomon;
      const suzuvchi = tomon === "chap" || tomon === "ong";
      return (
        <div
          className="blok-rasm-izoh-qatori"
          style={suzuvchi ? {
            float: tomon === "chap" ? "left" : "right",
            maxWidth: "42%",
            [tomon === "chap" ? "marginRight" : "marginLeft"]: 12,
            marginBottom: 8,
          } : undefined}
        >
          <img className="blok-rasm" src={url} alt={blok.izoh || ""} />
          {blok.izoh && <div className="blok-rasm-izoh-matni">{blok.izoh}</div>}
        </div>
      );
    }
    case "rasm_qatori": {
      const itemlar = blok.qator || [];
      const jamiKeng = itemlar.reduce((j, it) => j + (it.keng || 1), 0) || 1;
      return (
        <div className="blok-rasm-qatori">
          {itemlar.map((it, k) => {
            const url = rasmUrllar[it.rasm_idx];
            if (!url) return null;
            return (
              <div
                key={k}
                className="blok-rasm-karta"
                style={{ flexGrow: it.keng || 1, flexBasis: `${((it.keng || 1) / jamiKeng) * 100}%` }}
              >
                <img className="blok-rasm" src={url} alt={it.izoh || ""} />
                {it.matn && <div className="blok-pufakcha">{it.matn}</div>}
              </div>
            );
          })}
        </div>
      );
    }
    case "korsatma":
      return (
        <div className="blok-korsatma">
          {blok.raqam && <span className="blok-raqam">{blok.raqam}</span>}
          {audioBelgi}
          <span>{blok.matn}</span>
        </div>
      );
    case "dialog": {
      const qatorlar = blok.qatorlar || [];
      // 2026-08-16, foydalanuvchi talabi: so'zlovchi nomi bo'lmagan qisqa
      // savol-javob namunalari (masalan "What's this in English? / It's
      // a photo.") kitobdagi kabi haqiqiy SUHBAT PUFAKCHASI (uchburchak
      // "dumi" bilan) shaklida chiqsin — A/B nomli to'liq suhbat
      // qutisidan farqli.
      const hammaKimsiz = qatorlar.length > 0 && qatorlar.every((q) => !q.kim);
      if (hammaKimsiz) {
        return (
          <div className="blok-suhbat-pufakchalar">
            {audioBelgi}
            {qatorlar.map((q, k) => (
              <span key={k} className={`blok-suhbat-pufakcha ${k % 2 === 0 ? "so-ol" : "so-ong"}`}>
                {q.gap}
              </span>
            ))}
          </div>
        );
      }
      return (
        <div className="blok-dialog">
          {audioBelgi}
          {qatorlar.map((q, k) => (
            <div key={k} className="blok-dialog-qator">
              <span className="blok-dialog-kim">{q.kim}</span>
              {/* 2026-08-16, foydalanuvchi talabi: kitobdagi "namuna"
                  (allaqachon to'ldirilgan misol) javobi alohida rangda,
                  tagiga chizilgan holda ko'rinsin — oddiy gap matnidan
                  ajralib turishi uchun. */}
              <span className={q.namuna ? "blok-dialog-namuna" : undefined}>{q.gap}</span>
            </div>
          ))}
        </div>
      );
    }
    case "grammar_spot": {
      // 2026-08-16: GRAMMAR SPOT ichida ham bo'sh joy (masalan "Write
      // 'm, is, or are.") bo'lishi mumkin — shu holatda "qatorlar" har
      // biri {"bolaklar": [...]} bo'lishi mumkin ("mashq" bolaklari
      // bilan bir xil shakl), oddiy matn qatorlari bilan aralash holda.
      const bosBolaklar = (blok.qatorlar || []).flatMap((q) =>
        typeof q === "object" && q.bolaklar ? q.bolaklar.filter((b) => b.bosh_joy && !b.erkin) : []
      );
      const savolIdxlari = bosBolaklar.map((b) => b.savol_idx);
      const blokNatija = blokNatijalar[blokIdx];
      return (
        <div className="blok-mashq-blok">
          <div className="blok-gs">
            <div className="blok-gs-bosh">{blok.sarlavha || "GRAMMAR SPOT"}</div>
            <div className="blok-gs-tan">
              {(blok.qatorlar || []).map((q, k) =>
                typeof q === "object" && q.bolaklar ? (
                  <div key={k}>
                    <Bolaklar bolaklar={q.bolaklar} javoblar={javoblar} javobniQoy={javobniQoy} blokNatija={blokNatija} />
                  </div>
                ) : (
                  <div key={k}>{typeof q === "string" ? q : q.matn}</div>
                )
              )}
            </div>
          </div>
          {savolIdxlari.length > 0 && (
            blokNatija ? (
              <div className="izoh blok-mashq-natija">
                {savolIdxlari.filter((i) => blokNatija.natijalar[i]).length}/{savolIdxlari.length} {"correct"}
              </div>
            ) : (
              <button
                type="button"
                className="tugma ikkinchi kichik"
                onClick={() => tekshir(blokIdx, savolIdxlari)}
                disabled={yuborilayotganBlok === blokIdx}
              >
                {yuborilayotganBlok === blokIdx ? "Checking…" : "Check"}
              </button>
            )
          )}
        </div>
      );
    }
    case "pufakcha":
      return <div className="blok-pufakcha">{blok.matn}</div>;
    case "jadval": {
      // 2026-08-16, foydalanuvchi talabi: kitobdagi ustunli jadval
      // (masalan /s/ /z/ /ɪz/ talaffuz jadvali) — "sarlavhalar" ustun
      // nomlari, "qatorlar" har biri o'sha ustunlar soniga mos massiv
      // (bo'sh katak uchun "" yoziladi).
      const sarlavhalar = blok.sarlavhalar || [];
      const qatorlar = blok.qatorlar || [];
      return (
        <table className="blok-jadval">
          {sarlavhalar.length > 0 && (
            <thead>
              <tr>{sarlavhalar.map((s, k) => <th key={k}>{s}</th>)}</tr>
            </thead>
          )}
          <tbody>
            {qatorlar.map((q, k) => (
              <tr key={k}>{q.map((c, ci) => <td key={ci}>{c}</td>)}</tr>
            ))}
          </tbody>
        </table>
      );
    }
    case "soz_banki":
      return (
        <div className="blok-soz-banki">
          {(blok.qatorlar || []).map((s, k) => {
            const matn = typeof s === "string" ? s : s.matn;
            // 2026-08-16: kitobda namuna sifatida ISHLATILGAN so'z
            // ustidan chizilgan holda ko'rsatiladi (masalan "Good
            // morning!") — endi bank ichida qayta tanlanmasligi ko'rinib
            // tursin.
            const ishlatilgan = typeof s === "object" && s.ishlatilgan;
            return (
              <span key={k} style={ishlatilgan ? { textDecoration: "line-through", opacity: 0.55 } : undefined}>
                {matn}
              </span>
            );
          })}
        </div>
      );
    case "rasm_javobli": {
      const blokNatija = blokNatijalar[blokIdx];
      return (
        <div className="blok-mashq-blok">
          <RasmJavobKartasi
            url={rasmUrllar[blok.rasm_idx]}
            raqam={blok.raqam}
            savolIdx={blok.savol_idx}
            javoblar={javoblar}
            javobniQoy={javobniQoy}
            blokNatija={blokNatija}
          />
          <div className="blok-rasm-javobli-tek">
            {blokNatija ? (
              <div className="izoh blok-mashq-natija">
                {blokNatija.natijalar[blok.savol_idx] ? "✓" : "✗"} {"correct"}
              </div>
            ) : (
              <button
                type="button"
                className="tugma ikkinchi kichik"
                onClick={() => tekshir(blokIdx, [blok.savol_idx])}
                disabled={yuborilayotganBlok === blokIdx}
              >
                {yuborilayotganBlok === blokIdx ? "Checking…" : "Check"}
              </button>
            )}
          </div>
        </div>
      );
    }
    case "rasm_javobli_grid": {
      const itemlar = blok.itemlar || [];
      const savolIdxlari = itemlar.map((it) => it.savol_idx);
      const blokNatija = blokNatijalar[blokIdx];
      // 2026-08-16, foydalanuvchi talabi: "kenglik" (rasm keng, kvadrat
      // emas — masalan Numbers mashqidagi buyum qatorlari) belgisi
      // bo'lsa HAR BIRI ALOHIDA QATORDA, kattaroq chiqadi — kichik
      // kvadrat kartochkalar panjarasi emas.
      const ustunKo = blok.qator_boyicha;
      return (
        <div className="blok-mashq-blok">
          <div className={ustunKo ? "blok-rasm-javobli-ustun" : "blok-rasm-javobli-grid"}>
            {itemlar.map((it, k) => (
              <RasmJavobKartasi
                key={k}
                url={rasmUrllar[it.rasm_idx]}
                raqam={it.raqam}
                birlik={it.birlik}
                savolIdx={it.savol_idx}
                javoblar={javoblar}
                javobniQoy={javobniQoy}
                blokNatija={blokNatija}
              />
            ))}
          </div>
          {savolIdxlari.length > 0 && (
            <div className="blok-rasm-javobli-tek">
              {blokNatija ? (
                <div className="izoh blok-mashq-natija">
                  {savolIdxlari.filter((i) => blokNatija.natijalar[i]).length}/{savolIdxlari.length} {"correct"}
                </div>
              ) : (
                <button
                  type="button"
                  className="tugma ikkinchi kichik"
                  onClick={() => tekshir(blokIdx, savolIdxlari)}
                  disabled={yuborilayotganBlok === blokIdx}
                >
                  {yuborilayotganBlok === blokIdx ? "Checking…" : "Check"}
                </button>
              )}
            </div>
          )}
        </div>
      );
    }
    case "mashq": {
      // 2026-08-16, foydalanuvchi talabi: bir nechta so'zlovchili suhbat
      // (masalan "Check it" — A/B/C) HAR BIRI O'Z QATORIDAN boshlansin,
      // bitta uzun oqim sifatida emas. "qatorlar" bo'lsa — har biri
      // ({"bolaklar":[...]}) ALOHIDA qatorda chiqadi, hammasi bitta
      // umumiy Tekshirish tugmasini ulashadi (xuddi "grammar_spot"dagi
      // kabi). "bolaklar" (yagona, eski) hamon ishlaydi — orqaga moslik.
      const qatorlarRoyxati = blok.qatorlar
        ? blok.qatorlar.map((q) => q.bolaklar || [])
        : [blok.bolaklar || []];
      const bolaklar = qatorlarRoyxati.flat();
      const savolIdxlari = bolaklar.filter((b) => b.bosh_joy && !b.erkin).map((b) => b.savol_idx);
      const blokNatija = blokNatijalar[blokIdx];
      // 2026-08-16, foydalanuvchi talabi: mingle/roleplay mashqlari
      // (masalan "___, this is ___.") kitobdagi kabi suhbat pufakchasi
      // ko'rinishida chiqsin — oddiy chizilgan (dashed) qutidan farqli.
      // `blok.kim` bo'lsa (masalan "A"/"B" yoki ism) pufakcha ustida
      // kichik yorliq sifatida ko'rsatiladi — dialog/monolog ekani
      // ko'rinib turishi uchun.
      if (blok.bulut) {
        return (
          <div className="blok-pufakcha-mashq">
            {blok.kim && <span className="blok-pufakcha-kim">{blok.kim}</span>}
            {audioBelgi}
            <Bolaklar bolaklar={bolaklar} javoblar={javoblar} javobniQoy={javobniQoy} blokNatija={blokNatija} />
            {savolIdxlari.length > 0 && (
              blokNatija ? (
                <span className="izoh blok-mashq-natija">
                  {savolIdxlari.filter((i) => blokNatija.natijalar[i]).length}/{savolIdxlari.length} {"correct"}
                </span>
              ) : (
                <button
                  type="button"
                  className="tugma ikkinchi kichik"
                  onClick={() => tekshir(blokIdx, savolIdxlari)}
                  disabled={yuborilayotganBlok === blokIdx}
                >
                  {yuborilayotganBlok === blokIdx ? "Checking…" : "Check"}
                </button>
              )
            )}
          </div>
        );
      }
      return (
        <div className="blok-mashq-blok">
          <div className="blok-mashq">
            {audioBelgi}
            {qatorlarRoyxati.map((qatorBolaklari, qi) => (
              <div key={qi} className="blok-mashq-qator">
                <Bolaklar bolaklar={qatorBolaklari} javoblar={javoblar} javobniQoy={javobniQoy} blokNatija={blokNatija} />
              </div>
            ))}
          </div>
          {savolIdxlari.length > 0 && (
            blokNatija ? (
              <div className="izoh blok-mashq-natija">
                {savolIdxlari.filter((i) => blokNatija.natijalar[i]).length}/{savolIdxlari.length} {"correct"}
              </div>
            ) : (
              <button
                type="button"
                className="tugma ikkinchi kichik"
                onClick={() => tekshir(blokIdx, savolIdxlari)}
                disabled={yuborilayotganBlok === blokIdx}
              >
                {yuborilayotganBlok === blokIdx ? "Checking…" : "Check"}
              </button>
            )
          )}
        </div>
      );
    }
    default:
      return blok.matn ? <div className="blok-matn">{blok.matn}</div> : null;
  }
}

export default function BlokMashqi({ mashq, raqam }) {
  const { t } = useI18n();
  const [javoblar, setJavoblar] = useState(() => mashq.savollar.map(() => ""));
  // Har blok o'z natijasini mustaqil saqlaydi (blokIdx -> {ball,jami,natijalar})
  // — boshqa bloklar shu bilan bog'liq emas, tahrirlanadigan holicha qoladi.
  const [blokNatijalar, setBlokNatijalar] = useState({});
  const [yuborilayotganBlok, setYuborilayotganBlok] = useState(null);
  const [rasmUrllar, setRasmUrllar] = useState({});
  const [audioUrllar, setAudioUrllar] = useState({});
  const [tayyor, setTayyor] = useState(false);
  const [xato, setXato] = useState("");

  // Umumiy audio pleyer holati (2026-07-29) — bitta <audio>, inline
  // belgilar faqat shuni boshqaradi.
  const [faolRaqam, setFaolRaqam] = useState(null);
  const [ijro, setIjro] = useState(false);
  const audioRef = useRef(null);

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

  function audioTanla(trekRaqami) {
    const a = audioRef.current;
    if (!a) return;
    if (trekRaqami === faolRaqam) {
      // Xuddi shu trek — play/pause almashtiriladi.
      if (ijro) a.pause();
      else a.play();
      return;
    }
    setFaolRaqam(trekRaqami);
    // src o'zgarishi useEffect orqali ishlaydi, keyin play chaqiriladi.
  }

  useEffect(() => {
    const a = audioRef.current;
    if (!a || !faolRaqam) return;
    const url = audioUrllar[faolRaqam];
    if (!url) return;
    a.src = url;
    a.play().catch(() => {});
  }, [faolRaqam, audioUrllar]);

  async function tekshir(blokIdx) {
    setXato("");
    setYuborilayotganBlok(blokIdx);
    try {
      const natija = await api(`/api/kurslar/mashq/${mashq.id}/yechish/`, {
        method: "POST",
        body: { javoblar },
      });
      setBlokNatijalar((b) => ({ ...b, [blokIdx]: natija }));
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuborilayotganBlok(null);
    }
  }

  // 2026-08-10: admin "past" (matn ostida) deb belgilagan rasm bloklari
  // mashq OXIRIGA suriladi — asl indeksi (`k`) saqlanadi, chunki
  // `blokNatijalar`/`tekshir` shu indeks bo'yicha ishlaydi.
  const xomBloklar = mashq.bloklar || [];
  const pastmi = (b) => b.tur === "rasm" && b.tomon === "past";
  const bloklar = [
    ...xomBloklar.map((b, k) => [b, k]).filter(([b]) => !pastmi(b)),
    ...xomBloklar.map((b, k) => [b, k]).filter(([b]) => pastmi(b)),
  ];

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
          {bloklar.map(([b, k]) => (
            <Blok
              key={k}
              blok={b}
              blokIdx={k}
              rasmUrllar={rasmUrllar}
              faolRaqam={faolRaqam}
              ijro={ijro}
              audioTanla={audioTanla}
              javoblar={javoblar}
              javobniQoy={javobniQoy}
              blokNatijalar={blokNatijalar}
              tekshir={tekshir}
              yuborilayotganBlok={yuborilayotganBlok}
              t={t}
            />
          ))}
          {xato && <div className="xato-xabar">{xato}</div>}

          {/* Umumiy audio — bitta element, faqat pastdagi panel orqali
              ko'rinadi. onPlay global "faqat bitta audio" mexanizmiga
              ulanadi (2026-07-29) — sahifada boshqa audio chalinsa, bu
              to'xtaydi va aksincha. */}
          <audio
            ref={audioRef}
            onPlay={(e) => {
              faqatBittaAudioIjro(e.target);
              setIjro(true);
            }}
            onPause={() => setIjro(false)}
            onEnded={() => setIjro(false)}
          />
        </>
      )}

      {faolRaqam && (
        <div className="blok-audio-panel">
          <button
            type="button"
            className="blok-audio-panel-tugma"
            onClick={() => audioTanla(faolRaqam)}
          >
            <span aria-hidden="true">{ijro ? "⏸" : "▶"}</span>
          </button>
          <span className="blok-audio-panel-raqam">{faolRaqam}</span>
        </div>
      )}
    </div>
  );
}
