// Head Teacher dashboard (Matn-TZ 779, 2026-11-27). Backend:
// academics/head_teacher.py (`/api/head-teacher/...`).
//
// Sahifalar:
//   /head-teacher                  — bosh sahifa: 4 KPI, grafiklar, pastki bloklar
//   /head-teacher/groups-students  — guruhlar va talabalar ro'yxati
//   /head-teacher/talaba/:id       — talaba profili (natijalar + AI trenajyorlar)
//   /head-teacher/punktuallik      — ustozlar punktualligi (kiritish/yangilash)
// Davr (sana oralig'i) va filtrlar har sahifada KPI/grafik/jadvalga birga
// ta'sir qiladi: bitta so'rov, bitta javob.
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { Radar } from "../components/Grafiklar";
import NatijalarRoyxati from "../components/NatijalarRoyxati";
import XatolikHolati from "../components/XatolikHolati";
import { useI18n } from "../i18n";

const MATN = {
  uz: {
    dan: "Dan", gacha: "Gacha", daraja: "Daraja", guruh: "Guruh", ustoz: "Ustoz", hammasi: "Hammasi",
    qidiruv: "Ism yoki guruh bo'yicha qidirish", yuklanmoqda: "Yuklanmoqda...",
    bosh: "Ma'lumot topilmadi", xato: "Ma'lumot yuklanmadi",
    kpi_guruh: "Guruhlar va talabalar", guruhlar: "guruh", talabalar: "talaba",
    kpi_natija: "O'rtacha o'quv natijasi", otgan_davr: "o'tgan davrga nisbatan", bajarilgan: "bajarilgan",
    kpi_punkt: "Ustozlar punktualligi", oz_vaqtida: "o'z vaqtida", ort_kech: "o'rtacha kechikish", daq: "daq",
    kpi_sifat: "O'qitish sifati", davomat: "davomat", natija: "natija",
    holat_yaxshi: "Yaxshi", holat_orta: "O'rtacha", holat_diqqat: "Diqqat talab qiladi",
    konikmalar: "Markaz bo'yicha ko'nikmalar (o'rtacha band)", darajalar_kesimi: "Darajalar kesimida o'rtacha natija",
    darajasiz: "Darajasiz", punkt_blok: "Ustozlar punktualligi", batafsil: "Batafsil →",
    diqqat_blok: "Diqqat talab qiluvchi guruhlar", natija_yoq: "davrda natija yo'q",
    past_natija: "past natija", past_davomat: "past davomat", hammasi_yaxshi: "Hammasi joyida",
    kechikishlar: "kechikishlar", darslar: "darslar",
    nav_guruhlar: "Guruhlar", nav_talabalar: "Talabalar", jadval: "Dars jadvali", talaba_soni: "Talabalar",
    ism: "Ism-familiya", faollik: "Oxirgi faollik", profil: "Talaba profili", orqaga: "← Orqaga",
    shaxsiy: "Shaxsiy va guruh ma'lumotlari", telefon: "Telefon", oxirgi_natija: "Oxirgi natija",
    oxirgi_30: "Oxirgi 30 kun", ai_tarix: "AI Speaking Trainer va AI Grammar Coach tarixi",
    tur: "Tur", mavzu: "Daraja / mavzu", xabarlar: "Javoblar", sana: "Sana", oxirgi_javob: "AI'ning so'nggi javobi",
    ai_yoq: "AI trenajyorlarda mashg'ulot yo'q", testlar: "Bajarilgan testlar va mashqlar",
    punkt_sahifa: "Punktuallik nazorati", guruhlash: "Guruhlash", kun: "Kunlik", hafta: "Haftalik", oy: "Oylik",
    yangi: "Dars vaqtini kiritish", rejadagi: "Rejadagi boshlanish", amaliy: "Amaliy boshlanish",
    kechikish: "Kechikish", sabab: "Sabab / izoh", saqlash: "Saqlash", saqlandi: "Saqlandi",
    rejadagi_izoh: "bo'sh qolsa — dars jadvalidan", dinamika: "Punktuallik dinamikasi",
    ustozlar_kesimi: "Ustozlar kesimida", yozuvlar: "Darslar", tahrir: "Tahrirlash", bekor: "Bekor",
    guruh_tanlang: "Guruhni tanlang",
  },
  ru: {
    dan: "С", gacha: "По", daraja: "Уровень", guruh: "Группа", ustoz: "Учитель", hammasi: "Все",
    qidiruv: "Поиск по имени или группе", yuklanmoqda: "Загрузка...",
    bosh: "Данные не найдены", xato: "Не удалось загрузить данные",
    kpi_guruh: "Группы и студенты", guruhlar: "групп", talabalar: "студентов",
    kpi_natija: "Средний учебный результат", otgan_davr: "к прошлому периоду", bajarilgan: "выполнено",
    kpi_punkt: "Пунктуальность учителей", oz_vaqtida: "вовремя", ort_kech: "среднее опоздание", daq: "мин",
    kpi_sifat: "Качество обучения", davomat: "посещаемость", natija: "результат",
    holat_yaxshi: "Хорошо", holat_orta: "Средне", holat_diqqat: "Требует внимания",
    konikmalar: "Навыки по центру (средний band)", darajalar_kesimi: "Средний результат по уровням",
    darajasiz: "Без уровня", punkt_blok: "Пунктуальность учителей", batafsil: "Подробнее →",
    diqqat_blok: "Группы, требующие внимания", natija_yoq: "нет результатов за период",
    past_natija: "низкий результат", past_davomat: "низкая посещаемость", hammasi_yaxshi: "Всё в порядке",
    kechikishlar: "опоздания", darslar: "уроки",
    nav_guruhlar: "Группы", nav_talabalar: "Студенты", jadval: "Расписание", talaba_soni: "Студенты",
    ism: "Имя и фамилия", faollik: "Последняя активность", profil: "Профиль студента", orqaga: "← Назад",
    shaxsiy: "Личные данные и группы", telefon: "Телефон", oxirgi_natija: "Последний результат",
    oxirgi_30: "Последние 30 дней", ai_tarix: "История AI Speaking Trainer и AI Grammar Coach",
    tur: "Тип", mavzu: "Уровень / тема", xabarlar: "Ответы", sana: "Дата", oxirgi_javob: "Последний ответ AI",
    ai_yoq: "Занятий в AI-тренажёрах нет", testlar: "Выполненные тесты и упражнения",
    punkt_sahifa: "Контроль пунктуальности", guruhlash: "Группировка", kun: "По дням", hafta: "По неделям", oy: "По месяцам",
    yangi: "Ввести время урока", rejadagi: "Плановое начало", amaliy: "Фактическое начало",
    kechikish: "Опоздание", sabab: "Причина / комментарий", saqlash: "Сохранить", saqlandi: "Сохранено",
    rejadagi_izoh: "если пусто — из расписания", dinamika: "Динамика пунктуальности",
    ustozlar_kesimi: "По учителям", yozuvlar: "Уроки", tahrir: "Изменить", bekor: "Отмена",
    guruh_tanlang: "Выберите группу",
  },
  en: {
    dan: "From", gacha: "To", daraja: "Level", guruh: "Group", ustoz: "Teacher", hammasi: "All",
    qidiruv: "Search by name or group", yuklanmoqda: "Loading...",
    bosh: "No data found", xato: "Failed to load data",
    kpi_guruh: "Groups and students", guruhlar: "groups", talabalar: "students",
    kpi_natija: "Average learning result", otgan_davr: "vs previous period", bajarilgan: "completed",
    kpi_punkt: "Teacher punctuality", oz_vaqtida: "on time", ort_kech: "average delay", daq: "min",
    kpi_sifat: "Teaching quality", davomat: "attendance", natija: "result",
    holat_yaxshi: "Good", holat_orta: "Average", holat_diqqat: "Needs attention",
    konikmalar: "Center skills (average band)", darajalar_kesimi: "Average result by level",
    darajasiz: "No level", punkt_blok: "Teacher punctuality", batafsil: "Details →",
    diqqat_blok: "Groups needing attention", natija_yoq: "no results in period",
    past_natija: "low result", past_davomat: "low attendance", hammasi_yaxshi: "All good",
    kechikishlar: "delays", darslar: "lessons",
    nav_guruhlar: "Groups", nav_talabalar: "Students", jadval: "Schedule", talaba_soni: "Students",
    ism: "Full name", faollik: "Last activity", profil: "Student profile", orqaga: "← Back",
    shaxsiy: "Personal and group info", telefon: "Phone", oxirgi_natija: "Last result",
    oxirgi_30: "Last 30 days", ai_tarix: "AI Speaking Trainer and AI Grammar Coach history",
    tur: "Type", mavzu: "Level / topic", xabarlar: "Replies", sana: "Date", oxirgi_javob: "Last AI reply",
    ai_yoq: "No AI trainer sessions", testlar: "Completed tests and exercises",
    punkt_sahifa: "Punctuality control", guruhlash: "Grouping", kun: "Daily", hafta: "Weekly", oy: "Monthly",
    yangi: "Enter lesson time", rejadagi: "Planned start", amaliy: "Actual start",
    kechikish: "Delay", sabab: "Reason / note", saqlash: "Save", saqlandi: "Saved",
    rejadagi_izoh: "empty — taken from the schedule", dinamika: "Punctuality dynamics",
    ustozlar_kesimi: "By teacher", yozuvlar: "Lessons", tahrir: "Edit", bekor: "Cancel",
    guruh_tanlang: "Select a group",
  },
};

