import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";

const BOSH_ADMIN_FORMA = { username: "", parol: "", ism: "" };

export default function Markazlar() {
  const { t } = useI18n();
  const [markazlar, setMarkazlar] = useState(null);
  const [adminForma, setAdminForma] = useState({});
  const [xabar, setXabar] = useState({});

  function yukla() {
    api("/api/markazlar/").then(setMarkazlar).catch(() => {});
  }

  useEffect(() => {
    yukla();
  }, []);

  function adminMaydonYangila(markazId, maydon, qiymat) {
    setAdminForma((f) => ({
      ...f,
      [markazId]: { ...(f[markazId] || BOSH_ADMIN_FORMA), [maydon]: qiymat },
    }));
  }

  async function adminTayinla(markazId) {
    const f = adminForma[markazId] || BOSH_ADMIN_FORMA;
    if (!f.username?.trim() || !f.parol?.trim()) {
      setXabar((x) => ({ ...x, [markazId]: t("xato_yuz_berdi") }));
      return;
    }
    try {
      await api(`/api/markazlar/${markazId}/admin-tayinlash/`, {
        method: "POST",
        body: f,
      });
      setXabar((x) => ({ ...x, [markazId]: t("tayinlandi") }));
      setAdminForma((old) => ({ ...old, [markazId]: BOSH_ADMIN_FORMA }));
      yukla();
    } catch (e) {
      setXabar((x) => ({ ...x, [markazId]: e.data?.detail || t("xato_yuz_berdi") }));
    }
  }

  if (!markazlar) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <div style={{ display: "grid", gap: 12 }}>
      {markazlar.length === 0 && <span className="izoh">{t("markaz_yoq")}</span>}
      {markazlar.map((m) => (
        <div className="karta" key={m.id}>
          <h3 style={{ marginBottom: 4 }}>{m.name}</h3>
          <p className="izoh" style={{ marginTop: 0 }}>
            {m.ai_provider} · {m.admin_soni} {t("adminlar")}
          </p>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <input
              style={{ maxWidth: 160 }}
              placeholder={t("ism")}
              value={(adminForma[m.id] || BOSH_ADMIN_FORMA).ism}
              onChange={(e) => adminMaydonYangila(m.id, "ism", e.target.value)}
            />
            <input
              style={{ maxWidth: 160 }}
              placeholder={t("login")}
              value={(adminForma[m.id] || BOSH_ADMIN_FORMA).username}
              onChange={(e) => adminMaydonYangila(m.id, "username", e.target.value)}
            />
            <input
              style={{ maxWidth: 160 }}
              type="password"
              placeholder={t("parol")}
              value={(adminForma[m.id] || BOSH_ADMIN_FORMA).parol}
              onChange={(e) => adminMaydonYangila(m.id, "parol", e.target.value)}
            />
            <button className="tugma ikkinchi" onClick={() => adminTayinla(m.id)}>
              {t("tayinlash")}
            </button>
            {xabar[m.id] && <span className="izoh">{xabar[m.id]}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}
