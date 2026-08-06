import assert from "node:assert/strict";
import test from "node:test";
import { syncPiLockedInstancesToPreset, type AgentInstancesMap } from "./agentInstances";

test("syncPiLockedInstancesToPreset updates advisor alongside brief and it", () => {
  const instances: AgentInstancesMap = {
    "brief-1": {
      role_kind: "brief",
      executor: "pi",
      provider: "openrouter",
      model: "old-model",
      use_third_party: false,
    },
    "advisor-1": {
      role_kind: "advisor",
      executor: "pi",
      provider: "openrouter",
      model: "old-model",
      use_third_party: false,
    },
    "pm-1": {
      role_kind: "product_host",
      executor: "hermes",
      provider: "openrouter",
      model: "old-model",
      use_third_party: false,
    },
  };
  const next = syncPiLockedInstancesToPreset(
    instances,
    { provider: "openrouter", model: "old-model" },
    { provider: "deepseek", model: "deepseek-v4-flash" },
  );
  assert.equal(next["brief-1"]?.provider, "deepseek");
  assert.equal(next["advisor-1"]?.provider, "deepseek");
  assert.equal(next["advisor-1"]?.model, "deepseek-v4-flash");
  assert.equal(next["pm-1"]?.provider, "openrouter");
});
