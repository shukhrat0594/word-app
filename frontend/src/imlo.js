// Talaba javob yozadigan maydonlar uchun brauzer "yordami"ni o'chirish
// (2026-07-26 talabi).
//
// Nega: bu imtihon tizimi va IMLO XATOSI BAHOLANADI (AI xatolar ro'yxatiga
// imlo xatolarini ham qo'shadi, WRITING_SYSTEM_PROMPT 4-bandi). Brauzer yoki
// telefon klaviaturasi so'zni jimgina to'g'rilab qo'ysa yoki tagiga qizil
// chiziq chizib xatoni ko'rsatib bersa, baho talabaning haqiqiy bilimini
// emas, brauzerning imkoniyatini o'lchaydi.
//
// `data-gramm*` — Grammarly kabi kengaytmalarni maydondan chetlatish uchun.
// Grammarly IELTS Writing testida to'g'ridan-to'g'ri "chetlab o'tish"
// vositasi: u xatoni ham ko'rsatadi, ham tuzatadi.
//
// MUHIM CHEKLOV (halol ogohlantirish): bu atributlar brauzerga BERILGAN
// ILTIMOS, kafolat emas. iOS Safari `autoCorrect`/`autoCapitalize`ni
// hurmat qiladi, lekin Android'dagi ba'zi klaviaturalar (masalan Gboard)
// avtomatik tuzatishni o'z sozlamasidan boshqaradi va bu atributlarni
// e'tiborsiz qoldirishi mumkin. Shuningdek foydalanuvchi javobni boshqa
// joyda yozib, nusxa ko'chirib qo'yishi mumkin. To'liq nazorat faqat
// kuzatiladigan (proctoring) muhitda bo'ladi.
export const IMLO_OFF = {
  spellCheck: false,
  autoCorrect: "off",
  autoCapitalize: "off",
  autoComplete: "off",
  "data-gramm": "false",
  "data-gramm_editor": "false",
  "data-enable-grammarly": "false",
};
