import { useEffect, useRef, useState } from "react";
import { api, apiBlobUrl } from "../api";
import { useI18n } from "../i18n";
import { standartVaqt } from "../imtihonVaqt";

export function vaqtFormat(soniya) {
  const m = Math.floor(soniya / 60)
    .toString()
    .padStart(2, "0");
  const s = (soniya % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

// Ketma-ket, bir xil variantlar ro'yxatiga ega fill_blanks savollarni bitta
// "so'z banki" guruhiga birlashtiradi (oqim matn + umumiy variantlar banki
// sifatida render qilinadi). Qolganlari — oddiy blok (radio/matn).
function bloklarGaAjrat(savollar, boshIdx) {
  const bloklar = [];
  let i = 0;
  while (i < savollar.length) {
    const s = savollar[i];
    if (s.tur === "fill_blanks" && s.variantlar && s.variantlar.length > 0) {
      const guruh = [s];
      let j = i + 1;
      while (
        j < savollar.length &&
        savollar[j].tur === "fill_blanks" &&
        savollar[j].variantlar &&
        JSON.stringify(savollar[j].variantlar) === JSON.stringify(s.variantlar)
      ) {
        guruh.push(savollar[j]);
        j++;
      }
      if (guruh.length > 1) {
        bloklar.push({ tur: "bank", savollar: guruh, boshIdx: boshIdx + i });
        i = j;
        continue;
      }
    }
    bloklar.push({ tur: "oddiy", savol: s, idx: boshIdx + i });
    i++;
  }
  return bloklar;
}

const HARFLAR = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

// "matn {{5}} davomi" ko'rinishidagi matnni bo'laklarga ajratadi — {{n}}
// o'rniga kichik input (n — testdagi UMUMIY savol raqami, 1-based; javoblar
// massividagi indeks n-1), \n bo'lsa qatorga o'tadi. Table/Flow-chart
// Completion (2026-07-24) uchun.
function matnniBoslarGaAjrat(matn, javoblar, javobniQoy, natija) {
  if (!matn) return null;
  const qismlar = matn.split(/(\{\{\d+\}\}|\n)/g);
  return qismlar.map((b, i) => {
    if (b === "\n") return <br key={i} />;
    const mos = b.match(/^\{\{(\d+)\}\}$/);
    if (!mos) return <span key={i}>{b}</span>;
    const idx = parseInt(mos[1], 10) - 1;
    const holat = natija ? (natija.natijalar[idx] ? "togri" : "notogri") : "";
    return (
      <input
        key={i}
        className={`imtihon-inline-input ${holat}`}
        disabled={!!natija}
        value={javoblar[idx] || ""}
        onChange={(e) => javobniQoy(idx, e.target.value)}
      />
    );
  });
}

function MaxsusFormatBloki({ format, javoblar, javobniQoy, natija }) {
  if (format.tur === "jadval") {
    return (
      <div className="imtihon-jadval-wrap">
        {format.sarlavha && <div className="imtihon-jadval-sarlavha">{format.sarlavha}</div>}
        <table className="imtihon-jadval">
          {format.ustunlar && (
            <thead>
              <tr>
                {format.ustunlar.map((u, i) => (
                  <th key={i}>{u}</th>
                ))}
              </tr>
            </thead>
          )}
          <tbody>
            {format.qatorlar.map((qator, ri) => (
              <tr key={ri}>
                {qator.map((katak, ci) => (
                  <td key={ci}>{matnniBoslarGaAjrat(katak, javoblar, javobniQoy, natija)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (format.tur === "oqim") {
    return (
      <div className="imtihon-oqim-wrap">
        {format.sarlavha && <div className="imtihon-jadval-sarlavha">{format.sarlavha}</div>}
        {format.qadamlar.map((qadam, i) => (
          <div key={i}>
            <div className="imtihon-oqim-qadam">
              {matnniBoslarGaAjrat(qadam, javoblar, javobniQoy, natija)}
            </div>
            {i < format.qadamlar.length - 1 && <div className="imtihon-oqim-strelka">↓</div>}
          </div>
        ))}
      </div>
    );
  }

  return null;
}

// Matndan {{n}} orqali ishlatilgan barcha savol indekslarini (0-based)
// to'plamiga chiqarib beradi — bular oddiy ro'yxatda takror ko'rsatilmasligi
// uchun.
function maxsusFormatIdxlari(format) {
  const idxlar = new Set();
  if (!format) return idxlar;
  const matnlar = format.tur === "jadval" ? format.qatorlar.flat() : format.qadamlar || [];
  matnlar.forEach((m) => {
    for (const mos of String(m).matchAll(/\{\{(\d+)\}\}/g)) {
      idxlar.add(parseInt(mos[1], 10) - 1);
    }
  });
  return idxlar;
}

function SozBankiBloki({ blok, javoblar, javobniQoy, natija, t }) {
  const [tanlangan, setTanlangan] = useState(null);

  function bloshgaQoy(idx, qiymat) {
    javobniQoy(idx, qiymat);
    setTanlangan(null);
  }

  return (
    <div className="savol-blok">
      {blok.savollar[0].guruh_boshi && (
        <div className="imtihon-guruh-sarlavha">{blok.savollar[0].guruh_boshi}</div>
      )}
      <div className="imtihon-oqim-matn">
        {blok.savollar.map((s, k) => {
          const i = blok.boshIdx + k;
          const holat = natija ? (natija.natijalar[i] ? "togri" : "notogri") : javoblar[i] ? "toldirilgan" : "";
          return (
            <span key={i}>
              {s.savol}{" "}
              <span
                id={`imtihon-savol-${i}`}
                className={`imtihon-bosh-joy ${holat}`}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (natija) return;
                  bloshgaQoy(i, e.dataTransfer.getData("text/plain"));
                }}
                onClick={() => {
                  if (natija) return;
                  if (tanlangan) bloshgaQoy(i, tanlangan);
                }}
              >
                {i + 1}. {javoblar[i] || t("javob_yozing")}
                {natija && <span className={`natija-belgi ${holat}`}>{natija.natijalar[i] ? "✓" : "✗"}</span>}
              </span>{" "}
            </span>
          );
        })}
      </div>
      <div className="imtihon-bank">
        {blok.savollar[0].variantlar.map((v, vi) => (
          <div
            key={v}
            className={`imtihon-bank-chip ${tanlangan === v ? "tanlangan" : ""}`}
            draggable={!natija}
            onDragStart={(e) => e.dataTransfer.setData("text/plain", v)}
            onClick={() => !natija && setTanlangan((prev) => (prev === v ? null : v))}
          >
            {HARFLAR[vi]}. {v}
          </div>
        ))}
      </div>
    </div>
  );
}

// Rasm ustiga to'g'ridan-to'g'ri joylashtiriladigan savollar (Map/Diagram
// Labelling, jadval ichidagi bo'sh joy va h.k.) — savolda "pozitsiya":
// {"x": 0-100, "y": 0-100} (rasm eni/bo'yiga nisbatan foiz) bo'lsa, o'ng
// paneldagi umumiy ro'yxatda emas, aynan shu nuqtada kichik input sifatida
// ko'rsatiladi (2026-07-24).
function RasmSavollari({ rasmUrl, sarlavha, savollar, boshIdx, javoblar, javobniQoy, natija }) {
  return (
    <div style={{ position: "relative", display: "inline-block", maxWidth: "100%" }}>
      <img src={rasmUrl} alt={sarlavha} style={{ maxWidth: "100%", display: "block" }} />
      {savollar.map((s, k) => {
        if (!s.pozitsiya) return null;
        const i = boshIdx + k;
        const holat = natija ? (natija.natijalar[i] ? "togri" : "notogri") : "";
        return (
          <input
            key={i}
            className={`imtihon-rasm-input ${holat}`}
            style={{ left: `${s.pozitsiya.x}%`, top: `${s.pozitsiya.y}%` }}
            disabled={!!natija}
            value={javoblar[i] || ""}
            onChange={(e) => javobniQoy(i, e.target.value)}
            placeholder={`${i + 1}`}
          />
        );
      })}
    </div>
  );
}

function OddiySavolBloki({ blok, javoblar, javobniQoy, natija, t }) {
  const { savol: s, idx: i } = blok;
  return (
    <div className="savol-blok" id={`imtihon-savol-${i}`}>
      {s.guruh_boshi && <div className="imtihon-guruh-sarlavha">{s.guruh_boshi}</div>}
      <div className="savol-matni">
        {i + 1}. {s.savol}
        {natija && (
          <span className={`natija-belgi ${natija.natijalar[i] ? "togri" : "notogri"}`}>
            {natija.natijalar[i] ? "✓" : "✗"}
          </span>
        )}
      </div>
      {s.variantlar && s.variantlar.length > 0 ? (
        s.variantlar.map((v) => (
          <label className="variant-qator" key={v}>
            <input
              type="radio"
              name={`imtihon-savol-${i}`}
              disabled={!!natija}
              checked={javoblar[i] === v}
              onChange={() => javobniQoy(i, v)}
            />
            {v}
          </label>
        ))
      ) : (
        <input
          type="text"
          placeholder={t("javob_yozing")}
          disabled={!!natija}
          value={javoblar[i] || ""}
          onChange={(e) => javobniQoy(i, e.target.value)}
        />
      )}
    </div>
  );
}

/** Cambridge-uslubidagi to'liq IELTS testi — ro'yxat, split-screen yechish
 * rejimi (chapda matn/audio, o'ngda savollar), pastki Part-navigatsiya. */
export default function ImtihonOtish({ bolim }) {
  const { t } = useI18n();
  const [royxat, setRoyxat] = useState([]);
  const [test, setTest] = useState(null);
  const [audioUrllar, setAudioUrllar] = useState({});
  const [rasmUrllar, setRasmUrllar] = useState({});
  const [javoblar, setJavoblar] = useState({});
  const [natija, setNatija] = useState(null);
  const [xato, setXato] = useState("");
  const [yuklanmoqda, setYuklanmoqda] = useState(false);
  const [tayyorlanmoqda, setTayyorlanmoqda] = useState(false);
  const [fokus, setFokus] = useState(false);
  const [masshtab, setMasshtab] = useState(100);
  const [soniya, setSoniya] = useState(0);
  const [teskariMi, setTeskariMi] = useState(false);
  const [faolQism, setFaolQism] = useState(0);
  const [chapKenglik, setChapKenglik] = useState(45);
  const taymerRef = useRef(null);
  const splitRef = useRef(null);
  const sudralmoqda = useRef(false);

  useEffect(() => {
    setTest(null);
    setNatija(null);
    api(`/api/imtihon/testlar/?bolim=${bolim}`).then(setRoyxat).catch(() => {});
  }, [bolim]);

  useEffect(() => {
    if (!test || natija) {
      clearInterval(taymerRef.current);
      return;
    }
    taymerRef.current = setInterval(() => setSoniya((s) => s + 1), 1000);
    return () => clearInterval(taymerRef.current);
  }, [test, natija]);

  useEffect(() => {
    function chiqishdanOldin(e) {
      if (!test || natija) return;
      e.preventDefault();
      e.returnValue = "";
    }
    window.addEventListener("beforeunload", chiqishdanOldin);
    return () => window.removeEventListener("beforeunload", chiqishdanOldin);
  }, [test, natija]);

  useEffect(() => {
    function ustidaHarakat(e) {
      if (!sudralmoqda.current || !splitRef.current) return;
      const { left, width } = splitRef.current.getBoundingClientRect();
      const foiz = ((e.clientX - left) / width) * 100;
      setChapKenglik(Math.min(75, Math.max(20, foiz)));
    }
    function qoyib_yubordi() {
      sudralmoqda.current = false;
    }
    window.addEventListener("mousemove", ustidaHarakat);
    window.addEventListener("mouseup", qoyib_yubordi);
    return () => {
      window.removeEventListener("mousemove", ustidaHarakat);
      window.removeEventListener("mouseup", qoyib_yubordi);
    };
  }, []);

  async function ochish(id) {
    setXato("");
    setNatija(null);
    setJavoblar({});
    setSoniya(0);
    setTeskariMi(false);
    setFokus(false);
    setMasshtab(100);
    setFaolQism(0);
    setTayyorlanmoqda(true);
    try {
      const t2 = await api(`/api/imtihon/testlar/${id}/`);
      const urllar = {};
      const rasmlar = {};
      // Barcha qismlarning audio/rasmini PARALLEL (Promise.all) yuklab
      // olamiz, test oynasi FAQAT hammasi tayyor bo'lgandan keyin ochiladi
      // — shunda talaba "Audio yuklanmoqda..." holatini ko'rmaydi, buning
      // o'rniga bitta umumiy "tayyorlanmoqda" ko'rsatkichi chiqadi.
      await Promise.all(
        t2.qismlar.map(async (qism) => {
          await Promise.all([
            qism.audio_url
              ? apiBlobUrl(qism.audio_url)
                  .then((u) => { urllar[qism.id] = u; })
                  .catch(() => {})
              : Promise.resolve(),
            qism.rasm_url
              ? apiBlobUrl(qism.rasm_url)
                  .then((u) => { rasmlar[qism.id] = u; })
                  .catch(() => {})
              : Promise.resolve(),
          ]);
        })
      );
      setAudioUrllar(urllar);
      setRasmUrllar(rasmlar);
      setTest(t2);
    } finally {
      setTayyorlanmoqda(false);
    }
  }

  function javobniQoy(i, qiymat) {
    setJavoblar((prev) => ({ ...prev, [i]: qiymat }));
  }

  async function yuborish() {
    setYuklanmoqda(true);
    setXato("");
    try {
      const barchaSavollar = test.qismlar.flatMap((q) => q.savollar);
      const tartib = barchaSavollar.map((_, i) => javoblar[i] || "");
      const res = await api(`/api/imtihon/testlar/${test.id}/yechish/`, {
        method: "POST",
        body: { javoblar: tartib },
      });
      setNatija(res);
    } catch (e) {
      setXato(e.data?.detail || t("xato_yuz_berdi"));
    } finally {
      setYuklanmoqda(false);
    }
  }

  function ortgaQaytish() {
    if (!natija && !window.confirm(t("imtihon_ortga_tasdiq"))) return;
    setTest(null);
  }

  function yuborishBosildi() {
    if (!window.confirm(t("imtihon_yakunlash_tasdiq"))) return;
    yuborish();
  }

  function savolgaOt(qismIndex, i) {
    setFaolQism(qismIndex);
    setTimeout(() => {
      document.getElementById(`imtihon-savol-${i}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 50);
  }

  if (!test) {
    return (
      <div className="karta">
        {tayyorlanmoqda ? (
          <div className="yuklanmoqda">{t("imtihon_tayyorlanmoqda")}</div>
        ) : (
          <>
            {royxat.length === 0 && <span className="izoh">{t("imtihon_royxati_boshi")}</span>}
            {royxat.map((r) => (
              <div key={r.id} className="mashq-royxat-el" onClick={() => ochish(r.id)}>
                <span>{r.name}</span>
              </div>
            ))}
          </>
        )}
      </div>
    );
  }

  // Har qism uchun boshlang'ich global raqam + savollar soni.
  let hisoblagich = 0;
  const qismMalumot = test.qismlar.map((qism) => {
    const boshIdx = hisoblagich;
    hisoblagich += qism.savollar.length;
    return { qism, boshIdx, soni: qism.savollar.length };
  });
  const jamiSavollar = hisoblagich;
  const faol = qismMalumot[faolQism];

  const mazmun = (
    <div style={{ fontSize: `${masshtab}%` }}>
      <div className="imtihon-asboblar">
        <button className="tugma ikkinchi" onClick={ortgaQaytish}>
          {t("ortga")}
        </button>
        <span
          className="imtihon-taymer"
          title={t("imtihon_taymer_almashtir")}
          onClick={() => setTeskariMi((v) => !v)}
        >
          ⏱ {vaqtFormat(teskariMi ? Math.max(0, standartVaqt(bolim) - soniya) : soniya)}
        </span>
        <button className="tugma ikkinchi" onClick={() => setFokus((v) => !v)}>
          {fokus ? t("fokusdan_chiqish") : t("fokus_rejimi")}
        </button>
        <span style={{ fontWeight: 700, fontSize: 15 }}>{test.name}</span>
        <div className="imtihon-zoom">
          <button onClick={() => setMasshtab((m) => Math.max(80, m - 10))}>-</button>
          <span className="izoh">{masshtab}%</span>
          <button onClick={() => setMasshtab((m) => Math.min(140, m + 10))}>+</button>
        </div>
      </div>

      {(() => {
        // "pozitsiya" faqat shu qismga rasm biriktirilgan bo'lsagina
        // ma'noga ega — rasm bo'lmasa (masalan JSON'ni AI rasmni ko'rmasdan
        // yozib, "pozitsiya"ni xato qo'shib qo'ysa) savol ro'yxatdan yashirin
        // qolib, hech qayerda ko'rinmay qolmasligi uchun bu holatda pozitsiya
        // e'tiborga olinmaydi (oddiy ro'yxatda ko'rsatiladi).
        const rasmMavjud = !!rasmUrllar[faol.qism.id];
        const pozitsiyaliIdxlar = new Set();
        if (rasmMavjud) {
          faol.qism.savollar.forEach((s, k) => {
            if (s.pozitsiya) pozitsiyaliIdxlar.add(faol.boshIdx + k);
          });
        }
        // Table/Flow-chart Completion (maxsus_format) — shu blokda {{n}}
        // orqali ishlatilgan savollar ham oddiy ro'yxatda takror chiqmasin.
        const maxsusIdxlar = maxsusFormatIdxlari(faol.qism.maxsus_format);
        const yashirilganIdxlar = new Set([...pozitsiyaliIdxlar, ...maxsusIdxlar]);
        const savollarBlok = bloklarGaAjrat(faol.qism.savollar, faol.boshIdx)
          .filter((blok) => {
            if (blok.tur === "oddiy") return !yashirilganIdxlar.has(blok.idx);
            // "bank" bloki — ichidagi BARCHA savollar maxsus_format/pozitsiya
            // orqali allaqachon ko'rsatilgan bo'lsa, ro'yxatda takror chiqmasin.
            return !blok.savollar.every((_, k) => yashirilganIdxlar.has(blok.boshIdx + k));
          })
          .map((blok, bi) =>
          blok.tur === "bank" ? (
            <SozBankiBloki
              key={bi}
              blok={blok}
              javoblar={javoblar}
              javobniQoy={javobniQoy}
              natija={natija}
              t={t}
            />
          ) : (
            <OddiySavolBloki
              key={bi}
              blok={blok}
              javoblar={javoblar}
              javobniQoy={javobniQoy}
              natija={natija}
              t={t}
            />
          )
        );

        // Listening: audio doim yuqorida, to'liq kenglikda. Rasm (Map/
        // Diagram Labelling) bo'lsa — pastda split (rasm chap, savollar
        // o'ng), bo'lmasa — bitta to'liq kenglikdagi panel (split yo'q).
        // Barcha savollar rasmga joylashtirilgan bo'lsa (pozitsiya bilan) —
        // o'ng panel bo'sh qolib ketmasin deb, split umuman ko'rsatilmaydi,
        // rasm to'liq kenglikda chiqadi (2026-07-24).
        if (bolim === "listening") {
          const rasmBormi = !!rasmUrllar[faol.qism.id];
          const ongPanelKerak = savollarBlok.length > 0;
          return (
            <>
              <div className="imtihon-qism-sarlavha">{faol.qism.sarlavha}</div>
              {faol.qism.yoriqnoma && <div className="imtihon-yoriqnoma">{faol.qism.yoriqnoma}</div>}
              {audioUrllar[faol.qism.id] ? (
                <audio
                  controls
                  src={audioUrllar[faol.qism.id]}
                  style={{ width: "100%", marginBottom: fokus ? 6 : 14 }}
                />
              ) : (
                <span className="izoh">{t("audio_yuklanmoqda")}</span>
              )}
              {faol.qism.maxsus_format && (
                <MaxsusFormatBloki
                  format={faol.qism.maxsus_format}
                  javoblar={javoblar}
                  javobniQoy={javobniQoy}
                  natija={natija}
                />
              )}
              {rasmBormi && !ongPanelKerak ? (
                <RasmSavollari
                  rasmUrl={rasmUrllar[faol.qism.id]}
                  sarlavha={faol.qism.sarlavha}
                  savollar={faol.qism.savollar}
                  boshIdx={faol.boshIdx}
                  javoblar={javoblar}
                  javobniQoy={javobniQoy}
                  natija={natija}
                />
              ) : rasmBormi ? (
                <div className="imtihon-split" ref={splitRef}>
                  <div className="imtihon-panel-chap" style={{ flexBasis: `${chapKenglik}%` }}>
                    <RasmSavollari
                      rasmUrl={rasmUrllar[faol.qism.id]}
                      sarlavha={faol.qism.sarlavha}
                      savollar={faol.qism.savollar}
                      boshIdx={faol.boshIdx}
                      javoblar={javoblar}
                      javobniQoy={javobniQoy}
                      natija={natija}
                    />
                  </div>
                  <div
                    className="imtihon-drag-tutqich"
                    onMouseDown={() => {
                      sudralmoqda.current = true;
                    }}
                  >
                    ⋮
                  </div>
                  <div className="imtihon-panel-ong" style={{ flex: 1 }}>
                    {savollarBlok}
                  </div>
                </div>
              ) : (
                <div>{savollarBlok}</div>
              )}
            </>
          );
        }

        // Reading — chapda passage matni, o'ngda savollar. Barcha savollar
        // rasmga joylashtirilgan bo'lsa (pozitsiya bilan) va matn bo'lmasa —
        // o'ng panel bo'sh qolmasin deb split ko'rsatilmaydi (2026-07-24).
        const chapKontent = (
          <>
            <div className="imtihon-qism-sarlavha">{faol.qism.sarlavha}</div>
            {faol.qism.yoriqnoma && <div className="imtihon-yoriqnoma">{faol.qism.yoriqnoma}</div>}
            {faol.qism.matn && <div className="mashq-passage">{faol.qism.matn}</div>}
            {faol.qism.maxsus_format && (
              <MaxsusFormatBloki
                format={faol.qism.maxsus_format}
                javoblar={javoblar}
                javobniQoy={javobniQoy}
                natija={natija}
              />
            )}
            {rasmUrllar[faol.qism.id] && (
              <div style={{ marginTop: 10 }}>
                <RasmSavollari
                  rasmUrl={rasmUrllar[faol.qism.id]}
                  sarlavha={faol.qism.sarlavha}
                  savollar={faol.qism.savollar}
                  boshIdx={faol.boshIdx}
                  javoblar={javoblar}
                  javobniQoy={javobniQoy}
                  natija={natija}
                />
              </div>
            )}
          </>
        );

        if (savollarBlok.length === 0) {
          return <div>{chapKontent}</div>;
        }

        return (
          <div className="imtihon-split" ref={splitRef}>
            <div className="imtihon-panel-chap" style={{ flexBasis: `${chapKenglik}%` }}>
              {chapKontent}
            </div>
            <div
              className="imtihon-drag-tutqich"
              onMouseDown={() => {
                sudralmoqda.current = true;
              }}
            >
              ⋮
            </div>
            <div className="imtihon-panel-ong" style={{ flex: 1 }}>
              {savollarBlok}
            </div>
          </div>
        );
      })()}

      <div className="imtihon-pastki-panel">
        <button
          className="strelka"
          disabled={faolQism === 0}
          onClick={() => setFaolQism((q) => Math.max(0, q - 1))}
        >
          ←
        </button>
        {qismMalumot.map((qm, qi) => (
          <div
            key={qm.qism.id}
            className={`imtihon-part-tab ${qi === faolQism ? "faol" : ""}`}
            onClick={() => setFaolQism(qi)}
          >
            <strong>{qm.qism.sarlavha}:</strong>
            {qi === faolQism ? (
              <div className="raqamlar">
                {Array.from({ length: qm.soni }, (_, k) => {
                  const i = qm.boshIdx + k;
                  return (
                    <button
                      key={i}
                      className={javoblar[i] ? "javob-berilgan" : ""}
                      onClick={(e) => {
                        e.stopPropagation();
                        savolgaOt(qi, i);
                      }}
                    >
                      {i + 1}
                    </button>
                  );
                })}
              </div>
            ) : (
              <span>
                {qm.soni} {t("imtihon_qism_soni")}
              </span>
            )}
          </div>
        ))}
        <button
          className="strelka"
          disabled={faolQism === qismMalumot.length - 1}
          onClick={() => setFaolQism((q) => Math.min(qismMalumot.length - 1, q + 1))}
        >
          →
        </button>

        {!natija ? (
          <button className="tugma katta" onClick={yuborishBosildi} disabled={yuklanmoqda}>
            {yuklanmoqda ? t("tekshirilmoqda") : t("imtihon_topshirish")}
          </button>
        ) : (
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 22, fontWeight: 800, color: "var(--sariq)" }}>
              {natija.band != null ? Number(natija.band).toFixed(1) : "—"}
            </span>
            <span style={{ fontSize: 12.5 }}>
              {t("band_ball")} · {t("xom_ball")} {natija.ball}/{natija.jami}
            </span>
          </div>
        )}
      </div>
      {xato && (
        <div className="xato-xabar" style={{ marginTop: 10 }}>
          {xato}
        </div>
      )}
    </div>
  );

  return fokus ? <div className="imtihon-fokus-ustma">{mazmun}</div> : mazmun;
}
