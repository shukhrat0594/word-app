// Ota-ona boti (Telegram, @UtmostParentsBot): ota-ona so'rovlari, ulangan ota-onalar va
// xabarlar QACHON yuborilishi sozlamasi (video-TZ 2026-10-04).
//
// Avtomatik ulanmagan ota-onani admin shu yerda farzandiga ulaydi yoki rad etadi;
// ota-onaga botda darhol xabar boradi.

import { useEffect, useState } from "react";

import { api } from "../api.js";
import { sana } from "../format.js";
import { useI18n } from "../i18n.jsx";
import { useRuxsat } from "../profilContext.jsx";
import { useSorov } from "../soragich.js";

const TABLAR = ["sorovlar", "ulanganlar", "sozlama"];

function TalabaQatori({ x }) {
  return (
    <span>
      <b>{x.ism}</b>
      {x.tugilgan_sana ? ` · ${sana(x.tugilgan_sana)}` : ""}
      {x.guruhlar?.length ? ` · ${x.guruhlar.join(", ")}` : ""}
    </span>
  );
}

function SorovKartasi({ s, onHal, ruxsatUlash }) {
  const { t } = useI18n();
  const [tanlangan, setTanlangan] = useState(s.nomzodlar.length === 1 ? s.nomzodlar[0].id : null);
  const [qidiruv, setQidiruv] = useState("");
  const [topilgan, setTopilgan] = useState([]);
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  useEffect(() => {
    if (qidiruv.trim().length < 2) {
      setTopilgan([]);
      return undefined;
    }
    const id = setTimeout(() => {
      api(`/api/crm/otabot/talaba-qidiruv/?q=${encodeURIComponent(qidiruv.trim())}`)
        .then(setTopilgan)
        .catch(() => setTopilgan([]));
    }, 300);
    return () => clearTimeout(id);
  }, [qidiruv]);

  async function hal(amal) {
    if (amal === "rad" && !window.confirm(t("ob_rad_tasdiq"))) return;
    setXato("");
    setBand(true);
    try {
      await api(`/api/crm/otabot/sorovlar/${s.id}/hal/`, {
        method: "POST", body: amal === "ulash" ? { amal, talaba_id: tanlangan } : { amal },
      });
      onHal();
    } catch (e) {
      setXato(e.message);
    } finally {
      setBand(false);
    }
  }

  const royxat = [...s.nomzodlar, ...topilgan.filter((x) => !s.nomzodlar.some((n) => n.id === x.id))];
  return (
    <div className="karta ob-sorov">
      <div className="ob-sorov-bosh">
        <div>
          <b>{s.abonent.ism || "—"}</b> {s.abonent.username && <span className="kichik">@{s.abonent.username}</span>}
          <div className="kichik">{s.abonent.telefon || "—"} · {sana(s.yaratilgan)}</div>
        </div>
        <div>
          <div className="kichik">{t("ob_farzand_yozgan")}</div>
          <b>{s.farzand_ismi}</b> · {s.tugilgan_sana}
        </div>
      </div>

      <div className="kichik ob-sarlavha">{t("ob_nomzodlar")}</div>
      {royxat.length === 0 && <p className="kichik">{t("ob_nomzod_yoq")}</p>}
      {royxat.map((x) => (
        <label key={x.id} className="yonma ob-nomzod">
          <input type="radio" name={`s${s.id}`} checked={tanlangan === x.id} onChange={() => setTanlangan(x.id)} />
          <TalabaQatori x={x} />
        </label>
      ))}
      <input className="ob-qidiruv" placeholder={t("ob_qidirish")} value={qidiruv}
             onChange={(e) => setQidiruv(e.target.value)} />

      {xato && <div className="xato">{xato}</div>}
      {ruxsatUlash && (
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" disabled={band} onClick={() => hal("rad")}>
            {t("ob_rad")}
          </button>
          <button className="tugma" type="button" disabled={band || !tanlangan} onClick={() => hal("ulash")}>
            {t("ob_ulash")}
          </button>
        </div>
      )}
    </div>
  );
}

function Sorovlar() {
  const { t } = useI18n();
  const ruxsat = useRuxsat();
  const { malumot, yuklanmoqda, xato, yangila } = useSorov("/api/crm/otabot/sorovlar/");
  if (yuklanmoqda && !malumot) return <p className="kichik">{t("yuklanmoqda")}</p>;
  if (xato) return <div className="xato">{xato}</div>;
  if (!malumot?.length) return <p className="kichik">{t("ob_yangi_yoq")}</p>;
  return malumot.map((s) => (
    <SorovKartasi key={s.id} s={s} onHal={yangila} ruxsatUlash={ruxsat("otabot.ulash")} />
  ));
}

