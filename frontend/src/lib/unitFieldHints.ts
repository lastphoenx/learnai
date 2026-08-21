export type UnitFieldKey = "title" | "brief" | "subject" | "targetAge";

export type UnitFieldGuide = {
  placeholder: string;
  tip: string;
};

export type UnitFieldContext = {
  taskType: string;
  mathFocus: string;
  subject: string;
};

const BRIEF_STRUCTURE = `Thema und Ziel (1–2 Sätze):
Was soll geübt werden?

Inhaltliche Vorgaben für die KI:
- Welche Rechenarten / Aufgabentypen? (z.B. nur mit Dezimalzahlen)
- Schwierigkeit wie im Heft oder Stufe X.Y
- Was weglassen? (z.B. kein Buchcover, keine ISBN)

Optional: typische Fehler, Alltagsbeispiele aus dem Material`;

const MATH_FOCUS_BRIEF_LINES: Record<string, string> = {
  decimals:
    "- Aufgaben mit Dezimalzahlen in Kommaschreibweise (z.B. 3,08 + 1,5; 24,68 : 8)\n- Keine reinen Ganzzahl-Aufgaben ohne Dezimalbezug",
  fractions:
    "- Brüche darstellen, erweitern, kürzen, vergleichen und rechnen\n- Optional Bruch ↔ Dezimal (z.B. 3/4 = 0,75)",
  place_value:
    "- Stellenwert, Zehner/Hunderter/Tausender, Zahlenräume\n- Aufgaben passend zur Stufe",
  add_sub: "- Addition und Subtraktion im Fokus — Schwierigkeit und Zahlenraum nennen",
  mul_div: "- Multiplikation und Division im Fokus — auch mit Nachkommastellen wenn relevant",
  geometry: "- Formen, Umfang, Fläche, Winkel — Bezug zum Schulstoff",
  measures: "- Größen und Einheiten (mm, cm, m, g, kg, ml, l …) mit Umrechnungen",
  patterns: "- Zahlenreihen, Muster erkennen und fortsetzen",
  percent_ratio: "- Prozent, Verhältnisse, Dreisatz — mit konkreten Alltagsbeispielen",
  negative: "- Negative Zahlen: Darstellung und Rechnen im vereinbarten Zahlenraum",
};

const MATH_FOCUS_TITLES: Record<string, string> = {
  decimals: "Dezimalzahlen — rechnen mit Komma",
  fractions: "Bruchrechnen — Grundlagen",
  place_value: "Stellenwert und Zahlenräume",
  add_sub: "Addition und Subtraktion",
  mul_div: "Multiplikation und Division",
  geometry: "Geometrie — Formen und Flächen",
  measures: "Größen und Einheiten umrechnen",
  patterns: "Zahlenreihen und Muster",
  percent_ratio: "Prozent und Dreisatz",
  negative: "Negative Zahlen",
};

const LANGUAGE_BRIEF =
  "- Grammatik, Zeitformen oder Vokabeln wie im Schulstoff\n- Beispielsätze und typische Fehler aus dem Material";
const MGU_BRIEF =
  "- Themen aus MGU: Gesellschaft, Wirtschaft, Umwelt, Geschichte, Geografie\n- An das Schulheft und die Stufe orientieren";
const GERMAN_BRIEF =
  "- Rechtschreibung, Grammatik, Lesen oder Schreiben — je nach Schwerpunkt\n- Textsorten und Aufgaben wie im Heft";
const NATURE_BRIEF =
  "- Natur & Technik: Beobachtungen, Experimente, Fachbegriffe aus dem Stoff\n- An Lehrplan und Material halten";

function focusBriefLine(mathFocus: string): string {
  if (mathFocus.startsWith("lang_")) return LANGUAGE_BRIEF;
  if (mathFocus.startsWith("mgu_")) return MGU_BRIEF;
  if (mathFocus.startsWith("de_")) return GERMAN_BRIEF;
  if (mathFocus.startsWith("nt_")) return NATURE_BRIEF;
  return MATH_FOCUS_BRIEF_LINES[mathFocus] || "- Konkrete Inhalte und Schwierigkeit beschreiben";
}

