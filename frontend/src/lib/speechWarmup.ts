/** Mic- und STT-Warmup, sobald «Neue Einheit» geöffnet wird. */

type SpeechWindow = Window & {
  SpeechRecognition?: new () => { lang: string; continuous: boolean; interimResults: boolean; start: () => void; stop: () => void; onerror: unknown; onend: unknown };
  webkitSpeechRecognition?: new () => { lang: string; continuous: boolean; interimResults: boolean; start: () => void; stop: () => void; onerror: unknown; onend: unknown };
};

let micWarmup: Promise<void> | null = null;

export function warmupMicrophone(): Promise<void> {
  if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
    return Promise.resolve();
  }
  if (!micWarmup) {
    micWarmup = navigator.mediaDevices
      .getUserMedia({ audio: true })
      .then((stream) => {
        stream.getTracks().forEach((track) => track.stop());
      })
      .catch(() => undefined)
      .then(() => undefined);
  }
  return micWarmup;
}

export function warmupBrowserSpeech(language = "de"): void {
  if (typeof window === "undefined") return;
  const w = window as SpeechWindow;
  const Ctor = w.SpeechRecognition || w.webkitSpeechRecognition;
  if (!Ctor) return;
  try {
    const recognition = new Ctor();
    recognition.lang = language === "de" ? "de-DE" : language;
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onerror = () => undefined;
    recognition.onend = () => undefined;
  } catch {
    /* Engine lädt trotzdem bzw. Permission-Dialog ist schon offen. */
  }
}

export function warmupSpeechInput(opts?: {
  language?: string;
  serverStt?: boolean;
  warmupServer?: () => Promise<unknown>;
}): void {
  const language = opts?.language || "de";
  void warmupMicrophone().then(() => warmupBrowserSpeech(language));
  if (opts?.serverStt && opts.warmupServer) {
    void opts.warmupServer().catch(() => undefined);
  }
}
