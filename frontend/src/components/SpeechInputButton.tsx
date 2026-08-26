"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { transcribeSpeech, type SttProvider } from "@/lib/api";

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

function usesServerStt(provider: SttProvider): boolean {
  return provider === "local" || provider === "openai";
}

type Props = {
  language?: string;
  /** Einmal sprechen (Titel) vs. bis erneut geklickt (Beschreibung) */
  continuous?: boolean;
  disabled?: boolean;
  sttProvider?: SttProvider;
  profileId?: string;
  onTranscript: (text: string, finalChunk: boolean) => void;
  onError?: (message: string) => void;
  title?: string;
};

export function SpeechInputButton({
  language = "de",
  continuous = false,
  disabled = false,
  sttProvider = "browser",
  profileId,
  onTranscript,
  onError,
  title,
}: Props) {
  const [listening, setListening] = useState(false);
  const [busy, setBusy] = useState(false);
  const [browserSupported, setBrowserSupported] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const pendingTranscriptRef = useRef("");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const serverMode = usesServerStt(sttProvider);

  useEffect(() => {
    setBrowserSupported(
      typeof window !== "undefined" &&
        Boolean(window.SpeechRecognition || window.webkitSpeechRecognition),
    );
  }, []);

  const stopMedia = useCallback(() => {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
    mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    mediaStreamRef.current = null;
  }, []);

  const stopBrowser = useCallback(() => {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
  }, []);

  const stop = useCallback(() => {
    stopBrowser();
    stopMedia();
    setListening(false);
  }, [stopBrowser, stopMedia]);

  useEffect(() => () => stop(), [stop]);

  async function uploadRecording(chunks: Blob[]) {
    if (!chunks.length) return;
    setBusy(true);
    try {
      const blob = new Blob(chunks, { type: chunks[0]?.type || "audio/webm" });
      const result = await transcribeSpeech(blob, language, profileId);
      const text = result.text.trim();
      if (text) onTranscript(text, true);
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "Transkription fehlgeschlagen");
    } finally {
      setBusy(false);
      chunksRef.current = [];
    }
  }

  async function startServerRecording() {
    if (!navigator.mediaDevices?.getUserMedia) {
      onError?.("Mikrofon nicht verfügbar");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      chunksRef.current = [];
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "";
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        void uploadRecording(chunksRef.current);
        mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
        mediaStreamRef.current = null;
        mediaRecorderRef.current = null;
        setListening(false);
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setListening(true);
    } catch {
      onError?.("Mikrofon-Zugriff verweigert");
      stopMedia();
    }
  }

  function startBrowserRecording() {
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Ctor) return;

    const recognition = new Ctor();
    recognition.lang = speechLocale(language);
    recognition.continuous = continuous;
    recognition.interimResults = true;
    pendingTranscriptRef.current = "";
    recognition.onresult = (event) => {
      let chunk = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        chunk += event.results[i][0].transcript;
      }
      const text = chunk.trim();
      if (!text) return;
      const isFinal = event.results[event.results.length - 1]?.isFinal ?? false;
      if (isFinal) {
        pendingTranscriptRef.current = "";
        onTranscript(text, true);
      } else {
        pendingTranscriptRef.current = text;
      }
    };
    recognition.onerror = (event) => {
      const code = event.error || "";
      if (code && code !== "aborted" && code !== "no-speech") {
        onError?.(
          code === "not-allowed" || code === "service-not-allowed"
            ? "Mikrofon-Zugriff verweigert"
            : "Spracheingabe fehlgeschlagen",
        );
      }
      stop();
    };
    recognition.onend = () => {
      const leftover = pendingTranscriptRef.current.trim();
      pendingTranscriptRef.current = "";
      recognitionRef.current = null;
      setListening(false);
      if (leftover) onTranscript(leftover, true);
    };
    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }

  function toggle() {
    if (disabled || busy) return;
    if (sttProvider === "anthropic") {
      onError?.("Anthropic bietet keine Spracherkennung");
      return;
    }
    if (listening) {
      if (serverMode) {
        mediaRecorderRef.current?.stop();
      } else {
        stopBrowser();
      }
      return;
    }
    if (serverMode) {
      void startServerRecording();
    } else {
      startBrowserRecording();
    }
  }

  if (!serverMode && !browserSupported) {
    return (
      <span className="speech-input-hint muted" title="Spracheingabe nicht unterstützt (Chrome/Edge)">
        🎤—
      </span>
    );
  }

  const active = listening || busy;

  return (
    <button
      type="button"
      className={`speech-input-btn${active ? " speech-input-btn-active" : ""}`}
      onMouseDown={(event) => event.preventDefault()}
      onClick={toggle}
      disabled={disabled || busy}
      title={
        title ||
        (busy
          ? "Transkribiere…"
          : serverMode
            ? continuous
              ? listening
                ? "Aufnahme beenden und transkribieren"
                : "Aufnehmen (lokale/OpenAI STT)"
              : listening
                ? "Aufnahme beenden"
                : "Sprechen und transkribieren"
            : continuous
              ? listening
                ? "Diktat beenden"
                : "Beschreibung diktieren (erneut klicken zum Stoppen)"
              : listening
                ? "Zuhören…"
                : "Titel diktieren")
      }
      aria-pressed={active}
      aria-label={active ? "Spracheingabe stoppen" : "Spracheingabe starten"}
    >
      {busy ? "…" : listening ? "⏹" : "🎤"}
    </button>
  );
}
