import { useEffect, useState } from "react";
import { api } from "../api";
import { Dinamika, Radar } from "../components/Grafiklar";
import { useI18n } from "../i18n";

export default function OtaOna() {
  const { t } = useI18n();
  const [farzandlar, setFarzandlar] = useState(null);
  const [tanlangan, setTanlangan] = useState(null);
  const [stat, setStat] = useState(null);

  useEffect(() => {
    api("/api/farzandlar/").then((qs) => {
      setFarzandlar(qs);
      if (qs.length === 1) setTanlangan(qs[0].id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!tanlangan) {
      setStat(null);
      return;
    }
    api(`/api/farzandlar/${tanlangan}/statistika/`).then(setStat).catch(() => {});
  }, [tanlangan]);

  if (!farzandlar) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  if (farzandlar.length === 0) {
    return (
      <div className="karta">
        <span className="izoh">{t("farzand_yoq")}</span>
      </div>
    );
  }

  return (
    <>
      {farzandlar.length > 1 && (
        <div className="tab-guruh">
          {farzandlar.map((f) => (
            <button
              key={f.id}
              className={tanlangan === f.id ? "aktiv" : ""}
              onClick={() => setTanlangan(f.id)}
            >
              {f.ism}
            </button>
          ))}
        </div>
      )}

      {!stat && <div className="yuklanmoqda">{t("yuklanmoqda")}</div>}

      {stat && (
        <>
          <div className="stat-qator">
            <div className="stat">
              <div className="nom">Writing band</div>
              <div className="qiymat">
                {stat.writing.oxirgi_band ?? "—"}{" "}
                <small>
                  {stat.writing.soni} {t("tekshiruv")}
                </small>
              </div>
            </div>
            <div className="stat">
              <div className="nom">Speaking band</div>
              <div className="qiymat">
                {stat.speaking.oxirgi_band ?? "—"}{" "}
                <small>
                  {stat.speaking.soni} {t("tekshiruv")}
                </small>
              </div>
            </div>
            <div className="stat">
              <div className="nom">{t("listening_foiz")}</div>
              <div className="qiymat">
                {stat.listening.ortacha_foiz != null ? `${stat.listening.ortacha_foiz}%` : "—"}
              </div>
            </div>
            <div className="stat">
              <div className="nom">{t("reading_foiz")}</div>
              <div className="qiymat">
                {stat.reading.ortacha_foiz != null ? `${stat.reading.ortacha_foiz}%` : "—"}
              </div>
            </div>
          </div>

          <div className="ikki-ustun">
            <div className="karta">
              <h3>{t("konikmalar")}</h3>
              <Radar konikmalar={stat.konikmalar} />
            </div>
            <div className="karta">
              <h3>Writing</h3>
              <Dinamika dinamika={stat.writing.dinamika} />
            </div>
          </div>

          <div className="ikki-ustun">
            <div className="karta">
              <h3>{t("dars_faolligi")}</h3>
              <div className="stat-qator" style={{ gridTemplateColumns: "repeat(2, 1fr)" }}>
                <div className="stat">
                  <div className="nom">{t("boshlangan")}</div>
                  <div className="qiymat">{stat.dars_faollik.boshlangan}</div>
                </div>
                <div className="stat">
                  <div className="nom">{t("tugatilgan")}</div>
                  <div className="qiymat">{stat.dars_faollik.tugatilgan}</div>
                </div>
              </div>
            </div>
            <div className="karta">
              <h3>{t("davomat")}</h3>
              <div className="stat-qator" style={{ gridTemplateColumns: "repeat(2, 1fr)" }}>
                <div className="stat">
                  <div className="nom">{t("keldi")}</div>
                  <div className="qiymat">{stat.davomat.keldi}</div>
                </div>
                <div className="stat">
                  <div className="nom">{t("kelmadi")}</div>
                  <div className="qiymat">{stat.davomat.kelmadi}</div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
