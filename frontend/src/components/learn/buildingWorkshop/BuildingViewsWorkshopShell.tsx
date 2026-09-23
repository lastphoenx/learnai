"use client";

import type { ReactNode } from "react";
import { BuildingObserverGuide } from "@/components/learn/buildingWorkshop/BuildingObserverGuide";
import { WorkshopShell } from "@/components/learn/buildingWorkshop/WorkshopShell";

type Props = {
  taskTitle?: string;
  taskPrompt?: string;
  instruction?: ReactNode;
  modelPanel: ReactNode;
  observerGuide?: ReactNode;
  decisionBlock?: ReactNode;
  projectionsBlock?: ReactNode;
  projectionsHint?: ReactNode;
  helpBlock?: ReactNode;
  actions?: ReactNode;
  footer?: ReactNode;
};

/** Domänenspezifische Kap.-3-Hülle auf {@link WorkshopShell}. */
export function BuildingViewsWorkshopShell({
  taskTitle,
  taskPrompt,
  instruction,
  modelPanel,
  observerGuide,
  decisionBlock,
  projectionsBlock,
  projectionsHint,
  helpBlock,
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
      aside={observerGuide ?? <BuildingObserverGuide />}
      interaction={decisionBlock}
      belowWorkspace={
        projectionsBlock
          ? (
              <div className="building-views-projections">
                {projectionsHint ?? (
                  <p className="building-views-mark-hint">
                    <strong>Markiere die sichtbaren Quadrate.</strong> Tippe die Felder in den drei Ansichten an.
                    Verdeckte Würfel zählen nicht — nur die äussere Silhouette.
                  </p>
                )}
                {projectionsBlock}
              </div>
            )
          : undefined
      }
      help={helpBlock}
      actions={actions}
      footer={footer}
    />
  );
}
