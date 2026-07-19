import { useEffect, useState } from "react";
import { api } from "../api";
import { Dinamika, Radar } from "../components/Grafiklar";
import { useI18n } from "../i18n";

const BADGE_IKONLAR = {
  birinchi_mashq: "🚀",
  birinchi_writing: "✍",
  mukammal_natija: "💯",
  xp_100: "⭐",
  xp_500: "🏆",
  davomat_5: "📅",
};

export default function Dashboard() {
  const { t } = useI18n();
  const [stat, setStat] = useState(null);
  const [gami, setGami] = useState(null);
  const [lb, setLb] = useState(null);

  useEffect(() => {
    api("/api/statistika/").then(setStat).catch(() => {});
    api("/api/gamifikatsiya/").then(setGami).catch(() => {});
    api("/api/leaderboard/").then(setLb).catch(() => {});
  }, []);

  if (!stat || !gami) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  const k = stat.konikmalar;
  const orin = lb?.umumiy?.mening_ornim?.orin;

  return (
    <>
      <div className="stat-qator">
        <div className="stat">
          <div className="nom">{t("jami_xp")}</div>
          <div className="qiymat">{gami.jami_xp}</div>
        </div>
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
          <div className="nom">{t("reyting_orin")}</div>
          <div className="qiymat">{orin ? `#${orin}` : "—"}</div>
        </div>
      </div>

      <div className="ikki-ustun">
        <div className="karta">
          <h3>{t("konikmalar")}</h3>
          <Radar konikmalar={k} />
        </div>
        <div className="karta">
          <h3>Writing</h3>
          <Dinamika dinamika={stat.writing.dinamika} />
        </div>
      </div>

      <div className="ikki-ustun">
        <div className="karta">
          <h3>{t("umumiy_reyting")}</h3>
          {(lb?.umumiy?.top || []).slice(0, 5).map((r) => (
            <div
              key={r.id}
              className={
                "lb-qator" +
                (r.orin === 1 ? " birinchi" : "") +
                (lb.umumiy.mening_ornim?.id === r.id ? " men" : "")
              }
            >
              <span className="lb-orin">{r.orin}</span>
              <span className="lb-ism">
                {r.first_name || r.username}
                {lb.umumiy.mening_ornim?.id === r.id && (
                  <span style={{ color: "var(--matn-sokin)" }}> ({t("siz")})</span>
                )}
              </span>
              <span className="lb-xp">{r.xp} XP</span>
            </div>
          ))}
        </div>
        <div className="karta">
          <h3>{t("yutuqlar")}</h3>
          <div className="badge-qator">
            {gami.badges.length === 0 && (
              <span className="izoh">{t("hali_yoq")}</span>
            )}
            {gami.badges.map((b) => (
              <span className="badge" key={b.kod}>
                <span className="b-ikon">{BADGE_IKONLAR[b.kod] || "🎖"}</span>
                {b.nom}
              </span>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
