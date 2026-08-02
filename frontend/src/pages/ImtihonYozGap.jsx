import { useEffect, useRef, useState } from "react";
import { api, apiBlobUrl, apiForm } from "../api";
import { haqiqiyMatnniOl } from "../haqiqiyMatn";
import { useI18n } from "../i18n";
import { IMLO_OFF } from "../imlo";
import { standartVaqt } from "../imtihonVaqt";
import { useTestRejimi } from "../testRejimiContext";
import { PapkaliRoyxat, vaqtFormat } from "./ImtihonOtish";
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
    setJavoblar({});
    setNatijalar(null);
    setUmumiyBand(null);
    setXato("");
    setSoniya(0);
    setTeskariMi(false);
    setFaolQism(0);

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
    setTest(null);
  }

  // 2026-07-30 (Speaking), 2026-08-02 (Writing ham) talabi: har qism
  // (Task1/Task2 yoki Part1/2/3) ALOHIDA tekshiriladi, hammasi birga
  // emas. Speaking'da 20-so'z sharti YO'Q (faqat bo'sh bo'lmasligi
  // kifoya), Writing'da backend 20 so'zdan kam bo'lsa xato qaytaradi
  // (`ImtihonYozGapTekshirishView`). Har qism tekshirilganda paketdan
  // alohida sarflanadi. Hammasi tekshirilgach — Mock bo'lsa umumiy
  // bandni `mock_yakunlovchi_bandlar` orqali yakunlaymiz, aks holda
  // mahalliy o'rtachani ko'rsatamiz.
  async function qismniTekshir(qism) {
    setXato("");
    const matn = (javoblar[qism.id] || "").trim();
    if (!matn) {
      setXato(`"${qism.sarlavha || TASK_NOMI[qism.tur]}" — ${t("matn_kiritilmagan")}`);
      return;
    }
    setYuklanmoqda(true);
    try {
      const res = await api(`/api/imtihon/testlar/${test.id}/yozgap-tekshirish/`, {
        method: "POST",
        body: { javoblar: { [qism.id]: matn } },
      });
      const yangiNatijalar = [...(natijalar || []), ...res.natijalar];
      setNatijalar(yangiNatijalar);
      if (yangiNatijalar.length === test.qismlar.length) {
        const bandlar = yangiNatijalar
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
      }
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  const NatijaKomponenti = bolim === "writing" ? WritingNatija : SpeakingNatija;

  if (test) {
    const jamiVaqt = test.qismlar.reduce((s, q) => s + standartVaqt(bolim, q.tur), 0);
    const korsatilganVaqt = teskariMi ? Math.max(0, jamiVaqt - soniya) : soniya;
    const qism = test.qismlar[faolQism];
    const sozSoni = (javoblar[qism.id] || "").trim()
      ? javoblar[qism.id].trim().split(/\s+/).length
      : 0;
    // Speaking — har part alohida tekshiriladi, shuning uchun natija ham
    // qism bo'yicha tekshiriladi (Writing'da hammasi birga tekshirilgani
    // uchun bari bir vaqtda paydo bo'ladi, xatti-harakat o'zgarmaydi).
    const qismNatija = natijalar?.find((n) => n.qism_id === qism.id);
    const barchaTekshirildi = natijalar && natijalar.length === test.qismlar.length;

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
            {onYakunlandi && (
              <button className="tugma katta" onClick={() => onYakunlandi({ umumiyBand })}>
                {t("mock_keyingi_bolim")}
              </button>
            )}
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
                    disabled={transkripsiyaQilinmoqda}
                  >
                    🎙 {t("yozib_olish")}
                  </button>
                ) : (
                  <button
                    type="button"
                    className="tugma ikkinchi"
                    style={{ background: "#d33", color: "#fff" }}
                    onClick={yozishToxtat}
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
            />
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
              <span className="izoh">
                {sozSoni} {t("soz")}
              </span>
              <button
                className="tugma katta"
                onClick={() => qismniTekshir(qism)}
                disabled={yuklanmoqda}
              >
                {yuklanmoqda ? t("tekshirilmoqda") : t("tekshirish")}
              </button>
            </div>
            {xato && <div className="xato-xabar" style={{ marginTop: 10 }}>{xato}</div>}
          </div>
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
