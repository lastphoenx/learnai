import { describe, expect, it } from "vitest";
import { netFoldHintAllowed } from "@/lib/workshop/netBuildWorkshopGating";

describe("netFoldHintAllowed", () => {
  it("build: erst bei 6 Feldern", () => {
    expect(netFoldHintAllowed({ validateMode: false, validatePhase: "inspect", selectedCount: 5 })).toBe(false);
    expect(netFoldHintAllowed({ validateMode: false, validatePhase: "inspect", selectedCount: 6 })).toBe(true);
  });

  it("validate: erst in Entscheid-Phase", () => {
    expect(netFoldHintAllowed({ validateMode: true, validatePhase: "inspect", selectedCount: 6 })).toBe(false);
    expect(netFoldHintAllowed({ validateMode: true, validatePhase: "decide", selectedCount: 6 })).toBe(true);
  });
});
