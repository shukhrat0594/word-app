import { useEffect, useRef, useState } from "react";
import { api, apiBlobUrl, apiForm } from "../api";
import { AUDIO_HIMOYA, faqatBittaAudioIjro } from "../audio";
import BlokMashqi from "../components/BlokMashqi";
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

/** Talaba uchun — bitta mashqqa javob yozish va natija ko'rish.
 * `raqam` (2026-07-27) — "raqamlangan mashqlar" talabi bo'yicha har bir
 * mashq tartib raqami bilan ko'rsatiladi. */
function TalabaMashqi({ mashq, raqam }) {
  const { t } = useI18n();
  const [javoblar, setJavoblar] = useState(mashq.savollar.map(() => ""));
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
            <button className="tugma ikkinchi" onClick={tekshir} disabled={yuklanmoqda}>
              {yuklanmoqda ? t("tekshirilmoqda") : t("tekshirish")}
            </button>
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

/** Admin/owner uchun — bitta tugunning mashqlarini boshqarish (ro'yxat,
 * o'chirish, rasm/audio biriktirish). `jsonKiritishKorinadi=false`
 * (2026-07-27) — Beginner Unit'lari ichidagi "Mashqlar" bo'limida JSON
 * orqali qo'shish endi Unit darajasida (AdminUnitKiritish) bo'ladi, bu
 * yerda faqat ro'yxat+fayl biriktirish qoladi. Boshqa (flat) bo'limlar
 * uchun avvalgidek JSON+AI promt ko'rinadi. */
/** Admin uchun — bitta mashqning to'g'ri javoblarini QO'LDA (har savol
 * uchun matn maydoni) yoki Excel (.xlsx: 1-ustun savol raqami, 2-ustun
 * javob) orqali ommaviy tahrirlash (2026-07-29 talabi). */
function MashqJavoblariTahriri({ mashq, royxatniYangila }) {
  const { t } = useI18n();
  const [qiymatlar, setQiymatlar] = useState(
    () => mashq.savollar.map((s) => (Array.isArray(s.togri) ? s.togri.join(", ") : (s.togri || "")))
  );
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
      const javoblar = qiymatlar.map((v, i) => ({ raqam: i + 1, togri: v }));
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
              onChange={(e) => {
                const v = e.target.value;
                setQiymatlar((joriy) => joriy.map((x, j) => (j === i ? v : x)));
              }}
              placeholder={t("kurs_javob_kirit")}
              style={{ flex: 1, maxWidth: 260 }}
            />
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
  const [jsonMatn, setJsonMatn] = useState('[\n  {"matn": "", "savollar": [{"savol": "...", "togri": "..."}]}\n]');
  const [xato, setXato] = useState("");
  const [saqlanmoqda, setSaqlanmoqda] = useState(false);
  const [audioZipXato, setAudioZipXato] = useState("");
  const [audioZipYuklanmoqda, setAudioZipYuklanmoqda] = useState(false);
  const [promtKorinadi, setPromtKorinadi] = useState(false);
  const [nusxalandi, setNusxalandi] = useState(false);
  // 2026-07-30 talabi: ZIP shart emas — bitta rasm tanlab, bitta mashq
  // qo'shish (AI to'r+prompt bilan o'qiydi). Aniq javobli bo'sh joy
  // uchun AI javobni bilmasa ham savol yaratiladi ("javob talab
  // qiladi") — shu haqda qisqa xabar ko'rsatiladi.
  const [rasmMashqXato, setRasmMashqXato] = useState("");
  const [rasmMashqYuklanmoqda, setRasmMashqYuklanmoqda] = useState(false);
  const [rasmMashqXabar, setRasmMashqXabar] = useState("");
  // 2026-07-30 talabi: har mashqni YANGI rasm bilan almashtirish (o'sha
  // mashqning bloklari qayta hisoblanadi, o'rni/id o'zgarmaydi).
  const [qaytaYuklanayotganId, setQaytaYuklanayotganId] = useState(null);
  const [qaytaYuklashXato, setQaytaYuklashXato] = useState("");

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

  async function audioZipYukla(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setAudioZipXato("");
    setAudioZipYuklanmoqda(true);
    try {
      const fd = new FormData();
      fd.append("zip_fayl", fayl);
      await apiForm(`/api/kurslar/${tugunId}/audio-zip/`, { method: "POST", formData: fd });
      yukla();
    } catch (e2) {
      setAudioZipXato(e2.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setAudioZipYuklanmoqda(false);
    }
  }

  async function rasmdanMashqQoshish(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setRasmMashqXato("");
    setRasmMashqXabar("");
    setRasmMashqYuklanmoqda(true);
    try {
      const fd = new FormData();
      fd.append("rasm", fayl);
      const yaratilgan = await apiForm(`/api/kurslar/${tugunId}/mashq-rasm-qoshish/`, {
        method: "POST",
        formData: fd,
      });
      setRasmMashqXabar(
        yaratilgan.javob_talab_qiluvchi_soni > 0
          ? `${t("kurs_mashq_qoshildi")} — ${yaratilgan.javob_talab_qiluvchi_soni} ${t("kurs_javob_talab")}`
          : t("kurs_mashq_qoshildi")
      );
      yukla();
    } catch (e2) {
      setRasmMashqXato(e2.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setRasmMashqYuklanmoqda(false);
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 10, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <label className="tugma ikkinchi" style={{ cursor: "pointer" }}>
          {rasmMashqYuklanmoqda ? t("yuklanmoqda") : t("kurs_rasmdan_mashq_qoshish")}
          <input
            type="file"
            accept="image/*"
            onChange={rasmdanMashqQoshish}
            disabled={rasmMashqYuklanmoqda}
            style={{ display: "none" }}
          />
        </label>
        {rasmMashqXato && <span className="xato-xabar">{rasmMashqXato}</span>}
        {rasmMashqXabar && <span className="izoh">✓ {rasmMashqXabar}</span>}
        {qaytaYuklashXato && <span className="xato-xabar">{qaytaYuklashXato}</span>}
      </div>
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
                </span>
                <input type="file" accept="image/*" onChange={(e) => rasmYukla(m.id, e)} style={{ maxWidth: 140 }} />
                {m.savollar.length > 0 && (
                  <button
                    className="tugma ikkinchi"
                    onClick={() => setJavobOchiqId((joriy) => (joriy === m.id ? null : m.id))}
                  >
                    {javobOchiqId === m.id ? t("yopish") : t("kurs_javoblar")}
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
                <button className="tugma ikkinchi" style={{ color: "#d33" }} onClick={() => ochir(m.id)}>
                  {t("ochirish")}
                </button>
              </div>
              {javobOchiqId === m.id && (
                <MashqJavoblariTahriri mashq={m} royxatniYangila={yukla} />
              )}
            </div>
          ))}
        </div>
      )}
      {royxat && royxat.length > 0 && (
        <div style={{ marginBottom: 10 }}>
          <label className="izoh" style={{ display: "block", marginBottom: 4 }}>
            {t("kurs_audio_zip_yuklash")}
          </label>
          <input type="file" accept=".zip" onChange={audioZipYukla} disabled={audioZipYuklanmoqda} />
          {audioZipXato && <span className="xato-xabar" style={{ marginLeft: 8 }}>{audioZipXato}</span>}
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
function MashqPaneli({ tugunId, talabaMi, jsonKiritishKorinadi = true }) {
  const { t } = useI18n();
  const [mashqlar, setMashqlar] = useState(null);
  const [xato, setXato] = useState("");

  useEffect(() => {
    if (!talabaMi) return;
    api(`/api/kurslar/${tugunId}/mashqlar/`)
      .then(setMashqlar)
      .catch((e) => setXato(e.data?.detail || t("xato_yuz_berdi")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tugunId, talabaMi]);

  if (!talabaMi) {
    return <AdminMashqBoshqaruv tugunId={tugunId} jsonKiritishKorinadi={jsonKiritishKorinadi} />;
  }

  if (xato) return <div className="xato-xabar">{xato}</div>;
  if (!mashqlar) return <div className="izoh">{t("yuklanmoqda")}</div>;
  if (mashqlar.length === 0) return <div className="izoh">{t("kurs_mashq_yoq")}</div>;

  // 2026-07-28: `bloklar` to'ldirilgan bo'lsa — sahifa qaytadan quriladi
  // (BlokMashqi), aks holda eski ko'rinish (sahifa rasmi + ustida
  // pozitsiyalangan input'lar). Ikki format yonma-yon yashaydi, chunki
  // eski usulda yuklangan kontent bor.
  return (
    <div>
      {mashqlar.map((m, idx) =>
        m.bloklar?.length ? (
          <BlokMashqi key={m.id} mashq={m} raqam={idx + 1} />
        ) : (
          <TalabaMashqi key={m.id} mashq={m} raqam={idx + 1} />
        ),
      )}
    </div>
  );
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
 * ishlab chiqildi) — Grammar reference + Wordlist BIRLASHTIRILGAN
 * (darslikda BIR sahifada birga keladi): grammatika qisqa xulosasi
 * (bo'lsa) + so'zlarni tarjima yozib mashq qilish + O'yinlar bo'limidagi
 * 4 ta so'z o'yini, FAQAT shu Unit so'zlari bilan. Grammatika testi bu
 * yerga kirmaydi — u gap-asosidagi savollarga ishlaydi, so'z juftlariga
 * bog'liq emas. */
function VocabularyKorinishi({ tugunId, matn }) {
  const { t } = useI18n();
  const [sozlar, setSozlar] = useState(null);
  const [oyin, setOyin] = useState(null);
  const [oyinKey, setOyinKey] = useState(0);

  useEffect(() => {
    api(`/api/kurslar/${tugunId}/sozlar/`).then(setSozlar).catch(() => setSozlar([]));
  }, [tugunId]);

  if (!sozlar) return <div className="izoh">{t("yuklanmoqda")}</div>;

  if (oyin) {
    // `key={oyinKey}` — "qayta o'ynash" bosilganda komponent qayta
    // MOUNT bo'lib, ichki holat (ball, joriy savol) toza boshlanadi;
    // Oyinlar.jsx'da bu API'dan yangi tasodifiy so'zlar olib erishilardi,
    // bu yerda so'zlar ro'yxati Unit bo'yicha FIKS, shuning uchun shart emas.
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
      {matn && (
        <div className="mashq-passage" style={{ whiteSpace: "pre-wrap", marginBottom: 12 }}>
          {matn}
        </div>
      )}
      {sozlar.length === 0 ? (
        <div className="izoh">{t("kurs_wordlist_yoq")}</div>
      ) : (
        <>
          <SozlarniYozishMashqi sozlar={sozlar} />
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
        </>
      )}
    </div>
  );
}

/** Admin/owner uchun — bitta Unit'ning IKKALA bo'limini (Mashqlar,
 * Vocabulary) BITTA harakatda ZIP orqali yuklash (2026-07-27, foydalanuvchi
 * talabi — "unit uchun bitta tugma bo'lsin"; 2026-07-28: qo'lda-JSON
 * kiritish variantI OLIB TASHLANDI, ZIP+AI yagona yo'l qoldi — u
 * ancha tezroq va endi haqiqiy ZIP bilan sinovdan o'tgan). */
// 2026-07-29 talabi: bir vaqtda bir nechta sahifani yuborish — har bir
// so'rov backend'da ATOMIK ravishda alohida (takrorlanmaydigan) sahifa
// oladi (courses/blok_views.py, KursBlokSahifaView), shuning uchun bu
// yerda parallel yuborish xavfsiz.
const PARALLEL_SAHIFA_SONI = 3;

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

  async function oxirginiOchir() {
    if (!window.confirm(t("kurs_oxirgi_unit_ochirish_tasdiq"))) return;
    setXato("");
    setOchirilmoqda(true);
    try {
      await api(`/api/kurslar/${darajaId}/daraja-unit-yaratish/`, { method: "DELETE" });
      royxatniYangila();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setOchirilmoqda(false);
    }
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
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

function AdminUnitKiritish({ unitId, royxatniYangila }) {
  const { t } = useI18n();
  const [zipXato, setZipXato] = useState("");
  const [zipXabar, setZipXabar] = useState("");
  const [raqamsizOgohlantirish, setRaqamsizOgohlantirish] = useState("");
  // 2026-07-29(3) talabi: "har mashq uchun alohida rasm, fayl nomidan
  // mashq raqamini bilib qo'yish" — admin ikkisidan birini tanlaydi.
  // 2026-07-30: "mashq bo'yicha" standart rejim qilindi (foydalanuvchi
  // talabi) — "sahifa bo'yicha" ham qoladi, admin xohlasa tanlaydi.
  const [zipRejim, setZipRejim] = useState("mashq");
  const [zipYuklanmoqda, setZipYuklanmoqda] = useState(false);
  const [progress, setProgress] = useState(null);
  // 2026-07-29 talabi: yuklash necha daqiqada ketayotganini ko'rsatish.
  const [otganSoniya, setOtganSoniya] = useState(0);
  // 2026-07-29(2) talabi: "to'xtatish tugmasi" — bosilganda joriy
  // "to'lqin" (band qilingan sahifalar) fonda tugashiga ruxsat beriladi
  // (natijalari baribir saqlanadi), lekin YANGI to'lqin boshlanmaydi va
  // qoplama darhol yopiladi — jarayon keyinroq "Davom ettirish" bilan
  // xuddi shu joydan davom etadi (ref, chunki holat o'zgarishi darhol,
  // qayta render kutmay kerak — async sikl ichida o'qiladi).
  const toxtatishRef = useRef(false);

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

  const [faolJarayon, setFaolJarayon] = useState(null); // {id, ishlangan_sahifa, jami_sahifa}

  // 2026-07-29 talabi: "yuklanmagan qismini qo'lda yuklash imkoni kerak".
  // Sahifa ochilganda (yoki Unit qayta ko'rsatilganda) shu kitob uchun
  // yarim qolgan (avtomatik qayta urinishlar ham tugab ketgan) jarayon
  // bor-yo'qligi tekshiriladi — bo'lsa "Davom ettirish" tugmasi chiqadi.
  useEffect(() => {
    api(`/api/kurslar/${unitId}/blok-jarayon-holati/`)
      .then((d) => setFaolJarayon(d.faol_jarayon))
      .catch(() => {});
  }, [unitId]);

  // 2026-07-30 talabi: "Davom ettirish" yonida "Bekor qilish" — FAQAT
  // tugallanmagan jarayonni (ZIP holatini) o'chiradi, mashqlarga ASLO
  // tegmaydi (bu "Tozalash"dan MUSTAQIL, alohida amal).
  const [bekorQilinmoqda, setBekorQilinmoqda] = useState(false);
  async function jarayonniBekorQil() {
    if (!faolJarayon || !window.confirm(t("kurs_blok_bekor_qilish_tasdiq"))) return;
    setBekorQilinmoqda(true);
    try {
      await api(`/api/kurslar/${unitId}/blok-jarayon-holati/`, { method: "DELETE" });
      setFaolJarayon(null);
    } catch {
      // e'tiborsiz qoldirilsa ham xavfsiz — "Davom ettirish" tugmasi
      // ekranda qolaveradi, admin xohlasa qayta urinishi mumkin.
    } finally {
      setBekorQilinmoqda(false);
    }
  }

  // Navbatdagi BITTA sahifani band qilib ishlaydi — xatoda qayta
  // urinadi (Render konteyneri qayta ishga tushishi mumkin, bir necha
  // soniya olishi mumkin). Bir nechta nusxasi PARALLEL chaqiriladi
  // (backend har biriga alohida sahifani atomik beradi).
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

  // Bitta jarayonning QOLGAN sahifalarini ishlaydi — yangi yuklashda ham
  // (0 dan), "Davom ettirish"da ham (saqlangan ishlangan_sahifadan)
  // ISHLATILADI, shuning uchun umumiy funksiyaga chiqarilgan.
  //
  // 2026-07-29: har "to'lqin"da PARALLEL_SAHIFA_SONI tagacha so'rov bir
  // vaqtda yuboriladi — backend navbatdagi bo'sh sahifani ATOMIK band
  // qilib beradi (courses/blok_views.py), shuning uchun bu yerda
  // sahifa indeksini o'zimiz hisoblashimiz shart emas.
  async function jarayonniBajar(jid, jamiSahifa, boshlangichIshlangan) {
    toxtatishRef.current = false;
    let yakun = null;
    let tugadi = false;
    let oxirgiIshlangan = boshlangichIshlangan;
    setProgress({ ishlangan: boshlangichIshlangan, jami: jamiSahifa, fayl: "" });
    while (!tugadi) {
      if (toxtatishRef.current) {
        // 2026-07-29(2): admin "To'xtatish" bosdi — joriy to'lqindagi
        // (band qilingan) sahifalar natijasi baribir saqlangan, faqat
        // YANGI to'lqin boshlanmaydi. Jarayon bazada saqlanib qoladi.
        setFaolJarayon({ id: jid, ishlangan_sahifa: oxirgiIshlangan, jami_sahifa: jamiSahifa });
        return { toxtatildi: true };
      }
      const vadalar = [];
      for (let k = 0; k < PARALLEL_SAHIFA_SONI; k += 1) vadalar.push(bittaSahifaniIshla(jid));
      // eslint-disable-next-line no-await-in-loop
      const natijalar = await Promise.allSettled(vadalar);

      const xatoli = natijalar.find((n) => n.status === "rejected");
      if (xatoli) {
        // 2026-07-29: avtomatik qayta urinishlar ham tugasa, jarayon
        // BAZADA saqlanib qoladi (yo'qolmaydi) — keyinroq "Davom
        // ettirish" bilan xuddi shu joydan davom etish mumkin.
        setFaolJarayon({ id: jid, ishlangan_sahifa: oxirgiIshlangan, jami_sahifa: jamiSahifa });
        throw xatoli.reason;
      }

      let ishBorEdi = false;
      for (const n of natijalar) {
        const d = n.value;
        if (d.band_qilinadigan_sahifa_qolmadi) continue; // bu "ishchi"ga ish qolmadi
        ishBorEdi = true;
        oxirgiIshlangan = d.ishlangan_sahifa;
        setProgress({ ishlangan: d.ishlangan_sahifa, jami: d.jami_sahifa, fayl: d.joriy_fayl });
        if (d.tugadimi) {
          yakun = d.yakun;
          tugadi = true;
        }
      }
      if (!ishBorEdi) tugadi = true; // ehtiyot chorasi — hech kim ish topmadi
    }
    return { toxtatildi: false, yakun };
  }

  function yakunXabariniQoy(yakun) {
    const qismlar = [
      `${yakun.yaratilgan_mashqlar} ${t("kurs_natija_mashq")}`,
      `${yakun.kesilgan_rasmlar} ${t("kurs_blok_rasm")}`,
    ];
    if (yakun.baholanadigan_savollar) {
      qismlar.push(`${yakun.baholanadigan_savollar} ${t("kurs_blok_savol")}`);
    }
    if (yakun.moslangan_audio) {
      qismlar.push(`${yakun.moslangan_audio} ${t("kurs_zip_audio")}`);
    }
    if (yakun.qoshilgan_sozlar) {
      qismlar.push(`${yakun.qoshilgan_sozlar} ${t("kurs_natija_soz")}`);
    }
    let xabarMatni = qismlar.join(", ");
    if (yakun.xato_sahifalar?.length) {
      xabarMatni += ` — ⚠ ${yakun.xato_sahifalar.length} ${t("kurs_zip_xato_sahifa")}: ${yakun.xato_sahifalar
        .map((x) => x.fayl.split("/").pop())
        .join(", ")}`;
    }
    if (yakun.ishlatilmagan_audio?.length) {
      xabarMatni += ` — ⚠ ${t("kurs_zip_moslanmagan_audio")}: ${yakun.ishlatilmagan_audio.join(", ")}`;
    }
    setZipXabar(xabarMatni);
  }

  // Blok formatida yuklash (2026-07-28) — ZIP bir marta yuboriladi,
  // keyin sahifalar BITTALAB qayta ishlanadi. Sabab: har sahifa AI'da
  // ~2 daqiqa, 7-10 sahifa esa gunicorn'ning 300s timeout'iga sig'maydi.
  // Foydalanuvchi uchun bu bitta amal bo'lib qoladi — progress ko'rinadi.
  async function blokZipYukla(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setZipXato("");
    setZipXabar("");
    setRaqamsizOgohlantirish("");
    setZipYuklanmoqda(true);
    setProgress(null);
    try {
      const fd = new FormData();
      fd.append("zip_fayl", fayl);
      fd.append("rejim", zipRejim);
      const boshlash = await apiForm(`/api/kurslar/${unitId}/blok-zip/`, {
        method: "POST",
        formData: fd,
      });
      if (boshlash.raqamsiz_fayllar?.length) {
        setRaqamsizOgohlantirish(
          `${t("kurs_blok_raqamsiz_fayllar")}: ${boshlash.raqamsiz_fayllar.join(", ")}`
        );
      }
      const natija = await jarayonniBajar(boshlash.jarayon_id, boshlash.jami_sahifa, 0);
      if (natija.toxtatildi) {
        setZipXabar(t("kurs_blok_toxtatildi"));
      } else {
        yakunXabariniQoy(natija.yakun);
        setFaolJarayon(null);
        royxatniYangila();
      }
    } catch (e2) {
      setZipXato(e2.data?.detail || t("xato_yuz_berdi"));
      // 2026-07-29(6): 409 — backend jarayonni "tiqilib qolgan" deb
      // aniqlab, o'zi o'chirib tashladi (qarang courses/blok_views.py) —
      // "Davom ettirish" tugmasi endi ma'nosiz, darhol yashiramiz.
      if (e2.status === 409) setFaolJarayon(null);
    } finally {
      setZipYuklanmoqda(false);
      setProgress(null);
    }
  }

  async function jarayonniDavomEttir() {
    if (!faolJarayon) return;
    setZipXato("");
    setZipXabar("");
    setZipYuklanmoqda(true);
    setProgress(null);
    try {
      const natija = await jarayonniBajar(
        faolJarayon.id, faolJarayon.jami_sahifa, faolJarayon.ishlangan_sahifa,
      );
      if (natija.toxtatildi) {
        setZipXabar(t("kurs_blok_toxtatildi"));
      } else {
        yakunXabariniQoy(natija.yakun);
        setFaolJarayon(null);
        royxatniYangila();
      }
    } catch (e2) {
      setZipXato(e2.data?.detail || t("xato_yuz_berdi"));
      // 2026-07-29(6): 409 — backend jarayonni "tiqilib qolgan" deb
      // aniqlab, o'zi o'chirib tashladi (qarang courses/blok_views.py) —
      // "Davom ettirish" tugmasi endi ma'nosiz, darhol yashiramiz.
      if (e2.status === 409) setFaolJarayon(null);
    } finally {
      setZipYuklanmoqda(false);
      setProgress(null);
    }
  }

  // 2026-07-28: "Unit materialini yuklash" ochish/yopish tugmasi OLIB
  // TASHLANDI (foydalanuvchi talabi) — fayl tanlash maydoni to'g'ridan-
  // to'g'ri turadi. Sabab: tugma ortiqcha bosish edi, ichida baribir
  // yagona amal (ZIP tanlash) bor.
  return (
    <div style={{ marginTop: 4, marginBottom: 6, maxWidth: 640 }} onClick={(e) => e.stopPropagation()}>
      <label className="izoh" style={{ display: "block", marginBottom: 4 }}>
        {t("kurs_zip_yuklash_izoh")}
      </label>
      <div style={{ display: "flex", gap: 14, marginBottom: 6 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13 }}>
          <input
            type="radio"
            name={`zip-rejim-${unitId}`}
            checked={zipRejim === "sahifa"}
            onChange={() => setZipRejim("sahifa")}
            disabled={zipYuklanmoqda}
          />
          {t("kurs_zip_rejim_sahifa")}
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13 }}>
          <input
            type="radio"
            name={`zip-rejim-${unitId}`}
            checked={zipRejim === "mashq"}
            onChange={() => setZipRejim("mashq")}
            disabled={zipYuklanmoqda}
          />
          {t("kurs_zip_rejim_mashq")}
        </label>
      </div>
      {zipRejim === "mashq" && (
        <p className="izoh" style={{ marginTop: 0, marginBottom: 6 }}>
          {t("kurs_zip_rejim_mashq_izoh")}
        </p>
      )}
      <input type="file" accept=".zip" onChange={blokZipYukla} disabled={zipYuklanmoqda} />
      {raqamsizOgohlantirish && (
        <div className="xato-xabar" style={{ marginTop: 4 }}>⚠ {raqamsizOgohlantirish}</div>
      )}
      {faolJarayon && !zipYuklanmoqda && (
        <div style={{ marginTop: 6, display: "flex", gap: 8 }}>
          <button className="tugma ikkinchi kichik" onClick={jarayonniDavomEttir}>
            {t("kurs_blok_davom_ettirish")} ({faolJarayon.ishlangan_sahifa}/{faolJarayon.jami_sahifa})
          </button>
          <button
            className="tugma ikkinchi kichik"
            style={{ color: "#d33" }}
            onClick={jarayonniBekorQil}
            disabled={bekorQilinmoqda}
          >
            {t("kurs_blok_bekor_qilish")}
          </button>
        </div>
      )}
      {zipYuklanmoqda && !progress && (
        <span className="izoh" style={{ marginLeft: 8 }}>{t("kurs_zip_ishlanmoqda")}</span>
      )}
      {progress && (
        <div style={{ marginTop: 6 }}>
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
      {zipXato && <div className="xato-xabar" style={{ marginTop: 4 }}>{zipXato}</div>}
      {zipXabar && <div className="izoh" style={{ marginTop: 4 }}>✓ {zipXabar}</div>}

      {/* 2026-07-29 talabi: "fayl yuklanib bo'lmagungacha saytda hech
          qanday amal bajarish mumkin bo'lmasin". Butun oynani qoplaydigan
          qatlam (position:fixed + yuqori z-index) — bosishlarni yutadi,
          shuning uchun ostidagi hech qanday tugma/havola ishlamaydi.
          `onClick={(e)=>e.stopPropagation()}` yuqorida bor, shuning uchun
          bu qatlam DOMning istalgan joyida bo'lsa ham to'g'ri ishlaydi. */}
      {zipYuklanmoqda && (
        <div className="blok-yuklash-qoplama">
          <div className="blok-yuklash-karta">
            <div className="blok-yuklash-spinner" aria-hidden="true" />
            <div style={{ fontWeight: 700 }}>{t("kurs_blok_yuklash_band")}</div>
            <div className="izoh">{t("kurs_blok_otgan_vaqt")}: {vaqtFormat(otganSoniya)}</div>
            {progress && (
              <div
                className="izoh blok-yuklash-fayl"
                title={progress.fayl || undefined}
              >
                {progress.ishlangan}/{progress.jami}
                {progress.fayl ? ` — ${progress.fayl}` : ""}
              </div>
            )}
            {/* 2026-07-29(2) talabi: to'xtatish tugmasi — joriy band
                qilingan sahifalar fonda tugaydi (natijasi saqlanadi),
                keyinroq "Davom ettirish" bilan xuddi shu joydan
                davom etish mumkin. */}
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
    <button
      className="tugma ikkinchi"
      style={{ color: "#d33" }}
      onClick={tozala}
      disabled={ochirilmoqda}
    >
      {t("kurs_unit_tozalash")}
    </button>
  );
}

/** Bitta tugun — akkordeon (agar children bo'lsa) yoki oxirgi qatlam
 * (fayl + mashqlar + tugallandimi belgisi + admin uchun boshqaruv).
 *
 * `ichkariUnitMi` (2026-07-27) — shu tugunning BEVOSITA ota-tuguni Unit
 * (`unit_darsi=True`) bo'lsa true. Shu bo'lsa, nomi bo'yicha ("Mashqlar" /
 * "Vocabulary") maxsus ko'rinish tanlanadi — boshqa (flat) bo'limlar
 * avvalgidek fayl+mashq ko'rinishida qoladi. */
function Tugun({ tugun, chuqurlik, adminMi, talabaMi, royxatniYangila, ichkariUnitMi, ochiqmi, onOchish }) {
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
  // tarjima qilingani uchun u kalit bo'la olmaydi. `ichkariUnitMi` endi
  // "ota-tugun KITOB (Student's Book/Workbook)mi" degani.
  const unitBolimi = ichkariUnitMi ? tugun.kalit : null;
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
        <div
          className="kurs-qator kurs-qator-oxirgi"
          style={{ paddingLeft: otstup, display: "block" }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: mashqOchiq ? 8 : 0 }}>
            <span>{tugun.ikonka}</span>
            <span style={{ fontWeight: 600 }}>{nomi}</span>
            <button className="tugma ikkinchi" onClick={() => setMashqOchiq((v) => !v)}>
              {mashqOchiq
                ? t("yopish")
                : `${t("kurs_ochish")}${tugun.sozlar_soni ? ` (${tugun.sozlar_soni} ${t("kurs_soz")})` : ""}`}
            </button>
          </div>
          {mashqOchiq && <VocabularyKorinishi tugunId={tugun.id} matn={tugun.matn} />}
        </div>
      );
    }

    if (unitBolimi === "mashqlar") {
      return (
        <div
          className="kurs-qator kurs-qator-oxirgi"
          style={{ paddingLeft: otstup, display: "block" }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: mashqOchiq ? 8 : 0 }}>
            <span>{tugun.ikonka}</span>
            <span style={{ fontWeight: 600 }}>{nomi}</span>
            <button className="tugma ikkinchi" onClick={() => setMashqOchiq((v) => !v)}>
              {mashqOchiq
                ? t("yopish")
                : `${t("kurs_ochish")}${tugun.mashqlar_soni ? ` (${tugun.mashqlar_soni})` : ""}`}
            </button>
          </div>
          {mashqOchiq && (
            <MashqPaneli tugunId={tugun.id} talabaMi={talabaMi} jsonKiritishKorinadi={false} />
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
          <div style={{ paddingLeft: otstup, marginTop: 6 }}>
            <MashqPaneli tugunId={tugun.id} talabaMi={talabaMi} />
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
          {/* Yuklash/tozalash tugmalari KITOB darajasida (2026-07-28
              tuzilma o'zgarishi: Unit > Student's Book/Workbook > bo'limlar).
              Avval ular Unit darajasida edi — endi shunday qoldirilsa,
              kontent HAR DOIM Student's Book'ga tushib, Workbook'ni
              to'ldirib bo'lmasdi. Sarlavha qatoridan tashqarida, aks
              holda bosilganda akkordeon ham ochilib/yopilib ketardi. */}
          {adminMi && kitobmi && (
            <div style={{ paddingLeft: otstup + 18, display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 6 }}>
              <AdminUnitKiritish unitId={tugun.id} royxatniYangila={royxatniYangila} />
              <UnitTozalashTugmasi unitId={tugun.id} royxatniYangila={royxatniYangila} />
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
              talabaMi={talabaMi}
              royxatniYangila={royxatniYangila}
              ichkariUnitMi={kitobmi}
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
          talabaMi={talabaMi}
          royxatniYangila={yukla}
          ichkariUnitMi={false}
          ochiqmi={ochiqIldizId === tugun.id}
          onOchish={() => setOchiqIldizId((joriy) => (joriy === tugun.id ? null : tugun.id))}
        />
      ))}
    </div>
  );
}
