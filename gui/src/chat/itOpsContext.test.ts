import assert from "node:assert/strict";
import test from "node:test";
import { buildItGuiOpsContext, redactOpsSecrets } from "./itOpsContext";
import type { ChatSessionStore } from "./sessions";

test("redactOpsSecrets masks sk- tokens", () => {
  assert.equal(redactOpsSecrets("key=sk-or-abcdefghijklmnop"), "key=***");
});

test("buildItGuiOpsContext redacts PM chat secrets", () => {
  const store = {
    version: 2,
    roster: [{ id: "pm-1", roleKind: "product_host", displayName: "项目经理" }],
    activeInstanceId: "pm-1",
    activeByInstance: { "pm-1": "sess-1" },
    sessions: [
      {
        id: "sess-1",
        instanceId: "pm-1",
        role: "product_host",
        title: "t",
        messages: [
          {
            id: "m1",
            role: "assistant",
            content: "失败了 sk-abcdefghijklmnopqrst",
            timestamp: 1,
          },
        ],
        createdAt: 1,
        updatedAt: 1,
      },
    ],
  } as unknown as ChatSessionStore;
  const out = buildItGuiOpsContext({ store, pipelineLogs: ["token sk-or-abcdefghijklmnop"] });
  assert.match(out, /GUI 会话尾部/);
  assert.doesNotMatch(out, /sk-[a-zA-Z0-9_-]{12,}/);
});
