import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { RoyxatMaydoni } from "./ImtihonBoshqarish";

/** Tekis qatorlar ro'yxatini Bo'lim → Mashq → savollar daraxtiga
 * aylantiradi — birinchi uchragan tartibda (backend allaqachon
 * `bolim, name` bo'yicha saralab beradi). */
function bolimlargaGuruhla(qatorlar) {
  const bolimlar = [];
  const bolimMap = new Map();
  for (const q of qatorlar) {
    let b = bolimMap.get(q.bolim);
    if (!b) {
      b = { bolim: q.bolim, jami: 0, mashqlar: [], mashqMap: new Map() };
      bolimMap.set(q.bolim, b);
      bolimlar.push(b);
    }
    b.jami += 1;
    let m = b.mashqMap.get(q.test_id);
    if (!m) {
      m = { test_id: q.test_id, test_nomi: q.test_nomi, savollar: [] };
      b.mashqMap.set(q.test_id, m);
      b.mashqlar.push(m);
    }
    m.savollar.push(q);
  }
  return bolimlar;
}

/** Bitta mashqning javobsiz savollariga tez javob kiritish oynasi
 * (2026-08-12, foydalanuvchi talabi: "javobsiz savollar hisobotida
 * ... shu hisobotni o'zida kiritish imkonini qilish"). Har savol
 * o'zining mashqdagi HAQIQIY raqami bilan ko'rsatiladi, yoniga
 * `RoyxatMaydoni` (Enter — yangi qabul qilinadigan variant, masalan
 * "20" va "twenty" ikkalasi ham) orqali javob kiritiladi. "Saqlash" —
 * BITTA so'rovda faqat to'ldirilgan savollarni yangilaydi. */
