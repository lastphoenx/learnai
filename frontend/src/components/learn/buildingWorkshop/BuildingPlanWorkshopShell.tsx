"use client";

import type { ReactNode } from "react";
import { BuildingObserverGuide } from "@/components/learn/buildingWorkshop/BuildingObserverGuide";
import { WorkshopShell } from "@/components/learn/buildingWorkshop/WorkshopShell";

type Props = {
  taskTitle?: string;
  taskPrompt?: string;
  instruction?: ReactNode;
  modelPanel: ReactNode;
  planBlock: ReactNode;
  actions?: ReactNode;
  footer?: ReactNode;
};

/** Kap. 4 Bauplan — Gebäude links, Höhenplan unten (ohne Sicht-Entscheid / Projektionen). */
export function BuildingPlanWorkshopShell({
  taskTitle,
  taskPrompt,
  instruction,
  modelPanel,
  planBlock,
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
        <div className="building-views-projections building-plan-workshop-plan">
          <p className="building-views-mark-hint">
            <strong>Höhenplan ausfüllen.</strong> Zeile unten = <em>vorne</em>, oben = <em>hinten</em>;
            links/rechts wie am Modell.
          </p>
          {planBlock}
        </div>
      }
      actions={actions}
      footer={footer}
    />
  );
}
