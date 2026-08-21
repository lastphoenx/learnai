"use client";

import type { ReactNode } from "react";

type Props = {
  tip: string;
  show?: boolean;
};

export function UnitFieldGuide({ tip, show = true }: Props) {
  if (!show || !tip) return null;
  return <p className="unit-field-guide muted">{tip}</p>;
}

type FieldWrapProps = {
  label: ReactNode;
  tip: string;
  showTip?: boolean;
  children: ReactNode;
};

export function UnitFieldWrap({ label, tip, showTip = true, children }: FieldWrapProps) {
  return (
    <label className="unit-field-wrap">
      {label}
      {children}
      <UnitFieldGuide tip={tip} show={showTip} />
    </label>
  );
}
