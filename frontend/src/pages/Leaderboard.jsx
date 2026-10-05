import { useEffect, useState } from "react";
import { api } from "../api";
import Avatar from "../components/Avatar";
import XatolikHolati from "../components/XatolikHolati";
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
          <Avatar rasmUrl={r.rasm_url} olcham={28} sarlavha={r.first_name || r.username} />
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

function darajaNomi(d, t) {
  return d ? d.nomi : t("reyting_darajasiz");
}

export default function Leaderboard() {
  const { til, t } = useI18n();
  const { profil } = useProfil();
  const [lb, setLb] = useState(null);
  const [gami, setGami] = useState(null);
  // Reyting turi (IELTS | Kurslar) va davri (Shu oy | Hamma vaqt) — server tomonida hisoblanadi.
  const [tur, setTur] = useState("ielts");
  const [davr, setDavr] = useState("oy");
  const [tab, setTab] = useState("d0"); // d<indeks> — daraja, g<id> — guruh
  const [xato, setXato] = useState(false);

  function yukla() {
    setXato(false);
    api(`/api/leaderboard/?tur=${tur}&davr=${davr}`).then(setLb).catch(() => setXato(true));
    api("/api/gamifikatsiya/").then(setGami).catch(() => setXato(true));
  }

  useEffect(() => {
    yukla();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tur, davr]);

  if (xato) return <XatolikHolati qaytaUrin={yukla} />;

  if (!lb || !gami) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  const joriyId = profil?.id;
  const katalog = BADGE_KATALOG[til] || BADGE_KATALOG.uz;
  const olinganKodlar = new Set(gami.badges.map((b) => b.kod));
  const darajalar = lb.darajalar || [];
  const aktivTab = tab.startsWith("g") || darajalar[Number(tab.slice(1))] ? tab : "d0";
  const aktivDaraja = aktivTab.startsWith("d") ? darajalar[Number(aktivTab.slice(1))] : darajalar[0];

  return (
    <>
      <div className="stat-qator" style={{ gridTemplateColumns: "repeat(2, 1fr)" }}>
        <div className="stat">
          <div className="nom">{t("jami_xp")}</div>
          <div className="qiymat">{gami.jami_xp}</div>
        </div>
        <div className="stat">
          <div className="nom">
            {t("reyting_orin")}
            {aktivDaraja ? ` · ${darajaNomi(aktivDaraja.daraja, t)}` : ""}
          </div>
          <div className="qiymat">
            {aktivDaraja?.mening_ornim ? `#${aktivDaraja.mening_ornim.orin}` : "—"}
          </div>
        </div>
      </div>

      <div className="karta">
        <div className="tab-guruh" style={{ marginBottom: 8 }}>
          {["ielts", "kurs"].map((x) => (
            <button key={x} className={tur === x ? "aktiv" : ""} onClick={() => setTur(x)}>
              {t(x === "ielts" ? "reyting_ielts" : "reyting_kurslar")}
            </button>
          ))}
          <span style={{ width: 12 }} />
          {["oy", "hammasi"].map((x) => (
            <button key={x} className={davr === x ? "aktiv" : ""} onClick={() => setDavr(x)}>
              {t(x === "oy" ? "davr_oy" : "davr_hammasi")}
            </button>
          ))}
        </div>
        <div className="tab-guruh" style={{ marginBottom: 6 }}>
          {darajalar.map((d, i) => (
            <button key={`d${i}`} className={aktivTab === `d${i}` ? "aktiv" : ""} onClick={() => setTab(`d${i}`)}>
              {darajaNomi(d.daraja, t)}
            </button>
          ))}
          {lb.guruhlar.map((g) => (
            <button
              key={g.guruh.id}
              className={aktivTab === `g${g.guruh.id}` ? "aktiv" : ""}
              onClick={() => setTab(`g${g.guruh.id}`)}
            >
              {g.guruh.name}
            </button>
          ))}
        </div>
        <p className="izoh" style={{ margin: "0 0 10px" }}>{t("reyting_daraja_izoh")}</p>

        {aktivTab.startsWith("d") && aktivDaraja && <Reyting ma={aktivDaraja} joriyId={joriyId} t={t} />}
        {lb.guruhlar
          .filter((g) => aktivTab === `g${g.guruh.id}`)
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
