import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { tokenOl } from "./api";
import Layout from "./components/Layout";
import BoshSahifa from "./pages/BoshSahifa";
import Davomat from "./pages/Davomat";
import DavomatHisoboti from "./pages/DavomatHisoboti";
import Foydalanuvchilar from "./pages/Foydalanuvchilar";
import Guruhlar from "./pages/Guruhlar";
import Ielts from "./pages/Ielts";
import ImtihonBoshqarish from "./pages/ImtihonBoshqarish";
import Leaderboard from "./pages/Leaderboard";
import Login from "./pages/Login";
import Mashqlar from "./pages/Mashqlar";
import MashqlarBoshqarish from "./pages/MashqlarBoshqarish";
import MarkazSozlash from "./pages/MarkazSozlash";
import Markazlar from "./pages/Markazlar";
import Oyinlar from "./pages/Oyinlar";
import Profil from "./pages/Profil";
import Tarix from "./pages/Tarix";
import Xodimlar from "./pages/Xodimlar";

function Himoyalangan({ children }) {
  return tokenOl() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
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
          <Route path="mashqlar" element={<Mashqlar />} />
          <Route path="mashqlar-boshqarish" element={<MashqlarBoshqarish />} />
          <Route path="ielts" element={<Ielts />} />
          <Route path="ielts-boshqarish" element={<ImtihonBoshqarish />} />
          <Route path="reyting" element={<Leaderboard />} />
          <Route path="oyinlar" element={<Oyinlar />} />
          <Route path="tarix" element={<Tarix />} />
          <Route path="guruhlar" element={<Guruhlar />} />
          <Route path="davomat" element={<Davomat />} />
          <Route path="davomat-hisoboti" element={<DavomatHisoboti />} />
          <Route path="markazlar" element={<Markazlar />} />
          <Route path="xodimlar" element={<Xodimlar />} />
          <Route path="markaz-sozlash" element={<MarkazSozlash />} />
          <Route path="foydalanuvchilar" element={<Foydalanuvchilar />} />
          <Route path="profil" element={<Profil />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
