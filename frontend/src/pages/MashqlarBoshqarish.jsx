import { useEffect, useState } from "react";
import { api, apiForm } from "../api";
import { useI18n } from "../i18n";

const BOLIM_TURLARI = {
  listening: ["multiple_choice", "fill_blanks", "matching", "map_labelling", "short_answer"],
  reading: ["multiple_choice", "fill_blanks", "matching_headings", "tfng", "short_answer"],
  writing: ["task1", "task2"],
  speaking: ["part1", "part2", "part3"],
};

const AVTO_BAHOLANADI = ["listening", "reading"];

const AI_PROMT = `Men senga IELTS mashqlari uchun xom material (matn, savollar, mavzular) beraman. Sen shu materialni quyidagi JSON formatiga o'girib ber — natija FAQAT valid JSON massiv bo'lsin, hech qanday izoh, sarlavha yoki markdown belgisi (masalan \`\`\`json) qo'shma, faqat sof JSON matni qaytar.

Har bir mashq — shu formatdagi obyekt:
{
  "name": "Mashqning qisqa nomi",
  "bolim": "listening" | "reading" | "writing" | "speaking",
  "tur": "quyidagi ro'yxatdan, bolim'ga mos ravishda",
  "korinish": "private" | "public",
  "matn": "Reading uchun passage matni / Writing uchun topshiriq matni / Speaking uchun savol(lar) matni. Listening uchun bo'sh qoldirish mumkin (audio alohida yuklanadi).",
  "namuna_javob": "Writing/Speaking uchun namuna javob (ixtiyoriy, bo'lmasa bo'sh qoldir)",
  "savollar": [
    { "savol": "Savol matni", "variantlar": ["A variant", "B variant"], "togri": "To'g'ri javob" }
  ],
  "audio_base64": "(BUNI TO'LDIRMA — foydalanuvchi o'zi keyinroq qo'shadi, sen audio fayl yarata olmaysan)",
  "rasm_base64": "(BUNI TO'LDIRMA — foydalanuvchi o'zi keyinroq qo'shadi, sen rasm fayl yarata olmaysan)"
}

Qoidalar:
- "bolim" = "listening" bo'lsa "tur" quyidagilardan biri: multiple_choice, fill_blanks, matching, map_labelling, short_answer
- "bolim" = "reading" bo'lsa "tur": multiple_choice, fill_blanks, matching_headings, tfng, short_answer
- "bolim" = "writing" bo'lsa "tur": task1 yoki task2
- "bolim" = "speaking" bo'lsa "tur": part1, part2 yoki part3
- "savollar" faqat listening va reading uchun MAJBURIY (kamida 1 ta savol, har birida "savol" va "togri" bo'lishi shart, "variantlar" ixtiyoriy). Writing va speaking uchun "savollar"ni bo'sh massiv [] qoldir.
- "korinish": agar material barcha foydalanuvchilarga (Utmost talabasi bo'lmaganlarga ham) ochiq bo'lishi kerak bo'lsa "public", faqat Utmost talabalari uchun bo'lsa "private" yoz. Aniq ko'rsatilmagan bo'lsa "private" qo'y.
- "audio_base64" va "rasm_base64" maydonlarini HECH QACHON to'ldirma va JSON'ga qo'shma — sen (AI) haqiqiy audio yoki rasm fayl yarata olmaysan, bu ikki maydon faqat foydalanuvchi o'zida tayyor fayl bo'lsa, o'zi qo'lda base64'ga aylantirib qo'shishi uchun. Sen faqat matn/savol/namuna javoblarni to'ldir, media maydonlarini butunlay tashla.
- Agar bitta material ichida bir nechta mashq/savollar to'plami bo'lsa — har birini alohida obyekt qilib, bittasi array ichida bir nechta obyekt bo'lsin.

Natijani shu JSON massiv ko'rinishida qaytar, boshqa hech narsa yozma. Quyida mening materialim:

[BU YERGA MATERIALINGIZNI (matn, savollar, transkript va h.k.) joylashtiring]`;

