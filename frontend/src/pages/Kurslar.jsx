import { useEffect, useState } from "react";
import { api, apiBlobUrl, apiForm } from "../api";
import { AUDIO_HIMOYA } from "../audio";
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
                {audioUrl && <audio {...AUDIO_HIMOYA} controls src={audioUrl} style={{ width: "100%" }} />}
                {audioUrllar.map((a) => (
                  <div key={a.id} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    {a.raqam && <span className="izoh" style={{ minWidth: 40 }}>{a.raqam}</span>}
                    <audio {...AUDIO_HIMOYA} controls src={a.url} style={{ width: "100%" }} />
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
function AdminMashqBoshqaruv({ tugunId, jsonKiritishKorinadi = true }) {
  const { t } = useI18n();
  const [royxat, setRoyxat] = useState(null);
  const [jsonMatn, setJsonMatn] = useState('[\n  {"matn": "", "savollar": [{"savol": "...", "togri": "..."}]}\n]');
  const [xato, setXato] = useState("");
  const [saqlanmoqda, setSaqlanmoqda] = useState(false);
  const [audioZipXato, setAudioZipXato] = useState("");
  const [audioZipYuklanmoqda, setAudioZipYuklanmoqda] = useState(false);
  const [promtKorinadi, setPromtKorinadi] = useState(false);
  const [nusxalandi, setNusxalandi] = useState(false);

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

  return (
    <div>
      {royxat && royxat.length > 0 && (
        <div style={{ display: "grid", gap: 6, marginBottom: 10 }}>
          {royxat.map((m) => (
            <div key={m.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="izoh">
                #{m.tartib} — {m.matn ? m.matn.slice(0, 40) : ""} ({m.savollar.length} {t("kurs_savol")})
                {m.rasm_url ? " 🖼️" : ""}
                {m.audio_url ? " 🔊" : ""}
                {m.audiolar?.length ? ` 🔊×${m.audiolar.length}` : ""}
              </span>
              <input type="file" accept="image/*" onChange={(e) => rasmYukla(m.id, e)} style={{ maxWidth: 140 }} />
              <button className="tugma ikkinchi" style={{ color: "#d33" }} onClick={() => ochir(m.id)}>
                {t("ochirish")}
              </button>
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
function AdminUnitKiritish({ unitId, royxatniYangila }) {
  const { t } = useI18n();
  const [zipXato, setZipXato] = useState("");
  const [zipXabar, setZipXabar] = useState("");
  const [zipYuklanmoqda, setZipYuklanmoqda] = useState(false);
  const [progress, setProgress] = useState(null);

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
    setZipYuklanmoqda(true);
    setProgress(null);
    try {
      const fd = new FormData();
      fd.append("zip_fayl", fayl);
      const boshlash = await apiForm(`/api/kurslar/${unitId}/blok-zip/`, {
        method: "POST",
        formData: fd,
      });
      const jid = boshlash.jarayon_id;
      setProgress({ ishlangan: 0, jami: boshlash.jami_sahifa, fayl: "" });

      // 2026-07-28: har sahifa AI'da ~2 daqiqa ketadi — shu vaqtda server
      // (Render, ayniqsa bepul tarifda) vaqtincha uzilib qolishi mumkin
      // (haqiqiy holatda kuzatilgan: gunicorn logida Python xatosi yo'q,
      // shunchaki servis qayta ishga tushgan). Jarayon o'zi ZIP+progressni
      // bazada/R2'da saqlagani uchun, uzilgan sahifani QAYTA SO'RASH
      // xavfsiz — shuning uchun har sahifa uchun bir necha marta uriniladi.
      const SAHIFA_URINISHLAR = 3;
      let yakun = null;
      for (let i = 0; i < boshlash.jami_sahifa; i += 1) {
        let d = null;
        let oxirgiXato = null;
        for (let urinish = 0; urinish < SAHIFA_URINISHLAR; urinish += 1) {
          try {
            // eslint-disable-next-line no-await-in-loop
            d = await api(`/api/kurslar/blok-jarayon/${jid}/sahifa/`, { method: "POST" });
            oxirgiXato = null;
            break;
          } catch (sahifaXato) {
            oxirgiXato = sahifaXato;
            if (urinish < SAHIFA_URINISHLAR - 1) {
              setProgress({
                ishlangan: i,
                jami: boshlash.jami_sahifa,
                fayl: t("kurs_blok_qayta_urinish"),
              });
              // Konteyner qayta ishga tushishi (Render'da kuzatilgan holat)
              // bir necha soniya olishi mumkin — kutish vaqti ortib boradi
              // (5s, 10s), darhol qayta urinish befoyda bo'lmasin.
              // eslint-disable-next-line no-await-in-loop
              await new Promise((r) => { setTimeout(r, 5000 * (urinish + 1)); });
            }
          }
        }
        if (oxirgiXato) throw oxirgiXato;
        setProgress({ ishlangan: d.ishlangan_sahifa, jami: d.jami_sahifa, fayl: d.joriy_fayl });
        if (d.tugadimi) {
          yakun = d.yakun;
          break;
        }
      }

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
      royxatniYangila();
    } catch (e2) {
      setZipXato(e2.data?.detail || t("xato_yuz_berdi"));
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
      <input type="file" accept=".zip" onChange={blokZipYukla} disabled={zipYuklanmoqda} />
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
