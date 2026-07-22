import assert from "node:assert/strict";
import { PassThrough } from "node:stream";
import test from "node:test";

import { ACP_METHODS } from "./cursor_acp_adapter.mjs";
import { createCursorAcpSessionManager } from "./cursor_acp_session.mjs";

/**
 * Minimal mock `agent acp` child: NDJSON RPC over stdio.
 * @param {object} [opts]
 * @param {boolean} [opts.withPermission]
 */
function createMockAcpChild(opts = {}) {
  const stdin = new PassThrough();
  const stdout = new PassThrough();
  const stderr = new PassThrough();
  const proc = new PassThrough();
  proc.stdin = stdin;
  proc.stdout = stdout;
  proc.stderr = stderr;
  proc.killed = false;
  proc.kill = () => {
    proc.killed = true;
    proc.emit("exit", 0, "SIGTERM");
  };

  let acpSessionId = "mock-acp-session";
  let promptCount = 0;

  stdin.on("data", (chunk) => {
    for (const line of String(chunk).split("\n").filter(Boolean)) {
      const req = JSON.parse(line);
      const { id, method } = req;

      if (method === ACP_METHODS.INITIALIZE) {
        emitLine(stdout, { jsonrpc: "2.0", id, result: { protocolVersion: 1 } });
        continue;
      }
      if (method === ACP_METHODS.AUTHENTICATE) {
        emitLine(stdout, { jsonrpc: "2.0", id, result: {} });
        continue;
      }
      if (method === ACP_METHODS.SESSION_NEW) {
        emitLine(stdout, {
          jsonrpc: "2.0",
          id,
          result: {
            sessionId: acpSessionId,
            modes: { currentModeId: "agent", availableModes: [{ id: "agent" }, { id: "ask" }, { id: "plan" }] },
          },
        });
        continue;
      }
      if (method === ACP_METHODS.SESSION_SET_MODE) {
        emitLine(stdout, { jsonrpc: "2.0", id, result: {} });
        continue;
      }
      if (method === ACP_METHODS.SESSION_PROMPT) {
        promptCount += 1;
        if (opts.withPermission) {
          // Intentionally use a numeric id that could collide with naive client counters.
          emitLine(stdout, {
            jsonrpc: "2.0",
            id: promptCount,
            method: ACP_METHODS.SESSION_REQUEST_PERMISSION,
            params: {
              sessionId: acpSessionId,
              toolCall: { toolCallId: `tool-${promptCount}`, title: "Run test" },
            },
          });
        }
        emitLine(stdout, {
          jsonrpc: "2.0",
          method: ACP_METHODS.SESSION_UPDATE,
          params: {
            sessionId: acpSessionId,
            update: {
              sessionUpdate: "agent_message_chunk",
              content: { type: "text", text: opts.withPermission ? `reply-${promptCount}` : "hello" },
            },
          },
        });
        emitLine(stdout, { jsonrpc: "2.0", id, result: { stopReason: "end_turn" } });
      }
    }
  });

  return proc;
}

/** @param {PassThrough} stdout @param {Record<string, unknown>} msg */
function emitLine(stdout, msg) {
  queueMicrotask(() => stdout.write(`${JSON.stringify(msg)}\n`));
}

test("createCursorAcpSessionManager prompt returns buffered text", async () => {
  const manager = createCursorAcpSessionManager({
    getAgentPath: () => "/mock/agent",
    envPath: "/usr/bin",
    onPermission: () => {},
    spawnFn: () => createMockAcpChild(),
  });

  const result = await manager.prompt({
    instanceId: "inst-a",
    sessionId: "chat-1",
    turnId: "turn-1",
    workspaceCwd: "/tmp/ws",
    text: "hi",
  });

  assert.equal(result.text, "hello");
  manager.stopAll();
});

