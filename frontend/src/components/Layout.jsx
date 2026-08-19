import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { api, mediaManzil, tokenlarniTozala } from "../api";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";
import { useTestRejimi } from "../testRejimiContext";
import Avatar from "./Avatar";
import IjtimoiyPanel from "./IjtimoiyPanel";

// 2026-07-27: "Namunaviy mashqlar" (eski "Mashqlar") bo'limi VAQTINCHA
// yopildi — hech bir rolga ko'rinmaydi. Kod, sahifa, marshrut va bazadagi
// mashqlar joyida qoladi; qayta ochish uchun shu bayroqni `true` qilish
// kifoya (App.jsx marshruti ham shu bayroqqa qaraydi).
export const NAMUNAVIY_MASHQLAR_OCHIQ = false;

// PANEL REESTRI (2026-08-09) — har panelning ikonkasi va tarjima kaliti
// BIR JOYDA. Avval bu ma'lumot beshta ro'yxatga tarqalgan edi
// (`TALABA_NAVLAR`, `OWNER_NAVLAR`, `navlarniOl` ning uch shoxi, ustiga
// `oddiy` uchun alohida filtr va owner uchun alohida qo'shimcha blok) —
// ya'ni bitta panelning ikonkasi to'rt joyda takrorlanardi.
const PANELLAR = {
  "/": { ikon: "▦", kalit: "nav_dashboard" },
  "/mashqlar": { ikon: "✎", kalit: "nav_mashqlar" },
  "/ielts-boshqarish": { ikon: "🎓", kalit: "nav_ielts_boshqarish" },
  "/ai-mashqlari": { ikon: "🤖", kalit: "nav_ai_mashqlari" },
  "/kurslar": { ikon: "📚", kalit: "nav_kurslar" },
  "/oyinlar": { ikon: "🎮", kalit: "nav_oyinlar" },
  "/reyting": { ikon: "🏆", kalit: "nav_reyting" },
  "/guruhlar": { ikon: "☰", kalit: "nav_guruhlar" },
  "/talabalar": { ikon: "🎒", kalit: "nav_talabalar" },
  "/xodimlar": { ikon: "🧑‍🏫", kalit: "nav_xodimlar" },
  "/markaz-sozlash": { ikon: "🏢", kalit: "nav_markaz_sozlama" },
  "/foydalanuvchilar": { ikon: "🧑‍🤝‍🧑", kalit: "nav_foydalanuvchilar" },
  "/hisobotlar": { ikon: "📊", kalit: "nav_hisobotlar" },
  "/profil": { ikon: "👤", kalit: "nav_profil" },
};

// HAR DOIM ko'rinadigan panellar (2026-08-09 qarori): foydalanuvchi
// kamida bitta sahifani ko'rishi va o'z profilini (parol, rasm)
// boshqarishi kerak. Bular "ko'rinadigan panellar" tanlovida CHIQMAYDI
// va hech qachon yashirilmaydi.
export const MAJBURIY_PANELLAR = ["/", "/profil"];

// ROL -> PANELLAR — QAT'IY jadval (2026-08-09, foydalanuvchi qarori:
// "rollar bo'yicha qaysi rolga qaysi panellar ko'rinishi qat'iy
// qoladi"). Bu YAGONA MANBA: menyu ham, "ko'rinadigan panellar"
// tanlovi ham shu yerdan o'qiydi.
//
// Nega kerak bo'ldi: avval tanlov ro'yxati rolga QARAMASDI — global 13
// panel chiqardi. Natijada masalan ota-onaga "Kurslar"ni belgilash
// mumkin edi, lekin ta'siri YO'Q edi (ota-ona rolida u panel umuman
// yo'q, kesishma bo'sh chiqardi) — ya'ni galochka yolg'on gapirardi.
//
// Tartib MUHIM — menyu aynan shu ketma-ketlikda chiziladi.
//
// DIQQAT: bu FAQAT navigatsiya. Backend ruxsatlari bunga tayanmaydi —
// talabaga mo'ljallangan sahifalar (Reyting, Tarix, O'yinlar) ownerga
// uning O'Z ma'lumotini ko'rsatadi, ya'ni odatda bo'sh bo'ladi.
// 2026-08-15: "/tarix" ALOHIDA panel sifatida olib tashlandi — talaba
// o'z natijalarini endi PROFIL sahifasida ko'radi (bir xil
// `NatijalarRoyxati` komponenti). "/davomat" ham olib tashlandi —
// u endi guruh ichida ochiladi (`Guruhlar.jsx`).
const TALABA_PANELLARI = [
  "/",
  ...(NAMUNAVIY_MASHQLAR_OCHIQ ? ["/mashqlar"] : []),
  "/ielts-boshqarish",
  "/ai-mashqlari",
  "/kurslar",
  "/oyinlar",
  "/reyting",
];

