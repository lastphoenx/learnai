/** Einheitliche Anzeige für Quiz-Optionen (ohne doppeltes a) A)). */
export function formatQuizOption(option: string, index: number): string {
  const label = option.replace(/^[a-d]\)\s*/i, "").trim();
  const letter = String.fromCharCode(65 + index);
  return `${letter}) ${label}`;
}

/** Zeilenumbrüche zwischen Rechenweg-Varianten sichtbar machen. */
export function formatQuizExplanation(text: string): string {
  return text
    .replace(/(=\s*-?\d+(?:[.,]\d+)?)\s*,\s*(?=-?\d+(?:[.,]\d+)?\s*[·×*+\-−:÷/])/g, "$1.\nDann ")
    .replace(/\. Variante /g, ".\n\nVariante ")
    .replace(/ (?=Variante [2-9])/g, "\n\n");
}

export type QuizExplanationVariant = {
  index: number;
  label: string;
  badge: "heft" | "alt";
  body: string;
};

const VARIANT_HEAD = /Variante\s+(\d+)\s*(?:\(([^)]*)\))?\s*:/gi;

export function splitQuizExplanation(text: string): {
  preamble: string;
  variants: QuizExplanationVariant[];
} {
  const src = formatQuizExplanation(text || "").trim();
  if (!src) return { preamble: "", variants: [] };
  const matches = [...src.matchAll(new RegExp(VARIANT_HEAD.source, "gi"))];
  if (matches.length === 0) {
    return { preamble: "", variants: [{ index: 1, label: "", badge: "heft", body: src }] };
  }
  const preamble = src.slice(0, matches[0].index ?? 0).trim();
  const variants = matches.map((match, i) => {
    const start = (match.index ?? 0) + match[0].length;
    const end = i + 1 < matches.length ? (matches[i + 1].index ?? src.length) : src.length;
    return {
      index: Number(match[1]),
      label: (match[2] || "").trim(),
      badge: i === 0 ? "heft" : "alt",
      body: src.slice(start, end).trim(),
    };
  });
  return { preamble, variants };
}

export function splitQuizExplanationVariants(text: string): QuizExplanationVariant[] {
  return splitQuizExplanation(text).variants;
}

export function quizOptionClassName(
  index: number,
  selected: number | null,
  answerResult: { correct: boolean; correct_index: number } | null,
): string {
  let cls = "learn-quiz-option";
  if (!answerResult) {
    if (selected === index) cls += " selected";
    return cls;
  }
  if (selected === index) cls += " picked";
  if (selected === index) {
    cls += answerResult.correct ? " correct" : " wrong";
  } else if (!answerResult.correct && index === answerResult.correct_index) {
    cls += " correct";
  }
  return cls;
}
