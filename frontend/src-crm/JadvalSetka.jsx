// Haftalik dars jadvali setkasi — SoffCRM'ning bosh sahifasidagi
// ko'rinish: kun tablari, soatlar ustunda, XONALAR qatorda.
//
// Kutubxonasiz, sof CSS grid: bitta setka uchun tashqi bog'liqlik
// qo'shish arzimaydi va u CRM bundle'ini kattalashtirardi.

import { useMemo, useState } from "react";

import { useFilial } from "./filialContext.jsx";
import { useI18n } from "./i18n.jsx";
import { sorovSatri, useSorov } from "./soragich.js";

const KUNLAR = [
  "kun_dushanba", "kun_seshanba", "kun_chorshanba",
  "kun_payshanba", "kun_juma", "kun_shanba", "kun_yakshanba",
];

// Setka qadami — SoffCRM'dagi "Vaqt oralig'i" tanlovi, standart 30 daqiqa.
const QADAMLAR = [15, 30, 60];

// SoffCRM'dagi doimiy ish kuni oralig'i. Darslar bu oraliqdan tashqarida
// bo'lsa setka KENGAYADI (ertalabki 07:30 darsi tushib qolmasin), lekin
// dars kam bo'lganda ham to'liq kun ko'rinib turadi — admin bo'sh
// vaqtni ham ko'rishi kerak (xona qachon bo'sh?).
const KUN_BOSHI = 8 * 60 + 30;
const KUN_OXIRI = 20 * 60;

/** "14:30" -> 870 (yarim tundan beri daqiqa) */
function daqiqa(vaqt) {
  const [s, d] = String(vaqt).split(":").map(Number);
  return s * 60 + d;
}

function vaqtMatni(daqiqalar) {
  const s = Math.floor(daqiqalar / 60);
  const d = daqiqalar % 60;
  return `${String(s).padStart(2, "0")}:${String(d).padStart(2, "0")}`;
}

/** Guruh nomidan barqaror rang — har safar bir xil bo'lishi uchun.
 *  Tasodifiy rang bo'lsa, sahifa yangilanganda setka butunlay boshqacha
 *  ko'rinar va admin guruhni rangi bo'yicha eslab qola olmasdi. */
function guruhRangi(guruhId) {
  const burchak = (Number(guruhId) * 47) % 360;
  // SoffCRM'dagidek yorqin ranglar (2026-09-17, admin talabi).
  return {
    background: `hsl(${burchak} 85% 78%)`,
    borderInlineStart: `3px solid hsl(${burchak} 60% 40%)`,
    color: `hsl(${burchak} 60% 18%)`,
  };
}

