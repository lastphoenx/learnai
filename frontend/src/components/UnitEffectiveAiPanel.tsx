"use client";

import { useEffect, useState } from "react";
import { fetchAiEffective, type TaskCatalogItem } from "@/lib/api";
import { providerLabel, unitAiTaskKeys } from "@/lib/unitAiTasks";

type EffectiveTask = {
  provider: string;
  effective_model: string;
};

type Props = {
  unitId: string;
  taskType?: string;
  sourceCount: number;
};

function providerBadgeClass(provider: string): string {
  if (provider === "openai") return "unit-effective-ai-badge--openai";
  if (provider === "anthropic") return "unit-effective-ai-badge--anthropic";
  if (provider === "ollama") return "unit-effective-ai-badge--ollama";
  return "unit-effective-ai-badge--neutral";
}

export function UnitEffectiveAiPanel({ unitId, taskType, sourceCount }: Props) {
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

  return (
    <details className="unit-effective-ai">
      <summary className="unit-effective-ai-summary">
        <span className="unit-effective-ai-chevron" aria-hidden="true">
          ›
        </span>
        <span className={`unit-effective-ai-badge ${providerBadgeClass(primary.task.provider)}`}>
          Aktive KI-Modelle
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
  );
}