const AI_TURLARI = { speaking_trainer: "AI Speaking Trainer", grammar_coach: "AI Grammar Coach" };

function useMatn() {
  const { til } = useI18n();
  const lugat = MATN[til] || MATN.uz;
  return (k) => lugat[k] ?? MATN.uz[k] ?? k;
}

function bugun(siljish = 0) {
  const d = new Date();
  d.setDate(d.getDate() + siljish);
  const oy = String(d.getMonth() + 1).padStart(2, "0");
  const kun = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${oy}-${kun}`;
}

const BOSHLANGICH_FILTR = { dan: bugun(-29), gacha: bugun(), daraja: "", guruh: "", oqituvchi: "", q: "" };

function sorovQatori(filtr) {
  const p = new URLSearchParams();
  Object.entries(filtr).forEach(([k, v]) => {
    if (v !== "" && v != null) p.set(k, v);
  });
  return p.toString();
}

function foiz(v) {
  return v == null ? "—" : `${v}%`;
}

function sanaVaqt(v) {
  return v ? new Date(v).toLocaleString() : "—";
}

/** So'rov holati: yuklanmoqda / xato / ma'lumot. `yol` o'zgarsa qayta yuklaydi.
 * Faqat filtr (so'rov qatori) o'zgarsa eski ma'lumot xira ko'rinib turadi;
 * endpointning o'zi o'zgarsa (masalan Guruhlar -> Talabalar tabi) — boshqa
 * shakldagi eski ma'lumot chizilmasligi uchun tozalanadi. */
function useMalumot(yol) {
  const asos = yol.split("?")[0];
  const [holat, setHolat] = useState({ malumot: null, xato: "", yuklanmoqda: true, asos });
  const [qayta, setQayta] = useState(0);
  useEffect(() => {
    let bekor = false;
    const asos = yol.split("?")[0];
    setHolat((h) => ({ malumot: h.asos === asos ? h.malumot : null, xato: "", yuklanmoqda: true, asos }));
    api(yol)
      .then((m) => !bekor && setHolat({ malumot: m, xato: "", yuklanmoqda: false, asos }))
      .catch((e) => !bekor && setHolat({ malumot: null, xato: e.data?.detail || "x", yuklanmoqda: false, asos }));
    return () => {
      bekor = true;
    };
  }, [yol, qayta]);
  // Effekt ishlashidan oldingi birinchi renderda ham eski endpoint ma'lumoti berilmaydi.
  const malumot = holat.asos === asos ? holat.malumot : null;
  return { ...holat, malumot, qaytaYukla: () => setQayta((q) => q + 1) };
}

function Holatlar({ h, m, children }) {
  if (h.xato) return <XatolikHolati xabar={h.xato === "x" ? m("xato") : h.xato} qaytaUrin={h.qaytaYukla} />;
  if (!h.malumot) return <div className="yuklanmoqda">{m("yuklanmoqda")}</div>;
  return (
    <div style={{ opacity: h.yuklanmoqda ? 0.6 : 1, transition: "opacity .15s" }}>{children}</div>
  );
}

function BoshHolat({ m }) {
  return <div className="izoh ht-bosh">{m("bosh")}</div>;
}

/** Davr va filtrlar paneli. `maydonlar` — qaysi filtrlar ko'rinadi. */
function FiltrPaneli({ filtr, setFiltr, maydonlar = ["daraja", "guruh", "oqituvchi"], qidiruv = false, qoshimcha }) {
  const m = useMatn();
  const [tanlov, setTanlov] = useState({ darajalar: [], guruhlar: [], ustozlar: [] });
  useEffect(() => {
    api("/api/head-teacher/filtrlar/").then(setTanlov).catch(() => {});
  }, []);
  const ozgar = (k) => (e) => setFiltr((f) => ({ ...f, [k]: e.target.value }));
  const tanlash = (k, royxat, nom) => (
    <label className="ht-filtr">
      <span>{m(k === "oqituvchi" ? "ustoz" : k)}</span>
      <select value={filtr[k]} onChange={ozgar(k)}>
        <option value="">{m("hammasi")}</option>
        {royxat.map((r) => (
          <option key={r.id} value={r.id}>{r[nom]}</option>
        ))}
      </select>
    </label>
  );
  return (
    <div className="karta ht-filtrlar">
      <label className="ht-filtr">
        <span>{m("dan")}</span>
        <input type="date" value={filtr.dan} onChange={ozgar("dan")} />
      </label>
      <label className="ht-filtr">
        <span>{m("gacha")}</span>
        <input type="date" value={filtr.gacha} onChange={ozgar("gacha")} />
      </label>
      {maydonlar.includes("daraja") && tanlash("daraja", tanlov.darajalar, "nomi")}
      {maydonlar.includes("guruh") && tanlash("guruh", tanlov.guruhlar, "nomi")}
      {maydonlar.includes("oqituvchi") && tanlash("oqituvchi", tanlov.ustozlar, "ism")}
      {qidiruv && (
        <label className="ht-filtr ht-filtr-keng">
          <span>&nbsp;</span>
          <input type="search" placeholder={m("qidiruv")} value={filtr.q} onChange={ozgar("q")} />
        </label>
      )}
      {qoshimcha}
    </div>
  );
}

/** Qidiruvda har harfga so'rov ketmasin — 300 ms kutib yuboriladi. */
function useKechiktirilgan(qiymat, ms = 300) {
  const [k, setK] = useState(qiymat);
  useEffect(() => {
    const id = setTimeout(() => setK(qiymat), ms);
    return () => clearTimeout(id);
  }, [qiymat, ms]);
  return k;
}

function Chiziq({ qiymat }) {
  const v = Math.max(0, Math.min(100, qiymat ?? 0));
  const rang = qiymat == null ? "var(--chiziq)" : v >= 80 ? "var(--yaxshi)" : v >= 60 ? "var(--sariq)" : "var(--xato)";
  return (
    <div className="ht-chiziq">
      <div style={{ width: `${v}%`, background: rang }} />
    </div>
  );
}

// ── Bosh sahifa ───────────────────────────────────────────────────────

export function HeadTeacherDashboard() {
  const m = useMatn();
  const [filtr, setFiltr] = useState(BOSHLANGICH_FILTR);
  const h = useMalumot(`/api/head-teacher/dashboard/?${sorovQatori(filtr)}`);
  const d = h.malumot;
  const k = d?.kpi;

  return (
    <>
      <FiltrPaneli filtr={filtr} setFiltr={setFiltr} />
      <Holatlar h={h} m={m}>
        {d && (
          <>
            <div className="stat-qator">
              <div className="stat">
                <div className="nom">{m("kpi_guruh")}</div>
                <div className="qiymat">
                  {k.guruhlar} <small>{m("guruhlar")}</small> · {k.talabalar} <small>{m("talabalar")}</small>
                </div>
                <div className="izoh">
                  {k.darajalar.map((r) => `${r.nomi || m("darajasiz")}: ${r.talabalar}`).join(" · ")}
                </div>
              </div>
              <div className="stat">
                <div className="nom">{m("kpi_natija")}</div>
                <div className="qiymat">{foiz(k.natija_foiz)}</div>
                <div className="izoh">
                  {k.natija_ozgarish != null && (
                    <span style={{ color: k.natija_ozgarish >= 0 ? "var(--yaxshi)" : "var(--xato)", fontWeight: 700 }}>
                      {k.natija_ozgarish >= 0 ? "▲ +" : "▼ "}{k.natija_ozgarish}%{" "}
                    </span>
                  )}
                  {k.natija_ozgarish != null && `${m("otgan_davr")} · `}
                  {k.bajarilgan} {m("bajarilgan")}
                </div>
              </div>
              <div className="stat">
                <div className="nom">{m("kpi_punkt")}</div>
                <div className="qiymat">{foiz(k.punktuallik.oz_vaqtida_foiz)} <small>{m("oz_vaqtida")}</small></div>
                <div className="izoh">
                  {m("ort_kech")}: {k.punktuallik.ortacha_kechikish ?? "—"} {m("daq")} · {k.punktuallik.darslar} {m("darslar")}
                </div>
              </div>
              <div className="stat">
                <div className="nom">{m("kpi_sifat")}</div>
                <div className="qiymat">
                  {foiz(k.sifat.indeks)}{" "}
                  {k.sifat.holat && <small className={`ht-holat ht-holat-${k.sifat.holat}`}>{m(`holat_${k.sifat.holat}`)}</small>}
                </div>
                <div className="izoh">
                  {m("natija")} {foiz(k.natija_foiz)} · {m("davomat")} {foiz(k.davomat_foiz)} · {m("oz_vaqtida")} {foiz(k.punktuallik.oz_vaqtida_foiz)}
                </div>
              </div>
            </div>

            <div className="ikki-ustun" style={{ marginTop: 20 }}>
              <div className="karta">
                <h3>{m("konikmalar")}</h3>
                <Radar konikmalar={d.konikmalar} />
                <div className="izoh" style={{ textAlign: "center" }}>
                  Writing {d.konikmalar.writing_band ?? "—"} · Speaking {d.konikmalar.speaking_band ?? "—"} · Listening{" "}
                  {d.konikmalar.listening_band ?? "—"} · Reading {d.konikmalar.reading_band ?? "—"}
                </div>
              </div>
              <div className="karta">
                <h3>{m("darajalar_kesimi")}</h3>
                {k.darajalar.length === 0 && <BoshHolat m={m} />}
                {k.darajalar.map((r) => (
                  <div key={r.id ?? 0} className="ht-bar-qator">
                    <span className="ht-bar-nom">
                      {r.nomi || m("darajasiz")} <span className="izoh">({r.guruhlar} / {r.talabalar})</span>
                    </span>
                    <Chiziq qiymat={r.natija_foiz} />
                    <span className="ht-bar-qiymat">{foiz(r.natija_foiz)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="ikki-ustun" style={{ marginTop: 20 }}>
              <div className="karta">
                <h3>
                  {m("punkt_blok")} <Link className="ht-havola" to="/head-teacher/punktuallik">{m("batafsil")}</Link>
                </h3>
                {d.ustozlar_punktualligi.length === 0 ? (
                  <BoshHolat m={m} />
                ) : (
                  <div className="ht-jadval-wrap">
                    <table className="ht-jadval">
                      <thead>
                        <tr><th>{m("ustoz")}</th><th>{m("oz_vaqtida")}</th><th>{m("kechikishlar")}</th><th>{m("ort_kech")}</th></tr>
                      </thead>
                      <tbody>
                        {d.ustozlar_punktualligi.map((u) => (
                          <tr key={u.oqituvchi.id ?? 0}>
                            <td>{u.oqituvchi.ism}</td>
                            <td>{foiz(u.oz_vaqtida_foiz)}</td>
                            <td>{u.kechikishlar}</td>
                            <td>{u.ortacha_kechikish ?? "—"} {m("daq")}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
              <div className="karta">
                <h3>
                  {m("diqqat_blok")} <Link className="ht-havola" to="/head-teacher/groups-students">{m("batafsil")}</Link>
                </h3>
                {d.diqqat_guruhlar.length === 0 && <div className="izoh ht-bosh">{m("hammasi_yaxshi")}</div>}
                {d.diqqat_guruhlar.map((g) => (
                  <Link key={g.id} className="ht-diqqat" to={`/head-teacher/groups-students?guruh=${g.id}`}>
                    <b>{g.nomi}</b>
                    <span className="izoh">
                      {[g.daraja?.nomi, g.oqituvchi?.ism].filter(Boolean).join(" · ")}
                    </span>
                    <span className="ht-teglar">
                      {g.sabablar.map((s) => (
                        <span key={s} className="ht-teg">{m(s)}</span>
                      ))}
                      <span className="izoh">
                        {m("natija")} {foiz(g.natija_foiz)} · {m("davomat")} {foiz(g.davomat_foiz)}
                      </span>
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          </>
        )}
      </Holatlar>
    </>
  );
}

// ── Guruhlar va talabalar ─────────────────────────────────────────────

export function HeadTeacherGuruhlarTalabalar() {
  const m = useMatn();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [tab, setTab] = useState(params.get("guruh") ? "talabalar" : "guruhlar");
  const [filtr, setFiltr] = useState({ ...BOSHLANGICH_FILTR, guruh: params.get("guruh") || "" });
  const q = useKechiktirilgan(filtr.q);
  const sorov = sorovQatori({ ...filtr, q });
  const h = useMalumot(`/api/head-teacher/${tab}/?${sorov}`);

  return (
    <>
      <div className="ht-tablar">
        {["guruhlar", "talabalar"].map((tb) => (
          <button key={tb} className={tab === tb ? "tugma" : "tugma ikkinchi"} onClick={() => setTab(tb)}>
            {m(`nav_${tb}`)}
          </button>
        ))}
      </div>
      <FiltrPaneli filtr={filtr} setFiltr={setFiltr} qidiruv />
      <Holatlar h={h} m={m}>
        {h.malumot && h.malumot.length === 0 && <div className="karta"><BoshHolat m={m} /></div>}
        {h.malumot && h.malumot.length > 0 && tab === "guruhlar" && (
          <div className="karta ht-jadval-wrap">
            <table className="ht-jadval">
              <thead>
                <tr>
                  <th>{m("guruh")}</th><th>{m("daraja")}</th><th>{m("ustoz")}</th><th>{m("jadval")}</th>
                  <th>{m("talaba_soni")}</th><th>{m("natija")}</th><th>{m("davomat")}</th>
                </tr>
              </thead>
              <tbody>
                {h.malumot.map((g) => (
                  <tr
                    key={g.id}
                    className="ht-bosiladi"
                    onClick={() => {
                      setFiltr((f) => ({ ...f, guruh: String(g.id), q: "" }));
                      setTab("talabalar");
                    }}
                  >
                    <td><b>{g.nomi}</b></td>
                    <td>{g.daraja?.nomi || "—"}</td>
                    <td>{g.oqituvchi?.ism || "—"}</td>
                    <td>{g.jadval || "—"}</td>
                    <td>{g.talaba_soni}</td>
                    <td>{foiz(g.natija_foiz)}</td>
                    <td>{foiz(g.davomat_foiz)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {h.malumot && h.malumot.length > 0 && tab === "talabalar" && (
          <div className="karta ht-jadval-wrap">
            <table className="ht-jadval">
              <thead>
                <tr>
                  <th>{m("ism")}</th><th>{m("guruh")}</th><th>{m("daraja")}</th><th>{m("ustoz")}</th>
                  <th>{m("natija")}</th><th>{m("bajarilgan")}</th><th>{m("faollik")}</th>
                </tr>
              </thead>
              <tbody>
                {h.malumot.map((t) => (
                  <tr key={t.id} className="ht-bosiladi" onClick={() => navigate(`/head-teacher/talaba/${t.id}`)}>
                    <td><b>{t.ism}</b></td>
                    <td>{t.guruhlar.map((g) => g.nomi).join(", ") || "—"}</td>
                    <td>{t.darajalar.join(", ") || "—"}</td>
                    <td>{t.ustozlar.join(", ") || "—"}</td>
                    <td>{foiz(t.natija_foiz)}</td>
                    <td>{t.bajarilgan}</td>
                    <td>{sanaVaqt(t.oxirgi_faollik)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Holatlar>
    </>
  );
}

// ── Talaba profili ────────────────────────────────────────────────────

export function HeadTeacherTalabaProfil() {
  const m = useMatn();
  const { id } = useParams();
  const navigate = useNavigate();
  const h = useMalumot(`/api/head-teacher/talabalar/${id}/`);
  const p = h.malumot;

  return (
    <>
      <button className="tugma ikkinchi" onClick={() => navigate(-1)} style={{ marginBottom: 14 }}>
        {m("orqaga")}
      </button>
      <Holatlar h={h} m={m}>
        {p && (
          <>
            <div className="karta">
              <h3>{m("profil")}: {p.ism}</h3>
              <div className="ht-profil">
                <div>
                  <div className="izoh">{m("shaxsiy")}</div>
                  <div>@{p.username}{p.telefon && ` · ${m("telefon")}: ${p.telefon}`}</div>
                  {p.guruhlar.length === 0 && <div className="izoh">—</div>}
                  {p.guruhlar.map((g) => (
                    <div key={g.id} style={{ opacity: g.faol ? 1 : 0.55 }}>
                      <b>{g.nomi}</b> · {m("daraja")}: {g.daraja?.nomi || "—"} · {m("ustoz")}: {g.oqituvchi?.ism || "—"}
                    </div>
                  ))}
                </div>
                <div>
                  <div className="izoh">{m("faollik")}</div>
                  <div>{sanaVaqt(p.faollik.oxirgi_faollik)}</div>
                  <div className="izoh">{m("oxirgi_natija")}: {sanaVaqt(p.faollik.oxirgi_natija)}</div>
                  <div className="izoh">
                    {m("oxirgi_30")}: {p.faollik.oxirgi_30_kun_bajarilgan} {m("bajarilgan")}, {m("natija")}{" "}
                    {foiz(p.faollik.oxirgi_30_kun_natija_foiz)}
                  </div>
                </div>
              </div>
            </div>

            <div className="karta" style={{ marginTop: 20 }}>
              <h3>{m("ai_tarix")}</h3>
              {p.ai_trenajyorlar.length === 0 ? (
                <div className="izoh">{m("ai_yoq")}</div>
              ) : (
                <div className="ht-jadval-wrap">
                  <table className="ht-jadval">
                    <thead>
                      <tr><th>{m("tur")}</th><th>{m("mavzu")}</th><th>{m("xabarlar")}</th><th>{m("sana")}</th><th>{m("oxirgi_javob")}</th></tr>
                    </thead>
                    <tbody>
                      {p.ai_trenajyorlar.map((y) => (
                        <tr key={y.id}>
                          <td>{AI_TURLARI[y.tur] || y.tur}</td>
                          <td>{y.mavzu || "—"}</td>
                          <td>{y.xabar_soni}</td>
                          <td>{sanaVaqt(y.yangilangan)}</td>
                          <td>
                            <details>
                              <summary>{y.oxirgi_javob.slice(0, 60)}{y.oxirgi_javob.length > 60 ? "…" : ""}</summary>
                              <div className="ht-javob">{y.oxirgi_javob}</div>
                            </details>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="karta" style={{ marginTop: 20 }}>
              <h3>{m("testlar")}</h3>
              <NatijalarRoyxati talabaId={p.id} />
            </div>
          </>
        )}
      </Holatlar>
    </>
  );
}

// ── Punktuallik nazorati ──────────────────────────────────────────────

function YozuvQatori({ y, m, saqlandi }) {
  const [tahrir, setTahrir] = useState(false);
  const [amaliy, setAmaliy] = useState(y.amaliy_vaqt || "");
  const [sabab, setSabab] = useState(y.sabab || "");
  const [xato, setXato] = useState("");

  async function saqla() {
    setXato("");
    try {
      await api(`/api/head-teacher/punktuallik/${y.id}/`, {
        method: "PATCH", body: { amaliy_vaqt: amaliy, sabab },
      });
      setTahrir(false);
      saqlandi();
    } catch (e) {
      setXato(e.data?.detail || m("xato"));
    }
  }

  return (
    <tr>
      <td>{y.sana}</td>
      <td>{y.guruh.nomi}</td>
      <td>{y.oqituvchi?.ism || "—"}</td>
      <td>{y.rejadagi_vaqt}</td>
      <td>{tahrir ? <input type="time" value={amaliy} onChange={(e) => setAmaliy(e.target.value)} /> : y.amaliy_vaqt || "—"}</td>
      <td style={{ color: y.kechikish_daqiqa > 0 ? "var(--xato)" : undefined, fontWeight: 600 }}>
        {y.kechikish_daqiqa == null ? "—" : `${y.kechikish_daqiqa} ${m("daq")}`}
      </td>
      <td>
        {tahrir ? <input value={sabab} maxLength={300} onChange={(e) => setSabab(e.target.value)} /> : y.sabab || "—"}
        {xato && <div className="xato-xabar">{xato}</div>}
      </td>
      <td style={{ whiteSpace: "nowrap" }}>
        {tahrir ? (
          <>
            <button className="tugma kichik" onClick={saqla}>{m("saqlash")}</button>{" "}
            <button className="tugma kichik ikkinchi" onClick={() => setTahrir(false)}>{m("bekor")}</button>
          </>
        ) : (
          <button className="tugma kichik ikkinchi" onClick={() => setTahrir(true)}>{m("tahrir")}</button>
        )}
      </td>
    </tr>
  );
}

function YangiYozuv({ m, saqlandi }) {
  const [guruhlar, setGuruhlar] = useState([]);
  const [f, setF] = useState({ guruh: "", sana: bugun(), rejadagi_vaqt: "", amaliy_vaqt: "", sabab: "" });
  const [xabar, setXabar] = useState({ matn: "", xato: false });
  useEffect(() => {
    api("/api/head-teacher/filtrlar/").then((r) => setGuruhlar(r.guruhlar)).catch(() => {});
  }, []);
  const ozgar = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));

  async function yubor(e) {
    e.preventDefault();
    if (!f.guruh) return setXabar({ matn: m("guruh_tanlang"), xato: true });
    try {
      await api("/api/head-teacher/punktuallik/", { method: "POST", body: f });
      setXabar({ matn: m("saqlandi"), xato: false });
      setF((x) => ({ ...x, amaliy_vaqt: "", sabab: "" }));
      saqlandi();
    } catch (err) {
      setXabar({ matn: err.data?.detail || m("xato"), xato: true });
    }
  }

  return (
    <form className="karta ht-filtrlar" onSubmit={yubor}>
      <h3 style={{ width: "100%" }}>{m("yangi")}</h3>
      <label className="ht-filtr">
        <span>{m("guruh")}</span>
        <select value={f.guruh} onChange={ozgar("guruh")}>
          <option value="">—</option>
          {guruhlar.map((g) => <option key={g.id} value={g.id}>{g.nomi}</option>)}
        </select>
      </label>
      <label className="ht-filtr"><span>{m("sana")}</span><input type="date" value={f.sana} onChange={ozgar("sana")} /></label>
      <label className="ht-filtr" title={m("rejadagi_izoh")}>
        <span>{m("rejadagi")}</span>
        <input type="time" value={f.rejadagi_vaqt} onChange={ozgar("rejadagi_vaqt")} />
      </label>
      <label className="ht-filtr"><span>{m("amaliy")}</span><input type="time" value={f.amaliy_vaqt} onChange={ozgar("amaliy_vaqt")} /></label>
      <label className="ht-filtr ht-filtr-keng">
        <span>{m("sabab")}</span>
        <input value={f.sabab} maxLength={300} onChange={ozgar("sabab")} />
      </label>
      <div className="ht-filtr">
        <span>&nbsp;</span>
        <button className="tugma" type="submit">{m("saqlash")}</button>
      </div>
      <div className="izoh" style={{ width: "100%" }}>
        {m("rejadagi")}: {m("rejadagi_izoh")}.{" "}
        {xabar.matn && <span className={xabar.xato ? "xato-xabar" : ""}>{xabar.matn}</span>}
      </div>
    </form>
  );
}

export function HeadTeacherPunktuallik() {
  const m = useMatn();
  const [filtr, setFiltr] = useState({ ...BOSHLANGICH_FILTR, guruhlash: "kun" });
  const h = useMalumot(`/api/head-teacher/punktuallik/?${sorovQatori(filtr)}`);
  const d = h.malumot;

  return (
    <>
      <h2 style={{ marginTop: 0 }}>{m("punkt_sahifa")}</h2>
      <YangiYozuv m={m} saqlandi={h.qaytaYukla} />
      <FiltrPaneli
        filtr={filtr}
        setFiltr={setFiltr}
        maydonlar={["guruh", "oqituvchi"]}
        qoshimcha={
          <label className="ht-filtr">
            <span>{m("guruhlash")}</span>
            <select value={filtr.guruhlash} onChange={(e) => setFiltr((f) => ({ ...f, guruhlash: e.target.value }))}>
              {["kun", "hafta", "oy"].map((g) => <option key={g} value={g}>{m(g)}</option>)}
            </select>
          </label>
        }
      />
      <Holatlar h={h} m={m}>
        {d && (
          <>
            <div className="stat-qator">
              <div className="stat"><div className="nom">{m("darslar")}</div><div className="qiymat">{d.xulosa.darslar}</div></div>
              <div className="stat"><div className="nom">{m("oz_vaqtida")}</div><div className="qiymat">{foiz(d.xulosa.oz_vaqtida_foiz)}</div></div>
              <div className="stat"><div className="nom">{m("kechikishlar")}</div><div className="qiymat">{d.xulosa.kechikishlar}</div></div>
              <div className="stat">
                <div className="nom">{m("ort_kech")}</div>
                <div className="qiymat">{d.xulosa.ortacha_kechikish ?? "—"} <small>{m("daq")}</small></div>
              </div>
            </div>

            <div className="ikki-ustun" style={{ marginTop: 20 }}>
              <div className="karta">
                <h3>{m("dinamika")}</h3>
                {d.dinamika.length === 0 && <BoshHolat m={m} />}
                {d.dinamika.map((r) => (
                  <div key={r.davr} className="ht-bar-qator">
                    <span className="ht-bar-nom">{r.davr}</span>
                    <Chiziq qiymat={r.oz_vaqtida_foiz} />
                    <span className="ht-bar-qiymat" title={`${m("ort_kech")}: ${r.ortacha_kechikish ?? "—"} ${m("daq")}`}>
                      {foiz(r.oz_vaqtida_foiz)} · {r.kechikishlar}/{r.darslar}
                    </span>
                  </div>
                ))}
              </div>
              <div className="karta">
                <h3>{m("ustozlar_kesimi")}</h3>
                {d.ustozlar.length === 0 ? (
                  <BoshHolat m={m} />
                ) : (
                  <div className="ht-jadval-wrap">
                    <table className="ht-jadval">
                      <thead>
                        <tr><th>{m("ustoz")}</th><th>{m("darslar")}</th><th>{m("kechikishlar")}</th><th>{m("ort_kech")}</th><th>{m("oz_vaqtida")}</th></tr>
                      </thead>
                      <tbody>
                        {d.ustozlar.map((u) => (
                          <tr key={u.oqituvchi.id ?? 0}>
                            <td>{u.oqituvchi.ism}</td>
                            <td>{u.darslar}</td>
                            <td>{u.kechikishlar}</td>
                            <td>{u.ortacha_kechikish ?? "—"} {m("daq")}</td>
                            <td>{foiz(u.oz_vaqtida_foiz)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>

            <div className="karta ht-jadval-wrap" style={{ marginTop: 20 }}>
              <h3>{m("yozuvlar")}</h3>
              {d.yozuvlar.length === 0 ? (
                <BoshHolat m={m} />
              ) : (
                <table className="ht-jadval">
                  <thead>
                    <tr>
                      <th>{m("sana")}</th><th>{m("guruh")}</th><th>{m("ustoz")}</th><th>{m("rejadagi")}</th>
                      <th>{m("amaliy")}</th><th>{m("kechikish")}</th><th>{m("sabab")}</th><th />
                    </tr>
                  </thead>
                  <tbody>
                    {d.yozuvlar.map((y) => (
                      <YozuvQatori key={`${y.id}-${y.amaliy_vaqt}-${y.sabab}`} y={y} m={m} saqlandi={h.qaytaYukla} />
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </Holatlar>
    </>
  );
}