export const ROL_PANELLARI = {
  // 2026-08-08 talabi: "ownerga hamma panellar ko'rinsin". Avval owner
  // admin ro'yxatini olardi va Davomat/O'yinlar/Tarix/Reyting unga
  // ko'rinmasdi.
  owner: [
    "/", "/guruhlar", "/talabalar", "/xodimlar",
    "/ielts-boshqarish", "/ai-mashqlari", "/kurslar",
    "/oyinlar", "/reyting",
    "/markaz-sozlash", "/foydalanuvchilar", "/hisobotlar",
  ],
  // 2026-07-21: "Mashqlar boshqarish" (bo'lim o'zi ham yopiq), "Davomat"
  // (endi faqat o'qituvchida — u belgilaydi; hisoboti "Hisobotlar"ga
  // ko'chdi, faqat owner ko'radi) va "Markaz sozlamalari" (logo/ijtimoiy/
  // backup — 2026-08-15: backup FAQAT owner uchun bo'lgani sabab butun
  // sahifa ham owner-only qilib qoldirildi) adminda YO'Q. Sahifalari va
  // backendi joyida — kerak bo'lsa shu ro'yxatga qaytariladi.
  //
  // 2026-08-13: "/hisobotlar" adminga QO'SHILDI (foydalanuvchi talabi) —
  // lekin sahifaning o'zi (`Hisobotlar.jsx`) admin uchun FAQAT "Javobsiz
  // savollar" tabini ko'rsatadi, qolgan 3 tab (Davomat/Audit/Statistika)
  // hamon faqat owner uchun (backend ham 403 qaytaradi).
  admin: [
    "/", "/guruhlar", "/talabalar", "/xodimlar",
    "/ielts-boshqarish", "/ai-mashqlari", "/kurslar",
    "/hisobotlar",
  ],
  teacher: [
    "/", "/ielts-boshqarish", "/ai-mashqlari", "/kurslar",
    "/guruhlar", "/talabalar",
  ],
  student: TALABA_PANELLARI,
  // "Oddiy foydalanuvchi" talaba ro'yxatidan farq qiladi: "IELTS
  // testlari" va "Kurslar" unga berilmaydi (2026-07-20 / 2026-07-21).
  // "AI mashqlari" esa OCHIQ (2026-07-27) — "Namunaviy mashqlar" yopilgach
  // unga hech qanday mashq qolmagandi; backendda ham shunday,
  // `korinadigan_testlar` unga faqat AI manbali testlarni qaytaradi.
  oddiy: TALABA_PANELLARI.filter(
    (y) => y !== "/ielts-boshqarish" && y !== "/kurslar"
  ),
  parent: ["/"],
};

/** Shu foydalanuvchi roli ko'ra oladigan panellar (qat'iy jadvaldan).
 *
 * `is_owner` ROLDAN ustun: owner'ning `role` maydoni "admin" bo'lib
 * turadi (`FoydalanuvchiRolView` shunday yozadi), ya'ni rol bo'yicha
 * qaralsa owner admin ro'yxatini olib qolardi. */
export function rolPanellariOl(role, ownerMi) {
  if (ownerMi) return ROL_PANELLARI.owner;
  return ROL_PANELLARI[role] || ROL_PANELLARI.student;
}

