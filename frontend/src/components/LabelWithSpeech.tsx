"use client";

import type { ReactNode } from "react";
import { SpeechInputButton } from "@/components/SpeechInputButton";
import type { SttProvider } from "@/lib/api";

type Props = {
  label: string;
  htmlFor?: string;
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
  htmlFor,
  language,
  continuous,
  sttProvider,
  profileId,
  onTranscript,
  onError,
  children,
}: Props) {
  return (
    <div className="label-with-speech">
      <div className="label-with-speech-head">
        {htmlFor ? <label htmlFor={htmlFor}>{label}</label> : <span>{label}</span>}
        <SpeechInputButton
          language={language}
          continuous={continuous}
          sttProvider={sttProvider}
          profileId={profileId}
          onTranscript={onTranscript}
          onError={onError}
        />
      </div>
      {children}
    </div>
  );
}
