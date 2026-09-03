import { useEffect, useRef, useState } from "react";
import { api, apiBlobUrl } from "../api";
import { AUDIO_HIMOYA, faqatBittaAudioIjro } from "../audio";
import { useI18n } from "../i18n";
import { IMLO_OFF } from "../imlo";
import { standartVaqt } from "../imtihonVaqt";
import { useTestRejimi } from "../testRejimiContext";

export function vaqtFormat(soniya) {
  const m = Math.floor(soniya / 60)
    .toString()
    .padStart(2, "0");
  const s = (soniya % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

// Bitta bo'lim vaqti tugab, avtomatik tekshirilgandan keyin (Mock ichida)
// ko'rsatiladigan bloklovchi oyna — bitta "Keyingisi" tugmasi, ustida 30
// soniyalik teskari sanoq, 0 ga yetganda AVTOMATIK keyingi bo'limga
// o'tadi. Tugmani qo'lda bosish ham mumkin (2026-08-15, VAQT TUGAGANDA
// MAJBURIY YAKUNLASH ishi, foydalanuvchi bilan 2026-08-14 kelishilgan).
export function VaqtTugadiModal({ onKeyingisi, t }) {
  const [qoldi, setQoldi] = useState(30);

  useEffect(() => {
    if (qoldi <= 0) {
      onKeyingisi();
      return;
    }
    const id = setTimeout(() => setQoldi((q) => q - 1), 1000);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qoldi]);

  return (
    <div className="imtihon-vaqt-modal-fon">
      <div className="imtihon-vaqt-modal">
        <h3>{t("vaqt_tugadi_bolim_sarlavha")}</h3>
        <p>{t("vaqt_tugadi_bolim_izoh")}</p>
        <button className="tugma katta" onClick={onKeyingisi}>
          {t("keyingisi_sanoq").replace("{n}", qoldi)}
        </button>
      </div>
    </div>
  );
}

// Konteyner ichidagi (node, offset) DOM nuqtasini butun matnning tekis
// belgi-indeksiga aylantiradi — highlight range'larini matn ustida
// hisoblash uchun kerak (2026-08-02).
function belgiIndeksiniTop(container, node, offset) {
  let jami = 0;
  let topildi = -1;
  function chuqurlashtir(el) {
    for (const bola of el.childNodes) {
      if (bola === node) {
        topildi = jami + offset;
        return true;
      }
      if (bola.nodeType === Node.TEXT_NODE) {
        jami += bola.textContent.length;
      } else if (chuqurlashtir(bola)) {
        return true;
      }
    }
    return false;
  }
  chuqurlashtir(container);
  return topildi;
}

// Har highlight endi o'z rangiga ega bo'lishi mumkin (2026-08-02) — shu
// sababli kesishganlarni bir rangga BIRLASHTIRISH noto'g'ri (ikki xil rang
// aralashib ketadi). O'rniga: yangi tanlov eski range bilan kesishsa, eski
// range'ning kesishgan qismi olib tashlanadi/bo'linadi — yangi tanlov
// g'olib chiqadi. Bu bir vaqtda "bir joyni qayta boshqa rangga belgilash"
// (recolor) imkonini ham beradi.
function RANGLAR() {
  return [
    { kalit: "sariq", rang: "#ffe58a" },
    { kalit: "yashil", rang: "#a8e6a3" },
    { kalit: "kok", rang: "#a3d8f4" },
    { kalit: "pushti", rang: "#f4a3c4" },
  ];
}

function rangeQoshVaKesish(royxat, yangi) {
  const natija = [];
  for (const r of royxat) {
    if (r.end <= yangi.start || r.start >= yangi.end) {
      natija.push(r);
      continue;
    }
    if (r.start < yangi.start) natija.push({ ...r, end: yangi.start });
    if (r.end > yangi.end) natija.push({ ...r, start: yangi.end });
  }
  natija.push(yangi);
  return natija;
}

/** Reading passage matnini sichqoncha bilan belgilab (highlight) olish
 * imkonini beradi — faqat shu test-sessiyasi davomida (sessionStorage),
 * sahifa yopilsa yo'qoladi. Mavjud belgini bosish — o'chiradi.
 *
 * Matn tanlanganda highlight AVTOMATIK qo'yilmaydi (oldin shunday edi —
 * so'zga ikki marta bosish ham tanlov hisoblanib, xohlamasdan belgilab
 * qo'yardi) — o'rniga tanlov yonida rang tanlash paneli chiqadi, faqat
 * rang bosilganda shu rangda highlight qo'yiladi (2026-08-02). Mavjud
 * belgiga qayta boshqa rang tanlash — eskisini kesib, ustidan yozadi.
 *
 * Chaqiruvchi HAR passage uchun `key={matnId}` bilan render qilishi
 * SHART — aks holda komponent qayta ishlatilib, oldingi passage'ning
 * range (start/end) ro'yxati yangi matnga o'sha joylarda qo'llanadi
 * (haqiqiy bug, 2026-08-02 foydalanuvchi tomonidan topilgan). */
function BelgilanadiganMatn({ matnId, matn, sinf }) {
  const kalitRef = useRef(`reading-belgi-${matnId}`);
  const konteynerRef = useRef(null);
  const [royxat, setRoyxat] = useState(() => {
    try {
      const saqlangan = sessionStorage.getItem(kalitRef.current);
      return saqlangan ? JSON.parse(saqlangan) : [];
    } catch {
      return [];
    }
  });
  const [marker, setMarker] = useState(null); // {start, end, x, y}

  useEffect(() => {
    try {
      sessionStorage.setItem(kalitRef.current, JSON.stringify(royxat));
    } catch {
      // sessionStorage to'lgan bo'lsa — jim o'tkazib yuboramiz, kritik emas.
    }
  }, [royxat]);

  function tanlovTugaganda() {
    const tanlov = window.getSelection();
    if (!tanlov || tanlov.isCollapsed || tanlov.rangeCount === 0) {
      setMarker(null);
      return;
    }
    const range = tanlov.getRangeAt(0);
    if (!konteynerRef.current || !konteynerRef.current.contains(range.commonAncestorContainer)) {
      setMarker(null);
      return;
    }
    let start = belgiIndeksiniTop(konteynerRef.current, range.startContainer, range.startOffset);
    let end = belgiIndeksiniTop(konteynerRef.current, range.endContainer, range.endOffset);
    if (start === -1 || end === -1) {
      setMarker(null);
      return;
    }
    if (start > end) [start, end] = [end, start];
    if (start === end) {
      setMarker(null);
      return;
    }
    const chegara = range.getBoundingClientRect();
    const konteynerChegara = konteynerRef.current.getBoundingClientRect();
    setMarker({
      start,
      end,
      x: chegara.left - konteynerChegara.left + chegara.width / 2,
      y: chegara.top - konteynerChegara.top,
    });
  }

  function rangniBelgila(rang) {
    if (!marker) return;
    setRoyxat((prev) => rangeQoshVaKesish(prev, { start: marker.start, end: marker.end, rang }));
    setMarker(null);
    window.getSelection()?.removeAllRanges();
  }

  function belginiOchir(r, e) {
    e.stopPropagation();
    setRoyxat((prev) => prev.filter((x) => x !== r));
  }

  const qismlar = [];
  let joriy = 0;
  const tartiblangan = [...royxat].sort((a, b) => a.start - b.start);
  tartiblangan.forEach((r, i) => {
    if (r.start > joriy) qismlar.push(<span key={`o-${i}`}>{matn.slice(joriy, r.start)}</span>);
    qismlar.push(
      <mark
        className="reading-belgilangan"
        key={`m-${i}`}
        style={{ background: r.rang }}
        onClick={(e) => belginiOchir(r, e)}
        title="O'chirish uchun bosing"
      >
        {matn.slice(r.start, r.end)}
      </mark>
    );
    joriy = r.end;
  });
  if (joriy < matn.length) qismlar.push(<span key="oxiri">{matn.slice(joriy)}</span>);

  return (
    <div ref={konteynerRef} className={sinf} style={{ position: "relative" }} onMouseUp={tanlovTugaganda}>
      {qismlar}
      {marker && (
        <div
          className="reading-belgilash-marker"
          style={{ left: marker.x, top: marker.y }}
          onMouseDown={(e) => e.preventDefault()}
        >
          {RANGLAR().map((r) => (
            <button
              key={r.kalit}
              type="button"
              className="reading-rang-tugma"
              style={{ background: r.rang }}
              title={r.kalit}
              onClick={() => rangniBelgila(r.rang)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Ketma-ket, bir xil variantlar ro'yxatiga ega fill_blanks savollarni bitta
// "so'z banki" guruhiga birlashtiradi (oqim matn + umumiy variantlar banki
// sifatida render qilinadi). Qolganlari — oddiy blok (radio/matn).
function bloklarGaAjrat(savollar, boshIdx) {
  const bloklar = [];
  let i = 0;
  while (i < savollar.length) {
    const s = savollar[i];

    // "Choose TWO letters, A-E" (2026-07-27) — kitobda bu BITTA savol,
    // talaba A-E dan ikkitasini tanlaydi. Javoblar kaliti esa ikkita
    // alohida band beradi, shuning uchun bazada ikkita bir xil savol
    // bo'lib turadi. Ketma-ket kelgan, matni va variantlari bir xil
    // multiple_choice savollarni bitta ko'p-javobli blokka birlashtiramiz
    // (backendda `kop_javobli_guruhlar` bilan bir xil qoida).
    if (s.tur === "multiple_choice" && s.variantlar && s.variantlar.length > 0) {
      let j = i + 1;
      while (
        j < savollar.length &&
        savollar[j].tur === "multiple_choice" &&
        (savollar[j].savol || "").trim() === (s.savol || "").trim() &&
        JSON.stringify(savollar[j].variantlar) === JSON.stringify(s.variantlar)
      ) {
        j++;
      }
      if (j - i > 1) {
        bloklar.push({ tur: "kop_javob", savollar: savollar.slice(i, j), boshIdx: boshIdx + i });
        i = j;
        continue;
      }
    }

    // Moslashtirish (matching/matching_headings) — kitobda BARCHA
    // savollar (bayonotlar) ketma-ket ro'yxat qilinib, VARIANTLAR
    // (masalan "List of companies") FAQAT BIR MARTA, pastda alohida
    // qutida ko'rsatiladi. Avval har savol o'z variantlar ro'yxatini
    // TO'LIQ TAKRORLAB chiqarardi (2026-08-01, foydalanuvchi original
    // kitob skrinshoti bilan ko'rsatdi — bir xil emas edi). Endi
    // "so'z banki" bilan bir xil UX: variantlar pastda chip sifatida,
    // bosib tanlab, savolga bosib joylashtiriladi.
    if (
      (s.tur === "matching" || s.tur === "matching_headings") &&
      s.variantlar && s.variantlar.length > 1
    ) {
      let j = i + 1;
      while (
        j < savollar.length &&
        (savollar[j].tur === "matching" || savollar[j].tur === "matching_headings") &&
        JSON.stringify(savollar[j].variantlar) === JSON.stringify(s.variantlar)
      ) {
        j++;
      }
      if (j - i > 1) {
        bloklar.push({ tur: "moslashtirish", savollar: savollar.slice(i, j), boshIdx: boshIdx + i });
        i = j;
        continue;
      }
    }

    if (s.tur === "fill_blanks" && s.variantlar && s.variantlar.length > 0) {
      const guruh = [s];
      let j = i + 1;
      while (
        j < savollar.length &&
        savollar[j].tur === "fill_blanks" &&
        savollar[j].variantlar &&
        JSON.stringify(savollar[j].variantlar) === JSON.stringify(s.variantlar)
      ) {
        guruh.push(savollar[j]);
        j++;
      }
      if (guruh.length > 1) {
        bloklar.push({ tur: "bank", savollar: guruh, boshIdx: boshIdx + i });
        i = j;
        continue;
      }
    }
    bloklar.push({ tur: "oddiy", savol: s, idx: boshIdx + i });
    i++;
  }
  return bloklar;
}

const HARFLAR = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

// "matn {{5}} davomi" ko'rinishidagi matnni bo'laklarga ajratadi — {{n}}
// o'rniga kichik input (n — testdagi UMUMIY savol raqami, 1-based; javoblar
// massividagi indeks n-1), \n bo'lsa qatorga o'tadi. Table/Flow-chart
// Completion (2026-07-24) uchun.
/** Savolga javob berilganmi — ko'p-katakchali savolda javob RO'YXAT
 * bo'ladi, va faqat bo'sh satrlardan iborat ro'yxat "javob berilgan"
 * deb hisoblanmasligi kerak (2026-08-15). */
function javobBormi(qiymat) {
  if (Array.isArray(qiymat)) return qiymat.some((x) => String(x || "").trim());
  return !!qiymat;
}

function matnniBoslarGaAjrat(matn, javoblar, javobniQoy, natija) {
  if (!matn) return null;
  const qismlar = matn.split(/(\{\{\d+\}\}|\n)/g);

  // 2026-08-15 BUG TUZATILDI: bitta savol raqami matnda BIR NECHTA marta
  // uchrasa (masalan "pictures of both {{33}} and {{33}}" — asl IELTS
  // kalitida "IN EITHER ORDER; BOTH REQUIRED FOR ONE MARK"), avval
  // ikkala katakcha ham AYNAN BIR XIL indeksga yozardi — ya'ni birinchisiga
  // yozilgan matn ikkinchisida ham paydo bo'lardi (ko'zgu effekti).
  // Endi har uchrash o'z o'rniga (`sub`) ega bo'ladi va javob ro'yxat
  // sifatida saqlanadi. Bitta marta uchraydigan (odatiy) savollar
  // avvalgidek satr bilan ishlaydi — eski testlar buzilmaydi.
  const uchrashSoni = {};
  qismlar.forEach((b) => {
    const m = b.match(/^\{\{(\d+)\}\}$/);
    if (m) {
      const n = parseInt(m[1], 10) - 1;
      uchrashSoni[n] = (uchrashSoni[n] || 0) + 1;
    }
  });

  const korilgan = {};
  return qismlar.map((b, i) => {
    if (b === "\n") return <br key={i} />;
    const mos = b.match(/^\{\{(\d+)\}\}$/);
    if (!mos) return <span key={i}>{b}</span>;
    const idx = parseInt(mos[1], 10) - 1;
    const kopKatakcha = (uchrashSoni[idx] || 0) > 1;
    korilgan[idx] = (korilgan[idx] ?? -1) + 1;
    const sub = korilgan[idx];

    const saqlangan = javoblar[idx];
    const qiymat = kopKatakcha
      ? Array.isArray(saqlangan)
        ? saqlangan[sub] || ""
        : sub === 0
          ? saqlangan || ""
          : ""
      : saqlangan || "";

    const holat = natija ? (natija.natijalar[idx] ? "togri" : "notogri") : "";
    return (
      <span key={i} className="imtihon-inline-juft">
        {/* Ko'p katakchali savolda raqam FAQAT birinchisida — asl
            kitobdagidek ("33 ..... and .....", ikkinchi chiziqda raqam yo'q). */}
        {(!kopKatakcha || sub === 0) && (
          <span className="imtihon-inline-raqam">{idx + 1}</span>
        )}
        <input
          {...IMLO_OFF}
          className={`imtihon-inline-input ${holat}`}
          disabled={!!natija}
          value={qiymat}
          onChange={(e) => javobniQoy(idx, e.target.value, kopKatakcha ? sub : undefined)}
        />
      </span>
    );
  });
}

function MaxsusFormatGuruhKorsatma({ guruhBoshi, guruhKorsatma }) {
  if (!guruhBoshi && !guruhKorsatma) return null;
  return (
    <>
      {guruhBoshi && <div className="imtihon-guruh-sarlavha">{guruhBoshi}</div>}
      {guruhKorsatma && <div className="imtihon-guruh-korsatma">{guruhKorsatma}</div>}
    </>
  );
}

function MaxsusFormatBloki({ format, guruhBoshi, guruhKorsatma, javoblar, javobniQoy, natija }) {
  if (format.tur === "jadval") {
    return (
      <div className="imtihon-jadval-wrap">
        <MaxsusFormatGuruhKorsatma guruhBoshi={guruhBoshi} guruhKorsatma={guruhKorsatma} />
        {format.sarlavha && <div className="imtihon-jadval-sarlavha">{format.sarlavha}</div>}
        <table className="imtihon-jadval">
          {format.ustunlar && (
            <thead>
              <tr>
                {format.ustunlar.map((u, i) => (
                  <th key={i}>{u}</th>
                ))}
              </tr>
            </thead>
          )}
          <tbody>
            {format.qatorlar.map((qator, ri) => (
              <tr key={ri}>
                {qator.map((katak, ci) => (
                  <td key={ci}>{matnniBoslarGaAjrat(katak, javoblar, javobniQoy, natija)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (format.tur === "oqim") {
    return (
      <div className="imtihon-oqim-wrap">
        <MaxsusFormatGuruhKorsatma guruhBoshi={guruhBoshi} guruhKorsatma={guruhKorsatma} />
        {format.sarlavha && <div className="imtihon-jadval-sarlavha">{format.sarlavha}</div>}
        {format.qadamlar.map((qadam, i) => (
          <div key={i}>
            <div className="imtihon-oqim-qadam">
              {matnniBoslarGaAjrat(qadam, javoblar, javobniQoy, natija)}
            </div>
            {i < format.qadamlar.length - 1 && <div className="imtihon-oqim-strelka">↓</div>}
          </div>
        ))}
      </div>
    );
  }

  if (format.tur === "matn") {
    return (
      <div className="imtihon-maxsus-matn-wrap">
        <MaxsusFormatGuruhKorsatma guruhBoshi={guruhBoshi} guruhKorsatma={guruhKorsatma} />
        {format.sarlavha && <div className="imtihon-jadval-sarlavha">{format.sarlavha}</div>}
        <div className="imtihon-maxsus-matn">
          {matnniBoslarGaAjrat(format.matn, javoblar, javobniQoy, natija)}
        </div>
      </div>
    );
  }

  // 2026-08-08, foydalanuvchi talabi: admin qo'shadigan SOF MATNLI quti
  // (qo'shimcha ko'rsatma, misol, kitobdagi alohida ramka). "matn"
  // turidan farqi — ichida javob maydoni YO'Q, shuning uchun matn
  // {{n}} bo'yicha ajratilmaydi va qatorlar aynan saqlanadi.
  if (format.tur === "izoh") {
    return (
      <div className="imtihon-maxsus-matn-wrap">
        {format.sarlavha && <div className="imtihon-jadval-sarlavha">{format.sarlavha}</div>}
        <div className="imtihon-maxsus-matn" style={{ whiteSpace: "pre-wrap" }}>
          {format.matn}
        </div>
      </div>
    );
  }

  return null;
}

// Matndan {{n}} orqali ishlatilgan barcha savol indekslarini (0-based)
// to'plamiga chiqarib beradi — bular oddiy ro'yxatda takror ko'rsatilmasligi
// uchun.
/** `maxsus_format` TARIXAN bitta obyekt edi (bir qismda bitta jadval/
 * oqim/matn). 2026-08-08 dan boshlab RO'YXAT ham bo'lishi mumkin —
 * admin qism ichiga bir nechta qo'shimcha quti qo'ya oladi.
 *
 * Eski (bitta obyektli) kontent O'ZGARISHSIZ ishlashi uchun hamma joyda
 * shu funksiya orqali normallashtiriladi. */
function maxsusBloklarniOl(format) {
  if (!format) return [];
  return Array.isArray(format) ? format.filter(Boolean) : [format];
}

/** Bitta blokdagi {{n}} savol indekslari (0-based). */
function blokIdxlari(format) {
  const idxlar = new Set();
  const matnlar =
    format.tur === "jadval"
      ? (format.qatorlar || []).flat()
      : format.tur === "oqim"
        ? format.qadamlar || []
        : [format.matn || ""];
  matnlar.forEach((m) => {
    for (const mos of String(m).matchAll(/\{\{(\d+)\}\}/g)) {
      idxlar.add(parseInt(mos[1], 10) - 1);
    }
  });
  return idxlar;
}

function maxsusFormatIdxlari(format) {
  const idxlar = new Set();
  for (const blok of maxsusBloklarniOl(format)) {
    for (const i of blokIdxlari(blok)) idxlar.add(i);
  }
  return idxlar;
}

/** Blok savollar orasida QAYSI o'rinda chiqishi (kichik = tepada).
 *
 * Javob yoziladigan bloklar (jadval/oqim/matn) — ichidagi ENG KICHIK
 * savol raqami bo'yicha, ya'ni eski xatti-harakat saqlanadi.
 * Sof matnli "izoh" qutisida savol yo'q — uning o'rni admin sudrab
 * qo'ygan `joy` qiymati bilan beriladi (butun son emas, kasr ham
 * bo'lishi mumkin: 13.5 = 13- va 14-savol orasida). */
function blokJoyi(format, boshIdx) {
  const idxlar = blokIdxlari(format);
  if (idxlar.size > 0) return Math.min(...idxlar);
  const joy = Number(format.joy);
  return Number.isFinite(joy) ? joy : boshIdx - 0.5; // standart — qism boshida
}

function SozBankiBloki({ blok, javoblar, javobniQoy, natija, t }) {
  const [tanlangan, setTanlangan] = useState(null);

  function bloshgaQoy(idx, qiymat) {
    javobniQoy(idx, qiymat);
    setTanlangan(null);
  }

  return (
    <div className="savol-blok">
      {blok.savollar[0].guruh_boshi && (
        <div className="imtihon-guruh-sarlavha">{blok.savollar[0].guruh_boshi}</div>
      )}
      {blok.savollar[0].guruh_korsatma && (
        <div className="imtihon-guruh-korsatma">{blok.savollar[0].guruh_korsatma}</div>
      )}
      <div className="imtihon-oqim-matn">
        {blok.savollar.map((s, k) => {
          const i = blok.boshIdx + k;
          const holat = natija ? (natija.natijalar[i] ? "togri" : "notogri") : javoblar[i] ? "toldirilgan" : "";
          return (
            <span key={i}>
              {s.savol}{" "}
              <span
                id={`imtihon-savol-${i}`}
                className={`imtihon-bosh-joy ${holat}`}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (natija) return;
                  bloshgaQoy(i, e.dataTransfer.getData("text/plain"));
                }}
                onClick={() => {
                  if (natija) return;
                  if (tanlangan) bloshgaQoy(i, tanlangan);
                }}
              >
                {i + 1}. {javoblar[i] || t("javob_yozing")}
                {natija && <span className={`natija-belgi ${holat}`}>{natija.natijalar[i] ? "✓" : "✗"}</span>}
              </span>{" "}
            </span>
          );
        })}
      </div>
      <div className="imtihon-bank">
        {blok.savollar[0].variantlar.map((v, vi) => (
          <div
            key={v}
            className={`imtihon-bank-chip ${tanlangan === v ? "tanlangan" : ""}`}
            draggable={!natija}
            onDragStart={(e) => e.dataTransfer.setData("text/plain", v)}
            onClick={() => !natija && setTanlangan((prev) => (prev === v ? null : v))}
          >
            {HARFLAR[vi]}. {v}
          </div>
        ))}
      </div>
    </div>
  );
}

/** Moslashtirish (matching/matching_headings) guruhi — asl kitobdagidek:
 * bayonotlar RO'YXAT qilib chiqadi, variantlar (masalan "List of
 * companies") FAQAT BIR MARTA, pastda umumiy qutida.
 *
 * Javob YOZILADI, sudrab tashlanmaydi (2026-08-01, foydalanuvchi qarori):
 * asl kitobda talaba har doim HARF yozadi ("Write the correct letter, A-F,
 * in boxes 18-20"), pastdagi quti esa faqat MA'LUMOTNOMA — qaysi harf
 * kimga/nimaga tegishlini ko'rsatadi. Shu sababli javob katakchasi oddiy
 * input, quti esa bosilmaydigan ro'yxat. Ro'yxatsiz turlarda (masalan
 * "Which paragraph contains...") variantlar umuman bo'sh keladi va bu
 * savollar bu blokka tushmaydi — oddiy savol sifatida chiqadi. */
function MoslashtirishBloki({ blok, javoblar, javobniQoy, natija, t }) {
  // ESKI TESTLAR uchun (2026-08-01): avvalgi promt ro'yxatsiz turlarda ham
  // variantlarga harflarning O'ZINI yozdirardi (["A","B","C"...]). Bunday
  // ro'yxat "A → A, B → B" bo'lib chiqadi va hech qanday ma'lumot bermaydi.
  // Yangi yuklashlarda variantlar bo'sh keladi, lekin bazadagi eski testlar
  // qayta yuklanmaydi — shuning uchun bu yerda ham tekshiramiz.
  const variantlar = blok.savollar[0].variantlar || [];
  const foydaliRoyxat = variantlar.some((v, i) => String(v).trim() !== HARFLAR[i]);
  // 2026-09-03, foydalanuvchi shikoyati: harflardan iborat ro'yxat (masalan
  // "Match each name with one drawing ... letters A-H") butunlay YASHIRILAR
  // edi — talaba javob katakchasidan boshqa hech narsa ko'rmasdi, qaysi
  // harflar ruxsat etilganini ham bilmasdi. Endi bunday holatda harflar
  // bosiladigan qator sifatida chiqadi: talaba katakchani tanlab (yoki
  // shunchaki harfni bosib) javobni qo'yadi.
  const [faolIdx, setFaolIdx] = useState(null);

  function harfniQoy(harf) {
    if (natija) return;
    const idxlar = blok.savollar.map((_, k) => blok.boshIdx + k);
    const nishon =
      faolIdx != null && idxlar.includes(faolIdx)
        ? faolIdx
        : idxlar.find((i) => !javoblar[i]) ?? idxlar[0];
    javobniQoy(nishon, harf);
    setFaolIdx(nishon);
  }

  return (
    <div className="savol-blok">
      {blok.savollar[0].guruh_boshi && (
        <div className="imtihon-guruh-sarlavha">{blok.savollar[0].guruh_boshi}</div>
      )}
      {blok.savollar[0].guruh_korsatma && (
        <div className="imtihon-guruh-korsatma">{blok.savollar[0].guruh_korsatma}</div>
      )}
      <div className="imtihon-moslashtirish-royxat">
        {blok.savollar.map((s, k) => {
          const i = blok.boshIdx + k;
          const holat = natija ? (natija.natijalar[i] ? "togri" : "notogri") : javoblar[i] ? "toldirilgan" : "";
          return (
            <div key={i} className="imtihon-moslashtirish-qator">
              <span className="imtihon-moslashtirish-matn">
                {i + 1}. {s.savol}
              </span>
              <span className="imtihon-moslashtirish-javob">
                <input
                  {...IMLO_OFF}
                  id={`imtihon-savol-${i}`}
                  type="text"
                  className={`imtihon-bosh-joy ${holat} ${!foydaliRoyxat && faolIdx === i ? "faol" : ""}`}
                  placeholder={t("javob_yozing")}
                  disabled={!!natija}
                  value={javoblar[i] || ""}
                  onFocus={() => setFaolIdx(i)}
                  onChange={(e) => javobniQoy(i, e.target.value)}
                />
                {natija && <span className={`natija-belgi ${holat}`}>{natija.natijalar[i] ? "✓" : "✗"}</span>}
              </span>
            </div>
          );
        })}
      </div>
      {foydaliRoyxat ? (
        <div className="imtihon-moslashtirish-variantlar">
          {variantlar.map((v, vi) => (
            <div key={v} className="imtihon-moslashtirish-variant">
              <span className="imtihon-moslashtirish-variant-harf">{HARFLAR[vi]}</span>
              <span className="imtihon-moslashtirish-variant-matn">{v}</span>
            </div>
          ))}
        </div>
      ) : (
        variantlar.length > 0 && (
          <div className="imtihon-harf-tanlov">
            {variantlar.map((v) => (
              <button
                key={v}
                type="button"
                className={`imtihon-harf-chip ${javoblar[faolIdx] === v ? "tanlangan" : ""}`}
                disabled={!!natija}
                onClick={() => harfniQoy(v)}
              >
                {v}
              </button>
            ))}
          </div>
        )
      )}
    </div>
  );
}

// Rasm ustiga to'g'ridan-to'g'ri joylashtiriladigan savollar (Map/Diagram
// Labelling, jadval ichidagi bo'sh joy va h.k.) — savolda "pozitsiya":
// {"x": 0-100, "y": 0-100} (rasm eni/bo'yiga nisbatan foiz) bo'lsa, o'ng
// paneldagi umumiy ro'yxatda emas, aynan shu nuqtada kichik input sifatida
// ko'rsatiladi (2026-07-24).
function RasmSavollari({ rasmUrl, sarlavha, savollar, boshIdx, javoblar, javobniQoy, natija }) {
  return (
    <div style={{ position: "relative", display: "inline-block", maxWidth: "100%" }}>
      <img src={rasmUrl} alt={sarlavha} style={{ maxWidth: "100%", display: "block" }} />
      {savollar.map((s, k) => {
        if (!s.pozitsiya) return null;
        const i = boshIdx + k;
        const holat = natija ? (natija.natijalar[i] ? "togri" : "notogri") : "";
        return (
          <input
            key={i}
            {...IMLO_OFF}
            className={`imtihon-rasm-input ${holat}`}
            style={{ left: `${s.pozitsiya.x}%`, top: `${s.pozitsiya.y}%` }}
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

/** "Choose TWO letters, A-E" — kitobdagidek BITTA savol, bitta variantlar
 * ro'yxati, checkbox bilan (2026-07-27). Avval bu ikkita alohida savol
 * bo'lib chiqardi: matn ikki marta takrorlanardi va radio tugma bo'lgani
 * uchun talaba bir xil variantni ikki marta belgilashi mumkin edi.
 *
 * Tanlangan variantlar guruhning javob kataklariga (19, 20) tartib bilan
 * yoziladi; qaysi katakka tushishi ahamiyatsiz — backend ularni to'plam
 * sifatida tekshiradi (`kop_javobli_guruhlar`). */
function KopJavobBloki({ blok, javoblar, javobniQoy, natija, t }) {
  const { savollar, boshIdx } = blok;
  const soni = savollar.length;
  const idxlar = savollar.map((_, k) => boshIdx + k);
  const tanlangan = idxlar.map((i) => javoblar[i]).filter(Boolean);
  const raqamlar = idxlar.map((i) => i + 1).join(" & ");

  function almashtir(v) {
    if (natija) return;
    const yangi = tanlangan.includes(v)
      ? tanlangan.filter((x) => x !== v)
      : tanlangan.length >= soni
        ? tanlangan // limitga yetdi — avval bittasini olib tashlash kerak
        : [...tanlangan, v];
    idxlar.forEach((i, k) => javobniQoy(i, yangi[k] || ""));
  }

  return (
    <div className="savol-blok" id={`imtihon-savol-${boshIdx}`}>
      {savollar[0].guruh_boshi && (
        <div className="imtihon-guruh-sarlavha">{savollar[0].guruh_boshi}</div>
      )}
      {savollar[0].guruh_korsatma && (
        <div className="imtihon-guruh-korsatma">{savollar[0].guruh_korsatma}</div>
      )}
      <div className="savol-matni">
        {raqamlar}. {savollar[0].savol}
        {natija && (
          <span className="natija-belgi">
            {idxlar.filter((i) => natija.natijalar[i]).length}/{soni}
          </span>
        )}
      </div>
      <div className="izoh" style={{ marginBottom: 6 }}>
        {t("kop_javob_izoh").replace("{n}", soni)}
      </div>
      {savollar[0].variantlar.map((v, vi) => {
        const belgilangan = tanlangan.includes(v);
        return (
          <label className="variant-qator" key={v}>
            <input
              type="checkbox"
              disabled={!!natija || (!belgilangan && tanlangan.length >= soni)}
              checked={belgilangan}
              onChange={() => almashtir(v)}
            />
            {HARFLAR[vi]}. {v}
          </label>
        );
      })}
    </div>
  );
}

function OddiySavolBloki({ blok, javoblar, javobniQoy, natija, t }) {
  const { savol: s, idx: i } = blok;
  return (
    <div className="savol-blok" id={`imtihon-savol-${i}`}>
      {s.guruh_boshi && <div className="imtihon-guruh-sarlavha">{s.guruh_boshi}</div>}
      {s.guruh_korsatma && <div className="imtihon-guruh-korsatma">{s.guruh_korsatma}</div>}
      <div className="savol-matni">
        {i + 1}. {s.savol}
        {natija && (
          <span className={`natija-belgi ${natija.natijalar[i] ? "togri" : "notogri"}`}>
            {natija.natijalar[i] ? "✓" : "✗"}
          </span>
        )}
      </div>
      {s.variantlar && s.variantlar.length > 0 && s.tur !== "map_labelling" ? (
        s.variantlar.map((v, vi) => (
          <label className="variant-qator" key={v}>
            <input
              type="radio"
              name={`imtihon-savol-${i}`}
              disabled={!!natija}
              checked={javoblar[i] === v}
              onChange={() => javobniQoy(i, v)}
            />
            {HARFLAR[vi]}. {v}
          </label>
        ))
      ) : (
        <input
          {...IMLO_OFF}
          type="text"
          placeholder={t("javob_yozing")}
          disabled={!!natija}
          value={javoblar[i] || ""}
          onChange={(e) => javobniQoy(i, e.target.value)}
        />
      )}
    </div>
  );
}

/** Testlar ro'yxati — papkalar bo'yicha guruhlangan (2026-08-01).
 *
 * 2026-08-12: ichki (2-darajali) papkalar endi o'z OTASI ICHIDA nested
 * ko'rsatiladi (avval har test faqat o'zining bevosita papkasini
 * bilardi — ichki papka otasidan ajralib, boshqa otalarning bolalari
 * bilan bitta tekis ro'yxatda aralashib chiqardi, foydalanuvchi
 * skrinshot bilan ko'rsatdi). Backend endi `papka_ota_id`/
 * `papka_ota_nomi`ni ham qaytaradi (`ImtihonListView`) — shu orqali
 * ikki qavatli daraxt quramiz: OTA (accordion) → ICHKI PAPKA (ichida
 * yana accordion) → testlar. Otaning o'zida BEVOSITA test bo'lsa
 * (ichki papkasiz to'g'ridan-to'g'ri biriktirilgan), ular ham otaning
 * ichida, ichki papkalardan OLDIN ko'rsatiladi. Papkaga umuman
 * solinmagan testlar ro'yxat OXIRIDA, papkasiz holda qoladi. */
export function PapkaliRoyxat({ royxat, ochish, t }) {
  const [ochiq, setOchiq] = useState({});

  const otalar = [];
  const otaMap = new Map();
  const papkasiz = [];
  for (const r of royxat) {
    if (!r.papka) {
      papkasiz.push(r);
      continue;
    }
    const otaId = r.papka_ota_id || r.papka;
    const otaNomi = r.papka_ota_id ? r.papka_ota_nomi : r.papka_nomi;
    let ota = otaMap.get(otaId);
    if (!ota) {
      ota = { id: otaId, nomi: otaNomi || "—", bevosita: [], ichkilar: [], ichkiMap: new Map() };
      otaMap.set(otaId, ota);
      otalar.push(ota);
    }
    if (r.papka_ota_id) {
      let ich = ota.ichkiMap.get(r.papka);
      if (!ich) {
        ich = { id: r.papka, nomi: r.papka_nomi || "—", testlar: [] };
        ota.ichkiMap.set(r.papka, ich);
        ota.ichkilar.push(ich);
      }
      ich.testlar.push(r);
    } else {
      ota.bevosita.push(r);
    }
  }

  return (
    <>
      {otalar.map((ota) => {
        const jami = ota.bevosita.length + ota.ichkilar.reduce((s, i) => s + i.testlar.length, 0);
        return (
          <div key={ota.id} className="imtihon-papka">
            <div
              className="imtihon-papka-sarlavha"
              onClick={() => setOchiq((v) => ({ ...v, [`o${ota.id}`]: !v[`o${ota.id}`] }))}
            >
              <span>{ochiq[`o${ota.id}`] ? "▾" : "▸"} 📁 {ota.nomi}</span>
              <span className="izoh">{jami}</span>
            </div>
            {ochiq[`o${ota.id}`] && (
              <div className="imtihon-papka-ichi">
                {ota.bevosita.map((r) => (
                  <div key={r.id} className="mashq-royxat-el" onClick={() => ochish(r.id)}>
                    <span>{r.name}</span>
                  </div>
                ))}
                {ota.ichkilar.map((ich) => (
                  <div key={ich.id} className="imtihon-papka" style={{ marginLeft: 20 }}>
                    <div
                      className="imtihon-papka-sarlavha"
                      onClick={() => setOchiq((v) => ({ ...v, [`i${ich.id}`]: !v[`i${ich.id}`] }))}
                    >
                      <span>{ochiq[`i${ich.id}`] ? "▾" : "▸"} 📂 {ich.nomi}</span>
                      <span className="izoh">{ich.testlar.length}</span>
                    </div>
                    {ochiq[`i${ich.id}`] && (
                      <div className="imtihon-papka-ichi">
                        {ich.testlar.map((r) => (
                          <div key={r.id} className="mashq-royxat-el" onClick={() => ochish(r.id)}>
                            <span>{r.name}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
      {papkasiz.map((r) => (
        <div key={r.id} className="mashq-royxat-el" onClick={() => ochish(r.id)}>
          <span>{r.name}</span>
        </div>
      ))}
    </>
  );
}

// F5'da (yoki internet uzilib qayta ulanganda) test holati yo'qolmasligi
// uchun — javoblar va taymerning ABSOLYUT tugash vaqti shu kalit bilan
// sessionStorage'ga yoziladi (2026-08-15, F5'DA TEST HOLATI YO'QOLISHI
// ishi). `mockYechimId` ham kalitga kirdi — bir xil test Mock ichida VA
// alohida mashq sifatida turlicha sessiyada yechilishi mumkin, ular bir-
// biriga aralashmasligi kerak.
export function holatKaliti(bolim, testId, mockYechimId) {
  return `imtihon_holat_v1_${bolim}_${testId}_${mockYechimId || "yakka"}`;
}

/** Cambridge-uslubidagi to'liq IELTS testi — ro'yxat, split-screen yechish
 * rejimi (chapda matn/audio, o'ngda savollar), pastki Part-navigatsiya. */
export default function ImtihonOtish({ bolim, manba = "admin", testId, mockYechimId, onYakunlandi, ochirilganId }) {
  const { t } = useI18n();
  const [royxat, setRoyxat] = useState([]);
  const [test, setTest] = useState(null);
  const [audioUrllar, setAudioUrllar] = useState({});
  const [rasmUrllar, setRasmUrllar] = useState({});
  const [javoblar, setJavoblar] = useState({});
  const [natija, setNatija] = useState(null);
  const [xato, setXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [tayyorlanmoqda, setTayyorlanmoqda] = useState(false);
  // Test yechilayotganda bazadan yo'qolgan bo'lsa (o'chirilgan/qayta
  // yuklangan) — "Ro'yxatga qaytish" tugmasi ko'rsatiladi.
  const [testYoq, setTestYoq] = useState(false);
  const [fokus, setFokus] = useState(false);
  const [masshtab, setMasshtab] = useState(100);
  const [soniya, setSoniya] = useState(0);
  const [teskariMi, setTeskariMi] = useState(false);
  const [faolQism, setFaolQism] = useState(0);
  const [chapKenglik, setChapKenglik] = useState(45);
  // Vaqt tugab, avtomatik yuborilgach (Mock ichida) bloklovchi "Keyingisi"
  // oynasini ko'rsatish uchun — qo'lda yakunlashda bu oyna CHIQMAYDI.
  const [vaqtSababliYakun, setVaqtSababliYakun] = useState(false);
  const taymerRef = useRef(null);
  const splitRef = useRef(null);
  const sudralmoqda = useRef(false);
  const boshlanishVaqtiRef = useRef(null);
  const avtoYuborildiRef = useRef(false);
  const keyingigaOtildiRef = useRef(false);

  useEffect(() => {
    setTest(null);
    setNatija(null);
    if (testId) {
      ochish(testId);
      return;
    }
    api(`/api/imtihon/testlar/?bolim=${bolim}&manba=${manba}`).then(setRoyxat).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bolim, testId, manba]);

  // 2026-07-31: admin paneli (shu sahifaning TEPASIDA) testni o'chirsa,
  // pastda o'sha test ochiq qolib ketardi — "Testni yakunlash" bosilganda
  // esa backend 404 berardi ("No ImtihonTest matches the given query").
  // Endi ochiq test o'chirilgan bo'lsa oyna darhol yopiladi.
  useEffect(() => {
    if (ochirilganId != null && test && test.id === ochirilganId) {
      setTest(null);
      setNatija(null);
      api(`/api/imtihon/testlar/?bolim=${bolim}&manba=${manba}`).then(setRoyxat).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ochirilganId]);

  useEffect(() => {
    if (!test || natija) {
      clearInterval(taymerRef.current);
      return;
    }
    taymerRef.current = setInterval(() => setSoniya((s) => s + 1), 1000);
    return () => clearInterval(taymerRef.current);
  }, [test, natija]);

  useEffect(() => {
    function chiqishdanOldin(e) {
      if (!test || natija) return;
      e.preventDefault();
      e.returnValue = "";
    }
    window.addEventListener("beforeunload", chiqishdanOldin);
    return () => window.removeEventListener("beforeunload", chiqishdanOldin);
  }, [test, natija]);

  // 2026-07-30 talabi: test yechilayotganda saytning boshqa bo'limiga
  // o'tish mumkin bo'lmasin. `onYakunlandi` berilgan bo'lsa — bu komponent
  // Mock imtihon ichida (`ImtihonMock.jsx` butun sessiya davomida holatni
  // O'ZI boshqaradi, bo'lim almashganda qisqa "faolsiz" lahza bo'lmasin
  // uchun), aks holda mustaqil test sifatida shu yerda boshqaradi.
  const { setTestFaol } = useTestRejimi();
  useEffect(() => {
    if (onYakunlandi) return undefined;
    setTestFaol(!!test && !natija);
    return () => setTestFaol(false);
  }, [test, natija, onYakunlandi, setTestFaol]);

  useEffect(() => {
    function ustidaHarakat(e) {
      if (!sudralmoqda.current || !splitRef.current) return;
      const { left, width } = splitRef.current.getBoundingClientRect();
      const foiz = ((e.clientX - left) / width) * 100;
      setChapKenglik(Math.min(75, Math.max(20, foiz)));
    }
    function qoyib_yubordi() {
      sudralmoqda.current = false;
    }
    window.addEventListener("mousemove", ustidaHarakat);
    window.addEventListener("mouseup", qoyib_yubordi);
    return () => {
      window.removeEventListener("mousemove", ustidaHarakat);
      window.removeEventListener("mouseup", qoyib_yubordi);
    };
  }, []);

  async function ochish(id) {
    setXato("");
    setTestYoq(false);
    setNatija(null);
    setJavoblar({});
    setSoniya(0);
    setTeskariMi(false);
    setFokus(false);
    setMasshtab(100);
    setFaolQism(0);
    setTayyorlanmoqda(true);
    setVaqtSababliYakun(false);
    avtoYuborildiRef.current = false;
    keyingigaOtildiRef.current = false;
    try {
      const t2 = await api(`/api/imtihon/testlar/${id}/`);
      const urllar = {};
      const rasmlar = {};
      // F5'da (yoki internet uzilib qayta ulanganda) holatni tiklash —
      // sessionStorage'da shu test/mock uchun saqlangan javoblar+boshlanish
      // vaqti bo'lsa, o'shandan davom etamiz (2026-08-15).
      const kalit = holatKaliti(bolim, id, mockYechimId);
      let tiklanganJavoblar = {};
      let boshlanishVaqti = Date.now();
      try {
        const saqlangan = JSON.parse(sessionStorage.getItem(kalit) || "null");
        if (saqlangan && saqlangan.testId === id && Number.isFinite(saqlangan.boshlanishVaqti)) {
          tiklanganJavoblar = saqlangan.javoblar || {};
          boshlanishVaqti = saqlangan.boshlanishVaqti;
        }
      } catch {
        // sessionStorage buzilgan bo'lsa — jim o'tkazib yuboramiz, boshidan boshlanadi.
      }
      boshlanishVaqtiRef.current = boshlanishVaqti;
      setJavoblar(tiklanganJavoblar);
      setSoniya(Math.max(0, Math.floor((Date.now() - boshlanishVaqti) / 1000)));
      try {
        sessionStorage.setItem(
          kalit,
          JSON.stringify({ testId: id, boshlanishVaqti, javoblar: tiklanganJavoblar })
        );
      } catch {
        // to'lgan bo'lsa — kritik emas, faqat F5'da tiklash ishlamaydi.
      }
      // Barcha qismlarning audio/rasmini PARALLEL (Promise.all) yuklab
      // olamiz, test oynasi FAQAT hammasi tayyor bo'lgandan keyin ochiladi
      // — shunda talaba "Audio yuklanmoqda..." holatini ko'rmaydi, buning
      // o'rniga bitta umumiy "tayyorlanmoqda" ko'rsatkichi chiqadi.
      await Promise.all(
        t2.qismlar.map(async (qism) => {
          await Promise.all([
            qism.audio_url
              ? apiBlobUrl(qism.audio_url)
                  .then((u) => { urllar[qism.id] = u; })
                  .catch(() => {})
              : Promise.resolve(),
            qism.rasm_url
              ? apiBlobUrl(qism.rasm_url)
                  .then((u) => { rasmlar[qism.id] = u; })
                  .catch(() => {})
              : Promise.resolve(),
          ]);
        })
      );
      setAudioUrllar(urllar);
      setRasmUrllar(rasmlar);
      setTest(t2);
    } catch (e) {
      // Avval catch YO'Q edi — ro'yxatdagi test oradan o'chirilgan bo'lsa
      // (masalan tepadagi admin panelidan), sahifa jim qotib qolardi.
      setXato(e.data?.detail || t("xato_yuz_berdi"));
      api(`/api/imtihon/testlar/?bolim=${bolim}&manba=${manba}`).then(setRoyxat).catch(() => {});
    } finally {
      setTayyorlanmoqda(false);
    }
  }

  /** `sub` berilsa — BITTA savolning bir NECHTA katakchasidan biri
   * (2026-08-15, masalan Reading "...both 33 ..... and ..... " —
   * asl kalitda "IN EITHER ORDER; BOTH REQUIRED FOR ONE MARK").
   * Bunday savolda javob RO'YXAT bo'lib saqlanadi va shu holida
   * backendga boradi; oddiy savollarda esa avvalgidek satr. */
  function javobniQoy(i, qiymat, sub) {
    setJavoblar((prev) => {
      if (sub === undefined) return { ...prev, [i]: qiymat };
      const eski = Array.isArray(prev[i]) ? [...prev[i]] : prev[i] ? [prev[i]] : [];
      while (eski.length <= sub) eski.push("");
      eski[sub] = qiymat;
      return { ...prev, [i]: eski };
    });
  }

  // Har javob o'zgarganda sessionStorage'dagi holatni yangilaymiz (F5'da
  // tiklash uchun). Taymer ABSOLYUT boshlanish vaqti (boshlanishVaqtiRef)
  // o'zgarmaydi — shuning uchun bu yerda qayta yozilmaydi, faqat javoblar.
  useEffect(() => {
    if (!test || natija || boshlanishVaqtiRef.current == null) return;
    const kalit = holatKaliti(bolim, test.id, mockYechimId);
    try {
      sessionStorage.setItem(
        kalit,
        JSON.stringify({ testId: test.id, boshlanishVaqti: boshlanishVaqtiRef.current, javoblar })
      );
    } catch {
      // to'lgan bo'lsa — kritik emas.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [javoblar, test, natija]);

  function saqlanganHolatniTozala() {
    if (!test) return;
    try {
      sessionStorage.removeItem(holatKaliti(bolim, test.id, mockYechimId));
    } catch {
      // kritik emas.
    }
  }

  async function yuborish() {
    setYuklanmoqda(true);
    setXato("");
    try {
      const barchaSavollar = test.qismlar.flatMap((q) => q.savollar);
      const tartib = barchaSavollar.map((_, i) => javoblar[i] || "");
      const res = await api(`/api/imtihon/testlar/${test.id}/yechish/`, {
        method: "POST",
        body: { javoblar: tartib, mock_yechim_id: mockYechimId },
      });
      setNatija(res);
      // Test muvaffaqiyatli yakunlangach — saqlangan holat endi kerak emas,
      // eski qoldiq keyingi safar chalkashtirmasin (2026-08-15).
      saqlanganHolatniTozala();
    } catch (e) {
      // 2026-07-31: test yechilayotganda o'chirilgan/qayta yuklangan bo'lsa
      // (admin paneli shu sahifaning tepasida) — xom 404 o'rniga tushunarli
      // xabar va ro'yxatga qaytish yo'li.
      if (e.data?.kod === "test_topilmadi") setTestYoq(true);
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  // Vaqt tugaganda (real IELTS shartlariga mos) majburiy yakunlash
  // (2026-08-15, VAQT TUGAGANDA MAJBURIY YAKUNLASH ishi). Standalone
  // mashqda — avtomatik yuboriladi, natija kelgach barcha input'lar
  // `disabled={!!natija}` orqali allaqachon bloklanadi. Mock ichida
  // (`onYakunlandi` mavjud) — avtomatik yuborilgach, alohida
  // "Keyingisi" (30s) oynasi ko'rsatiladi (pastda, `vaqtSababliYakun`).
  const qolganVaqt = test ? standartVaqt(bolim) - soniya : null;
  const vaqtTugadi = !!test && !natija && qolganVaqt <= 0;
  useEffect(() => {
    if (vaqtTugadi && !avtoYuborildiRef.current && !yuklanmoqda) {
      avtoYuborildiRef.current = true;
      setVaqtSababliYakun(true);
      yuborish();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vaqtTugadi, yuklanmoqda]);

  function royxatgaQayt() {
    setTestYoq(false);
    setXato("");
    setTest(null);
    api(`/api/imtihon/testlar/?bolim=${bolim}&manba=${manba}`).then(setRoyxat).catch(() => {});
  }

  function ortgaQaytish() {
    if (!natija && !window.confirm(t("imtihon_ortga_tasdiq"))) return;
    // Foydalanuvchi ATAYLAB ortga qaytdi — "javoblar saqlanmaydi" degan
    // tasdiqqa mos, saqlangan F5-holati ham tozalanadi (2026-08-15).
    saqlanganHolatniTozala();
    setTest(null);
  }

  function yuborishBosildi() {
    if (!window.confirm(t("imtihon_yakunlash_tasdiq"))) return;
    yuborish();
  }

  function savolgaOt(qismIndex, i) {
    setFaolQism(qismIndex);
    setTimeout(() => {
      document.getElementById(`imtihon-savol-${i}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 50);
  }

  if (!test) {
    return (
      <div className="karta">
        {tayyorlanmoqda ? (
          <div className="yuklanmoqda">{t("imtihon_tayyorlanmoqda")}</div>
        ) : (
          <>
            {royxat.length === 0 && <span className="izoh">{t("imtihon_royxati_boshi")}</span>}
            <PapkaliRoyxat royxat={royxat} ochish={ochish} t={t} />
          </>
        )}
      </div>
    );
  }

  // Har qism uchun boshlang'ich global raqam + savollar soni.
  let hisoblagich = 0;
  const qismMalumot = test.qismlar.map((qism) => {
    const boshIdx = hisoblagich;
    hisoblagich += qism.savollar.length;
    return { qism, boshIdx, soni: qism.savollar.length };
  });
  const jamiSavollar = hisoblagich;
  const faol = qismMalumot[faolQism];

  // Vaqt tugab, hali natija kelmagan (avtomatik yuborilish jarayonida)
  // oraliqda — barcha input/tugmalar vizual ham, funksional ham
  // bloklansin (pointer-events: none) va qisqa xabar chiqsin.
  const bloklanganOraliqda = vaqtTugadi && !natija;

  const mazmun = (
    <div
      style={{ zoom: `${masshtab}%` }}
      className={bloklanganOraliqda ? "imtihon-vaqt-tugadi-overlay" : ""}
    >
      {bloklanganOraliqda && (
        <div className="izoh" style={{ marginBottom: 8, fontWeight: 700 }}>
          ⏱ {t("vaqt_tugadi_yuborilmoqda")}
        </div>
      )}
      <div className="imtihon-asboblar">
        <button className="tugma ikkinchi" onClick={ortgaQaytish}>
          {t("ortga")}
        </button>
        <span
          className="imtihon-taymer"
          title={t("imtihon_taymer_almashtir")}
          onClick={() => setTeskariMi((v) => !v)}
        >
          ⏱ {vaqtFormat(teskariMi ? Math.max(0, standartVaqt(bolim) - soniya) : soniya)}
        </span>
        <button className="tugma ikkinchi" onClick={() => setFokus((v) => !v)}>
          {fokus ? t("fokusdan_chiqish") : t("fokus_rejimi")}
        </button>
        <span style={{ fontWeight: 700, fontSize: 15 }}>{test.name}</span>
        <div className="imtihon-zoom">
          <button onClick={() => setMasshtab((m) => Math.max(80, m - 10))}>-</button>
          <span className="izoh">{masshtab}%</span>
          <button onClick={() => setMasshtab((m) => Math.min(140, m + 10))}>+</button>
        </div>
      </div>

      {(() => {
        // "pozitsiya" faqat shu qismga rasm biriktirilgan bo'lsagina
        // ma'noga ega — rasm bo'lmasa (masalan JSON'ni AI rasmni ko'rmasdan
        // yozib, "pozitsiya"ni xato qo'shib qo'ysa) savol ro'yxatdan yashirin
        // qolib, hech qayerda ko'rinmay qolmasligi uchun bu holatda pozitsiya
        // e'tiborga olinmaydi (oddiy ro'yxatda ko'rsatiladi).
        const rasmMavjud = !!rasmUrllar[faol.qism.id];
        const pozitsiyaliIdxlar = new Set();
        if (rasmMavjud) {
          faol.qism.savollar.forEach((s, k) => {
            if (s.pozitsiya) pozitsiyaliIdxlar.add(faol.boshIdx + k);
          });
        }
        // Table/Flow-chart Completion (maxsus_format) — shu blokda {{n}}
        // orqali ishlatilgan savollar ham oddiy ro'yxatda takror chiqmasin.
        const maxsusIdxlar = maxsusFormatIdxlari(faol.qism.maxsus_format);
        const yashirilganIdxlar = new Set([...pozitsiyaliIdxlar, ...maxsusIdxlar]);
        const boshqaBloklar = bloklarGaAjrat(faol.qism.savollar, faol.boshIdx)
          .filter((blok) => {
            if (blok.tur === "oddiy") return !yashirilganIdxlar.has(blok.idx);
            // "bank"/"kop_javob" bloki — ichidagi BARCHA savollar
            // maxsus_format/pozitsiya orqali allaqachon ko'rsatilgan bo'lsa,
            // ro'yxatda takror chiqmasin.
            return !blok.savollar.every((_, k) => yashirilganIdxlar.has(blok.boshIdx + k));
          })
          .map((blok, bi) => ({
            kalit: blok.tur === "oddiy" ? blok.idx : blok.boshIdx,
            tugun:
              blok.tur === "kop_javob" ? (
                <KopJavobBloki
                  key={`k${bi}`}
                  blok={blok}
                  javoblar={javoblar}
                  javobniQoy={javobniQoy}
                  natija={natija}
                  t={t}
                />
              ) : blok.tur === "bank" ? (
                <SozBankiBloki
                  key={`b${bi}`}
                  blok={blok}
                  javoblar={javoblar}
                  javobniQoy={javobniQoy}
                  natija={natija}
                  t={t}
                />
              ) : blok.tur === "moslashtirish" ? (
                <MoslashtirishBloki
                  key={`m${bi}`}
                  blok={blok}
                  javoblar={javoblar}
                  javobniQoy={javobniQoy}
                  natija={natija}
                  t={t}
                />
              ) : (
                <OddiySavolBloki
                  key={`o${bi}`}
                  blok={blok}
                  javoblar={javoblar}
                  javobniQoy={javobniQoy}
                  natija={natija}
                  t={t}
                />
              ),
          }));
        // maxsus_format (jadval/oqim/matn) o'z savol raqamiga qarab, boshqa
        // bloklar orasida TO'G'RI o'rinda chiqishi uchun bitta ro'yxatga
        // birlashtirilib, savol raqami bo'yicha saralanadi (2026-07-24) —
        // aks holda masalan 26-30 (jadval) har doim 21-25 (oddiy)dan oldin
        // chiqib qolardi.
        // 2026-08-08: `maxsus_format` endi RO'YXAT ham bo'lishi mumkin —
        // har blok o'z o'rnida chiqadi. Sof matnli "izoh" qutisida savol
        // yo'q, shuning uchun u `maxsusIdxlar` shartiga bog'lanmaydi
        // (avval faqat {{n}} bo'lgan blok ko'rsatilardi).
        maxsusBloklarniOl(faol.qism.maxsus_format).forEach((blok, bi) => {
          const blokIdx = blokIdxlari(blok);
          if (blok.tur !== "izoh" && blokIdx.size === 0) return;
          // 2026-08-05, foydalanuvchi topgan bug: maxsus_format (jadval/
          // oqim/matn to'ldirish) o'z savollarini oddiy ro'yxatdan olib
          // tashlagani uchun, o'sha savollarning "guruh_boshi"/
          // "guruh_korsatma"si (masalan "Complete the summary below...")
          // hech qayerda ko'rsatilmay qolib ketardi — endi shu guruhning
          // BIRINCHI savolidan olinib, MaxsusFormatBloki'ga uzatiladi.
          const birinchiIdx = blokIdx.size ? Math.min(...blokIdx) : null;
          const birinchiSavol =
            birinchiIdx == null ? null : faol.qism.savollar[birinchiIdx - faol.boshIdx];
          boshqaBloklar.push({
            kalit: blokJoyi(blok, faol.boshIdx),
            tugun: (
              <MaxsusFormatBloki
                key={`maxsus${bi}`}
                format={blok}
                guruhBoshi={birinchiSavol?.guruh_boshi}
                guruhKorsatma={birinchiSavol?.guruh_korsatma}
                javoblar={javoblar}
                javobniQoy={javobniQoy}
                natija={natija}
              />
            ),
          });
        });
        const savollarBlok = boshqaBloklar.sort((a, b) => a.kalit - b.kalit).map((x) => x.tugun);

        // Listening: audio doim yuqorida, to'liq kenglikda. Rasm (Map/
        // Diagram Labelling) bo'lsa — pastda split (rasm chap, savollar
        // o'ng), bo'lmasa — bitta to'liq kenglikdagi panel (split yo'q).
        // Barcha savollar rasmga joylashtirilgan bo'lsa (pozitsiya bilan) —
        // o'ng panel bo'sh qolib ketmasin deb, split umuman ko'rsatilmaydi,
        // rasm to'liq kenglikda chiqadi (2026-07-24).
        if (bolim === "listening") {
          const rasmBormi = !!rasmUrllar[faol.qism.id];
          const ongPanelKerak = savollarBlok.length > 0;
          return (
            <>
              <div className="imtihon-qism-sarlavha">{faol.qism.sarlavha}</div>
              {faol.qism.yoriqnoma && <div className="imtihon-yoriqnoma">{faol.qism.yoriqnoma}</div>}
              {audioUrllar[faol.qism.id] ? (
                <audio
                  {...AUDIO_HIMOYA} onPlay={(e) => faqatBittaAudioIjro(e.target)}
                  controls
                  src={audioUrllar[faol.qism.id]}
                  style={{ width: "100%", marginBottom: fokus ? 6 : 14 }}
                />
              ) : (
                <span className="izoh">{t("audio_yuklanmoqda")}</span>
              )}
              {rasmBormi && !ongPanelKerak ? (
                <RasmSavollari
                  rasmUrl={rasmUrllar[faol.qism.id]}
                  sarlavha={faol.qism.sarlavha}
                  savollar={faol.qism.savollar}
                  boshIdx={faol.boshIdx}
                  javoblar={javoblar}
                  javobniQoy={javobniQoy}
                  natija={natija}
                />
              ) : rasmBormi ? (
                <div className="imtihon-split" ref={splitRef}>
                  <div className="imtihon-panel-chap" style={{ flexBasis: `${chapKenglik}%` }}>
                    <RasmSavollari
                      rasmUrl={rasmUrllar[faol.qism.id]}
                      sarlavha={faol.qism.sarlavha}
                      savollar={faol.qism.savollar}
                      boshIdx={faol.boshIdx}
                      javoblar={javoblar}
                      javobniQoy={javobniQoy}
                      natija={natija}
                    />
                  </div>
                  <div
                    className="imtihon-drag-tutqich"
                    onMouseDown={() => {
                      sudralmoqda.current = true;
                    }}
                  >
                    ⋮
                  </div>
                  <div className="imtihon-panel-ong" style={{ flex: 1 }}>
                    {savollarBlok}
                  </div>
                </div>
              ) : (
                <div>{savollarBlok}</div>
              )}
            </>
          );
        }

        // Reading — chapda passage matni, o'ngda savollar. Barcha savollar
        // rasmga joylashtirilgan bo'lsa (pozitsiya bilan) va matn bo'lmasa —
        // o'ng panel bo'sh qolmasin deb split ko'rsatilmaydi (2026-07-24).
        const chapKontent = (
          <>
            <div className="imtihon-qism-sarlavha">{faol.qism.sarlavha}</div>
            {faol.qism.yoriqnoma && <div className="imtihon-yoriqnoma">{faol.qism.yoriqnoma}</div>}
            {faol.qism.matn && (
              <BelgilanadiganMatn key={faol.qism.id} matnId={faol.qism.id} matn={faol.qism.matn} sinf="mashq-passage" />
            )}
            {rasmUrllar[faol.qism.id] && (
              <div style={{ marginTop: 10 }}>
                <RasmSavollari
                  rasmUrl={rasmUrllar[faol.qism.id]}
                  sarlavha={faol.qism.sarlavha}
                  savollar={faol.qism.savollar}
                  boshIdx={faol.boshIdx}
                  javoblar={javoblar}
                  javobniQoy={javobniQoy}
                  natija={natija}
                />
              </div>
            )}
          </>
        );

        if (savollarBlok.length === 0) {
          return <div>{chapKontent}</div>;
        }

        return (
          <div className="imtihon-split" ref={splitRef}>
            <div className="imtihon-panel-chap" style={{ flexBasis: `${chapKenglik}%` }}>
              {chapKontent}
            </div>
            <div
              className="imtihon-drag-tutqich"
              onMouseDown={() => {
                sudralmoqda.current = true;
              }}
            >
              ⋮
            </div>
            <div className="imtihon-panel-ong" style={{ flex: 1 }}>
              {savollarBlok}
            </div>
          </div>
        );
      })()}

      <div className="imtihon-pastki-panel">
        <button
          className="strelka"
          disabled={faolQism === 0}
          onClick={() => setFaolQism((q) => Math.max(0, q - 1))}
        >
          ←
        </button>
        {qismMalumot.map((qm, qi) => (
          <div
            key={qm.qism.id}
            className={`imtihon-part-tab ${qi === faolQism ? "faol" : ""}`}
            onClick={() => setFaolQism(qi)}
          >
            <strong>{qm.qism.sarlavha}:</strong>
            {qi === faolQism ? (
              <div className="raqamlar">
                {Array.from({ length: qm.soni }, (_, k) => {
                  const i = qm.boshIdx + k;
                  return (
                    <button
                      key={i}
                      className={javobBormi(javoblar[i]) ? "javob-berilgan" : ""}
                      onClick={(e) => {
                        e.stopPropagation();
                        savolgaOt(qi, i);
                      }}
                    >
                      {i + 1}
                    </button>
                  );
                })}
              </div>
            ) : (
              <span>
                {qm.soni} {t("imtihon_qism_soni")}
              </span>
            )}
          </div>
        ))}
        <button
          className="strelka"
          disabled={faolQism === qismMalumot.length - 1}
          onClick={() => setFaolQism((q) => Math.min(qismMalumot.length - 1, q + 1))}
        >
          →
        </button>

        {!natija ? (
          <button className="tugma katta" onClick={yuborishBosildi} disabled={yuklanmoqda || bloklanganOraliqda}>
            {yuklanmoqda ? t("tekshirilmoqda") : t("imtihon_topshirish")}
          </button>
        ) : (
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 22, fontWeight: 800, color: "var(--sariq)" }}>
              {natija.band != null ? Number(natija.band).toFixed(1) : "—"}
            </span>
            <span style={{ fontSize: 12.5 }}>
              {t("band_ball")} · {t("xom_ball")} {natija.ball}/{natija.jami}
            </span>
            {/* Vaqt tugab avtomatik yuborilgan bo'lsa — bu tugma o'rniga
                pastdagi bloklovchi "Keyingisi" (30s) oynasi ko'rsatiladi. */}
            {onYakunlandi && !vaqtSababliYakun && (
              <button className="tugma katta" onClick={() => onYakunlandi(natija)}>
                {t("mock_keyingi_bolim")}
              </button>
            )}
          </div>
        )}
      </div>
      {xato && (
        <div className="xato-xabar" style={{ marginTop: 10 }}>
          {xato}
          {testYoq && (
            <button className="tugma ikkinchi kichik" style={{ marginLeft: 10 }} onClick={royxatgaQayt}>
              {t("imtihon_royxatga_qaytish")}
            </button>
          )}
        </div>
      )}
    </div>
  );

  // Vaqt tugab (Mock ichida) avtomatik yuborilgach — imtihon oynasi
  // bloklanadi, "Keyingisi" (30s teskari sanoq) oynasi ochiladi
  // (2026-08-15). Qo'lda yakunlashda bu oyna chiqmaydi (yuqoridagi
  // "mock_keyingi_bolim" tugmasi o'zi ishlaydi).
  const vaqtModal =
    natija && onYakunlandi && vaqtSababliYakun ? (
      <VaqtTugadiModal
        t={t}
        onKeyingisi={() => {
          if (keyingigaOtildiRef.current) return;
          keyingigaOtildiRef.current = true;
          onYakunlandi(natija);
        }}
      />
    ) : null;

  return (
    <>
      {fokus ? <div className="imtihon-fokus-ustma">{mazmun}</div> : mazmun}
      {vaqtModal}
    </>
  );
}
