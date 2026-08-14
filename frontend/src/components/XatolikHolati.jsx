// 2026-08-15: tarmoq xatosida (.catch) "abadiy yuklanmoqda" holatidan
// chiqish uchun umumiy komponent — xabar + qayta urinish tugmasi.
export default function XatolikHolati({ xabar, qaytaUrin }) {
  return (
    <div className="yuklanmoqda" style={{ textAlign: "center" }}>
      <p>{xabar || "Ma'lumot yuklanmadi"}</p>
      <button className="tugma" onClick={qaytaUrin}>
        Qayta urinish
      </button>
    </div>
  );
}
