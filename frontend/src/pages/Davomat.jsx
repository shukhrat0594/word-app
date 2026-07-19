import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";

function bugun() {
  return new Date().toISOString().slice(0, 10);
}

export default function Davomat() {
  const { t } = useI18n();
  const [guruhlar, setGuruhlar] = useState([]);
  const [guruhId, setGuruhId] = useState("");
  const [sana, setSana] = useState(bugun());
  const [talabalar, setTalabalar] = useState(null);
  const [xabar, setXabar] = useState("");
  const [band, setBand] = useState(false);

  useEffect(() => {
    api("/api/guruhlar/").then((qs) => {
      setGuruhlar(qs);
      if (qs.length === 1) setGuruhId(String(qs[0].id));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!guruhId) {
      setTalabalar(null);
      return;
    }
    setXabar("");
    api(`/api/davomat/?guruh=${guruhId}&sana=${sana}`)
      .then((d) => setTalabalar(d.talabalar))
      .catch(() => {});
  }, [guruhId, sana]);

  function holatQoy(talabaId, holat) {
    setTalabalar((list) =>
      list.map((t2) => (t2.id === talabaId ? { ...t2, holat } : t2))
    );
  }

  async function saqla() {
    setBand(true);
    setXabar("");
    const yozuvlar = talabalar
      .filter((t2) => t2.holat)
      .map((t2) => ({ talaba: t2.id, holat: t2.holat }));
    try {
      await api("/api/davomat/", {
        method: "POST",
        body: { guruh: Number(guruhId), sana, yozuvlar },
      });
      setXabar(t("saqlandi"));
    } catch {
      setXabar(t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  return (
    <div className="karta">
      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginBottom: 16 }}>
        <div>
          <div className="izoh" style={{ marginBottom: 6 }}>{t("guruh_tanlang")}</div>
          <select value={guruhId} onChange={(e) => setGuruhId(e.target.value)}>
            <option value="">— {t("tanlanmagan")} —</option>
            {guruhlar.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <div className="izoh" style={{ marginBottom: 6 }}>{t("davomat_sana")}</div>
          <input type="date" value={sana} onChange={(e) => setSana(e.target.value)} />
        </div>
      </div>

      {!guruhId && <span className="izoh">{t("guruh_tanlang")}</span>}

      {guruhId && talabalar && talabalar.length === 0 && (
        <span className="izoh">{t("talaba_yoq")}</span>
      )}

      {guruhId && talabalar && talabalar.length > 0 && (
        <>
          {talabalar.map((tl) => (
            <div className="davomat-qator" key={tl.id}>
              <span>{tl.ism}</span>
              <div className="holat-tugmalar">
                <button
                  className={"keldi" + (tl.holat === "keldi" ? " aktiv" : "")}
                  onClick={() => holatQoy(tl.id, "keldi")}
                >
                  {t("keldi")}
                </button>
                <button
                  className={"kelmadi" + (tl.holat === "kelmadi" ? " aktiv" : "")}
                  onClick={() => holatQoy(tl.id, "kelmadi")}
                >
                  {t("kelmadi")}
                </button>
              </div>
            </div>
          ))}
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 16 }}>
            <button className="tugma" onClick={saqla} disabled={band}>
              {t("saqlash")}
            </button>
            {xabar && <span className="izoh">{xabar}</span>}
          </div>
        </>
      )}
    </div>
  );
}
