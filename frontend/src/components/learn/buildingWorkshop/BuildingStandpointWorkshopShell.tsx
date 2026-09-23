"use client";

import type { ReactNode } from "react";
import { BuildingObserverGuide } from "@/components/learn/buildingWorkshop/BuildingObserverGuide";
import { WorkshopShell } from "@/components/learn/buildingWorkshop/WorkshopShell";

type Props = {
  taskTitle?: string;
  taskPrompt?: string;
  instruction?: ReactNode;
  modelPanel: ReactNode;
  planAside?: ReactNode;
  choiceBlock?: ReactNode;
  actions?: ReactNode;
  footer?: ReactNode;
};

/** Kap. 6 Standort — 3D mit 👁-Markern, Plan im Seitenbereich, Auswahl unten. */
export function BuildingStandpointWorkshopShell({
  taskTitle,
  taskPrompt,
  instruction,
  modelPanel,
  planAside,
  choiceBlock,
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
      aside={
        <div className="stack">
          <BuildingObserverGuide />
          {planAside}
        </div>
      }
      belowWorkspace={
        choiceBlock
          ? (
              <div className="building-views-projections building-standpoint-workshop-choice">
                <p className="building-views-mark-hint">
                  <strong>Standpunkt wählen.</strong> Tippe einen 👁-Marker in der 3D-Szene oder wähle in der Liste.
                </p>
                {choiceBlock}
              </div>
            )
          : undefined
      }
      actions={actions}
      footer={footer}
    />
  );
}
