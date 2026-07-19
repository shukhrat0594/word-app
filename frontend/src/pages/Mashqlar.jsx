import { useState } from "react";
import { useI18n } from "../i18n";
import MashqBank from "./MashqBank";
import Speaking from "./Speaking";
import Writing from "./Writing";

const IELTS_BOLIMLAR = [
  { kalit: "writing", nom_kaliti: "nav_writing" },
  { kalit: "speaking", nom_kaliti: "nav_speaking" },
  { kalit: "reading", nom_kaliti: "reading_bolimi" },
  { kalit: "listening", nom_kaliti: "listening_bolimi" },
];

export default function Mashqlar() {
  const { t } = useI18n();
  const [imtihon, setImtihon] = useState("ielts");
  const [bolim, setBolim] = useState("writing");

  return (
    <>
      <div className="tab-guruh">
        <button className={imtihon === "ielts" ? "aktiv" : ""} onClick={() => setImtihon("ielts")}>
          IELTS
        </button>
        <button disabled title={t("tez_orada")}>
          CEFR · {t("tez_orada")}
        </button>
      </div>

      {imtihon === "ielts" && (
        <>
          <div className="tab-guruh" style={{ marginTop: 10 }}>
            {IELTS_BOLIMLAR.map((b) => (
              <button
                key={b.kalit}
                className={bolim === b.kalit ? "aktiv" : ""}
                onClick={() => setBolim(b.kalit)}
              >
                {t(b.nom_kaliti)}
              </button>
            ))}
          </div>

          <div style={{ marginTop: 16 }}>
            {bolim === "writing" && <Writing />}
            {bolim === "speaking" && <Speaking />}
            {(bolim === "reading" || bolim === "listening") && <MashqBank bolim={bolim} />}
          </div>
        </>
      )}
    </>
  );
}
