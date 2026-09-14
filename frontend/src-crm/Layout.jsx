// CRM tashqi ko'rinishi — o'z sarlavhasi va menyusi.
// LMS menyusi bu yerda YO'Q (TZ 6.2).

import { NavLink, Outlet } from "react-router-dom";

import { serverdaChiqish, tokenlarniTozala } from "./api.js";
import { TILLAR, useI18n } from "./i18n.jsx";
import FilialTanlash from "./FilialTanlash.jsx";

const MENYU = [
  { yol: ".", kalit: "bosh_sahifa", ikon: "🏠", oxirigacha: true },
  { yol: "guruhlar", kalit: "guruhlar", ikon: "📚" },
  { yol: "talabalar", kalit: "talabalar", ikon: "👤" },
  { yol: "moliya", kalit: "moliya", ikon: "💰" },
  // Narxlar ATAYLAB alohida band (Shuhrat talabi 2026-09-14): u
  // hisobot emas, SOZLAMA — bir marta kiritiladi va butun tizimga
  // ta'sir qiladi, shuning uchun ko'rinadigan joyda turishi kerak.
  { yol: "narxlar", kalit: "narxlar", ikon: "🏷️" },
  { yol: "hisobotlar", kalit: "hisobotlar", ikon: "📊" },
  { yol: "sozlamalar", kalit: "sozlamalar", ikon: "⚙️" },
  // Lidlar va Jadval — keyingi bosqichlarda qo'shiladi.
];

export default function Layout({ profil }) {
  const { til, setTil, t } = useI18n();

  async function chiq() {
    await serverdaChiqish();
    tokenlarniTozala();
    window.location.href = "/crm";
  }

  return (
    <div className="crm">
      <header className="crm-sarlavha">
        <div className="crm-logo">
          <span className="crm-belgi">💰</span>
          <span>{t("crm")}</span>
        </div>

        <FilialTanlash />

        <div className="crm-onng">
          <select
            className="til-tanlash"
            value={til}
            onChange={(e) => setTil(e.target.value)}
            aria-label="Til"
          >
            {TILLAR.map((x) => (
              <option key={x.kod} value={x.kod}>
                {x.nomi}
              </option>
            ))}
          </select>
          <span className="kichik">{profil.ism}</span>
          {/* LMS'ga qaytish — alohida ilova, shuning uchun oddiy <a>,
              NavLink emas (to'liq sahifa yuklanadi). */}
          <a className="tugma tugma-sokin" href="/">
            {t("saytga_qaytish")}
          </a>
          <button className="tugma tugma-sokin" type="button" onClick={chiq}>
            {t("chiqish")}
          </button>
        </div>
      </header>

      <nav className="crm-menyu">
        {MENYU.map((band) => (
          <NavLink
            key={band.kalit}
            to={band.yol}
            end={band.oxirigacha}
            className={({ isActive }) => (isActive ? "menyu-band faol" : "menyu-band")}
          >
            <span aria-hidden="true">{band.ikon}</span> {t(band.kalit)}
          </NavLink>
        ))}
      </nav>

      <main className="crm-asosiy">
        <Outlet />
      </main>
    </div>
  );
}
