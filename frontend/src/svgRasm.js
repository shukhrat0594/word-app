// Matn ichiga yozib qo'yilgan SVG grafikni (svgAjrat orqali olingan data-URI)
// haqiqiy PNG rasmga aylantiradi (brauzerda, canvas orqali) — AI'ga rasm
// sifatida yuborish uchun. Backend'da SVG-parsing/rasterizatsiya kerak emas.
// Writing.jsx (Mashqlar bo'limi) va ImtihonYozGap.jsx (IELTS testlari)
// ikkalasida ham qayta ishlatiladi.
export function svgniPngGaAylantir(svgUrl) {
  return new Promise((resolve, reject) => {
    const rasm = new Image();
    rasm.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = rasm.naturalWidth || 800;
      canvas.height = rasm.naturalHeight || 500;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#fff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(rasm, 0, 0);
      resolve(canvas.toDataURL("image/png").split(",")[1]);
    };
    rasm.onerror = reject;
    rasm.src = svgUrl;
  });
}
