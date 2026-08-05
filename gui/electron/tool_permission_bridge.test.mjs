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

test("permission timeout notifies renderer via agent-tool-permission-resolved", async () => {
  /** @type {Array<{ channel: string, payload: Record<string, unknown> }>} */
  const sent = [];
  const bridge = createToolPermissionBridge({
    getSender: () => ({
      isDestroyed: () => false,
      send: (channel, payload) => {
        sent.push({ channel, payload });
      },
    }),
    timeoutMs: 50,
  });
  try {
    await new Promise((resolve, reject) => {
      bridge.server.once("listening", resolve);
      bridge.server.once("error", reject);
      if (bridge.server.listening) resolve(undefined);
    });

    const env = bridge.env();
    const res = await fetch(env.GAMEFACTORY_TOOL_PERMISSION_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GAMEFACTORY_TOOL_PERMISSION_TOKEN}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        permission_id: "p-timeout",
        session_id: "sess-x",
        turn_id: "t1",
        argv_summary: "setup executor step",
      }),
    });

    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.decision, "deny");
    assert.ok(sent.some((e) => e.channel === "agent-tool-permission"));
    const resolved = sent.find((e) => e.channel === "agent-tool-permission-resolved");
    assert.ok(resolved);
    assert.equal(resolved.payload.permissionId, "p-timeout");
    assert.equal(resolved.payload.decision, "deny");
  } finally {
    bridge.close();
  }
});
