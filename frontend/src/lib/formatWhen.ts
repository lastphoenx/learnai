/** Zeitstempel für die Schweiz (Europe/Zurich), konsistent mit der Einheiten-Detailseite. */
export function formatZurich(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString("de-CH", {
    timeZone: "Europe/Zurich",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** KI-Zeile für Batch-Karten: Pipeline/Modell + lokale Zeit aus finished_at. */
export function formatLastAiRunLine(run: {
  summary?: string | null;
  finished_at?: string | null;
} | null | undefined): string | null {
  if (!run?.summary && !run?.finished_at) return null;
  const when = formatZurich(run.finished_at);
  if (run.summary) {
    const base = run.summary.replace(/ · \d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?$/, "");
    if (when) return `${base} · ${when}`;
    return run.summary;
  }
  return when;
}
