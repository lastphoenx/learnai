import { describe, expect, it } from "vitest";
import { projectionReviewClass } from "@/lib/projectionReviewClass";

describe("projectionReviewClass", () => {
  it("leer+leer → keine Markierung", () => {
    expect(projectionReviewClass(false, false)).toBe("");
  });
  it("leer+belegt → fehlt noch", () => {
    expect(projectionReviewClass(false, true)).toBe("review-missing");
  });
  it("belegt+leer → zu viel", () => {
    expect(projectionReviewClass(true, false)).toBe("review-extra");
  });
  it("belegt+belegt → richtig gewählt", () => {
    expect(projectionReviewClass(true, true)).toBe("review-both");
  });
});
