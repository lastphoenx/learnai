"use client";

import type { ReactNode } from "react";
import { SpeechInputButton } from "@/components/SpeechInputButton";

type Props = {
  label: string;
  language?: string;
  continuous?: boolean;
  onTranscript: (text: string, finalChunk: boolean) => void;
  children: ReactNode;
};

export function LabelWithSpeech({
  label,
  language,
  continuous,
  onTranscript,
  children,
}: Props) {
  return (
    <label className="label-with-speech">
      <span className="label-with-speech-head">
        <span>{label}</span>
        <SpeechInputButton language={language} continuous={continuous} onTranscript={onTranscript} />
      </span>
      {children}
    </label>
  );
}
