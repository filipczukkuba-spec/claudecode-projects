export function norm(s: string): string {
  return s
    .toLowerCase()
    .replace(/ą/g, "a").replace(/ć/g, "c").replace(/ę/g, "e")
    .replace(/ł/g, "l").replace(/ń/g, "n").replace(/ó/g, "o")
    .replace(/ś/g, "s").replace(/ź/g, "z").replace(/ż/g, "z")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function matchScore(query: string, target: string): number {
  const q = norm(query);
  const t = norm(target);
  if (q === t) return 1;
  if (t.includes(q) || q.includes(t)) return 0.9;
  const qTokens = q.split(" ").filter(Boolean);
  const tTokens = t.split(" ").filter(Boolean);
  const matched = qTokens.filter((qt) =>
    tTokens.some((tt) => tt.includes(qt) || qt.includes(tt))
  );
  return qTokens.length > 0 ? matched.length / qTokens.length : 0;
}

export const MATCH_THRESHOLD = 0.6;
