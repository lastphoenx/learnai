"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
};

type SpeechRecognitionEventLike = {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      isFinal: boolean;
      0: { transcript: string };
    };
  };
};

declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognitionLike;
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
  }
}

function speechLocale(language: string): string {
  const map: Record<string, string> = {
    de: "de-DE",
    fr: "fr-FR",
    it: "it-IT",
    en: "en-US",
  };
  return map[language] || language;
}

type Props = {
  language?: string;
  /** Einmal sprechen (Titel) vs. bis erneut geklickt (Beschreibung) */
  continuous?: boolean;
  disabled?: boolean;
  onTranscript: (text: string, finalChunk: boolean) => void;
  title?: string;
};

export function SpeechInputButton({
  language = "de",
  continuous = false,
  disabled = false,
  onTranscript,
  title,
}: Props) {
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  useEffect(() => {
    setSupported(
      typeof window !== "undefined" &&
        Boolean(window.SpeechRecognition || window.webkitSpeechRecognition),
    );
  }, []);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    setListening(false);
  }, []);

  useEffect(() => () => stop(), [stop]);

  function toggle() {
    if (!supported || disabled) return;
    if (listening) {
      stop();
      return;
    }

    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Ctor) return;

    const recognition = new Ctor();
    recognition.lang = speechLocale(language);
    recognition.continuous = continuous;
    recognition.interimResults = true;
    recognition.onresult = (event) => {
      let chunk = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        chunk += event.results[i][0].transcript;
      }
      if (!chunk.trim()) return;
      const isFinal = event.results[event.results.length - 1]?.isFinal ?? false;
      onTranscript(chunk, isFinal);
    };
    recognition.onerror = () => stop();
    recognition.onend = () => {
      recognitionRef.current = null;
      setListening(false);
    };
    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }

  if (!supported) {
    return (
      <span className="speech-input-hint muted" title="Spracheingabe nicht unterstützt (Chrome/Edge)">
        🎤—
      </span>
    );
  }

  return (
    <button
      type="button"
      className={`speech-input-btn${listening ? " speech-input-btn-active" : ""}`}
      onClick={toggle}
      disabled={disabled}
      title={
        title ||
        (continuous
          ? listening
            ? "Diktat beenden"
            : "Beschreibung diktieren (erneut klicken zum Stoppen)"
          : listening
            ? "Zuhören…"
            : "Titel diktieren")
      }
      aria-pressed={listening}
      aria-label={listening ? "Spracheingabe stoppen" : "Spracheingabe starten"}
    >
      {listening ? "⏹" : "🎤"}
    </button>
  );
}
