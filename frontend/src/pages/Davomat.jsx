import { useEffect, useState } from "react";
import { api } from "../api";
import XatolikHolati from "../components/XatolikHolati";
import { useI18n } from "../i18n";

function bugun() {
  return new Date().toISOString().slice(0, 10);
}

/** Davomat belgilash.
 *
 * 2026-08-15: avval alohida "/davomat" paneli edi, endi GURUH ICHIDA
 * ochiladi (`Guruhlar.jsx`) — o'qituvchi guruhni tanlab, o'sha yerdayoq
 * davomat qo'yadi, ikki bo'lim orasida sakrash shart emas.
 * `guruhId` prop berilsa guruh tanlash ro'yxati KO'RSATILMAYDI (guruh
 * allaqachon ma'lum); berilmasa — avvalgidek o'zi tanlaydi (mustaqil
 * sahifa sifatida ishlatilsa). */
export default function Davomat({ guruhId: tashqiGuruhId }) {
  const { t } = useI18n();
  const [guruhlar, setGuruhlar] = useState([]);
  const [ichkiGuruhId, setIchkiGuruhId] = useState("");
  const [sana, setSana] = useState(bugun());
  const [talabalar, setTalabalar] = useState(null);
  const [xabar, setXabar] = useState("");
  const [band, setBand] = useState(false);
  const [xato, setXato] = useState(false);

  const guruhId = tashqiGuruhId != null ? String(tashqiGuruhId) : ichkiGuruhId;
  const setGuruhId = setIchkiGuruhId;

  function guruhlarniYukla() {
    if (tashqiGuruhId != null) return; // guruh tashqaridan berilgan
    api("/api/guruhlar/").then((qs) => {
      setGuruhlar(qs);
      if (qs.length === 1) setGuruhId(String(qs[0].id));
    }).catch(() => setXato(true));
  }

  function talabalarniYukla() {
    if (!guruhId) {
      setTalabalar(null);
      return;
    }
    setXabar("");
    api(`/api/davomat/?guruh=${guruhId}&sana=${sana}`)
      .then((d) => setTalabalar(d.talabalar))
      .catch(() => setXato(true));
  }

  function yukla() {
    setXato(false);
    guruhlarniYukla();
    talabalarniYukla();
  }

  useEffect(() => {
    guruhlarniYukla();
  }, []);

  useEffect(() => {
    talabalarniYukla();
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

  if (xato) return <XatolikHolati qaytaUrin={yukla} />;

  // Guruh ichiga joylashtirilganda tashqi "karta" o'rami berilmaydi —
  // aks holda karta ichida karta bo'lib ko'rinadi.
  return (
    <div className={tashqiGuruhId == null ? "karta" : ""}>
      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginBottom: 16 }}>
        {tashqiGuruhId == null && (
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
        )}
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
