import { useEffect, useRef, useState } from "react";
import { api, apiForm } from "../api";
import NamunaMavzular, { TURLAR } from "../components/NamunaMavzular";
import { haqiqiyMatnniOl } from "../haqiqiyMatn";
import { useI18n } from "../i18n";
import { IMLO_OFF } from "../imlo";
import { xatoniAjrat } from "../xatoUtils";
import OzMavzum from "./OzMavzum";

const PART_NOMI = { part1: "Part 1", part2: "Part 2", part3: "Part 3" };

// 2026-07-26: Writing.jsx bilan bir xil sabab — Gemma olib tashlangach
// modellarni solishtiradigan uch tugma o'rnini yagona "Tekshirish" oldi.
const MODEL_KALITI = "flash_lite";

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
  const [natijalar, setNatijalar] = useState(null);
  const [xato, setXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [tarix, setTarix] = useState([]);

  useEffect(() => {
    api("/api/speaking/tarix/").then(setTarix).catch(() => {});
  }, []);

  useEffect(() => {
    setMashq(null);
    setNatijalar(null);
    setRoyxat(null);
    api(`/api/mashqlar/?bolim=speaking&tur=${tur}`).then(setRoyxat).catch(() => {});
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
    setKorsatilganMatn(haqiqiyMatnniOl(m.matn || ""));
    setMatn("");
    setNatijalar(null);
    setXato("");
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
      const body = { matn, savol_matni: mashq.matn, tur: mashq.tur, model: modelKaliti };
      const res = await api("/api/speaking/matn/", { method: "POST", body });
      setNatijalar(res.natijalar);
      api("/api/speaking/tarix/").then(setTarix).catch(() => {});
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  if (natijalar) {
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
              setNatijalar(null);
              setMashq(null);
              setMatn("");
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
          {korsatilganMatn && <div className="mashq-passage">{korsatilganMatn}</div>}
        </div>
        <div className="karta">
          <textarea
            {...IMLO_OFF}
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

/** Mikrofon rejimi (2026-07-29): matnga o'girish o'rniga talaba ovoz
 * yozib oladi — brauzerning `MediaRecorder` API'si orqali, keyin audio
 * `/api/speaking/audio/`ga yuboriladi. Backend uni Gemini orqali matnga
 * o'giradi (transkripsiya) va xuddi Matn rejimidagi 3 mezon bilan
 * baholaydi (Pronunciation YO'Q — bu Azure'ning "Tezkor tahlil"
 * o'rnini bosuvchi soddaroq variant emas, alohida yo'l). */
function AudioHaqiqiyMashq() {
  const { t } = useI18n();
  const turlar = TURLAR.speaking;
  const [tur, setTur] = useState(turlar[0]?.tur);
  const [royxat, setRoyxat] = useState(null);
  const [mashq, setMashq] = useState(null);
  const [korsatilganMatn, setKorsatilganMatn] = useState("");
  const [natijalar, setNatijalar] = useState(null);
  const [transkript, setTranskript] = useState("");
  const [xato, setXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [tarix, setTarix] = useState([]);

  const [yozilmoqda, setYozilmoqda] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [yozishSoniya, setYozishSoniya] = useState(0);
  const [mikrofonXato, setMikrofonXato] = useState("");
  const mediaRecorderRef = useRef(null);
  const bolaklarRef = useRef([]);

  useEffect(() => {
    api("/api/speaking/tarix/").then(setTarix).catch(() => {});
  }, []);

  useEffect(() => {
    setMashq(null);
    setNatijalar(null);
    setRoyxat(null);
    api(`/api/mashqlar/?bolim=speaking&tur=${tur}`).then(setRoyxat).catch(() => {});
  }, [tur]);

  useEffect(() => {
    if (!yozilmoqda) return undefined;
    const boshlandi = Date.now();
    setYozishSoniya(0);
    const taymer = setInterval(() => setYozishSoniya(Math.floor((Date.now() - boshlandi) / 1000)), 1000);
    return () => clearInterval(taymer);
  }, [yozilmoqda]);

  // Audio Object URL'lar sahifa yopilganda/almashtirilganda tozalansin.
  useEffect(() => () => { if (audioUrl) URL.revokeObjectURL(audioUrl); }, [audioUrl]);

  function ortgaQaytish() {
    if (!natijalar && !window.confirm(t("imtihon_ortga_tasdiq"))) return;
    setMashq(null);
  }

  async function mashqniOch(id) {
    const m = await api(`/api/mashqlar/${id}/`);
    setMashq(m);
    setKorsatilganMatn(haqiqiyMatnniOl(m.matn || ""));
    setNatijalar(null);
    setTranskript("");
    setXato("");
    setAudioBlob(null);
    setAudioUrl(null);
  }

  async function yozishBoshla() {
    setMikrofonXato("");
    setAudioBlob(null);
    setAudioUrl(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      bolaklarRef.current = [];
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) bolaklarRef.current.push(e.data);
      };
      mr.onstop = () => {
        const blob = new Blob(bolaklarRef.current, { type: mr.mimeType || "audio/webm" });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
        stream.getTracks().forEach((tr) => tr.stop());
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

  async function yubor() {
    if (!audioBlob) return;
    if (!window.confirm(t("imtihon_yakunlash_tasdiq"))) return;
    setXato("");
    setYuklanmoqda(true);
    try {
      const fd = new FormData();
      fd.append("audio", audioBlob, "yozuv.webm");
      fd.append("savol_matni", mashq.matn);
      fd.append("tur", mashq.tur);
      const res = await apiForm("/api/speaking/audio/", { method: "POST", formData: fd });
      setNatijalar([{ natija: res.natija }]);
      setTranskript(res.transkript || "");
      api("/api/speaking/tarix/").then(setTarix).catch(() => {});
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  function vaqtFormat(soniya) {
    const daq = Math.floor(soniya / 60);
    const s = soniya % 60;
    return `${daq}:${String(s).padStart(2, "0")}`;
  }

  if (natijalar) {
    return (
      <>
        {korsatilganMatn && (
          <div className="karta" style={{ marginBottom: 14 }}>
            <h3>{mashq.name}</h3>
            <div className="mashq-passage">{korsatilganMatn}</div>
          </div>
        )}
        {transkript && (
          <div className="karta" style={{ marginBottom: 14 }}>
            <h3>{t("sizning_javobingiz")}</h3>
            <p className="izoh" style={{ margin: 0 }}>{transkript}</p>
          </div>
        )}
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
          <button
            className="tugma ikkinchi"
            onClick={() => {
              setNatijalar(null);
              setMashq(null);
              setTranskript("");
              setAudioBlob(null);
              setAudioUrl(null);
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
          <h3>{mashq.name}</h3>
          {korsatilganMatn && <div className="mashq-passage">{korsatilganMatn}</div>}
        </div>
        <div className="karta">
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            {!yozilmoqda ? (
              <button className="tugma katta" onClick={yozishBoshla}>
                🎙 {audioBlob ? t("qayta_yozish") : t("yozib_olish")}
              </button>
            ) : (
              <button className="tugma katta" style={{ background: "#d33", color: "#fff" }} onClick={yozishToxtat}>
                ⏹ {t("toxtatish")} ({vaqtFormat(yozishSoniya)})
              </button>
            )}
            {audioUrl && !yozilmoqda && (
              /* eslint-disable-next-line jsx-a11y/media-has-caption */
              <audio controls src={audioUrl} />
            )}
          </div>
          {mikrofonXato && <div className="xato-xabar" style={{ marginTop: 10 }}>{mikrofonXato}</div>}
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              alignItems: "center",
              marginTop: 12,
              gap: 8,
            }}
          >
            <button
              className="tugma katta"
              onClick={yubor}
              disabled={!audioBlob || yuklanmoqda || yozilmoqda}
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
        <button
          className={rejim === "audio" ? "aktiv" : ""}
          onClick={() => setRejim("audio")}
        >
          🎙 {t("mikrofon_rejimi")}
        </button>
      </div>

      {rejim === "audio" && (
        <div style={{ marginTop: 16 }}>
          <AudioHaqiqiyMashq />
        </div>
      )}

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
            <button
              className={ichkiRejim === "oz" ? "aktiv" : ""}
              onClick={() => setIchkiRejim("oz")}
            >
              {t("oz_mavzum")}
            </button>
          </div>
          <div style={{ marginTop: 16 }}>
            {ichkiRejim === "namunaviy" && <NamunaMavzular bolim="speaking" />}
            {ichkiRejim === "haqiqiy" && <HaqiqiyMashq />}
            {/* `Natija` prop orqali — aylanma import bo'lmasligi uchun. */}
            {ichkiRejim === "oz" && <OzMavzum bolim="speaking" NatijaKomponenti={Natija} />}
          </div>
          <p className="izoh" style={{ marginTop: 16 }}>
            {t("tezkor_izoh")}
          </p>
        </div>
      )}
    </>
  );
}
