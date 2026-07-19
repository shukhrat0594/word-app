import { useProfil } from "../profilContext";
import Dashboard from "./Dashboard";
import OtaOna from "./OtaOna";

export default function BoshSahifa() {
  const { profil } = useProfil();

  if (!profil) return null;
  if (profil.role === "parent") return <OtaOna />;
  return <Dashboard />;
}
