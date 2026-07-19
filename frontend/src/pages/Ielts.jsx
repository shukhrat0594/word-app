import { useState } from "react";
import { useI18n } from "../i18n";
import ImtihonOtish from "./ImtihonOtish";
import Speaking from "./Speaking";
import Writing from "./Writing";

const TURLAR = [
  { kalit: "reading", nom_kaliti: "reading_bolimi" },
  { kalit: "listening", nom_kaliti: "listening_bolimi" },
  { kalit: "writing", nom_kaliti: "nav_writing" },
  { kalit: "speaking", nom_kaliti: "nav_speaking" },
];

export default function Ielts() {
  const { t } = useI18n();
  const [tur, setTur] = useState("reading");

  return (
    <>
      <div className="tab-guruh">
        {TURLAR.map((b) => (
          <button key={b.kalit} className={tur === b.kalit ? "aktiv" : ""} onClick={() => setTur(b.kalit)}>
            {t(b.nom_kaliti)}
          </button>
        ))}
      </div>

      <div style={{ marginTop: 16 }}>
        {(tur === "reading" || tur === "listening") && <ImtihonOtish bolim={tur} />}
        {tur === "writing" && <Writing />}
        {tur === "speaking" && <Speaking />}
      </div>
    </>
  );
}
