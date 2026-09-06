import type { LearnSummary } from "@/lib/api";

export type LearnProgressDisplay = {
  show: boolean;
  percent: number;
  label: string;
  detail: string | null;
  status: string;
};

export function learnProgressDisplay(
  moduleCount: number,
  progress?: LearnSummary | null,
): LearnProgressDisplay {
  if (moduleCount <= 0) {
    return { show: false, percent: 0, label: "", detail: null, status: "none" };
  }
  const status = progress?.status ?? "not_started";
  const modulesDone = progress?.modules_done ?? 0;
  const moduleTotal = progress?.module_count ?? moduleCount;
  const percent = status === "completed" ? 100 : (progress?.percent ?? 0);

  let label = "Noch nicht gestartet";
  if (status === "completed") label = "Abgeschlossen";
  else if (status === "in_progress" || percent > 0) {
    label = `${percent}% · ${modulesDone}/${moduleTotal} Blöcke`;
  }

  let detail: string | null = null;
  if (progress && progress.quiz_total > 0) {
    detail = `Quiz: ${progress.quiz_correct}/${progress.quiz_total} richtig`;
  }

  return { show: true, percent, label, detail, status };
}

type Props = {
  moduleCount: number;
  progress?: LearnSummary | null;
  compact?: boolean;
};

export function LearnProgressSummary({ moduleCount, progress, compact = false }: Props) {
  const info = learnProgressDisplay(moduleCount, progress);
  if (!info.show) return null;

  return (
    <div
      className={`learn-progress-summary${compact ? " learn-progress-summary--compact" : ""}`}
      aria-label={`Lernfortschritt: ${info.label}`}
    >
      <div className="learn-progress-head">
        <span className="learn-progress-label">{info.label}</span>
        {info.detail ? <span className="muted learn-progress-detail">{info.detail}</span> : null}
      </div>
      <div
        className={`learn-progress-bar${info.status === "completed" ? " is-complete" : ""}`}
        role="progressbar"
        aria-valuenow={info.percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <span className="learn-progress-fill" style={{ width: `${info.percent}%` }} />
      </div>
    </div>
  );
}
