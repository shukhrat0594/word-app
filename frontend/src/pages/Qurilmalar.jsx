import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useI18n } from "../i18n";

/** «Qurilmalar» oynasi (2026-10-29, qurilmalar limiti 2-tizim) — owner va admin uchun
 * HAMMASI BITTA joyda: har bir foydalanuvchining qurilmalari, kutilayotgan so'rovlari,
 * bloklanganlari, limiti, ochiq seansi va kirish jurnali. Qurilma — telefon yoki kompyuter,
 * brauzer emas (uning brauzerlari qurilma ichida ko'rinadi). Ro'yxatlardagi «Qurilmalar n/limit»
 * tugmasi va yangi so'rov bildirishnomasi shu sahifani filtr bilan ochadi.
 * Backend: `accounts/qurilma_api.py`. */

const vaqt = (s) => (s ? new Date(s).toLocaleString([], { dateStyle: "short", timeStyle: "short" }) : "—");
const FILTRLAR = ["hammasi", "kutilmoqda", "blok", "kalitsiz"];
const ROLLAR = ["hammasi", "talaba", "xodim"];
const CHIPLAR = { ruxsat: "bor", kutilmoqda: "kutilmoqda", blok: "tugadi" };

export default function Qurilmalar() {
  const { t } = useI18n();
  const [params, setParams] = useSearchParams();
  const holat = FILTRLAR.includes(params.get("holat")) ? params.get("holat") : "hammasi";
  const rol = ROLLAR.includes(params.get("rol")) ? params.get("rol") : "hammasi";
  const foydalanuvchi = params.get("foydalanuvchi") || "";
  const q = params.get("q") || "";
  const [qidiruv, setQidiruv] = useState(q);
  const [m, setM] = useState(null);
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  const yukla = useCallback(() => {
    const so = new URLSearchParams({ holat, rol });
    if (foydalanuvchi) so.set("foydalanuvchi", foydalanuvchi);
    if (q) so.set("q", q);
    return api(`/api/qurilmalar/?${so}`)
      .then((d) => {
        setM(d);
        setXato("");
      })
      .catch((e) => setXato(e.data?.detail || t("xato_yuz_berdi")));
  }, [holat, rol, foydalanuvchi, q, t]);

  useEffect(() => {
    yukla();
  }, [yukla]);

  function filtr(qiymatlar) {
    const yangi = new URLSearchParams(params);
    for (const [kalit, qiymat] of Object.entries(qiymatlar)) {
      if (qiymat) yangi.set(kalit, qiymat);
      else yangi.delete(kalit);
    }
    setParams(yangi, { replace: true });
  }

  async function bajar(ish) {
    setBand(true);
    setXato("");
    try {
      await ish();
      await yukla();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  const amal = (qurilma, nomi, body = {}) =>
    bajar(() => api(`/api/qurilmalar/${qurilma.id}/amal/`, { method: "POST", body: { amal: nomi, ...body } }));
  const odamAmali = (odam, body) =>
    bajar(() => api(`/api/qurilmalar/foydalanuvchi/${odam.id}/`, { method: "POST", body }));

  return (
    <div>
      <h2>{t("nav_qurilmalar")}</h2>
      <p className="izoh">{t("qurilmalar_izoh")}</p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          filtr({ q: qidiruv.trim(), foydalanuvchi: "" });
        }}
        style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}
      >
        <input
          value={qidiruv}
          onChange={(e) => setQidiruv(e.target.value)}
          placeholder={t("q_qidirish")}
          style={{ flex: "1 1 220px" }}
        />
        <select value={rol} onChange={(e) => filtr({ rol: e.target.value })}>
          {ROLLAR.map((r) => (
            <option key={r} value={r}>{t(`qrol_${r}`)}</option>
          ))}
        </select>
        <button type="submit" className="tugma kichik">{t("q_qidir")}</button>
      </form>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
        {FILTRLAR.map((f) => (
          <button
            key={f}
            type="button"
            className={`tugma kichik${holat === f && !foydalanuvchi ? "" : " ikkinchi"}`}
            onClick={() => filtr({ holat: f, foydalanuvchi: "" })}
          >
            {t(`qf_${f}`)} {m ? m.sanoq[f] : ""}
          </button>
        ))}
        {(foydalanuvchi || q) && (
          <button type="button" className="tugma kichik ikkinchi" onClick={() => { setQidiruv(""); filtr({ foydalanuvchi: "", q: "" }); }}>
            {t("q_hammasini_korsat")}
          </button>
        )}
      </div>
      {xato && <div className="xato-xabar" style={{ marginBottom: 10 }}>{xato}</div>}
      {!m ? (
        <div className="yuklanmoqda">{t("yuklanmoqda")}</div>
      ) : m.foydalanuvchilar.length === 0 ? (
        <p className="izoh">{t("q_bosh")}</p>
      ) : (
        <div style={{ display: "grid", gap: 12 }}>
          {m.foydalanuvchilar.map((o) => (
            <OdamKartasi key={o.id} o={o} t={t} band={band} amal={amal} odamAmali={odamAmali} />
          ))}
          {m.kesildi && <p className="izoh">{t("q_kesildi")}</p>}
        </div>
      )}
    </div>
  );
}

