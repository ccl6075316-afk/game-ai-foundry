import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  GENERATE_DEV_HANDOFF,
  PM_HANDLE_FAILURE,
  RETRY_FIX_AND_CONTINUE,
  RUN_WITH_PROMPTS,
  formatPmFitAdvice,
  isGameDevHandoffReady,
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

  it("alreadyAutoFixed with pending-only still shows failure reason", () => {
    const plan = planPipelineStop({
      exitCode: 2,
      advice: adviceSuitable,
      healed: [],
      alreadyAutoFixed: true,
      stoppedReason: "same_failure",
      status: { counts: { done: 59, pending: 14, failed: 0 }, ready_ids: ["pose_x.prompt.craft"] },
      runData: { paused: false, summary: { counts: { done: 59, pending: 14, failed: 0 } } },
      failureLogPath: "projects/fishing-2d/pipeline/failure-log.jsonl",
    });
    assert.match(plan.title, /本轮已停下/);
    assert.match(plan.body, /失败原因/);
    assert.match(plan.body, /Chinese brief text/);
    assert.match(plan.body, /failure-log\.jsonl/);
  });

  it("only godot.dev-context ready → offer programmer handoff", () => {
    const emptyAdvice = formatPmFitAdvice(null);
    const plan = planPipelineStop({
      exitCode: 0,
      advice: emptyAdvice,
      healed: [],
      status: {
        counts: { done: 72, pending: 1, failed: 0 },
        ready_ids: ["brief.godot.dev-context"],
        failed_ids: [],
      },
      runData: {
        complete: false,
        summary: {
          counts: { done: 72, pending: 1, failed: 0 },
          ready_ids: ["brief.godot.dev-context"],
        },
      },
    });
    assert.match(plan.title, /程序员交接/);
    assert.deepEqual(plan.choices, [GENERATE_DEV_HANDOFF, "打开看板"]);
    assert.ok(!plan.choices.includes(RUN_WITH_PROMPTS));
  });

  it("isGameDevHandoffReady detects skipped Pass 4", () => {
    assert.equal(
      isGameDevHandoffReady({
        failedIds: [],
        readyIds: [],
        pending: 0,
        skippedIds: ["brief.godot.dev-context"],
      }),
      true,
    );
    assert.equal(
      isGameDevHandoffReady({
        failedIds: [],
        readyIds: ["pose_x.video.generate"],
        pending: 1,
      }),
      false,
    );
  });
});
