import assert from "node:assert/strict";
import test from "node:test";

import {
  clearActiveBriefRel,
  loadActiveBriefRel,
  readActiveBriefPreference,
  saveActiveBriefRel,
} from "./projectPaths";

const KEY = "gamefactory.activeBrief";

function withMemoryStorage(run: () => void) {
  const mem = new Map<string, string>();
  const prev = globalThis.localStorage;
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: {
      getItem: (k: string) => (mem.has(k) ? mem.get(k)! : null),
      setItem: (k: string, v: string) => {
        mem.set(k, String(v));
      },
      removeItem: (k: string) => {
        mem.delete(k);
      },
    },
  });
  try {
    run();
  } finally {
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: prev,
    });
  }
}

test("clearActiveBriefRel is explicit none (not unset)", () => {
  withMemoryStorage(() => {
    assert.equal(readActiveBriefPreference().kind, "unset");
    saveActiveBriefRel("projects/black-whistle/brief.json");
    assert.deepEqual(readActiveBriefPreference(), {
      kind: "brief",
      rel: "projects/black-whistle/brief.json",
    });
    clearActiveBriefRel();
    assert.equal(readActiveBriefPreference().kind, "none");
    assert.equal(loadActiveBriefRel(), null);
    assert.equal(globalThis.localStorage.getItem(KEY), "__none__");
  });
});
