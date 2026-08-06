import assert from "node:assert/strict";
import test from "node:test";
import { resolveAppendTarget, type SessionTarget } from "./appendTarget";
import type { ChatSessionStore } from "./sessions";

function stubStore(activeInstanceId: string): ChatSessionStore {
  return {
    version: 2,
    roster: [],
    activeInstanceId,
    activeByInstance: {},
    sessions: [],
  };
}

test("explicit target always wins", () => {
  const explicit: SessionTarget = { instanceId: "a", sessionId: "s-a" };
  const pins = new Map<string, SessionTarget>([
    ["b", { instanceId: "b", sessionId: "s-b" }],
  ]);
  assert.deepEqual(resolveAppendTarget(explicit, stubStore("b"), pins), explicit);
});

test("single busy pin routes away from active colleague", () => {
  const pins = new Map<string, SessionTarget>([
    ["brief-1", { instanceId: "brief-1", sessionId: "s-brief" }],
  ]);
  assert.deepEqual(
    resolveAppendTarget(undefined, stubStore("advisor-1"), pins),
    { instanceId: "brief-1", sessionId: "s-brief" },
  );
});

test("active busy pin preferred when multiple", () => {
  const pins = new Map<string, SessionTarget>([
    ["brief-1", { instanceId: "brief-1", sessionId: "s-brief" }],
    ["it-1", { instanceId: "it-1", sessionId: "s-it" }],
  ]);
  assert.deepEqual(
    resolveAppendTarget(undefined, stubStore("it-1"), pins),
    { instanceId: "it-1", sessionId: "s-it" },
  );
});

test("ambiguous multi-pin without active match falls back to null", () => {
  const pins = new Map<string, SessionTarget>([
    ["brief-1", { instanceId: "brief-1", sessionId: "s-brief" }],
    ["it-1", { instanceId: "it-1", sessionId: "s-it" }],
  ]);
  assert.equal(resolveAppendTarget(undefined, stubStore("advisor-1"), pins), null);
});
