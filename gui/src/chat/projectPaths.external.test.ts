import assert from "node:assert/strict";
import test from "node:test";

import {
  externalBriefRel,
  isExternalBriefRel,
  isIsolatedBriefRel,
  parseExternalBriefId,
  planTargetsFromBrief,
  planTargetsFromExternalEntry,
  projectRootFromBriefRel,
  sameProjectRoot,
  type ExternalProjectEntry,
} from "./projectPaths";

const sampleEntry: ExternalProjectEntry = {
  id: "ext_a1b2c3d4",
  display_name: "fishing-2d",
  root_abs: "/tmp/fishing-2d",
  godot_rel: ".",
  brief_rel: "brief.json",
  added_at: "2026-07-27T00:00:00+00:00",
};

const gameSubEntry: ExternalProjectEntry = {
  ...sampleEntry,
  id: "ext_game01",
  display_name: "foundry-style",
  godot_rel: "game",
};

test("isExternalBriefRel matches virtual brief keys", () => {
  assert.equal(isExternalBriefRel("external:ext_abc/brief.json"), true);
  assert.equal(isExternalBriefRel("EXTERNAL:ext_abc/brief.json"), true);
  assert.equal(isExternalBriefRel("projects/foo/brief.json"), false);
  assert.equal(isExternalBriefRel("external:ext_abc/output/x"), false);
});

test("parseExternalBriefId and externalBriefRel round-trip", () => {
  const rel = externalBriefRel("ext_deadbeef");
  assert.equal(rel, "external:ext_deadbeef/brief.json");
  assert.equal(parseExternalBriefId(rel), "ext_deadbeef");
  assert.equal(parseExternalBriefId("projects/x/brief.json"), null);
});

test("planTargetsFromExternalEntry root godot layout", () => {
  const t = planTargetsFromExternalEntry(sampleEntry);
  assert.equal(t.briefRel, "external:ext_a1b2c3d4/brief.json");
  assert.equal(t.projectRootRel, "external:ext_a1b2c3d4");
  assert.equal(t.godotProjectRel, "external:ext_a1b2c3d4");
  assert.equal(t.manifestRel, "external:ext_a1b2c3d4/pipeline/manifest.json");
  assert.equal(t.outputDirRel, "external:ext_a1b2c3d4/output");
  assert.equal(t.isolated, true);
  assert.equal(t.slug, "fishing-2d");
});

test("planTargetsFromExternalEntry game/ subdir godot", () => {
  const t = planTargetsFromExternalEntry(gameSubEntry);
  assert.equal(t.godotProjectRel, "external:ext_game01/game");
  assert.equal(t.slug, "foundry-style");
});

test("isIsolatedBriefRel includes external brief keys", () => {
  assert.equal(isIsolatedBriefRel("external:ext_x/brief.json"), true);
  assert.equal(isIsolatedBriefRel("projects/foo/brief.json"), true);
  assert.equal(isIsolatedBriefRel("resources/game-brief.json"), false);
});

test("sameProjectRoot treats external ids as roots", () => {
  assert.equal(projectRootFromBriefRel("external:ext_a/brief.json"), "external:ext_a");
  assert.equal(
    sameProjectRoot("external:ext_a/brief.json", "external:ext_a/output/x.png"),
    true,
  );
  assert.equal(
    sameProjectRoot("external:ext_a/brief.json", "external:ext_b/brief.json"),
    false,
  );
});

test("planTargetsFromBrief rejects external virtual keys", () => {
  assert.throws(
    () => planTargetsFromBrief("external:ext_x/brief.json"),
    /planTargetsFromExternalEntry/,
  );
});
