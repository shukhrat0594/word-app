// Audio pleyerlar uchun umumiy himoya atributlari (2026-07-28 talabi:
// "audiolarni yuklab olish imkonini qoldirmaslik kerak").
//
// Nega kerak: darslik audiolari (Headway) va IELTS Listening yozuvlari —
// sotib olingan o'quv materiali. Ular platformada eshitilishi kerak, lekin
// tarqatilishi kerak emas. Hozirgacha `<audio controls>` da hech qanday
// cheklov yo'q edi — Chrome pleyerining ⋮ menyusida "Download" tugmasi
// turardi, ya'ni talaba IKKI BOSISHDA faylni olib ketardi.
//
// Nima qiladi:
//   * `controlsList="nodownload"` — Chrome/Edge pleyeridan yuklab olish
//     tugmasini olib tashlaydi.
//   * `onContextMenu` — o'ng tugma > "Audioni saqlash" menyusini bloklaydi.
//
// MUHIM CHEKLOV (halol ogohlantirish, IMLO_OFF dagi kabi): bu himoya EMAS,
// TO'SIQ. Brauzer ovozni chala olsa, bayt allaqachon qurilmada. Buni
// chetlab o'tish yo'llari ochiq qoladi: DevTools > Network, `blob:`
// manzilni qo'lda saqlash, ekran/ovoz yozib olish. Ya'ni bu oddiy
// foydalanuvchini to'xtatadi, qasddan olmoqchi bo'lganni emas.
//
// Haqiqiy himoya uchun audio bo'laklarga bo'linib (HLS), har bo'lakka
// qisqa muddatli token berilishi kerak edi — bu ancha katta ish va baribir
// 100% kafolat bermaydi, shuning uchun hozircha ataylab qilinmadi.
//
// Asosiy himoya esa boshqa joyda va u ISHLAYDI: audio ochiq `/media/`
// orqali emas, autentifikatsiyalangan endpoint orqali beriladi
// (`apiBlobUrl`), shuning uchun havolani tashqi odamga berib bo'lmaydi.
export const AUDIO_HIMOYA = {
  controlsList: "nodownload",
  onContextMenu: (e) => e.preventDefault(),
};

// 2026-07-29 talabi: "bitta audio eshitilayotganda boshqasiga play bosilsa
// oldingisi to'xtasi kerak, bir paytda faqat bitta audio ishlashi kerak".
//
// Sahifada bir nechta <audio> elementi bo'lishi mumkin (masalan Kurslar
// bo'limida bitta mashqda bir nechta trek, yoki turli bo'limlar). Brauzer
// buni o'zi cheklamaydi — ikkita audio parallel chalinaverishi mumkin.
//
// Yechim: modul darajasidagi (React holatidan MUSTAQIL, chunki komponentlar
// turlicha bo'lishi mumkin) yagona "hozir kim chalinyapti" o'zgaruvchisi.
// Har bir <audio>ning "play" hodisasida shu funksiya chaqiriladi — agar
// boshqa audio chalinayotgan bo'lsa, u pauza qilinadi.
let hozirChalinayotgan = null;

export function faqatBittaAudioIjro(audioEl) {
  if (hozirChalinayotgan && hozirChalinayotgan !== audioEl && !hozirChalinayotgan.paused) {
    hozirChalinayotgan.pause();
  }
  hozirChalinayotgan = audioEl;
}
