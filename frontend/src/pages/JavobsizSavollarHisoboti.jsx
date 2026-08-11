import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { MashqTolaTahrir } from "./ImtihonBoshqarish";

/** Owner/admin uchun — Reading/Listening testlarida to'g'ri javobi
 * belgilanmagan savollarni jadval qilib ko'rsatadi (2026-08-11,
 * foydalanuvchi talabi). Mashq nomiga bosilganda mavjud
 * `MashqTolaTahrir` (IELTS testlari boshqaruvidagi tahrirlash oynasi)
 * ochiladi — yangi tahrirlash UI yozilmagan, borini qayta ishlatadi. */
export default function JavobsizSavollarHisoboti() {
  const { t } = useI18n();
  const [qatorlar, setQatorlar] = useState(null);
  const [xato, setXato] = useState("");
  const [ochilganTest, setOchilganTest] = useState(null);

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
        <div style={{ overflowX: "auto", marginTop: 10 }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid var(--chiziq)", textAlign: "left" }}>
                <th style={{ padding: "6px 10px" }}>{t("javobsiz_hisobot_bolim")}</th>
                <th style={{ padding: "6px 10px" }}>{t("javobsiz_hisobot_mashq")}</th>
                <th style={{ padding: "6px 10px" }}>{t("javobsiz_hisobot_savol_raqami")}</th>
                <th style={{ padding: "6px 10px" }}>{t("javobsiz_hisobot_savol_matni")}</th>
              </tr>
            </thead>
            <tbody>
              {qatorlar.map((q, i) => (
                <tr key={`${q.test_id}-${q.savol_raqami}-${i}`} style={{ borderBottom: "1px solid var(--chiziq)" }}>
                  <td style={{ padding: "6px 10px" }}>{t(`mashq_bolim_${q.bolim}`)}</td>
                  <td style={{ padding: "6px 10px" }}>
                    <span
                      style={{ cursor: "pointer", textDecoration: "underline dotted" }}
                      title={t("imtihon_tola_ochish")}
                      onClick={() => mashqniOch(q.test_id)}
                    >
                      {q.test_nomi}
                    </span>
                  </td>
                  <td style={{ padding: "6px 10px" }}>{q.savol_raqami}</td>
                  <td style={{ padding: "6px 10px" }}>{q.savol_matni}</td>
                </tr>
              ))}
            </tbody>
          </table>
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
