import { useEffect, useRef, useState } from "react";
import { api, apiBlobUrl, apiForm } from "../api";
import { haqiqiyMatnniOl } from "../haqiqiyMatn";
import { useI18n } from "../i18n";
import { IMLO_OFF } from "../imlo";
import { standartVaqt } from "../imtihonVaqt";
import { useTestRejimi } from "../testRejimiContext";
import { PapkaliRoyxat, VaqtTugadiModal, holatKaliti, vaqtFormat } from "./ImtihonOtish";
import OzMavzum from "./OzMavzum";
import { Natija as SpeakingNatija } from "./Speaking";
import { Natija as WritingNatija } from "./Writing";

const TASK_NOMI = { task1: "Task 1", task2: "Task 2", part1: "Part 1", part2: "Part 2", part3: "Part 3" };

/** "IELTS testlari"dagi Writing/Speaking — R/L bilan bir xil manba
 * (`ImtihonTest`/`TestQismi`, admin/owner qo'shadi) va bir xil uslub:
 * taymer, ortga/tekshirish tasdiq dialoglari, beforeunload ogohlantirish.
 * Mavjud "Mashqlar" bo'limidagi (AI-import, hammaga ochiq) Writing/
 * Speaking'ga MUSTAQIL — 2026-07-21'da ataylab ajratildi. Bitta test —
 * Task1+Task2 (yoki Part1/2/3) BIRGA, haqiqiy IELTS sessiyasi kabi. */
