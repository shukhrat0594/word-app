import { useEffect, useRef, useState } from "react";
import { api, apiBlobUrl } from "../api";
import { useI18n } from "../i18n";

/** Sahifa suratidan (foizdagi qutiga qarab) kichik nusxa (thumbnail)
 * data-URL sifatida kesib oladi — MIJOZ TOMONIDA (canvas), qayta so'rov
 * yubormasdan, chunki bitta sahifa surati allaqachon yuklangan bo'ladi.
 * Faqat KO'RISH uchun — haqiqiy (to'liq sifatli) kesish saqlashda
 * serverda (`rasmni_kes`) amalga oshadi. */
function kesimDataUrl(imgEl, quti) {
  if (!imgEl || !imgEl.naturalWidth || !quti) return null;
  const W = imgEl.naturalWidth;
  const H = imgEl.naturalHeight;
  const x1 = Math.max(0, Math.round((quti.x1 / 100) * W));
  const y1 = Math.max(0, Math.round((quti.y1 / 100) * H));
  const x2 = Math.min(W, Math.round((quti.x2 / 100) * W));
  const y2 = Math.min(H, Math.round((quti.y2 / 100) * H));
  const w = Math.max(1, x2 - x1);
  const h = Math.max(1, y2 - y1);
  try {
    const kanvas = document.createElement("canvas");
    kanvas.width = w;
    kanvas.height = h;
    const ctx = kanvas.getContext("2d");
    ctx.drawImage(imgEl, x1, y1, w, h, 0, 0, w, h);
    return kanvas.toDataURL("image/jpeg", 0.85);
  } catch {
    return null;
  }
}

/** Bitta sahifaning surati ustida rasm-qutilarini (AI aniqlagan chegaralar)
 * sudrab ko'chirish / burchagidan o'lchamini o'zgartirish imkonini beradi
 * (2026-08-03) — AI koordinatasi ba'zan noto'g'ri bo'lgani uchun (yuzlar
 * kesilib qolishi, qo'shni suratga aralashib ketishi) admin shu yerda
 * tasdiqlashdan oldin to'g'irlaydi. Surat elementini (`imgRef`) OTA
 * komponentga beradi — u orqali boshqa joyda (har mashqning rasm
 * bloklari yonida) kichik nusxalar kesib olinadi, qayta yuklanmasdan."""*/
function QutiTahrirlagich({ rasmUrl, imgRef, qutilar, onChange }) {
  const konteynerRef = useRef(null);
  const surinishRef = useRef(null);

  function davomEttirish(e) {
    const s = surinishRef.current;
    if (!s || !konteynerRef.current) return;
    const rect = konteynerRef.current.getBoundingClientRect();
    const dx = ((e.clientX - s.boshX) / rect.width) * 100;
    const dy = ((e.clientY - s.boshY) / rect.height) * 100;
    const q = { ...s.boshQuti };
    if (s.mod === "kochir") {
      q.x1 += dx; q.x2 += dx; q.y1 += dy; q.y2 += dy;
    } else if (s.mod === "yuqori-chap") {
      q.x1 += dx; q.y1 += dy;
    } else {
      q.x2 += dx; q.y2 += dy;
    }
    for (const k of ["x1", "y1", "x2", "y2"]) q[k] = Math.max(0, Math.min(100, q[k]));
    const yangi = [...qutilar];
    yangi[s.i] = q;
    onChange(yangi);
  }

  function tugatish() {
    surinishRef.current = null;
    window.removeEventListener("mousemove", davomEttirish);
    window.removeEventListener("mouseup", tugatish);
  }

  function boshlash(e, i, mod) {
    e.preventDefault();
    e.stopPropagation();
    surinishRef.current = { i, mod, boshX: e.clientX, boshY: e.clientY, boshQuti: { ...qutilar[i] } };
    window.addEventListener("mousemove", davomEttirish);
    window.addEventListener("mouseup", tugatish);
  }

  if (!rasmUrl) return <div className="yuklanmoqda">…</div>;

  return (
    <div ref={konteynerRef} className="blok-tasdiq-rasm-konteyner">
      <img ref={imgRef} src={rasmUrl} alt="" draggable={false} />
      {qutilar.map((q, i) => (
        <div
          key={i}
          className="blok-tasdiq-quti"
          style={{
            left: `${q.x1}%`, top: `${q.y1}%`,
            width: `${Math.max(0, q.x2 - q.x1)}%`, height: `${Math.max(0, q.y2 - q.y1)}%`,
          }}
          onMouseDown={(e) => boshlash(e, i, "kochir")}
        >
          <span className="blok-tasdiq-quti-raqam">{i + 1}</span>
          <div
            className="blok-tasdiq-tutqich"
            style={{ left: -6, top: -6 }}
            onMouseDown={(e) => boshlash(e, i, "yuqori-chap")}
          />
          <div
            className="blok-tasdiq-tutqich"
            style={{ right: -6, bottom: -6 }}
            onMouseDown={(e) => boshlash(e, i, "past-ong")}
          />
        </div>
      ))}
    </div>
  );
}

