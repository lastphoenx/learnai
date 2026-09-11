/** Trainer card filters — keep in sync with backend `app.core.trainer_cards`. */

export type CardFilter = "due" | "all" | "merk" | "mental" | "input" | "terms" | "practice";

export type TrainerCardLike = {
  card_key: string;
  kind?: string;
  card_role?: string;
  answer_type?: string;
  source?: string;
};

export function cardKind(card: { kind?: string }): string {
  return card.kind || "mental";
}

export function isTermCard(card: {
  card_role?: string;
  answer_type?: string;
  source?: string;
  kind?: string;
}): boolean {
  if (card.kind === "input") return false;
  if (card.card_role === "term" || card.card_role === "cloze") return true;
  if (card.source === "basiswissen") return true;
  return card.answer_type === "cloze";
}

export function filterTrainerCards<T extends TrainerCardLike>(
  cards: T[],
  filter: CardFilter,
  progress: Record<string, { due?: boolean } | undefined>,
  dueSessionKeys: Set<string>,
): T[] {
  if (filter === "practice") return [];
  let list = cards;
  if (filter === "due") {
    list = list.filter(
      (card) => progress[card.card_key]?.due !== false || dueSessionKeys.has(card.card_key),
    );
  } else if (filter === "merk" || filter === "mental" || filter === "input") {
    list = list.filter((card) => cardKind(card) === filter);
  } else if (filter === "terms") {
    list = list.filter((card) => isTermCard(card));
  }
  return list;
}

export function countTrainerCardFilters(
  cards: TrainerCardLike[],
  progress: Record<string, { due?: boolean } | undefined>,
): Record<"due" | "merk" | "mental" | "input" | "terms" | "all", number> {
  const dueKeys = new Set<string>();
  const dueList = cards.filter((card) => {
    if (progress[card.card_key]?.due !== false) {
      dueKeys.add(card.card_key);
      return true;
    }
    return false;
  });
  return {
    due: dueList.length,
    merk: cards.filter((c) => cardKind(c) === "merk").length,
    mental: cards.filter((c) => cardKind(c) === "mental").length,
    input: cards.filter((c) => cardKind(c) === "input").length,
    terms: cards.filter((c) => isTermCard(c)).length,
    all: cards.length,
  };
}

export function cardDeckTypeLabel(filter: CardFilter, card: { kind?: string }): string {
  if (filter === "terms") return "Fachbegriff-Karte";
  if (cardKind(card) === "merk") return "Merkkarte";
  if (cardKind(card) === "input") return "Eingabe-Karte";
  return "Kurzfrage";
}

export function cardJumpKind(filter: CardFilter, card: { kind?: string }): "input" | "merk" | "term" {
  if (filter === "terms") return "term";
  if (cardKind(card) === "input") return "input";
  return "merk";
}
