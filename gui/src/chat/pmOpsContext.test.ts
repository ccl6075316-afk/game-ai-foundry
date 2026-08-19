import test from "node:test";
import assert from "node:assert/strict";
import { buildPmGuiOpsContext } from "./pmOpsContext";

test("buildPmGuiOpsContext includes manifest and diagnose", () => {
  const out = buildPmGuiOpsContext({
    manifestRel: "pipeline/demo.json",
    pipelineLogs: ["task hero_idle failed exit 2"],
    diagnose: {
      pm_advice_short: "适合项目经理",
      needs_hermes: [{ task_id: "t1", kind: "config_size", pm_fit: "yes", pm_tip: "改 size_multiple" }],
      fix_commands: ["config set --key image.constraints.size_multiple --value 16"],
    },
  });
  assert.match(out, /pipeline\/demo\.json/);
  assert.match(out, /config_size/);
  assert.match(out, /目标模式/);
});
