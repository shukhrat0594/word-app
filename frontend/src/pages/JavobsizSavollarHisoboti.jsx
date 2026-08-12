import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { MashqTolaTahrir } from "./ImtihonBoshqarish";

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

/** Owner/admin uchun — Reading/Listening testlarida to'g'ri javobi
 * belgilanmagan savollarni papka-uslub ierarxik ko'rinishda ko'rsatadi
 * (2026-08-11 yaratildi tekis jadval sifatida; 2026-08-12 foydalanuvchi
 * talabi bilan Bo'lim → Mashq → savollar accordion'ga o'zgartirildi —
 * `ImtihonOtish.jsx: PapkaliRoyxat`dagi bilan bir xil vizual naqsh,
 * `imtihon-papka`/`imtihon-papka-sarlavha`/`imtihon-papka-ichi`
 * CSS klasslari qayta ishlatildi). Mashq nomiga bosilganda mavjud
 * `MashqTolaTahrir` (IELTS testlari boshqaruvidagi tahrirlash oynasi)
 * ochiladi — yangi tahrirlash UI yozilmagan, borini qayta ishlatadi. */
export default function JavobsizSavollarHisoboti() {
  const { t } = useI18n();
  const [qatorlar, setQatorlar] = useState(null);
  const [xato, setXato] = useState("");
  const [ochilganTest, setOchilganTest] = useState(null);
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

  async function mashqniOch(testId) {
    setXato("");
    try {
      const test = await api(`/api/imtihon/testlar-boshqaruv/${testId}/`);
      setOchilganTest(test);
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    }
  }

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
                            title={t("imtihon_tola_ochish")}
                            onClick={(e) => { e.stopPropagation(); mashqniOch(m.test_id); }}
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

      {ochilganTest && (
        <MashqTolaTahrir
          test={ochilganTest}
          manba={ochilganTest.manba}
          onYopish={() => setOchilganTest(null)}
          onSaqlandi={() => {
            mashqniOch(ochilganTest.id);
            yukla();
          }}
        />
      )}
    </div>
  );
}
