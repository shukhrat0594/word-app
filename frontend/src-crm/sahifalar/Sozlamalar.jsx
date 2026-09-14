// Sozlamalar — filiallar.
//
// Filial CRM'ning O'Z modeli (LMS'da yo'q), shuning uchun uni kiritish
// joyi ham CRM ichida bo'lishi kerak. 3 ta filial bir marta kiritiladi.

import { useState } from "react";

import { api } from "../api.js";
import { useI18n } from "../i18n.jsx";
import { useSorov } from "../soragich.js";

function FilialQatori({ filial, onSaqlandi }) {
  const { t } = useI18n();
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
          <button className="tugma kichik-tugma" type="button" onClick={() => setTahrir(true)}>
            {t("tahrirlash")}
          </button>{" "}
          <button className="tugma tugma-sokin kichik-tugma" type="button" onClick={faollikOzgartir}>
            {filial.faol ? t("arxivlash") : t("tiklash")}
          </button>
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

export default function Sozlamalar() {
  const { t } = useI18n();
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
    </section>
  );
}
