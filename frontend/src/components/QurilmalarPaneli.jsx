import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";

/** Qurilma limiti (2026-10-20) — bitta foydalanuvchining qurilmalari, limiti,
 * kutilayotgan so'rovlari va jurnali (owner/admin). Foydalanuvchilar,
 * Talabalar, Xodimlar qatoridagi tugma va `/qurilma-sorovlari` sahifasi
 * shuni ko'rsatadi. Backend: `accounts/qurilma_views.py`. */

function vaqt(s) {
  return s ? new Date(s).toLocaleString([], { dateStyle: "short", timeStyle: "short" }) : "—";
}

export default function QurilmalarPaneli({ userId, onOzgardi }) {
  const { t } = useI18n();
  const [m, setM] = useState(null);
  const [limit, setLimit] = useState("");
  const [tanlov, setTanlov] = useState({});
  const [band, setBand] = useState(false);
  const [xato, setXato] = useState("");
  const yol = `/api/foydalanuvchilar/${userId}/qurilmalar/`;

  function qoy(d) {
    setM(d);
    setLimit(String(d.limit));
  }

  useEffect(() => {
    api(yol).then(qoy).catch((e) => setXato(e.data?.detail || t("xato_yuz_berdi")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  async function bajar(ish) {
    setBand(true);
    setXato("");
    try {
      qoy(await ish());
      onOzgardi?.();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  const limitSaqla = () =>
    bajar(async () => {
      await api(`/api/foydalanuvchilar/${userId}/qurilma-limit/`, { method: "POST", body: { limit: Number(limit) } });
      return api(yol);
    });

  function ochir(q) {
    if (!window.confirm(t("qurilma_ochirish_tasdiq").replace("{nom}", q.nom))) return;
    bajar(() => api(yol, { method: "POST", body: { amal: "ochir", k: q.k } }));
  }

  function blokla(q) {
    if (!window.confirm(t("qurilma_bloklash_tasdiq").replace("{nom}", q.nom))) return;
    bajar(() => api(yol, { method: "POST", body: { amal: "blokla", k: q.k } }));
  }

  const qaror = (sorov, amal) =>
    bajar(() => api(`/api/qurilma-sorovlari/${sorov.id}/qaror/`, { method: "POST", body: { amal, k: tanlov[sorov.id] } }));

  if (!m) return xato ? <div className="xato-xabar">{xato}</div> : <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;
  if (m.owner) return <p className="izoh">{t("qurilma_owner_cheklovsiz")}</p>;

  const limitSon = Number(limit);
  const holatNomi = {
    ruxsat: t("qurilma_holat_ruxsat"),
    rad: t("qurilma_holat_rad"),
    avto: t("qurilma_holat_avto"),
    brauzer: t("qurilma_holat_brauzer"),
    blok: t("qurilma_holat_blok"),
  };

  return (
    <div style={{ display: "grid", gap: 14 }}>
      {xato && <div className="xato-xabar">{xato}</div>}

      <label style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }} title={t("qurilma_limiti_izoh")}>
        <span>{t("qurilma_limiti")}:</span>
        <input
          id={`qurilma-limit-${userId}`}
          type="number"
          min={1}
          value={limit}
          onChange={(e) => setLimit(e.target.value)}
          style={{ width: 80 }}
        />
        <button
          type="button"
          className="tugma kichik"
          onClick={limitSaqla}
          disabled={band || !Number.isInteger(limitSon) || limitSon < 1 || limitSon === m.limit}
        >
          {t("saqlash")}
        </button>
      </label>

      <div>
        <strong>{t("qurilmalar")} ({m.qurilmalar.length}/{m.limit})</strong>
        {m.qurilmalar.length === 0 ? (
          <p className="izoh" style={{ margin: "4px 0 0" }}>{t("qurilma_royxat_bosh")}</p>
        ) : (
          <div style={{ display: "grid", gap: 6, marginTop: 6 }}>
            {m.qurilmalar.map((q, i) => (
              <div key={q.k} style={{ display: "flex", gap: 8, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
                <span style={{ minWidth: 0 }}>
                  {i + 1}. {q.nom}
                  {q.faol && <span className="chip bor" style={{ marginLeft: 6 }}>{t("qurilma_hozir_ochiq")}</span>}
                  <span className="izoh" style={{ display: "block" }}>
                    {t("qurilma_qoshilgan")}: {vaqt(q.qoshilgan)} · {t("qurilma_oxirgi")}: {vaqt(q.oxirgi)}
                  </span>
                  {/* 2026-10-26: bitta qurilmadagi brauzerlar (Chrome, Telegram...) — birga ochiq turadi */}
                  <span className="izoh" style={{ display: "block" }}>
                    {t("qurilma_brauzerlar")}:{" "}
                    {q.brauzerlar
                      .map((b) => `${b.nom || t("qurilma_brauzer_nomalum")} (${vaqt(b.oxirgi)})`)
                      .join(", ")}
                  </span>
                </span>
                <span style={{ display: "flex", gap: 6 }}>
                  <button type="button" className="tugma ikkinchi kichik" onClick={() => ochir(q)} disabled={band}>
                    {t("ochirish")}
                  </button>
                  <button type="button" className="tugma ikkinchi kichik" onClick={() => blokla(q)} disabled={band}>
                    {t("qurilma_bloklash")}
                  </button>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {m.sorovlar.map((s) => (
        <div key={s.id} className="karta" style={{ display: "grid", gap: 8, borderColor: "var(--ogoh)" }}>
          <strong>{t("qurilma_sorov_sarlavha").replace("{nom}", s.nom)}</strong>
          <span className="izoh">
            {vaqt(s.oxirgi_urinish)} · {t("qurilma_urinishlar").replace("{n}", s.urinishlar)} · {t("qurilma_oy_almashtirish").replace("{n}", m.oy_almashtirishlari)}
          </span>
          {m.qurilmalar.length > 0 && (
            <div style={{ display: "grid", gap: 4 }}>
              <span className="izoh">{t("qurilma_qaysi_orniga")}</span>
              {m.qurilmalar.map((q) => (
                <label key={q.k} style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <input
                    type="radio"
                    name={`orniga-${s.id}`}
                    checked={tanlov[s.id] === q.k}
                    onChange={() => setTanlov((v) => ({ ...v, [s.id]: q.k }))}
                  />
                  {q.nom} <span className="izoh">({t("qurilma_oxirgi")}: {vaqt(q.oxirgi)})</span>
                </label>
              ))}
            </div>
          )}
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <button type="button" className="tugma kichik" onClick={() => qaror(s, "almashtir")} disabled={band || !tanlov[s.id]}>
              {t("qurilma_orniga_ruxsat")}
            </button>
            <button type="button" className="tugma ikkinchi kichik" onClick={() => qaror(s, "limit")} disabled={band}>
              {t("qurilma_limitni_oshir").replace("{n}", Math.max(m.limit, m.qurilmalar.length) + 1)}
            </button>
            <button type="button" className="tugma ikkinchi kichik" onClick={() => qaror(s, "rad")} disabled={band}>
              {t("qurilma_rad_etish")}
            </button>
          </div>
        </div>
      ))}

      {/* 2026-10-26 (Shuhrat): rad etilgan qurilma 24 soat bloklanadi (2026-10-27:
          admin «Bloklash» bilan bloklagani — muddatsiz; bo'lim har doim ko'rinadi) — admin
          blokdan chiqarsa, so'rov yana kutilayotganlarga qaytadi va yuqoridagi
          qaror tugmalari bilan hal qilinadi. */}
      <div>
        <strong>{t("qurilma_bloklangan")}</strong>
        {m.bloklangan.length === 0 ? (
          <p className="izoh" style={{ margin: "4px 0 0" }}>{t("qurilma_bloklangan_yoq")}</p>
        ) : (
          <div style={{ display: "grid", gap: 6, marginTop: 6 }}>
            {m.bloklangan.map((s) => (
              <div key={s.id} style={{ display: "flex", gap: 8, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
                <span style={{ minWidth: 0 }}>
                  {s.nom}
                  <span className="izoh" style={{ display: "block" }}>
                    {holatNomi[s.holat]}: {vaqt(s.hal_vaqti)}
                    {s.hal_qildi && ` — ${s.hal_qildi}`}
                  </span>
                </span>
                <button type="button" className="tugma ikkinchi kichik" onClick={() => qaror(s, "blokdan_chiqar")} disabled={band}>
                  {t("qurilma_blokdan_chiqar")}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {m.jurnal.length > 0 && (
        <div>
          <strong>{t("qurilma_jurnal")}</strong>
          <span className="izoh"> · {t("qurilma_oy_almashtirish").replace("{n}", m.oy_almashtirishlari)}</span>
          <div style={{ display: "grid", gap: 2, marginTop: 4 }}>
            {m.jurnal.map((j) => (
              <span key={j.id} className="izoh">
                {vaqt(j.hal_vaqti || j.yaratilgan)} — {holatNomi[j.holat] || j.holat}: {j.nom}
                {j.almashtirilgan_nom && ` (${t("qurilma_orniga").replace("{nom}", j.almashtirilgan_nom)})`}
                {j.hal_qildi && ` — ${j.hal_qildi}`}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
