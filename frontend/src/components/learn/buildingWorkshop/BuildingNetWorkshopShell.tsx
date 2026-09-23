"use client";

import type { ReactNode } from "react";
import { WorkshopShell } from "@/components/learn/buildingWorkshop/WorkshopShell";

type Props = {
  taskTitle?: string;
  taskPrompt?: string;
  instruction?: ReactNode;
  gridPanel: ReactNode;
  previewAside?: ReactNode;
  actions?: ReactNode;
  footer?: ReactNode;
};

/** Kap. 2 Netze — Raster + Faltvorschau (Flächen-Farben). */
export function BuildingNetWorkshopShell({
  taskTitle,
  taskPrompt,
  instruction,
  gridPanel,
  previewAside,
  actions,
  footer,
}: Props) {
  return (
    <WorkshopShell
      task={
        taskTitle || taskPrompt
          ? (
              <div>
                {taskTitle ? <h3 className="building-views-task-title">{taskTitle}</h3> : null}
                {taskPrompt ? <p className="muted">{taskPrompt}</p> : null}
              </div>
            )
          : undefined
      }
      instruction={instruction}
      workspace={gridPanel}
      aside={previewAside}
      actions={actions}
      footer={footer}
    />
  );
}
