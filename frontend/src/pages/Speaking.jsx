import { useEffect, useState } from "react";
import { api } from "../api";
import NamunaMavzular, { TURLAR } from "../components/NamunaMavzular";
import { haqiqiyMatnniOl } from "../haqiqiyMatn";
import { useI18n } from "../i18n";
import { xatoniAjrat } from "../xatoUtils";

const PART_NOMI = { part1: "Part 1", part2: "Part 2", part3: "Part 3" };

export function Natija({ natija }) {
  const { t } = useI18n();
  const mezonlar = [
    ["fluency_coherence", t("fluency_coherence")],
    ["lexical_resource", t("lexical_resource")],
    ["grammatical_range", t("grammatical_range")],
  ];
  const partNomi = PART_NOMI[natija.part_type] || natija.part_type || "";

  return (
    <>
      <div className="umumiy-band">
        <span className="u-ball">{natija.overall_band_no_pronunciation ?? "—"}</span>
        <div>
          <div style={{ fontWeight: 700 }}>
            Overall Band{partNomi ? ` — ${partNomi}` : ""}
          </div>
          <div className="u-izoh">
            {natija.word_count} {t("soz")}
          </div>
        </div>
      </div>

      <div className="mezon-qator" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
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
  const turlar = TURLAR.speaking;
  const [tur, setTur] = useState(turlar[0]?.tur);
  const [royxat, setRoyxat] = useState(null);
  const [mashq, setMashq] = useState(null);
  const [korsatilganMatn, setKorsatilganMatn] = useState("");
  const [matn, setMatn] = useState("");
  const [natija, setNatija] = useState(null);
  const [xato, setXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [tarix, setTarix] = useState([]);

  useEffect(() => {
    api("/api/speaking/tarix/").then(setTarix).catch(() => {});
  }, []);

  useEffect(() => {
    setMashq(null);
    setNatija(null);
    setRoyxat(null);
    api(`/api/mashqlar/?bolim=speaking&tur=${tur}`).then(setRoyxat).catch(() => {});
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
    setKorsatilganMatn(haqiqiyMatnniOl(m.matn || ""));
    setMatn("");
    setNatija(null);
    setXato("");
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
      const body = { matn, savol_matni: mashq.matn, tur: mashq.tur };
      const res = await api("/api/speaking/matn/", { method: "POST", body });
      setNatija(res.natija);
      api("/api/speaking/tarix/").then(setTarix).catch(() => {});
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  if (natija) {
    return (
      <>
        {korsatilganMatn && (
          <div className="karta" style={{ marginBottom: 14 }}>
            <h3>
              {mashq.name}
              {mashq.sun_iy_intellekt_yaratgan && <span className="si-belgi"> — {t("mashq_ai_yaratgan")}</span>}
            </h3>
            <div className="mashq-passage">{korsatilganMatn}</div>
          </div>
        )}
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
          <button
            className="tugma ikkinchi"
            onClick={() => {
              setNatija(null);
              setMashq(null);
              setMatn("");
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
          <h3>
            {mashq.name}
            {mashq.sun_iy_intellekt_yaratgan && <span className="si-belgi"> — {t("mashq_ai_yaratgan")}</span>}
          </h3>
          {korsatilganMatn && <div className="mashq-passage">{korsatilganMatn}</div>}
        </div>
        <div className="karta">
          <textarea
            value={matn}
            onChange={(e) => setMatn(e.target.value)}
            placeholder={t("javob_placeholder")}
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
                {PART_NOMI[tk.part_type] || tk.part_type || "—"} ·{" "}
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

export default function Speaking() {
  const { t } = useI18n();
  const [rejim, setRejim] = useState("matn");
  const [ichkiRejim, setIchkiRejim] = useState("namunaviy");

  return (
    <>
      <div className="tab-guruh">
        <button
          className={rejim === "matn" ? "aktiv" : ""}
          onClick={() => setRejim("matn")}
        >
          {t("matn_rejimi")}
        </button>
        <button disabled title={t("tez_orada")}>
          {t("tezkor_tahlil")} · {t("tez_orada")}
        </button>
      </div>

      {rejim === "matn" && (
        <div style={{ marginTop: 16 }}>
          <div className="tab-guruh">
            <button
              className={ichkiRejim === "namunaviy" ? "aktiv" : ""}
              onClick={() => setIchkiRejim("namunaviy")}
            >
              {t("namunaviy")}
            </button>
            <button
              className={ichkiRejim === "haqiqiy" ? "aktiv" : ""}
              onClick={() => setIchkiRejim("haqiqiy")}
            >
              {t("haqiqiy_mashq")}
            </button>
          </div>
          <div style={{ marginTop: 16 }}>
            {ichkiRejim === "namunaviy" && <NamunaMavzular bolim="speaking" />}
            {ichkiRejim === "haqiqiy" && <HaqiqiyMashq />}
          </div>
          <p className="izoh" style={{ marginTop: 16 }}>
            {t("tezkor_izoh")}
          </p>
        </div>
      )}
    </>
  );
}