/** Rasm-quti(lar)ga ega blok turlarining kichik nusxasi + izoh/matn
 * maydoni — foydalanuvchi talabi (2026-08-03): "matnni tahrirlashni
 * jsonda qilmasdan har bir rasm yoniga qo'ysa bo'ladimi".
 *
 * `onOchir` (2026-08-10, ixtiyoriy) — berilsa, kichik 🗑️ tugma chiqadi:
 * bosilsa shu rasmni (yoki rasm qatoridagi bitta elementni) mashqdan
 * BUTUNLAY olib tashlaydi (matn/savolga tegmaydi).*/
function RasmVaIzoh({ imgEl, quti, izoh, izohOzgardi, izohNomi, onOchir }) {
  const { t } = useI18n();
  const url = kesimDataUrl(imgEl, quti);
  return (
    <div className="blok-tasdiq-rasm-izoh">
      {url ? <img src={url} alt="" /> : <div className="blok-tasdiq-rasm-yoq">—</div>}
      <input
        type="text"
        value={izoh || ""}
        onChange={(e) => izohOzgardi(e.target.value)}
        placeholder={izohNomi}
      />
      {onOchir && (
        <button
          type="button"
          className="tugma ikkinchi kichik"
          style={{ color: "#d33" }}
          title={t("ochirish")}
          onClick={onOchir}
        >
          🗑️
        </button>
      )}
    </div>
  );
}

/** Rasm matnga nisbatan qayerda turishi (2026-08-10, foydalanuvchi
 * talabi: "rasmni matnning qaysi tomonida turishini aniqlaydigan
 * funksiya kerak"). Talaba ko'rinishida `BlokMashqi` shu qiymatga qarab
 * chizadi: chap/o'ng — CSS float (matn rasm atrofida oqadi, kitobdagidek),
 * past — rasm mashq oxiriga suriladi, tepa (standart) — hozirgidek. */
const TOMONLAR = ["tepa", "past", "chap", "ong"];

/** Bitta rasm bloki uchun boshqaruv qatori: tomon tanlovi + shu rasmni
 * boshqa mashqqa ulash (2026-08-10). */
function RasmBoshqaruvi({ blok, oz, sahifaIndeks, mashqIdx, barchaMashqlar, onUlash }) {
  const { t } = useI18n();
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
      <select value={blok.tomon || "tepa"} onChange={(e) => oz({ tomon: e.target.value })}>
        {TOMONLAR.map((x) => (
          <option key={x} value={x}>{t(`kurs_rasm_tomon_${x}`)}</option>
        ))}
      </select>
      {onUlash && (
        <select
          value=""
          onChange={(e) => {
            if (!e.target.value) return;
            const [s, m] = e.target.value.split(":").map(Number);
            onUlash(s, m);
          }}
        >
          <option value="">{t("kurs_blok_tasdiq_ulash_tanlang")}</option>
          {barchaMashqlar
            .filter((x) => !(x.sahifaIndeks === sahifaIndeks && x.mashqIdx === mashqIdx))
            .map((x) => (
              <option key={`${x.sahifaIndeks}:${x.mashqIdx}`} value={`${x.sahifaIndeks}:${x.mashqIdx}`}>
                {t("kurs_blok_tasdiq_sahifa")} {x.sahifaIndeks + 1} — {x.mashq.raqam ? `#${x.mashq.raqam}` : (x.mashq.sarlavha || t("kurs_mashq"))}
              </option>
            ))}
        </select>
      )}
      {blok.ulash && (
        <button type="button" className="tugma ikkinchi kichik" onClick={() => oz({ ulash: null })}>
          🔗 {t("kurs_blok_tasdiq_ulashni_uzish")}
        </button>
      )}
    </div>
  );
}

/** Bitta blokning STRUKTURAVIY (JSON emas) tahrirlagichi — turiga qarab
 * mos maydon(lar) ko'rsatadi. Rasm-quti o'zi (koordinata) yuqoridagi
 * `QutiTahrirlagich`da tuzatiladi — bu yerda faqat MATN/IZOH. */
const SAVOL_BOGLIQ_TURLAR = new Set(["mashq", "rasm_javobli", "rasm_javobli_grid"]);

