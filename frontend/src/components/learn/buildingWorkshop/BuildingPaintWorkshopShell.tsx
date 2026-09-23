"use client";

import type { ReactNode } from "react";
import { BuildingObserverGuide } from "@/components/learn/buildingWorkshop/BuildingObserverGuide";
import { WorkshopShell } from "@/components/learn/buildingWorkshop/WorkshopShell";

type Props = {
  taskTitle?: string;
  taskPrompt?: string;
  instruction?: ReactNode;
  modelPanel: ReactNode;
  paintBlock?: ReactNode;
  actions?: ReactNode;
  footer?: ReactNode;
};

/** Kap. 5 — Gebäude drehen und sichtbare Flächen einfärben. */
export function BuildingPaintWorkshopShell({
  taskTitle,
  taskPrompt,
  instruction,
  modelPanel,
  paintBlock,
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
      workspace={modelPanel}
      aside={<BuildingObserverGuide />}
      belowWorkspace={
        paintBlock
          ? (
              <div className="building-views-projections building-paint-workshop-palette">
                {paintBlock}
              </div>
            )
          : undefined
      }
      actions={actions}
      footer={footer}
    />
  );
}
