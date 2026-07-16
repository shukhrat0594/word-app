import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { tokenOl } from "./api";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";

function Himoyalangan({ children }) {
  return tokenOl() ? children : <Navigate to="/login" replace />;
}

function Tezkun({ nomi }) {
  return (
    <div className="karta">
      <h3>{nomi}</h3>
      <p className="izoh">Bu sahifa keyingi bosqichda quriladi (F3–F6).</p>
    </div>
  );
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
          <Route index element={<Dashboard />} />
          <Route path="mashqlar" element={<Tezkun nomi="Mashqlar" />} />
          <Route path="writing" element={<Tezkun nomi="Writing AI" />} />
          <Route path="speaking" element={<Tezkun nomi="Speaking AI" />} />
          <Route path="paketlar" element={<Tezkun nomi="Paketlar" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
