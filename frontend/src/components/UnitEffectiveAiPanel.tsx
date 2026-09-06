"use client";

import { useEffect, useState } from "react";
import { fetchAiEffective, type LastAiRun, type TaskCatalogItem } from "@/lib/api";
import {
  aiSourceBadgeClass,
  providerLabel,
  unitAiTaskKeys,
} from "@/lib/unitAiTasks";

type EffectiveTask = {
  provider: string;
  effective_model: string;
  source?: string;
  source_label?: string;
};

type Props = {
  unitId: string;
  taskType?: string;
  sourceCount: number;
  lastAiRun?: LastAiRun | null;
  formatWhen?: (iso: string | null | undefined) => string | null;
};

function providerBadgeClass(provider: string): string {
  if (provider === "openai") return "unit-effective-ai-badge--openai";
  if (provider === "anthropic") return "unit-effective-ai-badge--anthropic";
  if (provider === "ollama") return "unit-effective-ai-badge--ollama";
  return "unit-effective-ai-badge--neutral";
}

function formatRunStats(stats: LastAiRun["stats"]): string | null {
  if (!stats) return null;
  const parts: string[] = [];
  if (typeof stats.modules === "number") parts.push(`${stats.modules} Blöcke`);
  if (typeof stats.cards === "number") parts.push(`${stats.cards} Karten`);
  if (typeof stats.questions === "number") parts.push(`${stats.questions} Quizfragen`);
  return parts.length ? parts.join(" · ") : null;
}

export function UnitEffectiveAiPanel({
  unitId,
  taskType,
  sourceCount,
  lastAiRun,
  formatWhen,
}: Props) {
  const [tasks, setTasks] = useState<Record<string, EffectiveTask> | null>(null);
  const [catalog, setCatalog] = useState<TaskCatalogItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetchAiEffective(unitId)
      .then((data) => {
        if (cancelled) return;
        setTasks(data.tasks || null);
        setCatalog(data.task_catalog || []);
      })
      .catch(() => {
        if (!cancelled) {
          setTasks(null);
          setCatalog([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [unitId]);

  const keys = unitAiTaskKeys(taskType, sourceCount);
  const catalogByKey = Object.fromEntries(catalog.map((item) => [item.key, item]));

  if (!tasks) return null;

  const rows = keys
    .map((key) => {
      const task = tasks[key];
      const cat = catalogByKey[key];
      if (!task) return null;
      return { key, task, cat };
    })
    .filter(Boolean) as { key: string; task: EffectiveTask; cat?: TaskCatalogItem }[];

  if (rows.length === 0) return null;

  const primary = rows[0];
  const lastRunRows = lastAiRun?.tasks
    ? keys
        .map((key) => {
          const run = lastAiRun.tasks?.[key];
          if (!run) return null;
          const cat = catalogByKey[key];
          return { key, run, cat };
        })
        .filter(Boolean) as { key: string; run: { provider: string; model: string }; cat?: TaskCatalogItem }[]
    : [];
  const lastRunWhen = formatWhen?.(lastAiRun?.finished_at) || null;
  const lastRunStats = formatRunStats(lastAiRun?.stats);

  return (
    <div className="unit-ai-config stack">
      {lastRunRows.length > 0 ? (
        <details className="unit-effective-ai unit-effective-ai--last-run">
          <summary className="unit-effective-ai-summary">
            <span className="unit-effective-ai-chevron" aria-hidden="true">
              ›
            </span>
            <span className="unit-effective-ai-badge unit-effective-ai-badge--last">Zuletzt generiert</span>
            <span className="unit-effective-ai-primary">
              {providerLabel(lastRunRows[0].run.provider)} · {lastRunRows[0].run.model}
            </span>
            {lastRunWhen ? <span className="unit-effective-ai-more">{lastRunWhen}</span> : null}
          </summary>
          <ul className="unit-effective-ai-list">
            {lastRunRows.map(({ key, run, cat }) => (
              <li key={`run-${key}`} className="unit-effective-ai-item unit-effective-ai-item--flat">
                <strong>{cat?.label || key}</strong>
                <span className={`unit-effective-ai-row-badge ${providerBadgeClass(run.provider)}`}>
                  {providerLabel(run.provider)}
                </span>
                <span className="unit-effective-ai-row-model">{run.model}</span>
              </li>
            ))}
          </ul>
          {lastRunStats ? <p className="muted unit-ai-run-stats">{lastRunStats}</p> : null}
        </details>
      ) : null}

      <details className="unit-effective-ai">
        <summary className="unit-effective-ai-summary">
          <span className="unit-effective-ai-chevron" aria-hidden="true">
            ›
          </span>
          <span className={`unit-effective-ai-badge ${providerBadgeClass(primary.task.provider)}`}>
            Aktuelle KI-Konfiguration
          </span>
          <span className="unit-effective-ai-primary">
            {providerLabel(primary.task.provider)} · {primary.task.effective_model}
          </span>
          {rows.length > 1 ? (
            <span className="unit-effective-ai-more">+{rows.length - 1} Aufgabe{rows.length > 2 ? "n" : ""}</span>
          ) : null}
          <span className="unit-effective-ai-hint muted">Details aufklappen</span>
        </summary>
        <ul className="unit-effective-ai-list">
          {rows.map(({ key, task, cat }) => (
            <li key={key} className="unit-effective-ai-item">
              <details className="unit-effective-ai-row">
                <summary>
                  <span className="unit-effective-ai-row-chevron" aria-hidden="true">
                    ›
                  </span>
                  <strong>{cat?.label || key}</strong>
                  <span className={`unit-ai-source ${aiSourceBadgeClass(task.source)}`} title={task.source_label}>
                    {task.source_label || task.source || "?"}
                  </span>
                  <span className={`unit-effective-ai-row-badge ${providerBadgeClass(task.provider)}`}>
                    {providerLabel(task.provider)}
                  </span>
                  <span className="unit-effective-ai-row-model">{task.effective_model}</span>
                </summary>
                {cat?.why ? <p className="muted unit-effective-ai-why">{cat.why}</p> : null}
              </details>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
