"use client";

import type { ReactNode } from "react";
import { BuildingObserverGuide } from "@/components/learn/buildingWorkshop/BuildingObserverGuide";

type Props = {
  taskTitle?: string;
  taskPrompt?: string;
  instruction?: ReactNode;
  modelPanel: ReactNode;
  decisionBlock?: ReactNode;
  projectionsBlock?: ReactNode;
  helpBlock?: ReactNode;
  actions?: ReactNode;
  footer?: ReactNode;
};

/** Layout-Vorlage RaumWerkstatt Kap. 3 — Ansichten eines Gebäudes. */
export function BuildingViewsWorkshopShell({
  taskTitle,
  taskPrompt,
  instruction,
  modelPanel,
  decisionBlock,
  projectionsBlock,
  helpBlock,
  actions,
  footer,
}: Props) {
  return (
    <div className="building-views-workshop stack">
      {(taskTitle || taskPrompt) && (
        <div className="building-views-taskbar">
          <div>
            {taskTitle ? <h3 className="building-views-task-title">{taskTitle}</h3> : null}
            {taskPrompt ? <p className="muted">{taskPrompt}</p> : null}
          </div>
        </div>
      )}

      {instruction ? (
        <div className="building-views-instruction" role="note">
          {instruction}
        </div>
      ) : null}

      <div className="building-views-work">
        <div className="building-views-work-stage">{modelPanel}</div>
        <div className="building-views-work-aside stack">
          <BuildingObserverGuide />
        </div>
      </div>

      {decisionBlock ? <div className="building-views-decision">{decisionBlock}</div> : null}

      {projectionsBlock ? (
        <div className="building-views-projections">
          <p className="building-views-mark-hint">
            <strong>Markiere die sichtbaren Quadrate.</strong> Tippe die Felder in den drei Ansichten an. Verdeckte
            Würfel zählen nicht — nur die äussere Silhouette.
          </p>
          {projectionsBlock}
        </div>
      ) : null}

      {helpBlock ? <div className="building-views-help">{helpBlock}</div> : null}

      {actions ? <div className="building-views-actions btnrow">{actions}</div> : null}

      {footer}
    </div>
  );
}
