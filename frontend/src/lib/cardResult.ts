/** Ergebnis aus einer Kartenfrage ziehen, z. B. «6 × 0.5» → «3». */

const NUM = String.raw`-?\d+(?:[.,]\d+)?`;
const EXPR = new RegExp(`(${NUM})\\s*([·×*xX+\\-−:÷/])\\s*(${NUM})`, "g");

function parseDeNumber(raw: string): number {
  return Number(raw.replace(",", "."));
}

function decimalPlaces(raw: string): number {
  const part = raw.replace(",", ".").split(".")[1];
  return part ? part.length : 0;
}

function formatDeNumber(value: number, left: string, right: string): string {
  if (!Number.isFinite(value)) return "";
  if (Math.abs(value - Math.round(value)) < 1e-9) return String(Math.round(value));
  const places = Math.min(6, Math.max(decimalPlaces(left) + decimalPlaces(right), 1));
  let out = value.toFixed(places).replace(/\.?0+$/, "");
  if (left.includes(",") || right.includes(",")) out = out.replace(".", ",");
  return out;
}

function evalExpr(left: string, op: string, right: string): string | null {
  const a = parseDeNumber(left);
  const b = parseDeNumber(right);
  if (!Number.isFinite(a) || !Number.isFinite(b)) return null;
  let n: number;
  if (op === "·" || op === "×" || op === "*" || op === "x" || op === "X") n = a * b;
  else if (op === "+") n = a + b;
  else if (op === "-" || op === "−") n = a - b;
  else if (op === ":" || op === "÷" || op === "/") {
    if (b === 0) return null;
    n = a / b;
  } else return null;
  const formatted = formatDeNumber(n, left, right);
  return formatted || null;
}

export function inferResultFromQuestion(question: string): string | null {
  const matches = [...question.matchAll(new RegExp(EXPR, "g"))];
  if (matches.length === 0) return null;
  const beforeBlank = matches.find((m) => {
    const after = question.slice((m.index ?? 0) + m[0].length);
    return /^\s*[=_—–-]/.test(after);
  });
  const chosen = beforeBlank ?? (matches.length === 1 ? matches[0] : matches[matches.length - 1]);
  return evalExpr(chosen[1], chosen[2], chosen[3]);
}

/** Stellt sicher, dass die Kartenrückseite mit «Ergebnis: …» beginnt, wenn berechenbar. */
export function answerWithVisibleResult(question: string, answer: string): string {
  const result = inferResultFromQuestion(question);
  if (!result) return answer;
  const trimmed = (answer || "").trim();
  if (/^ergebnis\s*:/i.test(trimmed)) return trimmed;
  return `Ergebnis: ${result}\n\n${trimmed}`;
}
