import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, tokenlarniSaqla, qurilmaIdOl } from "../api";
import { useI18n } from "../i18n";
import IjtimoiyPanel from "../components/IjtimoiyPanel";
import { useProfil } from "../profilContext";

// 2026-08-05, foydalanuvchi qarori: Gmail orqali ro'yxatdan o'tish
// yopildi — Google Identity Services tugmasi endi ko'rsatilmaydi.
// Backend endpoint (`/api/auth/google/`) ham yangi hisob YARATISHNI
// rad etadi (`accounts/views.py: GoogleLoginView`), faqat oldin shu
// yo'l bilan yaratilgan mavjud hisoblar kirishda davom eta oladi.

export default function Login() {
  const { t } = useI18n();
  const { yangila } = useProfil();
  const navigate = useNavigate();
  // 2026-08-18, foydalanuvchi talabi: markaz nomi HAMMA joyda chiqsin.
  // Login ekranida profil yo'q (hali kirilmagan), shuning uchun nom OCHIQ
  // `/api/ijtimoiy/` endpointidan olinadi. Kelmaguncha standart nom turadi.
  const [markazNomi, setMarkazNomi] = useState("Utmost o'quv markazi");
  const [login, setLogin] = useState("");
  const [parol, setParol] = useState("");
  const [xato, setXato] = useState("");

  useEffect(() => {
    let bekor = false;
    api("/api/ijtimoiy/")
      .then((d) => {
        if (bekor || !d?.markaz_nomi) return;
        setMarkazNomi(d.markaz_nomi);
        document.title = d.markaz_nomi;
      })
      .catch(() => {});
    return () => {
      bekor = true;
    };
  }, []);
  const [band, setBand] = useState(false);
  const [xodimForma, setXodimForma] = useState(false);

  async function xodimKirish(e) {
    e.preventDefault();
    setXato("");
    setBand(true);
    try {
      const data = await api("/api/token/", {
        method: "POST",
        body: { username: login, password: parol, qurilma_id: qurilmaIdOl() },
      });
      tokenlarniSaqla(data);
      await yangila();
      navigate("/");
    } catch (e) {
      // 2026-08-15: Railway ko'chirish davrida owner'dan boshqa hech kim
      // kira olmaydigan holat — backend `kod: "kirish_cheklangan"` bilan
      // 403 qaytaradi, alohida tushunarli xabar ko'rsatiladi.
      if (e?.data?.kod === "kirish_cheklangan") {
        setXato(t("login_kirish_cheklangan"));
      } else {
        setXato(e?.data?.kod === "qurilma_mos_emas" ? t("login_qurilma_xato") : t("login_xato"));
      }
    } finally {
      setBand(false);
    }
  }

  return (
    <div className="login-qobiq">
      <div className="login-ekran">
      <div className="login-brend">
        <div className="login-brend-sarlavha">
          <img src="/logo.jpg" alt={markazNomi} className="katta-logo" />
          <div className="login-markaz-nomi">{markazNomi}</div>
        </div>
        <h2>{t("login_sarlavha")}</h2>
      </div>
      <div className="login-forma">
        <h3>{t("kirish")}</h3>
        {!xodimForma ? (
          <button
            type="button"
            className="tugma ikkinchi"
            onClick={() => setXodimForma(true)}
          >
            {t("xodim_kirish")}
          </button>
        ) : (
          <>
            <div className="yoki">{t("yoki_xodim")}</div>
            {/* 2026-08-15: `name`/`id` ATRIBUTLARI SHART — brauzer parol
                menejeri (Chrome/Edge) formani shular orqali tanidi va
                "parolni saqlaymi?" taklifini beradi. Faqat `autoComplete`
                bilan bu ba'zan ishlamas edi. Eslatma: parollar sayt
                MANZILI bo'yicha saqlanadi — yangi domenda (masalan
                Railway) bir marta qaytadan saqlash kerak bo'ladi. */}
            <form onSubmit={xodimKirish} style={{ display: "grid", gap: 14 }}>
              <input
                id="login-username"
                name="username"
                placeholder="Login"
                value={login}
                onChange={(e) => setLogin(e.target.value)}
                autoComplete="username"
              />
              <input
                id="login-parol"
                name="password"
                type="password"
                placeholder="Parol"
                value={parol}
                onChange={(e) => setParol(e.target.value)}
                autoComplete="current-password"
              />
              <p className="izoh" style={{ margin: 0 }}>{t("xodim_izoh")}</p>
              {xato && <div className="xato-xabar">{xato}</div>}
              <button type="submit" className="tugma katta" disabled={band}>
                {t("kirish")}
              </button>
            </form>
          </>
        )}
        </div>
      </div>
      <IjtimoiyPanel />
    </div>
  );
}