/** "Ko'rinadigan panellar" tanlovida chiqadigan ro'yxat — shu rolning
 * panellari, majburiylari (Bosh sahifa/Profil) olib tashlangan holda.
 * Ya'ni ro'yxatda faqat HAQIQATAN ta'sir qiladigan panellar turadi. */
export function panelTanloviOl(role, ownerMi) {
  return rolPanellariOl(role, ownerMi)
    .filter((yol) => !MAJBURIY_PANELLAR.includes(yol))
    .map((yol) => ({ yol, kalit: PANELLAR[yol].kalit }));
}

/** Yo'l ro'yxatini menyu elementlariga aylantiradi (ikon + tarjima
 * kaliti reestrdan). Ota-onaning "Bosh sahifa" ikonkasi ATAYLAB
 * boshqacha (👪) — u yerda bu sahifa farzandlar ro'yxati. */
function menyuQur(yollar, role) {
  return yollar.map((yol) => ({
    yol,
    ikon: yol === "/" && role === "parent" ? "👪" : PANELLAR[yol].ikon,
    kalit: PANELLAR[yol].kalit,
  }));
}

/** Ilova ichidagi bildirishnomalar (2026-08-08). Manbalari: owner'ga
 * `CHANGELOG.md` relizlari (backend: `accounts/relizlar.py`), har kimga
 * — profil rasmi o'chirilgani haqidagi ogohlantirish (2026-08-09).
 *
 * Faqat sarlavhadagi qo'ng'iroq va ochiladigan ro'yxat; so'rov FAQAT
 * ochilganda va sahifa birinchi yuklanganda yuboriladi (davomiy so'rov
 * qilmaymiz — reliz kuniga bir marta ham chiqmaydi). */
/** CHANGELOG bo'limini bandlar ro'yxatiga aylantiradi.
 *
 * To'liq markdown kutubxonasi SHART EMAS: manba faqat bizning
 * `CHANGELOG.md` va u atigi ikki narsadan foydalanadi — "- " bandlari
 * va **qalin** ta'kid. Fayl 72 belgida qattiq o'raladi, shuning uchun
 * bandning davomi keyingi qatorlarda keladi — ularni birlashtiramiz,
 * aks holda matn tasodifiy joylarda uzilib ko'rinardi. */
function bandlarniAjrat(matn) {
  const bandlar = [];
  for (const qator of (matn || "").split("\n")) {
    const tozalangan = qator.trim().replace(/\*\*/g, "");
    if (!tozalangan) continue;
    if (tozalangan.startsWith("- ")) bandlar.push(tozalangan.slice(2));
    else if (bandlar.length) bandlar[bandlar.length - 1] += ` ${tozalangan}`;
    else bandlar.push(tozalangan);
  }
  return bandlar;
}

