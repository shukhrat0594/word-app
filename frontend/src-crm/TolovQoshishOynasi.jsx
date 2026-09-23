// "To'lov qo'shish" oynasi — Moliya bo'limidagi umumiy tugma (2026-09-17,
// admin talabi, SoffCRM'dagi "TO'LOV" oynasiga o'xshash):
//   o'quvchini qidirish (ism/telefon) -> guruh -> oy -> summa -> bonus
//   -> izoh -> sana.
//
// `TolovOynasi`dan farqi: u BITTA hisobdan (qatordan) ochiladi, bu esa
// talabani NOLDAN topadi. Yozish mantiqi bir xil — `POST /api/crm/tolov/`.
// Bonus ALOHIDA yozuv (turi="bonus"): u kassaga pul emas, hisobotda
// alohida ustun (TZ 3.8), shuning uchun to'lov bilan qo'shib yuborilmaydi.

import { useEffect, useState } from "react";

import { api } from "./api.js";
import { useFilial } from "./filialContext.jsx";
import { balansMatn, balansSinfi, pul } from "./format.js";
import { useI18n } from "./i18n.jsx";
import UsulTanlash from "./TolovUsuli.jsx";
import { sorovSatri, useSorov } from "./soragich.js";

export default function TolovQoshishOynasi({ onYopish, onSaqlandi }) {
  const { t } = useI18n();
  const { tanlangan, filiallar } = useFilial();
  const [qidiruv, setQidiruv] = useState("");
  const [talaba, setTalaba] = useState(null);
  const [guruhId, setGuruhId] = useState("");
  const [hisobId, setHisobId] = useState("");
  const [summa, setSumma] = useState("");
  const [bonus, setBonus] = useState("");
  const [izoh, setIzoh] = useState("");
  const [sana, setSana] = useState(new Date().toISOString().slice(0, 10));
  const [usul, setUsul] = useState("naqd");
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);

  // Qidiruv — sarlavhadagi filial bo'yicha cheklanadi (Shuhrat, 09-17).
  const natijalar = useSorov(
    qidiruv.trim().length >= 2 && !talaba
      ? "/api/crm/talabalar/" + sorovSatri({ q: qidiruv.trim(), filial: tanlangan })
      : null
  );
  const oylar = useSorov(
    talaba && guruhId
      ? "/api/crm/hisoblar/" + sorovSatri({ talaba: talaba.id, guruh: guruhId })
      : null
  );

  // Guruh bitta bo'lsa — o'zi tanlanadi.
  useEffect(() => {
    if (talaba && talaba.guruhlar.length === 1) setGuruhId(String(talaba.guruhlar[0].guruh_id));
  }, [talaba]);

  // Oylar kelganda — eng eski TO'LANMAGAN oy tanlanadi, summa = qoldiq.
  useEffect(() => {
    const royxat = oylar.malumot || [];
    if (!royxat.length) {
      setHisobId("");
      return;
    }
    const tartib = [...royxat].sort((a, b) => String(a.oy).localeCompare(String(b.oy)));
    const birinchi = tartib.find((h) => h.holat !== "tolandi") || tartib[tartib.length - 1];
    setHisobId(String(birinchi.id));
    setSumma(String(Number(birinchi.qoldiq) > 0 ? Number(birinchi.qoldiq) : ""));
  }, [oylar.malumot]);

  const hisob = (oylar.malumot || []).find((h) => String(h.id) === hisobId) || null;
  const filialNomi = (id) => filiallar.find((f) => String(f.id) === String(id))?.nomi;

  async function yubor(turi, miqdor) {
    await api("/api/crm/tolov/", {
      method: "POST",
      body: {
        talaba_id: talaba.id,
        guruh_id: Number(guruhId),
        hisob_id: hisob?.id ?? null,
        summa: String(miqdor),
        turi,
        sana,
        usul,
        izoh,
      },
    });
  }

  async function saqla() {
    setXato("");
    if (!talaba || !guruhId) {
      setXato(t("guruh_talaba_kerak"));
      return;
    }
    if (!hisob) {
      setXato(t("hisob_topilmadi"));
      return;
    }
    const s = Number(summa || 0);
    const b = Number(bonus || 0);
    if (!(s > 0) && !(b > 0)) {
      setXato(t("summa_kerak"));
      return;
    }
    setBand(true);
    try {
      if (s > 0) await yubor("tolov", s);
      if (b > 0) await yubor("bonus", b);
      onSaqlandi?.();
      onYopish();
    } catch (e) {
      setXato(e.message || "Xato");
    } finally {
      setBand(false);
    }
  }

  return (
    <div className="oyna-fon" role="dialog" aria-modal="true">
      <div className="karta oyna">
        <h2>{t("tolov_qoshish")}</h2>

        <label>
          {t("talaba_qidirish")}
          {talaba ? (
            <div className="qator">
              <span>
                <b>{talaba.ism}</b>
                <span className="kichik"> {talaba.telefon || ""}</span>
                {" · "}
                <span className={balansSinfi(talaba.balans)}>{balansMatn(talaba.balans)}</span>
              </span>
              <button className="havola" type="button"
                      onClick={() => { setTalaba(null); setGuruhId(""); setHisobId(""); setSumma(""); }}>
                ✕
              </button>
            </div>
          ) : (
            <input value={qidiruv} onChange={(e) => setQidiruv(e.target.value)} autoFocus />
          )}
        </label>
        {!talaba && (natijalar.malumot || []).length > 0 && (
          <div className="qidiruv-natija">
            {natijalar.malumot.slice(0, 20).map((x) => (
              <button key={x.id} type="button" onClick={() => { setTalaba(x); setQidiruv(""); }}>
                {x.ism} <span className="kichik">{x.telefon || ""} · {x.guruhlar.map((g) => g.guruh).join(", ")}</span>
              </button>
            ))}
          </div>
        )}
        {!talaba && qidiruv.trim().length >= 2 && !natijalar.yuklanmoqda && (natijalar.malumot || []).length === 0 && (
          <p className="kichik">{t("yozuv_yoq")}</p>
        )}

        {talaba && (
          <>
            <label>
              {t("qaysi_guruh")}
              <select value={guruhId} onChange={(e) => setGuruhId(e.target.value)}>
                <option value="">{t("tanlang")}</option>
                {talaba.guruhlar.map((g) => (
                  <option key={g.guruh_id} value={g.guruh_id}>
                    {g.guruh}{filialNomi(g.filial_id) ? ` · ${filialNomi(g.filial_id)}` : ""}
                  </option>
                ))}
              </select>
            </label>

            {guruhId && (
              <label>
                {t("qaysi_oy")}
                <select value={hisobId} onChange={(e) => {
                  setHisobId(e.target.value);
                  const h = (oylar.malumot || []).find((x) => String(x.id) === e.target.value);
                  if (h) setSumma(String(Number(h.qoldiq) > 0 ? Number(h.qoldiq) : ""));
                }}>
                  {(oylar.malumot || []).length === 0 && <option value="">{t("hisob_topilmadi")}</option>}
                  {[...(oylar.malumot || [])]
                    .sort((a, b) => String(b.oy).localeCompare(String(a.oy)))
                    .map((h) => (
                      <option key={h.id} value={h.id}>
                        {String(h.oy).slice(0, 7)} — {pul(h.qoldiq)} ({t(`holat_${h.holat}`)})
                      </option>
                    ))}
                </select>
              </label>
            )}

            {hisob && (
              <div className="qator">
                <span className="kichik">{t("hisoblangan")} / {t("qoldiq")}</span>
                <b>{pul(hisob.summa)} / {pul(hisob.qoldiq)}</b>
              </div>
            )}

            <label>
              {t("summa")}
              <input type="number" min="0" step="1000" value={summa} onChange={(e) => setSumma(e.target.value)} />
            </label>
            <label>
              {t("bonus_summa")}
              <input type="number" min="0" step="1000" value={bonus} onChange={(e) => setBonus(e.target.value)} />
            </label>
            <label>
              {t("izoh")}
              <input value={izoh} onChange={(e) => setIzoh(e.target.value)} maxLength={300} />
            </label>
            <UsulTanlash qiymat={usul} onChange={setUsul} />
            <label>
              {t("sana")}
              <input type="date" value={sana} onChange={(e) => setSana(e.target.value)} />
            </label>
          </>
        )}

        {xato && <div className="xato">{xato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma tugma-sokin" type="button" onClick={onYopish}>{t("bekor")}</button>
          <button className="tugma" type="button" onClick={saqla} disabled={band || !talaba}>{t("saqlash")}</button>
        </div>
      </div>
    </div>
  );
}
