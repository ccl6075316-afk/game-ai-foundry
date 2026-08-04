import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { toRepoMediaRel } from "./toRepoMediaRel";

describe("toRepoMediaRel", () => {
  it("keeps projects/<slug> when abs is under ~/projects/<repo>", () => {
    const abs =
      "/Users/czl/projects/game-ai-foundry/projects/fishing-2d/output/visual-target/candidate_a.png";
    assert.equal(
      toRepoMediaRel(abs),
      "projects/fishing-2d/output/visual-target/candidate_a.png",
    );
  });

  it("does not slice at the parent folder named projects/", () => {
    const abs =
      "/Users/czl/projects/game-ai-foundry/projects/fishing-2d/output/visual-target/candidate_a.png";
    const rel = toRepoMediaRel(abs);
    assert.equal(rel.startsWith("projects/game-ai-foundry/"), false);
    assert.equal(rel.startsWith("projects/fishing-2d/"), true);
  });

  it("handles windows abs without a parent projects folder", () => {
    const abs =
      "E:\\game-ai-foundry\\projects\\black-whistle\\output\\visual-target\\candidate_a.png";
    assert.equal(
      toRepoMediaRel(abs),
      "projects/black-whistle/output/visual-target/candidate_a.png",
    );
  });

  it("passes through already-relative projects paths", () => {
    assert.equal(
      toRepoMediaRel(
        "projects/fishing-2d/output/visual-target/candidate_b.png",
      ),
      "projects/fishing-2d/output/visual-target/candidate_b.png",
    );
  });
});