export default function JadvalSetka() {
  const { t } = useI18n();
  const { tanlangan } = useFilial();
  const [kun, setKun] = useState(() => {
    // Dushanba = 0 (bizda), JS'da yakshanba = 0 — moslaymiz.
    const js = new Date().getDay();
    return js === 0 ? 6 : js - 1;
  });

  const { malumot, yuklanmoqda, xato } = useSorov(
    "/api/crm/jadval/" + sorovSatri({ filial: tanlangan })
  );

  const xonalar = malumot?.xonalar || [];
  // Bog'liqlik ATAYLAB `malumot` — `malumot?.darslar || []` har renderda
  // YANGI massiv yasab, useMemo'ni befoyda qilardi.
  const darslar = useMemo(
    () => (malumot?.darslar || []).filter((d) => d.hafta_kuni === kun),
    [malumot, kun]
  );

  const [QADAM, setQadam] = useState(30);

  const [boshi, oxiri] = useMemo(() => {
    const b = Math.min(KUN_BOSHI, ...darslar.map((d) => daqiqa(d.boshlanish_vaqti)));
    const o = Math.max(KUN_OXIRI, ...darslar.map((d) => daqiqa(d.tugash_vaqti)));
    return [Math.floor(b / QADAM) * QADAM, Math.ceil(o / QADAM) * QADAM];
  }, [darslar, QADAM]);

  const ustunlar = Math.max(1, (oxiri - boshi) / QADAM);
  const vaqtlar = Array.from({ length: ustunlar }, (_, i) => boshi + i * QADAM);

  // Qatorlar: faol xonalar + (kerak bo'lsa) "Xonasiz" qatori.
  //
  // "Barcha filiallar" tanlangan bo'lsa, xona nomiga FILIAL qo'shiladi:
  // har filialda "1-xona" bor va ularsiz setkada bir xil nomli to'rtta
  // qator turib, qaysi bino ekani bilinmay qolardi.
  const kopFilial = new Set(xonalar.map((x) => x.filial_id)).size > 1;
  const xonasizBor = darslar.some((d) => !d.xona_id);
  const qatorlar = [
    ...xonalar.map((x) => ({
      id: x.id,
      nomi: x.nomi,
      izoh: kopFilial ? x.filial : null,
    })),
    ...(xonasizBor ? [{ id: null, nomi: t("xonasiz"), izoh: null }] : []),
  ];

  return (
    <div className="setka-oram">
      <div className="kun-tablar">
        {KUNLAR.map((kalit, i) => (
          <button
            key={kalit}
            type="button"
            className={kun === i ? "kun-tab faol" : "kun-tab"}
            onClick={() => setKun(i)}
          >
            {t(kalit)}
          </button>
        ))}
        <label className="yonma setka-qadam">
          <span className="kichik">{t("vaqt_oraligi")}</span>
          <select value={QADAM} onChange={(e) => setQadam(Number(e.target.value))}>
            {QADAMLAR.map((q) => (
              <option key={q} value={q}>{q} {t("daqiqa")}</option>
            ))}
          </select>
        </label>
      </div>

      {xato && <div className="xato">{xato}</div>}
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      {!yuklanmoqda && qatorlar.length === 0 && (
        <p className="kichik">{t("xona_yoq")}</p>
      )}

      {qatorlar.length > 0 && (
        <div className="setka-suruv">
          <div
            className="setka"
            /* O'lchamlar CSS o'zgaruvchilarida (`index.css`) —
               setkani kattalashtirish uchun bitta joyni o'zgartirish
               yetarli bo'lsin. */
            style={{
              gridTemplateColumns:
                `var(--setka-xona-eni) repeat(${ustunlar}, minmax(var(--setka-ustun), 1fr))`,
            }}
          >
            {/* Sarlavha qatori */}
            <div className="setka-burchak">{t("xona_soat")}</div>
            {vaqtlar.map((v) => (
              <div key={v} className="setka-vaqt">{vaqtMatni(v)}</div>
            ))}

            {/* Xona qatorlari. `raqam` — CSS grid qatori: 1-qator
                sarlavha, shuning uchun xonalar 2-dan boshlanadi. U
                ANIQ berilishi shart, aks holda dars bloklari bo'sh
                kataklar ustiga emas, keyingi qatorga tushib ketadi. */}
            {qatorlar.map((qator, i) => (
              <Qator
                key={qator.id ?? "xonasiz"}
                qator={qator}
                raqam={i + 2}
                darslar={darslar.filter((d) => (d.xona_id ?? null) === qator.id)}
                boshi={boshi}
                ustunlar={ustunlar}
                qadam={QADAM}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Qator({ qator, raqam, darslar, boshi, ustunlar, qadam: QADAM }) {
  const { t } = useI18n();
  return (
    <>
      <div className="setka-xona" style={{ gridRow: raqam, gridColumn: 1 }}>
        <span>{qator.nomi}</span>
        {qator.izoh && <i>{qator.izoh}</i>}
      </div>
      {Array.from({ length: ustunlar }, (_, i) => (
        <div key={i} className="setka-katak" style={{ gridRow: raqam, gridColumn: i + 2 }} />
      ))}
      {darslar.map((d) => {
        // 1-ustun xona nomi uchun, shuning uchun +2.
        const dan = Math.floor((daqiqa(d.boshlanish_vaqti) - boshi) / QADAM) + 2;
        const gacha = Math.ceil((daqiqa(d.tugash_vaqti) - boshi) / QADAM) + 2;
        // Blokka bosilsa guruh kartasi ochiladi (2026-09-17, admin
        // talabi: "jadval orqali guruhga kirish"). Oddiy <a> — Guruhlar
        // sahifasi `?guruh=` parametrini o'qib guruhni ochiq ko'rsatadi.
        return (
          <a
            key={d.id}
            className="setka-dars"
            href={`/crm/guruhlar?guruh=${d.guruh_id}`}
            style={{
              gridRow: raqam,
              gridColumn: `${dan} / ${Math.max(gacha, dan + 1)}`,
              ...guruhRangi(d.guruh_id),
            }}
            title={`${d.guruh}\n${d.boshlanish_vaqti} - ${d.tugash_vaqti}\n${d.oqituvchi || ""}`}
          >
            <b>{d.boshlanish_vaqti} - {d.tugash_vaqti} / {d.guruh}</b>
            {d.oqituvchi && <i>{t("oqituvchi")}: {d.oqituvchi}</i>}
          </a>
        );
      })}
    </>
  );
}
