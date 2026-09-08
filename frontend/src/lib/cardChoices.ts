const CASE_NAMES = ["Nominativ", "Genitiv", "Dativ", "Akkusativ"] as const;
const W_FALL_NAMES = ["Wer-Fall", "Wessen-Fall", "Wem-Fall", "Wen- oder Was-Fall"] as const;
const W_QUESTIONS = ["Wer?", "Wessen?", "Wem?", "Wen?", "Wen oder was?", "Wer oder was?"] as const;
const PRONOUN_CHOICES = ["er", "ihn", "ihm", "es"] as const;
const ARTICLE_ENDINGS = ["er", "en", "em", "es", "e", "n", "s", "den", "dem", "des", "der"] as const;

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
  const a = normalizeAnswer(answer).toLowerCase().replace(/\?+$/, "");
  if (["wer", "wessen", "wem", "wen"].includes(a)) return true;
  if (a.startsWith("wer") || a.startsWith("wessen") || a.startsWith("wem") || a.startsWith("wen")) {
    return true;
  }
  return false;
}

function matchesVerbQuestion(question: string, answer: string): boolean {
  const a = normalizeAnswer(answer).toLowerCase();
  if (a === "verb" && /verb|satzglied|markier/i.test(question)) return true;
  if (a === "satzglieder" && /satzglied/i.test(question)) return true;
  return false;
}

function matchesPronounAnswer(answer: string): boolean {
  return /^(er|ihn|ihm|es|sie|ihr)$/i.test(normalizeAnswer(answer));
}

function matchesArticleEndingAnswer(answer: string): boolean {
  return /^(er|en|em|es|e|n|s|den|dem|des|der)$/i.test(normalizeAnswer(answer));
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
    return ["Verb", "Satzglieder", "Subjekt", "Objekt"];
  }
  if (matchesPronounAnswer(answer)) return [...PRONOUN_CHOICES];
  if (matchesArticleEndingAnswer(answer)) return [...ARTICLE_ENDINGS];
  if (/^er\|ihn$/i.test(answer.replace(/\s+/g, ""))) {
    return ["er", "ihn", "ihm", "es"];
  }
  if (/^er$/i.test(normalizeAnswer(answer)) && /ersatzprobe|zeigt.*nominativ/i.test(question)) {
    return ["er", "ihn", "ihm", "es"];
  }
  return null;
}
