import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { tokenOl } from "./api";
import ErrorBoundary from "./components/ErrorBoundary";
import Layout, { NAMUNAVIY_MASHQLAR_OCHIQ } from "./components/Layout";
import BoshSahifa from "./pages/BoshSahifa";
import Foydalanuvchilar from "./pages/Foydalanuvchilar";
import Guruhlar from "./pages/Guruhlar";
import Hisobotlar from "./pages/Hisobotlar";
import ImtihonBoshqarish from "./pages/ImtihonBoshqarish";
import Kurslar from "./pages/Kurslar";
import Leaderboard from "./pages/Leaderboard";
import Login from "./pages/Login";
import Mashqlar from "./pages/Mashqlar";
import MashqlarBoshqarish from "./pages/MashqlarBoshqarish";
import MarkazSozlash from "./pages/MarkazSozlash";
import Markazlar from "./pages/Markazlar";
import Oyinlar from "./pages/Oyinlar";
import Profil from "./pages/Profil";
import Talabalar from "./pages/Talabalar";
import Xodimlar from "./pages/Xodimlar";

function Himoyalangan({ children }) {
  return tokenOl() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <Himoyalangan>
                <Layout />
              </Himoyalangan>
            }
          >
            <Route index element={<BoshSahifa />} />
            {/* 2026-07-27: "Namunaviy mashqlar" vaqtincha yopiq — bayroq
                `Layout.jsx`da, uni `true` qilish bilan bo'lim to'liq (mashqlari
                bilan) qaytadi. Yopiq holatda marshrut o'chirilmaydi, balki bosh
                sahifaga yo'naltiradi: marshrut butunlay olib tashlansa, eski
                xatcho'p yoki havola bo'sh oq sahifa berardi (sinovda shunday
                chiqdi — na nav, na kontent). */}
            <Route
              path="mashqlar"
              element={NAMUNAVIY_MASHQLAR_OCHIQ ? <Mashqlar /> : <Navigate to="/" replace />}
            />
            <Route path="mashqlar-boshqarish" element={<MashqlarBoshqarish />} />
            <Route path="ielts-boshqarish" element={<ImtihonBoshqarish manba="admin" />} />
            <Route path="ai-mashqlari" element={<ImtihonBoshqarish manba="ai" />} />
            <Route path="kurslar" element={<Kurslar />} />
            <Route path="reyting" element={<Leaderboard />} />
            <Route path="oyinlar" element={<Oyinlar />} />
            {/* 2026-08-15: "Tarix" alohida sahifa sifatida olib tashlandi
                (natijalar endi Profil sahifasida), "Davomat" esa guruh
                ichiga ko'chdi. Marshrutlar O'CHIRILMAYDI, balki yangi
                joyga yo'naltiradi — aks holda eski xatcho'p/havola bo'sh
                oq sahifa berardi (xuddi "/mashqlar" holatidagidek). */}
            <Route path="tarix" element={<Navigate to="/profil" replace />} />
            <Route path="guruhlar" element={<Guruhlar />} />
            <Route path="davomat" element={<Navigate to="/guruhlar" replace />} />
            <Route path="hisobotlar" element={<Hisobotlar />} />
            <Route path="markazlar" element={<Markazlar />} />
            <Route path="xodimlar" element={<Xodimlar />} />
            <Route path="talabalar" element={<Talabalar />} />
            <Route path="markaz-sozlash" element={<MarkazSozlash />} />
            <Route path="foydalanuvchilar" element={<Foydalanuvchilar />} />
            <Route path="profil" element={<Profil />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
