import { describe, expect, it } from "vitest";
import { emptyProjectionDraft } from "@/lib/spatialSequence";

describe("spatialSequence", () => {
  it("emptyProjectionDraft starts empty", () => {
    expect(emptyProjectionDraft()).toEqual({});
  });
});
