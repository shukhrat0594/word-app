import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";

export default function DavomatHisoboti() {
  const { t } = useI18n();
  const [hisobot, setHisobot] = useState(null);

  useEffect(() => {
    api("/api/davomat-hisoboti/").then(setHisobot).catch(() => {});
  }, []);

  if (!hisobot) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  const guruhlar = hisobot.guruhlar || [];

  return (
    <>
      {guruhlar.length === 0 && (
        <div className="karta">
          <span className="izoh">{t("hisobot_yoq")}</span>
        </div>
      )}
      {guruhlar.map((g) => (
        <div className="karta" key={g.id} style={{ marginBottom: 16 }}>
          <h3>{g.name}</h3>
          {g.talabalar.length === 0 && <span className="izoh">{t("talaba_yoq")}</span>}
          {g.talabalar.map((tl) => (
            <div className="davomat-qator" key={tl.id}>
              <span>{tl.ism}</span>
              <span>
                <span className="chip bor" style={{ marginRight: 6 }}>
                  {t("keldi")}: {tl.keldi}
                </span>
                <span className="chip tugadi" style={{ marginRight: 6 }}>
                  {t("kelmadi")}: {tl.kelmadi}
                </span>
                <strong>{tl.foiz != null ? `${tl.foiz}%` : "—"}</strong>
              </span>
            </div>
          ))}
        </div>
      ))}
    </>
  );
}