function MashqgaKochirMaydoni({ joriyRaqam, onKochir }) {
  const { t } = useI18n();
  return (
    <input
      type="text"
      className="blok-tasdiq-mashqga-kochir"
      title={t("kurs_blok_tasdiq_mashqqa_kochir")}
      value={joriyRaqam ?? ""}
      onChange={(e) => onKochir(e.target.value)}
      style={{ width: 44, marginLeft: 6, textAlign: "center" }}
    />
  );
}

function BlokTahrir({
  blok, blokIdx, qutilar, imgEl, onChange, mashqRaqami, onMashqgaKochir, onBlokOchir,
  sahifaIndeks, mashqIdx, barchaMashqlar, onUlash,
}) {
  const { t } = useI18n();

  function oz(patch) {
    onChange(blokIdx, patch);
  }
  function itemOz(itemlarMaydoni, itemIdx, patch) {
    const yangi = [...(blok[itemlarMaydoni] || [])];
    yangi[itemIdx] = { ...yangi[itemIdx], ...patch };
    onChange(blokIdx, { [itemlarMaydoni]: yangi });
  }
  const kochirMaydoni =
    onMashqgaKochir && !SAVOL_BOGLIQ_TURLAR.has(blok.tur) ? (
      <MashqgaKochirMaydoni joriyRaqam={mashqRaqami} onKochir={(v) => onMashqgaKochir(blokIdx, v)} />
    ) : null;

  switch (blok.tur) {
    case "sarlavha":
    case "bolim_sarlavha":
    case "korsatma":
      return (
        <div className="blok-tasdiq-satr">
          <span className="blok-tasdiq-tur-belgi">{blok.tur}{blok.raqam ? ` #${blok.raqam}` : ""}</span>
          <input type="text" value={blok.matn || ""} onChange={(e) => oz({ matn: e.target.value })} />
          {kochirMaydoni}
        </div>
      );
    case "matn":
    case "pufakcha":
      return (
        <div className="blok-tasdiq-satr">
          <span className="blok-tasdiq-tur-belgi">{blok.tur}</span>
          <input type="text" value={blok.matn || ""} onChange={(e) => oz({ matn: e.target.value })} />
          {kochirMaydoni}
        </div>
      );
    case "soz_banki":
      return (
        <div className="blok-tasdiq-satr">
          <span className="blok-tasdiq-tur-belgi">{t("kurs_blok_tasdiq_soz_banki")}</span>
          <input
            type="text"
            value={(blok.qatorlar || []).join(", ")}
            onChange={(e) => oz({ qatorlar: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
          />
          {kochirMaydoni}
        </div>
      );
    case "grammar_spot":
      return (
        <div className="blok-tasdiq-blok-guruh">
          <div className="blok-tasdiq-satr">
            <span className="blok-tasdiq-tur-belgi">GRAMMAR SPOT</span>
            <input type="text" value={blok.sarlavha || ""} onChange={(e) => oz({ sarlavha: e.target.value })} />
            {kochirMaydoni}
          </div>
          {(blok.qatorlar || []).map((q, i) => (
            <input
              key={i}
              type="text"
              className="blok-tasdiq-qator-input"
              value={typeof q === "string" ? q : q.matn || ""}
              onChange={(e) => {
                const yangi = [...blok.qatorlar];
                yangi[i] = e.target.value;
                oz({ qatorlar: yangi });
              }}
            />
          ))}
        </div>
      );
    case "dialog":
      return (
        <div className="blok-tasdiq-blok-guruh">
          <span className="blok-tasdiq-tur-belgi">dialog{kochirMaydoni}</span>
          {(blok.qatorlar || []).map((q, i) => (
            <div key={i} className="blok-tasdiq-dialog-qator">
              <input
                type="text"
                className="blok-tasdiq-dialog-kim"
                value={q.kim || ""}
                onChange={(e) => itemOz("qatorlar", i, { kim: e.target.value })}
              />
              <input
                type="text"
                value={q.gap || ""}
                onChange={(e) => itemOz("qatorlar", i, { gap: e.target.value })}
              />
            </div>
          ))}
        </div>
      );
    case "rasm":
      return (
        <div className="blok-tasdiq-satr" style={{ flexWrap: "wrap" }}>
          <RasmVaIzoh
            imgEl={imgEl}
            quti={qutilar[blok.rasm_idx]}
            izoh={blok.izoh}
            izohOzgardi={(v) => oz({ izoh: v })}
            izohNomi={t("kurs_blok_tasdiq_rasm_izoh")}
            onOchir={onBlokOchir ? () => onBlokOchir(blokIdx) : undefined}
          />
          <RasmBoshqaruvi
            blok={blok}
            oz={oz}
            sahifaIndeks={sahifaIndeks}
            mashqIdx={mashqIdx}
            barchaMashqlar={barchaMashqlar}
            onUlash={onUlash ? (s, m) => onUlash(s, m, blokIdx) : undefined}
          />
          {kochirMaydoni}
        </div>
      );
    case "rasm_qatori":
      return (
        <div className="blok-tasdiq-satr">
          <div className="blok-tasdiq-rasm-qatori">
            {(blok.qator || []).map((it, i) => (
              <RasmVaIzoh
                key={i}
                imgEl={imgEl}
                quti={qutilar[it.rasm_idx]}
                izoh={it.matn || it.izoh}
                izohOzgardi={(v) => itemOz("qator", i, { matn: v })}
                izohNomi={t("kurs_blok_tasdiq_rasm_izoh")}
                onOchir={() => oz({ qator: blok.qator.filter((_, k) => k !== i) })}
              />
            ))}
          </div>
          {kochirMaydoni}
        </div>
      );
    case "rasm_javobli":
      return (
        <RasmVaIzoh
          imgEl={imgEl}
          quti={qutilar[blok.rasm_idx]}
          izoh={blok.raqam}
          izohOzgardi={(v) => oz({ raqam: v })}
          izohNomi={t("kurs_blok_tasdiq_raqam")}
        />
      );
    case "rasm_javobli_grid":
      return (
        <div className="blok-tasdiq-rasm-qatori">
          {(blok.itemlar || []).map((it, i) => (
            <RasmVaIzoh
              key={i}
              imgEl={imgEl}
              quti={qutilar[it.rasm_idx]}
              izoh={it.raqam}
              izohOzgardi={(v) => itemOz("itemlar", i, { raqam: v })}
              izohNomi={t("kurs_blok_tasdiq_raqam")}
            />
          ))}
        </div>
      );
    case "mashq": {
      const matn = (blok.bolaklar || [])
        .map((b) => (b.bosh_joy ? "____" : b.matn || ""))
        .join("");
      return (
        <div className="blok-tasdiq-satr">
          <span className="blok-tasdiq-tur-belgi">{t("kurs_blok_tasdiq_mashq_gap")}</span>
          <span className="izoh">{matn}</span>
        </div>
      );
    }
    default:
      return blok.matn ? (
        <div className="blok-tasdiq-satr">
          <span className="blok-tasdiq-tur-belgi">{blok.tur}</span>
          <input type="text" value={blok.matn} onChange={(e) => oz({ matn: e.target.value })} />
        </div>
      ) : null;
  }
}

/** Bitta ANIQLANGAN mashq (kitobda bosilgan raqami bilan) — sarlavha,
 * bloklari (strukturaviy tahrir) va savollari (to'g'ri javob) bilan
 * (2026-08-03: avval BUTUN sahifa bitta JSON edi, endi har mashq
 * alohida karta). */
function MashqKartasi({
  mashq, mashqIdx, qutilar, imgEl, onChange, onOchir, onBlokKochir,
  sahifaIndeks, barchaMashqlar, onUlash, onRasmQoshish,
}) {
  const { t } = useI18n();

  function maydonOz(patch) {
    onChange(mashqIdx, patch);
  }
  function blokOz(blokIdx, patch) {
    const yangi = [...mashq.bloklar];
    yangi[blokIdx] = { ...yangi[blokIdx], ...patch };
    maydonOz({ bloklar: yangi });
  }
  function blokniOchir(blokIdx) {
    maydonOz({ bloklar: mashq.bloklar.filter((_, i) => i !== blokIdx) });
  }
  function javobOz(savolIdx, qiymat) {
    const yangi = mashq.savollar.map((s, i) => (i === savolIdx ? { ...s, togri: qiymat } : s));
    maydonOz({ savollar: yangi });
  }
  function erkinOz(savolIdx, qiymat) {
    const yangi = mashq.savollar.map((s, i) => (i === savolIdx ? { ...s, erkin: qiymat } : s));
    maydonOz({ savollar: yangi });
  }

  return (
    <div className="blok-tasdiq-mashq-karta">
      <div className="blok-tasdiq-mashq-sarlavha-qator">
        <span className="blok-tasdiq-mashq-raqam">{t("kurs_mashq")}</span>
        <input
          type="text"
          value={mashq.raqam ?? ""}
          onChange={(e) => maydonOz({ raqam: e.target.value })}
          style={{ width: 44, textAlign: "center" }}
        />
        <input
          type="text"
          value={mashq.sarlavha || ""}
          onChange={(e) => maydonOz({ sarlavha: e.target.value })}
          placeholder={t("kurs_blok_tasdiq_sarlavha")}
          style={{ flex: 1 }}
        />
        <label className="izoh" style={{ display: "flex", alignItems: "center", gap: 4, whiteSpace: "nowrap" }}>
          <input
            type="checkbox"
            checked={!!mashq.audio_kerak}
            onChange={(e) => maydonOz({ audio_kerak: e.target.checked })}
          />
          {t("kurs_blok_tasdiq_audio_kerak")}
        </label>
        <button type="button" className="tugma ikkinchi kichik" onClick={onRasmQoshish}>
          {t("kurs_blok_tasdiq_rasm_qoshish")}
        </button>
        <button type="button" className="tugma ikkinchi kichik" onClick={() => onOchir(mashqIdx)}>
          {t("kurs_blok_tasdiq_mashqni_ochir")}
        </button>
      </div>

      {/* 2026-08-10: bu mashq BOSHQA mashqning rasmini ulashib oladi —
          o'z rasm bloki yo'q, rasm talaba ko'rinishida yonida chiqadi. */}
      {mashq.ulash_guruh && !(mashq.bloklar || []).some((b) => b.ulash === mashq.ulash_guruh) && (
        <div className="izoh" style={{ marginBottom: 8 }}>
          🔗 {t("kurs_blok_tasdiq_ulashilgan_rasm")}
          <button
            type="button"
            className="tugma ikkinchi kichik"
            style={{ marginLeft: 8 }}
            onClick={() => maydonOz({ ulash_guruh: null })}
          >
            {t("kurs_blok_tasdiq_ulashni_uzish")}
          </button>
        </div>
      )}

      <div className="blok-tasdiq-bloklar-royxati">
          {(mashq.bloklar || []).map((b, i) => (
            <BlokTahrir
              key={i}
              blok={b}
              blokIdx={i}
              qutilar={qutilar}
              imgEl={imgEl}
              onChange={blokOz}
              onBlokOchir={blokniOchir}
              mashqRaqami={mashq.raqam}
              sahifaIndeks={sahifaIndeks}
              mashqIdx={mashqIdx}
              barchaMashqlar={barchaMashqlar}
              onUlash={onUlash}
              onMashqgaKochir={onBlokKochir ? (blokIdx, yangiRaqam) => onBlokKochir(mashqIdx, blokIdx, yangiRaqam) : undefined}
            />
          ))}
      </div>

      {mashq.savollar?.length > 0 && (
        <div className="blok-tasdiq-savollar">
          <div className="izoh" style={{ marginBottom: 4 }}>{t("kurs_blok_tasdiq_savollar")}</div>
          {mashq.savollar.map((s, i) => (
            <div key={i} className="blok-tasdiq-savol-qator">
              <span className="izoh">#{i + 1} {s.savol ? `— ${s.savol.slice(0, 40)}` : ""}</span>
              <input
                type="text"
                value={Array.isArray(s.togri) ? s.togri.join(", ") : (s.togri || "")}
                disabled={!!s.erkin}
                placeholder={s.erkin ? t("kurs_erkin_javob_izoh") : ""}
                onChange={(e) => javobOz(i, e.target.value)}
              />
              <label className="izoh" style={{ display: "flex", alignItems: "center", gap: 4, whiteSpace: "nowrap" }}>
                <input type="checkbox" checked={!!s.erkin} onChange={(e) => erkinOz(i, e.target.checked)} />
                {t("kurs_erkin_javob")}
              </label>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** ZIP/PDF orqali kitob yuklash tugagach, AI natijasini bazaga yozishdan
 * OLDIN admin ko'rib chiqadigan/tuzatadigan oyna (2026-08-03) — nima
 * uchun kerak: real sinovlarda AI rasm-quti chegaralarini 1-15% xato
 * bilan belgilashi, va bitta sahifadagi bir nechta alohida mashqni
 * bittaga qo'shib yuborishi aniqlandi, shuning uchun avtomatik saqlash
 * xavfli. Bitta sahifa surati + shu sahifadan aniqlangan BIR NECHTA
 * mashq kartasi (har biri alohida) ko'rsatiladi."""*/
/** Bitta sahifaning suratini yuklaydi (blob URL, komponent hayoti
 * davomida bitta marta) — sahifalar endi HAMMASI birdan (pager'siz)
 * ko'rsatilgani uchun (2026-08-05, foydalanuvchi talabi: "10 ta mashqi
 * bo'lsa 10 ta oynaga alohida ajratsin"), har sahifa MUSTAQIL o'z
 * suratini yuklaydi (avval faqat JORIY sahifa uchun bitta umumiy holat
 * bo'lardi). Sahifa surati faqat rasm-quti (`QutiTahrirlagich`) va rasm
 * kesib ko'rsatish (`RasmVaIzoh`) uchun kerak — mashq matni/savollari
 * suratga bog'liq emas. */
function useSahifaSurati({ jarayonId, indeks }) {
  const [rasmUrl, setRasmUrl] = useState(null);
  const imgRef = useRef(null);

  useEffect(() => {
    let joriyUrl = null;
    let bekorQilindi = false;
    apiBlobUrl(`/api/kurslar/blok-jarayon/${jarayonId}/sahifa-rasm/${indeks}/`).then((u) => {
      if (bekorQilindi) {
        URL.revokeObjectURL(u);
        return;
      }
      joriyUrl = u;
      setRasmUrl(u);
    }).catch(() => {});
    return () => {
      bekorQilindi = true;
      setRasmUrl(null);
      if (joriyUrl) URL.revokeObjectURL(joriyUrl);
    };
  }, [jarayonId, indeks]);

  return { rasmUrl, imgRef };
}

/** Bitta sahifadan aniqlangan mashqlar — sahifa surati (rasm-quti
 * tahrirlagichi) + har mashq ALOHIDA vertikal karta sifatida (2026-08-05:
 * avval sahifalar orasida "oldingi/keyingi" bilan yurilardi, endi
 * HAMMASI bitta uzun vertikal ro'yxatda — sahifa faqat rasm manbai
 * sifatida guruh boshida bir marta ko'rinadi, mashqlarning o'zi bir-biri
 * ostida alohida oyna bo'lib chiqadi). */
function SahifaBlogi({ jarayonId, sahifa, sahifaHolati, ozgartir, barchaMashqlar, mashqniUlash }) {
  const { t } = useI18n();
  const { rasmUrl, imgRef } = useSahifaSurati({ jarayonId, indeks: sahifa.indeks });
  const faylNomi = sahifa.fayl?.split("/").pop() || "";
  const otkazilganmi = !!sahifaHolati.otkazib_yuborilsin;

  function mashqniYangila(mashqIdx, patch) {
    const yangi = [...sahifaHolati.mashqlar];
    yangi[mashqIdx] = { ...yangi[mashqIdx], ...patch };
    ozgartir({ mashqlar: yangi });
  }
  function mashqniOchir(mashqIdx) {
    ozgartir({ mashqlar: sahifaHolati.mashqlar.filter((_, i) => i !== mashqIdx) });
  }

  // 2026-08-10, foydalanuvchi talabi: "rasm qo'shish tugmasini bosaman,
  // kitob sahifasining rasmida yangi quti paydo bo'ladi, shu qutida
  // belgilagan qismimni rasm qilib qo'shish". AI aniqlagan qutilarni
  // FAQAT surish/o'lchamini o'zgartirish mumkin edi — bu YANGI quti
  // qo'shadi (sahifa markazida, kichikroq) va uni SHU mashqning
  // bloklariga "rasm" turi bilan biriktiradi. Quti joyi va o'lchami
  // `QutiTahrirlagich`da (yuqorida, sahifa surati ustida) sudrab
  // to'g'irlanadi — tomoni esa mashq kartasidagi mavjud tanlovdan.
  function rasmQoshish(mashqIdx) {
    const yangiIdx = sahifaHolati.qutilar.length;
    const yangiQuti = { x1: 30, y1: 30, x2: 70, y2: 55 };
    ozgartir({ qutilar: [...sahifaHolati.qutilar, yangiQuti] });
    const yangiBlok = { tur: "rasm", rasm_idx: yangiIdx, tomon: "tepa", izoh: "" };
    const mashqlar = sahifaHolati.mashqlar.map((m, i) =>
      i === mashqIdx ? { ...m, bloklar: [...(m.bloklar || []), yangiBlok] } : m
    );
    ozgartir({ mashqlar });
  }

  /** Bitta blokni (savol_idx'ga bog'liq bo'lmagan turlar — qarang
   * `SAVOL_BOGLIQ_TURLAR`) boshqa mashq raqamiga ko'chiradi (2026-08-05):
   * o'sha raqamli mashq allaqachon bor bo'lsa unga qo'shiladi, bo'lmasa
   * YANGI mashq yaratiladi. Manba mashq bo'sh qolib ketsa (bloklar ham,
   * savollar ham qolmasa) — avtomatik olib tashlanadi. */
  function blokniMashqgaKochir(mashqIdx, blokIdx, yangiRaqam) {
    const manba = sahifaHolati.mashqlar[mashqIdx];
    if (!manba) return;
    const blok = manba.bloklar[blokIdx];
    if (!blok) return;
    const raqam = yangiRaqam.trim();
    if (raqam === String(manba.raqam ?? "")) return;

    const qolganBloklar = manba.bloklar.filter((_, i) => i !== blokIdx);
    let mashqlar = sahifaHolati.mashqlar.map((m, i) =>
      i === mashqIdx ? { ...m, bloklar: qolganBloklar } : m
    );
    mashqlar = mashqlar.filter(
      (m, i) => i !== mashqIdx || m.bloklar.length > 0 || (m.savollar || []).length > 0
    );

    const nishonIdx = mashqlar.findIndex((m) => String(m.raqam ?? "") === raqam);
    if (nishonIdx >= 0) {
      mashqlar[nishonIdx] = { ...mashqlar[nishonIdx], bloklar: [...mashqlar[nishonIdx].bloklar, blok] };
    } else {
      mashqlar.push({ raqam, sarlavha: "", bloklar: [blok], savollar: [], audio_kerak: false });
    }
    ozgartir({ mashqlar });
  }

  return (
    <div className="blok-tasdiq-sahifa-blogi">
      <div className="blok-tasdiq-sarlavha-qator">
        <div style={{ fontWeight: 700 }}>
          {t("kurs_blok_tasdiq_sahifa")} {sahifa.indeks + 1}{faylNomi ? ` — ${faylNomi}` : ""}
        </div>
        <label className="izoh" style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input
            type="checkbox"
            checked={otkazilganmi}
            onChange={(e) => ozgartir({ otkazib_yuborilsin: e.target.checked })}
          />
          {t("kurs_blok_tasdiq_otkazib_yubor")}
        </label>
      </div>

      {sahifa.xato && (
        <div className="xato-xabar">{t("kurs_blok_sahifa_xato")}: {sahifa.xato}</div>
      )}

      {!otkazilganmi && (
        <>
          <QutiTahrirlagich
            rasmUrl={rasmUrl}
            imgRef={imgRef}
            qutilar={sahifaHolati.qutilar}
            onChange={(q) => ozgartir({ qutilar: q })}
          />

          <div className="blok-tasdiq-mashqlar-vertikal">
            {sahifaHolati.mashqlar.length === 0 && (
              <div className="izoh">{t("kurs_blok_tasdiq_mashq_yoq")}</div>
            )}
            {sahifaHolati.mashqlar.map((m, i) => (
              <MashqKartasi
                key={i}
                mashq={m}
                mashqIdx={i}
                qutilar={sahifaHolati.qutilar}
                imgEl={imgRef.current}
                onChange={mashqniYangila}
                onOchir={mashqniOchir}
                onBlokKochir={blokniMashqgaKochir}
                sahifaIndeks={sahifa.indeks}
                barchaMashqlar={barchaMashqlar}
                onUlash={(nishonS, nishonM, blokIdx) => mashqniUlash(sahifa.indeks, i, nishonS, nishonM, blokIdx)}
                onRasmQoshish={() => rasmQoshish(i)}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

/** ZIP/PDF orqali kitob yuklash tugagach, AI natijasini bazaga yozishdan
 * OLDIN admin ko'rib chiqadigan/tuzatadigan oyna (2026-08-03) — nima
 * uchun kerak: real sinovlarda AI rasm-quti chegaralarini 1-15% xato
 * bilan belgilashi, va bitta sahifadagi bir nechta alohida mashqni
 * bittaga qo'shib yuborishi aniqlandi, shuning uchun avtomatik saqlash
 * xavfli.
 *
 * 2026-08-05, foydalanuvchi talabi: sahifa-sahifa (oldingi/keyingi)
 * navigatsiya OLIB TASHLANDI — barcha sahifalardagi HAMMA mashqlar
 * bitta uzun VERTIKAL ro'yxatda ko'rsatiladi, har mashq o'zining
 * alohida kartasida (`SahifaBlogi`/`MashqKartasi`), sahifa surati esa
 * shu mashqlarning manbai sifatida guruh boshida bir marta chiqadi. */
export default function BlokTasdiqlash({ jarayonId, onYakunlandi, onBekor }) {
  const { t } = useI18n();
  const [sahifalar, setSahifalar] = useState(null);
  // holat[indeks] = {mashqlar, qutilar, otkazib_yuborilsin} — har sahifaning
  // JORIY (tuzatilgan bo'lishi mumkin) holati, boshida AI natijasidan olinadi.
  const [holat, setHolat] = useState(null);
  const [xato, setXato] = useState("");
  const [saqlanmoqda, setSaqlanmoqda] = useState(false);

  useEffect(() => {
    api(`/api/kurslar/blok-jarayon/${jarayonId}/tasdiq/`)
      .then((d) => {
        setSahifalar(d.sahifalar);
        const boshlangich = {};
        for (const s of d.sahifalar) {
          boshlangich[s.indeks] = {
            mashqlar: s.mashqlar || [],
            qutilar: s.qutilar || [],
            otkazib_yuborilsin: false,
          };
        }
        setHolat(boshlangich);
      })
      .catch(() => setXato(t("xato_yuz_berdi")));
  }, [jarayonId, t]);

  if (xato) return <div className="xato-xabar">{xato}</div>;
  if (!sahifalar || !holat) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  function sahifaHolatiniYangila(indeks, patch) {
    setHolat((prev) => ({ ...prev, [indeks]: { ...prev[indeks], ...patch } }));
  }

  function mashqniGlobalYangila(sIndeks, mIdx, patch) {
    setHolat((prev) => {
      const mashqlar = [...prev[sIndeks].mashqlar];
      mashqlar[mIdx] = { ...mashqlar[mIdx], ...patch };
      return { ...prev, [sIndeks]: { ...prev[sIndeks], mashqlar } };
    });
  }

  // 2026-08-10 (qayta qurilgan): "bitta rasm, yonida ikkita mashq" —
  // MATN YO'QOLMAYDI. Manba mashqning RASM BLOKI `ulash` kaliti bilan
  // belgilanadi, nishon mashq esa shu kalitni `ulash_guruh` sifatida
  // oladi. Saqlashda (`_jarayonni_yakunla`) shu rasm `KursMashqRasmGuruhi`
  // ga chiqariladi, blok bloklardan olib tashlanadi, qolgan bloklar
  // (dialog/matn/grammar-box) ikkala mashqda ham JOYIDA qoladi.
  function mashqniUlash(selfSahifa, selfMashq, nishonSahifa, nishonMashq, blokIdx) {
    const manba = holat[selfSahifa].mashqlar[selfMashq];
    const mavjud = (manba.bloklar || [])[blokIdx]?.ulash;
    const guruh = mavjud || `g${selfSahifa}_${selfMashq}_${blokIdx}`;
    const bloklar = (manba.bloklar || []).map((b, i) => (i === blokIdx ? { ...b, ulash: guruh } : b));
    mashqniGlobalYangila(selfSahifa, selfMashq, { bloklar });
    mashqniGlobalYangila(nishonSahifa, nishonMashq, { ulash_guruh: guruh });
  }

  const barchaMashqlar = sahifalar.flatMap((s) =>
    (holat[s.indeks].mashqlar || []).map((mashq, mashqIdx) => ({ sahifaIndeks: s.indeks, mashqIdx, mashq })),
  );

  async function hammasiniTasdiqla() {
    setSaqlanmoqda(true);
    setXato("");
    try {
      const tahrirlar = {};
      for (const s of sahifalar) {
        const h = holat[s.indeks];
        tahrirlar[String(s.indeks)] = {
          mashqlar: h.mashqlar,
          qutilar: h.qutilar,
          otkazib_yuborilsin: h.otkazib_yuborilsin,
        };
      }
      const natija = await api(`/api/kurslar/blok-jarayon/${jarayonId}/tasdiqla/`, {
        method: "POST",
        body: { tahrirlar },
      });
      onYakunlandi(natija);
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setSaqlanmoqda(false);
    }
  }

  return (
    <div className="blok-yuklash-qoplama">
      <div className="blok-tasdiq-karta">
        <div className="blok-tasdiq-sarlavha-qator">
          <div style={{ fontWeight: 700 }}>{t("kurs_blok_tasdiq_sahifa")} — {sahifalar.length}</div>
          <button className="tugma ikkinchi kichik" onClick={onBekor}>{t("kurs_blok_bekor_qilish")}</button>
        </div>

        <div className="blok-tasdiq-sahifalar-vertikal">
          {sahifalar.map((s) => (
            <SahifaBlogi
              key={s.indeks}
              jarayonId={jarayonId}
              sahifa={s}
              sahifaHolati={holat[s.indeks]}
              ozgartir={(patch) => sahifaHolatiniYangila(s.indeks, patch)}
              barchaMashqlar={barchaMashqlar}
              mashqniUlash={mashqniUlash}
            />
          ))}
        </div>

        <div className="blok-tasdiq-navigatsiya">
          <button className="tugma" onClick={hammasiniTasdiqla} disabled={saqlanmoqda}>
            {saqlanmoqda ? t("saqlanmoqda") : t("kurs_blok_tasdiq_saqlash")}
          </button>
        </div>
        {xato && <div className="xato-xabar">{xato}</div>}
      </div>
    </div>
  );
}
