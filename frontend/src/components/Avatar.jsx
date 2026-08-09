import { useEffect, useState } from "react";
import { apiBlobUrl } from "../api";

/** Profil rasmi (2026-08-09).
 *
 * MUHIM: rasm autentifikatsiyalangan endpointdan keladi
 * (`/api/foydalanuvchilar/<pk>/rasm/`, R2 bucket yopiq) — oddiy
 * `<img src=...>` Authorization sarlavhasini YUBORMAYDI va 401 oladi.
 * Shuning uchun loyihadagi boshqa media kabi `apiBlobUrl` orqali
 * yuklanadi (blob URL komponent yopilganda bo'shatiladi).
 *
 * `rasmUrl` bo'sh bo'lsa — o'rniga standart belgi ko'rsatiladi. */
export default function Avatar({ rasmUrl, olcham = 34, sarlavha }) {
  const [blobUrl, setBlobUrl] = useState(null);

  useEffect(() => {
    if (!rasmUrl) {
      setBlobUrl(null);
      return undefined;
    }
    let joriy = null;
    let bekorQilindi = false;
    apiBlobUrl(rasmUrl)
      .then((u) => {
        if (bekorQilindi) {
          URL.revokeObjectURL(u);
          return;
        }
        joriy = u;
        setBlobUrl(u);
      })
      .catch(() => {});
    return () => {
      bekorQilindi = true;
      setBlobUrl(null);
      if (joriy) URL.revokeObjectURL(joriy);
    };
  }, [rasmUrl]);

  const umumiy = {
    width: olcham,
    height: olcham,
    borderRadius: "50%",
    flexShrink: 0,
    display: "block",
  };

  if (blobUrl) {
    return <img src={blobUrl} alt="" title={sarlavha} style={{ ...umumiy, objectFit: "cover" }} />;
  }
  return (
    <span
      title={sarlavha}
      style={{
        ...umumiy,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: Math.round(olcham * 0.45),
        background: "var(--sirt-2)",
        border: "1px dashed var(--chiziq)",
      }}
    >
      👤
    </span>
  );
}
