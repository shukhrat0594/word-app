import { useEffect, useState } from "react";
import { api } from "../api";
import QurilmalarPaneli from "../components/QurilmalarPaneli";
import { useI18n } from "../i18n";

/** Qurilma so'rovlari (2026-10-20) — ruxsat etilmagan qurilmadan kirishga
 * urinishlar. Admin bildirishnomasi shu sahifaga olib keladi. Har
 * foydalanuvchi uchun bitta `QurilmalarPaneli` (qarorlar shu yerda). */
export default function QurilmaSorovlari() {
  const { t } = useI18n();
  const [sorovlar, setSorovlar] = useState(null);
  const [xato, setXato] = useState("");

  function yukla() {
    api("/api/qurilma-sorovlari/")
      .then(setSorovlar)
      .catch((e) => setXato(e.data?.detail || t("xato_yuz_berdi")));
  }

  useEffect(yukla, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Bir foydalanuvchida bir nechta so'rov bo'lishi mumkin — panel bittadan.
  const foydalanuvchilar = [];
  for (const s of sorovlar || []) {
    if (!foydalanuvchilar.some((f) => f.id === s.foydalanuvchi.id)) foydalanuvchilar.push(s.foydalanuvchi);
  }

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div>
        <h2 style={{ margin: 0 }}>{t("qurilma_sorovlari")}</h2>
        <p className="izoh">{t("qurilma_sorovlari_izoh")}</p>
      </div>
      {xato && <div className="xato-xabar">{xato}</div>}
      {!sorovlar && !xato && <div className="yuklanmoqda">{t("yuklanmoqda")}</div>}
      {sorovlar && foydalanuvchilar.length === 0 && <p className="izoh">{t("qurilma_sorov_yoq")}</p>}
      {foydalanuvchilar.map((f) => (
        <div key={f.id} className="karta" style={{ display: "grid", gap: 10 }}>
          <strong>
            {f.ism} <span className="izoh">({f.username})</span>
          </strong>
          <QurilmalarPaneli userId={f.id} />
        </div>
      ))}
    </div>
  );
}
