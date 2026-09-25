// Hisobotlar — oylar kesimida dinamika.
//
// Moliya → Hisobot tabidan FARQI: u bitta oyni guruhlar kesimida
// ko'rsatadi ("shu oyda kim qarzdor"), bu esa bir necha oyni yonma-yon
// ("yig'ilish yaxshilanyaptimi"). Ikkalasi boshqa savolga javob beradi,
// shuning uchun alohida.

import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { apiFayluniYuklab } from "../api.js";
import { useFilial } from "../filialContext.jsx";
import { oyNomi, oyQiymati, pul, sana } from "../format.js";
import { useI18n } from "../i18n.jsx";
import { sorovSatri, useSorov } from "../soragich.js";

const ORALIQLAR = [6, 12, 24];

/** Yig'ilish foizi bo'yicha rang — 90%+ yaxshi, 70%+ o'rtacha, pastda yomon. */
function foizSinfi(foiz) {
  if (foiz >= 90) return "rang-tolandi";
  if (foiz >= 70) return "rang-qisman";
  return "rang-qarzdor";
}

function Dinamika() {
  const { t, til } = useI18n();
  const { tanlangan } = useFilial();
  const [oylar, setOylar] = useState(12);

  const { malumot, yuklanmoqda, xato } = useSorov(
    "/api/crm/hisobot/dinamika/" + sorovSatri({ oylar, filial: tanlangan })
  );
  const qatorlar = malumot || [];

  // Eng katta "hisoblangan" — ustunchalar shunga nisbatan chiziladi.
  const eng = Math.max(1, ...qatorlar.map((q) => Number(q.hisoblangan || 0)));

  const jami = qatorlar.reduce(
    (yigindi, q) => ({
      hisoblangan: yigindi.hisoblangan + Number(q.hisoblangan || 0),
      olingan: yigindi.olingan + Number(q.olingan || 0),
      chegirma: yigindi.chegirma + Number(q.chegirma || 0),
      qarz: yigindi.qarz + Number(q.qarz || 0),
    }),
    { hisoblangan: 0, olingan: 0, chegirma: 0, qarz: 0 }
  );
  const jamiFoiz = jami.hisoblangan
    ? Math.round((jami.olingan / jami.hisoblangan) * 1000) / 10
    : 0;

  return (
    <section>

      <div className="filtrlar">
        {ORALIQLAR.map((x) => (
          <button
            key={x}
            type="button"
            className={oylar === x ? "tab faol" : "tab"}
            onClick={() => setOylar(x)}
          >
            {x} {t("oy")}
          </button>
        ))}
        <button
          className="tugma tugma-sokin"
          type="button"
          onClick={() => apiFayluniYuklab("/api/crm/eksport/" + sorovSatri({ filial: tanlangan }))}
        >
          ⬇ Excel
        </button>
      </div>

      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      <div className="karta jadval-oram">
        <table>
          <thead>
            <tr>
              <th>{t("qaysi_oy")}</th>
              <th className="ongga">{t("talabalar")}</th>
              <th className="ongga">{t("hisoblangan")}</th>
              <th className="ongga">{t("olingan_pul")}</th>
              <th className="ongga">{t("chegirma")}</th>
              <th className="ongga">{t("qarz")}</th>
              <th className="ongga">{t("yigilish")}</th>
              <th>{/* ustuncha */}</th>
            </tr>
          </thead>
          <tbody>
            {qatorlar.map((q) => (
              <tr key={String(q.oy)}>
                <td>{oyNomi(oyQiymati(q.oy), til)}</td>
                <td className="ongga">{q.talabalar}</td>
                <td className="ongga">{pul(q.hisoblangan)}</td>
                <td className="ongga"><b>{pul(q.olingan)}</b></td>
                <td className="ongga">{pul(q.chegirma)}</td>
                <td className="ongga rang-qarzdor">{pul(q.qarz)}</td>
                <td className={`ongga ${foizSinfi(q.yigilish_foizi)}`}>
                  <b>{q.yigilish_foizi}%</b>
                </td>
                <td className="ustuncha-katak">
                  {/* Oddiy ustuncha: kutubxonasiz, chunki bitta
                      grafik uchun CRM bundle'iga recharts qo'shish
                      arzimaydi (u LMS'da bor, lekin import qilmaymiz). */}
                  <span className="ustuncha-fon">
                    <span
                      className="ustuncha-hisoblangan"
                      style={{ width: `${(Number(q.hisoblangan) / eng) * 100}%` }}
                    >
                      <span
                        className="ustuncha-olingan"
                        style={{
                          width: q.hisoblangan
                            ? `${(Number(q.olingan) / Number(q.hisoblangan)) * 100}%`
                            : "0%",
                        }}
                      />
                    </span>
                  </span>
                </td>
              </tr>
            ))}
            {!yuklanmoqda && qatorlar.length === 0 && (
              <tr><td colSpan={8} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
          {qatorlar.length > 0 && (
            <tfoot>
              <tr>
                <td colSpan={2}><b>{t("jami")}</b></td>
                <td className="ongga"><b>{pul(jami.hisoblangan)}</b></td>
                <td className="ongga"><b>{pul(jami.olingan)}</b></td>
                <td className="ongga">{pul(jami.chegirma)}</td>
                <td className="ongga rang-qarzdor"><b>{pul(jami.qarz)}</b></td>
                <td className={`ongga ${foizSinfi(jamiFoiz)}`}><b>{jamiFoiz}%</b></td>
                <td />
              </tr>
            </tfoot>
          )}
        </table>
      </div>

      <p className="kichik">{t("hisobot_izoh")}</p>
    </section>
  );
}

// ── Davr hisobotlari (video 28:50: "Hisobotlar" menyusi) ─────────────

const HISOBOT_TABLARI = ["dinamika", "tolovlar", "lidlar", "ketganlar", "bitiruvchilar"];

function DavrTanlash({ dan, setDan, gacha, setGacha, turi, filial }) {
  const { t } = useI18n();
  return (
    <div className="filtrlar">
      <label className="yonma">{t("dan")}<input type="date" value={dan} onChange={(e) => setDan(e.target.value)} /></label>
      <label className="yonma">{t("gacha")}<input type="date" value={gacha} onChange={(e) => setGacha(e.target.value)} /></label>
      {turi && (
        <button className="tugma tugma-sokin kichik-tugma" type="button"
                onClick={() => apiFayluniYuklab("/api/crm/hisobot/eksport/" + sorovSatri({ turi, dan, gacha, filial }))}>
          ⬇ Excel
        </button>
      )}
    </div>
  );
}

// ── Ketish hisoboti (video-TZ 2026-09-25, SoffCRM "Ketish hisoboti") ──

/** Kunlik ketishlar — oddiy ustunli grafik (kutubxonasiz, `Dinamika`dagi
 *  sabab bilan). Davrdagi HAR kun ko'rsatiladi: bo'sh kun ham ko'rinsin. */
function KunlikGrafik({ dan, gacha, qatorlar }) {
  const { t } = useI18n();
  const soni = Object.fromEntries(qatorlar.map((x) => [String(x.sana), x.soni]));
  const kunlar = [];
  for (let d = new Date(dan); d <= new Date(gacha) && kunlar.length < 93; d.setDate(d.getDate() + 1)) {
    kunlar.push(d.toISOString().slice(0, 10));
  }
  const eng = Math.max(1, ...qatorlar.map((x) => x.soni));
  return (
    <div className="kunlik-grafik" role="img" aria-label={t("ketish_dinamikasi")}>
      {kunlar.map((k) => (
        <div key={k} className="kunlik-ustun" title={`${sana(k)}: ${soni[k] || 0}`}>
          <span style={{ height: `${((soni[k] || 0) / eng) * 100}%` }}>{soni[k] ? soni[k] : ""}</span>
          <i>{k.slice(8, 10)}</i>
        </div>
      ))}
    </div>
  );
}

function KetishHisoboti() {
  const { t } = useI18n();
  const { tanlangan } = useFilial();
  const b = new Date();
  const [dan, setDan] = useState(`${b.getFullYear()}-${String(b.getMonth() + 1).padStart(2, "0")}-01`);
  const [gacha, setGacha] = useState(b.toISOString().slice(0, 10));
  const [f, setF] = useState({ q: "", kurs: "", guruh: "", oqituvchi: "", sabab_turi: "", chegirma: "" });
  const guruhlar = useSorov("/api/crm/guruhlar/" + sorovSatri({ filial: tanlangan }));
  const parametrlar = { dan, gacha, filial: tanlangan, ...f };
  const { malumot: d, yuklanmoqda, xato } = useSorov("/api/crm/hisobot/ketganlar/" + sorovSatri(parametrlar));
  const [eksportXato, setEksportXato] = useState("");

  const gv = guruhlar.malumot || [];
  const kurslar = [...new Map(gv.filter((g) => g.daraja).map((g) => [g.daraja.id, g.daraja.nomi])).entries()];
  const oqituvchilar = [...new Map(gv.filter((g) => g.oqituvchi_id).map((g) => [g.oqituvchi_id, g.oqituvchi])).entries()];
  const maydon = (k) => ({ value: f[k], onChange: (e) => setF((x) => ({ ...x, [k]: e.target.value })) });
  const jamiSabab = (d?.sabablar || []).reduce((s, x) => s + x.soni, 0);

  return (
    <>
      <div className="filtrlar">
        <label className="yonma">{t("dan")}<input type="date" value={dan} onChange={(e) => setDan(e.target.value)} /></label>
        <label className="yonma">{t("gacha")}<input type="date" value={gacha} onChange={(e) => setGacha(e.target.value)} /></label>
        <button className="tugma tugma-sokin kichik-tugma" type="button"
                onClick={() => apiFayluniYuklab("/api/crm/hisobot/eksport/" + sorovSatri({ turi: "ketganlar", ...parametrlar }))
                  .catch((e) => setEksportXato(e.message))}>
          ⬇ Excel
        </button>
      </div>
      {(xato || eksportXato) && <div className="xato">{xato || eksportXato}</div>}
      {yuklanmoqda && !d && <p className="kichik">{t("yuklanmoqda")}</p>}
      {d && (
        <>
          <div className="kataklar">
            <div className="katak" title={t("ketish_koeffitsienti_izoh")}>
              <span className="kichik">{t("ketish_koeffitsienti")}</span><b className="rang-qarzdor">{d.koeffitsient}%</b>
            </div>
            <div className="katak"><span className="kichik">{t("ketganlar_soni")}</span><b>{d.soni}</b></div>
            <div className="katak" title={t("yoqotilgan_daromad_izoh")}>
              <span className="kichik">{t("yoqotilgan_daromad")}</span><b className="rang-qarzdor">{pul(d.yoqotilgan_daromad)}</b>
            </div>
            <div className="katak" title={t("ortacha_umr_izoh")}>
              <span className="kichik">{t("ortacha_umr")}</span>
              <b>{d.ortacha_umr_oy !== null ? `${d.ortacha_umr_oy} ${t("oy")}` : "—"}</b>
            </div>
            <div className="katak"><span className="kichik">{t("bitirganlar")}</span><b className="rang-tolandi">{d.bitirganlar}</b></div>
          </div>

          <div className="hisobot-ikki">
            <div className="karta">
              <h3>{t("ketish_dinamikasi")}</h3>
              <KunlikGrafik dan={dan} gacha={gacha} qatorlar={d.dinamika} />
            </div>
            <div className="karta">
              <h3>{t("asosiy_ketish_sabablari")}</h3>
              {d.sabablar.length === 0 && <p className="kichik">{t("yozuv_yoq")}</p>}
              {d.sabablar.map((x) => (
                <div key={x.sabab_turi} className="sabab-qator">
                  <span>{t(`sabab_${x.sabab_turi}`)}</span>
                  <span className="sabab-chiziq">
                    <span style={{ width: `${(x.soni / jamiSabab) * 100}%` }} />
                  </span>
                  <b>{x.soni} <span className="kichik">({Math.round((x.soni / jamiSabab) * 100)}%)</span></b>
                </div>
              ))}
            </div>
          </div>

          <div className="hisobot-ikki">
            <div className="karta">
              <h3>{t("ichki_migratsiya")}</h3>
              <div className="kataklar">
                <div className="katak"><span className="kichik">{t("jami_ozgarishlar")}</span><b>{d.migratsiya.soni}</b></div>
                <div className="katak" title={t("ozgargandan_keyin_ketish_izoh")}>
                  <span className="kichik">{t("ozgargandan_keyin_ketish")}</span><b>{d.migratsiya.keyin_ketgan_foiz}%</b>
                </div>
              </div>
            </div>
            <div className="karta">
              <h3>{t("chegirmalar_tasiri")}</h3>
              <div className="kataklar">
                <div className="katak"><span className="kichik">{t("chegirmasi_bor")}</span><b>{d.chegirma.bor}</b></div>
                <div className="katak"><span className="kichik">{t("chegirmasiz")}</span><b>{d.chegirma.yoq}</b></div>
              </div>
            </div>
          </div>

          <div className="karta jadval-oram">
            <h3>{t("ketgan_talabalar_royxati")} <span className="belgi">{d.royxat.length}</span></h3>
            <div className="filtrlar">
              <input placeholder={t("qidiruv")} {...maydon("q")} />
              <select {...maydon("kurs")} aria-label={t("kurs")}>
                <option value="">{t("kurs")}: {t("hammasi")}</option>
                {kurslar.map(([id, nomi]) => <option key={id} value={id}>{nomi}</option>)}
              </select>
              <select {...maydon("guruh")} aria-label={t("guruh")}>
                <option value="">{t("guruh")}: {t("hammasi")}</option>
                {gv.map((g) => <option key={g.id} value={g.id}>{g.nomi}</option>)}
              </select>
              <select {...maydon("oqituvchi")} aria-label={t("oqituvchi")}>
                <option value="">{t("oqituvchi")}: {t("hammasi")}</option>
                {oqituvchilar.map(([id, ism]) => <option key={id} value={id}>{ism}</option>)}
              </select>
              <select {...maydon("sabab_turi")} aria-label={t("sabab")}>
                <option value="">{t("sabab")}: {t("hammasi")}</option>
                {["narx", "natija", "oqituvchi", "dars_jadvali", "joylashuv", "boshqa", "lidga"].map((k) => (
                  <option key={k} value={k}>{t(`sabab_${k}`)}</option>
                ))}
              </select>
              <select {...maydon("chegirma")} aria-label={t("chegirma")}>
                <option value="">{t("chegirma")}: {t("hammasi")}</option>
                <option value="1">{t("chegirmasi_bor")}</option>
                <option value="0">{t("chegirmasiz")}</option>
              </select>
            </div>
            <table>
              <thead>
                <tr>
                  <th>#</th><th>{t("talaba")}</th><th>{t("guruh")}</th><th>{t("kurs")}</th><th>{t("chegirma")}</th>
                  <th>{t("oqituvchi")}</th><th>{t("sabab")}</th><th>{t("ketgan_sana")}</th>
                  <th>{t("kim_chiqargan")}</th><th>{t("izoh")}</th>
                </tr>
              </thead>
              <tbody>
                {d.royxat.map((x, i) => (
                  <tr key={i}>
                    <td>{i + 1}</td>
                    <td>{x.talaba_id ? <Link className="havola" to={`/talabalar?talaba=${x.talaba_id}`}>{x.talaba}</Link> : x.talaba}</td>
                    <td>{x.guruh}</td>
                    <td>{x.kurs || "—"}</td>
                    <td>{x.chegirma_bor ? <span className="belgi">{t("bor")}</span> : "—"}</td>
                    <td>{x.oqituvchi || "—"}</td>
                    <td>{t(`sabab_${x.sabab_turi}`)}</td>
                    <td className="nowrap">{sana(x.sana)}</td>
                    <td>{x.kim || "—"}</td>
                    <td className="kichik" title={x.sabab}>{x.sabab || "—"}</td>
                  </tr>
                ))}
                {d.royxat.length === 0 && <tr><td colSpan={10} className="bosh">{t("yozuv_yoq")}</td></tr>}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}

function DavrHisoboti({ turi }) {
  const { t } = useI18n();
  const { tanlangan } = useFilial();
  const b = new Date();
  const [dan, setDan] = useState(`${b.getFullYear()}-${String(b.getMonth() + 1).padStart(2, "0")}-01`);
  const [gacha, setGacha] = useState(b.toISOString().slice(0, 10));
  const { malumot: d, yuklanmoqda, xato } = useSorov(`/api/crm/hisobot/${turi}/` + sorovSatri({ dan, gacha, filial: tanlangan }));
  const eksportTuri = ["tolovlar", "lidlar"].includes(turi) ? turi : null;

  return (
    <>
      <DavrTanlash dan={dan} setDan={setDan} gacha={gacha} setGacha={setGacha} turi={eksportTuri} filial={tanlangan} />
      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && !d && <p className="kichik">{t("yuklanmoqda")}</p>}
      {d && turi === "tolovlar" && (
        <>
          <div className="kataklar">
            <div className="katak"><span className="kichik">{t("olingan_pul")}</span><b className="rang-tolandi">{pul(d.jami)}</b></div>
            <div className="katak"><span className="kichik">{t("pul_qaytarish")}</span><b className="rang-qarzdor">{pul(d.qaytarish)}</b></div>
            <div className="katak"><span className="kichik">{t("chegirma")} / bonus</span><b>{pul(d.chegirma_bonus)}</b></div>
          </div>
          <div className="karta jadval-oram">
            <table>
              <thead><tr><th>{t("tolov_usuli")}</th><th className="ongga">{t("soni")}</th><th className="ongga">{t("summa")}</th></tr></thead>
              <tbody>
                {d.usullar.map((x) => (
                  <tr key={x.usul || "yoq"}><td>{x.usul ? t(`usul_${x.usul}`) : "—"}</td><td className="ongga">{x.soni}</td><td className="ongga">{pul(x.summa)}</td></tr>
                ))}
              </tbody>
            </table>
            <table>
              <thead><tr><th>{t("sana")}</th><th className="ongga">{t("soni")}</th><th className="ongga">{t("summa")}</th></tr></thead>
              <tbody>
                {d.kunlar.map((x) => (
                  <tr key={x.sana}><td>{sana(x.sana)}</td><td className="ongga">{x.soni}</td><td className="ongga">{pul(x.summa)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {d && turi === "lidlar" && (
        <>
          <div className="kataklar">
            <div className="katak"><span className="kichik">{t("jami")}</span><b>{d.jami}</b></div>
            <div className="katak"><span className="kichik">{t("oquvchi_boldi")}</span><b className="rang-tolandi">{d.qoshildi}</b></div>
            <div className="katak"><span className="kichik">{t("konversiya")}</span>
              <b>{d.jami ? Math.round((d.qoshildi / d.jami) * 1000) / 10 : 0}%</b></div>
          </div>
          <div className="karta jadval-oram">
            <table>
              <thead><tr><th>{t("manba")}</th><th className="ongga">{t("jami")}</th><th className="ongga">{t("oquvchi_boldi")}</th><th className="ongga">{t("konversiya")}</th></tr></thead>
              <tbody>
                {d.manbalar.map((x) => (
                  <tr key={x.manba}><td>{x.manba}</td><td className="ongga">{x.jami}</td><td className="ongga">{x.qoshildi}</td><td className="ongga">{x.konversiya}%</td></tr>
                ))}
              </tbody>
            </table>
            <table>
              <thead><tr><th>{t("holat")}</th><th className="ongga">{t("soni")}</th></tr></thead>
              <tbody>
                {d.holatlar.map((x) => <tr key={x.holat}><td>{t(`lid_${x.holat}`)}</td><td className="ongga">{x.soni}</td></tr>)}
              </tbody>
            </table>
          </div>
        </>
      )}
      {d && turi === "bitiruvchilar" && (
        <div className="karta jadval-oram">
          <table>
            <thead><tr><th>{t("guruh")}</th><th>{t("kurs")}</th><th>{t("oqituvchi")}</th><th>{t("tugash_sana")}</th><th>{t("talabalar")}</th></tr></thead>
            <tbody>
              {d.guruhlar.map((g) => (
                <tr key={g.guruh_id}><td>{g.guruh}</td><td>{g.kurs || "—"}</td><td>{g.oqituvchi || "—"}</td><td>{sana(g.tugash_sana)}</td><td>{g.talabalar.join(", ") || "—"}</td></tr>
              ))}
              {d.guruhlar.length === 0 && <tr><td colSpan={5} className="bosh">{t("yozuv_yoq")}</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

export default function Hisobotlar() {
  const { t } = useI18n();
  // `?tab=ketganlar` — bosh sahifadagi "Shu oy ketganlar" kartochkasidan.
  const [params] = useSearchParams();
  const [tab, setTab] = useState(() => (HISOBOT_TABLARI.includes(params.get("tab")) ? params.get("tab") : "dinamika"));
  return (
    <section>
      <h1>{t("hisobotlar")}</h1>
      <div className="tablar">
        {HISOBOT_TABLARI.map((x) => (
          <button key={x} type="button" className={tab === x ? "tab faol" : "tab"} onClick={() => setTab(x)}>
            {t(`hisobot_${x}`)}
          </button>
        ))}
      </div>
      {tab === "dinamika" ? <Dinamika /> : tab === "ketganlar" ? <KetishHisoboti /> : <DavrHisoboti key={tab} turi={tab} />}
    </section>
  );
}
