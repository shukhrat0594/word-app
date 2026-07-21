import { useState } from "react";
import { useI18n } from "../i18n";
import AuditHisobot from "./AuditHisobot";
import DavomatHisoboti from "./DavomatHisoboti";

/** Owner uchun — barcha hisobotlar bitta joyda: Davomat + Foydalanuvchilar
 * faoliyati (audit). Ikkalasi ham avval alohida nav bo'lim edi, endi shu
 * yerga birlashtirildi. */
export default function Hisobotlar() {
  const { t } = useI18n();
  const [tab, setTab] = useState("davomat");

  return (
    <div>
      <div className="tab-guruh" style={{ marginBottom: 14 }}>
        <button className={tab === "davomat" ? "aktiv" : ""} onClick={() => setTab("davomat")}>
          {t("nav_davomat_hisoboti")}
        </button>
        <button className={tab === "audit" ? "aktiv" : ""} onClick={() => setTab("audit")}>
          {t("nav_audit")}
        </button>
      </div>
      {tab === "davomat" ? <DavomatHisoboti /> : <AuditHisobot />}
    </div>
  );
}
