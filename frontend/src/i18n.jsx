import { createContext, useContext, useState } from "react";

const LUGAT = {
  uz: {
    platforma: "IELTS platforma",
    nav_dashboard: "Bosh sahifa",
    nav_mashqlar: "Mashqlar",
    nav_writing: "Writing AI",
    nav_speaking: "Speaking AI",
    nav_paketlar: "Paketlar",
    nav_chiqish: "Chiqish",
    jami_xp: "Jami XP",
    reyting_orin: "Reytingdagi o'rin",
    konikmalar: "Ko'nikmalar",
    yutuqlar: "Yutuqlar",
    umumiy_reyting: "Umumiy reyting",
    guruh_reyting: "Guruh reytingi",
    siz: "siz",
    kirish: "Kirish",
    google_kirish: "Google orqali kirish",
    yoki_xodim: "yoki xodim sifatida",
    login_sarlavha: "IELTS'ga AI bilan tayyorlaning",
    login_izoh:
      "Writing va Speaking javoblaringizni sun'iy intellekt soniyalarda baholaydi. Reading va Listening — har kuni bepul mashqlar.",
    login_xato: "Login yoki parol noto'g'ri",
    yuklanmoqda: "Yuklanmoqda…",
    hali_yoq: "hali yo'q",
    tekshiruv: "tekshiruv",
  },
  ru: {
    platforma: "IELTS платформа",
    nav_dashboard: "Главная",
    nav_mashqlar: "Упражнения",
    nav_writing: "Writing AI",
    nav_speaking: "Speaking AI",
    nav_paketlar: "Пакеты",
    nav_chiqish: "Выход",
    jami_xp: "Всего XP",
    reyting_orin: "Место в рейтинге",
    konikmalar: "Навыки",
    yutuqlar: "Достижения",
    umumiy_reyting: "Общий рейтинг",
    guruh_reyting: "Рейтинг группы",
    siz: "вы",
    kirish: "Войти",
    google_kirish: "Войти через Google",
    yoki_xodim: "или как сотрудник",
    login_sarlavha: "Готовьтесь к IELTS с AI",
    login_izoh:
      "AI оценит ваши Writing и Speaking за секунды. Reading и Listening — бесплатные упражнения каждый день.",
    login_xato: "Неверный логин или пароль",
    yuklanmoqda: "Загрузка…",
    hali_yoq: "пока нет",
    tekshiruv: "проверок",
  },
  en: {
    platforma: "IELTS platform",
    nav_dashboard: "Dashboard",
    nav_mashqlar: "Exercises",
    nav_writing: "Writing AI",
    nav_speaking: "Speaking AI",
    nav_paketlar: "Packages",
    nav_chiqish: "Log out",
    jami_xp: "Total XP",
    reyting_orin: "Leaderboard rank",
    konikmalar: "Skills",
    yutuqlar: "Achievements",
    umumiy_reyting: "Global leaderboard",
    guruh_reyting: "Group leaderboard",
    siz: "you",
    kirish: "Sign in",
    google_kirish: "Sign in with Google",
    yoki_xodim: "or as staff",
    login_sarlavha: "Prepare for IELTS with AI",
    login_izoh:
      "AI grades your Writing and Speaking in seconds. Reading and Listening — free daily exercises.",
    login_xato: "Wrong login or password",
    yuklanmoqda: "Loading…",
    hali_yoq: "none yet",
    tekshiruv: "checks",
  },
};

const I18nContext = createContext(null);

export function I18nProvider({ children }) {
  const [til, setTil] = useState(localStorage.getItem("til") || "uz");
  const t = (kalit) => LUGAT[til]?.[kalit] ?? kalit;
  const tilniQoy = (t2) => {
    localStorage.setItem("til", t2);
    setTil(t2);
  };
  return (
    <I18nContext.Provider value={{ til, tilniQoy, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export const useI18n = () => useContext(I18nContext);