function briefForInteractive(ctx: UnitFieldContext): string {
  const focusBlock = ctx.mathFocus
    ? `${focusBriefLine(ctx.mathFocus)}\n`
    : "- Konkrete Inhalte und Schwierigkeit beschreiben\n";

  return `Thema und Ziel (1–2 Sätze):
Was soll im Lerntrainer geübt werden?

Inhaltliche Vorgaben für die KI:
${focusBlock}- An knappes Schulheft / hochgeladene Fotos orientieren
- Was weglassen? (Buchcover, ISBN, Verlagsinfo)

Optional: typische Fehler, die vorkommen sollen`;
}

function briefForTask(ctx: UnitFieldContext): string {
  switch (ctx.taskType) {
    case "interactive":
      return briefForInteractive(ctx);
    case "math":
    case "workbook":
    case "practice":
      return BRIEF_STRUCTURE.replace(
        "Welche Rechenarten / Aufgabentypen? (z.B. nur mit Dezimalzahlen)",
        ctx.mathFocus && MATH_FOCUS_BRIEF_LINES[ctx.mathFocus]
          ? MATH_FOCUS_BRIEF_LINES[ctx.mathFocus].split("\n")[0].replace(/^- /, "")
          : "Welche Rechenarten / Aufgabentypen?",
      );
    case "vocab":
      return `Thema und Ziel:
Welche Wörter / Grammatik soll geübt werden?

Vorgaben für die KI:
- Sprache und Schwierigkeitsstufe
- Fokus: Bedeutung, Schreibung, Beispielsätze?
- Aus dem Material übernehmen, was im Heft steht`;
    case "quiz":
      return `Thema:
Worum geht es?

Vorgaben:
- Welche Fragentypen? (Verständnis, Anwendung, Rechenaufgaben)
- Schwierigkeit und Umfang
- Bezug zum hochgeladenen Material`;
    default:
      return BRIEF_STRUCTURE;
  }
}

function titlePlaceholder(ctx: UnitFieldContext): string {
  if (ctx.mathFocus && MATH_FOCUS_TITLES[ctx.mathFocus]) {
    return MATH_FOCUS_TITLES[ctx.mathFocus];
  }
  switch (ctx.taskType) {
    case "interactive":
      return "Bruchrechnen mit Dezimalstellen — Stufe 1.2";
    case "vocab":
      return "Französisch — Unité 4: La maison";
    case "math":
      return "Mathematik — Thema aus dem Heft";
    default:
      return "z.B. Einstieg ins Bruchrechnen";
  }
}

function titleTip(ctx: UnitFieldContext): string {
  return "Kurz und konkret: Thema + ggf. Stufe oder Kapitel. Der Titel ist die erste Zeile im KI-Prompt.";
}

function briefTip(ctx: UnitFieldContext): string {
  if (ctx.taskType === "interactive") {
    return "Strukturierter Auftrag = bessere Karten und Quiz. Platzhalter oben ist eine Vorlage — einfach überschreiben oder anpassen.";
  }
  return "Je klarer Ziel und Vorgaben, desto passender die KI-Aufbereitung. Fotos vom Heft danach hochladen.";
}

function subjectPlaceholder(ctx: UnitFieldContext): string {
  if (/mathe|math|rechnen/i.test(ctx.subject)) return ctx.subject;
  if (ctx.mathFocus || ["math", "workbook", "practice", "interactive"].includes(ctx.taskType)) {
    return "Mathematik";
  }
  return "Mathematik, Französisch, Grammatik…";
}

export function getUnitFieldGuide(field: UnitFieldKey, ctx: UnitFieldContext): UnitFieldGuide {
  switch (field) {
    case "title":
      return { placeholder: titlePlaceholder(ctx), tip: titleTip(ctx) };
    case "brief":
      return { placeholder: briefForTask(ctx), tip: briefTip(ctx) };
    case "subject":
      return {
        placeholder: subjectPlaceholder(ctx),
        tip: "Hilft der KI beim Fach — steuert die Schwerpunkt-Liste.",
      };
    case "targetAge":
      return {
        placeholder: "z.B. 13 oder 10–14",
        tip: "Alter oder Jahrgang — beeinflusst Sprache und Schwierigkeit der KI.",
      };
    default:
      return { placeholder: "", tip: "" };
  }
}
