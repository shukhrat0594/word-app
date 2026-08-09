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

// 2026-08-05 — "Ko'rinadigan panellar" tanlovi (Foydalanuvchilar/
// Talabalar sahifasidagi checkbox ro'yxati) shu yerdan olinadi, nav
// yo'llari bilan bir joyda saqlanishi uchun (ikkalasi sinxron qolsin).
export const PANEL_TANLOV = [
  { yol: "/ielts-boshqarish", kalit: "nav_ielts_boshqarish" },
  { yol: "/ai-mashqlari", kalit: "nav_ai_mashqlari" },
  { yol: "/kurslar", kalit: "nav_kurslar" },
  { yol: "/oyinlar", kalit: "nav_oyinlar" },
  { yol: "/tarix", kalit: "nav_tarix" },
  { yol: "/reyting", kalit: "nav_reyting" },
  { yol: "/guruhlar", kalit: "nav_guruhlar" },
  { yol: "/talabalar", kalit: "nav_talabalar" },
  { yol: "/xodimlar", kalit: "nav_xodimlar" },
  { yol: "/davomat", kalit: "nav_davomat" },
  { yol: "/ijtimoiy-tarmoqlar", kalit: "nav_ijtimoiy" },
  { yol: "/foydalanuvchilar", kalit: "nav_foydalanuvchilar" },
  { yol: "/hisobotlar", kalit: "nav_hisobotlar" },
];

const TALABA_NAVLAR = [
  { yol: "/", ikon: "▦", kalit: "nav_dashboard" },
  ...(NAMUNAVIY_MASHQLAR_OCHIQ
    ? [{ yol: "/mashqlar", ikon: "✎", kalit: "nav_mashqlar" }]
    : []),
  { yol: "/ielts-boshqarish", ikon: "🎓", kalit: "nav_ielts_boshqarish" },
  { yol: "/ai-mashqlari", ikon: "🤖", kalit: "nav_ai_mashqlari" },
  { yol: "/kurslar", ikon: "📚", kalit: "nav_kurslar" },
  { yol: "/oyinlar", ikon: "🎮", kalit: "nav_oyinlar" },
  { yol: "/tarix", ikon: "🕐", kalit: "nav_tarix" },
  { yol: "/reyting", ikon: "🏆", kalit: "nav_reyting" },
];

// 2026-08-08, foydalanuvchi talabi: "ownerga hamma panellarni
// ko'rinadigan qilish kerak". Avval owner `navlarniOl("admin")`
// natijasini olardi va shu sababli Davomat, O'yinlar, Tarix, Reyting
// unga KO'RINMASDI (ular faqat o'qituvchi/talaba ro'yxatlarida bor
// edi). Endi owner uchun alohida, TO'LIQ ro'yxat.
//
// DIQQAT: bu FAQAT navigatsiya. Backend ruxsatlari o'zgarmagan —
// talabaga mo'ljallangan sahifalar (Reyting, Tarix, O'yinlar) ownerga
// uning O'Z ma'lumotini ko'rsatadi, ya'ni odatda bo'sh bo'ladi.
const OWNER_NAVLAR = [
  { yol: "/", ikon: "▦", kalit: "nav_dashboard" },
  { yol: "/guruhlar", ikon: "☰", kalit: "nav_guruhlar" },
  { yol: "/talabalar", ikon: "🎒", kalit: "nav_talabalar" },
  { yol: "/xodimlar", ikon: "🧑‍🏫", kalit: "nav_xodimlar" },
  { yol: "/davomat", ikon: "🗓", kalit: "nav_davomat" },
  { yol: "/ielts-boshqarish", ikon: "🎓", kalit: "nav_ielts_boshqarish" },
  { yol: "/ai-mashqlari", ikon: "🤖", kalit: "nav_ai_mashqlari" },
  { yol: "/kurslar", ikon: "📚", kalit: "nav_kurslar" },
  { yol: "/oyinlar", ikon: "🎮", kalit: "nav_oyinlar" },
  { yol: "/tarix", ikon: "🕐", kalit: "nav_tarix" },
  { yol: "/reyting", ikon: "🏆", kalit: "nav_reyting" },
];

