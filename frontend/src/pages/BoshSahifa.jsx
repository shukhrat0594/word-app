import { Navigate } from "react-router-dom";
import { useProfil } from "../profilContext";
import Dashboard from "./Dashboard";
import OtaOna from "./OtaOna";

export default function BoshSahifa() {
  const { profil } = useProfil();

  if (!profil) return null;
  if (profil.role === "parent") return <OtaOna />;
  // Matn-TZ 779: Head Teacher kirganda o'quvchi paneli emas, o'z dashboardi.
  if (profil.role === "head_teacher") return <Navigate to="/head-teacher" replace />;
  return <Dashboard />;
}
