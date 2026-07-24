import { useEffect, useState } from "react";
import { api, apiBlobUrl, apiForm } from "../api";
import { useI18n } from "../i18n";
import { useProfil } from "../profilContext";

/** Talaba uchun — bitta mashqqa javob yozish va natija ko'rish. */
function TalabaMashqi({ mashq }) {
  const { t } = useI18n();
  const [javoblar, setJavoblar] = useState(mashq.savollar.map(() => ""));
  const [natija, setNatija] = useState(null);
  const [rasmUrl, setRasmUrl] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [xato, setXato] = useState("");

  useEffect(() => {
    if (mashq.rasm_url) {
      apiBlobUrl(mashq.rasm_url).then(setRasmUrl).catch(() => {});
    }
  }, [mashq.rasm_url]);

  useEffect(() => {
    if (mashq.audio_url) {
      apiBlobUrl(mashq.audio_url).then(setAudioUrl).catch(() => {});
    }
  }, [mashq.audio_url]);

  async function tekshir() {
    setXato("");
    setYuklanmoqda(true);
    try {
      const res = await api(`/api/kurslar/mashq/${mashq.id}/yechish/`, {
        method: "POST",
        body: { javoblar },
      });
      setNatija(res);
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  return (
    <div style={{ border: "1px solid var(--chiziq)", borderRadius: 8, padding: 10, marginBottom: 8 }}>
      {mashq.matn && <div style={{ marginBottom: 8 }}>{mashq.matn}</div>}
      {rasmUrl && <img src={rasmUrl} alt="" style={{ maxWidth: "100%", marginBottom: 8 }} />}
      {audioUrl && <audio controls src={audioUrl} style={{ width: "100%", marginBottom: 8 }} />}
      {mashq.savollar.map((s, i) => (
        <div key={i} style={{ marginBottom: 6 }}>
          <div className="izoh">{s.savol}</div>
          {s.variantlar && s.variantlar.length > 0 ? (
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              {s.variantlar.map((v) => (
                <label key={v} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <input
                    type="radio"
                    name={`mashq-${mashq.id}-${i}`}
                    checked={javoblar[i] === v}
                    disabled={!!natija}
                    onChange={() => setJavoblar((j) => j.map((x, idx) => (idx === i ? v : x)))}
                  />
                  {v}
                </label>
              ))}
            </div>
          ) : (
            <input
              value={javoblar[i]}
              disabled={!!natija}
              onChange={(e) => setJavoblar((j) => j.map((x, idx) => (idx === i ? e.target.value : x)))}
              style={{ maxWidth: 260 }}
            />
          )}
          {natija && (
            <span style={{ marginLeft: 8 }}>{natija.natijalar[i] ? "✓" : "✗"}</span>
          )}
        </div>
      ))}
      {!natija ? (
        <button className="tugma ikkinchi" onClick={tekshir} disabled={yuklanmoqda}>
          {yuklanmoqda ? t("tekshirilmoqda") : t("tekshirish")}
        </button>
      ) : (
        <div className="izoh">
          {t("band_ball")}: {natija.ball}/{natija.jami}
        </div>
      )}
      {xato && <div className="xato-xabar">{xato}</div>}
    </div>
  );
}

/** Admin/owner uchun — bitta tugunning mashqlarini boshqarish (ro'yxat,
 * JSON orqali bir nechtasini qo'shish, o'chirish, rasm biriktirish). */
function AdminMashqBoshqaruv({ tugunId }) {
  const { t } = useI18n();
  const [royxat, setRoyxat] = useState(null);
  const [jsonMatn, setJsonMatn] = useState('[\n  {"matn": "", "savollar": [{"savol": "...", "togri": "..."}]}\n]');
  const [xato, setXato] = useState("");
  const [saqlanmoqda, setSaqlanmoqda] = useState(false);
  const [audioZipXato, setAudioZipXato] = useState("");
  const [audioZipYuklanmoqda, setAudioZipYuklanmoqda] = useState(false);

  function yukla() {
    api(`/api/kurslar/${tugunId}/mashq-boshqaruv/`).then(setRoyxat).catch(() => {});
  }

  useEffect(() => {
    yukla();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tugunId]);

  async function qoshish() {
    setXato("");
    let mashqlar;
    try {
      mashqlar = JSON.parse(jsonMatn);
    } catch {
      setXato(t("kurs_json_xato"));
      return;
    }
    setSaqlanmoqda(true);
    try {
      await api(`/api/kurslar/${tugunId}/mashq-boshqaruv/`, { method: "POST", body: { mashqlar } });
      yukla();
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setSaqlanmoqda(false);
    }
  }

  async function ochir(id) {
    if (!window.confirm(t("kurs_mashq_ochirish_tasdiq"))) return;
    await api(`/api/kurslar/mashq/${id}/`, { method: "DELETE" }).catch(() => {});
    yukla();
  }

  async function rasmYukla(id, e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    const fd = new FormData();
    fd.append("rasm", fayl);
    await apiForm(`/api/kurslar/mashq/${id}/rasm-boshqaruv/`, { method: "PATCH", formData: fd }).catch(() => {});
    yukla();
  }

  async function audioZipYukla(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setAudioZipXato("");
    setAudioZipYuklanmoqda(true);
    try {
      const fd = new FormData();
      fd.append("zip_fayl", fayl);
      await apiForm(`/api/kurslar/${tugunId}/audio-zip/`, { method: "POST", formData: fd });
      yukla();
    } catch (e2) {
      setAudioZipXato(e2.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setAudioZipYuklanmoqda(false);
    }
  }

  return (
    <div>
      {royxat && royxat.length > 0 && (
        <div style={{ display: "grid", gap: 6, marginBottom: 10 }}>
          {royxat.map((m) => (
            <div key={m.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="izoh">
                #{m.tartib} — {m.matn ? m.matn.slice(0, 40) : ""} ({m.savollar.length} {t("kurs_savol")})
                {m.rasm_url ? " 🖼️" : ""}
                {m.audio_url ? " 🔊" : ""}
              </span>
              <input type="file" accept="image/*" onChange={(e) => rasmYukla(m.id, e)} style={{ maxWidth: 140 }} />
              <button className="tugma ikkinchi" style={{ color: "#d33" }} onClick={() => ochir(m.id)}>
                {t("ochirish")}
              </button>
            </div>
          ))}
        </div>
      )}
      {royxat && royxat.length > 0 && (
        <div style={{ marginBottom: 10 }}>
          <label className="izoh" style={{ display: "block", marginBottom: 4 }}>
            {t("kurs_audio_zip_yuklash")}
          </label>
          <input type="file" accept=".zip" onChange={audioZipYukla} disabled={audioZipYuklanmoqda} />
          {audioZipXato && <span className="xato-xabar" style={{ marginLeft: 8 }}>{audioZipXato}</span>}
        </div>
      )}
      <textarea
        rows={6}
        value={jsonMatn}
        onChange={(e) => setJsonMatn(e.target.value)}
        style={{ width: "100%", fontFamily: "monospace", fontSize: 12 }}
      />
      <div style={{ marginTop: 6 }}>
        <button className="tugma ikkinchi" onClick={qoshish} disabled={saqlanmoqda}>
          {t("kurs_mashq_qoshish")}
        </button>
        {xato && <span className="xato-xabar" style={{ marginLeft: 8 }}>{xato}</span>}
      </div>
    </div>
  );
}

/** Mashqlar paneli — talaba uchun yechish, admin uchun boshqarish. */
function MashqPaneli({ tugunId, talabaMi }) {
  const { t } = useI18n();
  const [mashqlar, setMashqlar] = useState(null);
  const [xato, setXato] = useState("");

  useEffect(() => {
    if (!talabaMi) return;
    api(`/api/kurslar/${tugunId}/mashqlar/`)
      .then(setMashqlar)
      .catch((e) => setXato(e.data?.detail || t("xato_yuz_berdi")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tugunId, talabaMi]);

  if (!talabaMi) return <AdminMashqBoshqaruv tugunId={tugunId} />;

  if (xato) return <div className="xato-xabar">{xato}</div>;
  if (!mashqlar) return <div className="izoh">{t("yuklanmoqda")}</div>;
  if (mashqlar.length === 0) return <div className="izoh">{t("kurs_mashq_yoq")}</div>;

  return (
    <div>
      {mashqlar.map((m) => (
        <TalabaMashqi key={m.id} mashq={m} />
      ))}
    </div>
  );
}

/** Bitta tugun — akkordeon (agar children bo'lsa) yoki oxirgi qatlam
 * (fayl + mashqlar + tugallandimi belgisi + admin uchun boshqaruv). */
function Tugun({ tugun, chuqurlik, adminMi, talabaMi, royxatniYangila }) {
  const { t } = useI18n();
  const [ochiq, setOchiq] = useState(chuqurlik === 0);
  const [mashqOchiq, setMashqOchiq] = useState(false);
  const [faylXato, setFaylXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [tugallandimi, setTugallandimi] = useState(tugun.tugallandimi);

  const otstup = 14 + chuqurlik * 20;

  if (tugun.tez_kunda) {
    return (
      <div
        className="kurs-qator"
        style={{ paddingLeft: otstup, display: "flex", alignItems: "center", gap: 8, opacity: 0.55 }}
      >
        <span>{tugun.ikonka}</span>
        <span>{tugun.nomi}</span>
        <span className="izoh">— {t("tez_orada")}</span>
      </div>
    );
  }

  if (tugun.qulflangan) {
    return (
      <div
        className="kurs-qator"
        style={{ paddingLeft: otstup, display: "flex", alignItems: "center", gap: 8, opacity: 0.5 }}
      >
        <span>🔒</span>
        <span>{tugun.nomi}</span>
        <span className="izoh">— {t("kurs_qulflangan")}</span>
      </div>
    );
  }

  if (tugun.oxirgi_qatlammi) {
    async function faylniOch() {
      if (!tugun.fayl_url) return;
      const url = await apiBlobUrl(tugun.fayl_url).catch(() => null);
      if (url) window.open(url, "_blank");
    }

    async function faylYukla(e) {
      const fayl = e.target.files[0];
      e.target.value = "";
      if (!fayl) return;
      setFaylXato("");
      setYuklanmoqda(true);
      try {
        const fd = new FormData();
        fd.append("fayl", fayl);
        await apiForm(`/api/kurslar/${tugun.id}/fayl-boshqaruv/`, { method: "PATCH", formData: fd });
        royxatniYangila();
      } catch (e2) {
        setFaylXato(e2.data?.detail || t("xato_yuz_berdi"));
      } finally {
        setYuklanmoqda(false);
      }
    }

    async function tugallandiBelgila() {
      const res = await api(`/api/kurslar/${tugun.id}/tugallandi/`, { method: "POST" }).catch(() => null);
      if (res) setTugallandimi(res.tugallandimi);
    }

    return (
      <div>
        <div
          className="kurs-qator kurs-qator-oxirgi"
          style={{ paddingLeft: otstup, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}
        >
          <span>{tugun.ikonka}</span>
          <span>{tugun.nomi}</span>
          {tugun.fayl_url ? (
            <button className="tugma ikkinchi" onClick={faylniOch}>
              {t("kurs_faylni_ochish")}
            </button>
          ) : (
            <span className="izoh">{t("kurs_fayl_yoq")}</span>
          )}
          {talabaMi && tugun.fayl_url && (
            <button
              className="tugma ikkinchi"
              style={tugallandimi ? { background: "var(--komir)", color: "var(--sariq)" } : undefined}
              onClick={tugallandiBelgila}
            >
              {tugallandimi ? `✓ ${t("kurs_tugallandi")}` : t("kurs_tugallandim")}
            </button>
          )}
          {adminMi && (
            <>
              <input type="file" onChange={faylYukla} disabled={yuklanmoqda} style={{ maxWidth: 200 }} />
              {faylXato && <span className="xato-xabar">{faylXato}</span>}
            </>
          )}
          {(adminMi || tugun.mashqlar_soni) && (
            <button className="tugma ikkinchi" onClick={() => setMashqOchiq((v) => !v)}>
              {mashqOchiq
                ? t("yopish")
                : `${t("kurs_mashqlar")}${tugun.mashqlar_soni ? ` (${tugun.mashqlar_soni})` : ""}`}
            </button>
          )}
        </div>
        {mashqOchiq && (
          <div style={{ paddingLeft: otstup, marginTop: 6 }}>
            <MashqPaneli tugunId={tugun.id} adminMi={adminMi} talabaMi={talabaMi} />
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <div
        className="kurs-qator kurs-qator-branch"
        style={{ paddingLeft: otstup, display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}
        onClick={() => setOchiq((v) => !v)}
      >
        <span>{ochiq ? "▾" : "▸"}</span>
        <span>{tugun.ikonka}</span>
        <span style={{ fontWeight: chuqurlik < 2 ? 700 : 500 }}>{tugun.nomi}</span>
      </div>
      {ochiq && (
        <div>
          {tugun.children.map((b) => (
            <Tugun
              key={b.id}
              tugun={b}
              chuqurlik={chuqurlik + 1}
              adminMi={adminMi}
              talabaMi={talabaMi}
              royxatniYangila={royxatniYangila}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/** "Kurslar" bo'limi — ko'p bosqichli iyerarxik menyu (Kurs > Daraja >
 * Unit/Bo'lim > Mashq turi). Talaba/admin/owner/o'qituvchi ko'radi, "oddiy
 * foydalanuvchi" ko'rmaydi. Tuzilma qattiq (kurslar_urugla buyrug'i orqali
 * bir martalik yaratiladi) — admin oxirgi qatlamga fayl/mashq biriktiradi.
 * Unit'lar (masalan darslik bo'limlari) ketma-ket ochiladi — talaba uchun
 * keyingisi oldingisining BARCHA bo'limlaridagi mashqlardan jami 60%+
 * ball olmaguncha qulflangan (🔒) bo'lib ko'rsatiladi. */
export default function Kurslar() {
  const { t } = useI18n();
  const { profil } = useProfil();
  const adminMi = profil?.is_owner || profil?.role === "admin";
  const talabaMi = profil?.role === "student";
  const [daraxt, setDaraxt] = useState(null);

  function yukla() {
    api("/api/kurslar/daraxt/").then(setDaraxt).catch(() => {});
  }

  useEffect(() => {
    yukla();
  }, []);

  if (!daraxt) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  return (
    <div className="karta">
      <h3>{t("nav_kurslar")}</h3>
      {daraxt.children.map((tugun) => (
        <Tugun
          key={tugun.id}
          tugun={tugun}
          chuqurlik={0}
          adminMi={adminMi}
          talabaMi={talabaMi}
          royxatniYangila={yukla}
        />
      ))}
    </div>
  );
}
