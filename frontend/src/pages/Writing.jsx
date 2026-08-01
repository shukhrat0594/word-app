import { useEffect, useState } from "react";
import { api } from "../api";
import NamunaMavzular, { svgAjrat, TURLAR } from "../components/NamunaMavzular";
import { haqiqiyMatnniOl } from "../haqiqiyMatn";
import { useI18n } from "../i18n";
import { IMLO_OFF } from "../imlo";
import { svgniPngGaAylantir } from "../svgRasm";
import { xatoniAjrat } from "../xatoUtils";
import OzMavzum from "./OzMavzum";

const TASK_NOMI = { task1: "Task 1", task2: "Task 2" };

// 2026-07-26: avval uchta tugma bor edi (Gemma / Flash Lite / "ikkalasida
// ham tekshirish") — ular modellarni solishtirish uchun vaqtincha qo'yilgan.
// Gemma olib tashlangach solishtiradigan narsa qolmadi: bitta model, bitta
// tugma. Kalit backendga hamon yuboriladi (`gemini_provider_ol`).
const MODEL_KALITI = "flash_lite";

// Speaking.jsx'dagi bilan bir xil (2026-08-01): matnli maydonlar endi
// {en,uz,ru} obyekti bo'lib keladi — ikkisini ham qo'llab-quvvatlaydi.
function T(qiymat, til) {
  if (qiymat == null) return "";
  if (typeof qiymat === "object") return qiymat[til] ?? qiymat.en ?? "";
  return qiymat;
}

const TIL_TUGMALAR = [
  ["en", "EN"],
  ["uz", "UZ"],
  ["ru", "RU"],
];

export function Natija({ natija }) {
  const { t } = useI18n();
  const [til, setTil] = useState("en");
  const mezonlar = [
    ["task_achievement", t("task_achievement")],
    ["coherence_cohesion", t("coherence_cohesion")],
    ["lexical_resource", t("lexical_resource")],
    ["grammatical_range", t("grammatical_range")],
  ];
  const taskNomi = TASK_NOMI[natija.task_type] || natija.task_type || "";
  const koTillik = Object.values(natija.analysis || {}).some(
    (v) => v && typeof v === "object",
  );

  return (
    <>
      {koTillik && (
        <div className="til-guruh" style={{ marginBottom: 10, width: "fit-content" }}>
          {TIL_TUGMALAR.map(([kod, nomi]) => (
            <button
              key={kod}
              type="button"
              className={til === kod ? "aktiv" : ""}
              onClick={() => setTil(kod)}
            >
              {nomi}
            </button>
          ))}
        </div>
      )}
      <div className="umumiy-band">
        <span className="u-ball">{natija.overall_band ?? "—"}</span>
        <div>
          <div style={{ fontWeight: 700 }}>
            Overall Band{taskNomi ? ` — ${taskNomi}` : ""}
          </div>
          <div className="u-izoh">
            {natija.word_count} {t("soz")}
          </div>
        </div>
      </div>

      <div className="mezon-qator">
        {mezonlar.map(([kalit, nomi]) => (
          <div className="mezon" key={kalit}>
            <div className="m-nom">{nomi}</div>
            <div className="m-ball">{natija[kalit]?.score ?? "—"}</div>
          </div>
        ))}
      </div>

      <div className="ikki-ustun">
        <div className="karta">
          <h3>
            {t("xatolar")} ({natija.errors?.length || 0})
          </h3>
          {(!natija.errors || natija.errors.length === 0) && (
            <span className="izoh">{t("xato_topilmadi")}</span>
          )}
          {(natija.errors || []).map((qator, i) => {
            const kop = typeof qator === "object" && "izoh" in qator;
            const { notogri, togri, sabab } = kop
              ? { notogri: qator.xato, togri: qator.tuzatish, sabab: T(qator.izoh, til) }
              : xatoniAjrat(qator);
            return (
              <div className="xato-el" key={i}>
                <span className="xato-notogri">{notogri}</span>
                {togri && <>→ <span className="xato-togri">{togri}</span></>}
                {sabab && <span className="xato-sabab">({sabab})</span>}
              </div>
            );
          })}
        </div>
        <div className="karta">
          <h3>{t("kuchli")}</h3>
          {(natija.strengths || []).map((s, i) => (
            <div className="xato-el" key={i}>✓ {T(s, til)}</div>
          ))}
          <h3 style={{ marginTop: 20 }}>{t("tahlil")}</h3>
          <p className="izoh" style={{ margin: 0 }}>
            {Object.values(natija.analysis || {}).map((v) => T(v, til)).join(" ")}
          </p>
        </div>
      </div>
    </>
  );
}

