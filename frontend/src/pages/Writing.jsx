import { useEffect, useState } from "react";
import { api } from "../api";
import NamunaMavzular, { svgAjrat, TURLAR } from "../components/NamunaMavzular";
import { useI18n } from "../i18n";
import { svgniPngGaAylantir } from "../svgRasm";
import { xatoniAjrat } from "../xatoUtils";

const TASK_NOMI = { task1: "Task 1", task2: "Task 2" };

export function Natija({ natija }) {
  const { t } = useI18n();
  const mezonlar = [
    ["task_achievement", t("task_achievement")],
    ["coherence_cohesion", t("coherence_cohesion")],
    ["lexical_resource", t("lexical_resource")],
    ["grammatical_range", t("grammatical_range")],
  ];
  const taskNomi = TASK_NOMI[natija.task_type] || natija.task_type || "";

  return (
    <>
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
            const { notogri, togri, sabab } = xatoniAjrat(qator);
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
            <div className="xato-el" key={i}>✓ {s}</div>
          ))}
          <h3 style={{ marginTop: 20 }}>{t("tahlil")}</h3>
          <p className="izoh" style={{ margin: 0 }}>
            {Object.values(natija.analysis || {}).join(" ")}
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
  const [grafikUrl, setGrafikUrl] = useState(null);
  const [grafikPng, setGrafikPng] = useState(null);
  const [matn, setMatn] = useState("");
  const [natija, setNatija] = useState(null);
  const [xato, setXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [tarix, setTarix] = useState([]);

  useEffect(() => {
    api("/api/writing/tarix/").then(setTarix).catch(() => {});
  }, []);

  useEffect(() => {
    setMashq(null);
    setNatija(null);
    setRoyxat(null);
    api(`/api/mashqlar/?bolim=writing&tur=${tur}`).then(setRoyxat).catch(() => {});
  }, [tur]);

  useEffect(() => {
    function chiqishdanOldin(e) {
      if (!mashq || natija) return;
      e.preventDefault();
      e.returnValue = "";
    }
    window.addEventListener("beforeunload", chiqishdanOldin);
    return () => window.removeEventListener("beforeunload", chiqishdanOldin);
  }, [mashq, natija]);

  function ortgaQaytish() {
    if (!natija && !window.confirm(t("imtihon_ortga_tasdiq"))) return;
    setMashq(null);
  }

  async function mashqniOch(id) {
    const m = await api(`/api/mashqlar/${id}/`);
    setMashq(m);
    setMatn("");
    setNatija(null);
    setXato("");
    setGrafikUrl(null);
    setGrafikPng(null);

    if (m.tur === "task1") {
      const { matn: tozaMatn, svgUrl } = svgAjrat(m.matn || "");
      setMashqMatn(tozaMatn);
      if (svgUrl) {
        setGrafikUrl(svgUrl);
        svgniPngGaAylantir(svgUrl).then(setGrafikPng).catch(() => {});
      }
    } else {
      setMashqMatn(m.matn || "");
    }
  }

  const sozSoni = matn.trim() ? matn.trim().split(/\s+/).length : 0;

  async function tekshir() {
    setXato("");
    if (sozSoni < 20) {
      setXato(t("matn_qisqa"));
      return;
    }
    if (!window.confirm(t("imtihon_yakunlash_tasdiq"))) return;
    setYuklanmoqda(true);
    try {
      const body = { matn, savol_matni: mashqMatn, tur: mashq.tur };
      if (grafikPng) {
        body.grafik_rasm = grafikPng;
      } else if (mashq?.rasm_url) {
        body.mashq_id = mashq.id;
      }
      const res = await api("/api/writing/tekshirish/", { method: "POST", body });
      setNatija(res.natija);
      api("/api/writing/tarix/").then(setTarix).catch(() => {});
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  if (natija) {
    return (
      <>
        {mashqMatn && (
          <div className="karta" style={{ marginBottom: 14 }}>
            <h3>{mashq.name}</h3>
            <div className="mashq-passage">{mashqMatn}</div>
            {grafikUrl && <img src={grafikUrl} alt="chart" style={{ maxWidth: "100%", marginTop: 10 }} />}
          </div>
        )}
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
          <button
            className="tugma ikkinchi"
            onClick={() => {
              setNatija(null);
              setMashq(null);
              setMatn("");
              setGrafikUrl(null);
              setGrafikPng(null);
            }}
          >
            {t("yangi_tekshiruv")}
          </button>
        </div>
        <Natija natija={natija} />
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
          <h3>{mashq.name}</h3>
          {mashqMatn && <div className="mashq-passage">{mashqMatn}</div>}
          {grafikUrl && <img src={grafikUrl} alt="chart" style={{ maxWidth: "100%", marginTop: 10 }} />}
        </div>
        <div className="karta">
          <textarea
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
            }}
          >
            <span className="izoh">
              {sozSoni} {t("soz")}
            </span>
            <button className="tugma katta" onClick={tekshir} disabled={yuklanmoqda}>
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
            <div className="tarix-el" key={tk.id} onClick={() => setNatija(tk.natija)}>
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
      </div>

      <div style={{ marginTop: 16 }}>
        {rejim === "namunaviy" && <NamunaMavzular bolim="writing" />}
        {rejim === "haqiqiy" && <HaqiqiyMashq />}
      </div>
    </>
  );
}
