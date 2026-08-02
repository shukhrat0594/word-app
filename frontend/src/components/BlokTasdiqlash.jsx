import { useEffect, useRef, useState } from "react";
import { api, apiBlobUrl } from "../api";
import { useI18n } from "../i18n";

/** Bitta sahifaning surati ustida rasm-qutilarini (AI aniqlagan chegaralar)
 * sudrab ko'chirish / burchagidan o'lchamini o'zgartirish imkonini beradi
 * (2026-08-03) — AI koordinatasi ba'zan noto'g'ri bo'lgani uchun (yuzlar
 * kesilib qolishi, qo'shni suratga aralashib ketishi) admin shu yerda
 * tasdiqlashdan oldin to'g'irlaydi. */
function QutiTahrirlagich({ jarayonId, indeks, qutilar, onChange }) {
  const [rasmUrl, setRasmUrl] = useState(null);
  const konteynerRef = useRef(null);
  const surinishRef = useRef(null);

  useEffect(() => {
    let joriyUrl = null;
    let bekorQilindi = false;
    apiBlobUrl(`/api/kurslar/blok-jarayon/${jarayonId}/sahifa-rasm/${indeks}/`).then((u) => {
      if (bekorQilindi) {
        URL.revokeObjectURL(u);
        return;
      }
      joriyUrl = u;
      setRasmUrl(u);
    }).catch(() => {});
    return () => {
      bekorQilindi = true;
      if (joriyUrl) URL.revokeObjectURL(joriyUrl);
    };
  }, [jarayonId, indeks]);

  function davomEttirish(e) {
    const s = surinishRef.current;
    if (!s || !konteynerRef.current) return;
    const rect = konteynerRef.current.getBoundingClientRect();
    const dx = ((e.clientX - s.boshX) / rect.width) * 100;
    const dy = ((e.clientY - s.boshY) / rect.height) * 100;
    const q = { ...s.boshQuti };
    if (s.mod === "kochir") {
      q.x1 += dx; q.x2 += dx; q.y1 += dy; q.y2 += dy;
    } else if (s.mod === "yuqori-chap") {
      q.x1 += dx; q.y1 += dy;
    } else {
      q.x2 += dx; q.y2 += dy;
    }
    for (const k of ["x1", "y1", "x2", "y2"]) q[k] = Math.max(0, Math.min(100, q[k]));
    const yangi = [...qutilar];
    yangi[s.i] = q;
    onChange(yangi);
  }

  function tugatish() {
    surinishRef.current = null;
    window.removeEventListener("mousemove", davomEttirish);
    window.removeEventListener("mouseup", tugatish);
  }

  function boshlash(e, i, mod) {
    e.preventDefault();
    e.stopPropagation();
    surinishRef.current = { i, mod, boshX: e.clientX, boshY: e.clientY, boshQuti: { ...qutilar[i] } };
    window.addEventListener("mousemove", davomEttirish);
    window.addEventListener("mouseup", tugatish);
  }

  if (!rasmUrl) return <div className="yuklanmoqda">…</div>;

  return (
    <div ref={konteynerRef} className="blok-tasdiq-rasm-konteyner">
      <img src={rasmUrl} alt="" draggable={false} />
      {qutilar.map((q, i) => (
        <div
          key={i}
          className="blok-tasdiq-quti"
          style={{
            left: `${q.x1}%`, top: `${q.y1}%`,
            width: `${Math.max(0, q.x2 - q.x1)}%`, height: `${Math.max(0, q.y2 - q.y1)}%`,
          }}
          onMouseDown={(e) => boshlash(e, i, "kochir")}
        >
          <span className="blok-tasdiq-quti-raqam">{i + 1}</span>
          <div
            className="blok-tasdiq-tutqich"
            style={{ left: -6, top: -6 }}
            onMouseDown={(e) => boshlash(e, i, "yuqori-chap")}
          />
          <div
            className="blok-tasdiq-tutqich"
            style={{ right: -6, bottom: -6 }}
            onMouseDown={(e) => boshlash(e, i, "past-ong")}
          />
        </div>
      ))}
    </div>
  );
}

/** ZIP/PDF orqali kitob yuklash tugagach, AI natijasini bazaga yozishdan
 * OLDIN admin ko'rib chiqadigan/tuzatadigan oyna (2026-08-03) — nima
 * uchun kerak: real sinovlarda AI rasm-quti chegaralarini 1-15% xato
 * bilan belgilashi aniqlandi (yuzlar kesilib qolishi va h.k.), shuning
 * uchun avtomatik saqlash xavfli. */