test("decidePermission resolves pending permission and continues", async () => {
  /** @type {import('./cursor_acp_session.mjs').createCursorAcpSessionManager extends (o: any) => infer R ? R : never} */
  let manager;
  /** @type {string | undefined} */
  let seenPermissionId;

  manager = createCursorAcpSessionManager({
    getAgentPath: () => "/mock/agent",
    envPath: "/usr/bin",
    onPermission: (req) => {
      seenPermissionId = req.permissionId;
      assert.equal(req.source, "cursor_acp");
      assert.equal(req.instanceId, "inst-b");
      queueMicrotask(() => manager.decidePermission(req.permissionId, "once"));
    },
    spawnFn: () => createMockAcpChild({ withPermission: true }),
  });

  const result = await manager.prompt({
    instanceId: "inst-b",
    sessionId: "chat-2",
    turnId: "turn-2",
    workspaceCwd: "/tmp/ws",
    text: "run tool",
  });

  assert.equal(seenPermissionId, "tool-1");
  assert.equal(result.text, "reply-1");
  manager.stopAll();
});

test("permission request with numeric id does not steal session/prompt response", async () => {
  let manager;
  let uiCalls = 0;

  manager = createCursorAcpSessionManager({
    getAgentPath: () => "/mock/agent",
    envPath: "/usr/bin",
    onPermission: (req) => {
      uiCalls += 1;
      queueMicrotask(() => manager.decidePermission(req.permissionId, "once"));
    },
    spawnFn: () => createMockAcpChild({ withPermission: true }),
  });

  const result = await manager.prompt({
    instanceId: "inst-collide",
    sessionId: "chat-c",
    turnId: "turn-c",
    workspaceCwd: "/tmp/ws",
    text: "run",
    permissionMode: "auto_review",
  });

  assert.equal(uiCalls, 1);
  assert.equal(result.text, "reply-1");
  manager.stopAll();
});

test("turnAllow cache auto-approves without onPermission UI", async () => {
  let uiCalls = 0;
  let manager;

  manager = createCursorAcpSessionManager({
    getAgentPath: () => "/mock/agent",
    envPath: "/usr/bin",
    onPermission: (req) => {
      uiCalls += 1;
      queueMicrotask(() => manager.decidePermission(req.permissionId, "turn"));
    },
    spawnFn: () => createMockAcpChild({ withPermission: true }),
  });

  await manager.prompt({
    instanceId: "inst-c",
    sessionId: "chat-3",
    turnId: "turn-shared",
    workspaceCwd: "/tmp/ws",
    text: "first",
  });
  assert.equal(uiCalls, 1);

  await manager.prompt({
    instanceId: "inst-c",
    sessionId: "chat-3",
    turnId: "turn-shared",
    workspaceCwd: "/tmp/ws",
    text: "second",
  });
  assert.equal(uiCalls, 1, "turn cache should skip second UI prompt");

  manager.stop("inst-c");
});

test("stop clears instance and allows restart", async () => {
  let spawnCount = 0;
  const manager = createCursorAcpSessionManager({
    getAgentPath: () => "/mock/agent",
    envPath: "/usr/bin",
    onPermission: () => {},
    spawnFn: () => {
      spawnCount += 1;
      return createMockAcpChild();
    },
  });

  await manager.prompt({
    instanceId: "inst-d",
    sessionId: "s",
    turnId: "t",
    workspaceCwd: "/tmp/ws",
    text: "a",
  });
  manager.stop("inst-d");
  await manager.prompt({
    instanceId: "inst-d",
    sessionId: "s",
    turnId: "t2",
    workspaceCwd: "/tmp/ws",
    text: "b",
  });
  assert.equal(spawnCount, 2);
  manager.stopAll();
});

test("module exports expected API", async () => {
  const mod = await import("./cursor_acp_session.mjs");
  assert.deepEqual(Object.keys(mod).sort(), [
    "createCursorAcpSessionManager",
    "pathWithCommonNodeBins",
  ]);
});
