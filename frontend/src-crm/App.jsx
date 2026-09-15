// CRM ilovasining ildizi — kirish nazorati va marshrutlar.
//
// LMS'ning `src/App.jsx` bilan hech qanday aloqasi yo'q: alohida bundle,
// alohida marshrut daraxti, alohida CSS.

import { useCallback, useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { api, tokenOl, tokenlarniTozala } from "./api.js";
import { FilialProvider } from "./filialContext.jsx";
import { ProfilProvider } from "./profilContext.jsx";
import { useI18n } from "./i18n.jsx";
import Kirish from "./Kirish.jsx";
import Layout from "./Layout.jsx";
import BoshSahifa from "./sahifalar/BoshSahifa.jsx";
import Guruhlar from "./sahifalar/Guruhlar.jsx";
import Hisobotlar from "./sahifalar/Hisobotlar.jsx";
import Moliya from "./sahifalar/Moliya.jsx";
import Narxlar from "./sahifalar/Narxlar.jsx";
import Sozlamalar from "./sahifalar/Sozlamalar.jsx";
import Talabalar from "./sahifalar/Talabalar.jsx";

/** CRM'ga kira oladigan rollar. Bu — faqat KO'RINISH nazorati;
 *  haqiqiy himoya backendda (`crm.permissions.CrmRuxsati`), chunki
 *  frontendda yashirish hech qanday himoya emas. */
function crmGaKiraOladi(profil) {
  return Boolean(profil?.is_owner || profil?.role === "admin");
}

function XabarEkrani({ sarlavha, matn, havola }) {
  return (
    <div className="markaz-ekran">
      <div className="karta xabar-karta">
        <h1>{sarlavha}</h1>
        <p>{matn}</p>
        {havola}
      </div>
    </div>
  );
}

export default function App() {
  const { t } = useI18n();
  const [profil, setProfil] = useState(null);
  const [yuklanmoqda, setYuklanmoqda] = useState(true);

  const profilniOl = useCallback(async () => {
    if (!tokenOl()) {
      setProfil(null);
      setYuklanmoqda(false);
      return;
    }
    try {
      setProfil(await api("/api/profil/"));
    } catch {
      // Token yaroqsiz yoki kirish cheklangan — kirish oynasiga.
      tokenlarniTozala();
      setProfil(null);
    } finally {
      setYuklanmoqda(false);
    }
  }, []);

  useEffect(() => {
    profilniOl();
  }, [profilniOl]);

  if (yuklanmoqda) {
    return <div className="markaz-ekran">{t("yuklanmoqda")}</div>;
  }

  if (!profil) {
    return <Kirish onKirdi={profilniOl} />;
  }

  if (!crmGaKiraOladi(profil)) {
    // Owner "Ko'rish rejimi"ni Talaba/O'qituvchiga qo'ygan bo'lsa,
    // `role` SIMULYATSIYA qilingan qiymatni qaytaradi va CRM yopiladi.
    // Bu ATAYLAB shunday (butun loyiha shu qoidaga bo'ysunadi —
    // accounts/authentication.py), lekin sabab aytilmasa owner tizimni
    // buzuq deb o'ylaydi. Shuning uchun alohida xabar.
    const simulyatsiyada = profil.asl_owner_mi && profil.korish_rejimi !== "owner";
    return (
      <XabarEkrani
        sarlavha={simulyatsiyada ? t("korish_rejimi_sarlavha") : t("ruxsat_yoq_sarlavha")}
        matn={simulyatsiyada ? t("korish_rejimi_matn") : t("ruxsat_yoq_matn")}
        havola={<a className="tugma" href="/">{t("saytga_qaytish")}</a>}
      />
    );
  }

  return (
    // `basename="/crm"` — ilova sayt ildizida emas, `/crm` ostida
    // yashaydi. `/crm/moliya` kabi ichki manzillar sahifa yangilanganda
    // ham ishlashi uchun `vite.config.js` dagi `crmMarshrut` plagini
    // so'rovni `crm.html`ga qayta yozadi.
    // `FilialProvider` faqat SHU YERDA — ruxsat tekshiruvidan keyin:
    // u `/api/crm/filiallar/` ni so'raydi va tokensiz chaqirilsa
    // cheksiz qayta yuklanish hosil qilardi.
    <ProfilProvider profil={profil}>
    <FilialProvider>
      <BrowserRouter basename="/crm">
      <Routes>
        <Route element={<Layout profil={profil} />}>
          <Route index element={<BoshSahifa />} />
          <Route path="guruhlar" element={<Guruhlar />} />
          <Route path="talabalar" element={<Talabalar />} />
          <Route path="moliya" element={<Moliya />} />
          <Route path="narxlar" element={<Narxlar />} />
          <Route path="hisobotlar" element={<Hisobotlar />} />
          <Route path="sozlamalar" element={<Sozlamalar />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
      </BrowserRouter>
    </FilialProvider>
    </ProfilProvider>
  );
}