export default function BlokTasdiqlash({ jarayonId, onYakunlandi, onBekor }) {
  const { t } = useI18n();
  const [sahifalar, setSahifalar] = useState(null);
  const [joriyIdx, setJoriyIdx] = useState(0);
  const [tahrirlar, setTahrirlar] = useState({});
  const [bloklarMatn, setBloklarMatn] = useState("");
  const [bloklarXato, setBloklarXato] = useState("");
  const [xato, setXato] = useState("");
  const [saqlanmoqda, setSaqlanmoqda] = useState(false);

  useEffect(() => {
    api(`/api/kurslar/blok-jarayon/${jarayonId}/tasdiq/`)
      .then((d) => setSahifalar(d.sahifalar))
      .catch(() => setXato(t("xato_yuz_berdi")));
  }, [jarayonId, t]);

  const joriy = sahifalar?.[joriyIdx];
  const kalit = joriy ? String(joriy.indeks) : null;
  const joriyTahrir = kalit ? tahrirlar[kalit] || {} : {};

  useEffect(() => {
    if (!joriy) return;
    const bloklar = joriyTahrir.bloklar ?? joriy.bloklar ?? [];
    setBloklarMatn(JSON.stringify(bloklar, null, 2));
    setBloklarXato("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [joriyIdx]);

  if (xato) return <div className="xato-xabar">{xato}</div>;
  if (!sahifalar) return <div className="yuklanmoqda">{t("yuklanmoqda")}</div>;

  function tahrirniYangila(patch) {
    setTahrirlar((prev) => ({ ...prev, [kalit]: { ...prev[kalit], ...patch } }));
  }

  const sarlavha = joriyTahrir.sarlavha ?? joriy.sarlavha ?? "";
  const savollar = joriyTahrir.savollar ?? joriy.savollar ?? [];
  const qutilar = joriyTahrir.qutilar ?? joriy.qutilar ?? [];
  const otkazilganmi = !!joriyTahrir.otkazib_yuborilsin;
  const faylNomi = joriy.fayl?.split("/").pop() || "";

  function bloklarMatniOzgardi(matn) {
    setBloklarMatn(matn);
    try {
      const ajratilgan = JSON.parse(matn);
      setBloklarXato("");
      tahrirniYangila({ bloklar: ajratilgan });
    } catch {
      setBloklarXato(t("kurs_blok_tasdiq_json_xato"));
    }
  }

  function javobniOzgartir(i, qiymat) {
    const yangi = savollar.map((s, j) => (j === i ? { ...s, togri: qiymat } : s));
    tahrirniYangila({ savollar: yangi });
  }

  async function hammasiniTasdiqla() {
    setSaqlanmoqda(true);
    setXato("");
    try {
      const natija = await api(`/api/kurslar/blok-jarayon/${jarayonId}/tasdiqla/`, {
        method: "POST",
        body: { tahrirlar },
      });
      onYakunlandi(natija);
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setSaqlanmoqda(false);
    }
  }

  return (
    <div className="blok-yuklash-qoplama">
      <div className="blok-tasdiq-karta">
        <div className="blok-tasdiq-sarlavha-qator">
          <div style={{ fontWeight: 700 }}>
            {t("kurs_blok_tasdiq_sahifa")} {joriyIdx + 1}/{sahifalar.length}
            {faylNomi ? ` — ${faylNomi}` : ""}
          </div>
          <button className="tugma ikkinchi kichik" onClick={onBekor}>{t("kurs_blok_bekor_qilish")}</button>
        </div>

        {joriy.xato && !joriyTahrir.bloklar && (
          <div className="xato-xabar">{t("kurs_blok_sahifa_xato")}: {joriy.xato}</div>
        )}

        <div className="blok-tasdiq-tana">
          <QutiTahrirlagich
            jarayonId={jarayonId}
            indeks={joriy.indeks}
            qutilar={qutilar}
            onChange={(q) => tahrirniYangila({ qutilar: q })}
          />

          <div className="blok-tasdiq-panel">
            <label>
              <div className="izoh" style={{ marginBottom: 4 }}>{t("kurs_blok_tasdiq_sarlavha")}</div>
              <input
                type="text"
                value={sarlavha}
                onChange={(e) => tahrirniYangila({ sarlavha: e.target.value })}
                style={{ width: "100%" }}
              />
            </label>

            <label>
              <div className="izoh" style={{ marginBottom: 4 }}>{t("kurs_blok_tasdiq_bloklar")}</div>
              <textarea
                value={bloklarMatn}
                onChange={(e) => bloklarMatniOzgardi(e.target.value)}
                rows={10}
                style={{ width: "100%", fontFamily: "monospace", fontSize: 12.5 }}
              />
              {bloklarXato && <div className="xato-xabar" style={{ marginTop: 4 }}>{bloklarXato}</div>}
            </label>

            {savollar.length > 0 && (
              <div>
                <div className="izoh" style={{ marginBottom: 4 }}>{t("kurs_blok_tasdiq_savollar")}</div>
                <div style={{ display: "grid", gap: 4 }}>
                  {savollar.map((s, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span className="izoh" style={{ minWidth: 160, flex: 1 }}>
                        #{i + 1} {s.savol ? `— ${s.savol.slice(0, 40)}` : ""}
                      </span>
                      <input
                        type="text"
                        value={Array.isArray(s.togri) ? s.togri.join(", ") : (s.togri || "")}
                        onChange={(e) => javobniOzgartir(i, e.target.value)}
                        style={{ maxWidth: 200 }}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input
                type="checkbox"
                checked={otkazilganmi}
                onChange={(e) => tahrirniYangila({ otkazib_yuborilsin: e.target.checked })}
              />
              {t("kurs_blok_tasdiq_otkazib_yubor")}
            </label>
          </div>
        </div>

        <div className="blok-tasdiq-navigatsiya">
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className="tugma ikkinchi kichik"
              disabled={joriyIdx === 0}
              onClick={() => setJoriyIdx((i) => i - 1)}
            >
              ← {t("oldingi")}
            </button>
            <button
              className="tugma ikkinchi kichik"
              disabled={joriyIdx === sahifalar.length - 1}
              onClick={() => setJoriyIdx((i) => i + 1)}
            >
              {t("keyingi")} →
            </button>
          </div>
          <button className="tugma" onClick={hammasiniTasdiqla} disabled={saqlanmoqda}>
            {saqlanmoqda ? t("saqlanmoqda") : t("kurs_blok_tasdiq_saqlash")}
          </button>
        </div>
        {xato && <div className="xato-xabar">{xato}</div>}
      </div>
    </div>
  );
}