export default function ImtihonYozGap({ bolim, manba = "admin", testId, mockYechimId, onYakunlandi }) {
  const { t } = useI18n();
  const [royxat, setRoyxat] = useState(null);
  const [test, setTest] = useState(null);
  const [rasmUrllar, setRasmUrllar] = useState({});
  const [faolQism, setFaolQism] = useState(0);
  const [javoblar, setJavoblar] = useState({});
  const [natijalar, setNatijalar] = useState(null);
  const [umumiyBand, setUmumiyBand] = useState(null);
  const [xato, setXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [soniya, setSoniya] = useState(0);
  const [teskariMi, setTeskariMi] = useState(false);
  const [rejim, setRejim] = useState("testlar");
  // Vaqt tugab, avtomatik tekshirilgach (Mock ichida) bloklovchi
  // "Keyingisi" oynasini ko'rsatish uchun (2026-08-15).
  const [vaqtSababliYakun, setVaqtSababliYakun] = useState(false);
  const boshlanishVaqtiRef = useRef(null);
  const avtoYakunlashRef = useRef(false);
  const keyingigaOtildiRef = useRef(false);

  // 2026-07-30 talabi: Speaking uchun mikrofon — yozib olingan ovoz
  // FAQAT transkripsiya qilinadi (baholanmaydi!) va natija oddiy matn
  // maydoniga qo'yiladi (talaba xohlasa tahrirlaydi) — shundan keyin
  // MAVJUD "Tekshirish" oqimi (barcha qismlarni birga baholaydigan
  // `/yozgap-tekshirish/`) o'ZGARISHSIZ ishlaydi.
  const [yozilmoqda, setYozilmoqda] = useState(false);
  const [transkripsiyaQilinmoqda, setTranskripsiyaQilinmoqda] = useState(false);
  const [mikrofonXato, setMikrofonXato] = useState("");
  const mediaRecorderRef = useRef(null);
  const bolaklarRef = useRef([]);

  useEffect(() => {
    setTest(null);
    setNatijalar(null);
    setRoyxat(null);
    if (testId) {
      testniOch(testId);
      return;
    }
    api(`/api/imtihon/testlar/?bolim=${bolim}&manba=${manba}`).then(setRoyxat).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bolim, testId, manba]);

  useEffect(() => {
    if (!test || natijalar) return;
    const idT = setInterval(() => setSoniya((s) => s + 1), 1000);
    return () => clearInterval(idT);
  }, [test, natijalar]);

  useEffect(() => {
    function chiqishdanOldin(e) {
      if (!test || natijalar) return;
      e.preventDefault();
      e.returnValue = "";
    }
    window.addEventListener("beforeunload", chiqishdanOldin);
    return () => window.removeEventListener("beforeunload", chiqishdanOldin);
  }, [test, natijalar]);

  // 2026-07-30 talabi: test yechilayotganda navigatsiya bloklansin.
  // `onYakunlandi` bo'lsa — Mock ichida, holatni `ImtihonMock.jsx` o'zi
  // boshqaradi (bo'lim almashganda qisqa "faolsiz" lahza bo'lmasin uchun).
  const { setTestFaol } = useTestRejimi();
  useEffect(() => {
    if (onYakunlandi) return undefined;
    setTestFaol(!!test && !natijalar);
    return () => setTestFaol(false);
  }, [test, natijalar, onYakunlandi, setTestFaol]);

  async function testniOch(id) {
    const t2 = await api(`/api/imtihon/testlar/${id}/`);
    setTest(t2);
    setNatijalar(null);
    setUmumiyBand(null);
    setXato("");
    setTeskariMi(false);
    setFaolQism(0);
    setVaqtSababliYakun(false);
    avtoYakunlashRef.current = false;
    keyingigaOtildiRef.current = false;

    // F5'da (yoki internet uzilib qayta ulanganda) holatni tiklash —
    // javoblar (qismId bo'yicha) va taymerning boshlanish vaqti
    // sessionStorage'da saqlangan bo'lsa, o'shandan davom etamiz
    // (2026-08-15). Natijalar (tekshirilgan qismlar) ATAYLAB
    // tiklanmaydi — tekshirish serverda paketdan sarflanadi, F5'dan
    // keyin qayta tekshirtirish xatoga olib kelmasligi uchun talaba
    // shu qismni qaytadan "Tekshirish"ga bosishi kerak.
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
      // sessionStorage buzilgan bo'lsa — jim o'tkazib yuboramiz.
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
      // to'lgan bo'lsa — kritik emas.
    }

    const rasmlar = {};
    for (const qism of t2.qismlar) {
      if (qism.rasm_url) {
        rasmlar[qism.id] = await apiBlobUrl(qism.rasm_url).catch(() => null);
      }
    }
    setRasmUrllar(rasmlar);
  }

  function javobniQoy(qismId, qiymat) {
    setJavoblar((prev) => ({ ...prev, [qismId]: qiymat }));
  }

  // Har javob o'zgarganda sessionStorage'dagi holatni yangilaymiz (F5'da
  // tiklash uchun) — taymer boshlanish vaqti o'zgarmaydi.
  useEffect(() => {
    if (!test || boshlanishVaqtiRef.current == null) return;
    const kalit = holatKaliti(bolim, test.id, mockYechimId);
    try {
      sessionStorage.setItem(
        kalit,
        JSON.stringify({ testId: test.id, boshlanishVaqti: boshlanishVaqtiRef.current, javoblar })
      );
    } catch {
      // kritik emas.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [javoblar, test]);

  function saqlanganHolatniTozala() {
    if (!test) return;
    try {
      sessionStorage.removeItem(holatKaliti(bolim, test.id, mockYechimId));
    } catch {
      // kritik emas.
    }
  }

  async function yozishBoshla() {
    setMikrofonXato("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      bolaklarRef.current = [];
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) bolaklarRef.current.push(e.data);
      };
      mr.onstop = async () => {
        const blob = new Blob(bolaklarRef.current, { type: mr.mimeType || "audio/webm" });
        stream.getTracks().forEach((tr) => tr.stop());
        setTranskripsiyaQilinmoqda(true);
        try {
          const fd = new FormData();
          fd.append("audio", blob, "yozuv.webm");
          const res = await apiForm("/api/speaking/transkripsiya/", { method: "POST", formData: fd });
          const qismId = test.qismlar[faolQism].id;
          javobniQoy(qismId, ((javoblar[qismId] || "") + " " + res.transkript).trim());
        } catch (e) {
          setMikrofonXato(e.data?.detail || t("xato_yuz_berdi"));
        } finally {
          setTranskripsiyaQilinmoqda(false);
        }
      };
      mediaRecorderRef.current = mr;
      mr.start();
      setYozilmoqda(true);
    } catch {
      setMikrofonXato(t("mikrofon_ruxsat_yoq"));
    }
  }

  function yozishToxtat() {
    mediaRecorderRef.current?.stop();
    setYozilmoqda(false);
  }

  function ortgaQaytish() {
    if (!natijalar && !window.confirm(t("imtihon_ortga_tasdiq"))) return;
    // Foydalanuvchi ATAYLAB ortga qaytdi — saqlangan F5-holati ham
    // tozalanadi (2026-08-15).
    saqlanganHolatniTozala();
    setTest(null);
  }

  // 2026-07-30 (Speaking), 2026-08-02 (Writing ham) talabi: har qism
  // (Task1/Task2 yoki Part1/2/3) ALOHIDA tekshiriladi, hammasi birga
  // emas. Speaking'da 20-so'z sharti YO'Q (faqat bo'sh bo'lmasligi
  // kifoya), Writing'da backend 20 so'zdan kam bo'lsa xato qaytaradi
  // (`ImtihonYozGapTekshirishView`). Hammasi tekshirilgach — Mock bo'lsa
  // umumiy bandni `mock_yakunlovchi_bandlar` orqali yakunlaymiz, aks
  // holda mahalliy o'rtachani ko'rsatamiz.
  // 2026-08-15: AI'ga so'rov yuborib, natijani `natijalar`ga qo'shadi —
  // yangilangan (funksional) ro'yxatni qaytaradi. Yakunlash (band hisoblash,
  // mock finalize, saqlangan holatni tozalash) BU YERDA emas — chaqiruvchi
  // (`qismniTekshir` yoki avto-yakunlash effekti) barcha qismlar
  // hisoblanganini o'zi tekshirib, `yakunlashniBajar`ni chaqiradi. Bu
  // ajratish SHART: vaqt tugaganda oxirgi qism BO'SH bo'lishi mumkin (AI'ga
  // yuborilmaydi) — shu holatda ham yakunlash ishga tushishi kerak, lekin
  // bu funksiya orqali emas (pastga qarang).
  async function _apiOrqaliTekshir(qism) {
    const matn = (javoblar[qism.id] || "").trim();
    const res = await api(`/api/imtihon/testlar/${test.id}/yozgap-tekshirish/`, {
      method: "POST",
      body: { javoblar: { [qism.id]: matn } },
    });
    let yangiNatijalar;
    setNatijalar((prev) => {
      yangiNatijalar = [...(prev || []), ...res.natijalar];
      return yangiNatijalar;
    });
    return yangiNatijalar;
  }

  async function yakunlashniBajar(hammaNatijalar) {
    const bandlar = hammaNatijalar
      .map((n) => n.natija?.overall_band_no_pronunciation)
      .filter((b) => b != null);
    if (mockYechimId) {
      const fin = await api(`/api/imtihon/testlar/${test.id}/yozgap-tekshirish/`, {
        method: "POST",
        body: { mock_yakunlovchi_bandlar: bandlar, mock_yechim_id: mockYechimId },
      });
      setUmumiyBand(fin.umumiy_band);
    } else {
      setUmumiyBand(bandlar.length ? Math.round((bandlar.reduce((a, b) => a + b, 0) / bandlar.length) * 2) / 2 : null);
    }
    // Barcha qismlar tekshirilgach — test muvaffaqiyatli yakunlandi,
    // saqlangan F5-holati endi kerak emas (2026-08-15).
    saqlanganHolatniTozala();
  }

  async function qismniTekshir(qism) {
    setXato("");
    const matn = (javoblar[qism.id] || "").trim();
    if (!matn) {
      setXato(`"${qism.sarlavha || TASK_NOMI[qism.tur]}" — ${t("matn_kiritilmagan")}`);
      return;
    }
    setYuklanmoqda(true);
    try {
      const yangiNatijalar = await _apiOrqaliTekshir(qism);
      if (yangiNatijalar.length === test.qismlar.length) {
        await yakunlashniBajar(yangiNatijalar);
      }
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  // Vaqt tugaganda (real IELTS shartlariga mos) majburiy yakunlash
  // (2026-08-15). Umumiy vaqt — barcha qismlar (Task1+Task2 yoki
  // Part1/2/3) uchun standart vaqtlar YIG'INDISI, `ImtihonOtish.jsx`dagi
  // bilan bir xil ABSOLYUT boshlanish vaqti mantig'i.
  const jamiVaqt = test ? test.qismlar.reduce((s, q) => s + standartVaqt(bolim, q.tur), 0) : null;
  const barchaTekshirildi = !!(test && natijalar && natijalar.length === test.qismlar.length);
  const vaqtTugadi = !!test && !barchaTekshirildi && jamiVaqt != null && soniya >= jamiVaqt;

  useEffect(() => {
    if (!vaqtTugadi || avtoYakunlashRef.current || yuklanmoqda) return;
    avtoYakunlashRef.current = true;
    setVaqtSababliYakun(true);
    // Hali tekshirilmagan qismlarni ketma-ket ko'rib chiqamiz (parallel
    // emas, aks holda bitta paketdan ikki so'rov bir vaqtda sarflanib,
    // natijalar chalkashishi mumkin). Matni BO'SH qism (talaba hech narsa
    // yozmagan/aytmagan) uchun backend bo'sh javobni qabul qilmaydi —
    // shuning uchun uni AI'ga umuman yubormasdan, 0 band bilan MAHALLIY
    // yakunlaymiz (2026-08-15 tuzatish: avval bunday qism butunlay
    // o'tkazib yuborilardi, `barchaTekshirildi` HECH QACHON true
    // bo'lmasdi, "Keyingisi" oynasi chiqmasdi — Mock o'sha joyda
    // "osilib" qolardi).
    (async () => {
      let jamiNatijalar = natijalar || [];
      for (const q of test.qismlar) {
        if (jamiNatijalar.some((n) => n.qism_id === q.id)) continue;
        if (!(javoblar[q.id] || "").trim()) {
          const boshNatija = {
            qism_id: q.id,
            tur: q.tur,
            sarlavha: q.sarlavha,
            natija: {
              overall_band: 0,
              overall_band_no_pronunciation: 0,
              vaqt_tugagani_sababli_bosh: true,
            },
          };
          jamiNatijalar = [...jamiNatijalar, boshNatija];
          setNatijalar(jamiNatijalar);
          continue;
        }
        try {
          // eslint-disable-next-line no-await-in-loop
          jamiNatijalar = await _apiOrqaliTekshir(q);
        } catch {
          // AI xatosida ham to'xtab qolmasin — qism tekshirilmagan
          // holda qoladi, lekin sikl davom etadi (boshqa qismlar
          // yakunlansin, foydalanuvchi keyin "Qayta urinish" bilan
          // shu qismni alohida tekshira oladi).
        }
      }
      if (jamiNatijalar.length === test.qismlar.length) {
        await yakunlashniBajar(jamiNatijalar);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vaqtTugadi, yuklanmoqda]);

  const NatijaKomponenti = bolim === "writing" ? WritingNatija : SpeakingNatija;

  if (test) {
    const korsatilganVaqt = teskariMi ? Math.max(0, jamiVaqt - soniya) : soniya;
    const qism = test.qismlar[faolQism];
    const sozSoni = (javoblar[qism.id] || "").trim()
      ? javoblar[qism.id].trim().split(/\s+/).length
      : 0;
    // Speaking — har part alohida tekshiriladi, shuning uchun natija ham
    // qism bo'yicha tekshiriladi (Writing'da hammasi birga tekshirilgani
    // uchun bari bir vaqtda paydo bo'ladi, xatti-harakat o'zgarmaydi).
    const qismNatija = natijalar?.find((n) => n.qism_id === qism.id);
    // Vaqt tugab, hali barchasi tekshirilmagan (avtomatik tekshirish
    // ketmoqda) oraliqda — matn kiritish/mikrofon bloklanadi (2026-08-15).
    const bloklanganOraliqda = vaqtTugadi && !barchaTekshirildi;

    return (
      <div>
        <div className="imtihon-asboblar">
          <button className="tugma ikkinchi" onClick={ortgaQaytish}>
            {t("ortga")}
          </button>
          <span
            className="imtihon-taymer"
            title={t("imtihon_taymer_almashtir")}
            onClick={() => setTeskariMi((v) => !v)}
          >
            ⏱ {vaqtFormat(korsatilganVaqt)}
          </span>
        </div>

        <h3 style={{ margin: "10px 0" }}>{test.name}</h3>

        <div className="tab-guruh" style={{ marginBottom: 12 }}>
          {test.qismlar.map((q, i) => (
            <button key={q.id} className={faolQism === i ? "aktiv" : ""} onClick={() => setFaolQism(i)}>
              {q.sarlavha || TASK_NOMI[q.tur] || `#${q.tartib}`}
              {natijalar?.some((n) => n.qism_id === q.id) && " ✓"}
            </button>
          ))}
        </div>

        {barchaTekshirildi && umumiyBand != null && (
          <div className="karta" style={{ marginBottom: 14, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <strong>{t("band_ball")}: {umumiyBand}</strong>
            {/* Vaqt tugab avtomatik yakunlangan bo'lsa — o'rniga pastdagi
                bloklovchi "Keyingisi" (30s) oynasi ko'rsatiladi. */}
            {onYakunlandi && !vaqtSababliYakun && (
              <button className="tugma katta" onClick={() => onYakunlandi({ umumiyBand })}>
                {t("mock_keyingi_bolim")}
              </button>
            )}
          </div>
        )}

        <div
          className={bloklanganOraliqda ? "imtihon-vaqt-tugadi-overlay" : ""}
        >
          {bloklanganOraliqda && (
            <div className="izoh" style={{ marginBottom: 8, fontWeight: 700 }}>
              ⏱ {t("vaqt_tugadi_yuborilmoqda")}
            </div>
          )}
          <div className="karta" style={{ marginBottom: 14 }}>
            <h4>{qism.sarlavha || TASK_NOMI[qism.tur]}</h4>
            <div className="mashq-passage">{haqiqiyMatnniOl(qism.matn)}</div>
            {rasmUrllar[qism.id] && (
              <img src={rasmUrllar[qism.id]} alt="" style={{ maxWidth: "100%", marginTop: 10 }} />
            )}
          </div>

          {qismNatija ? (
            <>
              {/* Foydalanuvchi talabi (2026-08-02): yozilgan/aytilgan matn
                  natija chiqqandan keyin ham ko'rinib tursin — avval
                  butunlay yashirilardi, talaba o'zi nima yozgani/deganini
                  unutib qolardi. */}
              {javoblar[qism.id] && (
                <div className="karta" style={{ marginBottom: 14 }}>
                  <h4>{t("sizning_javobingiz")}</h4>
                  <p className="izoh" style={{ margin: 0, whiteSpace: "pre-wrap" }}>
                    {javoblar[qism.id]}
                  </p>
                </div>
              )}
              <NatijaKomponenti natija={qismNatija.natija} />
            </>
          ) : (
            <div className="karta">
              {bolim === "speaking" && (
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
                  {!yozilmoqda ? (
                    <button
                      type="button"
                      className="tugma ikkinchi"
                      onClick={yozishBoshla}
                      disabled={transkripsiyaQilinmoqda || bloklanganOraliqda}
                    >
                      🎙 {t("yozib_olish")}
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="tugma ikkinchi"
                      style={{ background: "#d33", color: "#fff" }}
                      onClick={yozishToxtat}
                      disabled={bloklanganOraliqda}
                    >
                      ⏹ {t("toxtatish")}
                    </button>
                  )}
                  {transkripsiyaQilinmoqda && (
                    <span className="izoh">{t("tekshirilmoqda")}</span>
                  )}
                  {mikrofonXato && <span className="xato-xabar">{mikrofonXato}</span>}
                </div>
              )}
              <textarea
                {...IMLO_OFF}
                value={javoblar[qism.id] || ""}
                onChange={(e) => javobniQoy(qism.id, e.target.value)}
                placeholder={bolim === "writing" ? t("insho_placeholder") : t("javob_placeholder")}
                disabled={bloklanganOraliqda}
              />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
                <span className="izoh">
                  {sozSoni} {t("soz")}
                </span>
                <button
                  className="tugma katta"
                  onClick={() => qismniTekshir(qism)}
                  disabled={yuklanmoqda || bloklanganOraliqda}
                >
                  {yuklanmoqda ? t("tekshirilmoqda") : t("tekshirish")}
                </button>
              </div>
              {xato && <div className="xato-xabar" style={{ marginTop: 10 }}>{xato}</div>}
            </div>
          )}
        </div>
        {/* Vaqt tugab (Mock ichida) avtomatik yakunlangach — imtihon
            oynasi bloklanadi, "Keyingisi" (30s) oynasi ochiladi
            (2026-08-15). Qo'lda yakunlashda bu oyna chiqmaydi. */}
        {barchaTekshirildi && onYakunlandi && vaqtSababliYakun && (
          <VaqtTugadiModal
            t={t}
            onKeyingisi={() => {
              if (keyingigaOtildiRef.current) return;
              keyingigaOtildiRef.current = true;
              onYakunlandi({ umumiyBand });
            }}
          />
        )}
      </div>
    );
  }

  // 2026-07-27: test ro'yxati yonida "O'z mavzuyim" tabi — talaba tayyor
  // testlardan tashqari o'zi kiritgan mavzuni ham tekshirtira oladi.
  // Mock oqimida (testId berilganda) bu yerga umuman kelinmaydi — test
  // to'g'ridan-to'g'ri ochiladi, ya'ni mock jarayoniga ta'sir qilmaydi.
  return (
    <>
      <div className="tab-guruh">
        <button className={rejim === "testlar" ? "aktiv" : ""} onClick={() => setRejim("testlar")}>
          {t("testlar")}
        </button>
        <button className={rejim === "oz" ? "aktiv" : ""} onClick={() => setRejim("oz")}>
          {t("oz_mavzum")}
        </button>
      </div>

      <div style={{ marginTop: 16 }}>
        {rejim === "oz" ? (
          <OzMavzum bolim={bolim} NatijaKomponenti={NatijaKomponenti} />
        ) : (
          <div className="karta">
            {royxat === null && <div className="yuklanmoqda">{t("yuklanmoqda")}</div>}
            {royxat && royxat.length === 0 && (
              <span className="izoh">{t("imtihon_royxati_boshi")}</span>
            )}
            {royxat && <PapkaliRoyxat royxat={royxat} ochish={testniOch} t={t} />}
          </div>
        )}
      </div>
    </>
  );
}
