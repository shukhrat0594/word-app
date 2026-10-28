import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  api, tokenlarniSaqla, qurilmaIdOl, qurilmaBelgilari, kalitQollaydimi, kalitBilanTasdiqla,
  ilovaIchidami, chromeHavolasi,
} from "../api";
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
  // 2026-10-29 (qurilmalar limiti, 2-tizim): yangi brauzer yoki tarixi tozalangan brauzer —
  // «Qurilmangizni tasdiqlang» bosqichi (backend `kalit_kerak`: chipta + kalit sozlamalari).
  const [kalitBosqichi, setKalitBosqichi] = useState(null);
  // Telegram/Instagram ichidagi brauzerda qurilma kaliti ishlamaydi va xotirasi alohida —
  // kirish faqat Chrome yoki Safari'da.
  const [ilovada] = useState(ilovaIchidami);
  const [nusxalandi, setNusxalandi] = useState(false);

  // 2026-10-20: admin qurilmani o'chirgani/almashtirgani yoki (2026-10-26)
  // talaba boshqa qurilmasidan kirgani uchun chiqarilgan bo'lsa
  // (`api.js: chiqishSababiniYoz`) — sababi bir marta aytiladi.
  useEffect(() => {
    try {
      const xabar = {
        qurilma: "login_qurilma_ochirildi",
        boshqa_qurilma: "login_boshqa_qurilmada",
        bloklandi: "login_qurilma_bloklangan",
      }[
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

  function xatoMatni(e) {
    const d = e?.data;
    // 2026-08-15: Railway ko'chirish davrida owner'dan boshqa hech kim kira olmaydigan holat.
    if (d?.kod === "kirish_cheklangan") return t("login_kirish_cheklangan");
    if (d?.kod === "qurilma_mos_emas") {
      return t(d.sabab === "bloklangan" || d.sorov === "rad" ? "login_qurilma_bloklangan" : "login_qurilma_sorov");
    }
    if (d?.kod === "kalit_xatosi") return d.detail;
    if (e?.status === 429) return t("login_kop_urinish");
    // 2026-10-23: qurilma ID'si yuborilmagan yoki so'rov umuman ketmagan (internet / brauzer xatosi).
    if (d?.kod === "qurilma_id_yoq" || !e?.status) return t("login_ulanish_xato");
    if (e.status === 400 || e.status === 401) return t("login_xato");
    // 2026-10-29: server xatosi endi «parol noto'g'ri» bo'lib ko'rinmaydi.
    return t("login_server_xato");
  }

  async function kirildi(data) {
    tokenlarniSaqla(data);
    await yangila();
    navigate("/");
  }

  async function xodimKirish(e) {
    e.preventDefault();
    setXato("");
    setBand(true);
    try {
      const data = await api("/api/token/", {
        method: "POST",
        body: {
          // 2026-10-29: telefon klaviaturasi login oxiriga bo'sh joy qo'yishi mumkin.
          username: login.trim(),
          password: parol,
          qurilma_id: qurilmaIdOl(),
          qurilma_belgilari: await qurilmaBelgilari(),
          kalit_qollaydi: await kalitQollaydimi(),
        },
      });
      await kirildi(data);
    } catch (e) {
      if (e?.data?.kod === "kalit_kerak") {
        setKalitBosqichi(e.data);
      } else {
        setXato(xatoMatni(e));
      }
    } finally {
      setBand(false);
    }
  }

  /** «Qurilmangizni tasdiqlang»: telefon qulfi bilan kalitni tasdiqlash yoki «Bu yangi
   * qurilma». Kalit so'rovi BIRINCHI qadam bo'lishi shart — Safari uni faqat bosish
   * paytida (orada kutishsiz) ruxsat beradi. */
  async function kalitBilanDavom(kalitsiz) {
    setXato("");
    setBand(true);
    try {
      const body = { chipta: kalitBosqichi.chipta };
      if (kalitsiz) body.kalitsiz = true;
      else body.javob = await kalitBilanTasdiqla(kalitBosqichi.kalit);
      await kirildi(await api("/api/token/kalit/", { method: "POST", body }));
    } catch (e) {
      if (e instanceof DOMException) {
        // Bekor qilindi yoki bu brauzerda kalit yo'q — tanlov ekranida qolamiz.
        setXato(t("kalit_topilmadi"));
      } else {
        setKalitBosqichi(null);
        setXato(xatoMatni(e));
      }
    } finally {
      setBand(false);
    }
  }

  async function havolaniNusxala() {
    const havola = `${window.location.origin}/login`;
    try {
      await navigator.clipboard.writeText(havola);
      setNusxalandi(true);
    } catch {
      window.prompt(t("havolani_nusxalash"), havola);
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
        {ilovada ? (
          <div style={{ display: "grid", gap: 12 }}>
            <strong>{t("ilova_brauzer_sarlavha")}</strong>
            <p className="izoh" style={{ margin: 0 }}>{t("ilova_brauzer_izoh")}</p>
            {/Android/i.test(navigator.userAgent) ? (
              <a className="tugma katta" href={chromeHavolasi()}>{t("ilova_brauzer_chrome")}</a>
            ) : (
              <p className="izoh" style={{ margin: 0 }}>{t("ilova_brauzer_ios")}</p>
            )}
            <button type="button" className="tugma ikkinchi" onClick={havolaniNusxala}>
              {nusxalandi ? t("havola_nusxalandi") : t("havolani_nusxalash")}
            </button>
          </div>
        ) : kalitBosqichi ? (
          <div style={{ display: "grid", gap: 12 }}>
            <strong>{t("kalit_tasdiq_sarlavha")}</strong>
            <p className="izoh" style={{ margin: 0 }}>{t("kalit_tasdiq_izoh")}</p>
            {xato && <div className="xato-xabar">{xato}</div>}
            <button type="button" className="tugma katta" onClick={() => kalitBilanDavom(false)} disabled={band}>
              {t("kalit_tasdiqlash")}
            </button>
            <button type="button" className="tugma ikkinchi" onClick={() => kalitBilanDavom(true)} disabled={band}>
              {t("kalit_yangi_qurilma")}
            </button>
          </div>
        ) : !xodimForma ? (
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
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
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
