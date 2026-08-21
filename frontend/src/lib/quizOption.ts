/** Einheitliche Anzeige für Quiz-Optionen (ohne doppeltes a) A)). */
export function formatQuizOption(option: string, index: number): string {
  const label = option.replace(/^[a-d]\)\s*/i, "").trim();
  const letter = String.fromCharCode(65 + index);
  return `${letter}) ${label}`;
}

/** Zeilenumbrüche zwischen Rechenweg-Varianten sichtbar machen. */
export function formatQuizExplanation(text: string): string {
  return text
    .replace(/\. Variante /g, ".\n\nVariante ")
    .replace(/ (?=Variante [2-9])/g, "\n\n");
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
