// Guruh a'zolari ro'yxati — guruhlar ro'yxatidagi yoyilgan kartada ham,
// alohida guruh sahifasida ham (video-TZ 2026-09-25) shu komponent.
//
// Har o'quvchida holat (sinov / faol / muzlatilgan — muzlatishda sana va
// izoh so'raladi), balans va ⋮ harakatlar (`OquvchiAmallari.jsx`).

import { useState } from "react";

import { api } from "./api.js";
import OquvchiMenyusi, { MuzlatishOynasi } from "./OquvchiAmallari.jsx";
import { useRuxsat } from "./profilContext.jsx";
import { balansMatn, balansSinfi, pul, sana } from "./format.js";
import { useI18n } from "./i18n.jsx";
import { useSorov } from "./soragich.js";

export function NarxManbasi({ manba }) {
  const { t } = useI18n();
  if (!manba) return <span className="belgi rang-qarzdor">{t("narx_yoq")}</span>;
  const nomlar = { kurs: "narx_kursdan", guruh: "narx_guruhdan", talaba: "narx_talabadan", chegirma: "narx_chegirmadan" };
  return <span className="belgi">{t(nomlar[manba])}</span>;
}

const HOLAT_TARTIBI = { faol: 0, sinov: 1, muzlatilgan: 2, arxiv: 3 };

