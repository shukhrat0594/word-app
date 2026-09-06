import { useEffect, useRef, useState } from "react";
import { api, apiBlobUrl, apiFayluniYuklab, apiForm, apiManzil, mediaManzil, tokenOl } from "../api";
import IjtimoiyIkon from "../components/IjtimoiyIkonlar";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";

// Tartib va yorliqlar backend bilan bir xil (accounts.Markaz.IJTIMOIY_MAYDONLAR).
export const TARMOQLAR = [
  { kalit: "telegram", nomi: "Telegram", namuna: "t.me/utmost" },
  { kalit: "instagram", nomi: "Instagram", namuna: "instagram.com/utmost" },
  { kalit: "youtube", nomi: "YouTube", namuna: "youtube.com/@utmost" },
  { kalit: "facebook", nomi: "Facebook", namuna: "facebook.com/utmost" },
];

/** Fayl yo'llaridan daraxt yasaydi (2026-09-07, foydalanuvchi talabi:
 * "ierarxik qila olasanmi").
 *
 * `[{nom: "kurslar/blok_rasm/a.png", hajm: 1234}, ...]` dan:
 *   kurslar > blok_rasm > a.png
 *
 * Har tugunda `soni` va `hajm` — o'zi va butun avlodi bo'yicha
 * yig'indi, shunda papkani ochmasdan ham ichida nima borligi ko'rinadi. */
function daraxtYasa(fayllar) {
  const ildiz = { bolalar: {}, soni: 0, hajm: 0, papka: true, nom: null };
  for (const { nom, hajm } of fayllar) {
    const bolaklar = nom.split("/");
    let tugun = ildiz;
    tugun.soni += 1;
    tugun.hajm += hajm;
    bolaklar.forEach((bolak, i) => {
      const oxirgimi = i === bolaklar.length - 1;
      if (!tugun.bolalar[bolak]) {
        tugun.bolalar[bolak] = {
          bolalar: {}, soni: 0, hajm: 0, papka: !oxirgimi,
          // Faqat FAYL tugunida to'ldiriladi — o'chirishga aynan shu
          // to'liq yo'l yuboriladi.
          nom: oxirgimi ? nom : null,
        };
      }
      tugun = tugun.bolalar[bolak];
      tugun.soni += 1;
      tugun.hajm += hajm;
    });
  }
  return ildiz;
}

/** Tugun ostidagi BARCHA fayl nomlari (rekursiv). */
function tugunFayllari(tugun) {
  if (tugun.nom) return [tugun.nom];
  return Object.values(tugun.bolalar).flatMap(tugunFayllari);
}

const MB = (b) => (b / 1024 / 1024).toFixed(1);

// Ko'rish mumkin bo'lgan turlar (2026-09-07). Rasm — oynada, audio —
// pleyer bilan. Qolganlari (PDF, ZIP) bosilmaydi: ularni ko'rsatishning
// foydasi yo'q, nomi allaqachon ko'rinib turibdi.
const RASM_KENGAYTMA = /\.(jpe?g|png|gif|webp|bmp|svg)$/i;
const AUDIO_KENGAYTMA = /\.(mp3|wav|ogg|m4a|webm)$/i;
const korsatsaBoladimi = (nom) => RASM_KENGAYTMA.test(nom) || AUDIO_KENGAYTMA.test(nom);

/** Daraxtning bitta qatori.
 *
 * Galochka papkada butun avlodni belgilaydi/olib tashlaydi; avlodning
 * bir qismi belgilangan bo'lsa "aniqlanmagan" (indeterminate) holatda
 * ko'rinadi — ya'ni papkani ochib ichidan tanlash mumkin. */
function MediaTugun({ nomi, tugun, yol, tanlangan, tanlash, ochiqlar, ochish, chuqurlik, korish }) {
  const fayllar = tugunFayllari(tugun);
  const belgilangan = fayllar.filter((f) => tanlangan.has(f)).length;
  const hammasi = fayllar.length > 0 && belgilangan === fayllar.length;
  const qisman = belgilangan > 0 && !hammasi;
  const ochiq = !!ochiqlar[yol];

  return (
    <>
      <tr>
        <td style={{ paddingLeft: chuqurlik * 18 }}>
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {tugun.papka ? (
              <button
                type="button"
                onClick={() => ochish(yol)}
                style={{
                  border: "none", background: "none", cursor: "pointer",
                  padding: 0, width: 16, fontSize: 11, lineHeight: 1,
                }}
              >
                {ochiq ? "▼" : "▶"}
              </button>
            ) : (
              <span style={{ width: 16, display: "inline-block" }} />
            )}
            <input
              type="checkbox"
              checked={hammasi}
              ref={(el) => { if (el) el.indeterminate = qisman; }}
              onChange={(e) => tanlash(fayllar, e.target.checked)}
            />
            {/* Rasm/audio bo'lsa nomiga bosib ko'rish mumkin
                (2026-09-07) — o'chirishdan oldin "bu aynan nima?"
                degan savolga javob beradi. */}
            {!tugun.papka && korsatsaBoladimi(nomi) ? (
              <button
                type="button"
                onClick={() => korish(tugun.nom)}
                title={nomi}
                style={{
                  border: "none", background: "none", padding: 0,
                  cursor: "pointer", textAlign: "left", wordBreak: "break-all",
                  color: "var(--havola, #06c)", textDecoration: "underline",
                  font: "inherit",
                }}
              >
                {RASM_KENGAYTMA.test(nomi) ? "🖼" : "🔊"} {nomi}
              </button>
            ) : (
              <span style={{ wordBreak: "break-all" }}>
                {tugun.papka ? "📁" : "📄"} {nomi}
              </span>
            )}
          </span>
        </td>
        <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
          {tugun.papka ? tugun.soni : ""}
        </td>
        <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>{MB(tugun.hajm)} MB</td>
      </tr>
      {ochiq &&
        Object.entries(tugun.bolalar)
          .sort((a, b) => b[1].hajm - a[1].hajm)
          .map(([bolaNomi, bola]) => (
            <MediaTugun
              key={bolaNomi}
              nomi={bolaNomi}
              tugun={bola}
              yol={`${yol}/${bolaNomi}`}
              tanlangan={tanlangan}
              tanlash={tanlash}
              ochiqlar={ochiqlar}
              ochish={ochish}
              chuqurlik={chuqurlik + 1}
              korish={korish}
            />
          ))}
    </>
  );
}