function Bildirishnomalar({ t }) {
  const [ochiq, setOchiq] = useState(false);
  const [malumot, setMalumot] = useState(null);
  const qutiRef = useRef(null);

  function yukla() {
    api("/api/bildirishnomalar/").then(setMalumot).catch(() => {});
  }

  useEffect(() => {
    yukla();
  }, []);

  // Tashqariga bosilsa yopilsin.
  useEffect(() => {
    if (!ochiq) return undefined;
    function tashqariga(e) {
      if (qutiRef.current && !qutiRef.current.contains(e.target)) setOchiq(false);
    }
    window.addEventListener("mousedown", tashqariga);
    return () => window.removeEventListener("mousedown", tashqariga);
  }, [ochiq]);

  async function hammasiniOqilganQil() {
    try {
      await api("/api/bildirishnomalar/", { method: "POST", body: { hammasi: true } });
      yukla();
    } catch {
      // Belgilash muvaffaqiyatsiz bo'lsa ham ro'yxat ko'rinib turadi —
      // bu faqat "o'qilgan" bayrog'i, muhim ma'lumot yo'qolmaydi.
    }
  }

  const oqilmagan = malumot?.oqilmagan || 0;
  const royxat = malumot?.bildirishnomalar || [];

  return (
    <div ref={qutiRef} style={{ position: "relative" }}>
      <button
        className="tema-tugma"
        onClick={() => setOchiq((v) => !v)}
        aria-label={t("bildirishnomalar")}
        title={t("bildirishnomalar")}
      >
        🔔
        {oqilmagan > 0 && (
          <span
            style={{
              position: "absolute", top: 0, right: 0, minWidth: 16, height: 16,
              padding: "0 3px", borderRadius: 8, background: "var(--xato)",
              color: "#fff", fontSize: 10, lineHeight: "16px", fontWeight: 700,
            }}
          >
            {oqilmagan}
          </span>
        )}
      </button>
      {ochiq && (
        <div
          style={{
            position: "absolute", top: "100%", right: 0, marginTop: 6, width: 340,
            maxHeight: 420, overflowY: "auto", background: "var(--sirt)",
            border: "1px solid var(--chiziq)", borderRadius: 10, padding: 10,
            boxShadow: "0 6px 24px rgba(0,0,0,0.25)",
            // Kurslar sahifasidagi yuklash qoplamasi 1000 da — ustida tursin.
            zIndex: 1200,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
            <strong>{t("bildirishnomalar")}</strong>
            {oqilmagan > 0 && (
              <button className="tugma ikkinchi kichik" onClick={hammasiniOqilganQil}>
                {t("bildirishnoma_hammasi_oqildi")}
              </button>
            )}
          </div>
          {royxat.length === 0 ? (
            <div className="izoh">{t("bildirishnoma_yoq")}</div>
          ) : (
            royxat.map((b) => (
              <div
                key={b.id}
                style={{
                  padding: "8px 0", borderTop: "1px solid var(--chiziq)",
                  opacity: b.oqilgan ? 0.6 : 1,
                }}
              >
                <div style={{ fontWeight: 700, marginBottom: 4 }}>
                  {b.oqilgan ? "" : "• "}{b.sarlavha}
                </div>
                <ul className="izoh" style={{ margin: 0, paddingLeft: 18 }}>
                  {bandlarniAjrat(b.matn).map((band, k) => (
                    <li key={k} style={{ marginBottom: 3 }}>{band}</li>
                  ))}
                </ul>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default function Layout() {
  const { til, tilniQoy, t } = useI18n();
  const navigate = useNavigate();
  const { profil } = useProfil();
  const { testFaol } = useTestRejimi();
  const [menyuOchiq, setMenyuOchiq] = useState(false);
  // 2026-08-18, foydalanuvchi talabi: yon panelni YIG'IB qo'yish (ekran
  // joyi kengaysin), keyin qaytarish uchun alohida tugma. Tanlov
  // localStorage'da saqlanadi — har sahifa yangilanganda qayta yig'ish
  // shart emas. Faqat KENG ekran uchun: mobil (<900px) da panel
  // allaqachon "☰" orqali chiqadi/yopiladi.
  const [panelYigilgan, setPanelYigilgan] = useState(
    () => localStorage.getItem("panel_yigilgan") === "1",
  );

  function panelniAlmashtir() {
    setPanelYigilgan((v) => {
      localStorage.setItem("panel_yigilgan", v ? "0" : "1");
      return !v;
    });
  }

  // 2026-08-19, foydalanuvchi talabi: uzun ism-familiya yon panelda 2
  // qatorga sig'sin, kerak bo'lsa shrift kichrayadi (avval har harfda
  // sinib, uch qatorga bo'linib ketardi — `overflow-wrap: anywhere`).
  const ismUzunmi = (profil?.ism || "").length > 16;
  const markazNomi = profil?.markaz?.name || "Utmost o'quv markazi";
  // Owner markazga biriktirilmagan (markaz=null) — shu holatda ham standart
  // logo ko'rsatiladi, umumiy "U" harfiga tushib qolmasin.
  const markazLogo = profil?.markaz?.logo_url
    ? mediaManzil(profil.markaz.logo_url)
    : "/logo.jpg";
  useEffect(() => {
    if (profil?.markaz?.brend_rang) {
      document.documentElement.style.setProperty("--sariq", profil.markaz.brend_rang);
    }
  }, [profil]);

  // Brauzer tab sarlavhasi va favicon — markaz nomi/logotipiga moslanadi.
  // 2026-08-19, foydalanuvchi talabi: sarlavhada FAQAT markaz nomi
  // chiqsin — avval "{nom} — IELTS platforma" qo'shimchasi bor edi.
  useEffect(() => {
    document.title = markazNomi;
    if (markazLogo) {
      let ikon = document.querySelector('link[rel="icon"]');
      if (!ikon) {
        ikon = document.createElement("link");
        ikon.rel = "icon";
        document.head.appendChild(ikon);
      }
      ikon.type = "";
      ikon.href = markazLogo;
    }
  }, [markazNomi, markazLogo, t]);

  // Menyu QAT'IY rol jadvalidan quriladi (`ROL_PANELLARI`) — "Markazlar"
  // bo'limi ataylab hech bir rolda yo'q (2026-07-21, sahifa/backend
  // joyida), "Faoliyat tarixi" esa alohida bo'lim emas, "Hisobotlar"
  // ichiga ko'chgan. "/profil" oxirida — u jadvalda emas, chunki HAR
  // rolga beriladi (`MAJBURIY_PANELLAR`).
  const navlar = menyuQur(
    [...rolPanellariOl(profil?.role, profil?.is_owner), "/profil"],
    profil?.role
  );

  // 2026-08-05, foydalanuvchi qarori: rolga QO'SHIMCHA cheklov — owner
  // yoki admin bu foydalanuvchiga "korinadigan_panellar" belgilagan
  // bo'lsa (backend ruxsat tekshiruvlari o'zgarmaydi, bu FAQAT
  // navigatsiyani qo'shimcha toraytiradi), faqat shu ro'yxatdagi
  // yo'llar ko'rsatiladi. Owner O'ZIGA bu cheklovni qo'llamaydi (aks
  // holda o'zini panellardan mahrum qilib qo'yishi mumkin edi).
  // `MAJBURIY_PANELLAR` har doim qoladi.
  const yakuniyNavlar =
    !profil?.is_owner && profil?.korinadigan_panellar
      ? navlar.filter(
          (n) =>
            MAJBURIY_PANELLAR.includes(n.yol) ||
            profil.korinadigan_panellar.includes(n.yol)
        )
      : navlar;

  function temaAlmash() {
    const r = document.documentElement;
    const hozirgi =
      r.dataset.theme ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    r.dataset.theme = hozirgi === "dark" ? "light" : "dark";
    localStorage.setItem("tema", r.dataset.theme);
  }

  function chiqish() {
    if (testFaol) {
      window.alert(t("test_faol_navigatsiya_yoq"));
      return;
    }
    tokenlarniTozala();
    navigate("/login");
  }

  return (
    <div className={"qobiq" + (panelYigilgan ? " panel-yigilgan" : "")}>
      <div
        className={"menyu-parda" + (menyuOchiq ? " ochiq" : "")}
        onClick={() => setMenyuOchiq(false)}
      />
      <nav className={"sidebar" + (menyuOchiq ? " ochiq" : "")}>
        {/* 2026-08-09 talabi: bu yerda markaz nomi/logotipi emas, FOYDALANUVCHINING
            o'zi ko'rinadi — profil rasmi va ism-familiyasi, ustiga bosilganda o'z
            profiliga o'tadi. Markaz nomi topbar sarlavhasida, logotipi esa brauzer
            tab ikonkasida qoladi (yuqoridagi `markazLogo` shu uchun saqlanadi). */}
        <div className="sidebar-bosh">
        <Link to="/profil" className="logo" onClick={() => setMenyuOchiq(false)}>
          <Avatar rasmUrl={profil?.rasm_url} olcham={38} sarlavha={t("nav_profil")} />
          <div className="logo-nom">
            {/* Ism-familiya alohida "qutida" 2 qatorga cheklanadi (ortig'i
                "..." bilan kesiladi) — rol yorlig'i (OWNER va h.k.) shu
                cheklovdan TASHQARIDA, doim to'liq ko'rinadi. */}
            <span className={"logo-nom-matn" + (ismUzunmi ? " logo-nom-kichik" : "")}>
              {profil?.ism || t("platforma")}
            </span>
            {/* 2026-07-29 talabi: foydalanuvchi qaysi rol nazari bilan
                ko'rayotganini aniqlash uchun — ayniqsa owner "Ko'rish
                rejimi"da bo'lganda, ekranda qaysi profilni sinab
                ko'rayotganini unutmasligi uchun. */}
            {profil && (
              <small className="rol-korsatkich">
                {profil.is_owner ? t("rol_owner") : t(`rol_${profil.role}`)}
              </small>
            )}
          </div>
        </Link>
        <button
          className="panel-yigish"
          onClick={panelniAlmashtir}
          title={t("panel_yigish")}
          aria-label={t("panel_yigish")}
        >
          «
        </button>
        </div>
        {yakuniyNavlar.map((n) => (
          <NavLink
            key={n.yol}
            to={n.yol}
            end={n.yol === "/"}
            className={({ isActive }) =>
              "nav-tugma" + (isActive ? " aktiv" : "") + (testFaol ? " nofaol" : "")
            }
            title={testFaol ? t("test_faol_navigatsiya_yoq") : undefined}
            onClick={(e) => {
              // 2026-07-30 talabi: test yechilayotganda boshqa bo'limga
              // o'tish MUMKIN EMAS — havola DOM'da qoladi (fokusdan
              // chiqib ketmasin), lekin bosilganda hech qayerga
              // yubormaydi, faqat sababini tushuntiradi.
              if (testFaol) {
                e.preventDefault();
                window.alert(t("test_faol_navigatsiya_yoq"));
                return;
              }
              setMenyuOchiq(false);
            }}
          >
            <span className="nav-ikon">{n.ikon}</span>
            {t(n.kalit)}
          </NavLink>
        ))}
        <div style={{ flex: 1 }} />
        <button className="nav-tugma" onClick={chiqish}>
          <span className="nav-ikon">⇥</span>
          {t("nav_chiqish")}
        </button>
      </nav>

      <div className="asosiy">
        <header className="topbar">
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <button
              className="menyu-tugma"
              onClick={() => setMenyuOchiq((v) => !v)}
              aria-label="Menyu"
            >
              ☰
            </button>
            {/* Yon panel yig'ilgan bo'lsa — uni qaytaradigan tugma. */}
            <button
              className="panel-ochish"
              onClick={panelniAlmashtir}
              title={t("panel_ochish")}
              aria-label={t("panel_ochish")}
            >
              »
            </button>
            <h1>{markazNomi}</h1>
          </div>
          <div className="topbar-ong">
            <div className="til-guruh" role="group" aria-label="Til">
              {["uz", "ru", "en"].map((t2) => (
                <button
                  key={t2}
                  className={til === t2 ? "aktiv" : ""}
                  onClick={() => tilniQoy(t2)}
                >
                  {t2.toUpperCase()}
                </button>
              ))}
            </div>
            {/* 2026-08-09: avval faqat owner'ga ko'rinardi (yagona manba
                reliz xabari edi). Endi har kimga — "Ogohlantirish" turi
                qo'shildi (profil rasmi o'chirilganda egasiga boradi). */}
            {profil && <Bildirishnomalar t={t} />}
            <button className="tema-tugma" onClick={temaAlmash} aria-label="Tema">
              ◐
            </button>
          </div>
        </header>
        <main className="kontent">
          {profil && !profil.parol_bormi && (
            <div className="karta parol-ogohlantirish">
              {t("parol_ogohlantirish")}{" "}
              <NavLink to="/profil">{t("parol_qoy")}</NavLink>
            </div>
          )}
          <Outlet />
        </main>
        <IjtimoiyPanel havolalar={profil?.markaz?.ijtimoiy} />
      </div>
    </div>
  );
}
