export function formatKiSummary(byTask?: Record<string, { provider: string; model: string }>): string {
  if (!byTask || Object.keys(byTask).length === 0) {
    return "";
  }
  const counts: Record<string, number> = {};
  for (const row of Object.values(byTask)) {
    const p = (row.provider || "").trim().toLowerCase();
    if (!p) continue;
    counts[p] = (counts[p] || 0) + 1;
  }
  const parts = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([p, n]) => `${p} (${n})`);
  return parts.length ? parts.join(" · ") : "";
}
