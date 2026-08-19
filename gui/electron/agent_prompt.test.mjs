import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAgentTurnArgs,
  buildAgentPromptArgs,
  normalizeItExecutor,
  prepareRoleAwareAcpPrompt,
  resolveItExecutor,
} from "./agent_prompt.mjs";

test("normalizeItExecutor rejects stale Hermes selections", () => {
  assert.equal(normalizeItExecutor("hermes"), "pi");
  assert.equal(normalizeItExecutor("codex"), "codex");
  assert.equal(normalizeItExecutor("cursor"), "cursor");
});

test("resolveItExecutor prefers saved instance over stale roster override", () => {
  assert.equal(
    resolveItExecutor({
      override: "pi",
      instanceExecutor: "codex",
      roleExecutor: "pi",
    }),
    "codex",
  );
  assert.equal(
    resolveItExecutor({
      override: "cursor",
      instanceExecutor: "",
      roleExecutor: "pi",
    }),
    "cursor",
  );
  assert.equal(
    resolveItExecutor({
      override: "",
      instanceExecutor: "hermes",
      roleExecutor: "hermes",
    }),
    "pi",
  );
});

test("buildAgentPromptArgs forwards IT turn context to shared CLI prompt builder", () => {
  assert.deepEqual(
    buildAgentPromptArgs({
      roleKind: "it",
      sessionId: "session-1",
      message: "检查策划只说不写",
      executor: "codex",
      instanceId: "it-1",
      briefArg: "../projects/demo/brief.draft.json",
      progressArg: "../projects/demo/plans/progress.json",
      opsContextArg: "GUI 会话尾部：ok",
    }),
    [
      "agent",
      "prompt",
      "--role",
      "it",
      "--session-id",
      "session-1",
      "--message",
      "检查策划只说不写",
      "--executor",
      "codex",
      "--instance-id",
      "it-1",
      "--brief",
      "../projects/demo/brief.draft.json",
      "--progress",
      "../projects/demo/plans/progress.json",
      "--ops-context",
      "GUI 会话尾部：ok",
      "--json",
    ],
  );
});

test("buildAgentTurnArgs forwards the resolved executor to non-ACP CLI", () => {
  assert.deepEqual(
    buildAgentTurnArgs({
      roleKind: "it",
      sessionId: "session-1",
      message: "检查环境",
      effectiveExecutor: "codex",
      instanceId: "it-1",
      briefArg: "../projects/demo/brief.json",
      progressArg: "../projects/demo/progress.json",
      opsContextArg: "最近流水线终端日志：exit 2",
    }),
    [
      "agent",
      "turn",
      "--role",
      "it",
      "--session-id",
      "session-1",
      "--message",
      "检查环境",
      "--executor",
      "codex",
      "--brief",
      "../projects/demo/brief.json",
      "--progress",
      "../projects/demo/progress.json",
      "--instance-id",
      "it-1",
      "--ops-context",
      "最近流水线终端日志：exit 2",
      "--json",
    ],
  );
});

test("prepareRoleAwareAcpPrompt returns the shared CLI prompt", async () => {
  let receivedArgs;
  const prompt = await prepareRoleAwareAcpPrompt({
    roleKind: "it",
    message: "检查环境",
    promptOptions: {
      roleKind: "it",
      sessionId: "session-1",
      message: "检查环境",
      executor: "codex",
    },
    runPromptCommand: async (args) => {
      receivedArgs = args;
      return { exitCode: 0, stdout: '{"ok":true,"prompt":"完整 IT prompt"}', stderr: "" };
    },
    parseJsonOutput: JSON.parse,
  });

  assert.equal(prompt, "完整 IT prompt");
  assert.equal(receivedArgs[0], "agent");
  assert.equal(receivedArgs[1], "prompt");
});

test("prepareRoleAwareAcpPrompt rejects failed or empty CLI output", async () => {
  for (const result of [
    { exitCode: 1, stdout: '{"ok":false,"error":"构建失败"}', stderr: "" },
    { exitCode: 0, stdout: '{"ok":true,"prompt":""}', stderr: "" },
  ]) {
    await assert.rejects(
      prepareRoleAwareAcpPrompt({
        roleKind: "it",
        message: "检查环境",
        promptOptions: {
          roleKind: "it",
          sessionId: "session-1",
          message: "检查环境",
          executor: "codex",
        },
        runPromptCommand: async () => result,
        parseJsonOutput: JSON.parse,
      }),
      /构建失败|无法构建 IT 角色提示词/,
    );
  }
});
