"use client";

import type { ExamTransfer } from "@/lib/api";

const SIGNAL_TEXT: Record<string, string> = {
  transfer_gap:
    "In der App deutlich besser als in der Prüfung — mögliches Transferproblem (Gelerntes nicht in der Prüfung abrufbar).",
  exam_better: "In der Prüfung besser als im App-Quiz — Übung in der App trifft die Prüfungsanforderungen evtl. nicht.",
  aligned: "App-Quiz und Prüfung liegen nah beieinander.",
  quiz_only: "Nur App-Quiz vorhanden — noch keine vergleichbare Prüfungsnote.",
  exam_only: "Nur Prüfungsergebnis — noch kein oder kein auswertbares App-Quiz.",
  insufficient_data: "Noch nicht genug Daten für einen Vergleich.",
};

type Props = {
  transfer: ExamTransfer;
  compact?: boolean;
};

export function TransferComparison({ transfer, compact }: Props) {
  const quiz =
    transfer.quiz_percent != null && transfer.quiz_total
      ? `App-Quiz ${transfer.quiz_correct}/${transfer.quiz_total} (${transfer.quiz_percent}%)`
      : transfer.quiz_total
        ? `App-Quiz ${transfer.quiz_correct}/${transfer.quiz_total}`
        : null;
  const exam =
    transfer.exam_percent != null && transfer.exam_max_score
      ? `Prüfung ${transfer.exam_score}/${transfer.exam_max_score} (${transfer.exam_percent}%)`
      : transfer.exam_score != null && transfer.exam_max_score
        ? `Prüfung ${transfer.exam_score}/${transfer.exam_max_score}`
        : null;

  if (!quiz && !exam) return null;

  const signal = transfer.signal || "insufficient_data";
  const isAlert = signal === "transfer_gap" || signal === "exam_better";

  return (
    <div className={`exam-transfer ${isAlert ? "exam-transfer-alert" : ""}`}>
      <strong>App vs. Prüfung</strong>
      <p className="muted" style={{ margin: "0.35rem 0 0" }}>
        {[quiz, exam].filter(Boolean).join(" · ")}
        {transfer.gap_percent != null && (
          <span>
            {" "}
            · Differenz {transfer.gap_percent > 0 ? "+" : ""}
            {transfer.gap_percent} %
          </span>
        )}
      </p>
      {!compact && SIGNAL_TEXT[signal] && (
        <p className="exam-transfer-hint muted" style={{ margin: "0.35rem 0 0", fontSize: "0.9rem" }}>
          {SIGNAL_TEXT[signal]}
        </p>
      )}
    </div>
  );
}
