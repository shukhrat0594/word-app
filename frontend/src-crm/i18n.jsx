// CRM tarjimalari — uz/ru/en.
//
// LMS'ning `src/i18n.jsx` (2305 qator) ATAYLAB nusxalanmadi: unda CRM'ga
// aloqasi yo'q yuzlab satr bor. CRM o'z lug'atini yuritadi.
//
// Til tanlovi LMS bilan BIR XIL localStorage kalitida (`til`) saqlanadi —
// admin LMS'da ruscha tanlagan bo'lsa, CRM ham ruscha ochiladi.

import { createContext, useContext, useEffect, useState } from "react";

export const TILLAR = [
  { kod: "uz", nomi: "O'zbekcha" },
  { kod: "ru", nomi: "Русский" },
  { kod: "en", nomi: "English" },
];

const SATRLAR = {
  uz: {
    crm: "CRM",
    kirish: "Kirish",
    login: "Login",
    parol: "Parol",
    kirish_tugma: "Kirish",
    kirilmoqda: "Kirilmoqda...",
    chiqish: "Chiqish",
    yuklanmoqda: "Yuklanmoqda...",
    saqlash: "Saqlash",
    saqlandi: "Saqlandi",
    bekor: "Bekor qilish",
    yopish: "Yopish",
    qoshish: "Qo'shish",
    yozuv_yoq: "Yozuv yo'q",
    qidiruv: "Qidirish...",
    jami: "Jami",
    hammasi: "Hammasi",

    bosh_sahifa: "Bosh sahifa",
    guruhlar: "Guruhlar",
    talabalar: "Talabalar",
    moliya: "Moliya",
    hisobotlar: "Hisobotlar",
    hamma_filiallar: "Barcha filiallar",

    ruxsat_yoq_sarlavha: "Bu bo'lim faqat administratorlar uchun",
    ruxsat_yoq_matn:
      "CRM'ga faqat administrator va owner kira oladi. Saytga qaytish uchun quyidagi havoladan foydalaning.",
    saytga_qaytish: "Saytga qaytish",
    korish_rejimi_sarlavha: "Ko'rish rejimi yoqilgan",
    korish_rejimi_matn:
      "Hozir siz saytni boshqa rol nazari bilan ko'ryapsiz, shuning uchun CRM yopiq. Profil sahifasida ko'rish rejimini «Owner»ga qaytaring.",

    tab_qarzdorlar: "Qarzdorlar",
    tab_tolovlar: "To'lovlar",
    tab_hisobot: "Hisobot",

    talaba: "Talaba",
    guruh: "Guruh",
    filial: "Filial",
    sana: "Sana",
    turi: "Turi",
    summa: "Summa",
    izoh: "Izoh",
    kim: "Kim kiritdi",
    holat: "Holat",
    balans: "Balans",
    narx: "Narx",
    dan: "dan",
    gacha: "gacha",
    qaysi_oy: "Qaysi oy uchun",

    hisoblangan: "Hisoblangan",
    tolangan: "To'langan",
    qoldiq: "Qoldiq",
    olingan_pul: "Olingan pul",
    chegirma: "Chegirma",
    bonus: "Bonus",
    qaytarilgan: "Qaytarilgan",
    qarz: "Qarz",
    yigilish: "Yig'ilish",

    barcha_holatlar: "Barcha holatlar",
    barcha_turlar: "Barcha turlar",
    hisoblar_bilan: "Hisob-fakturalar bilan",
    proporsional_izoh: "Proporsional — to'liq oy emas",

    holat_qarzdor: "Qarzdor",
    holat_qisman: "Qisman",
    holat_tolandi: "To'langan",
    holat_kutilayotgan: "Kutilayotgan",

    turi_tolov: "To'lov",
    turi_chegirma: "Chegirma",
    turi_bonus: "Bonus",
    turi_qaytarish: "Pul qaytarish",

    tolov_qilish: "To'lov qilish",
    pul_qaytarish: "Pul qaytarish",
    tolangan_summa: "To'langan summa",
    summa_kerak: "Summa kiriting",
    kam_summa_ogoh: "Hisoblangandan kam. Qoldiq qarz bo'lib qoladi.",
    kop_summa_ogoh: "Hisoblangandan ko'p. Ortiqchasi balansda qoladi:",
    qarz_qoldi: "Qarz qoldi",
    chegirma_izoh:
      "Qoldiqni chegirma bilan yopish mumkin. Chegirma — pul emas: hisobotda alohida ustunda ko'rinadi va kassaga qo'shilmaydi.",
    qarz_qoldirish: "Qarz bo'lib qolsin",
    chegirma_qilish: "Chegirma qilish",

    kurs_narxlari: "Kurs narxlari",
    daraja: "Daraja",
    fan: "Fan",
    guruh_soni: "Guruhlar",
    narx_kursdan: "Kurs narxi",
    narx_guruhdan: "Guruhga alohida",
    narx_talabadan: "Talabaga alohida",
    narx_yoq: "Narx belgilanmagan",

    dars_kunlari: "Dars kunlari",
    boshlanish_sana: "Boshlanish sanasi",
    tugash_sana: "Tugash sanasi",
    sozlash: "Sozlash",
    sozlanmagan: "Sozlanmagan",
    talabalar_soni: "Talabalar",
    azolar: "A'zolar",

    holat_sinov: "Sinov",
    holat_faol: "Faol",
    holat_muzlatilgan: "Muzlatilgan",
    holat_arxiv: "Arxiv",

    keyingi_tolov: "Keyingi to'lov",
    darslar_taqvimi: "Darslar taqvimi",
    tolov_tarixi: "To'lov tarixi",
    telefon: "Telefon",
    ota_ona_telefon: "Ota-ona telefoni",
    umumiy_balans: "Umumiy balans",

    ogohlantirishlar: "Ogohlantirishlar",
    ogohlantirish_izoh:
      "Bu guruhlarga hisob OCHILMAYDI — ya'ni ular jimgina pul yo'qotadi.",
    ogohlantirish_yoq: "Hammasi sozlangan",

    narxlar: "Narxlar",
    sozlamalar: "Sozlamalar",
    filiallar: "Filiallar",
    yangi_filial: "Yangi filial",
    manzil: "Manzil",
    faol: "Faol",
    arxivlangan: "Arxivlangan",
    arxivlash: "Arxivlash",
    tiklash: "Tiklash",
    tahrirlash: "Tahrirlash",
    filial_nomi_kerak: "Filial nomi kerak",
    oy: "oy",
    qolda_hisob: "Qo'lda hisob",
    qolda_hisob_izoh: "Tizim yoqilgunga qadar bo'lgan eski qarz uchun. Tizim o'zi ochadigan oylarga qo'lda kiritish shart emas.",
    guruh_talaba_kerak: "Guruh va talabani tanlang",
    qaytarish_izoh: "Pul qaytarish bitta oyga bog'lanmaydi: oy holati o'zgarmaydi, summa faqat balansdan chiqadi.",
    hisobot_izoh: "«Olingan pul» faqat haqiqiy to'lovlar. Chegirma va bonus qarzni yopadi, lekin kassaga tushmaydi — shuning uchun alohida ustunlarda.",

    sahifa_topilmadi: "Sahifa topilmadi",
  },

  ru: {
    crm: "CRM",
    kirish: "Вход",
    login: "Логин",
    parol: "Пароль",
    kirish_tugma: "Войти",
    kirilmoqda: "Вход...",
    chiqish: "Выйти",
    yuklanmoqda: "Загрузка...",
    saqlash: "Сохранить",
    saqlandi: "Сохранено",
    bekor: "Отмена",
    yopish: "Закрыть",
    qoshish: "Добавить",
    yozuv_yoq: "Записей нет",
    qidiruv: "Поиск...",
    jami: "Итого",
    hammasi: "Все",

    bosh_sahifa: "Главная",
    guruhlar: "Группы",
    talabalar: "Ученики",
    moliya: "Финансы",
    hisobotlar: "Отчёты",
    hamma_filiallar: "Все филиалы",

    ruxsat_yoq_sarlavha: "Раздел только для администраторов",
    ruxsat_yoq_matn:
      "В CRM могут войти только администратор и владелец. Вернуться на сайт можно по ссылке ниже.",
    saytga_qaytish: "Вернуться на сайт",
    korish_rejimi_sarlavha: "Включён режим просмотра",
    korish_rejimi_matn:
      "Сейчас вы смотрите сайт от имени другой роли, поэтому CRM закрыт. Верните режим просмотра на «Owner» в профиле.",

    tab_qarzdorlar: "Должники",
    tab_tolovlar: "Платежи",
    tab_hisobot: "Отчёт",

    talaba: "Ученик",
    guruh: "Группа",
    filial: "Филиал",
    sana: "Дата",
    turi: "Тип",
    summa: "Сумма",
    izoh: "Примечание",
    kim: "Кто внёс",
    holat: "Статус",
    balans: "Баланс",
    narx: "Цена",
    dan: "с",
    gacha: "по",
    qaysi_oy: "За какой месяц",

    hisoblangan: "Начислено",
    tolangan: "Оплачено",
    qoldiq: "Остаток",
    olingan_pul: "Получено денег",
    chegirma: "Скидка",
    bonus: "Бонус",
    qaytarilgan: "Возвращено",
    qarz: "Долг",
    yigilish: "Собираемость",

    barcha_holatlar: "Все статусы",
    barcha_turlar: "Все типы",
    hisoblar_bilan: "Вместе с начислениями",
    proporsional_izoh: "Пропорционально — неполный месяц",

    holat_qarzdor: "Должник",
    holat_qisman: "Частично",
    holat_tolandi: "Оплачено",
    holat_kutilayotgan: "Ожидается",

    turi_tolov: "Платёж",
    turi_chegirma: "Скидка",
    turi_bonus: "Бонус",
    turi_qaytarish: "Возврат",

    tolov_qilish: "Внести платёж",
    pul_qaytarish: "Вернуть деньги",
    tolangan_summa: "Внесённая сумма",
    summa_kerak: "Введите сумму",
    kam_summa_ogoh: "Меньше начисленного. Остаток останется долгом.",
    kop_summa_ogoh: "Больше начисленного. Излишек останется на балансе:",
    qarz_qoldi: "Остался долг",
    chegirma_izoh:
      "Остаток можно закрыть скидкой. Скидка — не деньги: в отчёте она идёт отдельной колонкой и в кассу не попадает.",
    qarz_qoldirish: "Оставить долгом",
    chegirma_qilish: "Сделать скидку",

    kurs_narxlari: "Цены курсов",
    daraja: "Уровень",
    fan: "Предмет",
    guruh_soni: "Групп",
    narx_kursdan: "Цена курса",
    narx_guruhdan: "Отдельно для группы",
    narx_talabadan: "Отдельно для ученика",
    narx_yoq: "Цена не указана",

    dars_kunlari: "Дни занятий",
    boshlanish_sana: "Дата начала",
    tugash_sana: "Дата окончания",
    sozlash: "Настроить",
    sozlanmagan: "Не настроено",
    talabalar_soni: "Учеников",
    azolar: "Участники",

    holat_sinov: "Пробный",
    holat_faol: "Активный",
    holat_muzlatilgan: "Заморожен",
    holat_arxiv: "Архив",

    keyingi_tolov: "Следующий платёж",
    darslar_taqvimi: "Календарь занятий",
    tolov_tarixi: "История платежей",
    telefon: "Телефон",
    ota_ona_telefon: "Телефон родителя",
    umumiy_balans: "Общий баланс",

    ogohlantirishlar: "Предупреждения",
    ogohlantirish_izoh:
      "По этим группам начисления НЕ создаются — то есть они тихо теряют деньги.",
    ogohlantirish_yoq: "Всё настроено",

    narxlar: "Цены",
    sozlamalar: "Настройки",
    filiallar: "Филиалы",
    yangi_filial: "Новый филиал",
    manzil: "Адрес",
    faol: "Активен",
    arxivlangan: "В архиве",
    arxivlash: "В архив",
    tiklash: "Восстановить",
    tahrirlash: "Изменить",
    filial_nomi_kerak: "Укажите название филиала",
    oy: "мес.",
    qolda_hisob: "Начисление вручную",
    qolda_hisob_izoh: "Для старого долга, накопившегося до запуска системы. Месяцы, которые система открывает сама, вручную вводить не нужно.",
    guruh_talaba_kerak: "Выберите группу и ученика",
    qaytarish_izoh: "Возврат не привязан к месяцу: статус месяца не меняется, сумма только уходит с баланса.",
    hisobot_izoh: "«Получено денег» — только реальные платежи. Скидка и бонус закрывают долг, но в кассу не попадают, поэтому вынесены в отдельные колонки.",

    sahifa_topilmadi: "Страница не найдена",
  },

  en: {
    crm: "CRM",
    kirish: "Sign in",
    login: "Login",
    parol: "Password",
    kirish_tugma: "Sign in",
    kirilmoqda: "Signing in...",
    chiqish: "Sign out",
    yuklanmoqda: "Loading...",
    saqlash: "Save",
    saqlandi: "Saved",
    bekor: "Cancel",
    yopish: "Close",
    qoshish: "Add",
    yozuv_yoq: "No records",
    qidiruv: "Search...",
    jami: "Total",
    hammasi: "All",

    bosh_sahifa: "Home",
    guruhlar: "Groups",
    talabalar: "Students",
    moliya: "Finance",
    hisobotlar: "Reports",
    hamma_filiallar: "All branches",

    ruxsat_yoq_sarlavha: "Administrators only",
    ruxsat_yoq_matn:
      "Only an administrator or owner can open the CRM. Use the link below to go back to the site.",
    saytga_qaytish: "Back to the site",
    korish_rejimi_sarlavha: "View-as mode is on",
    korish_rejimi_matn:
      "You are currently viewing the site as another role, so the CRM is closed. Switch view mode back to “Owner” in your profile.",

    tab_qarzdorlar: "Debtors",
    tab_tolovlar: "Payments",
    tab_hisobot: "Report",

    talaba: "Student",
    guruh: "Group",
    filial: "Branch",
    sana: "Date",
    turi: "Type",
    summa: "Amount",
    izoh: "Note",
    kim: "Entered by",
    holat: "Status",
    balans: "Balance",
    narx: "Price",
    dan: "from",
    gacha: "to",
    qaysi_oy: "For month",

    hisoblangan: "Charged",
    tolangan: "Paid",
    qoldiq: "Remaining",
    olingan_pul: "Cash received",
    chegirma: "Discount",
    bonus: "Bonus",
    qaytarilgan: "Refunded",
    qarz: "Debt",
    yigilish: "Collection",

    barcha_holatlar: "All statuses",
    barcha_turlar: "All types",
    hisoblar_bilan: "Include charges",
    proporsional_izoh: "Pro-rated — partial month",

    holat_qarzdor: "Unpaid",
    holat_qisman: "Partial",
    holat_tolandi: "Paid",
    holat_kutilayotgan: "Upcoming",

    turi_tolov: "Payment",
    turi_chegirma: "Discount",
    turi_bonus: "Bonus",
    turi_qaytarish: "Refund",

    tolov_qilish: "Record payment",
    pul_qaytarish: "Refund",
    tolangan_summa: "Amount paid",
    summa_kerak: "Enter an amount",
    kam_summa_ogoh: "Less than charged. The remainder stays as debt.",
    kop_summa_ogoh: "More than charged. The excess stays on the balance:",
    qarz_qoldi: "Debt remaining",
    chegirma_izoh:
      "You can close the remainder with a discount. A discount is not cash: it appears in its own report column and never counts as money received.",
    qarz_qoldirish: "Leave as debt",
    chegirma_qilish: "Apply discount",

    kurs_narxlari: "Course prices",
    daraja: "Level",
    fan: "Subject",
    guruh_soni: "Groups",
    narx_kursdan: "Course price",
    narx_guruhdan: "Group override",
    narx_talabadan: "Student override",
    narx_yoq: "No price set",

    dars_kunlari: "Class days",
    boshlanish_sana: "Start date",
    tugash_sana: "End date",
    sozlash: "Configure",
    sozlanmagan: "Not configured",
    talabalar_soni: "Students",
    azolar: "Members",

    holat_sinov: "Trial",
    holat_faol: "Active",
    holat_muzlatilgan: "Frozen",
    holat_arxiv: "Archived",

    keyingi_tolov: "Next payment",
    darslar_taqvimi: "Class calendar",
    tolov_tarixi: "Payment history",
    telefon: "Phone",
    ota_ona_telefon: "Parent phone",
    umumiy_balans: "Total balance",

    ogohlantirishlar: "Warnings",
    ogohlantirish_izoh:
      "No charges are created for these groups — they are quietly losing money.",
    ogohlantirish_yoq: "Everything is configured",

    narxlar: "Prices",
    sozlamalar: "Settings",
    filiallar: "Branches",
    yangi_filial: "New branch",
    manzil: "Address",
    faol: "Active",
    arxivlangan: "Archived",
    arxivlash: "Archive",
    tiklash: "Restore",
    tahrirlash: "Edit",
    filial_nomi_kerak: "Enter a branch name",
    oy: "mo.",
    qolda_hisob: "Manual charge",
    qolda_hisob_izoh: "For debt carried over from before the system went live. Months the system opens by itself do not need manual entry.",
    guruh_talaba_kerak: "Choose a group and a student",
    qaytarish_izoh: "A refund is not tied to a month: the month's status does not change, the amount only leaves the balance.",
    hisobot_izoh: "“Cash received” counts real payments only. Discounts and bonuses close the debt but never reach the till, so they have their own columns.",

    sahifa_topilmadi: "Page not found",
  },
};

const I18nContext = createContext(null);

export function I18nProvider({ children }) {
  const [til, setTil] = useState(() => localStorage.getItem("til") || "uz");

  useEffect(() => {
    localStorage.setItem("til", til);
    document.documentElement.lang = til;
  }, [til]);

  // Kalit topilmasa — o'zbekchaga, u ham bo'lmasa kalitning o'zi
  // qaytariladi. Shunda tarjima unutilgani ekranda ko'rinib qoladi.
  const t = (kalit) => SATRLAR[til]?.[kalit] ?? SATRLAR.uz[kalit] ?? kalit;

  return <I18nContext.Provider value={{ til, setTil, t }}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const qiymat = useContext(I18nContext);
  if (!qiymat) throw new Error("useI18n faqat I18nProvider ichida ishlaydi");
  return qiymat;
}
