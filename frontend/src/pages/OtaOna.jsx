import { useEffect, useState } from "react";
import { api } from "../api";
import { Dinamika, Radar } from "../components/Grafiklar";
import NatijalarRoyxati from "../components/NatijalarRoyxati";
import { useI18n } from "../i18n";

export default function OtaOna() {
  const { t } = useI18n();
  const [farzandlar, setFarzandlar] = useState(null);
  const [tanlangan, setTanlangan] = useState(null);
  const [stat, setStat] = useState(null);

  useEffect(() => {
    api("/api/farzandlar/").then((qs) => {
      setFarzandlar(qs);
      if (qs.length === 1) setTanlangan(qs[0].id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!tanlangan) {
      setStat(null);
      return;
    }
    api(`/api/farzandlar/${tanlangan}/statistika/`).then(setStat).catch(() => {});
  }, [tanlangan]);

  if (!farzandlar) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  if (farzandlar.length === 0) {
    return (
      <div className="karta">
        <span className="izoh">{t("farzand_yoq")}</span>
      </div>
    );
  }

  return (
    <>
      {farzandlar.length > 1 && (
        <div className="tab-guruh">
          {farzandlar.map((f) => (
            <button
              key={f.id}
              className={tanlangan === f.id ? "aktiv" : ""}
              onClick={() => setTanlangan(f.id)}
            >
              {f.ism}
            </button>
          ))}
        </div>
      )}

      {!stat && <div className="yuklanmoqda">{t("yuklanmoqda")}</div>}

      {stat && (
        <>
          <div className="stat-qator">
            <div className="stat">
              <div className="nom">Writing band</div>
              <div className="qiymat">
                {stat.writing.oxirgi_band ?? "—"}{" "}
                <small>
                  {stat.writing.soni} {t("tekshiruv")}
                </small>
              </div>
            </div>
            <div className="stat">
              <div className="nom">Speaking band</div>
              <div className="qiymat">
                {stat.speaking.oxirgi_band ?? "—"}{" "}
                <small>
                  {stat.speaking.soni} {t("tekshiruv")}
                </small>
              </div>
            </div>
            {/* Video-TZ IMG_2216: o'rtacha band radar bilan bir xil — test bo'lsa testlardan,
                bo'lmasa mashqlardan; son ham shu manbaniki */}
            <div className="stat">
              <div className="nom">Listening band</div>
              <div className="qiymat">
                {stat.konikmalar.listening_band ?? "—"}{" "}
                <small>
                  {stat.listening.soni || stat.listening.jami_yechildi} {t("tekshiruv")}
                </small>
              </div>
            </div>
            <div className="stat">
              <div className="nom">Reading band</div>
              <div className="qiymat">
                {stat.konikmalar.reading_band ?? "—"}{" "}
                <small>
                  {stat.reading.soni || stat.reading.jami_yechildi} {t("tekshiruv")}
                </small>
              </div>
            </div>
          </div>

          <div className="ikki-ustun">
            <div className="karta">
              <h3>{t("konikmalar")}</h3>
              <Radar konikmalar={stat.konikmalar} />
            </div>
            <div className="karta">
              <h3>Writing</h3>
              <Dinamika dinamika={stat.writing.dinamika} />
            </div>
          </div>

          <div className="ikki-ustun">
            <div className="karta">
              <h3>Speaking</h3>
              <Dinamika dinamika={stat.speaking.dinamika} />
            </div>
            <div className="karta">
              <h3>Listening</h3>
              <Dinamika dinamika={stat.listening.dinamika} />
            </div>
          </div>

          <div className="ikki-ustun">
            <div className="karta">
              <h3>Reading</h3>
              <Dinamika dinamika={stat.reading.dinamika} />
            </div>
            <div className="karta">
              <h3>{t("listening_foiz")} %</h3>
              <Dinamika dinamika={stat.listening.mashq_dinamika} maydon="foiz" minQ={0} maxQ={100} qadam={25} />
            </div>
          </div>

          <div className="karta">
            <h3>{t("reading_foiz")} %</h3>
            <Dinamika dinamika={stat.reading.mashq_dinamika} maydon="foiz" minQ={0} maxQ={100} qadam={25} />
          </div>

          {/* 2026-08-09: ota-ona endi farzandning BARCHA mashq/test
              natijalarini ham ko'radi (avval faqat umumiy statistika
              bor edi). Admin/teacher tomonidagi bilan BIR XIL komponent —
              backendda ham shu endpoint, `PARENT` shoxi bilan. */}
          <div className="karta">
            <h3>{t("mashq_natijalari")}</h3>
            <NatijalarRoyxati talabaId={tanlangan} />
          </div>

          <div className="karta">
            <h3>{t("davomat")}</h3>
            <div className="stat-qator" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
              <div className="stat">
                <div className="nom">{t("keldi")}</div>
                <div className="qiymat">{stat.davomat.keldi}</div>
              </div>
              <div className="stat">
                <div className="nom">{t("kechikdi")}</div>
                <div className="qiymat">{stat.davomat.kechikdi}</div>
              </div>
              <div className="stat">
                <div className="nom">{t("kelmadi")}</div>
                <div className="qiymat">{stat.davomat.kelmadi}</div>
              </div>
              <div className="stat">
                <div className="nom">{t("sababli")}</div>
                <div className="qiymat">{stat.davomat.sababli}</div>
              </div>
            </div>
          </div>

          {/* Video-TZ IMG_2217: to'lov/qarz holati va guruh ustozlari */}
          <div className="ikki-ustun">
            <div className="karta">
              <h3>{t("tolov_holati")}</h3>
              <div className="stat">
                <div className="nom">
                  {stat.tolov.qarz > 0
                    ? t("qarzdorlik")
                    : stat.tolov.balans > 0
                      ? t("oldindan_tolangan")
                      : t("qarz_yoq")}
                </div>
                <div className="qiymat" style={{ color: stat.tolov.qarz > 0 ? "#d33" : undefined }}>
                  {(stat.tolov.qarz || stat.tolov.balans).toLocaleString("ru-RU")} {t("som")}
                </div>
              </div>
            </div>
            <div className="karta">
              <h3>{t("ustozlar")}</h3>
              {stat.ustozlar.length === 0 && <span className="izoh">{t("ustoz_yoq")}</span>}
              {stat.ustozlar.map((u, i) => (
                <div key={i}style={{ marginBottom: 8 }}>
                  <b>{u.ism || t("ustoz_yoq")}</b> <span className="izoh">({u.guruh})</span>
                  {u.telefon && (
                    <div>
                      <a href={`tel:${u.telefon}`}>{u.telefon}</a>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </>
  );
}