function navlarniOl(role) {
  if (role === "admin") {
    return [
      { yol: "/", ikon: "▦", kalit: "nav_dashboard" },
      { yol: "/guruhlar", ikon: "☰", kalit: "nav_guruhlar" },
      { yol: "/talabalar", ikon: "🎒", kalit: "nav_talabalar" },
      { yol: "/xodimlar", ikon: "🧑‍🏫", kalit: "nav_xodimlar" },
      // 2026-07-21: "Mashqlar boshqarish" vaqtincha yopilgan (bo'lim o'zi
      // ham yopiq, MashqlarBoshqarish.jsx) — nav'dan ham olib tashlandi,
      // kerak bo'lsa qayta ochiladi.
      { yol: "/ielts-boshqarish", ikon: "🎓", kalit: "nav_ielts_boshqarish" },
      { yol: "/ai-mashqlari", ikon: "🤖", kalit: "nav_ai_mashqlari" },
      { yol: "/kurslar", ikon: "📚", kalit: "nav_kurslar" },
      { yol: "/ijtimoiy-tarmoqlar", ikon: "🔗", kalit: "nav_ijtimoiy" },
      // 2026-07-21: Davomat endi faqat o'qituvchida (u belgilaydi);
      // Davomat hisoboti "Hisobotlar" ostiga ko'chdi, faqat owner ko'radi.
      // 2026-07-21: "Markaz" (brend sozlash) bo'limi hech kimga ko'rinmasin
      // deb so'ralgan — nav'dan olib tashlandi (sahifa/backend tegilmadi).
    ];
  }
  if (role === "teacher") {
    return [
      { yol: "/", ikon: "▦", kalit: "nav_dashboard" },
      { yol: "/ielts-boshqarish", ikon: "🎓", kalit: "nav_ielts_boshqarish" },
      { yol: "/ai-mashqlari", ikon: "🤖", kalit: "nav_ai_mashqlari" },
      { yol: "/kurslar", ikon: "📚", kalit: "nav_kurslar" },
      { yol: "/guruhlar", ikon: "☰", kalit: "nav_guruhlar" },
      { yol: "/talabalar", ikon: "🎒", kalit: "nav_talabalar" },
      { yol: "/davomat", ikon: "🗓", kalit: "nav_davomat" },
    ];
  }
  if (role === "parent") {
    return [{ yol: "/", ikon: "👪", kalit: "nav_dashboard" }];
  }
  return TALABA_NAVLAR;
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
  useEffect(() => {
    document.title = `${markazNomi} — ${t("platforma")}`;
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

  // "IELTS testlari" va "Kurslar" talaba/admin/owner/teacher uchun ko'rinadi
  // — faqat "oddiy foydalanuvchi" ularni ko'rmaydi, unga faqat Mashqlar
  // ochiq (2026-07-20, Kurslar uchun 2026-07-21).
  const oddiyMi = profil?.role === "oddiy";
  const asosiyNavlar = (profil?.is_owner ? OWNER_NAVLAR : navlarniOl(profil?.role)).filter(
    // 2026-07-27: "AI mashqlari" oddiy foydalanuvchiga HAM ochiq (talabaga
    // ham) — "Namunaviy mashqlar" yopilgach unga hech qanday mashq
    // qolmagandi. Backendda ham shunday: `korinadigan_testlar` oddiy
    // foydalanuvchiga faqat AI manbali testlarni qaytaradi.
    (n) => !(oddiyMi && (n.yol === "/ielts-boshqarish" || n.yol === "/kurslar"))
  );
  // 2026-07-21: "Markazlar" bo'limi hozircha hech kimga ko'rinmaydi (nav'dan
  // olib tashlandi, sahifa/backend o'zi tegilmagan — kerak bo'lsa qaytariladi).
  // "Faoliyat tarixi" (audit) alohida bo'lim emas — "Hisobotlar" ichiga
  // ko'chdi (Davomat hisoboti bilan birga), faqat owner ko'radi.
  // Takrorlanmasin: owner roli "admin" bo'lsa "Ijtimoiy tarmoqlar" ikkala
  // ro'yxatdan ham kelib, React'da bir xil `key` bilan ikki marta chiqardi.
  const navlar = [
    ...asosiyNavlar,
    ...(profil?.is_owner
      ? [
          { yol: "/ijtimoiy-tarmoqlar", ikon: "🔗", kalit: "nav_ijtimoiy" },
          { yol: "/foydalanuvchilar", ikon: "🧑‍🤝‍🧑", kalit: "nav_foydalanuvchilar" },
          { yol: "/hisobotlar", ikon: "📊", kalit: "nav_hisobotlar" },
        ]
      : []),
    { yol: "/profil", ikon: "👤", kalit: "nav_profil" },
  ].filter((n, i, hammasi) => hammasi.findIndex((x) => x.yol === n.yol) === i);

  // 2026-08-05, foydalanuvchi qarori: rolga QO'SHIMCHA cheklov — owner
  // yoki admin bu foydalanuvchiga "korinadigan_panellar" belgilagan
  // bo'lsa (backend ruxsat tekshiruvlari o'zgarmaydi, bu FAQAT
  // navigatsiyani qo'shimcha toraytiradi), faqat shu ro'yxatdagi
  // yo'llar ko'rsatiladi. Owner O'ZIGA bu cheklovni qo'llamaydi (aks
  // holda o'zini panellardan mahrum qilib qo'yishi mumkin edi). "/" va
  // "/profil" har doim ko'rinadi.
  const yakuniyNavlar =
    !profil?.is_owner && profil?.korinadigan_panellar
      ? navlar.filter(
          (n) => n.yol === "/" || n.yol === "/profil" || profil.korinadigan_panellar.includes(n.yol)
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
    <div className="qobiq">
      <div
        className={"menyu-parda" + (menyuOchiq ? " ochiq" : "")}
        onClick={() => setMenyuOchiq(false)}
      />
      <nav className={"sidebar" + (menyuOchiq ? " ochiq" : "")}>
        {/* 2026-08-09 talabi: bu yerda markaz nomi/logotipi emas, FOYDALANUVCHINING
            o'zi ko'rinadi — profil rasmi va ism-familiyasi, ustiga bosilganda o'z
            profiliga o'tadi. Markaz nomi topbar sarlavhasida, logotipi esa brauzer
            tab ikonkasida qoladi (yuqoridagi `markazLogo` shu uchun saqlanadi). */}
        <Link to="/profil" className="logo" onClick={() => setMenyuOchiq(false)}>
          <Avatar rasmUrl={profil?.rasm_url} olcham={38} sarlavha={t("nav_profil")} />
          <div className="logo-nom">
            {profil?.ism || t("platforma")}
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
