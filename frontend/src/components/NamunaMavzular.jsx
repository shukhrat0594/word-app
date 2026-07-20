import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";

const SVG_BELGISI = "[Grafik SVG manba kodi]\n";

// matn ichiga yozib qo'yilgan xom SVG kodini (Writing Task1 grafiklari)
// ajratib oladi va <img> sifatida (data URI) xavfsiz render qilish uchun
// qaytaradi — dangerouslySetInnerHTML ishlatilmaydi.
export function svgAjrat(matn) {
  const i = matn.indexOf(SVG_BELGISI);
  if (i === -1) return { matn, svgUrl: null };
  const svg = matn.slice(i + SVG_BELGISI.length).trim();
  const asosiyMatn = matn.slice(0, i).trim();
  return { matn: asosiyMatn, svgUrl: `data:image/svg+xml;utf8,${encodeURIComponent(svg)}` };
}

// Bo'lim bo'yicha qaysi turlar bor — mavjud Mashq ma'lumotlari shu tur
// qiymatlari bilan yozilgan (Speaking Part2/3 birlashtirilgan, tur="part2").
// Writing.jsx/Speaking.jsx'dagi "Haqiqiy mashq" rejimi ham shu ro'yxatni
// qayta ishlatadi (mos tur-tab'lar bo'lishi uchun).
export const TURLAR = {
  writing: [
    { tur: "task1", kalit: "mashq_tur_task1" },
    { tur: "task2", kalit: "mashq_tur_task2" },
  ],
  speaking: [
    { tur: "part1", kalit: "mashq_tur_part1" },
    { tur: "part2", kalit: "mashq_tur_part23" },
  ],
};

/** Writing/Speaking uchun tayyor namuna mavzular banki — o'qish uchun,
 * tekshiruvsiz (savol + namuna javob birga ko'rsatiladi). "Haqiqiy mashq"
 * rejimidan farqli — bu yerda talaba hech narsa yozmaydi, faqat o'qiydi. */
export default function NamunaMavzular({ bolim }) {
  const { t } = useI18n();
  const turlar = TURLAR[bolim] || [];
  const [tur, setTur] = useState(turlar[0]?.tur);
  const [royxat, setRoyxat] = useState(null);
  const [tanlangan, setTanlangan] = useState(null);

  useEffect(() => {
    if (tur) {
      setRoyxat(null);
      setTanlangan(null);
      api(`/api/mashqlar/?bolim=${bolim}&tur=${tur}`).then(setRoyxat).catch(() => {});
    }
  }, [bolim, tur]);

  async function ochish(id) {
    const m = await api(`/api/mashqlar/${id}/`);
    setTanlangan(m);
  }

  return (
    <>
      <div className="tab-guruh" style={{ marginBottom: 12 }}>
        {turlar.map((tt) => (
          <button
            key={tt.tur}
            className={tur === tt.tur ? "aktiv" : ""}
            onClick={() => {
              setTur(tt.tur);
              setTanlangan(null);
            }}
          >
            {t(tt.kalit)}
          </button>
        ))}
      </div>

      {!tanlangan && (
        <div className="karta">
          {royxat === null && <div className="yuklanmoqda">{t("yuklanmoqda")}</div>}
          {royxat && royxat.length === 0 && <span className="izoh">{t("namuna_royxat_boshi")}</span>}
          {royxat && royxat.map((m) => (
            <div key={m.id} className="mashq-royxat-el" onClick={() => ochish(m.id)}>
              <span>{m.name}</span>
            </div>
          ))}
        </div>
      )}

      {tanlangan && (
        <div className="karta">
          <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
            <button className="tugma ikkinchi" onClick={() => setTanlangan(null)}>
              {t("namuna_yopish")}
            </button>
          </div>
          {(() => {
            const { matn, svgUrl } = svgAjrat(tanlangan.matn);
            return (
              <>
                <div className="mashq-passage">{matn}</div>
                {svgUrl && (
                  <img src={svgUrl} alt="chart" style={{ maxWidth: "100%", marginBottom: 18 }} />
                )}
              </>
            );
          })()}
          {tanlangan.namuna_javob && (
            <>
              <h3 style={{ marginTop: 16 }}>{t("mashq_namuna_javob")}</h3>
              <div className="mashq-passage">{tanlangan.namuna_javob}</div>
            </>
          )}
        </div>
      )}
    </>
  );
}
