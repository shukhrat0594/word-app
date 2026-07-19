// AI xato qatorini ("noto'g'ri -> to'g'ri (sabab)") uch qismga ajratadi.
export function xatoniAjrat(qator) {
  const m = /^(.*?)\s*->\s*(.*?)\s*\(([^)]*)\)\s*$/.exec(qator);
  if (!m) return { notogri: qator, togri: "", sabab: "" };
  return { notogri: m[1], togri: m[2], sabab: m[3] };
}
