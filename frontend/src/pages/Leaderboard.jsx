import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";

const BADGE_KATALOG = {
  uz: {
    birinchi_mashq: ["Birinchi qadam", "Birinchi mashq yechildi"],
    birinchi_writing: ["Yozuvchi", "Birinchi Writing tekshiruvi"],
    mukammal_natija: ["Mukammal", "Birinchi 100% natija"],
    xp_100: ["Yulduz", "100 XP to'plandi"],
    xp_500: ["Chempion", "500 XP to'plandi"],
    davomat_5: ["Intizomli", "5 kun darsga keldi"],
  },
  ru: {
    birinchi_mashq: ["Первый шаг", "Первое упражнение выполнено"],
    birinchi_writing: ["Писатель", "Первая проверка Writing"],
    mukammal_natija: ["Идеально", "Первый результат 100%"],
    xp_100: ["Звезда", "Набрано 100 XP"],
    xp_500: ["Чемпион", "Набрано 500 XP"],
    davomat_5: ["Дисциплина", "5 дней на занятиях"],
  },
  en: {
    birinchi_mashq: ["First step", "First exercise completed"],
    birinchi_writing: ["Writer", "First Writing check"],
    mukammal_natija: ["Perfect", "First 100% score"],
    xp_100: ["Star", "Reached 100 XP"],
    xp_500: ["Champion", "Reached 500 XP"],
    davomat_5: ["Disciplined", "Attended 5 days"],
  },
};

const BADGE_IKONLAR = {
  birinchi_mashq: "🚀",
  birinchi_writing: "✍",
  mukammal_natija: "💯",
  xp_100: "⭐",
  xp_500: "🏆",
  davomat_5: "📅",
};

function Reyting({ ma, joriyId, t }) {
  if (!ma.top || ma.top.length === 0) {
    return <span className="izoh">{t("reyting_boshsiz")}</span>;
  }
  return (
    <>
      {ma.top.map((r) => (
        <div
          key={r.id}
          className={
            "lb-qator" +
            (r.orin === 1 ? " birinchi" : "") +
            (r.id === joriyId ? " men" : "")
          }
        >
          <span className="lb-orin">{r.orin}</span>
          <span className="lb-ism">
            {r.first_name || r.username}
            {r.id === joriyId && (
              <span style={{ color: "var(--matn-sokin)" }}> ({t("siz")})</span>
            )}
          </span>
          <span className="lb-xp">{r.xp} XP</span>
        </div>
      ))}
    </>
  );
}

export default function Leaderboard() {
  const { til, t } = useI18n();
  const { profil } = useProfil();
  const [lb, setLb] = useState(null);
  const [gami, setGami] = useState(null);
  const [tab, setTab] = useState("umumiy");

  useEffect(() => {
    api("/api/leaderboard/").then(setLb).catch(() => {});
    api("/api/gamifikatsiya/").then(setGami).catch(() => {});
  }, []);

  if (!lb || !gami) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  const joriyId = profil?.id;
  const katalog = BADGE_KATALOG[til] || BADGE_KATALOG.uz;
  const olinganKodlar = new Set(gami.badges.map((b) => b.kod));

  return (
    <>
      <div className="stat-qator" style={{ gridTemplateColumns: "repeat(2, 1fr)" }}>
        <div className="stat">
          <div className="nom">{t("jami_xp")}</div>
          <div className="qiymat">{gami.jami_xp}</div>
        </div>
        <div className="stat">
          <div className="nom">{t("reyting_orin")}</div>
          <div className="qiymat">
            {lb.umumiy.mening_ornim ? `#${lb.umumiy.mening_ornim.orin}` : "—"}
          </div>
        </div>
      </div>

      <div className="karta">
        <div className="tab-guruh" style={{ marginBottom: 14 }}>
          <button
            className={tab === "umumiy" ? "aktiv" : ""}
            onClick={() => setTab("umumiy")}
          >
            {t("umumiy_reyting")}
          </button>
          {lb.guruhlar.map((g) => (
            <button
              key={g.guruh.id}
              className={tab === `g${g.guruh.id}` ? "aktiv" : ""}
              onClick={() => setTab(`g${g.guruh.id}`)}
            >
              {g.guruh.name}
            </button>
          ))}
        </div>

        {tab === "umumiy" && <Reyting ma={lb.umumiy} joriyId={joriyId} t={t} />}
        {lb.guruhlar
          .filter((g) => tab === `g${g.guruh.id}`)
          .map((g) => <Reyting key={g.guruh.id} ma={g} joriyId={joriyId} t={t} />)}
      </div>

      <div className="ikki-ustun">
        <div className="karta">
          <h3>{t("barcha_yutuqlar")}</h3>
          <div className="badge-qator">
            {Object.keys(BADGE_IKONLAR).map((kod) => {
              const olinganmi = olinganKodlar.has(kod);
              const [nom, tavsif] = katalog[kod];
              return (
                <span className={"badge" + (olinganmi ? "" : " qulf")} key={kod}>
                  <span className="b-ikon">{BADGE_IKONLAR[kod]}</span>
                  <span>
                    {nom}
                    <br />
                    <span className="b-tavsif">{tavsif}</span>
                  </span>
                </span>
              );
            })}
          </div>
        </div>

        <div className="karta">
          <h3>{t("songgi_hodisalar")}</h3>
          {gami.oxirgi.length === 0 && <span className="izoh">{t("hodisa_yoq")}</span>}
          {gami.oxirgi.map((h, i) => (
            <div className="xp-hodisa" key={i}>
              <span>{t(`xp_${h.sabab}`)}</span>
              <span className="h-miqdor">+{h.miqdor}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
