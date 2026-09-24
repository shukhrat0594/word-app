// Sozlamalar — filiallar.
//
// Filial CRM'ning O'Z modeli (LMS'da yo'q), shuning uchun uni kiritish
// joyi ham CRM ichida bo'lishi kerak. 3 ta filial bir marta kiritiladi.

import { useState } from "react";

import { api } from "../api.js";
import { useI18n } from "../i18n.jsx";
import { useCheklangan } from "../profilContext.jsx";
import { useSorov } from "../soragich.js";

function FilialQatori({ filial, onSaqlandi }) {
  const { t } = useI18n();
  const cheklangan = useCheklangan();
  const [tahrir, setTahrir] = useState(false);
  const [nomi, setNomi] = useState(filial.nomi);
  const [manzil, setManzil] = useState(filial.manzil);
  const [telefon, setTelefon] = useState(filial.telefon);
  const [xato, setXato] = useState("");

  async function saqla() {
    setXato("");
    try {
      await api(`/api/crm/filiallar/${filial.id}/`, {
        method: "PATCH",
        body: { nomi, manzil, telefon },
      });
      setTahrir(false);
      onSaqlandi();
    } catch (e) {
      setXato(e.message || "Xato");
    }
  }

  async function faollikOzgartir() {
    // Filial O'CHIRILMAYDI, arxivlanadi: unga bog'langan hisoblarda
    // `filial` snapshot sifatida turibdi va o'tgan oylar hisoboti
    // buzilmasligi kerak.
    await api(`/api/crm/filiallar/${filial.id}/`, {
      method: "PATCH",
      body: { faol: !filial.faol },
    });
    onSaqlandi();
  }

  if (!tahrir) {
    return (
      <tr className={filial.faol ? "" : "qator-sokin"}>
        <td>{filial.nomi}</td>
        <td>{filial.manzil || "—"}</td>
        <td>{filial.telefon || "—"}</td>
        <td>{filial.faol ? t("faol") : t("arxivlangan")}</td>
        <td>
          {/* Filiallar — markaz sozlamasi: filialga bog'langan xodim faqat ko'radi. */}
          {!cheklangan && (
            <>
              <button className="tugma kichik-tugma" type="button" onClick={() => setTahrir(true)}>
                {t("tahrirlash")}
              </button>{" "}
              <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={faollikOzgartir}>
                {filial.faol ? t("arxivlash") : t("tiklash")}
              </button>
            </>
          )}
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td><input value={nomi} onChange={(e) => setNomi(e.target.value)} /></td>
      <td><input value={manzil} onChange={(e) => setManzil(e.target.value)} /></td>
      <td><input value={telefon} onChange={(e) => setTelefon(e.target.value)} /></td>
      <td>{xato && <span className="xato">{xato}</span>}</td>
      <td>
        <button className="tugma kichik-tugma" type="button" onClick={saqla}>{t("saqlash")}</button>{" "}
        <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={() => setTahrir(false)}>
          {t("bekor")}
        </button>
      </td>
    </tr>
  );
}

function Xonalar({ filiallar }) {
  const { t } = useI18n();
  const { malumot, yuklanmoqda, yangila } = useSorov("/api/crm/xonalar/");
  const [filialId, setFilialId] = useState("");
  const [nomi, setNomi] = useState("");
  const [sigimi, setSigimi] = useState("");
  const [xato, setXato] = useState("");

  async function qosh() {
    if (!filialId || !nomi.trim()) {
      setXato(t("xona_nomi_kerak"));
      return;
    }
    setXato("");
    try {
      await api("/api/crm/xonalar/", {
        method: "POST",
        body: { filial_id: filialId, nomi, sigimi: sigimi || null },
      });
      setNomi("");
      setSigimi("");
      yangila();
    } catch (e) {
      setXato(e.message || "Xato");
    }
  }

  async function faollikOzgartir(xona) {
    // Xona O'CHIRILMAYDI, arxivlanadi: dars yozuvlarida u `SET_NULL`
    // bilan bog'langan va o'chirilsa jadval jimgina "xonasiz" bo'lib
    // qolardi.
    await api(`/api/crm/xonalar/${xona.id}/`, {
      method: "PATCH",
      body: { faol: !xona.faol },
    });
    yangila();
  }

  const xonalar = malumot || [];

  return (
    <div className="karta">
      <h2>{t("xonalar")}</h2>
      {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

      <div className="jadval-oram">
        <table>
          <thead>
            <tr>
              <th>{t("filial")}</th>
              <th>{t("xona")}</th>
              <th className="ongga">{t("sigimi")}</th>
              <th>{t("holat")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {xonalar.map((x) => (
              <tr key={x.id} className={x.faol ? "" : "qator-sokin"}>
                <td>{x.filial}</td>
                <td>{x.nomi}</td>
                <td className="ongga">{x.sigimi ?? "—"}</td>
                <td>{x.faol ? t("faol") : t("arxivlangan")}</td>
                <td>
                  <button className="tugma tugma-sokin kichik-tugma" type="button"
                          onClick={() => faollikOzgartir(x)}>
                    {x.faol ? t("arxivlash") : t("tiklash")}
                  </button>
                </td>
              </tr>
            ))}
            {!yuklanmoqda && xonalar.length === 0 && (
              <tr><td colSpan={5} className="bosh">{t("yozuv_yoq")}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="uch-ustun" style={{ marginTop: 14 }}>
        <label>
          {t("filial")}
          <select value={filialId} onChange={(e) => setFilialId(e.target.value)}>
            <option value="">—</option>
            {filiallar.filter((f) => f.faol).map((f) => (
              <option key={f.id} value={f.id}>{f.nomi}</option>
            ))}
          </select>
        </label>
        <label>
          {t("xona")}
          <input value={nomi} onChange={(e) => setNomi(e.target.value)} placeholder="2-xona" />
        </label>
        <label>
          {t("sigimi")}
          <input type="number" min="0" value={sigimi} onChange={(e) => setSigimi(e.target.value)} />
        </label>
      </div>
      {xato && <div className="xato">{xato}</div>}
      <div className="oyna-tugmalar">
        <button className="tugma" type="button" onClick={qosh}>{t("qoshish")}</button>
      </div>
    </div>
  );
}

export default function Sozlamalar() {
  const { t } = useI18n();
  const cheklangan = useCheklangan();
  const { malumot, yuklanmoqda, xato, yangila } = useSorov("/api/crm/filiallar/");
  const [yangiNomi, setYangiNomi] = useState("");
  const [yangiManzil, setYangiManzil] = useState("");
  const [yangiTelefon, setYangiTelefon] = useState("");
  const [qoshXato, setQoshXato] = useState("");

  async function qosh() {
    if (!yangiNomi.trim()) {
      setQoshXato(t("filial_nomi_kerak"));
      return;
    }
    setQoshXato("");
    try {
      await api("/api/crm/filiallar/", {
        method: "POST",
        body: { nomi: yangiNomi, manzil: yangiManzil, telefon: yangiTelefon },
      });
      setYangiNomi("");
      setYangiManzil("");
      setYangiTelefon("");
      yangila();
    } catch (e) {
      setQoshXato(e.message || "Xato");
    }
  }

  const filiallar = malumot || [];

  return (
    <section>
      <h1>{t("sozlamalar")}</h1>

      <div className="karta">
        <h2>{t("filiallar")}</h2>
        {xato && <div className="xato">{xato}</div>}
        {yuklanmoqda && <p className="kichik">{t("yuklanmoqda")}</p>}

        <div className="jadval-oram">
          <table>
            <thead>
              <tr>
                <th>{t("filial")}</th>
                <th>{t("manzil")}</th>
                <th>{t("telefon")}</th>
                <th>{t("holat")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filiallar.map((f) => (
                <FilialQatori key={f.id} filial={f} onSaqlandi={yangila} />
              ))}
              {!yuklanmoqda && filiallar.length === 0 && (
                <tr><td colSpan={5} className="bosh">{t("yozuv_yoq")}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <Xonalar filiallar={filiallar} />

      {!cheklangan && (
      <div className="karta">
        <h2>{t("yangi_filial")}</h2>
        <div className="uch-ustun">
          <label>
            {t("filial")}
            <input value={yangiNomi} onChange={(e) => setYangiNomi(e.target.value)} />
          </label>
          <label>
            {t("manzil")}
            <input value={yangiManzil} onChange={(e) => setYangiManzil(e.target.value)} />
          </label>
          <label>
            {t("telefon")}
            <input value={yangiTelefon} onChange={(e) => setYangiTelefon(e.target.value)} />
          </label>
        </div>
        {qoshXato && <div className="xato">{qoshXato}</div>}
        <div className="oyna-tugmalar">
          <button className="tugma" type="button" onClick={qosh}>{t("qoshish")}</button>
        </div>
      </div>
      )}
    </section>
  );
}
