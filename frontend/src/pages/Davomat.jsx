import { useEffect, useState } from "react";
import { api } from "../api";
import XatolikHolati from "../components/XatolikHolati";
import { useI18n } from "../i18n";

// 2026-09-07, auditda topildi: bu yerda `toISOString()` ishlatilardi va u
// HAR DOIM UTC qaytaradi, brauzerning mahalliy sanasini emas. Toshkent
// UTC+5, ya'ni har kuni 00:00-05:00 oralig'ida sana tanlagich KECHAGI
// kunni ko'rsatardi va o'qituvchi buni sezmasa davomat noto'g'ri kunga
// yozilardi. "sv-SE" lokali ataylab: u sanani aynan "YYYY-MM-DD"
// ko'rinishida beradi (<input type="date"> shu formatni kutadi), lekin
// hisob MAHALLIY vaqt mintaqasida ketadi.
function bugun() {
  return new Date().toLocaleDateString("sv-SE");
}

// "YYYY-MM-DD" satrlari — leksik taqqoslash sana tartibiga mos keladi.
// Oy surilganda shu oyning 1-sanasi beriladi, keyin `talabalarniYukla`
// uni o'sha oyning birinchi dars kuniga to'g'rilaydi.
function oySur(sana, qadam) {
  const [y, m] = sana.split("-").map(Number);
  const d = new Date(y, m - 1 + qadam, 1);
  return d.toLocaleDateString("sv-SE");
}

const SANA_LOKALI = { uz: "uz-Latn-UZ", ru: "ru-RU", en: "en-GB" };

function sanaMatni(sana, til) {
  const [y, m, k] = sana.split("-").map(Number);
  return new Date(y, m - 1, k).toLocaleDateString(SANA_LOKALI[til] || "uz-Latn-UZ", {
    weekday: "short",
    day: "numeric",
    month: "long",
  });
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
  const { t, til } = useI18n();
  const [guruhlar, setGuruhlar] = useState([]);
  const [ichkiGuruhId, setIchkiGuruhId] = useState("");
  const [sana, setSana] = useState(bugun());
  // Video-TZ IMG_7340.MOV: davomat faqat guruhning DARS kunlariga
  // belgilanadi. Server `sana` oyidagi dars sanalarini beradi; `null` —
  // guruhga jadval kiritilmagan, unda avvalgidek istalgan kun tanlanadi.
  const [darsSanalari, setDarsSanalari] = useState(null);
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
      setDarsSanalari(null);
      return;
    }
    setXabar("");
    api(`/api/davomat/?guruh=${guruhId}&sana=${sana}`)
      .then((d) => {
        const ds = d.dars_sanalari ?? null;
        setDarsSanalari(ds);
        setTalabalar(d.talabalar);
        // Tanlangan kun dars kuni bo'lmasa — shu oydagi eng yaqin O'TGAN
        // dars kuniga (bugun juma bo'lsa — payshanbaga), u ham bo'lmasa
        // oyning birinchi dars kuniga o'tiladi.
        if (ds && ds.length && !ds.includes(sana)) {
          const otgan = ds.filter((s) => s <= sana);
          setSana(otgan.length ? otgan[otgan.length - 1] : ds[0]);
        }
      })
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

  function holatQoy(talabaId, holat, izoh) {
    setTalabalar((list) =>
      list.map((t2) => (t2.id === talabaId ? { ...t2, holat, izoh: izoh ?? t2.izoh } : t2))
    );
  }

  // "Sababli" tanlanganda izoh so'raladi — admin CRM paneli bilan bir xil
  // (`GuruhOynalari.jsx` dagi `DavomatMenyusi`).
  function sababliTanla(talabaId) {
    const javob = window.prompt(t("sabab_izoh"), "");
    if (javob === null) return;
    holatQoy(talabaId, "sababli", javob);
  }

  async function saqla() {
    setBand(true);
    setXabar("");
    const yozuvlar = talabalar
      .filter((t2) => t2.holat)
      .map((t2) => ({ talaba: t2.id, holat: t2.holat, izoh: t2.izoh || "" }));
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

  // Jadvalsiz guruhda har kun "dars kuni" hisoblanadi.
  const darsDa = !darsSanalari || darsSanalari.includes(sana);

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
          {darsSanalari ? (
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <button
                className="tugma ikkinchi"
                title={t("davomat_oldingi_oy")}
                onClick={() => setSana(oySur(sana, -1))}
              >
                ‹
              </button>
              <select value={darsDa ? sana : ""} onChange={(e) => setSana(e.target.value)}>
                {!darsDa && <option value="">—</option>}
                {darsSanalari.map((s) => (
                  <option key={s} value={s}>
                    {sanaMatni(s, til)}
                  </option>
                ))}
              </select>
              <button
                className="tugma ikkinchi"
                title={t("davomat_keyingi_oy")}
                onClick={() => setSana(oySur(sana, 1))}
              >
                ›
              </button>
            </div>
          ) : (
            <input type="date" value={sana} onChange={(e) => setSana(e.target.value)} />
          )}
        </div>
      </div>

      {!guruhId && <span className="izoh">{t("guruh_tanlang")}</span>}

      {guruhId && darsSanalari && darsSanalari.length === 0 && (
        <span className="izoh">{t("davomat_oyda_dars_yoq")}</span>
      )}

      {guruhId && darsDa && talabalar && talabalar.length === 0 && (
        <span className="izoh">{t("talaba_yoq")}</span>
      )}

      {guruhId && darsDa && talabalar && talabalar.length > 0 && (
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
                <button
                  className={"kechikdi" + (tl.holat === "kechikdi" ? " aktiv" : "")}
                  onClick={() => holatQoy(tl.id, "kechikdi")}
                >
                  {t("kechikdi")}
                </button>
                <button
                  className={"sababli" + (tl.holat === "sababli" ? " aktiv" : "")}
                  onClick={() => sababliTanla(tl.id)}
                >
                  {t("sababli")}
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
