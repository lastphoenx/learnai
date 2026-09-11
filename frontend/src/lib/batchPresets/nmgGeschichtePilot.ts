/** Referenz-Mapping NMG Schweizer Geschichte — Posten 14–26 (Pilot CT 135). */

import type { BatchImportPayload } from "@/lib/api";
import type { TrainerPresetId } from "@/lib/trainerPresets";

export type NmgPilotRow = {
  title: string;
  pageFrom: number;
  pageTo: number;
  posten: number;
  preset?: TrainerPresetId | "";
};

export const NMG_PILOT_INTRO = { from: 1, to: 5 };

export const NMG_PILOT_ROWS: NmgPilotRow[] = [
  { title: "Posten 14 — Zeitstrahl", pageFrom: 6, pageTo: 7, posten: 14 },
  { title: "Posten 15 — Altsteinzeit", pageFrom: 8, pageTo: 9, posten: 15 },
  { title: "Posten 16 — Mittel- und Jungsteinzeit", pageFrom: 10, pageTo: 11, posten: 16 },
  { title: "Posten 17 — Bronze- und Eisenzeit", pageFrom: 12, pageTo: 13, posten: 17 },
  { title: "Posten 18", pageFrom: 14, pageTo: 15, posten: 18 },
  { title: "Posten 19", pageFrom: 16, pageTo: 17, posten: 19 },
  { title: "Posten 20", pageFrom: 18, pageTo: 19, posten: 20 },
  { title: "Posten 21", pageFrom: 20, pageTo: 21, posten: 21 },
  { title: "Posten 22", pageFrom: 22, pageTo: 23, posten: 22 },
  { title: "Posten 23", pageFrom: 24, pageTo: 25, posten: 23 },
  { title: "Posten 24", pageFrom: 26, pageTo: 27, posten: 24 },
  { title: "Posten 25", pageFrom: 28, pageTo: 29, posten: 25 },
  { title: "Posten 26", pageFrom: 30, pageTo: 31, posten: 26 },
];

export const NMG_PILOT_META = {
  subject: "NMG",
  mathFocus: "nmg_history",
  targetAge: "11–12",
  language: "de",
  difficulty: 2,
  defaultPreset: "posten_compact" as TrainerPresetId,
  sharedBriefText:
    "NMG Schweizer Geschichte. Nur Stoff der jeweiligen Heft-Doppelseite. Jahreszahlen und Begriffe exakt aus dem Material — nichts dazuerfinden.",
  reviewTitle: "Lernzielkontrolle NMG Geschichte",
  reviewFrom: 1,
  reviewTo: 5,
};

export function buildNmgPilotPayload(profileId?: string): BatchImportPayload {
  return {
    subject: NMG_PILOT_META.subject,
    math_focus: NMG_PILOT_META.mathFocus,
    target_age: NMG_PILOT_META.targetAge,
    language: NMG_PILOT_META.language,
    difficulty: NMG_PILOT_META.difficulty,
    task_type: "interactive",
    default_preset: NMG_PILOT_META.defaultPreset,
    profile_id: profileId,
    shared_brief_pages: [1, 2, 3, 4, 5],
    shared_brief_text: NMG_PILOT_META.sharedBriefText,
    units: NMG_PILOT_ROWS.map((row) => ({
      title: row.title,
      page_from: row.pageFrom,
      page_to: row.pageTo,
      posten: row.posten,
      preset: row.preset || undefined,
      brief_suffix: `Leitfrage der Doppelseite. Nur Stoff Posten ${row.posten}.`,
    })),
    review_unit: {
      title: NMG_PILOT_META.reviewTitle,
      page_from: NMG_PILOT_META.reviewFrom,
      page_to: NMG_PILOT_META.reviewTo,
      preset: "exam_review",
    },
  };
}
