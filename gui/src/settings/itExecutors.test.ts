import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { loadAgentInstancesFromConfig } from "./agentInstances";
import { HIRE_IT_EXECUTORS } from "./hireColleague";

describe("IT executors", () => {
  it("does not offer Hermes", () => {
    assert.deepEqual(HIRE_IT_EXECUTORS, ["pi", "codex", "cursor"]);
  });

  it("falls back stale Hermes IT instances to Pi", () => {
    const instances = loadAgentInstancesFromConfig({
      agents: {
        instances: {
          "it-1": {
            role_kind: "it",
            executor: "hermes",
            provider: "openrouter",
          },
        },
      },
    });

    assert.equal(instances["it-1"]?.executor, "pi");
  });
});
