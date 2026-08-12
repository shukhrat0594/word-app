import { useState } from "react";
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
  const [login, setLogin] = useState("");
  const [parol, setParol] = useState("");
  const [xato, setXato] = useState("");
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
      setXato(e?.data?.kod === "qurilma_mos_emas" ? t("login_qurilma_xato") : t("login_xato"));
    } finally {
      setBand(false);
    }
  }

  return (
    <div className="login-qobiq">
      <div className="login-ekran">
      <div className="login-brend">
        <div className="login-brend-sarlavha">
          <img src="/logo.jpg" alt="Utmost" className="katta-logo" />
          <div className="login-markaz-nomi">Utmost o'quv markazi</div>
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
            <form onSubmit={xodimKirish} style={{ display: "grid", gap: 14 }}>
              <input
                placeholder="Login"
                value={login}
                onChange={(e) => setLogin(e.target.value)}
                autoComplete="username"
              />
              <input
                type="password"
                placeholder="Parol"
                value={parol}
                onChange={(e) => setParol(e.target.value)}
                autoComplete="current-password"
              />
              <p className="izoh" style={{ margin: 0 }}>{t("xodim_izoh")}</p>
              {xato && <div className="xato-xabar">{xato}</div>}
              <button className="tugma katta" disabled={band}>
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