export default function GuruhAzolari({ guruhId, guruhNomi, onOzgardi }) {
  const { t } = useI18n();
  const ruxsat = useRuxsat();
  const { malumot, yuklanmoqda, yangila } = useSorov(`/api/crm/guruhlar/${guruhId}/azoliklar/`);
  // Boshlanish uniti (saytdagi Kurslar bo'limida qaysi Unit'dan boshlaydi).
  // Guruhda daraja bo'lmasa ro'yxat bo'sh — ustun ko'rinmaydi.
  const unitlar = useSorov(`/api/crm/guruhlar/${guruhId}/unitlar/`);
  const unitRoyxati = unitlar.malumot || [];
  // Qidiruv va tartiblash — mijoz tomonida: guruhda 4-8 kishi, server
  // so'rovi shart emas. SoffCRM'da ham shu ikkisi ro'yxat tepasida.
  const [qidiruv, setQidiruv] = useState("");
  const [tartib, setTartib] = useState("ism");
  const azolar = (malumot || [])
    .filter((a) => !qidiruv || `${a.talaba} ${a.telefon || ""}`.toLowerCase().includes(qidiruv.toLowerCase()))
    .sort((a, b) => {
      if (tartib === "balans") return Number(a.balans ?? 0) - Number(b.balans ?? 0);
      if (tartib === "sana") return String(a.boshlanish_sana || "").localeCompare(String(b.boshlanish_sana || ""));
      if (tartib === "holat") return HOLAT_TARTIBI[a.holat] - HOLAT_TARTIBI[b.holat];
      return String(a.talaba).localeCompare(String(b.talaba));
    });

  const [amalXato, setAmalXato] = useState("");
  const [muzlatish, setMuzlatish] = useState(null);

  // Amal xatosi (403/400) jim yutilmasin — foydalanuvchi sababini ko'rsin.
  async function amal(fn) {
    setAmalXato("");
    try {
      await fn();
    } catch (e) {
      setAmalXato(e.message);
    }
  }

  function ozgartir(id, maydon, qiymat) {
    return amal(async () => {
      await api(`/api/crm/azoliklar/${id}/`, { method: "PATCH", body: { [maydon]: qiymat } });
      yangila();
      onOzgardi?.();
    });
  }

  function holatTanla(a, holat) {
    if (holat === "muzlatilgan") return setMuzlatish(a);
    return ozgartir(a.id, "holat", holat);
  }

  // SoffCRM guruh sahifasidagi tugmalar: "O'qishgan sanani ko'rsatish",
  // "Balansni yopish" (ustunni yashirish), "O'quvchilarni faollashtirish",
  // "Arxivdagi o'quvchilarni ko'rish".
  const [sanaKorsin, setSanaKorsin] = useState(true);
  const [balansKorsin, setBalansKorsin] = useState(true);
  const [sobiqKorsin, setSobiqKorsin] = useState(false);
  const sobiqlar = useSorov(sobiqKorsin ? `/api/crm/guruhlar/${guruhId}/sobiqlar/` : null);
  const sinovdagilar = (malumot || []).filter((a) => a.holat === "sinov").length;

  function hammasiniYangila() {
    yangila();
    if (sobiqKorsin) sobiqlar.yangila();
    onOzgardi?.();
  }

  function faollashtir() {
    if (!window.confirm(t("faollashtirish_tasdiq"))) return;
    return amal(async () => {
      await api(`/api/crm/guruhlar/${guruhId}/faollashtirish/`, { method: "POST", body: {} });
      yangila();
      onOzgardi?.();
    });
  }

  if (yuklanmoqda) return <p className="kichik">{t("yuklanmoqda")}</p>;

  return (
    <div className="jadval-oram">
      <div className="filtrlar">
        <input placeholder={t("qidiruv")} value={qidiruv} onChange={(e) => setQidiruv(e.target.value)} />
        <select value={tartib} onChange={(e) => setTartib(e.target.value)} aria-label={t("tartiblash")}>
          <option value="ism">{t("tartib_ism")}</option>
          <option value="balans">{t("tartib_balans")}</option>
          <option value="sana">{t("tartib_sana")}</option>
          <option value="holat">{t("tartib_holat")}</option>
        </select>
        <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={() => setSanaKorsin(!sanaKorsin)}>
          {sanaKorsin ? "🙈" : "👁"} {t("qoshilgan_sana")}
        </button>
        <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={() => setBalansKorsin(!balansKorsin)}>
          {balansKorsin ? "🙈" : "👁"} {t("balans")}
        </button>
        {sinovdagilar > 0 && ruxsat("guruhlar.talaba_qoshish") && (
          <button className="tugma kichik-tugma" type="button" onClick={faollashtir}>
            ✔ {t("oquvchilarni_faollashtirish")} ({sinovdagilar})
          </button>
        )}
      </div>
      {amalXato && <div className="xato">{amalXato}</div>}
      <table>
        <thead>
          <tr>
            <th>{t("talaba")}</th>
            <th>{t("telefon")}</th>
            <th>{t("holat")}</th>
            {sanaKorsin && <th>{t("boshlanish_sana")}</th>}
            {unitRoyxati.length > 0 && <th title={t("boshlanish_uniti_izoh")}>{t("boshlanish_uniti")}</th>}
            <th>{t("narx")}</th>
            {balansKorsin && <th className="ongga">{t("balans")}</th>}
            <th className="ongga">{t("harakatlar")}</th>
          </tr>
        </thead>
        <tbody>
          {azolar.map((a) => (
            <tr key={a.id}>
              <td>{a.talaba}</td>
              <td>{a.telefon || "—"}</td>
              <td>
                {/* Sinov va muzlatilgan talabaga hisob OCHILMAYDI —
                    shuning uchun holat aynan shu yerdan boshqariladi. */}
                <select value={a.holat} onChange={(e) => holatTanla(a, e.target.value)}
                        disabled={!ruxsat("guruhlar.tahrirlash") && !ruxsat("guruhlar.talaba_qoshish")}>
                  {["sinov", "faol", "muzlatilgan"].map((h) => (
                    <option key={h} value={h}>{t(`holat_${h}`)}</option>
                  ))}
                </select>
                {a.holat === "muzlatilgan" && (a.muzlatish_sana || a.muzlatish_izoh) && (
                  <div className="kichik" title={a.muzlatish_izoh}>
                    ❄ {sana(a.muzlatish_sana)}{a.muzlatish_izoh ? ` — ${a.muzlatish_izoh}` : ""}
                  </div>
                )}
              </td>
              {sanaKorsin && (
                <td>
                  <input
                    type="date"
                    value={a.boshlanish_sana || ""}
                    disabled={!ruxsat("guruhlar.tahrirlash")}
                    onChange={(e) => ozgartir(a.id, "boshlanish_sana", e.target.value)}
                  />
                </td>
              )}
              {unitRoyxati.length > 0 && (
                <td>
                  <select value={a.boshlanish_unit_id ?? ""} disabled={!ruxsat("guruhlar.tahrirlash")}
                          title={t("boshlanish_uniti_izoh")} aria-label={t("boshlanish_uniti")}
                          onChange={(e) => ozgartir(a.id, "boshlanish_unit_id", e.target.value || null)}>
                    <option value="">{t("boshlanish_uniti_standart")}</option>
                    {unitRoyxati.map((u) => <option key={u.id} value={u.id}>{u.nomi}</option>)}
                  </select>
                </td>
              )}
              <td>
                {a.narx_talabaga ? pul(a.narx_talabaga) : pul(a.narx)}{" "}
                <NarxManbasi manba={a.narx_manbasi} />
              </td>
              {balansKorsin && <td className={`ongga ${balansSinfi(a.balans)}`}>{balansMatn(a.balans)}</td>}
              <td className="ongga">
                <OquvchiMenyusi
                  guruhId={guruhId}
                  guruhNomi={guruhNomi}
                  talaba={{ id: a.talaba_id, ism: a.talaba, telefon: a.telefon, balans: a.balans }}
                  onOzgardi={hammasiniYangila}
                />
              </td>
            </tr>
          ))}
          {azolar.length === 0 && (
            <tr><td colSpan={8} className="bosh">{t("yozuv_yoq")}</td></tr>
          )}
        </tbody>
      </table>
      <button className="havola rang-qarzdor" type="button" onClick={() => setSobiqKorsin(!sobiqKorsin)}>
        🗄 {sobiqKorsin ? t("yopish") : t("arxivdagi_oquvchilar")}
      </button>
      {sobiqKorsin && (
        <table>
          <thead>
            <tr>
              <th>{t("talaba")}</th><th>{t("boshlanish_sana")}</th><th>{t("chiqqan_sana")}</th>
              <th>{t("sabab")}</th><th className="ongga">{t("balans")}</th>
            </tr>
          </thead>
          <tbody>
            {(sobiqlar.malumot || []).map((x, i) => (
              <tr key={i} className="qator-sokin">
                <td>{x.talaba}</td><td>{sana(x.boshlagan_sana)}</td><td>{sana(x.sana)}</td>
                <td>
                  {t(`sabab_${x.sabab_turi}`)}
                  {x.sabab && <span className="kichik"> — {x.sabab}</span>}
                </td>
                <td className={`ongga ${balansSinfi(x.balans)}`}>{x.balans === null ? "—" : balansMatn(x.balans)}</td>
              </tr>
            ))}
            {!sobiqlar.yuklanmoqda && (sobiqlar.malumot || []).length === 0 && (
              <tr><td colSpan={5} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
        </table>
      )}
      {muzlatish && (
        <MuzlatishOynasi azolikId={muzlatish.id} talabaIsmi={muzlatish.talaba}
                         onYopish={() => setMuzlatish(null)} onSaqlandi={() => { yangila(); onOzgardi?.(); }} />
      )}
    </div>
  );
}
