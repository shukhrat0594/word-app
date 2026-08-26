import { useEffect, useState } from "react";
import { api } from "../api";
import XatolikHolati from "../components/XatolikHolati";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";
import Davomat from "./Davomat";
import { ProfilRasmi } from "./Foydalanuvchilar";

const BOSH_FORMA = { id: null, name: "", faol: true, oqituvchi_id: "", talaba_idlar: [], fan_id: "", daraja_id: "" };

/** Admin/owner — to'liq boshqaruv (yaratish/tahrirlash). O'qituvchi — faqat
 * o'z guruhlarini o'qish uchun ko'radi, tahrirlay olmaydi (backend ham shu
 * cheklovni qo'llaydi — bu faqat mos UI). */
export default function Guruhlar() {
  const { t } = useI18n();
  const { profil } = useProfil();
  const oqituvchiMi = profil?.role === "teacher";
  const [guruhlar, setGuruhlar] = useState([]);
  const [azolar, setAzolar] = useState(null);
  // Fan/daraja (2026-08-02) — Kurslar bo'limidagi daraxtdan olinadi,
  // qattiq ro'yxat emas (yangi fan/daraja qo'shilsa avtomatik chiqadi).
  const [fanlar, setFanlar] = useState([]);
  const [tanlangan, setTanlangan] = useState(null);
  const [forma, setForma] = useState(null);
  const [xato, setXato] = useState("");
  const [band, setBand] = useState(false);
  // Har talabaning "boshlanish uniti" (2026-08-02) — guruh darajasi
  // ichida qaysi Unit'dan boshlaydi. Faqat MAVJUD a'zolar uchun (yangi
  // qo'shilganlar saqlashda avtomatik Unit 1 oladi, keyin shu yerdan
  // o'zgartiriladi).
  const [boshlanishMap, setBoshlanishMap] = useState({});
  const [darajaUnitlari, setDarajaUnitlari] = useState([]);
  // Arxivlangan guruhlarni ko'rish (2026-08-02) — standart holatda faqat
  // faol guruhlar ko'rinadi.
  const [arxivKorish, setArxivKorish] = useState(false);
  // Ro'yxatni yuklashda tarmoq xatosi (2026-08-15) — form ichidagi
  // validatsiya xatolari uchun ishlatiladigan `xato` dan alohida,
  // sahifa darajasidagi "qayta urinish" holati uchun.
  const [yuklashXato, setYuklashXato] = useState(false);
  // 2026-08-25, foydalanuvchi talabi: talaba qo'shish endi "+" tugmasi
  // bosilganda ochiladigan BITTA qatorda — shu qatordagi ro'yxatdan talaba
  // tanlanadi (qidiruv ro'yxatni qisqartirish uchun), yonida daraja
  // Unit'ga ega bo'lsa (Ingliz tili darajalari) boshlanish Unit'ini
  // tanlash ham chiqadi, standart — Unit 1.
  const [azoQidiruv, setAzoQidiruv] = useState("");
  const [qoshishOchiq, setQoshishOchiq] = useState(false);
  const [yangiUnitId, setYangiUnitId] = useState("");
  // Guruh ochilganda (yoki yangi guruh boshlanganda) MAVJUD (serverda
  // haqiqatan saqlangan) a'zolar to'plami — yangi qo'shilgan (hali
  // saqlanmagan) a'zodan farqlash uchun: mavjudlarning Unit'i darhol
  // PATCH bilan o'zgaradi, yangilarniki esa saqlashda qo'shiladi (chunki
  // ularning `GuruhAzoligi` yozuvi saqlashdan oldin serverda yo'q).
  const [mavjudAzoIds, setMavjudAzoIds] = useState(new Set());
  // Guruhdan o'chirish uchun o'ziga xos tasdiqlash oynasi (2026-08-25,
  // foydalanuvchi talabi: brauzerning window.confirm() EMAS).
  const [ochirishSorash, setOchirishSorash] = useState(null);

  function guruhlarniYukla(arxiv = arxivKorish) {
    setYuklashXato(false);
    api(`/api/guruhlar/${arxiv ? "?arxiv=1" : ""}`).then(setGuruhlar).catch(() => setYuklashXato(true));
  }

  useEffect(() => {
    guruhlarniYukla(arxivKorish);
  }, [arxivKorish]);

  useEffect(() => {
    // Owner markazga biriktirilmagan bo'lishi mumkin — bu holda 400 keladi,
    // sahifa "yuklanmoqda"da abadiy qolmasligi uchun bo'sh ro'yxat bilan davom etamiz.
    // O'qituvchi uchun bu endpoint 403 qaytaradi (faqat admin) — shu sababdan
    // ham bo'sh qiymat bilan tinch davom etiladi (tahrirlash formasi bo'lmagani
    // uchun kerak ham emas).
    api("/api/markaz-azolari/")
      .then(setAzolar)
      .catch(() => setAzolar({ oqituvchilar: [], talabalar: [] }));
    api("/api/guruh-fanlari/").then(setFanlar).catch(() => setFanlar([]));
  }, []);

  async function guruhniOch(id) {
    setXato("");
    try {
      const g = await api(`/api/guruhlar/${id}/`);
      setTanlangan(g);
      setDarajaUnitlari(g.daraja_unitlari || []);
      setBoshlanishMap(
        Object.fromEntries(g.talabalar.map((t2) => [t2.id, t2.boshlanish_unit_id || ""]))
      );
      setMavjudAzoIds(new Set(g.talabalar.map((t2) => t2.id)));
      if (!oqituvchiMi) {
        setForma({
          id: g.id,
          name: g.name,
          faol: g.faol,
          oqituvchi_id: g.oqituvchi?.id || "",
          talaba_idlar: g.talabalar.map((t2) => t2.id),
          fan_id: g.fan?.id || "",
          daraja_id: g.daraja?.id || "",
        });
      }
    } catch {
      setXato(t("xato_yuz_berdi"));
    }
  }

  // Daraja tanlanganda/o'zgarganda shu darajaning Unit'lari so'raladi —
  // "boshlanish Unit'i" tanlovi uchun kerak (2026-08-25). Yangi guruh
  // uchun ham, mavjud guruhni tahrirlashda daraja o'zgartirilganda ham
  // ishlaydi (`guruhniOch` allaqachon o'z Unit'larini bergan bo'lsa ham,
  // bu yerda qayta so'ralishi zararsiz — natija bir xil).
  useEffect(() => {
    if (!forma) return;
    if (!forma.daraja_id) {
      setDarajaUnitlari([]);
      return;
    }
    api(`/api/kurslar/${forma.daraja_id}/unitlari/`)
      .then(setDarajaUnitlari)
      .catch(() => setDarajaUnitlari([]));
  }, [forma?.daraja_id]);

  function yopish() {
    setTanlangan(null);
    setForma(null);
    setBoshlanishMap({});
    setDarajaUnitlari([]);
    setAzoQidiruv("");
    setQoshishOchiq(false);
    setYangiUnitId("");
    setMavjudAzoIds(new Set());
  }

  /** Bitta a'zoning "boshlanish Unit'i"ni o'zgartirish. MAVJUD (serverda
   * saqlangan) a'zo bo'lsa — darhol PATCH bilan saqlanadi. Yangi (hali
   * saqlanmagan, `talabaBelgila` orqali lokal qo'shilgan) a'zo bo'lsa —
   * uning `GuruhAzoligi`si serverda hali yo'q (guruh o'zi ham hali
   * saqlanmagan bo'lishi mumkin), shuning uchun faqat lokal saqlanadi —
   * asosiy `saqla()` guruhni yaratgach/yangilagach shu qiymatlarni ham
   * PATCH qiladi. */
  async function boshlanishUnitiniOzgartir(talabaId, unitId) {
    setBoshlanishMap((m) => ({ ...m, [talabaId]: unitId }));
    if (!forma.id || !mavjudAzoIds.has(talabaId)) return;
    try {
      await api(`/api/guruhlar/${forma.id}/azolik/${talabaId}/`, {
        method: "PATCH",
        body: { boshlanish_unit_id: unitId || null },
      });
    } catch {
      setXato(t("xato_yuz_berdi"));
    }
  }

  async function arxivHolatiniOzgartir(yangiFaol) {
    setXato("");
    setBand(true);
    try {
      await api(`/api/guruhlar/${forma.id}/`, {
        method: "PATCH",
        body: { faol: yangiFaol },
      });
      yopish();
      guruhlarniYukla();
    } catch {
      setXato(t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  async function butunlayOchir() {
    if (!window.confirm(t("guruh_ochir_tasdiq"))) return;
    setXato("");
    setBand(true);
    try {
      await api(`/api/guruhlar/${forma.id}/`, { method: "DELETE" });
      yopish();
      guruhlarniYukla();
    } catch {
      setXato(t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  function talabaBelgila(id) {
    setForma((f) => ({
      ...f,
      talaba_idlar: f.talaba_idlar.includes(id)
        ? f.talaba_idlar.filter((x) => x !== id)
        : [...f.talaba_idlar, id],
    }));
  }

  /** Qidiruv qatoridan tanlab, YANGI a'zo qo'shish — tanlangan Unit
   * (agar bo'lsa) ham darhol saqlanadi (`boshlanishMap`ga), asosiy
   * saqlashda serverga yuboriladi (`saqla()`). Qidiruv qatori ochiq
   * qoladi — bir nechta talabani ketma-ket qo'shish uchun. */
  function yangiTalabaQosh(id) {
    talabaBelgila(id);
    if (yangiUnitId) setBoshlanishMap((m) => ({ ...m, [id]: yangiUnitId }));
    setAzoQidiruv("");
  }

  /** Guruhdan o'chirish — o'ziga xos tasdiqlash oynasi orqali (2026-08-25,
   * foydalanuvchi talabi: brauzerning window.confirm() emas). Faqat
   * lokal forma holatidan olib tashlaydi — haqiqiy o'chirish "Saqlash"
   * bosilganda backenddagi diff orqali sodir bo'ladi. */
  function ochirishTasdiqlandi() {
    if (!ochirishSorash) return;
    talabaBelgila(ochirishSorash.id);
    setBoshlanishMap((m) => {
      const nusxa = { ...m };
      delete nusxa[ochirishSorash.id];
      return nusxa;
    });
    setOchirishSorash(null);
  }

  async function saqla() {
    setXato("");
    if (!forma.name.trim()) {
      setXato(t("guruh_nomi"));
      return;
    }
    setBand(true);
    const body = {
      name: forma.name,
      oqituvchi_id: forma.oqituvchi_id || null,
      talaba_idlar: forma.talaba_idlar,
      fan_id: forma.fan_id || null,
      daraja_id: forma.daraja_id || null,
    };
    try {
      let guruhId = forma.id;
      if (forma.id) {
        await api(`/api/guruhlar/${forma.id}/`, { method: "PATCH", body });
      } else {
        const yaratilgan = await api("/api/guruhlar/", { method: "POST", body });
        guruhId = yaratilgan.id;
      }
      // Yangi (hali serverda mavjud bo'lmagan) a'zolar uchun standart
      // bo'lmagan boshlanish Unit'i tanlangan bo'lsa — endi guruh (va
      // a'zolik) real mavjud, shularni alohida PATCH qilamiz.
      const yangiOverride = forma.talaba_idlar.filter(
        (id) => !mavjudAzoIds.has(id) && boshlanishMap[id]
      );
      for (const id of yangiOverride) {
        await api(`/api/guruhlar/${guruhId}/azolik/${id}/`, {
          method: "PATCH",
          body: { boshlanish_unit_id: boshlanishMap[id] },
        }).catch(() => {});
      }
      yopish();
      guruhlarniYukla();
    } catch {
      setXato(t("xato_yuz_berdi"));
    } finally {
      setBand(false);
    }
  }

  if (yuklashXato) return <XatolikHolati qaytaUrin={() => guruhlarniYukla(arxivKorish)} />;

  if (!azolar) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <>
      {!tanlangan && !oqituvchiMi && (
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button className="tugma" onClick={() => setForma(BOSH_FORMA)}>
            {t("yangi_guruh")}
          </button>
        </div>
      )}

      {forma && !oqituvchiMi && (
        <div className="karta">
          <h3>{forma.id ? forma.name : t("yangi_guruh")}</h3>
          <div style={{ display: "grid", gap: 14 }}>
            <input
              placeholder={t("guruh_nomi")}
              value={forma.name}
              onChange={(e) => setForma({ ...forma, name: e.target.value })}
            />
            <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 160 }}>
                <div className="izoh" style={{ marginBottom: 6 }}>{t("guruh_fani")}</div>
                <select
                  value={forma.fan_id}
                  onChange={(e) => setForma({ ...forma, fan_id: e.target.value, daraja_id: "" })}
                >
                  <option value="">— {t("tanlanmagan")} —</option>
                  {fanlar.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.nomi}{f.tez_kunda ? ` (${t("tez_orada")})` : ""}
                    </option>
                  ))}
                </select>
              </div>
              <div style={{ flex: 1, minWidth: 160 }}>
                <div className="izoh" style={{ marginBottom: 6 }}>{t("guruh_darajasi")}</div>
                <select
                  value={forma.daraja_id}
                  onChange={(e) => setForma({ ...forma, daraja_id: e.target.value })}
                  disabled={!forma.fan_id}
                >
                  <option value="">— {t("tanlanmagan")} —</option>
                  {(fanlar.find((f) => String(f.id) === String(forma.fan_id))?.darajalar || []).map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.nomi}{d.tez_kunda ? ` (${t("tez_orada")})` : ""}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <div className="izoh" style={{ marginBottom: 6 }}>{t("oqituvchi")}</div>
              <select
                value={forma.oqituvchi_id}
                onChange={(e) => setForma({ ...forma, oqituvchi_id: e.target.value })}
              >
                <option value="">— {t("tanlanmagan")} —</option>
                {azolar.oqituvchilar.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.ism}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <h4 style={{ margin: 0 }}>
                  {t("talabalar")} ({forma.talaba_idlar.length})
                </h4>
                <button
                  type="button"
                  className="tugma ikkinchi kichik"
                  onClick={() => setQoshishOchiq((v) => !v)}
                >
                  + {t("talaba_qosh")}
                </button>
              </div>
              <div className="azo-royxat">
                {azolar.talabalar.filter((tl) => forma.talaba_idlar.includes(tl.id)).length === 0 && (
                  <span className="izoh">{t("talaba_yoq")}</span>
                )}
                {azolar.talabalar
                  .filter((tl) => forma.talaba_idlar.includes(tl.id))
                  .map((tl) => (
                    <div className="azo-qator" key={tl.id} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{ display: "flex", alignItems: "center", gap: 8, flex: 1 }}>
                        <ProfilRasmi user={tl} t={t} />
                        {tl.ism}
                      </span>
                      {darajaUnitlari.length > 0 && (
                        <select
                          value={boshlanishMap[tl.id] || ""}
                          onChange={(e) => boshlanishUnitiniOzgartir(tl.id, e.target.value)}
                          title={t("boshlanish_uniti")}
                        >
                          <option value="">— {t("boshlanish_uniti")}: Unit 1 —</option>
                          {darajaUnitlari.map((u) => (
                            <option key={u.id} value={u.id}>
                              {u.nomi}
                            </option>
                          ))}
                        </select>
                      )}
                      <button
                        type="button"
                        className="tugma xavfli kichik"
                        onClick={() => setOchirishSorash(tl)}
                        title={t("ochirish")}
                      >
                        {t("ochirish")}
                      </button>
                    </div>
                  ))}
              </div>

              {/* 2026-08-25, foydalanuvchi talabi: "+" bosilganda bitta
                  qidiruv+ro'yxat qatori ochiladi, shundan talaba tanlanadi;
                  daraja Unit'larga ega bo'lsa (Ingliz tili darajalari)
                  yonida boshlanish Unit'i ham tanlanadi (standart — Unit 1),
                  qator ochiq qoladi — ketma-ket bir nechtasini qo'shish uchun. */}
              {qoshishOchiq && (
                <div style={{ marginTop: 10, display: "grid", gap: 6 }}>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <input
                      placeholder={t("talaba_qidir")}
                      value={azoQidiruv}
                      onChange={(e) => setAzoQidiruv(e.target.value)}
                      style={{ flex: 1, minWidth: 160 }}
                    />
                    {darajaUnitlari.length > 0 && (
                      <select
                        value={yangiUnitId}
                        onChange={(e) => setYangiUnitId(e.target.value)}
                        title={t("boshlanish_uniti")}
                      >
                        <option value="">— {t("boshlanish_uniti_standart")} —</option>
                        {darajaUnitlari.map((u) => (
                          <option key={u.id} value={u.id}>
                            {u.nomi}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                  <div className="azo-royxat">
                    {azolar.talabalar
                      .filter((tl) => !forma.talaba_idlar.includes(tl.id))
                      .filter((tl) => tl.ism.toLowerCase().includes(azoQidiruv.trim().toLowerCase()))
                      .slice(0, 20)
                      .map((tl) => (
                        <div
                          className="azo-qator"
                          key={tl.id}
                          style={{ cursor: "pointer" }}
                          onClick={() => yangiTalabaQosh(tl.id)}
                        >
                          <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <ProfilRasmi user={tl} t={t} />
                            {tl.ism}
                          </span>
                        </div>
                      ))}
                    {azolar.talabalar
                      .filter((tl) => !forma.talaba_idlar.includes(tl.id))
                      .filter((tl) => tl.ism.toLowerCase().includes(azoQidiruv.trim().toLowerCase())).length === 0 && (
                      <span className="izoh">{t("hech_narsa_topilmadi")}</span>
                    )}
                  </div>
                </div>
              )}
            </div>
            {xato && <div className="xato-xabar">{xato}</div>}
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button className="tugma" onClick={saqla} disabled={band}>
                {forma.id ? t("saqlash") : t("yaratish")}
              </button>
              <button className="tugma ikkinchi" onClick={yopish}>
                {t("ortga")}
              </button>
              {forma.id && (
                <>
                  <button
                    className="tugma ikkinchi"
                    onClick={() => arxivHolatiniOzgartir(!forma.faol)}
                    disabled={band}
                  >
                    {forma.faol ? t("arxivlash") : t("faollashtirish")}
                  </button>
                  <button
                    className="tugma xavfli"
                    onClick={butunlayOchir}
                    disabled={band}
                    style={{ marginLeft: "auto" }}
                  >
                    {t("guruh_ochir")}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {tanlangan && oqituvchiMi && (
        <div className="karta">
          <h3>{tanlangan.name}</h3>
          <div className="izoh" style={{ marginBottom: 10 }}>
            {t("oqituvchi")}: {tanlangan.oqituvchi ? tanlangan.oqituvchi.ism : `— ${t("tanlanmagan")} —`}
          </div>
          <div className="izoh" style={{ marginBottom: 6 }}>{t("talabalar")}</div>
          <div style={{ display: "grid", gap: 4 }}>
            {tanlangan.talabalar.length === 0 && <span className="izoh">{t("talaba_yoq")}</span>}
            {tanlangan.talabalar.map((tl) => (
              <div key={tl.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <ProfilRasmi user={tl} t={t} />
                {tl.ism}
              </div>
            ))}
          </div>
          <button className="tugma ikkinchi" onClick={yopish} style={{ marginTop: 14 }}>
            {t("ortga")}
          </button>
        </div>
      )}

      {/* 2026-08-15: Davomat endi ALOHIDA panel emas — guruh ichida
          ochiladi (admin ham, o'qituvchi ham). Guruh allaqachon
          tanlangani uchun `guruhId` prop bilan beriladi — ichida guruh
          tanlash ro'yxati chiqmaydi. */}
      {tanlangan && (
        <div className="karta" style={{ marginTop: 12 }}>
          <h3>{t("nav_davomat")}</h3>
          <Davomat guruhId={tanlangan.id} />
        </div>
      )}

      {!tanlangan && !oqituvchiMi && (
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
          <button className="tugma ikkinchi" onClick={() => setArxivKorish((v) => !v)}>
            {arxivKorish ? t("faol_guruhlar") : t("arxivlangan_guruhlar")}
          </button>
        </div>
      )}

      {!tanlangan && (
        <div style={{ display: "grid", gap: 12, marginTop: 12 }}>
          {guruhlar.length === 0 && <span className="izoh">{t("guruh_yoq")}</span>}
          {guruhlar.map((g) => (
            <div className="guruh-karta" key={g.id} onClick={() => guruhniOch(g.id)}>
              <div className="g-mal">
                <div className="g-nomi">
                  {g.name}
                  {g.daraja && <span className="izoh"> · {g.fan.nomi} — {g.daraja.nomi}</span>}
                </div>
                <div className="g-info">
                  {g.oqituvchi ? g.oqituvchi.ism : `— ${t("tanlanmagan")} —`} ·{" "}
                  {g.talaba_soni} {t("talabalar").toLowerCase()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 2026-08-25, foydalanuvchi talabi: guruhdan o'chirish uchun
          o'ziga xos tasdiqlash oynasi (window.confirm() EMAS). */}
      {ochirishSorash && (
        <div className="blok-yuklash-qoplama" onClick={() => setOchirishSorash(null)}>
          <div className="blok-tasdiq-karta" onClick={(e) => e.stopPropagation()}>
            <p style={{ marginTop: 0 }}>
              {t("guruhdan_ochirish_tasdiq").replace("{nom}", ochirishSorash.ism)}
            </p>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button className="tugma ikkinchi" onClick={() => setOchirishSorash(null)}>
                {t("yoq")}
              </button>
              <button className="tugma xavfli" onClick={ochirishTasdiqlandi}>
                {t("ha")}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