const BOSH_DRAFT = {
  name: "",
  bolim: "reading",
  tur: "multiple_choice",
  korinish: "private",
  matn: "",
  namuna_javob: "",
  audio_fayl: null,
  rasm: null,
  savollar: [],
};

export default function MashqlarBoshqarish() {
  const { t } = useI18n();
  const [draft, setDraft] = useState(BOSH_DRAFT);
  const [navbat, setNavbat] = useState([]);
  const [royxat, setRoyxat] = useState(null);
  const [filtrBolim, setFiltrBolim] = useState("");
  const [saqlanmoqda, setSaqlanmoqda] = useState(false);
  const [natijalar, setNatijalar] = useState([]);
  const [jsonXato, setJsonXato] = useState("");
  const [promtKorinadi, setPromtKorinadi] = useState(false);
  const [nusxalandi, setNusxalandi] = useState(false);

  function promtNusxala() {
    navigator.clipboard?.writeText(AI_PROMT).then(() => {
      setNusxalandi(true);
      setTimeout(() => setNusxalandi(false), 2000);
    });
  }

  function yukla(bolim) {
    api(`/api/mashqlar-boshqaruv/${bolim ? `?bolim=${bolim}` : ""}`)
      .then(setRoyxat)
      .catch(() => {});
  }

  useEffect(() => {
    yukla(filtrBolim);
  }, [filtrBolim]);

  function bolimOzgar(bolim) {
    setDraft((d) => ({ ...d, bolim, tur: BOLIM_TURLARI[bolim][0] }));
  }

  function savolQosh() {
    setDraft((d) => ({
      ...d,
      savollar: [...d.savollar, { savol: "", variantlar: "", togri: "" }],
    }));
  }

  function savolOzgar(i, maydon, qiymat) {
    setDraft((d) => ({
      ...d,
      savollar: d.savollar.map((s, idx) => (idx === i ? { ...s, [maydon]: qiymat } : s)),
    }));
  }

  function savolOlibTashla(i) {
    setDraft((d) => ({ ...d, savollar: d.savollar.filter((_, idx) => idx !== i) }));
  }

  function navbatgaQosh() {
    if (!draft.name.trim()) return;
    setNavbat((n) => [...n, draft]);
    setDraft({ ...BOSH_DRAFT, bolim: draft.bolim, tur: draft.tur, korinish: draft.korinish });
  }

  function navbatdanOlibTashla(i) {
    setNavbat((n) => n.filter((_, idx) => idx !== i));
  }

  function base64gaFayl(qiymat, standartNomi, standartMime) {
    if (!qiymat) return null;
    let mime = standartMime || "application/octet-stream";
    let b64 = qiymat;
    const dataUriMos = qiymat.match(/^data:([^;]+);base64,([\s\S]*)$/);
    if (dataUriMos) {
      mime = dataUriMos[1];
      b64 = dataUriMos[2];
    }
    try {
      const bin = atob(b64);
      const arr = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
      return new File([arr], standartNomi, { type: mime });
    } catch {
      return null;
    }
  }

  async function jsonYukla(e) {
    const fayl = e.target.files[0];
    e.target.value = "";
    if (!fayl) return;
    setJsonXato("");
    try {
      const matn = await fayl.text();
      const data = JSON.parse(matn);
      const royxatJson = Array.isArray(data) ? data : [data];
      const yangi = royxatJson.map((m) => ({
        name: m.name || "",
        bolim: BOLIM_TURLARI[m.bolim] ? m.bolim : "reading",
        tur: m.tur || BOLIM_TURLARI[BOLIM_TURLARI[m.bolim] ? m.bolim : "reading"][0],
        korinish: m.korinish === "public" ? "public" : "private",
        matn: m.matn || "",
        namuna_javob: m.namuna_javob || "",
        audio_fayl: base64gaFayl(m.audio_base64, m.audio_nomi || "audio.mp3", m.audio_mime),
        rasm: base64gaFayl(m.rasm_base64, m.rasm_nomi || "rasm.png", m.rasm_mime),
        savollar: Array.isArray(m.savollar)
          ? m.savollar.map((s) => ({
              savol: s.savol || "",
              variantlar: Array.isArray(s.variantlar) ? s.variantlar.join(", ") : s.variantlar || "",
              togri: Array.isArray(s.togri) ? s.togri.join(", ") : s.togri || "",
            }))
          : [],
      }));
      setNavbat((n) => [...n, ...yangi]);
    } catch (err) {
      setJsonXato(t("mashq_json_xato"));
    }
  }

  async function mediaBiriktir(id, maydon, fayl) {
    if (!fayl) return;
    const fd = new FormData();
    fd.append(maydon, fayl);
    try {
      await apiForm(`/api/mashqlar-boshqaruv/${id}/`, { method: "PATCH", formData: fd });
      yukla(filtrBolim);
    } catch (e) {
      setJsonXato(e.data?.detail || t("xato_yuz_berdi"));
    }
  }

  async function hammasiniSaqla() {
    setSaqlanmoqda(true);
    setNatijalar([]);
    const yangiNavbat = [];
    for (const m of navbat) {
      const fd = new FormData();
      fd.append("name", m.name);
      fd.append("bolim", m.bolim);
      fd.append("tur", m.tur);
      fd.append("korinish", m.korinish);
      fd.append("matn", m.matn);
      fd.append("namuna_javob", m.namuna_javob);
      const savollarToza = m.savollar.map((s) => ({
        savol: s.savol,
        variantlar: s.variantlar
          ? s.variantlar.split(",").map((v) => v.trim()).filter(Boolean)
          : undefined,
        togri: s.togri,
      }));
      fd.append("savollar", JSON.stringify(savollarToza));
      if (m.audio_fayl) fd.append("audio_fayl", m.audio_fayl);
      if (m.rasm) fd.append("rasm", m.rasm);

      try {
        await apiForm("/api/mashqlar-boshqaruv/", { method: "POST", formData: fd });
        setNatijalar((r) => [...r, { name: m.name, ok: true }]);
      } catch (e) {
        setNatijalar((r) => [...r, { name: m.name, ok: false, xato: e.data?.detail || JSON.stringify(e.data) }]);
        yangiNavbat.push(m);
      }
    }
    setNavbat(yangiNavbat);
    setSaqlanmoqda(false);
    yukla(filtrBolim);
  }

  async function ochir(id) {
    if (!window.confirm(t("mashq_ochirish_tasdiq"))) return;
    try {
      await api(`/api/mashqlar-boshqaruv/${id}/`, { method: "DELETE" });
      yukla(filtrBolim);
    } catch {
      // sokin
    }
  }

  const savollarKerak = AVTO_BAHOLANADI.includes(draft.bolim);

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <div className="karta">
        <h3>{t("mashq_json_yuklash")}</h3>
        <p className="izoh" style={{ marginTop: 0 }}>{t("mashq_json_izoh")}</p>
        <input type="file" accept="application/json" onChange={jsonYukla} />
        {jsonXato && <div className="xato-xabar" style={{ marginTop: 8 }}>{jsonXato}</div>}

        <div style={{ marginTop: 14 }}>
          <button
            type="button"
            className="tugma ikkinchi"
            onClick={() => setPromtKorinadi((v) => !v)}
          >
            {promtKorinadi ? t("mashq_promt_yashirish") : t("mashq_promt_korsatish")}
          </button>
          {promtKorinadi && (
            <div style={{ marginTop: 10 }}>
              <p className="izoh" style={{ marginTop: 0 }}>{t("mashq_promt_izoh")}</p>
              <textarea
                readOnly
                rows={14}
                value={AI_PROMT}
                onClick={(e) => e.target.select()}
                style={{ width: "100%", fontFamily: "monospace", fontSize: 12.5 }}
              />
              <button type="button" className="tugma" onClick={promtNusxala} style={{ marginTop: 8 }}>
                {nusxalandi ? t("nusxalandi") : t("nusxalash")}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="karta">
        <h3>{t("mashq_yangi_qoshish")}</h3>

        <div style={{ display: "grid", gap: 12, maxWidth: 640 }}>
          <div className="tab-guruh">
            {Object.keys(BOLIM_TURLARI).map((b) => (
              <button
                key={b}
                type="button"
                className={draft.bolim === b ? "aktiv" : ""}
                onClick={() => bolimOzgar(b)}
              >
                {t(`mashq_bolim_${b}`)}
              </button>
            ))}
          </div>

          <input
            placeholder={t("mashq_nomi")}
            value={draft.name}
            onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
          />

          <select
            value={draft.tur}
            onChange={(e) => setDraft((d) => ({ ...d, tur: e.target.value }))}
          >
            {BOLIM_TURLARI[draft.bolim].map((tr) => (
              <option key={tr} value={tr}>
                {t(`mashq_tur_${tr}`)}
              </option>
            ))}
          </select>

          <select
            value={draft.korinish}
            onChange={(e) => setDraft((d) => ({ ...d, korinish: e.target.value }))}
          >
            <option value="private">{t("mashq_faqat_talaba")}</option>
            <option value="public">{t("mashq_hammaga_ochiq")}</option>
          </select>

          <textarea
            placeholder={t("mashq_matn")}
            rows={5}
            value={draft.matn}
            onChange={(e) => setDraft((d) => ({ ...d, matn: e.target.value }))}
          />

          {(draft.bolim === "writing" || draft.bolim === "speaking") && (
            <textarea
              placeholder={t("mashq_namuna_javob")}
              rows={4}
              value={draft.namuna_javob}
              onChange={(e) => setDraft((d) => ({ ...d, namuna_javob: e.target.value }))}
            />
          )}

          {draft.bolim === "listening" && (
            <div>
              <div className="izoh" style={{ marginBottom: 4 }}>{t("mashq_audio")}</div>
              <input
                type="file"
                accept="audio/*"
                onChange={(e) => setDraft((d) => ({ ...d, audio_fayl: e.target.files[0] }))}
              />
            </div>
          )}

          <div>
            <div className="izoh" style={{ marginBottom: 4 }}>{t("mashq_rasm")}</div>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setDraft((d) => ({ ...d, rasm: e.target.files[0] }))}
            />
          </div>

          {savollarKerak && (
            <div>
              <div className="izoh" style={{ marginBottom: 6 }}>{t("mashq_savollar")}</div>
              <div style={{ display: "grid", gap: 8 }}>
                {draft.savollar.map((s, i) => (
                  <div
                    key={i}
                    style={{ display: "grid", gap: 6, padding: 8, border: "1px solid var(--chiziq)", borderRadius: 8 }}
                  >
                    <input
                      placeholder={t("mashq_savol_matni")}
                      value={s.savol}
                      onChange={(e) => savolOzgar(i, "savol", e.target.value)}
                    />
                    <input
                      placeholder={t("mashq_variantlar")}
                      value={s.variantlar}
                      onChange={(e) => savolOzgar(i, "variantlar", e.target.value)}
                    />
                    <div style={{ display: "flex", gap: 6 }}>
                      <input
                        placeholder={t("mashq_togri_javob")}
                        value={s.togri}
                        onChange={(e) => savolOzgar(i, "togri", e.target.value)}
                      />
                      <button className="tugma ikkinchi" type="button" onClick={() => savolOlibTashla(i)}>
                        {t("ochirish")}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              <button className="tugma ikkinchi" type="button" onClick={savolQosh} style={{ marginTop: 8 }}>
                {t("mashq_savol_qoshish")}
              </button>
            </div>
          )}

          <button className="tugma" type="button" onClick={navbatgaQosh}>
            {t("mashq_royxatga_qoshish")}
          </button>
        </div>
      </div>

      {navbat.length > 0 && (
        <div className="karta">
          <h3>{t("mashq_navbat")} ({navbat.length})</h3>
          <div style={{ display: "grid", gap: 8 }}>
            {navbat.map((m, i) => (
              <div className="davomat-qator" key={i}>
                <span>
                  <strong>{m.name}</strong>{" "}
                  <span className="izoh">
                    {t(`mashq_bolim_${m.bolim}`)} · {t(`mashq_tur_${m.tur}`)}
                    {m.audio_fayl && " · 🎧"}
                    {m.rasm && " · 🖼"}
                  </span>
                </span>
                <button className="tugma ikkinchi" onClick={() => navbatdanOlibTashla(i)}>
                  {t("ochirish")}
                </button>
              </div>
            ))}
          </div>
          <button className="tugma katta" onClick={hammasiniSaqla} disabled={saqlanmoqda} style={{ marginTop: 12 }}>
            {saqlanmoqda ? t("saqlanmoqda") : t("mashq_hammasini_saqlash")}
          </button>
          {natijalar.length > 0 && (
            <div style={{ marginTop: 10, display: "grid", gap: 4 }}>
              {natijalar.map((n, i) => (
                <div key={i} className={n.ok ? "izoh" : "xato-xabar"}>
                  {n.name}: {n.ok ? t("saqlandi") : n.xato}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="karta">
        <h3>{t("mashq_mavjud_royxat")}</h3>
        <div className="tab-guruh" style={{ marginBottom: 12 }}>
          <button className={filtrBolim === "" ? "aktiv" : ""} onClick={() => setFiltrBolim("")}>
            {t("hammasi")}
          </button>
          {Object.keys(BOLIM_TURLARI).map((b) => (
            <button
              key={b}
              className={filtrBolim === b ? "aktiv" : ""}
              onClick={() => setFiltrBolim(b)}
            >
              {t(`mashq_bolim_${b}`)}
            </button>
          ))}
        </div>
        {!royxat ? (
          <div className="yuklanmoqda">{t("yuklanmoqda")}</div>
        ) : royxat.length === 0 ? (
          <span className="izoh">{t("mashq_royxat_boshi")}</span>
        ) : (
          <div style={{ display: "grid", gap: 8 }}>
            {royxat.map((m) => (
              <div className="davomat-qator" key={m.id}>
                <span>
                  <strong>{m.name}</strong>{" "}
                  <span className="izoh">
                    {t(`mashq_bolim_${m.bolim}`)} · {t(`mashq_tur_${m.tur}`)} ·{" "}
                    {m.korinish === "public" ? t("mashq_hammaga_ochiq") : t("mashq_faqat_talaba")}
                    {!m.audio_url && m.bolim === "listening" && ` · ${t("mashq_audio_yoq")}`}
                    {!m.rasm_url && ` · ${t("mashq_rasm_yoq")}`}
                  </span>
                </span>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  {m.bolim === "listening" && !m.audio_url && (
                    <input
                      type="file"
                      accept="audio/*"
                      title={t("mashq_audio_biriktir")}
                      style={{ maxWidth: 140 }}
                      onChange={(e) => mediaBiriktir(m.id, "audio_fayl", e.target.files[0])}
                    />
                  )}
                  {!m.rasm_url && (
                    <input
                      type="file"
                      accept="image/*"
                      title={t("mashq_rasm_biriktir")}
                      style={{ maxWidth: 140 }}
                      onChange={(e) => mediaBiriktir(m.id, "rasm", e.target.files[0])}
                    />
                  )}
                  <button className="tugma ikkinchi" style={{ color: "#d33" }} onClick={() => ochir(m.id)}>
                    {t("ochirish")}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
