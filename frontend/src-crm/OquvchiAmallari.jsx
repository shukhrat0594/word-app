// Guruhdagi o'quvchi ustidagi ⋮ harakatlar (video-TZ 2026-09-25, SoffCRM
// guruh sahifasi va o'quvchi kartasi): To'lov, Boshqa guruhga ko'chirish,
// Guruhdan chiqarish (sabab bilan), Bitirdi, Lidlarga qaytarish.
//
// Guruh sahifasida ham, o'quvchi kartasida ham AYNAN shu komponent —
// ikki joyda ikki xil oyna bo'lsa, biri sabab so'rab, ikkinchisi so'ramay
// qolardi va "Ketish hisoboti" to'liq chiqmasdi.

import { useState } from "react";

import { api } from "./api.js";
import { useFilial } from "./filialContext.jsx";
import { useI18n } from "./i18n.jsx";
import { useRuxsat } from "./profilContext.jsx";
import { sorovSatri, useSorov } from "./soragich.js";
import TolovQoshishOynasi from "./TolovQoshishOynasi.jsx";

const bugun = () => new Date().toISOString().slice(0, 10);

// Guruhdan ketish sabablari — SoffCRM "O'quvchini guruhdan chetlatish"
// ro'yxati bilan bir xil (backend `KETISH_SABABLARI`).
export const KETISH_SABABLARI = ["narx", "natija", "oqituvchi", "dars_jadvali", "joylashuv", "boshqa"];

/** Umumiy "sabab + izoh" oynasi. `sabablar` bo'lmasa — faqat izoh.
 *  `izohMajburiy(sabab)` — izoh qaysi sababda majburiy. */
export function SababOynasi({
  sarlavha, izoh: tushuntirish = null, sabablar = null, izohMajburiy = () => true, sanaBilan = false,
  tasdiqMatni = null, xavfli = false, onYopish, onTasdiq, children = null,
}) {
  const { t } = useI18n();
  const [sabab, setSabab] = useState("");
  const [matn, setMatn] = useState("");
  const [sana, setSana] = useState(bugun());
  const [band, setBand] = useState(false);
  const [xato, setXato] = useState("");

  async function tasdiqla() {
    setXato("");
    if (sabablar && !sabab) return setXato(t("sabab_tanlang"));
    if (izohMajburiy(sabab) && !matn.trim()) return setXato(t("izoh_majburiy"));
    setBand(true);
    try {
      await onTasdiq({ sabab, izoh: matn.trim(), sana });
      onYopish();
    } catch (e) {
      setXato(e.message);
    } finally {
      setBand(false);
    }
  }

  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna">
        <h2>{sarlavha}</h2>
        {tushuntirish && <p className="kichik">{tushuntirish}</p>}
        {children}
        {sabablar && (
          <label>{t("sabab")} *
            <select value={sabab} onChange={(e) => setSabab(e.target.value)} autoFocus>
              <option value="">{t("tanlang")}</option>
              {sabablar.map(([k, nomi]) => <option key={k} value={k}>{nomi}</option>)}
            </select>
          </label>
        )}
        <label>{t("izoh")}{izohMajburiy(sabab) ? " *" : ""}
          <textarea rows={3} maxLength={300} value={matn} onChange={(e) => setMatn(e.target.value)}
                    autoFocus={!sabablar} />
        </label>
        {sanaBilan && (
          <label>{t("sana")}<input type="date" value={sana} onChange={(e) => setSana(e.target.value)} /></label>
        )}
        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
          <button className={`tugma${xavfli ? " tugma-xavfli" : ""}`} type="button" onClick={tasdiqla} disabled={band}>
            {tasdiqMatni || t("tasdiqlash")}
          </button>
        </div>
      </div>
    </div>
  );
}