/** Haqiqiy mashq — tur tanlanadi, ro'yxatdan mavzu tanlanadi (namuna javobsiz),
 * talaba o'zi javob yozadi, AI tekshiradi. */
function HaqiqiyMashq() {
  const { t } = useI18n();
  const turlar = TURLAR.writing;
  const [tur, setTur] = useState(turlar[0]?.tur);
  const [royxat, setRoyxat] = useState(null);
  const [mashq, setMashq] = useState(null);
  const [mashqMatn, setMashqMatn] = useState("");
  const [korsatilganMatn, setKorsatilganMatn] = useState("");
  const [grafikUrl, setGrafikUrl] = useState(null);
  const [grafikPng, setGrafikPng] = useState(null);
  const [matn, setMatn] = useState("");
  const [natijalar, setNatijalar] = useState(null);
  const [xato, setXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [tarix, setTarix] = useState([]);

  useEffect(() => {
    api("/api/writing/tarix/").then(setTarix).catch(() => {});
  }, []);

  useEffect(() => {
    setMashq(null);
    setNatijalar(null);
    setRoyxat(null);
    api(`/api/mashqlar/?bolim=writing&tur=${tur}`).then(setRoyxat).catch(() => {});
  }, [tur]);

  useEffect(() => {
    function chiqishdanOldin(e) {
      if (!mashq || natijalar) return;
      e.preventDefault();
      e.returnValue = "";
    }
    window.addEventListener("beforeunload", chiqishdanOldin);
    return () => window.removeEventListener("beforeunload", chiqishdanOldin);
  }, [mashq, natijalar]);

  function ortgaQaytish() {
    if (!natijalar && !window.confirm(t("imtihon_ortga_tasdiq"))) return;
    setMashq(null);
  }

  async function mashqniOch(id) {
    const m = await api(`/api/mashqlar/${id}/`);
    setMashq(m);
    setMatn("");
    setNatijalar(null);
    setXato("");
    setGrafikUrl(null);
    setGrafikPng(null);

    let tozaMatn = m.matn || "";
    if (m.tur === "task1") {
      const ajratilgan = svgAjrat(tozaMatn);
      tozaMatn = ajratilgan.matn;
      if (ajratilgan.svgUrl) {
        setGrafikUrl(ajratilgan.svgUrl);
        svgniPngGaAylantir(ajratilgan.svgUrl).then(setGrafikPng).catch(() => {});
      }
    }
    setMashqMatn(tozaMatn);
    setKorsatilganMatn(haqiqiyMatnniOl(tozaMatn));
  }

  const sozSoni = matn.trim() ? matn.trim().split(/\s+/).length : 0;

  async function tekshir(modelKaliti) {
    setXato("");
    if (sozSoni < 20) {
      setXato(t("matn_qisqa"));
      return;
    }
    if (!window.confirm(t("imtihon_yakunlash_tasdiq"))) return;
    setYuklanmoqda(true);
    try {
      const body = { matn, savol_matni: mashqMatn, tur: mashq.tur, model: modelKaliti };
      if (grafikPng) {
        body.grafik_rasm = grafikPng;
      } else if (mashq?.rasm_url) {
        body.mashq_id = mashq.id;
      }
      const res = await api("/api/writing/tekshirish/", { method: "POST", body });
      setNatijalar(res.natijalar);
      api("/api/writing/tarix/").then(setTarix).catch(() => {});
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  // 2026-07-29 talabi: Task 1'da grafik/jadval ustidagi TAVSIF MATNI
  // ("The chart below shows...") ko'rsatilmasin — faqat rasm (grafik)
  // qoladi. Task 2'da esa insho savoli matni avvalgidek ko'rinadi.
  const tavsifKorinsinmi = korsatilganMatn && mashq.tur !== "task1";

  if (natijalar) {
    return (
      <>
        {(tavsifKorinsinmi || grafikUrl) && (
          <div className="karta" style={{ marginBottom: 14 }}>
            <h3>
              {mashq.name}
              {mashq.sun_iy_intellekt_yaratgan && <span className="si-belgi"> — {t("mashq_ai_yaratgan")}</span>}
            </h3>
            {tavsifKorinsinmi && <div className="mashq-passage">{korsatilganMatn}</div>}
            {grafikUrl && <img src={grafikUrl} alt="chart" style={{ maxWidth: "100%", marginTop: 10 }} />}
          </div>
        )}
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
          <button
            className="tugma ikkinchi"
            onClick={() => {
              setNatijalar(null);
              setMashq(null);
              setMatn("");
              setGrafikUrl(null);
              setGrafikPng(null);
            }}
          >
            {t("yangi_tekshiruv")}
          </button>
        </div>
        {natijalar.map((n, i) => (
          <Natija key={i} natija={n.natija} />
        ))}
      </>
    );
  }

  if (mashq) {
    return (
      <>
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
          <button className="tugma ikkinchi" onClick={ortgaQaytish}>
            {t("ortga")}
          </button>
        </div>
        <div className="karta" style={{ marginBottom: 14 }}>
          <h3>
            {mashq.name}
            {mashq.sun_iy_intellekt_yaratgan && <span className="si-belgi"> — {t("mashq_ai_yaratgan")}</span>}
          </h3>
          {tavsifKorinsinmi && <div className="mashq-passage">{korsatilganMatn}</div>}
          {grafikUrl && <img src={grafikUrl} alt="chart" style={{ maxWidth: "100%", marginTop: 10 }} />}
        </div>
        <div className="karta">
          <textarea
            {...IMLO_OFF}
            value={matn}
            onChange={(e) => setMatn(e.target.value)}
            placeholder={t("insho_placeholder")}
          />
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginTop: 12,
              flexWrap: "wrap",
              gap: 8,
            }}
          >
            <span className="izoh">
              {sozSoni} {t("soz")}
            </span>
            <button
              className="tugma katta"
              onClick={() => tekshir(MODEL_KALITI)}
              disabled={yuklanmoqda}
            >
              {yuklanmoqda ? t("tekshirilmoqda") : t("tekshirish")}
            </button>
          </div>
          {xato && <div className="xato-xabar" style={{ marginTop: 10 }}>{xato}</div>}
        </div>
      </>
    );
  }

  return (
    <>
      <div className="tab-guruh" style={{ marginBottom: 12 }}>
        {turlar.map((tt) => (
          <button key={tt.tur} className={tur === tt.tur ? "aktiv" : ""} onClick={() => setTur(tt.tur)}>
            {t(tt.kalit)}
          </button>
        ))}
      </div>
      <div className="karta">
        {royxat === null && <div className="yuklanmoqda">{t("yuklanmoqda")}</div>}
        {royxat && royxat.length === 0 && <span className="izoh">{t("mashq_royxati_boshi")}</span>}
        {royxat && royxat.map((m) => (
          <div key={m.id} className="mashq-royxat-el" onClick={() => mashqniOch(m.id)}>
            <span>{m.name}</span>
          </div>
        ))}
      </div>

      {tarix.length > 0 && (
        <div className="karta" style={{ marginTop: 18 }}>
          <h3>{t("tarix")}</h3>
          {tarix.map((tk) => (
            <div className="tarix-el" key={tk.id} onClick={() => setNatijalar([{ natija: tk.natija }])}>
              <span>
                {TASK_NOMI[tk.task_type] || tk.task_type || "—"} ·{" "}
                {new Date(tk.created_at).toLocaleDateString()}
              </span>
              <strong>{tk.overall_band ?? "—"}</strong>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export default function Writing() {
  const { t } = useI18n();
  const [rejim, setRejim] = useState("namunaviy");

  return (
    <>
      <div className="tab-guruh">
        <button className={rejim === "namunaviy" ? "aktiv" : ""} onClick={() => setRejim("namunaviy")}>
          {t("namunaviy")}
        </button>
        <button className={rejim === "haqiqiy" ? "aktiv" : ""} onClick={() => setRejim("haqiqiy")}>
          {t("haqiqiy_mashq")}
        </button>
        <button className={rejim === "oz" ? "aktiv" : ""} onClick={() => setRejim("oz")}>
          {t("oz_mavzum")}
        </button>
      </div>

      <div style={{ marginTop: 16 }}>
        {rejim === "namunaviy" && <NamunaMavzular bolim="writing" />}
        {rejim === "haqiqiy" && <HaqiqiyMashq />}
        {/* `Natija` prop orqali beriladi — OzMavzum bu fayldan import
            qilsa aylanma bog'liqlik paydo bo'lardi. */}
        {rejim === "oz" && <OzMavzum bolim="writing" NatijaKomponenti={Natija} />}
      </div>
    </>
  );
}
