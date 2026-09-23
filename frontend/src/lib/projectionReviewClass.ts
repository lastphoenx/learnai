/** Lösungsüberlagerung — vier Fälle (RaumWerkstatt Kap. 3). */

export type ProjectionReviewClass = "" | "review-both" | "review-missing" | "review-extra";

export function projectionReviewClass(userFilled: boolean, expectedFilled: boolean): ProjectionReviewClass {
  if (userFilled && expectedFilled) return "review-both";
  if (!userFilled && expectedFilled) return "review-missing";
  if (userFilled && !expectedFilled) return "review-extra";
  return "";
}
