import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, tokenlarniSaqla } from "../api";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";

const GOOGLE_CLIENT_ID =
  "664162111049-l5kll7qhdboiurn3phhmqb7nd5j76hc9.apps.googleusercontent.com";

export default function Login() {
  const { t } = useI18n();
  const { yangila } = useProfil();
  const navigate = useNavigate();
  const googleDiv = useRef(null);
  const [login, setLogin] = useState("");
  const [parol, setParol] = useState("");
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);
  const [xodimForma, setXodimForma] = useState(false);

  useEffect(() => {
    // Google Identity Services tugmasi
    const urin = () => {
      if (!window.google?.accounts?.id || !googleDiv.current) return false;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (javob) => {
          try {
            const data = await api("/api/auth/google/", {
              method: "POST",
              body: { id_token: javob.credential },
            });
            tokenlarniSaqla(data);
            await yangila();
            navigate("/");
          } catch {
            setXato(t("login_xato"));
          }
        },
      });
      window.google.accounts.id.renderButton(googleDiv.current, {
        theme: "outline",
        size: "large",
        width: 356,
      });
      return true;
    };
    if (!urin()) {
      const interval = setInterval(() => urin() && clearInterval(interval), 300);
      return () => clearInterval(interval);
    }
  }, [navigate, t, yangila]);

  async function xodimKirish(e) {
    e.preventDefault();
    setXato("");
    setBand(true);
    try {
      const data = await api("/api/token/", {
        method: "POST",
        body: { username: login, password: parol },
      });
      tokenlarniSaqla(data);
      await yangila();
      navigate("/");
    } catch {
      setXato(t("login_xato"));
    } finally {
      setBand(false);
    }
  }

  return (
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
        <div ref={googleDiv} />
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
  );
}
