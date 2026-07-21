import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";

const LIMIT = 50;

function OzgarishlarKorinishi({ ozgarishlar }) {
  if (!ozgarishlar || Object.keys(ozgarishlar).length === 0) return null;
  return (
    <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
      {Object.entries(ozgarishlar).map(([maydon, qiymat]) => (
        <li key={maydon} className="izoh">
          <strong>{maydon}</strong>:{" "}
          {qiymat && typeof qiymat === "object" && "eski" in qiymat ? (
            <>
              {String(qiymat.eski ?? "—")} → {String(qiymat.yangi ?? "—")}
            </>
          ) : (
            String(qiymat)
          )}
        </li>
      ))}
    </ul>
  );
}

export default function AuditHisobot() {
  const { t } = useI18n();
  const [natijalar, setNatijalar] = useState(null);
  const [jami, setJami] = useState(0);
  const [xato, setXato] = useState("");
  const [filtr, setFiltr] = useState({
    turi: "",
    foydalanuvchi: "",
    sana_dan: "",
    sana_gacha: "",
  });
  const [offset, setOffset] = useState(0);

  function yukla(yangiFiltr, yangiOffset) {
    const f = yangiFiltr !== undefined ? yangiFiltr : filtr;
    const o = yangiOffset !== undefined ? yangiOffset : 0;
    const params = new URLSearchParams({ limit: LIMIT, offset: o });
    if (f.turi) params.set("turi", f.turi);
    if (f.foydalanuvchi) params.set("foydalanuvchi", f.foydalanuvchi);
    if (f.sana_dan) params.set("sana_dan", f.sana_dan);
    if (f.sana_gacha) params.set("sana_gacha", f.sana_gacha);

    api(`/api/audit/?${params}`)
      .then((r) => {
        setJami(r.jami);
        setNatijalar(o === 0 ? r.natijalar : (prev) => [...(prev || []), ...r.natijalar]);
        setOffset(o);
        setXato("");
      })
      .catch((e) => setXato(e.data?.detail || t("xato_yuz_berdi")));
  }

  useEffect(() => {
    yukla(filtr, 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function filtrlash(e) {
    e.preventDefault();
    yukla(filtr, 0);
  }

  function tozalash() {
    const bosh = { turi: "", foydalanuvchi: "", sana_dan: "", sana_gacha: "" };
    setFiltr(bosh);
    yukla(bosh, 0);
  }

  if (natijalar === null) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <div className="karta">
      <h3>{t("nav_audit")}</h3>

      <form
        onSubmit={filtrlash}
        style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 18 }}
      >
        <select
          value={filtr.turi}
          onChange={(e) => setFiltr((f) => ({ ...f, turi: e.target.value }))}
        >
          <option value="">{t("audit_turi_hammasi")}</option>
          <option value="boshqaruv">{t("audit_boshqaruv")}</option>
          <option value="mashq">{t("audit_mashq")}</option>
        </select>
        <input
          style={{ maxWidth: 120 }}
          type="number"
          placeholder={t("audit_filtr_foydalanuvchi")}
          value={filtr.foydalanuvchi}
          onChange={(e) => setFiltr((f) => ({ ...f, foydalanuvchi: e.target.value }))}
        />
        <input
          type="date"
          value={filtr.sana_dan}
          onChange={(e) => setFiltr((f) => ({ ...f, sana_dan: e.target.value }))}
        />
        <input
          type="date"
          value={filtr.sana_gacha}
          onChange={(e) => setFiltr((f) => ({ ...f, sana_gacha: e.target.value }))}
        />
        <button className="tugma">{t("audit_filtr_qollash")}</button>
        <button type="button" className="tugma ikkinchi" onClick={tozalash}>
          {t("audit_filtr_tozalash")}
        </button>
      </form>

      {xato && <div className="xato-xabar">{xato}</div>}

      <div className="izoh" style={{ marginBottom: 10 }}>
        {t("jami")}: {jami}
      </div>

      {natijalar.length === 0 ? (
        <div className="izoh">{t("audit_yozuv_yoq")}</div>
      ) : (
        <div style={{ display: "grid", gap: 10 }}>
          {natijalar.map((y, i) => (
            <div className="davomat-qator" key={i} style={{ alignItems: "flex-start" }}>
              <span>
                <strong>{y.harakat_nomi}</strong>
                {y.obyekt_turi ? ` — ${y.obyekt_turi}` : ""}
                {y.obyekt_nomi ? ` "${y.obyekt_nomi}"` : ""}
                <br />
                <span className="izoh">
                  {y.foydalanuvchi?.ism || "—"} ({y.foydalanuvchi?.username}) ·{" "}
                  {new Date(y.vaqt).toLocaleString()} ·{" "}
                  {y.turi === "boshqaruv" ? t("audit_boshqaruv") : t("audit_mashq")}
                </span>
                <OzgarishlarKorinishi ozgarishlar={y.ozgarishlar} />
              </span>
            </div>
          ))}
        </div>
      )}

      {offset + LIMIT < jami && (
        <button
          className="tugma ikkinchi"
          style={{ marginTop: 14 }}
          onClick={() => yukla(filtr, offset + LIMIT)}
        >
          {t("audit_kop_yuklash")}
        </button>
      )}
    </div>
  );
}
