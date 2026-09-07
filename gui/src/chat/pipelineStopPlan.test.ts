import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  PM_HANDLE_FAILURE,
  RETRY_FIX_AND_CONTINUE,
  RUN_WITH_PROMPTS,
  formatPmFitAdvice,
  planPipelineStop,
} from "./pipelineStopPlan";

describe("planPipelineStop ping-pong guard", () => {
  const adviceSuitable = formatPmFitAdvice({
    pm_suitable: true,
    pm_advice_short: "适合项目经理直接处理",
    pm_advice: "点处理失败即可",
    items: [
      {
        task_id: "pose_x.prompt.craft",
        kind: "validation",
        summary: "Chinese brief text cannot be used",
        pm_fit: "yes",
      },
    ],
  });

  it("first failure suitable → only PM heal, not run", () => {
    const plan = planPipelineStop({
      exitCode: 2,
      advice: adviceSuitable,
      healed: [],
      status: { counts: { done: 59, pending: 12, failed: 1 }, failed_ids: ["pose_x.prompt.craft"] },
      runData: { paused: true, summary: { counts: { done: 59, pending: 12, failed: 1 } } },
    });
    assert.match(plan.body, /含文案续跑/);
    assert.deepEqual(plan.choices, [PM_HANDLE_FAILURE, "打开看板"]);
    assert.ok(!plan.choices.includes("运行资产生成"));
    assert.ok(!plan.choices.includes(RUN_WITH_PROMPTS));
  });

  it("after auto-fix → never recommend the other button", () => {
    const plan = planPipelineStop({
      exitCode: 2,
      advice: adviceSuitable,
      healed: [],
      alreadyAutoFixed: true,
      stoppedReason: "max_rounds",
      status: { counts: { done: 59, pending: 12, failed: 1 }, failed_ids: ["pose_x.prompt.craft"] },
      runData: { paused: true, summary: { counts: { done: 59, pending: 12, failed: 1 } } },
    });
    assert.match(plan.body, /来回点/);
    assert.deepEqual(plan.choices, ["打开看板", RETRY_FIX_AND_CONTINUE]);
    assert.ok(!plan.choices.includes(PM_HANDLE_FAILURE));
    assert.ok(!plan.choices.includes("运行资产生成"));
  });

  it("same_failure → board only", () => {
    const plan = planPipelineStop({
      exitCode: 2,
      advice: adviceSuitable,
      healed: [],
      alreadyAutoFixed: true,
      stoppedReason: "same_failure",
      status: { counts: { done: 59, pending: 12, failed: 1 }, failed_ids: ["pose_x.prompt.craft"] },
      runData: { paused: true, summary: { counts: { done: 59, pending: 12, failed: 1 } } },
    });
    assert.match(plan.body, /空转/);
    assert.deepEqual(plan.choices, ["打开看板"]);
  });
});