function Ulanganlar() {
  const { t } = useI18n();
  const ruxsat = useRuxsat();
  const { malumot, yuklanmoqda, xato, yangila } = useSorov("/api/crm/otabot/abonentlar/");
  const [amalXato, setAmalXato] = useState("");

  async function uz(id) {
    if (!window.confirm(t("ob_uzish_tasdiq"))) return;
    setAmalXato("");
    try {
      await api(`/api/crm/otabot/boglanishlar/${id}/uzish/`, { method: "POST", body: {} });
      yangila();
    } catch (e) {
      setAmalXato(e.message);
    }
  }

  if (yuklanmoqda && !malumot) return <p className="kichik">{t("yuklanmoqda")}</p>;
  if (xato) return <div className="xato">{xato}</div>;
  if (!malumot?.length) return <p className="kichik">{t("ob_ulanganlar_yoq")}</p>;
  return (
    <div className="jadval-oram">
      {amalXato && <div className="xato">{amalXato}</div>}
      <table>
        <thead>
          <tr><th>{t("ob_ota_ona")}</th><th>Telegram</th><th>{t("ob_farzandlar")}</th><th /></tr>
        </thead>
        <tbody>
          {malumot.map((a) => (
            <tr key={a.id}>
              <td>{a.ism || "—"}<div className="kichik">{a.telefon}</div></td>
              <td>{a.username ? `@${a.username}` : "—"}{!a.faol && <div className="kichik">⏸ stop</div>}</td>
              <td>
                {a.farzandlar.map((f) => (
                  <div key={f.boglanish_id} className="ob-farzand">
                    <TalabaQatori x={f.talaba} /> <span className="kichik">({f.usul_nomi})</span>
                    {ruxsat("otabot.ulash") && (
                      <button className="havola" type="button" onClick={() => uz(f.boglanish_id)}>
                        {t("ob_uzish")}
                      </button>
                    )}
                  </div>
                ))}
              </td>
              <td />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const KUNLAR = [0, 1, 2, 3, 4, 5, 6];

function KunTanlash({ qiymat, onChange, disabled }) {
  const { t } = useI18n();
  const almashtir = (k) => onChange(qiymat.includes(k) ? qiymat.filter((x) => x !== k) : [...qiymat, k].sort());
  return (
    <span className="ob-kunlar">
      {KUNLAR.map((k) => (
        <label key={k} className="yonma">
          <input type="checkbox" checked={qiymat.includes(k)} disabled={disabled} onChange={() => almashtir(k)} />
          {t(`ob_kun_${k}`)}
        </label>
      ))}
    </span>
  );
}

function Sozlama() {
  const { t } = useI18n();
  const ruxsat = useRuxsat();
  const { malumot, yuklanmoqda, xato, yangila } = useSorov("/api/crm/otabot/sozlama/");
  const [forma, setForma] = useState(null);
  const [holat, setHolat] = useState("");
  const [saqlashXato, setSaqlashXato] = useState("");
  const tahrir = ruxsat("otabot.sozlama");

  useEffect(() => {
    if (malumot) setForma(malumot);
  }, [malumot]);

  if (yuklanmoqda && !forma) return <p className="kichik">{t("yuklanmoqda")}</p>;
  if (xato) return <div className="xato">{xato}</div>;
  if (!forma) return null;

  const o = (k, v) => { setHolat(""); setForma({ ...forma, [k]: v }); };
  const Belgi = ({ k, nom }) => (
    <label className="yonma">
      <input type="checkbox" checked={forma[k]} disabled={!tahrir} onChange={(e) => o(k, e.target.checked)} /> {nom}
    </label>
  );
  const Soat = ({ k }) => (
    <input type="time" value={forma[k]} disabled={!tahrir} onChange={(e) => o(k, e.target.value)} />
  );

  async function saqla() {
    setSaqlashXato("");
    try {
      await api("/api/crm/otabot/sozlama/", { method: "PUT", body: forma });
      setHolat(t("ob_saqlandi"));
      yangila();
    } catch (e) {
      setSaqlashXato(e.message);
    }
  }

  return (
    <div className="karta ob-sozlama">
      <h3>{t("ob_davomat")}</h3>
      <div className="ob-qator">
        <Belgi k="davomat_yoqilgan" nom={t("faol")} />
        <Belgi k="davomat_kelmadi" nom={t("ob_kelmadi")} />
        <Belgi k="davomat_kechikdi" nom={t("ob_kechikdi")} />
        <Belgi k="davomat_sababli" nom={t("ob_sababli")} />
      </div>

      <h3>{t("ob_tolov")}</h3>
      <div className="ob-qator"><Belgi k="tolov_yoqilgan" nom={t("faol")} /></div>

      <h3>{t("ob_qarz")}</h3>
      <div className="ob-qator">
        <Belgi k="qarz_yoqilgan" nom={t("faol")} />
        <KunTanlash qiymat={forma.qarz_kunlari} disabled={!tahrir} onChange={(v) => o("qarz_kunlari", v)} />
        <span>{t("ob_soat")}: <Soat k="qarz_soati" /></span>
      </div>

      <h3>{t("ob_natija")}</h3>
      <div className="ob-qator">
        <Belgi k="natija_yoqilgan" nom={t("faol")} />
        <KunTanlash qiymat={forma.natija_kunlari} disabled={!tahrir} onChange={(v) => o("natija_kunlari", v)} />
        <span>{t("ob_soat")}: <Soat k="natija_soati" /></span>
      </div>

      <h3>{t("ob_tinch")}</h3>
      <div className="ob-qator">
        <span>{t("ob_boshi")}: <Soat k="tinch_boshi" /></span>
        <span>{t("ob_oxiri")}: <Soat k="tinch_oxiri" /></span>
      </div>
      <p className="kichik">{t("ob_tinch_izoh")}</p>

      {saqlashXato && <div className="xato">{saqlashXato}</div>}
      {tahrir && (
        <div className="oyna-tugmalar">
          {holat && <span className="kichik">{holat}</span>}
          <button className="tugma" type="button" onClick={saqla}>{t("saqlash")}</button>
        </div>
      )}
    </div>
  );
}

export default function OtaBot() {
  const { t } = useI18n();
  const [tab, setTab] = useState("sorovlar");
  return (
    <div>
      <h1>{t("otabot")}</h1>
      <div className="tablar">
        {TABLAR.map((x) => (
          <button key={x} type="button" className={tab === x ? "tab faol" : "tab"} onClick={() => setTab(x)}>
            {t(`ob_${x}`)}
          </button>
        ))}
      </div>
      {tab === "sorovlar" && <Sorovlar />}
      {tab === "ulanganlar" && <Ulanganlar />}
      {tab === "sozlama" && <Sozlama />}
    </div>
  );
}
