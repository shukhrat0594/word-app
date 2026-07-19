import { useEffect, useRef } from "react";

function cssVar(nom) {
  return getComputedStyle(document.documentElement).getPropertyValue(nom).trim();
}

export function Radar({ konikmalar }) {
  const ref = useRef(null);
  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const x = c.getContext("2d");
    x.clearRect(0, 0, c.width, c.height);
    const cx = c.width / 2,
      cy = c.height / 2 + 8,
      R = 88;
    const oqlar = ["Writing", "Speaking", "Listening", "Reading"];
    const q = [
      (konikmalar.writing_band || 0) / 9,
      (konikmalar.speaking_band || 0) / 9,
      (konikmalar.listening_foiz || 0) / 100,
      (konikmalar.reading_foiz || 0) / 100,
    ];
    const n = oqlar.length;
    x.strokeStyle = cssVar("--chiziq");
    x.fillStyle = cssVar("--matn-sokin");
    x.font = "600 12px Segoe UI, sans-serif";
    for (let d = 1; d <= 3; d++) {
      x.beginPath();
      for (let i = 0; i <= n; i++) {
        const a = (Math.PI * 2 * i) / n - Math.PI / 2;
        const px = cx + Math.cos(a) * R * (d / 3),
          py = cy + Math.sin(a) * R * (d / 3);
        i ? x.lineTo(px, py) : x.moveTo(px, py);
      }
      x.stroke();
    }
    for (let i = 0; i < n; i++) {
      const a = (Math.PI * 2 * i) / n - Math.PI / 2;
      x.beginPath();
      x.moveTo(cx, cy);
      x.lineTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R);
      x.stroke();
      x.textAlign = "center";
      x.fillText(
        oqlar[i],
        cx + Math.cos(a) * (R + 24),
        cy + Math.sin(a) * (R + 14) + 4
      );
    }
    x.beginPath();
    for (let i = 0; i <= n; i++) {
      const a = (Math.PI * 2 * (i % n)) / n - Math.PI / 2;
      x[i ? "lineTo" : "moveTo"](
        cx + Math.cos(a) * R * q[i % n],
        cy + Math.sin(a) * R * q[i % n]
      );
    }
    x.closePath();
    x.fillStyle = "rgba(255,212,0,.25)";
    x.fill();
    x.strokeStyle = cssVar("--sariq");
    x.lineWidth = 2.5;
    x.stroke();
  }, [konikmalar]);
  return <canvas ref={ref} width={400} height={260} style={{ maxWidth: "100%" }} />;
}

export function Dinamika({ dinamika }) {
  const ref = useRef(null);
  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const x = c.getContext("2d");
    x.clearRect(0, 0, c.width, c.height);
    const ballar = dinamika.map((d) => d.band).filter((b) => b != null);
    if (ballar.length < 2) {
      x.fillStyle = cssVar("--matn-sokin");
      x.font = "600 13px Segoe UI, sans-serif";
      x.textAlign = "center";
      x.fillText("Kamida 2 ta tekshiruv kerak", c.width / 2, c.height / 2);
      return;
    }
    const chap = 30,
      ost = c.height - 24,
      keng = c.width - chap - 14,
      bal = c.height - 58;
    const minB = 3,
      maxB = 9;
    const nx = (i) => chap + (keng * i) / (ballar.length - 1);
    const ny = (b) => ost - ((b - minB) / (maxB - minB)) * bal;
    x.strokeStyle = cssVar("--chiziq");
    x.fillStyle = cssVar("--matn-sokin");
    x.font = "600 11px Segoe UI, sans-serif";
    x.textAlign = "left";
    for (let b = minB; b <= maxB; b += 2) {
      x.beginPath();
      x.moveTo(chap, ny(b));
      x.lineTo(c.width - 8, ny(b));
      x.stroke();
      x.fillText(String(b), 6, ny(b) + 4);
    }
    x.beginPath();
    ballar.forEach((b, i) => x[i ? "lineTo" : "moveTo"](nx(i), ny(b)));
    x.lineTo(nx(ballar.length - 1), ost);
    x.lineTo(nx(0), ost);
    x.closePath();
    x.fillStyle = "rgba(255,212,0,.18)";
    x.fill();
    x.beginPath();
    ballar.forEach((b, i) => x[i ? "lineTo" : "moveTo"](nx(i), ny(b)));
    x.strokeStyle = cssVar("--sariq");
    x.lineWidth = 2.5;
    x.stroke();
    const oxi = ballar.length - 1;
    x.beginPath();
    x.arc(nx(oxi), ny(ballar[oxi]), 5, 0, 7);
    x.fillStyle = cssVar("--sariq");
    x.fill();
    x.strokeStyle = cssVar("--komir");
    x.lineWidth = 2;
    x.stroke();
  }, [dinamika]);
  return <canvas ref={ref} width={400} height={260} style={{ maxWidth: "100%" }} />;
}
