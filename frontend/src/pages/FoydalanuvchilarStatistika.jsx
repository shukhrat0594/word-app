import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import { useI18n } from "../i18n";

const ROL_RANGI = {
  owner: "#8b5cf6",
  admin: "#f59e0b",
  teacher: "#3b82f6",
  student: "#10b981",
  parent: "#ec4899",
  oddiy: "#94a3b8",
};

export default function FoydalanuvchilarStatistika() {
  const { t } = useI18n();
  const [malumot, setMalumot] = useState(null);
  const [xato, setXato] = useState("");
  const [kunlar, setKunlar] = useState(30);

  useEffect(() => {
    api(`/api/statistika/foydalanuvchilar/?kunlar=${kunlar}`)
      .then((r) => {
        setMalumot(r);
        setXato("");
      })
      .catch((e) => setXato(e.data?.detail || t("xato_yuz_berdi")));
  }, [kunlar, t]);

  if (xato) return <div className="xato-xabar">{xato}</div>;
  if (!malumot) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  const rollar = malumot.rollar_soni.map((r) => ({
    ...r,
    nomi: t(`rol_${r.rol}`) || r.rol,
  }));
  const rolKalitlari = [...new Set(malumot.kunlik_loginlar.flatMap((k) => Object.keys(k).filter((key) => key !== "sana")))];

  return (
    <div className="karta">
      <h3>{t("nav_foydalanuvchilar_statistika")}</h3>

      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 18 }}>
        <label>
          {t("stat_kunlar_soni")}:{" "}
          <select value={kunlar} onChange={(e) => setKunlar(Number(e.target.value))}>
            <option value={7}>7</option>
            <option value={30}>30</option>
            <option value={90}>90</option>
            <option value={365}>365</option>
          </select>
        </label>
        <span className="izoh">
          {t("stat_jami_login")}: {malumot.jami_login}
        </span>
      </div>

      <h4>{t("stat_rollar_taqsimoti")}</h4>
      {rollar.length === 0 ? (
        <div className="izoh">{t("hisobot_yoq")}</div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie data={rollar} dataKey="soni" nameKey="nomi" outerRadius={90} label>
              {rollar.map((r) => (
                <Cell key={r.rol} fill={ROL_RANGI[r.rol] || "#94a3b8"} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      )}

      <h4 style={{ marginTop: 24 }}>{t("stat_kunlik_loginlar")}</h4>
      {malumot.kunlik_loginlar.length === 0 ? (
        <div className="izoh">{t("stat_malumot_yoq")}</div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={malumot.kunlik_loginlar}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="sana" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Legend />
            {rolKalitlari.map((rol) => (
              <Line
                key={rol}
                type="monotone"
                dataKey={rol}
                name={t(`rol_${rol}`) || rol}
                stroke={ROL_RANGI[rol] || "#94a3b8"}
                strokeWidth={2}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}

      <h4 style={{ marginTop: 24 }}>{t("stat_soatlik_loginlar")}</h4>
      {malumot.jami_login === 0 ? (
        <div className="izoh">{t("stat_malumot_yoq")}</div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={malumot.soatlik_loginlar}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="soat" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="soni" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
