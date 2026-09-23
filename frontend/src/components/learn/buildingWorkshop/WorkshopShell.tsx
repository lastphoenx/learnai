"use client";

import type { ReactNode } from "react";

/** Generisches 2-Spalten-Workshop-Layout (ohne domänenspezifische Texte). */
export type WorkshopShellProps = {
  task?: ReactNode;
  instruction?: ReactNode;
  workspace: ReactNode;
  aside?: ReactNode;
  interaction?: ReactNode;
  belowWorkspace?: ReactNode;
  help?: ReactNode;
  actions?: ReactNode;
  footer?: ReactNode;
};

export function WorkshopShell({
  task,
  instruction,
  workspace,
  aside,
  interaction,
  belowWorkspace,
  help,
  actions,
  footer,
}: WorkshopShellProps) {
  return (
    <div className="building-views-workshop stack">
      {task ? <div className="building-views-taskbar">{task}</div> : null}
      {instruction ? (
        <div className="building-views-instruction" role="note">
          {instruction}
        </div>
      ) : null}
      <div className="building-views-work">
        <div className="building-views-work-stage">{workspace}</div>
        {aside ? <div className="building-views-work-aside stack">{aside}</div> : null}
      </div>
      {interaction ? <div className="building-views-decision">{interaction}</div> : null}
      {belowWorkspace ?? null}
      {help ? <div className="building-views-help">{help}</div> : null}
      {actions ? <div className="building-views-actions btnrow">{actions}</div> : null}
      {footer}
    </div>
  );
}
