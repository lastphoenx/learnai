const CASE_NAMES = ["Nominativ", "Genitiv", "Dativ", "Akkusativ"] as const;
const W_FALL_NAMES = ["Wer-Fall", "Wessen-Fall", "Wem-Fall", "Wen- oder Was-Fall"] as const;
const W_QUESTIONS = ["Wer oder was?", "Wessen?", "Wem?", "Wen oder was?"] as const;

function normalizeAnswer(answer: string): string {
  return answer.split("|")[0]?.trim() || "";
}

function matchesCaseAnswer(answer: string): boolean {
  return /^(nominativ|genitiv|dativ|akkusativ|nom\.?|gen\.?|dat\.?|akk\.?)$/i.test(
    normalizeAnswer(answer),
  );
}

function matchesWFallAnswer(answer: string): boolean {
  return /fall$/i.test(normalizeAnswer(answer)) || /^wen-? oder was-?fall$/i.test(normalizeAnswer(answer));
}

function matchesWQuestionAnswer(answer: string): boolean {
  const a = normalizeAnswer(answer).toLowerCase();
  return a.startsWith("wer") || a.startsWith("wessen") || a.startsWith("wem") || a.startsWith("wen");
}

function matchesVerbQuestion(question: string, answer: string): boolean {
  const a = normalizeAnswer(answer).toLowerCase();
  if (a !== "verb") return false;
  return /verb|satzglied|markier/i.test(question);
}

/** Einzel-Lücke mit bekannter Antwortmenge → Buttons statt Cloze-Tippen. */
export function shouldUseCardChoices(question: string, answer: string): boolean {
  const choices = inferCardChoices(question, answer);
  if (!choices) return false;
  const blanks = question.match(/___/g)?.length ?? 0;
  if (blanks === 0) return true;
  const parts = answer
    .split("|")
    .map((part) => part.trim())
    .filter(Boolean);
  return blanks === 1 && parts.length === 1;
}

/** Lückentext in Choice-Aufgaben lesbar machen (Antwort kommt per Klick). */
export function formatChoiceQuestion(question: string): string {
  return question.replace(/___+/g, "…");
}

/** Endliche Antwortmengen → Klick-Auswahl statt freies Tippen. */
export function inferCardChoices(question: string, answer: string): string[] | null {
  if (!answer?.trim()) return null;
  if (matchesCaseAnswer(answer)) return [...CASE_NAMES];
  if (matchesWFallAnswer(answer)) return [...W_FALL_NAMES];
  if (matchesWQuestionAnswer(answer)) return [...W_QUESTIONS];
  if (matchesVerbQuestion(question, answer)) {
    return ["Verb", "Subjekt", "Objekt", "Präposition"];
  }
  if (/^er\|ihn$/i.test(answer.replace(/\s+/g, ""))) {
    return ["er", "ihn", "ihm", "des"];
  }
  if (/^er$/i.test(normalizeAnswer(answer)) && /ersatzprobe|zeigt.*nominativ/i.test(question)) {
    return ["er", "ihn", "ihm", "es"];
  }
  return null;
}
