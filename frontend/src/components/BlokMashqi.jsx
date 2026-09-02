import { useEffect, useRef, useState } from "react";
import { api, apiBlobUrl } from "../api";
import { faqatBittaAudioIjro } from "../audio";
import { useI18n } from "../i18n";
import { IMLO_OFF } from "../imlo";

/** Blok formatidagi darslik sahifasi (2026-07-28, audio/tekshirish
 * qismlari 2026-07-29 da, tekshirish tugmasi 2026-08-17 da qayta
 * ishlandi).
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
 * TEKSHIRISH (2026-08-17 talabi — 2026-07-29dagi "har blok o'z tugmasi"
 * qarori BEKOR QILINDI): endi HAR MAVZU (butun sahifa/`KursMashq`) uchun
 * BITTA umumiy Tekshirish tugmasi bor, pastda. Bosilganda BUTUN
 * sahifadagi barcha bo'sh joylar bir vaqtda tekshiriladi va natija
 * (to'g'ri/noto'g'ri rangi) barcha bloklarga birdek qo'llaniladi. */

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
function RasmJavobKartasi({ url, raqam, birlik, izoh, namuna, savolIdx, javoblar, javobniQoy, natija }) {
  const holat = natija ? (natija.natijalar[savolIdx] ? "togri" : "notogri") : "";
  return (
    <div className="blok-rasm-javobli-karta">
      {raqam && <div className="blok-rasm-javobli-raqam">{raqam}</div>}
      {url && <img className="blok-rasm" src={url} alt="" />}
      {/* 2026-08-22, foydalanuvchi talabi: rasm nomi/izohi mashqda
          umuman ko'rinmasin (talabaga keraksiz ichki yozuv bo'lib
          chiqadi) — endi hech qachon chizilmaydi, faqat ma'lumot
          sifatida saqlanadi. */}
      <div className="blok-rasm-javobli-javob-qatori">
        {/* 2026-08-18, foydalanuvchi talabi: kitobda BIRINCHI rasm javobi
            namuna sifatida allaqachon yozilgan bo'ladi (masalan "1 a
            businessman") — u kiritish maydoni emas, tagi chizilgan
            tayyor matn bo'lib chiqsin (mashq qatoridagi `namuna` bilan
            bir xil ko'rinish). */}
        {namuna ? (
          <span className="blok-dialog-namuna">{namuna}</span>
        ) : (
          <input
            {...IMLO_OFF}
            className={`blok-bosh-joy ${holat}`}
            value={javoblar[savolIdx] || ""}
            disabled={!!natija}
            onChange={(e) => javobniQoy(savolIdx, e.target.value)}
          />
        )}
        {/* 2026-08-16, foydalanuvchi talabi: kitobdagi kabi otning o'zi
            statik yozilgan, faqat SON kiritiladi (masalan "___ books"). */}
        {birlik && <span className="blok-rasm-javobli-birlik">{birlik}</span>}
      </div>
    </div>
  );
}

/** Moslashtirish mashqi (2026-08-17, foydalanuvchi talabi: kitobdagi
 * "chiziq tortib moslashtirish" — chapdan bandni, keyin o'ngdan mos
 * javobni bosish orqali "bog'lanadi", ular orasiga SVG chiziq chiziladi.
 * Javob xuddi oddiy matn kiritilgandek `javobniQoy(savol_idx, matn)`
 * orqali saqlanadi — backend tekshiruvi o'zgarishsiz ishlaydi. */
