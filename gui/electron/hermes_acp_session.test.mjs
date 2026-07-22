import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { PassThrough } from "node:stream";
import test from "node:test";

import { ACP_METHODS, HERMES_ACP_SPAWN_ARGS } from "./hermes_acp_adapter.mjs";
import { createHermesAcpSessionManager } from "./hermes_acp_session.mjs";

/**
 * Minimal mock `hermes acp --accept-hooks` child: NDJSON RPC over stdio.
 * @param {object} [opts]
 * @param {boolean} [opts.withPermission]
 */
function createMockHermesAcpChild(opts = {}) {
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

  let acpSessionId = "mock-hermes-session";
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

test("spawn argv includes acp and --accept-hooks", async () => {
  /** @type {string[][]} */
  const spawnArgs = [];
  const manager = createHermesAcpSessionManager({
    getHermesPath: () => "/mock/hermes",
    envPath: "/usr/bin",
    onPermission: () => {},
    spawnFn: (_cmd, args) => {
      spawnArgs.push([...args]);
      return createMockHermesAcpChild();
    },
  });

  await manager.prompt({
    instanceId: "inst-spawn",
    sessionId: "s",
    turnId: "t",
    workspaceCwd: "/tmp/ws",
    text: "hi",
  });

  assert.equal(spawnArgs.length, 1);
  assert.deepEqual(spawnArgs[0], ["acp", ...HERMES_ACP_SPAWN_ARGS]);
  assert.ok(spawnArgs[0].includes("--accept-hooks"));
  manager.stopAll();
});

test("createHermesAcpSessionManager prompt returns buffered text", async () => {
  const manager = createHermesAcpSessionManager({
    getHermesPath: () => "/mock/hermes",
    envPath: "/usr/bin",
    onPermission: () => {},
    spawnFn: () => createMockHermesAcpChild(),
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
  /** @type {import('./hermes_acp_session.mjs').createHermesAcpSessionManager extends (o: any) => infer R ? R : never} */
  let manager;
  /** @type {string | undefined} */
  let seenPermissionId;

  manager = createHermesAcpSessionManager({
    getHermesPath: () => "/mock/hermes",
    envPath: "/usr/bin",
    onPermission: (req) => {
      seenPermissionId = req.permissionId;
      assert.equal(req.source, "hermes_acp");
      assert.equal(req.instanceId, "inst-b");
      queueMicrotask(() => manager.decidePermission(req.permissionId, "once"));
    },
    spawnFn: () => createMockHermesAcpChild({ withPermission: true }),
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

  manager = createHermesAcpSessionManager({
    getHermesPath: () => "/mock/hermes",
    envPath: "/usr/bin",
    onPermission: (req) => {
      uiCalls += 1;
      queueMicrotask(() => manager.decidePermission(req.permissionId, "once"));
    },
    spawnFn: () => createMockHermesAcpChild({ withPermission: true }),
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

  manager = createHermesAcpSessionManager({
    getHermesPath: () => "/mock/hermes",
    envPath: "/usr/bin",
    onPermission: (req) => {
      uiCalls += 1;
      queueMicrotask(() => manager.decidePermission(req.permissionId, "turn"));
    },
    spawnFn: () => createMockHermesAcpChild({ withPermission: true }),
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

test("sessionAllow cache does not bleed across instances", async () => {
  let uiCallsA = 0;
  let uiCallsB = 0;
  let manager;

  manager = createHermesAcpSessionManager({
    getHermesPath: () => "/mock/hermes",
    envPath: "/usr/bin",
    onPermission: (req) => {
      if (req.instanceId === "inst-x") {
        uiCallsA += 1;
        queueMicrotask(() => manager.decidePermission(req.permissionId, "session"));
      }
      if (req.instanceId === "inst-y") {
        uiCallsB += 1;
      }
    },
    spawnFn: () => createMockHermesAcpChild({ withPermission: true }),
  });

  await manager.prompt({
    instanceId: "inst-x",
    sessionId: "shared-session",
    turnId: "turn-1",
    workspaceCwd: "/tmp/ws",
    text: "first on x",
  });
  assert.equal(uiCallsA, 1);

  await manager.prompt({
    instanceId: "inst-x",
    sessionId: "shared-session",
    turnId: "turn-2",
    workspaceCwd: "/tmp/ws",
    text: "second on x",
  });
  assert.equal(uiCallsA, 1, "inst-x session cache should skip second UI prompt");

  await manager.prompt({
    instanceId: "inst-y",
    sessionId: "shared-session",
    turnId: "turn-3",
    workspaceCwd: "/tmp/ws",
    text: "first on y",
  });
  assert.equal(uiCallsB, 1, "inst-y must not inherit inst-x sessionAllow");

  manager.stopAll();
});

test("stop clears instance and allows restart", async () => {
  let spawnCount = 0;
  const manager = createHermesAcpSessionManager({
    getHermesPath: () => "/mock/hermes",
    envPath: "/usr/bin",
    onPermission: () => {},
    spawnFn: () => {
      spawnCount += 1;
      return createMockHermesAcpChild();
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

test("pathWithCommonNodeBins prepends ~/.local/bin when present", async () => {
  const { pathWithCommonNodeBins } = await import("./hermes_acp_session.mjs");
  const localBin = path.join(os.homedir(), ".local", "bin");
  const result = pathWithCommonNodeBins("/usr/bin");
  if (existsSync(localBin)) {
    assert.ok(result.includes(localBin));
  }
});

test("module exports expected API", async () => {
  const mod = await import("./hermes_acp_session.mjs");
  assert.deepEqual(Object.keys(mod).sort(), [
    "createHermesAcpSessionManager",
    "pathWithCommonNodeBins",
  ]);
});
