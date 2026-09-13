import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";

/**
 * Kurslar bo'limida yechilgan mashqlar tarixi — PAPKA ko'rinishi
 * (2026-09-14, Shuhrat talabi: "o'tilgan testlarning tarixini matn
 * ko'rinishida saqlash, ya'ni qaysi savolga qanday javob berganini,
 * papka ko'rinishida saqlasin. Masalan: Beginner 01.09.2026 - 15/30
 * uni ustiga bossa qaysi raqamdagi savolga nima javob bergani").
 *
 * Uch qatlam: daraja (papka) > yechim (sana + ball) > savol-javob.
 * Ma'lumot yangi emas — `KursMashqYechim` uni boshidan saqlab kelgan,
 * bu yerda faqat ko'rsatiladi (`courses.KursTarixView`).
 *
 * `talabaId` berilmasa — ko'rayotgan odamning O'Z tarixi. Berilsa,
 * backend `natijalarni_korish_ruxsati` orqali tekshiradi (o'qituvchi
 * o'z guruhidagini, ota-ona o'z farzandiniki, admin/owner hammasini).
 */
export default function KursTarixi({ talabaId }) {
  const { t } = useI18n();
  const [malumot, setMalumot] = useState(null);
  const [xato, setXato] = useState("");
  const [ochiqDaraja, setOchiqDaraja] = useState(null);
  const [ochiqYechim, setOchiqYechim] = useState(null);
  const [tafsilot, setTafsilot] = useState(null);
  const [tafsilotYuklanmoqda, setTafsilotYuklanmoqda] = useState(false);

  useEffect(() => {
    const soralar = talabaId ? `?talaba=${talabaId}` : "";
    api(`/api/kurslar/tarix/${soralar}`)
      .then(setMalumot)
      .catch((e) => setXato(e.data?.detail || t("xato_yuz_berdi")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [talabaId]);

  async function yechimniOch(id) {
    // Ikkinchi bosish — yopadi.
    if (ochiqYechim === id) {
      setOchiqYechim(null);
      setTafsilot(null);
      return;
    }
    setOchiqYechim(id);
    setTafsilot(null);
    setTafsilotYuklanmoqda(true);
    try {
      setTafsilot(await api(`/api/kurslar/tarix/${id}/`));
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setTafsilotYuklanmoqda(false);
    }
  }

  function sanaMatni(iso) {
    const d = new Date(iso);
    const ikki = (n) => String(n).padStart(2, "0");
    return `${ikki(d.getDate())}.${ikki(d.getMonth() + 1)}.${d.getFullYear()}`;
  }

  if (xato) return <div className="xato-xabar">{xato}</div>;
  if (!malumot) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;
  if (malumot.darajalar.length === 0) {
    return <div className="izoh">{t("kurs_tarix_bosh")}</div>;
  }

  return (
    <div>
      {malumot.darajalar.map((daraja) => (
        <div key={daraja.id} style={{ marginBottom: 8 }}>
          <button
            type="button"
            className="tugma ikkinchi"
            style={{ width: "100%", textAlign: "left" }}
            onClick={() =>
              setOchiqDaraja((joriy) => (joriy === daraja.id ? null : daraja.id))
            }
          >
            {ochiqDaraja === daraja.id ? "📂" : "📁"} {daraja.nomi}{" "}
            <span className="izoh">({daraja.yechimlar.length})</span>
          </button>

          {ochiqDaraja === daraja.id && (
            <div style={{ paddingLeft: 16, marginTop: 6 }}>
              {daraja.yechimlar.map((y) => (
                <div key={y.id} style={{ marginBottom: 6 }}>
                  <button
                    type="button"
                    className="tugma ikkinchi"
                    style={{ width: "100%", textAlign: "left" }}
                    onClick={() => yechimniOch(y.id)}
                  >
                    📄 {daraja.nomi} {sanaMatni(y.sana)} — {y.ball}/{y.jami}
                    {y.yol && <span className="izoh"> · {y.yol}</span>}
                  </button>

                  {ochiqYechim === y.id && (
                    <div style={{ paddingLeft: 16, marginTop: 6 }}>
                      {tafsilotYuklanmoqda && (
                        <div className="yuklanmoqda">{t("yuklanmoqda")}</div>
                      )}
                      {tafsilot && tafsilot.id === y.id && (
                        <div style={{ overflowX: "auto" }}>
                          <table className="tarix-jadval">
                            <thead>
                              <tr>
                                <th>№</th>
                                <th>{t("kurs_tarix_savol")}</th>
                                <th>{t("kurs_tarix_javobi")}</th>
                                <th>{t("kurs_tarix_togri_javob")}</th>
                              </tr>
                            </thead>
                            <tbody>
                              {tafsilot.savollar.map((q) => (
                                <tr key={q.raqam}>
                                  <td>{q.raqam}</td>
                                  <td>{q.savol}</td>
                                  <td
                                    style={{
                                      color: q.togrimi ? "#1a7f37" : "#d33",
                                      fontWeight: 600,
                                    }}
                                  >
                                    {q.togrimi ? "✓" : "✗"} {q.javob || "—"}
                                  </td>
                                  <td>{q.togri_javob || "—"}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