function Moslashtirish({ chap, ong, javoblar, javobniQoy, natija }) {
  const [tanlanganChap, setTanlanganChap] = useState(null);
  const [chiziqlar, setChiziqlar] = useState([]);
  const contRef = useRef(null);
  const chapRefs = useRef([]);
  const ongRefs = useRef([]);

  const hisoblaChiziqlar = () => {
    if (!contRef.current) return;
    const contRect = contRef.current.getBoundingClientRect();
    const yangi = [];
    chap.forEach((item, i) => {
      const javob = javoblar[item.savol_idx];
      if (!javob) return;
      const ongIdx = ong.indexOf(javob);
      const a = chapRefs.current[i];
      const b = ongRefs.current[ongIdx];
      if (ongIdx === -1 || !a || !b) return;
      const ar = a.getBoundingClientRect();
      const br = b.getBoundingClientRect();
      yangi.push({
        x1: ar.right - contRect.left, y1: ar.top - contRect.top + ar.height / 2,
        x2: br.left - contRect.left, y2: br.top - contRect.top + br.height / 2,
        savolIdx: item.savol_idx,
      });
    });
    setChiziqlar(yangi);
  };

  useEffect(() => {
    hisoblaChiziqlar();
    window.addEventListener("resize", hisoblaChiziqlar);
    return () => window.removeEventListener("resize", hisoblaChiziqlar);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [javoblar, natija]);

  const chapBosildi = (i) => {
    if (natija) return;
    setTanlanganChap(tanlanganChap === i ? null : i);
  };
  const ongBosildi = (matn) => {
    if (natija || tanlanganChap === null) return;
    javobniQoy(chap[tanlanganChap].savol_idx, matn);
    setTanlanganChap(null);
  };

  return (
    <div className="blok-moslashtir" ref={contRef}>
      <svg className="blok-moslashtir-svg">
        {chiziqlar.map((c, k) => {
          const holat = natija ? (natija.natijalar[c.savolIdx] ? "togri" : "notogri") : "";
          const orta = (c.x1 + c.x2) / 2;
          return (
            <path
              key={k}
              className={`blok-moslashtir-chiziq ${holat}`}
              d={`M ${c.x1} ${c.y1} C ${orta} ${c.y1}, ${orta} ${c.y2}, ${c.x2} ${c.y2}`}
              fill="none"
            />
          );
        })}
      </svg>
      <div className="blok-moslashtir-ustun">
        {chap.map((item, i) => (
          <button
            key={i}
            type="button"
            ref={(el) => (chapRefs.current[i] = el)}
            className={`blok-moslashtir-band ${tanlanganChap === i ? "tanlangan" : ""}`}
            disabled={!!natija}
            onClick={() => chapBosildi(i)}
          >
            {item.matn}
          </button>
        ))}
      </div>
      <div className="blok-moslashtir-ustun blok-moslashtir-ustun-ong">
        {ong.map((matn, i) => (
          <button
            key={i}
            type="button"
            ref={(el) => (ongRefs.current[i] = el)}
            className="blok-moslashtir-band"
            disabled={!!natija}
            onClick={() => ongBosildi(matn)}
          >
            {matn}
          </button>
        ))}
      </div>
    </div>
  );
}

const RAQAM_RANGLARI = [
  "#7EC8C0", "#8FCB8C", "#C7DE8C", "#E8B87A", "#E29B9B",
  "#E7A8CB", "#B9A8DB", "#8FB6D8", "#6FB8DE", "#9AD1D6",
];

/** Statik rangli raqam-kartalar (2026-08-17, foydalanuvchi talabi:
 * kitobdagi kabi "11 eleven, 12 twelve..." rangli kartochkalarda,
 * oddiy matn qatori emas). Faqat ko'rsatish uchun, javob yo'q. */
function RaqamKartalari({ itemlar }) {
  return (
    <div className="blok-raqam-kartalari">
      {itemlar.map((it, k) => (
        <div key={k} className="blok-raqam-karta" style={{ background: RAQAM_RANGLARI[k % RAQAM_RANGLARI.length] }}>
          <div className="blok-raqam-katta">{it.raqam}</div>
          <div className="blok-raqam-soz">{it.soz}</div>
        </div>
      ))}
    </div>
  );
}

/** "Eshitib, to'g'ri raqamni belgilang" — o'yin kartochkalaridagi kabi,
 * har qatorda bitta sonni bosib tanlash (2026-08-17, foydalanuvchi
 * talabi). Tanlangan songa ✓ chiqadi, Tekshirish bosilganda shu
 * tanlovning to'g'ri/noto'g'riligi rangda ko'rsatiladi. */
function RaqamTanlash({ qatorlar, javoblar, javobniQoy, natija, keng }) {
  return (
    <div className={`blok-raqam-tanlash ${keng ? "keng" : ""}`}>
      {qatorlar.map((q, qi) => {
        const tanlangan = javoblar[q.savol_idx];
        const holat = natija ? (natija.natijalar[q.savol_idx] ? "togri" : "notogri") : "";
        return (
          <div key={qi} className="blok-raqam-tanlash-qator">
            {q.raqam && <span className="blok-raqam-tanlash-raqam">{q.raqam}</span>}
            {/* 2026-09-02: qator matni ("Richard still hasn't arrived. Do you
                think I should/must call him?") umuman chizilmasdi — talaba
                faqat raqam va ikkita variantni ko'rar, gapning o'zini
                ko'rmasdi (U5 SB p51 vizual tekshiruvida topildi). */}
            {q.matn && <span className="blok-raqam-tanlash-matn">{q.matn}</span>}
            {(q.variantlar || []).map((v, vi) => {
              const tanlanganMi = tanlangan === v;
              return (
                <button
                  key={vi}
                  type="button"
                  className={`blok-raqam-tanlash-band ${tanlanganMi ? "tanlangan" : ""} ${tanlanganMi ? holat : ""}`}
                  disabled={!!natija}
                  onClick={() => javobniQoy(q.savol_idx, v)}
                >
                  {/* 2026-08-18, foydalanuvchi talabi: variantning O'ZI
                      ✓ yoki ✗ bo'lishi mumkin ("Tick or cross") — bunda
                      yoniga yana ✓ qo'yilsa "✓ ✓" / "✗ ✓" bo'lib
                      chalkashtirardi. Tanlangani sariq fon bilan
                      allaqachon ajralib turadi, qo'shimcha belgi KERAK EMAS. */}
                  {v}
                </button>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

function Bolaklar({ bolaklar, javoblar, javobniQoy, natija }) {
  return (
    <>
      {bolaklar.map((b, k) => {
        if (!b.bosh_joy) {
          // 2026-08-17, foydalanuvchi talabi: kitobdagi kabi namuna
          // sifatida ISHLATILGAN so'z (masalan "the _weather_!") tagiga
          // chizilgan holda ajratib ko'rsatiladi.
          if (b.namuna) return <span key={k} className="blok-dialog-namuna">{b.matn}</span>;
          return <span key={k}>{b.matn}</span>;
        }
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

function Blok({ blok, rasmUrllar, faolRaqam, ijro, audioTanla, javoblar, javobniQoy, natija }) {
  const audioBelgi = blok.audio_raqam ? (
    <AudioBelgi raqam={blok.audio_raqam} faolRaqam={faolRaqam} ijro={ijro} tanla={audioTanla} />
  ) : null;

  switch (blok.tur) {
    case "sarlavha":
      return <h3 className="blok-sarlavha">{blok.matn}</h3>;
    case "bolim_sarlavha":
      return <h4 className="blok-bolim">{blok.matn}</h4>;
    case "kichik_sarlavha":
      return <h5 className="blok-kichik">{blok.matn}</h5>;
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
          className={suzuvchi ? "blok-rasm-izoh-qatori blok-rasm-suzuvchi" : "blok-rasm-izoh-qatori"}
          style={suzuvchi ? {
            float: tomon === "chap" ? "left" : "right",
            maxWidth: "42%",
            [tomon === "chap" ? "marginRight" : "marginLeft"]: 12,
            marginBottom: 8,
          } : undefined}
        >
          {/* 2026-08-17, foydalanuvchi talabi: Unit boshlanish (muqova)
              rasmi kattaroq chiqsin — `katta:true` bo'lsa maxsus klass. */}
          <img
            className={blok.katta ? "blok-rasm blok-rasm-katta" : "blok-rasm"}
            src={url}
            alt={blok.izoh || ""}
          />
          {/* 2026-08-22, foydalanuvchi talabi: izoh mashqda ko'rinmasin. */}
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
      // 2026-08-30, Shuxrat talabi: suhbat qatorlari DB'da ikki xil kalit
      // shaklida uchraydi — asosiysi {kim, gap}, lekin Elementary Unit 9
      // SB seed'ida {kishi, matn} ishlatilgan. Render faqat birinchisini
      // bilgani uchun o'sha 15 qator talabaga BUTUNLAY ko'rinmay qolar edi
      // (mashq 1222 va 1224). Shu yerda bir shaklga keltiramiz.
      const qatorlar = (blok.qatorlar || []).map((q) =>
        q && typeof q === "object" && (q.kishi !== undefined || q.matn !== undefined)
          ? { ...q, kim: q.kim ?? q.kishi, gap: q.gap ?? q.matn }
          : q,
      );
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
                {/* 2026-08-26: bu yerda ham qator `bolaklar` (bo'sh joyli)
                    bo'lishi mumkin — pastdagi izohga qarang. */}
                {q.bolaklar ? (
                  <Bolaklar bolaklar={q.bolaklar} javoblar={javoblar} javobniQoy={javobniQoy} natija={natija} />
                ) : (
                  q.gap
                )}
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
              {/* 2026-08-26: suhbat qatori `gap` (oddiy matn) O'RNIGA
                  `bolaklar` (bo'sh joyli) bo'lishi ham mumkin — avval
                  faqat `q.gap` chizilgani uchun bunday qatorlar
                  butunlay KO'RINMAY qolar edi (U4 SB s2 / WB s2, s3,
                  U6 SB s8 — jami 33 qator). */}
              {q.bolaklar ? (
                <Bolaklar bolaklar={q.bolaklar} javoblar={javoblar} javobniQoy={javobniQoy} natija={natija} />
              ) : (
                <span className={q.namuna ? "blok-dialog-namuna" : undefined}>{q.gap}</span>
              )}
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
      // 2026-08-18, foydalanuvchi talabi: kitobda GRAMMAR SPOT ICHIDA ham
      // audio tugmasi bo'ladi (masalan SB p54: "6.6 Listen to the verbs
      // and repeat."). Avval bu shox audio belgisini umuman chizmasdi,
      // shuning uchun trek raqami oddiy matn bo'lib yozilardi va talaba
      // uni ESHITA OLMASDI. Endi qator obyekt bo'lsa va `audio_raqam`
      // bo'lsa — o'sha qatorda haqiqiy ▶ tugmasi chiqadi.
      return (
        <div className="blok-gs">
          <div className="blok-gs-bosh">{blok.sarlavha || "GRAMMAR SPOT"}</div>
          {audioBelgi}
          <div className="blok-gs-tan">
            {(blok.qatorlar || []).map((q, k) => {
              const qAudio = typeof q === "object" && q.audio_raqam ? (
                <AudioBelgi raqam={q.audio_raqam} faolRaqam={faolRaqam} ijro={ijro} tanla={audioTanla} />
              ) : null;
              if (typeof q === "object" && q.bolaklar) {
                return (
                  <div key={k}>
                    {qAudio}
                    <Bolaklar bolaklar={q.bolaklar} javoblar={javoblar} javobniQoy={javobniQoy} natija={natija} />
                  </div>
                );
              }
              return (
                <div key={k}>
                  {qAudio}
                  {typeof q === "string" ? q : q.matn}
                </div>
              );
            })}
          </div>
        </div>
      );
    }
    case "moslashtir":
      return (
        <Moslashtirish
          chap={blok.chap || []}
          ong={blok.ong || []}
          javoblar={javoblar}
          javobniQoy={javobniQoy}
          natija={natija}
        />
      );
    case "raqam_kartalari":
      return <RaqamKartalari itemlar={blok.itemlar || []} />;
    case "raqam_tanlash":
      return (
        <RaqamTanlash
          qatorlar={blok.qatorlar || []}
          javoblar={javoblar}
          javobniQoy={javobniQoy}
          natija={natija}
        />
      );
    case "tanlov":
      // 2026-08-17, foydalanuvchi talabi: "Tick the correct sentence"
      // kabi ikki variantli mashqlar — matn kiritish o'rniga variantning
      // USTIGA BOSILADI, tanlangani sariq rangga aylanadi va yoniga ✓
      // chiqadi (raqam_tanlash bilan bir xil mexanika, matn variantlar).
      return (
        <RaqamTanlash
          qatorlar={blok.qatorlar || []}
          javoblar={javoblar}
          javobniQoy={javobniQoy}
          natija={natija}
          keng
        />
      );
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
            {/* 2026-08-18, foydalanuvchi talabi: kitobdagi to'ldiriladigan
                jadval (masalan "Listen and complete the chart") — katak
                oddiy matn (string), bo'sh joyli mashq bo'lagi
                ({"bolaklar": [...]}) YOKI namuna sifatida tayyor javob
                ({"matn": "...", "namuna": true}) bo'lishi mumkin. */}
            {qatorlar.map((q, k) => (
              <tr key={k}>
                {q.map((c, ci) => (
                  <td key={ci}>
                    {c && typeof c === "object" && c.bolaklar ? (
                      <Bolaklar bolaklar={c.bolaklar} javoblar={javoblar} javobniQoy={javobniQoy} natija={natija} />
                    ) : c && typeof c === "object" && c.namuna ? (
                      <span className="blok-dialog-namuna">{c.matn}</span>
                    ) : (
                      c
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    case "soz_banki":
      return (
        <div className="blok-soz-banki">
          {(blok.sozlar || blok.qatorlar || []).map((s, k) => {
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
    case "rasm_javobli":
      return (
        <div className="blok-mashq-blok">
          <RasmJavobKartasi
            url={rasmUrllar[blok.rasm_idx]}
            raqam={blok.raqam}
            namuna={blok.namuna}
            savolIdx={blok.savol_idx}
            javoblar={javoblar}
            javobniQoy={javobniQoy}
            natija={natija}
          />
        </div>
      );
    case "rasm_javobli_grid": {
      const itemlar = blok.itemlar || [];
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
                izoh={it.izoh}
                namuna={it.namuna}
                savolIdx={it.savol_idx}
                javoblar={javoblar}
                javobniQoy={javobniQoy}
                natija={natija}
              />
            ))}
          </div>
        </div>
      );
    }
    // 2026-08-26: `gap` — Unit 5 seed'ida ishlatilgan bo'sh joyli suhbat
    // QATORI (shakli `mashq`ning eski yagona `bolaklar` ko'rinishi bilan
    // bir xil). Renderda `case` bo'lmagani uchun butun Unit 5 mashq
    // kontenti talabaga KO'RINMAY qolgan edi. Ketma-ket suhbat
    // qatorlari bo'lgani uchun har birini alohida chizilgan qutiga
    // solmasdan, oddiy qator sifatida chiqaramiz.
    case "gap":
      return (
        <div className="blok-mashq-qator">
          {audioBelgi}
          <Bolaklar bolaklar={blok.bolaklar || []} javoblar={javoblar} javobniQoy={javobniQoy} natija={natija} />
        </div>
      );
    case "mashq": {
      // 2026-08-16, foydalanuvchi talabi: bir nechta so'zlovchili suhbat
      // (masalan "Check it" — A/B/C) HAR BIRI O'Z QATORIDAN boshlansin,
      // bitta uzun oqim sifatida emas. "qatorlar" bo'lsa — har biri
      // ({"bolaklar":[...]}) ALOHIDA qatorda chiqadi. "bolaklar" (yagona,
      // eski) hamon ishlaydi — orqaga moslik.
      const qatorlarRoyxati = blok.qatorlar
        ? blok.qatorlar.map((q) => q.bolaklar || [])
        : [blok.bolaklar || []];
      const bolaklar = qatorlarRoyxati.flat();
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
            <Bolaklar bolaklar={bolaklar} javoblar={javoblar} javobniQoy={javobniQoy} natija={natija} />
          </div>
        );
      }
      return (
        <div className="blok-mashq-blok">
          <div className="blok-mashq">
            {audioBelgi}
            {qatorlarRoyxati.map((qatorBolaklari, qi) => (
              <div key={qi} className="blok-mashq-qator">
                <Bolaklar bolaklar={qatorBolaklari} javoblar={javoblar} javobniQoy={javobniQoy} natija={natija} />
              </div>
            ))}
          </div>
        </div>
      );
    }
    default:
      return blok.matn ? <div className="blok-matn">{blok.matn}</div> : null;
  }
}

/** `javoblarOchiq` (2026-08-18, foydalanuvchi talabi) — O'QITUVCHI
 * ko'rinishi: sahifa talaba ko'rgan bilan bir xil chiziladi, lekin bo'sh
 * joylar to'g'ri javob bilan oldindan to'ldirilgan va "Check" tugmasi
 * chiqmaydi (javob yuborish backendda faqat TALABAGA ruxsat etilgan). */
export default function BlokMashqi({ mashq, raqam, javoblarOchiq }) {
  const { t } = useI18n();
  const [javoblar, setJavoblar] = useState(() =>
    mashq.savollar.map((s) => (javoblarOchiq ? s.togri || "" : "")),
  );
  // 2026-08-17, foydalanuvchi talabi: endi BUTUN sahifa uchun BITTA
  // natija (avval har blok o'z natijasini mustaqil saqlar edi).
  const [natija, setNatija] = useState(null);
  const [yuborilmoqda, setYuborilmoqda] = useState(false);
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

  async function tekshir() {
    setXato("");
    setYuborilmoqda(true);
    try {
      const d = await api(`/api/kurslar/mashq/${mashq.id}/yechish/`, {
        method: "POST",
        body: { javoblar },
      });
      setNatija(d);
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuborilmoqda(false);
    }
  }

  // 2026-08-10: admin "past" (matn ostida) deb belgilagan rasm bloklari
  // mashq OXIRIGA suriladi.
  const xomBloklar = mashq.bloklar || [];
  // 2026-08-16, foydalanuvchi talabi: pastdagi (sticky) audio panelida
  // qaysi mavzu ekani ham yozilib tursin — sahifaning birinchi
  // sarlavha/bo'lim sarlavhasi shu maqsadda ishlatiladi.
  const mavzu = xomBloklar.find((b) => b.tur === "sarlavha" || b.tur === "bolim_sarlavha")?.matn;
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
          {/* 2026-08-21, foydalanuvchi talabi: chap/o'ng tomonga
              "suzuvchi" (float) rasm mobil ekranda dialog matnini
              torайтirib, ustiga chiqib qolardi — `.blok-oqim` mobilda
              flex-column'ga o'tadi (float flex ichida ishlamaydi,
              o'zi ham to'liq kenglikka qaytadi) va `blok-rasm-suzuvchi`
              CSS orqali oqim OXIRIGA (dialogdan keyinga) suriladi. */}
          <div className="blok-oqim">
            {bloklar.map(([b, k]) => (
              <Blok
                key={k}
                blok={b}
                rasmUrllar={rasmUrllar}
                faolRaqam={faolRaqam}
                ijro={ijro}
                audioTanla={audioTanla}
                javoblar={javoblar}
                javobniQoy={javobniQoy}
                natija={natija}
              />
            ))}
          </div>
          {xato && <div className="xato-xabar">{xato}</div>}

          {/* 2026-08-17, foydalanuvchi talabi: HAR MAVZU (sahifa) uchun
              BITTA umumiy Tekshirish tugmasi. */}
          {mashq.savollar.length > 0 && !javoblarOchiq && (
            <div className="blok-umumiy-tekshirish">
              {natija ? (
                <div className="izoh blok-umumiy-natija">
                  {natija.ball}/{natija.jami} {t("natija_togri")}
                </div>
              ) : (
                <button
                  type="button"
                  className="tugma"
                  onClick={tekshir}
                  disabled={yuborilmoqda}
                >
                  {yuborilmoqda ? t("tekshirilmoqda") : t("tekshirish")}
                </button>
              )}
            </div>
          )}

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
          {mavzu && <span className="blok-audio-panel-mavzu">{mavzu}</span>}
          <button
            type="button"
            className="blok-audio-panel-yopish"
            title="Yopish"
            onClick={() => {
              audioRef.current?.pause();
              setFaolRaqam(null);
            }}
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