function OdamKartasi({ o, t, band, amal, odamAmali }) {
  const [limit, setLimit] = useState(String(o.limit));
  const [jurnal, setJurnal] = useState(null);
  const ruxsatlar = o.qurilmalar.filter((q) => q.holat === "ruxsat");
  const limitSon = Number(limit);

  useEffect(() => setLimit(String(o.limit)), [o.limit]);

  const jurnalniYukla = useCallback(
    () => api(`/api/qurilmalar/foydalanuvchi/${o.id}/`).then(setJurnal).catch(() => setJurnal([])),
    [o.id]
  );
  // Amaldan keyin ro'yxat yangilanadi — ochiq jurnal ham.
  useEffect(() => {
    if (jurnal) jurnalniYukla();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [o]);

  return (
    <div className="karta" style={{ display: "grid", gap: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <span>
          <strong>{o.ism}</strong> <span className="izoh">({o.username}) · {t(`rol_${o.rol}`)}</span>
        </span>
        <span style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          <span>{t("q_limit")}: {o.ruxsat_soni} /</span>
          <input
            type="number"
            min={1}
            max={100}
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
            style={{ width: 64 }}
          />
          <button
            type="button"
            className="tugma kichik"
            disabled={band || !Number.isInteger(limitSon) || limitSon < 1 || limitSon === o.limit}
            onClick={() => odamAmali(o, { amal: "limit", limit: limitSon })}
          >
            {t("saqlash")}
          </button>
        </span>
      </div>
      <div className="izoh" style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        {o.seans
          ? t("q_seans")
              .replace("{qurilma}", o.seans.qurilma)
              .replace("{brauzer}", o.seans.brauzer || "—")
              .replace("{vaqt}", vaqt(o.seans.boshlangan))
          : t("q_seans_yoq")}
        {o.seans && (
          <button
            type="button"
            className="tugma ikkinchi kichik"
            disabled={band}
            onClick={() => window.confirm(t("q_seans_yop_tasdiq").replace("{ism}", o.ism)) && odamAmali(o, { amal: "seans_yop" })}
          >
            {t("q_seans_yop")}
          </button>
        )}
      </div>
      {o.qurilmalar.length === 0 && <p className="izoh" style={{ margin: 0 }}>{t("q_qurilmasi_yoq")}</p>}
      {o.qurilmalar.map((q) => (
        <QurilmaQatori key={q.id} q={q} o={o} ruxsatlar={ruxsatlar} t={t} band={band} amal={amal} />
      ))}
      <div>
        <button type="button" className="tugma ikkinchi kichik" onClick={() => (jurnal ? setJurnal(null) : jurnalniYukla())}>
          {jurnal ? "▾" : "▸"} {t("q_jurnal")}
        </button>
        {jurnal &&
          (jurnal.length === 0 ? (
            <p className="izoh">{t("q_jurnal_yoq")}</p>
          ) : (
            <div style={{ display: "grid", gap: 2, marginTop: 6 }}>
              {jurnal.map((j, i) => (
                <span key={i} className="izoh">
                  {vaqt(j.vaqt)} — {t(`qn_${j.natija}`)}: {t(`qs_${j.sabab}`)}
                  {j.qurilma && ` · ${j.qurilma}`}
                  {j.kim && ` · ${j.kim}`}
                </span>
              ))}
            </div>
          ))}
      </div>
    </div>
  );
}

function QurilmaQatori({ q, o, ruxsatlar, t, band, amal }) {
  const [boshqa, setBoshqa] = useState("");
  const tanlangan = boshqa || String(q.oxshash?.id ?? ruxsatlar[0]?.id ?? "");
  const tanlanganNom = ruxsatlar.find((r) => String(r.id) === tanlangan)?.nom || "";

  return (
    <div style={{ display: "grid", gap: 6, paddingTop: 8, borderTop: "1px solid var(--chiziq)" }}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <strong>{q.nom}</strong>
        <span className={`chip ${CHIPLAR[q.holat]}`}>{t(`q_holat_${q.holat}`)}</span>
        {q.holat === "ruxsat" && <span className="izoh">{q.kalit_bor ? t("q_kalit_bor") : t("q_kalit_yoq")}</span>}
        {q.seans && <span className="chip bor">{t("q_seans_shu")}</span>}
      </div>
      <span className="izoh">
        {q.brauzerlar.length > 0 && `${t("q_brauzerlar")}: ${q.brauzerlar.map((b) => b.nom || "—").join(", ")} · `}
        {t("q_qoshilgan")}: {vaqt(q.yaratilgan)} · {t("q_oxirgi")}: {vaqt(q.oxirgi)}
        {q.holat === "kutilmoqda" && ` · ${t("q_urinish").replace("{n}", q.urinishlar)}`}
        {q.holat === "blok" && q.hal_qildi && ` · ${q.hal_qildi}, ${vaqt(q.hal_vaqti)}`}
      </span>
      {q.holat === "kutilmoqda" && (
        <span className="izoh">{q.oxshash ? t("q_oxshaydi").replace("{nom}", q.oxshash.nom) : t("q_oxshamaydi")}</span>
      )}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        {q.holat === "kutilmoqda" && (
          <>
            <button type="button" className="tugma kichik" disabled={band} onClick={() => amal(q, "ruxsat")}>
              {o.ruxsat_soni >= o.limit ? t("q_ruxsat_limit") : t("q_ruxsat")}
            </button>
            {ruxsatlar.length > 0 && (
              <>
                <select value={tanlangan} onChange={(e) => setBoshqa(e.target.value)}>
                  {ruxsatlar.map((r) => (
                    <option key={r.id} value={r.id}>{r.nom}</option>
                  ))}
                </select>
                <button
                  type="button"
                  className="tugma ikkinchi kichik"
                  disabled={band}
                  onClick={() =>
                    window.confirm(t("q_orniga_tasdiq").replace(/\{eski\}/g, tanlanganNom).replace("{yangi}", q.nom)) &&
                    amal(q, "orniga", { boshqa: Number(tanlangan) })
                  }
                >
                  {t("q_orniga")}
                </button>
                <button
                  type="button"
                  className="tugma ikkinchi kichik"
                  disabled={band}
                  title={t("q_shu_qurilmaga_izoh")}
                  onClick={() => amal(q, "shu_qurilmaga", { boshqa: Number(tanlangan) })}
                >
                  {t("q_shu_qurilmaga")}
                </button>
              </>
            )}
          </>
        )}
        {q.holat !== "blok" ? (
          <button
            type="button"
            className="tugma ikkinchi kichik"
            disabled={band}
            onClick={() => window.confirm(t("q_blokla_tasdiq").replace("{nom}", q.nom)) && amal(q, "blokla")}
          >
            {t("q_blokla")}
          </button>
        ) : (
          <button type="button" className="tugma kichik" disabled={band} onClick={() => amal(q, "blokdan_chiqar")}>
            {t("q_blokdan")}
          </button>
        )}
        <button
          type="button"
          className="tugma ikkinchi kichik"
          disabled={band}
          onClick={() => window.confirm(t("q_ochir_tasdiq").replace("{nom}", q.nom)) && amal(q, "ochir")}
        >
          {t("q_ochir")}
        </button>
      </div>
    </div>
  );
}
