import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { xatoniAjrat } from "../xatoUtils";

const TASK_NOMI = { task1: "Task 1", task2: "Task 2" };
const PART_NOMI = { part1: "Part 1", part2: "Part 2", part3: "Part 3" };

function sarlavhaOl(y) {
  if (y.turi === "writing") return TASK_NOMI[y.sarlavha] || y.sarlavha || "Writing";
  return PART_NOMI[y.sarlavha] || y.sarlavha || "Speaking";
}

export default function Tarix() {
  const { t } = useI18n();
  const [royxat, setRoyxat] = useState(null);
  const [ochiqId, setOchiqId] = useState(null);

  useEffect(() => {
    api("/api/tarix/").then(setRoyxat).catch(() => {});
  }, []);

  if (!royxat) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <div className="karta">
      <h3>{t("mening_tarixim")}</h3>
      {royxat.length === 0 && <span className="izoh">{t("tarix_yoq")}</span>}
      {royxat.map((y) => {
        const kalit = `${y.turi}-${y.id}`;
        const ochiqmi = ochiqId === kalit;
        return (
          <div key={kalit}>
            <div
              className="tarix-el"
              onClick={() => setOchiqId(ochiqmi ? null : kalit)}
            >
              <span>
                <span className="chip bor" style={{ marginRight: 8 }}>
                  {y.turi === "writing" ? t("nav_writing") : t("nav_speaking")}
                </span>
                {sarlavhaOl(y)} · {new Date(y.created_at).toLocaleDateString()}
                {y.audio_url && " 🎙"}
              </span>
              <strong>{y.overall_band ?? "—"}</strong>
            </div>

            {ochiqmi && (
              <div className="karta" style={{ margin: "8px 0 16px", background: "var(--sirt-2)" }}>
                {y.audio_url && (
                  <audio controls src={y.audio_url} style={{ width: "100%", marginBottom: 14 }} />
                )}
                <h3>
                  {t("xatolar")} ({y.natija.errors?.length || 0})
                </h3>
                {(!y.natija.errors || y.natija.errors.length === 0) && (
                  <span className="izoh">{t("xato_topilmadi")}</span>
                )}
                {(y.natija.errors || []).map((qator, i) => {
                  const { notogri, togri, sabab } = xatoniAjrat(qator);
                  return (
                    <div className="xato-el" key={i}>
                      <span className="xato-notogri">{notogri}</span>
                      {togri && <>→ <span className="xato-togri">{togri}</span></>}
                      {sabab && <span className="xato-sabab">({sabab})</span>}
                    </div>
                  );
                })}
                {y.natija.strengths?.length > 0 && (
                  <>
                    <h3 style={{ marginTop: 16 }}>{t("kuchli")}</h3>
                    {y.natija.strengths.map((s, i) => (
                      <div className="xato-el" key={i}>✓ {s}</div>
                    ))}
                  </>
                )}
                {y.natija.analysis && (
                  <>
                    <h3 style={{ marginTop: 16 }}>{t("tahlil")}</h3>
                    <p className="izoh" style={{ margin: 0 }}>
                      {Object.values(y.natija.analysis).join(" ")}
                    </p>
                  </>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
