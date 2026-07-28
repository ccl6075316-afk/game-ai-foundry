/**
 * Unit tests for IT session trust on the tool permission bridge.
 * Run: node --test gui/electron/tool_permission_bridge.test.mjs
 */
import assert from "node:assert/strict";
import test from "node:test";
import { createToolPermissionBridge } from "./tool_permission_bridge.mjs";

test("trustSession auto-allows mutate permission without UI", async () => {
  let uiCalls = 0;
  const bridge = createToolPermissionBridge({
    getSender: () => ({
      isDestroyed: () => false,
      send: () => {
        uiCalls += 1;
      },
    }),
    timeoutMs: 2000,
  });
  try {
    await new Promise((resolve, reject) => {
      bridge.server.once("listening", resolve);
      bridge.server.once("error", reject);
      if (bridge.server.listening) resolve(undefined);
    });

    bridge.trustSession("sess-it-1");
    assert.equal(bridge.isSessionTrusted("sess-it-1"), true);

    const env = bridge.env();
    const url = env.GAMEFACTORY_TOOL_PERMISSION_URL;
    const token = env.GAMEFACTORY_TOOL_PERMISSION_TOKEN;
    const res = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        permission_id: "p1",
        session_id: "sess-it-1",
        turn_id: "t1",
        argv_summary: "pipeline run",
      }),
    });
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.decision, "session");
    assert.equal(uiCalls, 0);

    bridge.untrustSession("sess-it-1");
    assert.equal(bridge.isSessionTrusted("sess-it-1"), false);
  } finally {
    bridge.close();
  }
});
