/** Ijtimoiy tarmoq belgilari (2026-07-27).
 *
 * Avval emoji ishlatilgan edi (✈️ 📷 ▶️ 👥) — ular tarmoqlarga mos emas
 * (samolyot Telegram emas, fotoapparat Instagram emas) va har operatsion
 * tizimda boshqacha ko'rinadi. Endi SVG: shakl tanib olinadigan, lekin
 * ranglari Utmost brendiga bo'ysunadi — ko'mir fon (--komir) ustida sariq
 * glif (--sariq), hover'da almashadi. Rasm fayllari yo'q, hammasi kodda.
 *
 * viewBox hamma joyda 24x24, glif `currentColor` bilan chiziladi — ya'ni
 * rang CSS'dan boshqariladi va mavzu (kunduzgi/tungi) bilan ishlaydi.
 */

const YOLLAR = {
  // Qog'oz samolyot
  telegram: (
    <path d="M21.9 4.3 18.7 19.4c-.24 1.07-.88 1.33-1.78.83l-4.87-3.57-2.35 2.25c-.26.26-.48.48-.98.48l.34-4.73L17.5 5.7c.4-.36-.09-.55-.62-.2L5.24 12.68 1.38 11.17C.31 10.84.29 10.12 1.6 9.62L20.54 2.76c.88-.33 1.66.2 1.36 1.54z" />
  ),
  // Kamera konturi + linza + kichik nuqta
  instagram: (
    <>
      <rect x="2.6" y="2.6" width="18.8" height="18.8" rx="5.4" fill="none" stroke="currentColor" strokeWidth="2.1" />
      <circle cx="12" cy="12" r="4.1" fill="none" stroke="currentColor" strokeWidth="2.1" />
      <circle cx="17.5" cy="6.6" r="1.35" />
    </>
  ),
  // Ekran + o'ynatish uchburchagi
  youtube: (
    <>
      <path d="M22.6 7.2a3 3 0 0 0-2.1-2.1C18.6 4.6 12 4.6 12 4.6s-6.6 0-8.5.5A3 3 0 0 0 1.4 7.2C.9 9.1.9 12 .9 12s0 2.9.5 4.8a3 3 0 0 0 2.1 2.1c1.9.5 8.5.5 8.5.5s6.6 0 8.5-.5a3 3 0 0 0 2.1-2.1c.5-1.9.5-4.8.5-4.8s0-2.9-.5-4.8z" />
      <path d="M9.75 15.4V8.6L15.6 12z" fill="var(--komir)" />
    </>
  ),
  // "f" harfi
  facebook: (
    <path d="M13.5 21.9v-8.2h2.8l.42-3.2H13.5V8.44c0-.93.26-1.56 1.59-1.56h1.7V4.02c-.3-.04-1.3-.13-2.47-.13-2.45 0-4.12 1.49-4.12 4.24V10.5H7.4v3.2h2.8v8.2z" />
  ),
};

/** Bitta belgi — Utmost rangidagi kvadrat nishon ichida. */
export default function IjtimoiyIkon({ kalit, olcham = 18 }) {
  const yol = YOLLAR[kalit];
  if (!yol) return null;
  return (
    <span className="ijtimoiy-nishon" style={{ "--ikon-olcham": `${olcham}px` }}>
      <svg viewBox="0 0 24 24" width={olcham} height={olcham} fill="currentColor" aria-hidden="true">
        {yol}
      </svg>
    </span>
  );
}
