import { useEffect, useState } from "react";
import { api } from "../api";
import { svgAjrat, TURLAR } from "../components/NamunaMavzular";
import { useI18n } from "../i18n";
import { standartVaqt } from "../imtihonVaqt";
import { svgniPngGaAylantir } from "../svgRasm";
import { vaqtFormat } from "./ImtihonOtish";
import { Natija as SpeakingNatija } from "./Speaking";
import { Natija as WritingNatija } from "./Writing";

const TASK_NOMI = { task1: "Task 1", task2: "Task 2", part1: "Part 1", part2: "Part 2", part3: "Part 3" };

/** "IELTS testlari"dagi Writing/Speaking — R/L bilan bir xil uslubda:
 * taymer (bosilsa teskari sanoqqa aylanadi), ortga/tekshirish tasdiq
 * dialoglari, sahifani yopishda ogohlantirish. Mavjud "Mashqlar"
 * bo'limidagi Writing/Speaking'ga (hammaga ochiq) tegmaydi — mustaqil. */
export default function ImtihonYozGap({ bolim }) {
  const { t } = useI18n();
  const turlar = TURLAR[bolim] || [];
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
  const [soniya, setSoniya] = useState(0);
  const [teskariMi, setTeskariMi] = useState(false);

  useEffect(() => {
    setMashq(null);
    setNatija(null);
    setRoyxat(null);
    api(`/api/mashqlar/?bolim=${bolim}&tur=${tur}`).then(setRoyxat).catch(() => {});
  }, [bolim, tur]);

  useEffect(() => {
    if (!mashq || natija) return;
    const idT = setInterval(() => setSoniya((s) => s + 1), 1000);
    return () => clearInterval(idT);
  }, [mashq, natija]);

  useEffect(() => {
    function chiqishdanOldin(e) {
      if (!mashq || natija) return;
      e.preventDefault();
      e.returnValue = "";
    }
    window.addEventListener("beforeunload", chiqishdanOldin);
    return () => window.removeEventListener("beforeunload", chiqishdanOldin);
  }, [mashq, natija]);

  async function mashqniOch(id) {
    const m = await api(`/api/mashqlar/${id}/`);
    setMashq(m);
    setMatn("");
    setNatija(null);
    setXato("");
    setSoniya(0);
    setTeskariMi(false);
    setGrafikUrl(null);
    setGrafikPng(null);

    if (bolim === "writing" && m.tur === "task1") {
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

  function ortgaQaytish() {
    if (!natija && !window.confirm(t("imtihon_ortga_tasdiq"))) return;
    setMashq(null);
  }

  async function tekshir() {
    setXato("");
    if (sozSoni < 20) {
      setXato(t("matn_qisqa"));
      return;
    }
    if (!window.confirm(t("imtihon_yakunlash_tasdiq"))) return;

    setYuklanmoqda(true);
    try {
      const yol = bolim === "writing" ? "/api/writing/tekshirish/" : "/api/speaking/matn/";
      const body = { matn, savol_matni: mashqMatn, tur };
      if (bolim === "writing" && grafikPng) {
        body.grafik_rasm = grafikPng;
      } else if (bolim === "writing" && mashq?.rasm_url) {
        body.mashq_id = mashq.id;
      }
      const res = await api(yol, { method: "POST", body });
      setNatija(res.natija);
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  const NatijaKomponenti = bolim === "writing" ? WritingNatija : SpeakingNatija;
  const jamiVaqt = standartVaqt(bolim, tur);
  const korsatilganVaqt = teskariMi ? Math.max(0, jamiVaqt - soniya) : soniya;

  if (mashq) {
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

        {natija ? (
          <>
            <div className="karta" style={{ margin: "14px 0" }}>
              <h3>{mashq.name}</h3>
              {mashqMatn && <div className="mashq-passage">{mashqMatn}</div>}
              {grafikUrl && <img src={grafikUrl} alt="chart" style={{ maxWidth: "100%", marginTop: 10 }} />}
            </div>
            <NatijaKomponenti natija={natija} />
          </>
        ) : (
          <>
            <div className="karta" style={{ margin: "14px 0" }}>
              <h3>{mashq.name}</h3>
              {mashqMatn && <div className="mashq-passage">{mashqMatn}</div>}
              {grafikUrl && <img src={grafikUrl} alt="chart" style={{ maxWidth: "100%", marginTop: 10 }} />}
            </div>
            <div className="karta">
              <textarea
                value={matn}
                onChange={(e) => setMatn(e.target.value)}
                placeholder={bolim === "writing" ? t("insho_placeholder") : t("javob_placeholder")}
              />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
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
        )}
      </div>
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
            <span>{TASK_NOMI[m.tur] ? `${TASK_NOMI[m.tur]} — ` : ""}{m.name}</span>
          </div>
        ))}
      </div>
    </>
  );
}
