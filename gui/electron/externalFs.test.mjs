import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import {
  absForResolved,
  cliArgForResolved,
  isExternalVirtualRel,
  manifestBelongsToBrief,
  normalizeRepoRel,
  parseExternalVirtual,
  projectRootKeyFromBriefRel,
  resolveExternalAbs,
} from "./externalFs.mjs";

const fakeEntry = {
  id: "ext_abc123",
  display_name: "demo-game",
  root_abs: path.resolve("/tmp/foundry-external-demo"),
  godot_rel: ".",
  brief_rel: "brief.json",
};

function getEntryById(id) {
  return id === "ext_abc123" ? fakeEntry : null;
}

test("parseExternalVirtual splits id and subpath", () => {
  assert.deepEqual(parseExternalVirtual("external:ext_abc123/brief.json"), {
    raw: "external:ext_abc123/brief.json",
    extId: "ext_abc123",
    sub: "brief.json",
  });
  assert.equal(parseExternalVirtual("projects/foo/brief.json"), null);
  assert.equal(parseExternalVirtual("external:ext_x/../brief.json"), null);
});

test("isExternalVirtualRel detects virtual keys", () => {
  assert.equal(isExternalVirtualRel("external:ext_abc123/pipeline/manifest.json"), true);
  assert.equal(isExternalVirtualRel("pipeline/foo.json"), false);
});

test("resolveExternalAbs joins under root_abs with containment", () => {
  const resolved = resolveExternalAbs("external:ext_abc123/brief.json", getEntryById);
  assert.ok(resolved);
  assert.equal(resolved.full, path.join(fakeEntry.root_abs, "brief.json"));
  assert.equal(resolved.rel, "external:ext_abc123/brief.json");
  assert.equal(resolveExternalAbs("external:missing/brief.json", getEntryById), null);
  assert.equal(
    resolveExternalAbs("external:ext_abc123/../../etc/passwd", getEntryById),
    null,
  );
});

test("cliArgForResolved uses absolute path for external", () => {
  const resolved = resolveExternalAbs("external:ext_abc123/brief.json", getEntryById);
  const cliArg = cliArgForResolved("external:ext_abc123/brief.json", {
    resolvedExternal: resolved,
    repoRoot: "/repo",
  });
  assert.equal(cliArg, path.join(fakeEntry.root_abs, "brief.json"));
});

test("cliArgForResolved keeps ../ convention for repo paths", () => {
  const cliArg = cliArgForResolved("projects/foo/brief.json", {
    resolvedExternal: null,
    repoRoot: "/repo",
  });
  assert.equal(cliArg, path.join("..", "projects/foo/brief.json"));
});

test("absForResolved maps repo and external paths", () => {
  const resolved = resolveExternalAbs("external:ext_abc123/output", getEntryById);
  assert.equal(
    absForResolved("external:ext_abc123/output", {
      resolvedExternal: resolved,
      repoRoot: "/repo",
    }),
    path.join(fakeEntry.root_abs, "output"),
  );
  assert.equal(
    absForResolved("projects/foo/brief.json", {
      resolvedExternal: null,
      repoRoot: "/repo",
    }),
    path.resolve("/repo", "projects/foo/brief.json"),
  );
});

test("projectRootKeyFromBriefRel covers projects and external", () => {
  assert.equal(projectRootKeyFromBriefRel("projects/foo/brief.json"), "projects/foo");
  assert.equal(
    projectRootKeyFromBriefRel("external:ext_abc123/brief.json"),
    "external:ext_abc123",
  );
});

test("manifestBelongsToBrief matches abs and project root, not basename", () => {
  const repo = path.resolve("/repo");
  const briefAbs = path.join(repo, "projects", "foo", "brief.json");
  assert.equal(
    manifestBelongsToBrief({
      briefAbs,
      briefRel: "projects/foo/brief.json",
      manBriefPath: briefAbs,
      repoRoot: repo,
    }),
    true,
  );
  assert.equal(
    manifestBelongsToBrief({
      briefAbs,
      briefRel: "projects/foo/brief.json",
      manBriefPath: "projects/foo/brief.json",
      repoRoot: repo,
    }),
    true,
  );
  // Same basename, different project — must NOT match.
  assert.equal(
    manifestBelongsToBrief({
      briefAbs,
      briefRel: "projects/foo/brief.json",
      manBriefPath: "projects/bar/brief.json",
      repoRoot: repo,
    }),
    false,
  );
});

test("normalizeRepoRel rejects path escape", () => {
  assert.equal(normalizeRepoRel("projects/foo/brief.json"), "projects/foo/brief.json");
  assert.equal(normalizeRepoRel("../projects/foo/brief.json"), "");
  assert.equal(normalizeRepoRel("projects/foo/../../outside"), "");
  assert.equal(normalizeRepoRel("./projects/foo/brief.json"), "projects/foo/brief.json");
});

test("cliArgForResolved rejects mid-path escape", () => {
  assert.throws(
    () =>
      cliArgForResolved("projects/foo/../../outside", {
        resolvedExternal: null,
        repoRoot: "/repo",
      }),
    /invalid repo-relative path|path outside repo/,
  );
});

test("absForResolved rejects mid-path escape", () => {
  assert.throws(
    () =>
      absForResolved("projects/x/../../etc/passwd", {
        resolvedExternal: null,
        repoRoot: "/repo",
      }),
    /invalid repo-relative path|path outside repo/,
  );
});
