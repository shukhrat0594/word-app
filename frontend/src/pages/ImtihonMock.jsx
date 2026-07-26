import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";
import ImtihonOtish from "./ImtihonOtish";
import ImtihonYozGap from "./ImtihonYozGap";

const BOLIM_TARTIBI = ["listening", "reading", "writing", "speaking"];
const BOLIM_KALIT = {
  listening: "listening_bolimi",
  reading: "reading_bolimi",
  writing: "nav_writing",
  speaking: "nav_speaking",
};

/** To'liq mock imtihon — 4 ta bo'lim (Listening/Reading/Writing/Speaking)
 * ketma-ket, bitta yaxlit sessiyada o'tiladi, oxirida Overall Band
 * ko'rsatiladi (2026-07-25). Admin/owner ro'yxatdan mockni o'chira oladi
 * (4-papkali ZIP yuklashda avtomatik yaratiladi). */
export default function ImtihonMock() {
  const { t } = useI18n();
  const { profil } = useProfil();
  const adminMi = profil?.is_owner || profil?.role === "admin";
  const [royxat, setRoyxat] = useState(null);
  const [yechim, setYechim] = useState(null);
  const [xato, setXato] = useState("");

  function royxatniYukla() {
    api("/api/imtihon-mock/").then(setRoyxat).catch(() => {});
  }

  useEffect(() => {
    royxatniYukla();
  }, []);

  async function boshlash(mockId) {
    setXato("");
    try {
      const res = await api(`/api/imtihon-mock/${mockId}/boshlash/`, { method: "POST" });
      setYechim(res);
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    }
  }

  async function yechimniYangila() {
    const res = await api(`/api/imtihon-mock/yechim/${yechim.id}/`);
    setYechim(res);
  }

  async function ochirish(mockId) {
    if (!window.confirm(t("mashq_ochirish_tasdiq"))) return;
    await api(`/api/imtihon-mock/${mockId}/`, { method: "DELETE" }).catch(() => {});
    royxatniYukla();
  }

  if (yechim) {
    if (yechim.tugadimi) {
      return (
        <div className="karta">
          <h3>{yechim.mock.name}</h3>
          <div style={{ display: "grid", gap: 8, maxWidth: 320, marginTop: 10 }}>
            <div>{t("listening_bolimi")}: <strong>{yechim.listening_band ?? "—"}</strong></div>
            <div>{t("reading_bolimi")}: <strong>{yechim.reading_band ?? "—"}</strong></div>
            <div>{t("nav_writing")}: <strong>{yechim.writing_band ?? "—"}</strong></div>
            <div>{t("nav_speaking")}: <strong>{yechim.speaking_band ?? "—"}</strong></div>
          </div>
          <div className="umumiy-band" style={{ marginTop: 16 }}>
            <span className="u-ball">{yechim.overall_band ?? "—"}</span>
            <div style={{ fontWeight: 700 }}>Overall Band</div>
          </div>
          <button className="tugma ikkinchi" style={{ marginTop: 16 }} onClick={() => setYechim(null)}>
            {t("ortga")}
          </button>
        </div>
      );
    }

    const joriyBolim = BOLIM_TARTIBI.find((b) => !yechim[`${b}_tugadimi`]);
    const testId = yechim.mock.bolim_testlari[joriyBolim];
    if (!testId) {
      // Mock'da shu bo'lim mavjud emas (o'chirilgan) — o'tkazib yuboramiz.
      const keyingi = { ...yechim, [`${joriyBolim}_tugadimi`]: true };
      setYechim(keyingi);
      return null;
    }

    const props = {
      bolim: joriyBolim,
      testId,
      mockYechimId: yechim.id,
      onYakunlandi: yechimniYangila,
    };

    return (
      <div>
        <div className="tab-guruh" style={{ marginBottom: 12 }}>
          {BOLIM_TARTIBI.map((b) => (
            <button key={b} className={b === joriyBolim ? "aktiv" : ""} disabled>
              {t(BOLIM_KALIT[b])}
              {yechim[`${b}_tugadimi`] && " ✓"}
            </button>
          ))}
        </div>
        {joriyBolim === "writing" || joriyBolim === "speaking" ? (
          <ImtihonYozGap {...props} />
        ) : (
          <ImtihonOtish {...props} />
        )}
      </div>
    );
  }

  return (
    <div className="karta">
      {royxat === null && <div className="yuklanmoqda">{t("yuklanmoqda")}</div>}
      {royxat && royxat.length === 0 && <span className="izoh">{t("imtihon_royxati_boshi")}</span>}
      {royxat && royxat.map((m) => (
        <div key={m.id} className="mashq-royxat-el" style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ flex: 1, cursor: "pointer" }} onClick={() => boshlash(m.id)}>
            {m.name}
          </span>
          {adminMi && (
            <button
              className="tugma ikkinchi"
              style={{ color: "#d33" }}
              onClick={(e) => {
                e.stopPropagation();
                ochirish(m.id);
              }}
            >
              {t("ochirish")}
            </button>
          )}
        </div>
      ))}
      {xato && <div className="xato-xabar" style={{ marginTop: 10 }}>{xato}</div>}
    </div>
  );
}
