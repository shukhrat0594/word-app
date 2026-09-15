// Talabalar (TZ 6.5) — ro'yxat va talaba kartasi.

import { useState } from "react";

import Eslatmalar from "../Eslatmalar.jsx";
import { useFilial } from "../filialContext.jsx";
import { useProfil } from "../profilContext.jsx";
import { balansMatn, balansSinfi, pul, sana } from "../format.js";
import { api } from "../api.js";
import { useI18n } from "../i18n.jsx";
import { sorovSatri, useSorov } from "../soragich.js";
import QaytarishOynasi from "../QaytarishOynasi.jsx";
import TolovOynasi from "../TolovOynasi.jsx";

const HAFTA = ["Du", "Se", "Chor", "Pay", "Ju", "Sha", "Yak"];

// ── Darslar taqvimi ─────────────────────────────────────────────────

function Taqvim({ kunlar }) {
  const { t } = useI18n();
  if (!kunlar?.length) return <p className="kichik">{t("yozuv_yoq")}</p>;
  // Legenda ATAYLAB bor: rangli kataklar o'z-o'zidan tushunarli emas,
  // ayniqsa kulrang "kutilayotgan" — u qarz emas, hali kelmagan oy.
  const legenda = ["tolandi", "qisman", "qarzdor", "kutilayotgan"];

  return (
    <>
      <div className="taqvim">
        {kunlar.map((k) => (
          <span key={k.sana} className={`taqvim-kun holat-${k.holat}`} title={sana(k.sana)}>
            {String(k.sana).slice(8, 10)}
          </span>
        ))}
      </div>
      <div className="taqvim-legenda">
        {legenda.map((h) => (
          <span key={h}>
            <i className={`legenda-nuqta holat-${h}`} /> {t(`holat_${h}`)}
          </span>
        ))}
      </div>
    </>
  );
}

/** Bitta ko'rsatkich kartasi. Ma'lumot yo'q bo'lsa "—" chiqadi va
 *  rang berilmaydi — 0% deb ko'rsatish "yomon natija" degan yolg'on
 *  taassurot berardi. */
function Natija({ sarlavha, qiymat, foiz = false, sof = false, izoh = null }) {
  const bor = qiymat !== null && qiymat !== undefined;
  const sinf = !bor || sof ? "" : foizSinfi(foiz ? qiymat : qiymat * 10);
  return (
    <div className="katak">
      <span className="kichik">{sarlavha}</span>
      <b className={sinf}>
        {bor ? `${qiymat}${foiz ? "%" : ""}` : "—"}
      </b>
      {izoh && <span className="kichik">{izoh}</span>}
    </div>
  );
}

/** 80%+ yaxshi, 60%+ o'rtacha, pastda yomon. */
function foizSinfi(foiz) {
  if (foiz === null || foiz === undefined) return "";
  if (foiz >= 80) return "rang-tolandi";
  if (foiz >= 60) return "rang-qisman";
  return "rang-qarzdor";
}

// ── Talaba kartasi ──────────────────────────────────────────────────

