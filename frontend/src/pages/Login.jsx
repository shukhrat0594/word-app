import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, tokenlarniSaqla, qurilmaIdOl, qurilmaBelgilari } from "../api";
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

  // 2026-10-20: admin qurilmani o'chirgani/almashtirgani yoki (2026-10-26)
  // talaba boshqa qurilmasidan kirgani uchun chiqarilgan bo'lsa
  // (`api.js: chiqishSababiniYoz`) — sababi bir marta aytiladi.
  useEffect(() => {
    try {
      const xabar = { qurilma: "login_qurilma_ochirildi", boshqa_qurilma: "login_boshqa_qurilmada" }[
        sessionStorage.getItem("chiqish_sababi")
      ];
      if (xabar) {
        sessionStorage.removeItem("chiqish_sababi");
        setXodimForma(true);
        setXato(t(xabar));
      }
    } catch {
      // sessionStorage yopiq — xabarsiz davom etadi
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function xodimKirish(e) {
    e.preventDefault();
    setXato("");
    setBand(true);
    try {
      const data = await api("/api/token/", {
        method: "POST",
        body: {
          username: login,
          password: parol,
          qurilma_id: qurilmaIdOl(),
          qurilma_belgilari: await qurilmaBelgilari(),
        },
      });
      tokenlarniSaqla(data);
      await yangila();
      navigate("/");
    } catch (e) {
      // 2026-08-15: Railway ko'chirish davrida owner'dan boshqa hech kim
      // kira olmaydigan holat — backend `kod: "kirish_cheklangan"` bilan
      // 403 qaytaradi, alohida tushunarli xabar ko'rsatiladi.
      const d = e?.data;
      if (d?.kod === "kirish_cheklangan") {
        setXato(t("login_kirish_cheklangan"));
      } else if (d?.kod === "qurilma_mos_emas") {
        // 2026-10-20: ruxsat etilgan qurilma nomi ko'rsatiladi — ko'pincha
        // o'quvchi saytni boshqa brauzerda (masalan Telegram ichida) ochgan bo'ladi.
        setXato(
          d.sorov === "rad"
            ? t("login_qurilma_rad")
            : t("login_qurilma_xato").replace("{nomlar}", (d.ruxsat_etilgan || []).join(", ") || "—")
        );
      } else if (e?.status === 429) {
        setXato(t("login_kop_urinish"));
      } else if (d?.kod === "qurilma_id_yoq" || !e?.status) {
        // 2026-10-23: qurilma ID'si yuborilmagan yoki so'rov umuman ketmagan
        // (internet / brauzer xatosi) — bu parol xatosi emas.
        setXato(t("login_ulanish_xato"));
      } else {
        setXato(t("login_xato"));
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
