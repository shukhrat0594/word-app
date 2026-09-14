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