function Karta({ talabaId, onOrqaga }) {
  const { t } = useI18n();
  const profil = useProfil();
  const { malumot, yuklanmoqda, xato, yangila } = useSorov(`/api/crm/talaba/${talabaId}/`);
  const [tolovHisobi, setTolovHisobi] = useState(null);
  const [qaytarishGuruhi, setQaytarishGuruhi] = useState(null);

  async function tolovniOchir(id) {
    if (!window.confirm(t("tolov_ochirish_tasdiq"))) return;
    await api(`/api/crm/tolov/${id}/`, { method: "DELETE" });
    yangila();
  }

  if (yuklanmoqda) return <p className="kichik">{t("yuklanmoqda")}</p>;
  if (xato) return <div className="xato">{xato}</div>;
  if (!malumot) return null;

  const talaba = malumot;

  return (
    <section>
      <button className="havola" type="button" onClick={onOrqaga}>← {t("talabalar")}</button>
      <h1>{talaba.ism}</h1>

      <div className="karta">
        <div className="qator">
          <span className="kichik">{t("telefon")}</span>
          <span>{talaba.telefon || "—"}</span>
        </div>
        <div className="qator">
          <span className="kichik">{t("ota_ona_telefon")}</span>
          <span>{talaba.ota_ona_telefon || "—"}</span>
        </div>
        <div className="qator">
          <span className="kichik">{t("umumiy_balans")}</span>
          <b className={balansSinfi(talaba.balans_jami)}>{balansMatn(talaba.balans_jami)}</b>
        </div>
      </div>

      {/* Umumiy o'quv natijasi — LMS'da hosil bo'ladi, bu yerda faqat
          ko'rsatiladi (SoffCRM kartasidagi "Baho" o'rnida, lekin bitta
          son emas, to'rt ko'nikma bo'yicha). */}
      <div className="karta">
        <div className="karta-sarlavha">
          <h2>{t("tab_natijalar")}</h2>
          <span className="belgi">{t("faqat_oqish")}</span>
        </div>
        <div className="kataklar">
          <Natija sarlavha="Writing" qiymat={talaba.natijalar?.writing_band} />
          <Natija sarlavha="Speaking" qiymat={talaba.natijalar?.speaking_band} />
          <Natija sarlavha="Listening" qiymat={talaba.natijalar?.listening_foiz} foiz />
          <Natija sarlavha="Reading" qiymat={talaba.natijalar?.reading_foiz} foiz />
          <Natija sarlavha={t("mashqlar")} qiymat={talaba.natijalar?.mashq_soni} sof />
          <Natija
            sarlavha={t("davomat")}
            qiymat={talaba.natijalar?.davomat_foizi}
            foiz
            izoh={
              talaba.natijalar && talaba.natijalar.keldi + talaba.natijalar.kelmadi > 0
                ? `${talaba.natijalar.keldi}/${talaba.natijalar.keldi + talaba.natijalar.kelmadi}`
                : null
            }
          />
        </div>
      </div>

      {talaba.guruhlar.map((g) => (
        <div className="karta" key={g.id}>
          <div className="karta-sarlavha">
            <div>
              <h2>{g.guruh}</h2>
              <p className="kichik">
                {g.jadval.map((j) => `${HAFTA[j.hafta_kuni]} ${j.boshlanish_vaqti}`).join(", ") || "—"}
                {" · "}{t(`holat_${g.holat}`)}
                {" · "}{g.narx ? pul(g.narx) : "—"}
              </p>
            </div>
            <div className="ongga">
              <b className={balansSinfi(g.balans)}>{balansMatn(g.balans)}</b>
              {g.keyingi_tolov && (
                <div className="kichik">
                  {t("keyingi_tolov_sanasi")}: <b>{sana(g.keyingi_tolov)}</b>
                </div>
              )}
            </div>
          </div>

          <h3>{t("darslar_taqvimi")}</h3>
          <Taqvim kunlar={g.darslar_taqvimi} />

          <div className="oyna-tugmalar">
            <button className="tugma tugma-sokin" type="button"
                    onClick={() => setQaytarishGuruhi(g)}>
              {t("pul_qaytarish")}
            </button>
          </div>
        </div>
      ))}

      <div className="karta">
        <h2>{t("tab_eslatmalar")}</h2>
        <Eslatmalar talabaId={talaba.id} profilId={profil?.id} />
      </div>

      <div className="karta">
        <h2>{t("tolov_tarixi")}</h2>
        <div className="jadval-oram">
          <table>
            <thead>
              <tr>
                <th>{t("sana")}</th>
                <th>{t("qaysi_oy")}</th>
                <th>{t("turi")}</th>
                <th className="ongga">{t("summa")}</th>
                <th>{t("guruh")}</th>
                <th>{t("izoh")}</th>
                <th>{t("kim")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {talaba.tolovlar.map((x) => (
                <tr key={x.id}>
                  <td>{sana(x.sana)}</td>
                  <td>{x.oy ? String(x.oy).slice(0, 7) : "—"}</td>
                  <td>{x.turi_nomi}</td>
                  <td className={`ongga ${x.turi === "qaytarish" ? "rang-qarzdor" : ""}`}>
                    {x.turi === "qaytarish" ? "−" : ""}{pul(x.summa)}
                  </td>
                  <td>{x.guruh}</td>
                  <td>{x.izoh}</td>
                  <td>{x.kim || "—"}</td>
                  <td>
                    {/* Pul yozuvini o'chirish — FAQAT owner (backend ham
                        shunday tekshiradi). Chegirmani bekor qilish ham
                        shu yo'l bilan: yozuv o'chgach qarz tiklanadi. */}
                    {profil?.is_owner && (
                      <button className="havola" type="button"
                              onClick={() => tolovniOchir(x.id)}>
                        {t("ochirish")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {talaba.tolovlar.length === 0 && (
                <tr><td colSpan={8} className="bosh">{t("yozuv_yoq")}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="karta">
        <h2>{t("hisoblangan")}</h2>
        <div className="jadval-oram">
          <table>
            <thead>
              <tr>
                <th>{t("qaysi_oy")}</th>
                <th>{t("guruh")}</th>
                <th className="ongga">{t("summa")}</th>
                <th className="ongga">{t("tolangan")}</th>
                <th className="ongga">{t("qoldiq")}</th>
                <th>{t("holat")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {talaba.hisoblar.map((h) => (
                <tr key={h.id}>
                  <td>{String(h.oy).slice(0, 7)}</td>
                  <td>{h.guruh}</td>
                  <td className="ongga">{pul(h.summa)}</td>
                  <td className="ongga">{pul(h.tolangan)}</td>
                  <td className="ongga">{pul(h.qoldiq)}</td>
                  <td><span className={`holat holat-${h.holat}`}>{t(`holat_${h.holat}`)}</span></td>
                  <td>
                    {h.holat !== "tolandi" && (
                      <button className="tugma kichik-tugma" type="button"
                              onClick={() => setTolovHisobi({ ...h, talaba: talaba.ism })}>
                        {t("tolov_qilish")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {talaba.hisoblar.length === 0 && (
                <tr><td colSpan={7} className="bosh">{t("yozuv_yoq")}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {tolovHisobi && (
        <TolovOynasi
          hisob={tolovHisobi}
          onYopish={() => setTolovHisobi(null)}
          onSaqlandi={({ yopmasdan }) => {
            yangila();
            if (!yopmasdan) setTolovHisobi(null);
          }}
        />
      )}
      {qaytarishGuruhi && (
        <QaytarishOynasi
          talabaId={talaba.id}
          talabaIsmi={talaba.ism}
          guruhId={qaytarishGuruhi.guruh_id}
          guruhNomi={qaytarishGuruhi.guruh}
          balans={qaytarishGuruhi.balans}
          onYopish={() => setQaytarishGuruhi(null)}
          onSaqlandi={yangila}
        />
      )}
    </section>
  );
}

// ── Sahifa ──────────────────────────────────────────────────────────

export default function Talabalar() {
  const { t } = useI18n();
  const { tanlangan } = useFilial();
  const [qidiruv, setQidiruv] = useState("");
  const [holat, setHolat] = useState("");
  const [ochilgan, setOchilgan] = useState(null);

  // Ro'yxat `Hisob`dan EMAS, a'zoliklardan yig'iladi: sinov va
  // muzlatilgan talabaga hisob ochilmaydi, lekin ular ham ko'rinishi
  // kerak — aks holda admin ularni topa olmaydi va holatini
  // o'zgartira olmaydi.
  const { malumot, yuklanmoqda, xato } = useSorov(
    "/api/crm/talabalar/" + sorovSatri({ filial: tanlangan, q: qidiruv, holat })
  );

  if (ochilgan) return <Karta talabaId={ochilgan} onOrqaga={() => setOchilgan(null)} />;

  const royxat = malumot || [];

  return (
    <section>
      <h1>{t("talabalar")}</h1>

      <div className="filtrlar">
        <input placeholder={t("qidiruv")} value={qidiruv} onChange={(e) => setQidiruv(e.target.value)} />
        <select value={holat} onChange={(e) => setHolat(e.target.value)}>
          <option value="">{t("barcha_holatlar")}</option>
          {["sinov", "faol", "muzlatilgan", "arxiv"].map((h) => (
            <option key={h} value={h}>{t(`holat_${h}`)}</option>
          ))}
        </select>
        <span className="kichik">{royxat.length}</span>
      </div>

      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      <div className="karta jadval-oram">
        <table>
          <thead>
            <tr>
              <th>{t("talaba")}</th>
              <th>{t("telefon")}</th>
              <th>{t("guruhlar")}</th>
              <th className="ongga">{t("balans")}</th>
            </tr>
          </thead>
          <tbody>
            {royxat.map((x) => (
              <tr key={x.id}>
                <td>
                  <button className="havola" type="button" onClick={() => setOchilgan(x.id)}>
                    {x.ism}
                  </button>
                </td>
                <td>{x.telefon || "—"}</td>
                <td>
                  {x.guruhlar.map((g) => (
                    <span key={g.azolik_moliya_id} className="guruh-belgi">
                      {g.guruh}
                      {g.holat !== "faol" && <i> ({t(`holat_${g.holat}`)})</i>}
                    </span>
                  ))}
                </td>
                <td className={`ongga ${balansSinfi(x.balans)}`}>{balansMatn(x.balans)}</td>
              </tr>
            ))}
            {!yuklanmoqda && royxat.length === 0 && (
              <tr><td colSpan={4} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