function JavobKiritishOynasi({ testId, onYopish, onSaqlandi, t }) {
  const [mashq, setMashq] = useState(null);
  const [javoblar, setJavoblar] = useState({});
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  useEffect(() => {
    api(`/api/imtihon/javobsiz-hisobot/${testId}/`)
      .then((r) => setMashq(r))
      .catch((e) => setXato(e.data?.detail || t("xato_yuz_berdi")));
  }, [testId]);

  async function saqla() {
    const toldirilgan = Object.entries(javoblar)
      .filter(([, arr]) => arr && arr.length > 0)
      .map(([raqam, arr]) => ({ savol_raqami: Number(raqam), togri: arr }));
    if (toldirilgan.length === 0) return;
    setBand(true);
    setXato("");
    try {
      await api(`/api/imtihon/javobsiz-hisobot/${testId}/javob-kiritish/`, {
        method: "POST",
        body: { javoblar: toldirilgan },
      });
      onSaqlandi();
      onYopish();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  return (
    <div
      onClick={onYopish}
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 2000,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="karta"
        style={{ maxWidth: 640, width: "90%", maxHeight: "85vh", overflowY: "auto" }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0 }}>{mashq?.test_nomi || "…"}</h3>
          <button className="tugma ikkinchi kichik" onClick={onYopish}>{t("yopish")}</button>
        </div>
        <p className="izoh">{t("javobsiz_javob_kiritish_izoh")}</p>

        {xato && <div className="xato-xabar" style={{ marginTop: 8 }}>{xato}</div>}

        {!mashq ? (
          <div className="yuklanmoqda">{t("yuklanmoqda")}</div>
        ) : (
          <div style={{ display: "grid", gap: 12, marginTop: 10, maxHeight: "60vh", overflowY: "auto" }}>
            {mashq.savollar.map((s) => (
              <div key={s.savol_raqami} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                <strong style={{ minWidth: 28 }}>{s.savol_raqami}.</strong>
                <span style={{ flex: 1 }}>{s.savol_matni}</span>
                <RoyxatMaydoni
                  qiymat={(javoblar[s.savol_raqami] || []).join("\n")}
                  ajratgich={"\n"}
                  ozgardi={(arr) => setJavoblar((v) => ({ ...v, [s.savol_raqami]: arr }))}
                  rows={2}
                  placeholder={t("javobsiz_javob_placeholder")}
                  style={{ width: 220, fontSize: 13 }}
                />
              </div>
            ))}
          </div>
        )}

        <div style={{ marginTop: 14 }}>
          <button className="tugma" onClick={saqla} disabled={band}>
            {band ? t("yuklanmoqda") : t("saqlash")}
          </button>
        </div>
      </div>
    </div>
  );
}

/** Owner/admin uchun — Reading/Listening testlarida to'g'ri javobi
 * belgilanmagan savollarni papka-uslub ierarxik ko'rinishda ko'rsatadi
 * (2026-08-11 yaratildi tekis jadval sifatida; 2026-08-12 foydalanuvchi
 * talabi bilan Bo'lim → Mashq → savollar accordion'ga o'zgartirildi —
 * `ImtihonOtish.jsx: PapkaliRoyxat`dagi bilan bir xil vizual naqsh,
 * `imtihon-papka`/`imtihon-papka-sarlavha`/`imtihon-papka-ichi`
 * CSS klasslari qayta ishlatildi). Mashq nomiga bosilganda YANGI
 * "javob kiritish" oynasi ochiladi (2026-08-12) — to'liq tahrirlash
 * formasi emas, faqat javobsiz savollarga tez javob kiritish. */
export default function JavobsizSavollarHisoboti() {
  const { t } = useI18n();
  const [qatorlar, setQatorlar] = useState(null);
  const [xato, setXato] = useState("");
  const [ochilganTestId, setOchilganTestId] = useState(null);
  const [ochiq, setOchiq] = useState({});

  function yukla() {
    api("/api/imtihon/javobsiz-hisobot/")
      .then((r) => {
        setQatorlar(r);
        setXato("");
      })
      .catch((e) => setXato(e.data?.detail || t("xato_yuz_berdi")));
  }

  useEffect(() => {
    yukla();
  }, []);

  return (
    <div className="karta">
      <h3>{t("javobsiz_hisobot")}</h3>
      <p className="izoh" style={{ marginTop: 0 }}>{t("javobsiz_hisobot_izoh")}</p>

      {xato && <div className="xato-xabar" style={{ marginTop: 8 }}>{xato}</div>}

      {qatorlar === null ? (
        <div className="yuklanmoqda">{t("yuklanmoqda")}</div>
      ) : qatorlar.length === 0 ? (
        <span className="izoh">{t("javobsiz_hisobot_boshi")}</span>
      ) : (
        <div style={{ marginTop: 10 }}>
          {bolimlargaGuruhla(qatorlar).map((b) => (
            <div key={b.bolim} className="imtihon-papka">
              <div
                className="imtihon-papka-sarlavha"
                onClick={() => setOchiq((v) => ({ ...v, [`b${b.bolim}`]: !v[`b${b.bolim}`] }))}
              >
                <span>{ochiq[`b${b.bolim}`] ? "▾" : "▸"} 📁 {t(`mashq_bolim_${b.bolim}`)}</span>
                <span className="izoh">{b.jami}</span>
              </div>
              {ochiq[`b${b.bolim}`] && (
                <div className="imtihon-papka-ichi">
                  {b.mashqlar.map((m) => (
                    <div key={m.test_id} className="imtihon-papka" style={{ marginLeft: 20 }}>
                      <div
                        className="imtihon-papka-sarlavha"
                        onClick={() =>
                          setOchiq((v) => ({ ...v, [`m${m.test_id}`]: !v[`m${m.test_id}`] }))
                        }
                      >
                        <span>
                          {ochiq[`m${m.test_id}`] ? "▾" : "▸"} 📂{" "}
                          <span
                            style={{ cursor: "pointer", textDecoration: "underline dotted" }}
                            title={t("javobsiz_javob_kiritish_ochish")}
                            onClick={(e) => { e.stopPropagation(); setOchilganTestId(m.test_id); }}
                          >
                            {m.test_nomi}
                          </span>
                        </span>
                        <span className="izoh">{m.savollar.length}</span>
                      </div>
                      {ochiq[`m${m.test_id}`] && (
                        <div className="imtihon-papka-ichi">
                          {m.savollar.map((s, i) => (
                            <div
                              key={`${s.savol_raqami}-${i}`}
                              style={{
                                padding: "8px 0", borderBottom: "1px solid var(--chiziq)",
                                fontSize: "13.5px",
                              }}
                            >
                              <span>
                                <strong>{s.savol_raqami}.</strong> {s.savol_matni}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {ochilganTestId && (
        <JavobKiritishOynasi
          testId={ochilganTestId}
          onYopish={() => setOchilganTestId(null)}
          onSaqlandi={yukla}
          t={t}
        />
      )}
    </div>
  );
}
