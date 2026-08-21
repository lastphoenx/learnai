"use client";

import type { ReactNode } from "react";
import { SpeechInputButton } from "@/components/SpeechInputButton";
import type { SttProvider } from "@/lib/api";

type Props = {
  label: string;
  language?: string;
  continuous?: boolean;
  sttProvider?: SttProvider;
  profileId?: string;
  onTranscript: (text: string, finalChunk: boolean) => void;
  onError?: (message: string) => void;
  children: ReactNode;
};

export function LabelWithSpeech({
  label,
  language,
  continuous,
  sttProvider,
  profileId,
  onTranscript,
  onError,
  children,
}: Props) {
  return (
    <label className="label-with-speech">
      <span className="label-with-speech-head">
        <span>{label}</span>
        <SpeechInputButton
          language={language}
          continuous={continuous}
          sttProvider={sttProvider}
          profileId={profileId}
          onTranscript={onTranscript}
          onError={onError}
        />
      </span>
      {children}
    </label>
  );
}
