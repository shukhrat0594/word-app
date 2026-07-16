import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api, tokenlarniTozala } from "../api";
import { useI18n } from "../i18n";

const NAVLAR = [
  { yol: "/", ikon: "▦", kalit: "nav_dashboard" },
  { yol: "/mashqlar", ikon: "✎", kalit: "nav_mashqlar" },
  { yol: "/writing", ikon: "✍", kalit: "nav_writing" },
  { yol: "/speaking", ikon: "🎙", kalit: "nav_speaking" },
  { yol: "/paketlar", ikon: "◈", kalit: "nav_paketlar" },
];

export default function Layout() {
  const { til, tilniQoy, t } = useI18n();
  const navigate = useNavigate();
  const [profil, setProfil] = useState(null);

  useEffect(() => {
    api("/api/profil/").then(setProfil).catch(() => {});
  }, []);

  const markazNomi = profil?.markaz?.name || "EduCenter";
  const markazLogo = profil?.markaz?.logo_url;

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
      <nav className="sidebar">
        <div className="logo">
          {markazLogo ? (
            <img className="logo-rasm" src={markazLogo} alt={markazNomi} />
          ) : (
            <div className="logo-belgi">U</div>
          )}
          <div className="logo-nom">
            {markazNomi}
            <small>{t("platforma")}</small>
          </div>
        </div>
        {NAVLAR.map((n) => (
          <NavLink
            key={n.yol}
            to={n.yol}
            end={n.yol === "/"}
            className={({ isActive }) => "nav-tugma" + (isActive ? " aktiv" : "")}
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
          <h1>{markazNomi}</h1>
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
          <Outlet />
        </main>
      </div>
    </div>
  );
}