/** Muzlatish oynasi (SoffCRM "O'quvchini statusini o'zgartirish"): sana + izoh. */
export function MuzlatishOynasi({ azolikId, talabaIsmi, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  return (
    <SababOynasi
      sarlavha={`${t("muzlatish")} — ${talabaIsmi}`}
      izoh={t("muzlatish_izoh")}
      sanaBilan
      izohMajburiy={() => true}
      onYopish={onYopish}
      onTasdiq={async ({ izoh, sana }) => {
        await api(`/api/crm/azoliklar/${azolikId}/`, {
          method: "PATCH", body: { holat: "muzlatilgan", muzlatish_sana: sana, muzlatish_izoh: izoh },
        });
        onSaqlandi?.();
      }}
    />
  );
}

function KochirishOynasi({ guruhId, talaba, onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const { tanlangan } = useFilial();
  const guruhlar = useSorov("/api/crm/guruhlar/" + sorovSatri({ filial: tanlangan }));
  const [yangi, setYangi] = useState("");
  const variantlar = (guruhlar.malumot || []).filter((g) => g.id !== guruhId);
  return (
    <SababOynasi
      sarlavha={`${t("boshqa_guruhga_kochirish")} — ${talaba.ism}`}
      izoh={t("kochirish_tushuntirish")}
      sanaBilan
      izohMajburiy={() => false}
      onYopish={onYopish}
      onTasdiq={async ({ izoh, sana }) => {
        if (!yangi) throw new Error(t("yangi_guruh_tanlang"));
        await api(`/api/crm/guruhlar/${guruhId}/talabalar/amal/`, {
          method: "POST", body: { amal: "kochirish", talaba_id: talaba.id, yangi_guruh_id: Number(yangi), sana, izoh },
        });
        onSaqlandi?.();
      }}
    >
      <label>{t("kochiriladigan_guruh")} *
        <select value={yangi} onChange={(e) => setYangi(e.target.value)} autoFocus>
          <option value="">{t("tanlang")}</option>
          {variantlar.map((g) => (
            <option key={g.id} value={g.id}>{g.nomi}{g.oqituvchi ? ` · ${g.oqituvchi}` : ""}</option>
          ))}
        </select>
      </label>
    </SababOynasi>
  );
}

/** ⋮ tugma va uning oynalari. `talaba` — {id, ism, telefon, balans}. */
export default function OquvchiMenyusi({ guruhId, guruhNomi, talaba, onOzgardi }) {
  const { t } = useI18n();
  const ruxsat = useRuxsat();
  const [ochiq, setOchiq] = useState(false);
  const [oyna, setOyna] = useState(null);
  const boshqarish = ruxsat("guruhlar.talaba_qoshish");

  const amal = (body) => api(`/api/crm/guruhlar/${guruhId}/talabalar/amal/`, {
    method: "POST", body: { talaba_id: talaba.id, ...body },
  });
  const tanla = (nomi) => () => { setOchiq(false); setOyna(nomi); };

  if (!boshqarish && !ruxsat("moliya.tolov")) return null;

  return (
    <span className="harakat-oram">
      <button className="tugma tugma-sokin kichik-tugma" type="button" aria-label={t("harakatlar")}
              onClick={() => setOchiq(!ochiq)}>⋮</button>
      {ochiq && (
        <div className="harakat-menyu" onMouseLeave={() => setOchiq(false)}>
          {ruxsat("moliya.tolov") && <button type="button" onClick={tanla("tolov")}>💵 {t("tolov")}</button>}
          {boshqarish && (
            <>
              <button type="button" onClick={tanla("kochirish")}>🔀 {t("boshqa_guruhga_kochirish")}</button>
              <button type="button" onClick={tanla("chiqarish")}>🚪 {t("guruhdan_chiqarish")}</button>
              <button type="button" onClick={tanla("bitirdi")}>🎓 {t("bitirdi")}</button>
              <button type="button" onClick={tanla("lidga")}>↩ {t("lidlarga_qaytarish")}</button>
            </>
          )}
        </div>
      )}

      {oyna === "tolov" && (
        <TolovQoshishOynasi
          talabaBilan={{ ...talaba, guruhlar: [{ guruh_id: guruhId, guruh: guruhNomi }] }}
          guruhBilan={guruhId}
          onYopish={() => setOyna(null)}
          onSaqlandi={onOzgardi}
        />
      )}
      {oyna === "kochirish" && (
        <KochirishOynasi guruhId={guruhId} talaba={talaba} onYopish={() => setOyna(null)} onSaqlandi={onOzgardi} />
      )}
      {oyna === "chiqarish" && (
        <SababOynasi
          sarlavha={`${t("guruhdan_chiqarish")} — ${talaba.ism}`}
          izoh={t("chiqarish_tushuntirish")}
          sabablar={KETISH_SABABLARI.map((k) => [k, t(`sabab_${k}`)])}
          sanaBilan
          xavfli
          onYopish={() => setOyna(null)}
          onTasdiq={async ({ sabab, izoh, sana }) => {
            await api(
              `/api/crm/guruhlar/${guruhId}/talabalar/` +
                sorovSatri({ talaba: talaba.id, sana, sabab_turi: sabab, sabab: izoh }),
              { method: "DELETE" },
            );
            onOzgardi?.();
          }}
        />
      )}
      {oyna === "bitirdi" && (
        <SababOynasi
          sarlavha={`${t("bitirdi")} — ${talaba.ism}`}
          izoh={t("bitirdi_tushuntirish")}
          sanaBilan
          izohMajburiy={() => false}
          onYopish={() => setOyna(null)}
          onTasdiq={async ({ izoh, sana }) => { await amal({ amal: "bitirdi", izoh, sana }); onOzgardi?.(); }}
        />
      )}
      {oyna === "lidga" && (
        <SababOynasi
          sarlavha={`${t("lidlarga_qaytarish")} — ${talaba.ism}`}
          izoh={t("lidga_tushuntirish")}
          sanaBilan
          onYopish={() => setOyna(null)}
          onTasdiq={async ({ izoh, sana }) => { await amal({ amal: "lidga", izoh, sana }); onOzgardi?.(); }}
        />
      )}
    </span>
  );
}
