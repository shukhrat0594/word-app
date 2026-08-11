import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";
import { useTestRejimi } from "../testRejimiContext";
import ImtihonOtish from "./ImtihonOtish";
import ImtihonYozGap from "./ImtihonYozGap";

// 2026-08-11, foydalanuvchi talabi: qo'lda mock yaratish (mavjud
// testlardan bo'lim tanlab) VAQTINCHA yashirildi — "papka ichida
// papka" (2-darajali papka, har bo'limdan bittadan) tizimi tayyor
// bo'lgach, mock BUTUNLAY shu papkalar orqali yig'iladi va bu forma
// KERAKMAS bo'lib qoladi. Kod/backend endpoint ATAYLAB o'chirilmadi —
// reja tasdiqlanmagan, tuzatish oson bo'lsin. O'chirish REJA.md'da
// "Navbatdagi ishlar"ga yozib qo'yilgan.
const QOLDA_MOCK_YARATISH_OCHIQ = false;

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
function AdminMockYaratish({ manba, royxatniYukla }) {
  const { t } = useI18n();
  const [nomi, setNomi] = useState("");
  const [tanlovlar, setTanlovlar] = useState({});
  const [testlar, setTestlar] = useState({});
  const [xato, setXato] = useState("");
  const [saqlanmoqda, setSaqlanmoqda] = useState(false);

  useEffect(() => {
    BOLIM_TARTIBI.forEach((b) => {
      api(`/api/imtihon/testlar/?bolim=${b}&manba=${manba}`).then((r) =>
        setTestlar((prev) => ({ ...prev, [b]: r }))
      );
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [manba]);

  async function yaratish() {
    setXato("");
    if (!nomi.trim()) {
      setXato(t("mock_nomi_kerak"));
      return;
    }
    setSaqlanmoqda(true);
    try {
      await api("/api/imtihon-mock/yaratish/", {
        method: "POST",
        body: { name: nomi, ...tanlovlar, manba },
      });
      setNomi("");
      setTanlovlar({});
      royxatniYukla();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setSaqlanmoqda(false);
    }
  }

  return (
    <div className="karta" style={{ marginBottom: 16 }}>
      <h3>{t("mock_yaratish")}</h3>
      <div style={{ display: "grid", gap: 10, maxWidth: 420 }}>
        <input
          placeholder={t("mock_nomi")}
          value={nomi}
          onChange={(e) => setNomi(e.target.value)}
        />
        {BOLIM_TARTIBI.map((b) => (
          <label key={b} style={{ display: "grid", gap: 4 }}>
            <span className="izoh">{t(BOLIM_KALIT[b])}</span>
            <select
              value={tanlovlar[b] || ""}
              onChange={(e) => setTanlovlar((p) => ({ ...p, [b]: e.target.value }))}
            >
              <option value="">—</option>
              {(testlar[b] || []).map((tst) => (
                <option key={tst.id} value={tst.id}>
                  {tst.name}
                </option>
              ))}
            </select>
          </label>
        ))}
        <button className="tugma" onClick={yaratish} disabled={saqlanmoqda}>
          {saqlanmoqda ? t("saqlanmoqda") : t("mock_yaratish")}
        </button>
        {xato && <div className="xato-xabar">{xato}</div>}
      </div>
    </div>
  );
}

export default function ImtihonMock({ manba = "admin" }) {
  const { t } = useI18n();
  const { profil } = useProfil();
  const adminMi = profil?.is_owner || profil?.role === "admin";
  // 2026-08-11, foydalanuvchi talabi: "mock qismida mavjud papkalar
  // hammasi ko'rinadi, talaba papkani tanlaydi, ichidan yana bitta
  // papkani tanlasa shuni mock sifatida ishlaydi". R/L/W/S bo'limlari
  // (`ImtihonOtish`/`ImtihonYozGap`) BUTUNLAY O'ZGARMAYDI — faqat shu
  // "Mock" tabi endi tekis ro'yxat o'rniga ikki bosqichli papka
  // ko'rinishida (1-daraja -> 2-daraja -> mock boshlanadi).
  const [royxat, setRoyxat] = useState(null); // {papkalar, papkasiz_moklar}
  // Faqat ID saqlanadi (obyektning o'zi emas) — shunda "Ochirish"dan
  // keyin `royxatniYukla()` yangi ma'lumot olib kelganda, tanlangan
  // papkaning ICHKI RO'YXATI ham YANGI holatdan olinadi (pastda
  // `.find()` bilan), eskirgan (stale) nusxa ko'rsatilmaydi.
  const [tanlanganPapkaId, setTanlanganPapkaId] = useState(null);
  const [yechim, setYechim] = useState(null);
  const [xato, setXato] = useState("");
  const { setTestFaol } = useTestRejimi();

  // 2026-07-30 talabi: mock imtihon boshidan oxirigacha (barcha 4 bo'lim
  // tugaguncha) navigatsiya bloklansin — bu yerda, bo'linm-darajasida
  // EMAS (bo'lim almashganda `ImtihonOtish`/`ImtihonYozGap` qayta
  // mount bo'ladi, ular ichida boshqarilsa qisqa "faolsiz" lahza
  // bo'lib, o'sha lahzada navigatsiya vaqtincha ochilib qolardi).
  useEffect(() => {
    setTestFaol(!!yechim && !yechim.tugadimi);
    return () => setTestFaol(false);
  }, [yechim, setTestFaol]);

  function royxatniYukla() {
    api(`/api/imtihon-mock/papkalar/?manba=${manba}`).then(setRoyxat).catch(() => {});
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

  const papkalar = royxat?.papkalar || [];
  const papkasizMoklar = royxat?.papkasiz_moklar || [];
  const tanlanganPapka = papkalar.find((p) => p.id === tanlanganPapkaId) || null;
  const bosh = royxat && !tanlanganPapka;
  const boshBosh = bosh && papkalar.length === 0 && papkasizMoklar.length === 0;

  function ochirishTugmasi(mockId) {
    if (!adminMi) return null;
    return (
      <button
        className="tugma ikkinchi"
        style={{ color: "#d33" }}
        onClick={(e) => {
          e.stopPropagation();
          ochirish(mockId);
        }}
      >
        {t("ochirish")}
      </button>
    );
  }

  return (
    <>
      {adminMi && QOLDA_MOCK_YARATISH_OCHIQ && (
        <AdminMockYaratish manba={manba} royxatniYukla={royxatniYukla} />
      )}
      <div className="karta">
      {royxat === null && <div className="yuklanmoqda">{t("yuklanmoqda")}</div>}
      {boshBosh && <span className="izoh">{t("imtihon_royxati_boshi")}</span>}

      {/* 2-BOSQICH: bitta 1-darajali papka tanlangan — ichidagi
          2-darajali (mock tayyor) papkalarni ko'rsatamiz. Bosilsa
          O'SHA papkaga bog'langan mock boshlanadi. */}
      {royxat && !bosh && (
        <>
          <button className="tugma ikkinchi kichik" style={{ marginBottom: 10 }} onClick={() => setTanlanganPapkaId(null)}>
            {t("ortga")}
          </button>
          <div className="izoh" style={{ marginBottom: 8 }}>📁 {tanlanganPapka.nomi}</div>
          {tanlanganPapka.ichki.map((ich) => (
            <div key={ich.id} className="mashq-royxat-el" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ flex: 1, cursor: "pointer" }} onClick={() => boshlash(ich.mock_id)}>
                📂 {ich.nomi}
              </span>
              {ochirishTugmasi(ich.mock_id)}
            </div>
          ))}
        </>
      )}

      {/* 1-BOSQICH (asosiy ko'rinish): mavjud 1-darajali papkalar +
          eski, papkasiz mocklar (orqaga moslik). */}
      {bosh && (
        <>
          {papkalar.map((p) => (
            <div
              key={p.id}
              className="mashq-royxat-el"
              style={{ cursor: "pointer" }}
              onClick={() => setTanlanganPapkaId(p.id)}
            >
              📁 {p.nomi} <span className="izoh">({p.ichki.length})</span>
            </div>
          ))}
          {papkasizMoklar.map((m) => (
            <div key={m.id} className="mashq-royxat-el" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ flex: 1, cursor: "pointer" }} onClick={() => boshlash(m.id)}>
                {m.name}
              </span>
              {ochirishTugmasi(m.id)}
            </div>
          ))}
        </>
      )}

      {xato && <div className="xato-xabar" style={{ marginTop: 10 }}>{xato}</div>}
      </div>
    </>
  );
}
