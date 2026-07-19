import { useEffect, useState } from "react";
import { api } from "../api";
import NamunaMavzular from "../components/NamunaMavzular";
import { useI18n } from "../i18n";
import { xatoniAjrat } from "../xatoUtils";

const TASK_NOMI = { task1: "Task 1", task2: "Task 2" };

function Natija({ natija }) {
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

export default function Writing() {
  const { t } = useI18n();
  const [matn, setMatn] = useState("");
  const [natija, setNatija] = useState(null);
  const [xato, setXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [tarix, setTarix] = useState([]);

  useEffect(() => {
    api("/api/writing/tarix/").then(setTarix).catch(() => {});
  }, []);

  const sozSoni = matn.trim() ? matn.trim().split(/\s+/).length : 0;

  async function tekshir() {
    setXato("");
    if (sozSoni < 20) {
      setXato(t("matn_qisqa"));
      return;
    }
    setYuklanmoqda(true);
    try {
      const res = await api("/api/writing/tekshirish/", {
        method: "POST",
        body: { matn },
      });
      setNatija(res.natija);
      api("/api/writing/tarix/").then(setTarix).catch(() => {});
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  function yangiTekshiruv() {
    setNatija(null);
    setMatn("");
    setXato("");
  }

  return (
    <>
      {!natija && (
        <div className="karta">
          <h3>{t("insho_yuboring")}</h3>
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
      )}

      {natija && (
        <>
          <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
            <button className="tugma ikkinchi" onClick={yangiTekshiruv}>
              {t("yangi_tekshiruv")}
            </button>
          </div>
          <Natija natija={natija} />
        </>
      )}

      {tarix.length > 0 && (
        <div className="karta">
          <h3>{t("tarix")}</h3>
          {tarix.map((tk) => (
            <div
              className="tarix-el"
              key={tk.id}
              onClick={() => setNatija(tk.natija)}
            >
              <span>
                {TASK_NOMI[tk.task_type] || tk.task_type || "—"} ·{" "}
                {new Date(tk.created_at).toLocaleDateString()}
              </span>
              <strong>{tk.overall_band ?? "—"}</strong>
            </div>
          ))}
        </div>
      )}

      <NamunaMavzular bolim="writing" />
    </>
  );
}