/** Markaz sozlamalari (2026-08-15) — avval ikkita alohida sahifa
 * ("Markaz sozlash" — logo/rang, "Ijtimoiy tarmoqlar") edi, bittaga
 * birlashtirildi + Backup bo'limi qo'shildi. Faqat OWNER ko'radi
 * (Layout.jsx). Backup — faqat baza (dumpdata/loaddata), R2 fayllarga
 * tegilmaydi (ikkala server bir xil R2 bucket'ga ulangan, fayl
 * manzillari baza orqali avtomatik to'g'ri ishlaydi). */
export default function MarkazSozlash() {
  const { t } = useI18n();
  const { yangila } = useProfil();
  const [markaz, setMarkaz] = useState(null);
  const [nom, setNom] = useState("");
  const [rang, setRang] = useState("#FFD400");
  const [logoFayl, setLogoFayl] = useState(null);
  const [ijtimoiy, setIjtimoiy] = useState({});
  const [xabar, setXabar] = useState("");
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  const [backupBand, setBackupBand] = useState(false);
  const [backupXato, setBackupXato] = useState("");
  const [backupXabar, setBackupXabar] = useState("");
  // Ishlatilmayotgan media (2026-09-07). `mediaSoat` — himoya
  // chegarasi: shu vaqtdan yangi fayllarga tegilmaydi. Standart 30
  // kun: prodda birinchi tozalash ehtiyotkor bo'lsin.
  const [mediaBand, setMediaBand] = useState(false);
  const [mediaXato, setMediaXato] = useState("");
  const [mediaXabar, setMediaXabar] = useState("");
  const [mediaNatija, setMediaNatija] = useState(null);
  const [mediaTasdiq, setMediaTasdiq] = useState(false);
  const [mediaSoat, setMediaSoat] = useState(720);
  // 2026-09-07: tanlov endi PAPKA nomi bo'yicha emas, aniq FAYL
  // nomlari to'plami bilan yuritiladi. Sabab: daraxtda papkani ham,
  // uning ichidagi bitta faylni ham alohida belgilash mumkin —
  // papka-darajasidagi bayroq buni ifodalay olmasdi.
  const [mediaTanlangan, setMediaTanlangan] = useState(() => new Set());
  const [mediaOchiqlar, setMediaOchiqlar] = useState({});
  // Ko'rish oynasi: {nom, url, xato} yoki null.
  const [mediaKorish, setMediaKorish] = useState(null);

  const mediaDaraxt = mediaNatija ? daraxtYasa(mediaNatija.fayllar) : null;
  const tanlanganFayllar = [...mediaTanlangan];
  const tanlanganHajm =
    (mediaNatija?.fayllar || [])
      .filter((f) => mediaTanlangan.has(f.nom))
      .reduce((s, f) => s + f.hajm, 0) / 1024 / 1024;

  /** Berilgan fayllarni belgilaydi yoki olib tashlaydi. */
  function mediaTanlash(fayllar, belgilansinmi) {
    setMediaTanlangan((eski) => {
      const yangi = new Set(eski);
      for (const f of fayllar) {
        if (belgilansinmi) yangi.add(f);
        else yangi.delete(f);
      }
      return yangi;
    });
  }

  function mediaOchish(yol) {
    setMediaOchiqlar((p) => ({ ...p, [yol]: !p[yol] }));
  }

  /** Faylni ko'rish oynasi (2026-09-07). `/media/` ochiq emas,
   * shuning uchun fayl autentifikatsiyalangan endpointdan blob
   * sifatida olinadi. Oyna yopilganda blob bo'shatiladi — aks holda
   * har bosishda xotirada 26 MB lik audio to'planib borardi. */
  async function mediaFaylKor(nom) {
    setMediaKorish({ nom, url: null, xato: "" });
    try {
      const url = await apiBlobUrl(`/api/media-tozalash/korish/?nom=${encodeURIComponent(nom)}`);
      setMediaKorish({ nom, url, xato: "" });
    } catch (e) {
      setMediaKorish({ nom, url: null, xato: e.message || t("xato_yuz_berdi") });
    }
  }

  function mediaKorishYop() {
    if (mediaKorish?.url) URL.revokeObjectURL(mediaKorish.url);
    setMediaKorish(null);
  }
  const [tanlanganFayl, setTanlanganFayl] = useState("");
  const tiklashFaylRef = useRef(null);

  function faylniTozala() {
    if (tiklashFaylRef.current) tiklashFaylRef.current.value = "";
    setTanlanganFayl("");
    setBackupXato("");
    setBackupXabar("");
  }

  // 2026-08-15: Railway ko'chirish davrida eski (Render) saytga adashib
  // kirishning oldini olish uchun — yoqilsa OWNER'dan boshqa hech kim
  // kira olmaydi (backend: `accounts.views.SaytHolatiView`/`XodimLoginView`).
  // Avtomatik kunlik zaxira (2026-09-03) — sozlamalar `/api/markaz-sozlama/`
  // dan keladi, ro'yxat esa `/api/zaxiralar/` dan.
  const [zaxiraAvtomatik, setZaxiraAvtomatik] = useState(false);
  const [zaxiraVaqti, setZaxiraVaqti] = useState("03:00");
  const [zaxiraKun, setZaxiraKun] = useState(7);
  const [zaxiralar, setZaxiralar] = useState([]);
  const [zaxiraBand, setZaxiraBand] = useState(false);
  const [zaxiraXato, setZaxiraXato] = useState("");
  const [zaxiraXabar, setZaxiraXabar] = useState("");
  // To'liq zaxira (2026-09-03) — media R2'dan BEVOSITA diskka.
  const [toliqBand, setToliqBand] = useState(false);
  const [toliq, setToliq] = useState(null);
  const toxtatRef = useRef(false);

  const [kirishCheklangan, setKirishCheklangan] = useState(false);
  const [aktivFoydalanuvchilar, setAktivFoydalanuvchilar] = useState(0);
  const [cheklovBand, setCheklovBand] = useState(false);
  const [cheklovXato, setCheklovXato] = useState("");

  useEffect(() => {
    api("/api/markaz-sozlama/").then((m) => {
      setNom(m.name || "");
      setMarkaz(m);
      setRang(m.brend_rang);
      setIjtimoiy(m.ijtimoiy || {});
      setZaxiraAvtomatik(!!m.zaxira_avtomatik);
      setZaxiraVaqti(m.zaxira_vaqti || "03:00");
      setZaxiraKun(m.zaxira_saqlash_kuni ?? 7);
    }).catch(() => {});
    saytHolatiniYukla();
    zaxiralarniYukla();
  }, []);

  function saytHolatiniYukla() {
    return api("/api/sayt-holati/")
      .then((r) => {
        setKirishCheklangan(r.kirish_cheklangan);
        setAktivFoydalanuvchilar(r.aktiv_foydalanuvchilar || 0);
      })
      .catch(() => {});
  }

  async function kirishCheklovniOzgartir(yangiQiymat) {
    // 2026-08-15 talabi: yoqishdan oldin — hozir tizimda ishlayotgan
    // foydalanuvchilar bo'lsa ogohlantirish (ular DARHOL chiqarib
    // yuboriladi, chunki cheklov har so'rovda tekshiriladi).
    if (yangiQiymat) {
      const holat = await api("/api/sayt-holati/").catch(() => null);
      const soni = holat?.aktiv_foydalanuvchilar ?? aktivFoydalanuvchilar;
      setAktivFoydalanuvchilar(soni);
      const savol = soni > 0
        ? `${t("aktiv_foydalanuvchilar_ogoh").replace("{n}", soni)}\n\n${t("kirishni_cheklash_tasdiq")}`
        : t("kirishni_cheklash_tasdiq");
      if (!window.confirm(savol)) return;
    }

    setCheklovXato("");
    setCheklovBand(true);
    try {
      const r = await api("/api/sayt-holati/", {
        method: "PATCH",
        body: { kirish_cheklangan: yangiQiymat },
      });
      setKirishCheklangan(r.kirish_cheklangan);
      await saytHolatiniYukla();
    } catch (e) {
      setCheklovXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setCheklovBand(false);
    }
  }

  function zaxiralarniYukla() {
    return api("/api/zaxiralar/").then(setZaxiralar).catch(() => {});
  }

  /** Zaxira sozlamalarini saqlaydi. Alohida (umumiy "Saqlash" emas) —
   * shunda logo/ijtimoiy havolalar qayta yuborilmaydi va bu bo'lim
   * mustaqil ishlaydi. */
  async function zaxiraSozlamaSaqla() {
    setZaxiraXato("");
    setZaxiraXabar("");
    setZaxiraBand(true);
    try {
      const fd = new FormData();
      fd.append("zaxira_avtomatik", zaxiraAvtomatik ? "1" : "0");
      fd.append("zaxira_vaqti", zaxiraVaqti);
      fd.append("zaxira_saqlash_kuni", String(zaxiraKun));
      const m = await apiForm("/api/markaz-sozlama/", { method: "PATCH", formData: fd });
      setZaxiraAvtomatik(!!m.zaxira_avtomatik);
      setZaxiraVaqti(m.zaxira_vaqti || "03:00");
      setZaxiraKun(m.zaxira_saqlash_kuni ?? 7);
      setZaxiraXabar(t("saqlandi"));
    } catch (e) {
      setZaxiraXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setZaxiraBand(false);
    }
  }

  async function zaxiraHozirOl() {
    setZaxiraXato("");
    setZaxiraXabar("");
    setZaxiraBand(true);
    try {
      await api("/api/zaxiralar/", { method: "POST", body: {} });
      await zaxiralarniYukla();
      setZaxiraXabar(t("zaxira_olindi"));
    } catch (e) {
      setZaxiraXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setZaxiraBand(false);
    }
  }

  async function zaxiraYuklabOl(id) {
    setZaxiraXato("");
    setZaxiraBand(true);
    try {
      await apiFayluniYuklab(`/api/zaxiralar/${id}/yuklab-olish/`);
      // Yuklab olingani serverda belgilandi — ro'yxatni va tepadagi
      // tasmani yangilash uchun qayta o'qiymiz.
      await zaxiralarniYukla();
      if (yangila) yangila();
    } catch (e) {
      setZaxiraXato(e.data?.detail || e.message || t("xato_yuz_berdi"));
    } finally {
      setZaxiraBand(false);
    }
  }

  // ── To'liq zaxira ────────────────────────────────────────────────
  // Fayllar SERVERDAN O'TMAYDI: server faqat ro'yxat va imzolangan
  // havola beradi, brauzer esa R2'dan to'g'ridan-to'g'ri diskka oqim
  // bilan yozadi (`accounts/zaxira_media.py` izohiga qara). Shu sababli
  // 6+ GB ham Railway chegarasiga urilmaydi.

  /** `kurslar/audio` kabi yo'l uchun ichma-ich papkalarni yaratadi. */
  async function papkaniOl(kok, qismlar) {
    let joriy = kok;
    for (const q of qismlar) {
      joriy = await joriy.getDirectoryHandle(q, { create: true });
    }
    return joriy;
  }

  /** Papkada shu nomli fayl bor bo'lsa hajmini, aks holda `null`. */
  async function mavjudHajm(papka, nom) {
    try {
      const h = await papka.getFileHandle(nom);
      return (await h.getFile()).size;
    } catch {
      return null;
    }
  }

  /** Bitta faylni oqim bilan diskka yozadi. Imzolangan havola tashqi
   * (R2) bo'lsa sarlavhasiz olinadi; lokal ishlab chiqishda esa havola
   * bizning endpointga ishora qiladi va token kerak bo'ladi. */
  async function faylniYoz(papka, nom, url) {
    // Nisbiy yo'l (lokal ishlab chiqish rejimi) bo'lsa — backend
    // domenini `apiManzil` qo'shadi va token kerak; imzolangan R2
    // havolasi mutlaq bo'ladi va sarlavhasiz olinadi.
    const ichkimi = url.startsWith("/");
    const res = await fetch(
      ichkimi ? apiManzil(url) : url,
      ichkimi ? { headers: { Authorization: `Bearer ${tokenOl()}` } } : {},
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const h = await papka.getFileHandle(nom, { create: true });
    const yozuvchi = await h.createWritable();
    await res.body.pipeTo(yozuvchi);
  }

  /** Sahifadagi fayllarni bir vaqtda 4 tadan yuklaydi (foydalanuvchi
   * talabi: "hammasini to'liq olmasin, bir nechtadan olsin"). Papkada
   * bor va hajmi mos fayl tashlab ketiladi — uzilgan yuklash boshidan
   * boshlanmaydi. */
  async function paketBilanYukla(kok, fayllar) {
    const NAVBAT = [...fayllar];
    const PAKET = 4;

    async function ishchi() {
      while (NAVBAT.length && !toxtatRef.current) {
        const f = NAVBAT.shift();
        const qismlar = f.yol.split("/");
        const nom = qismlar.pop();
        const papka = qismlar.length ? await papkaniOl(kok, qismlar) : kok;
        const bor = await mavjudHajm(papka, nom);
        if (bor !== f.hajm) {
          await faylniYoz(papka, nom, f.url);
        }
        setToliq((v) => v && {
          ...v,
          joriy: v.joriy + 1,
          bayt: v.bayt + f.hajm,
          nomi: f.yol,
          otkazilgan: v.otkazilgan + (bor === f.hajm ? 1 : 0),
        });
      }
    }

    await Promise.all(Array.from({ length: PAKET }, ishchi));
  }

  async function toliqZaxiraOl() {
    if (!window.showDirectoryPicker) {
      setZaxiraXato(t("zaxira_toliq_brauzer"));
      return;
    }
    let kok;
    try {
      kok = await window.showDirectoryPicker({ mode: "readwrite" });
    } catch {
      return; // foydalanuvchi bekor qildi
    }
    setZaxiraXato("");
    setZaxiraXabar("");
    toxtatRef.current = false;
    setToliqBand(true);
    try {
      const hisob = await api("/api/zaxira/media/?hisob=1");
      setToliq({
        joriy: 0, jami: hisob.jami_soni, bayt: 0,
        jamiBayt: hisob.jami_hajm, nomi: "", otkazilgan: 0,
      });

      // 1) Bazaning o'zi — kichik, serverdan keladi.
      //
      // `apiManzil` SHART (2026-09-03 (2), kod-ревьюda topilgan haqiqiy
      // xato): prodda frontend va backend ALOHIDA domenlarda va nisbiy
      // "/api/..." yo'li frontend servisiga ketardi. `vite preview` esa
      // mavjud bo'lmagan yo'lga SPA fallback bilan `index.html`ni 200
      // qilib qaytaradi — ya'ni `baza.ok` true bo'lib, papkadagi
      // `baza.zip` ichiga ZIP emas, HTML yozilib qolardi. Xato ham
      // chiqmasdi: buzuqligi faqat tiklashga urinilganda bilinardi.
      const baza = await fetch(apiManzil("/api/backup/yuklab-olish/"), {
        headers: { Authorization: `Bearer ${tokenOl()}` },
      });
      if (baza.ok) {
        const h = await kok.getFileHandle("baza.zip", { create: true });
        const yozuvchi = await h.createWritable();
        await baza.body.pipeTo(yozuvchi);
      }

      // 2) Media — sahifalab, har sahifa 4 tadan.
      let kursor = null;
      do {
        const yol = kursor
          ? `/api/zaxira/media/?kursor=${encodeURIComponent(kursor)}`
          : "/api/zaxira/media/";
        const sahifa = await api(yol);
        await paketBilanYukla(kok, sahifa.fayllar);
        kursor = sahifa.keyingi;
      } while (kursor && !toxtatRef.current);

      setZaxiraXabar(toxtatRef.current ? t("zaxira_toliq_toxtatildi") : t("zaxira_toliq_tugadi"));
    } catch (e) {
      setZaxiraXato(e.data?.detail || e.message || t("xato_yuz_berdi"));
    } finally {
      setToliqBand(false);
      setToliq(null);
      toxtatRef.current = false;
    }
  }

  async function saqla() {
    setXato("");
    setXabar("");
    setBand(true);
    try {
      const fd = new FormData();
      fd.append("name", nom.trim());
      fd.append("brend_rang", rang);
      if (logoFayl) fd.append("logo", logoFayl);
      TARMOQLAR.forEach(({ kalit }) => fd.append(kalit, ijtimoiy[kalit] || ""));
      const m = await apiForm("/api/markaz-sozlama/", { method: "PATCH", formData: fd });
      setMarkaz(m);
      setNom(m.name || "");
      setLogoFayl(null);
      setIjtimoiy(m.ijtimoiy || {});
      setXabar(t("saqlandi"));
      // Pastki panel (ijtimoiy havolalar) darhol yangilanishi uchun.
      if (yangila) yangila();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  /** Skanerlash — hech narsa o'chirmaydi, faqat ro'yxat beradi. */
  async function mediaSkanerla() {
    setMediaBand(true);
    setMediaXato("");
    setMediaXabar("");
    setMediaNatija(null);
    setMediaOchiqlar({});
    try {
      const j = await api(`/api/media-tozalash/?soat=${mediaSoat}`);
      setMediaNatija(j);
      // Boshida HAMMASI belgilangan — keraksizini olib tashlash
      // belgilashdan ko'ra tezroq (odatda hammasi o'chiriladi).
      setMediaTanlangan(new Set(j.fayllar.map((f) => f.nom)));
    } catch (e) {
      setMediaXato(e.data?.detail || e.message || t("xato_yuz_berdi"));
    } finally {
      setMediaBand(false);
    }
  }

  /** O'chirish — AYNAN skanerlashda ko'rilgan ro'yxat yuboriladi,
   * server qaytadan skanerlamaydi. Shu orada bazaga biriktirilgan
   * fayl bo'lsa, server uni baribir o'tkazib yuboradi. */
  /** O'chirish — ro'yxat BO'LAKLAB yuboriladi.
   *
   * 2026-09-07, prodda topildi: 1105 faylni bitta so'rovda yuborganda
   * server javob berishga ulgurmay "Failed to fetch" chiqardi (R2 da
   * har fayl alohida tarmoq murojaati). Bo'laklab yuborilganda har
   * so'rov qisqa bo'ladi va jarayon ko'rinib turadi; uzilib qolsa ham
   * o'chirilganlari o'chgan bo'ladi, qaytadan bosish yetarli. */
  async function mediaOchir() {
    setMediaBand(true);
    setMediaXato("");
    const BOLAK = 300;
    let ochirildi = 0;
    let hajm = 0;
    try {
      for (let i = 0; i < tanlanganFayllar.length; i += BOLAK) {
        const bolak = tanlanganFayllar.slice(i, i + BOLAK);
        setMediaXabar(
          `${Math.min(i + BOLAK, tanlanganFayllar.length)} / ${tanlanganFayllar.length}...`,
        );
        const j = await api("/api/media-tozalash/", {
          method: "POST",
          body: { fayllar: bolak },
        });
        ochirildi += j.ochirildi;
        hajm += j.ozod_hajm;
      }
      setMediaXabar(
        t("media_tozalash_natija")
          .replace("{soni}", ochirildi)
          .replace("{hajm}", (hajm / 1024 / 1024).toFixed(1)),
      );
      setMediaNatija(null);
      setMediaTasdiq(false);
    } catch (e) {
      setMediaXato(
        `${e.data?.detail || e.message || t("xato_yuz_berdi")} — ` +
        `${ochirildi} ta o'chirildi, qolgani uchun qaytadan bosing`,
      );
    } finally {
      setMediaBand(false);
    }
  }

  async function backupYuklabOl() {
    setBackupXato("");
    setBackupXabar("");
    setBackupBand(true);
    try {
      await apiFayluniYuklab("/api/backup/yuklab-olish/");
      setBackupXabar(t("backup_yuklandi"));
    } catch (e) {
      setBackupXato(e.message || t("xato_yuz_berdi"));
    } finally {
      setBackupBand(false);
    }
  }

  async function backupdanTiklash() {
    const fayl = tiklashFaylRef.current?.files?.[0];
    if (!fayl) {
      setBackupXato(t("backup_fayl_tanlanmagan"));
      return;
    }
    if (!window.confirm(t("backup_tiklash_tasdiq"))) return;

    setBackupXato("");
    setBackupXabar("");
    setBackupBand(true);
    try {
      const fd = new FormData();
      fd.append("fayl", fayl);
      fd.append("tasdiqlash", "HA");
      const res = await apiForm("/api/backup/tiklash/", { method: "POST", formData: fd });
      setBackupXabar(res.detail || t("backup_tiklandi"));
      if (tiklashFaylRef.current) tiklashFaylRef.current.value = "";
      setTanlanganFayl("");
    } catch (e) {
      setBackupXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setBackupBand(false);
    }
  }

  if (!markaz) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <div style={{ display: "grid", gap: 20, maxWidth: 560 }}>
      <div className="karta">
        <h3>{markaz.name}</h3>
        <p className="izoh">{t("markaz_sozlama_izoh")}</p>

        <div style={{ display: "grid", gap: 16, marginTop: 4 }}>
          {/* 2026-08-18, foydalanuvchi talabi: markaz nomi shu yerdan
              o'zgartiriladi — u brauzer tab sarlavhasida, tepa panelda,
              profilda va login ekranida ko'rinadi. */}
          <div>
            <div className="izoh" style={{ marginBottom: 6 }}>{t("markaz_nomi")}</div>
            <input
              type="text"
              value={nom}
              maxLength={200}
              onChange={(e) => setNom(e.target.value)}
              style={{ width: "100%" }}
            />
          </div>

          <div>
            <div className="izoh" style={{ marginBottom: 6 }}>{t("logo")}</div>
            {markaz.logo_url && (
              <img
                src={mediaManzil(markaz.logo_url)}
                alt={markaz.name}
                style={{ height: 48, marginBottom: 8, display: "block" }}
              />
            )}
            <input type="file" accept="image/*" onChange={(e) => setLogoFayl(e.target.files[0])} />
          </div>

          <div>
            <div className="izoh" style={{ marginBottom: 6 }}>{t("brend_rangi")}</div>
            <input
              type="color"
              value={rang}
              onChange={(e) => setRang(e.target.value)}
              style={{ width: 60, height: 40, padding: 2 }}
            />
          </div>

          <div>
            <div className="izoh" style={{ marginBottom: 6 }}>{t("nav_ijtimoiy")}</div>
            <div style={{ display: "grid", gap: 10 }}>
              {TARMOQLAR.map(({ kalit, nomi, namuna }) => (
                <div key={kalit} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span
                    style={{ width: 130, fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 8 }}
                  >
                    <IjtimoiyIkon kalit={kalit} /> {nomi}
                  </span>
                  <input
                    style={{ flex: 1, minWidth: 0 }}
                    placeholder={namuna}
                    value={ijtimoiy[kalit] || ""}
                    onChange={(e) => setIjtimoiy({ ...ijtimoiy, [kalit]: e.target.value })}
                  />
                </div>
              ))}
            </div>
          </div>

          {xato && <div className="xato-xabar">{xato}</div>}
          {xabar && <div className="izoh">{xabar}</div>}
          <button className="tugma" onClick={saqla} disabled={band}>
            {t("saqlash")}
          </button>
        </div>
      </div>

      <div className="karta">
        <h3>{t("kirish_cheklovi_sarlavha")}</h3>
        <p className="izoh">{t("kirish_cheklovi_izoh")}</p>

        <div style={{ display: "grid", gap: 10, marginTop: 4 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span className={`chip ${kirishCheklangan ? "tugadi" : "bor"}`}>
              {kirishCheklangan ? t("kirish_cheklangan_holat") : t("kirish_ochiq_holat")}
            </span>
            {!kirishCheklangan && aktivFoydalanuvchilar > 0 && (
              <span className="izoh">
                {t("aktiv_foydalanuvchilar_ogoh").replace("{n}", aktivFoydalanuvchilar)}
              </span>
            )}
          </div>
          {kirishCheklangan ? (
            <button
              className="tugma"
              onClick={() => kirishCheklovniOzgartir(false)}
              disabled={cheklovBand}
              style={{ width: "fit-content" }}
            >
              {t("cheklovni_olib_tashlash")}
            </button>
          ) : (
            <button
              className="tugma xavfli"
              onClick={() => kirishCheklovniOzgartir(true)}
              disabled={cheklovBand}
              style={{ width: "fit-content" }}
            >
              {t("kirishni_cheklash")}
            </button>
          )}
          {cheklovXato && <div className="xato-xabar">{cheklovXato}</div>}
        </div>
      </div>

      {/* Avtomatik kunlik zaxira (2026-09-03, foydalanuvchi talabi) —
          faqat BAZA, R2'ga saqlanadi. Media uchun alohida "To'liq
          zaxira" rejada. */}
      <div className="karta">
        <h3>{t("zaxira_sarlavha")}</h3>
        <p className="izoh">{t("zaxira_izoh")}</p>

        <div style={{ display: "grid", gap: 12, marginTop: 4 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input
              type="checkbox"
              checked={zaxiraAvtomatik}
              onChange={(e) => setZaxiraAvtomatik(e.target.checked)}
              disabled={zaxiraBand}
            />
            {t("zaxira_yoqish")}
          </label>

          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
            <label style={{ display: "grid", gap: 4 }}>
              <span className="izoh">{t("zaxira_vaqti")}</span>
              <input
                type="time"
                value={zaxiraVaqti}
                onChange={(e) => setZaxiraVaqti(e.target.value)}
                disabled={zaxiraBand || !zaxiraAvtomatik}
                style={{ maxWidth: 120 }}
              />
            </label>
            <label style={{ display: "grid", gap: 4 }}>
              <span className="izoh">{t("zaxira_saqlash_kuni")}</span>
              <input
                type="number"
                min="1"
                max="365"
                value={zaxiraKun}
                onChange={(e) => setZaxiraKun(e.target.value)}
                disabled={zaxiraBand}
                style={{ maxWidth: 100 }}
              />
            </label>
            <button className="tugma" onClick={zaxiraSozlamaSaqla} disabled={zaxiraBand}>
              {t("saqlash")}
            </button>
            <button className="tugma ikkinchi" onClick={zaxiraHozirOl} disabled={zaxiraBand || toliqBand}>
              {t("zaxira_hozir_ol")}
            </button>
          </div>

          {/* To'liq zaxira — baza + BARCHA media. Media serverdan
              o'tmaydi, R2'dan bevosita diskka tushadi. */}
          <div style={{ borderTop: "1px solid var(--chiziq)", paddingTop: 12 }}>
            <div className="izoh" style={{ marginBottom: 8 }}>{t("zaxira_toliq_izoh")}</div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
              <button className="tugma" onClick={toliqZaxiraOl} disabled={zaxiraBand || toliqBand}>
                {t("zaxira_toliq")}
              </button>
              {toliqBand && (
                <button
                  type="button"
                  className="tugma ikkinchi"
                  onClick={() => { toxtatRef.current = true; }}
                >
                  {t("zaxira_toxtatish")}
                </button>
              )}
            </div>
            {toliq && (
              <div className="izoh" style={{ marginTop: 8 }}>
                {toliq.joriy} / {toliq.jami} {t("zaxira_fayl")} ·{" "}
                {(toliq.bayt / 1e9).toFixed(2)} / {(toliq.jamiBayt / 1e9).toFixed(2)} GB
                {toliq.otkazilgan > 0 && ` · ${toliq.otkazilgan} ${t("zaxira_otkazilgan")}`}
                <div style={{ opacity: 0.7, wordBreak: "break-all" }}>{toliq.nomi}</div>
              </div>
            )}
          </div>

          <div className="izoh">{t("zaxira_muddat_izoh")}</div>

          {zaxiralar.length > 0 && (
            <div style={{ display: "grid", gap: 6 }}>
              {zaxiralar.map((z) => (
                <div
                  key={z.id}
                  style={{
                    display: "flex", alignItems: "center", gap: 10,
                    flexWrap: "wrap", borderTop: "1px solid var(--chiziq)", paddingTop: 6,
                  }}
                >
                  <strong style={{ minWidth: 96 }}>{z.sana}</strong>
                  <span className="izoh">
                    {z.turi === "qolda" ? t("zaxira_qolda") : t("zaxira_avtomatik_belgi")}
                  </span>
                  <span className="izoh">{(z.hajm / 1e6).toFixed(2)} MB</span>
                  {z.xato ? (
                    <span className="xato-xabar">{z.xato}</span>
                  ) : (
                    <>
                      <span className="izoh">
                        {z.yuklab_olindi ? `✓ ${t("zaxira_yuklab_olingan")}` : `⚠ ${t("zaxira_yuklanmagan")}`}
                      </span>
                      <button
                        type="button"
                        className="tugma ikkinchi kichik"
                        onClick={() => zaxiraYuklabOl(z.id)}
                        disabled={zaxiraBand || !z.fayl_bor}
                      >
                        {t("backup_yuklab_olish")}
                      </button>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}

          {zaxiraXato && <div className="xato-xabar">{zaxiraXato}</div>}
          {zaxiraXabar && <div className="izoh">{zaxiraXabar}</div>}
        </div>
      </div>

      <div className="karta">
        <h3>{t("backup_sarlavha")}</h3>
        <p className="izoh">{t("backup_izoh")}</p>

        <div style={{ display: "grid", gap: 14, marginTop: 4 }}>
          <div>
            <button className="tugma" onClick={backupYuklabOl} disabled={backupBand}>
              {t("backup_yuklab_olish")}
            </button>
          </div>

          <div>
            <div className="izoh" style={{ marginBottom: 6 }}>{t("backup_tiklash")}</div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <input
                type="file"
                accept=".zip"
                ref={tiklashFaylRef}
                onChange={(e) => setTanlanganFayl(e.target.files?.[0]?.name || "")}
              />
              {tanlanganFayl && (
                <button
                  type="button"
                  className="tugma ikkinchi"
                  onClick={faylniTozala}
                  disabled={backupBand}
                >
                  {t("faylni_ochirish")}
                </button>
              )}
              <button className="tugma xavfli" onClick={backupdanTiklash} disabled={backupBand}>
                {t("backup_tiklash")}
              </button>
            </div>
          </div>

          {backupXato && <div className="xato-xabar">{backupXato}</div>}
          {backupXabar && <div className="izoh">{backupXabar}</div>}
        </div>
      </div>

      {/* Ishlatilmayotgan media (2026-09-07, foydalanuvchi talabi:
          "R2 da turgan medialarning qaysi biriga hech qanday link
          bo'lmasa, shu mediani o'chirib tashlash kerak").
          IKKI BOSQICH: avval skanerlash (hech narsa o'chmaydi), keyin
          ro'yxatni ko'rib turib o'chirish. */}
      <div className="karta">
        <h3>{t("media_tozalash_sarlavha")}</h3>
        <p className="izoh">{t("media_tozalash_izoh")}</p>

        <div style={{ display: "grid", gap: 14, marginTop: 4 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <button className="tugma" onClick={mediaSkanerla} disabled={mediaBand}>
              {mediaBand && !mediaNatija ? "⏳" : t("media_tozalash_skan")}
            </button>
            <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span className="izoh">{t("media_tozalash_himoya")}</span>
              <select
                value={mediaSoat}
                onChange={(e) => setMediaSoat(Number(e.target.value))}
                disabled={mediaBand}
              >
                <option value={720}>30 {t("media_tozalash_kun")}</option>
                <option value={168}>7 {t("media_tozalash_kun")}</option>
                <option value={24}>1 {t("media_tozalash_kun")}</option>
              </select>
            </label>
          </div>

          {mediaNatija && (
            <div>
              {/* Fayllar QAYERDA saqlanayotgani (2026-09-07) —
                  o'chirish qaysi omborga tegishini bilib turish uchun. */}
              {mediaNatija.saqlash && (
                <div className="izoh" style={{ marginBottom: 8 }}>
                  {mediaNatija.saqlash.tur === "s3" ? "☁" : "💽"}{" "}
                  {mediaNatija.saqlash.nomi}
                  {mediaNatija.saqlash.bucket ? ` — ${mediaNatija.saqlash.bucket}` : ""}
                </div>
              )}
              {mediaNatija.soni === 0 ? (
                <div className="izoh">{t("media_tozalash_toza")}</div>
              ) : (
                <>
                  <div style={{ marginBottom: 8 }}>
                    <strong>
                      {mediaNatija.soni} {t("media_tozalash_fayl")} ·{" "}
                      {(mediaNatija.jami_hajm / 1024 / 1024).toFixed(1)} MB
                    </strong>
                  </div>
                  {/* Ierarxik daraxt (2026-09-07, foydalanuvchi talabi:
                      "ierarxiyani yuqori qatlamiga galochka qo'ysam
                      ichidagi hammasi o'chsin, agar uni ochib
                      ichidagilarga alohida galochka qo'ysam ... faqat
                      galochkasi borlari o'chsin").

                      Boshida hammasi belgilangan va papkalar YOPIQ —
                      1600+ faylni birdan chizish sahifani og'irlashtirardi. */}
                  <div
                    style={{
                      maxHeight: 380, overflowY: "auto", marginBottom: 10,
                      border: "1px solid var(--chegara, #ddd)", borderRadius: 6,
                    }}
                  >
                    <table className="oddiy-jadval" style={{ width: "100%" }}>
                      <tbody>
                        {Object.entries(mediaDaraxt.bolalar)
                          .sort((a, b) => b[1].hajm - a[1].hajm)
                          .map(([nomi, tugun]) => (
                            <MediaTugun
                              key={nomi}
                              nomi={nomi}
                              tugun={tugun}
                              yol={nomi}
                              tanlangan={mediaTanlangan}
                              tanlash={mediaTanlash}
                              ochiqlar={mediaOchiqlar}
                              ochish={mediaOchish}
                              chuqurlik={0}
                              korish={mediaFaylKor}
                            />
                          ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="izoh" style={{ marginBottom: 10 }}>
                    {t("media_tozalash_himoyalangan")}: {mediaNatija.himoyalangan} ·{" "}
                    {t("media_tozalash_chetlab")}: {mediaNatija.chetlab_otilgan}
                  </div>
                  <button
                    className="tugma xavfli"
                    onClick={() => setMediaTasdiq(true)}
                    disabled={mediaBand || tanlanganFayllar.length === 0}
                  >
                    {t("media_tozalash_ochir")} ({tanlanganFayllar.length} · {tanlanganHajm.toFixed(1)} MB)
                  </button>
                </>
              )}
            </div>
          )}

          {mediaXato && <div className="xato-xabar">{mediaXato}</div>}
          {mediaXabar && <div className="izoh">{mediaXabar}</div>}
        </div>
      </div>

      {/* Faylni ko'rish oynasi (2026-09-07) — o'chirishdan oldin
          "bu aynan qaysi media?" degan savolga javob. */}
      {mediaKorish && (
        <div className="blok-yuklash-qoplama" onClick={mediaKorishYop}>
          <div
            className="blok-tasdiq-karta"
            style={{ maxWidth: "min(90vw, 900px)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="blok-tasdiq-sarlavha-qator">
              <strong style={{ wordBreak: "break-all", fontSize: 13 }}>{mediaKorish.nom}</strong>
            </div>
            <div style={{ margin: "10px 0", textAlign: "center", minHeight: 60 }}>
              {mediaKorish.xato ? (
                <div className="xato-xabar">{mediaKorish.xato}</div>
              ) : !mediaKorish.url ? (
                <div className="izoh">{t("yuklanmoqda")}</div>
              ) : RASM_KENGAYTMA.test(mediaKorish.nom) ? (
                <img
                  src={mediaKorish.url}
                  alt={mediaKorish.nom}
                  style={{ maxWidth: "100%", maxHeight: "70vh" }}
                />
              ) : (
                <audio src={mediaKorish.url} controls style={{ width: "100%" }} />
              )}
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button type="button" className="tugma ikkinchi" onClick={mediaKorishYop}>
                {t("yopish")}
              </button>
            </div>
          </div>
        </div>
      )}

      {mediaTasdiq && mediaNatija && (
        <div className="blok-yuklash-qoplama">
          <div className="blok-tasdiq-karta" style={{ maxWidth: 440 }}>
            <div className="blok-tasdiq-sarlavha-qator">
              <strong>{t("media_tozalash_ochir")}</strong>
            </div>
            <div style={{ marginBottom: 14 }}>
              {t("media_tozalash_tasdiq")
                .replace("{soni}", tanlanganFayllar.length)
                .replace("{hajm}", tanlanganHajm.toFixed(1))}
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button className="tugma ikkinchi" onClick={() => setMediaTasdiq(false)}>
                {t("yoq")}
              </button>
              <button className="tugma xavfli" onClick={mediaOchir} disabled={mediaBand}>
                {mediaBand ? "⏳" : t("ha")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
