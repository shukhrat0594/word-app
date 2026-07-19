import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { mediaManzil, tokenlarniTozala } from "../api";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";

const TALABA_NAVLAR = [
  { yol: "/", ikon: "▦", kalit: "nav_dashboard" },
  { yol: "/mashqlar", ikon: "✎", kalit: "nav_mashqlar" },
  { yol: "/oyinlar", ikon: "🎮", kalit: "nav_oyinlar" },
  { yol: "/tarix", ikon: "🕐", kalit: "nav_tarix" },
  { yol: "/reyting", ikon: "🏆", kalit: "nav_reyting" },
];

function navlarniOl(role) {
  if (role === "admin") {
    return [
      { yol: "/", ikon: "▦", kalit: "nav_dashboard" },
      { yol: "/guruhlar", ikon: "☰", kalit: "nav_guruhlar" },
      { yol: "/xodimlar", ikon: "🧑‍🏫", kalit: "nav_xodimlar" },
      { yol: "/mashqlar-boshqarish", ikon: "🗂", kalit: "nav_mashqlar_boshqarish" },
      { yol: "/davomat", ikon: "🗓", kalit: "nav_davomat" },
      { yol: "/davomat-hisoboti", ikon: "📊", kalit: "nav_davomat_hisoboti" },
      { yol: "/markaz-sozlash", ikon: "🎨", kalit: "nav_markaz_sozlama" },
    ];
  }
  if (role === "teacher") {
    return [
      { yol: "/", ikon: "▦", kalit: "nav_dashboard" },
      { yol: "/davomat", ikon: "🗓", kalit: "nav_davomat" },
    ];
  }
  if (role === "parent") {
    return [{ yol: "/", ikon: "👪", kalit: "nav_dashboard" }];
  }
  return TALABA_NAVLAR;
}

export default function Layout() {
  const { til, tilniQoy, t } = useI18n();
  const navigate = useNavigate();
  const { profil } = useProfil();
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

  // Owner'ning o'z markazi yo'q — "Markaz sozlash" (bitta markazga tegishli)
  // unga emas, balki "Markazlar" (barchasi) paneliga tegishli.
  const asosiyNavlar = navlarniOl(profil?.role).filter(
    (n) => !(profil?.is_owner && n.yol === "/markaz-sozlash")
  );
  const navlar = [
    ...asosiyNavlar,
    ...(profil?.is_owner
      ? [
          { yol: "/markazlar", ikon: "🏢", kalit: "nav_markazlar" },
          { yol: "/foydalanuvchilar", ikon: "🧑‍🤝‍🧑", kalit: "nav_foydalanuvchilar" },
        ]
      : []),
    { yol: "/profil", ikon: "👤", kalit: "nav_profil" },
  ];

  function temaAlmash() {
    const r = document.documentElement;
    const hozirgi =
      r.dataset.theme ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    r.dataset.theme = hozirgi === "dark" ? "light" : "dark";
    localStorage.setItem("tema", r.dataset.theme);
  }

  function chiqish() {
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
        <div className="logo">
          {markazLogo ? (
            <img className="logo-rasm" src={markazLogo} alt={markazNomi} />
          ) : (
            <div className="logo-belgi">U</div>
          )}
          <div className="logo-nom">
            {markazNomi}
            <small>{profil?.ism || t("platforma")}</small>
          </div>
        </div>
        {navlar.map((n) => (
          <NavLink
            key={n.yol}
            to={n.yol}
            end={n.yol === "/"}
            className={({ isActive }) => "nav-tugma" + (isActive ? " aktiv" : "")}
            onClick={() => setMenyuOchiq(false)}
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
      </div>
    </div>
  );
}
