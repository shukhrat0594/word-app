// CRM tashqi ko'rinishi — o'z sarlavhasi va menyusi.
// LMS menyusi bu yerda YO'Q (TZ 6.2).

import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { serverdaChiqish, tokenlarniTozala } from "./api.js";
import { EslatmaXabarProvider, XabarQongirogi } from "./EslatmaXabarlari.jsx";
import { TILLAR, useI18n } from "./i18n.jsx";
import FilialTanlash from "./FilialTanlash.jsx";
import { useRuxsat } from "./profilContext.jsx";
import { sorovSatri, useSorov } from "./soragich.js";

// `ruxsat` — backenddagi bo'lim kaliti (`crm/ruxsatlar.py`). Ruxsati
// yo'q band menyuda ko'rinmaydi.
const MENYU = [
  { yol: ".", kalit: "bosh_sahifa", ikon: "🏠", oxirigacha: true, ruxsat: "bosh_sahifa" },
  { yol: "lidlar", kalit: "lidlar", ikon: "🎯", ruxsat: "lidlar" },
  { yol: "guruhlar", kalit: "guruhlar", ikon: "📚", ruxsat: "guruhlar" },
  { yol: "talabalar", kalit: "talabalar", ikon: "👤", ruxsat: "talabalar" },
  { yol: "moliya", kalit: "moliya", ikon: "💰", ruxsat: "moliya" },
  // Narxlar ATAYLAB alohida band (Shuhrat talabi 2026-09-14): u
  // hisobot emas, SOZLAMA — bir marta kiritiladi va butun tizimga
  // ta'sir qiladi, shuning uchun ko'rinadigan joyda turishi kerak.
  { yol: "narxlar", kalit: "narxlar", ikon: "🏷️", ruxsat: "sozlamalar" },
  { yol: "hisobotlar", kalit: "hisobotlar", ikon: "📊", ruxsat: "hisobotlar" },
  { yol: "xodimlar", kalit: "xodimlar", ikon: "🧑‍🏫", ruxsat: "xodimlar" },
  { yol: "sozlamalar", kalit: "sozlamalar", ikon: "⚙️", ruxsat: "sozlamalar" },
  { yol: "harakatlar", kalit: "harakatlar_tarixi", ikon: "🕘", ruxsat: "sozlamalar" },
];

// Sarlavhadagi tezkor qidiruv — istalgan CRM sahifasidan o'quvchini
// ismi yoki telefoni bilan topib, kartasini ochadi (video-TZ, SoffCRM
// bosh sahifasidagi qidiruv ko'rinishi).
function TezQidiruv() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [qidiruv, setQidiruv] = useState("");
  const [ochiq, setOchiq] = useState(false);
  const joy = useRef(null);
  const izlov = qidiruv.trim();
  const { malumot } = useSorov(izlov.length >= 2 ? "/api/crm/talaba-qidiruv/" + sorovSatri({ q: izlov }) : null);

  useEffect(() => {
    if (!ochiq) return undefined;
    const yop = (ev) => { if (joy.current && !joy.current.contains(ev.target)) setOchiq(false); };
    document.addEventListener("mousedown", yop);
    return () => document.removeEventListener("mousedown", yop);
  }, [ochiq]);

  function tanla(talabaId) {
    setOchiq(false);
    setQidiruv("");
    navigate(`/talabalar?talaba=${talabaId}`);
  }

  return (
    <span className="crm-qidiruv" ref={joy}>
      <input
        placeholder={t("oquvchini_qidiring")}
        value={qidiruv}
        onChange={(e) => { setQidiruv(e.target.value); setOchiq(true); }}
        onFocus={() => setOchiq(true)}
      />
      {ochiq && izlov.length >= 2 && (malumot || []).length > 0 && (
        <ul className="qidiruv-natija crm-qidiruv-natija">
          {malumot.map((x) => (
            <li key={x.id}>
              <button className="havola" type="button" onClick={() => tanla(x.id)}>
                {x.ism} <span className="kichik">{x.telefon || x.username}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </span>
  );
}

export default function Layout({ profil }) {
  const { til, setTil, t } = useI18n();
  const ruxsat = useRuxsat();

  async function chiq() {
    await serverdaChiqish();
    tokenlarniTozala();
    window.location.href = "/crm";
  }

  return (
    <EslatmaXabarProvider>
    <div className="crm">
      <header className="crm-sarlavha">
        <div className="crm-logo">
          <span className="crm-belgi">💰</span>
          <span>{t("crm")}</span>
        </div>

        <FilialTanlash />

        <TezQidiruv />

        <div className="crm-onng">
          <XabarQongirogi />
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
        {MENYU.filter((band) => ruxsat(band.ruxsat)).map((band) => (
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
    </EslatmaXabarProvider>
  );
}
