import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { PassThrough } from "node:stream";
import test from "node:test";

import {
  CLIENT_METHODS,
  ITEM_APPROVAL_DECISIONS,
  SERVER_APPROVAL_METHODS,
  decodeLine,
} from "./codex_app_server_adapter.mjs";
import { createCodexAppServerSessionManager } from "./codex_app_server_session.mjs";

/**
 * Minimal mock `codex app-server --listen stdio://` child.
 * @param {object} [opts]
 * @param {boolean} [opts.withPermission]
 * @param {string} [opts.replyText]
 */
function createMockCodexAppServerChild(opts = {}) {
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

  let threadId = "mock-thread-1";
  let turnCount = 0;
  /** @type {string | number | null} */
  let pendingTurnStartId = null;
  let awaitingPermission = false;

  /**
   * @param {string | number} turnStartReqId
   */
  function finishTurn(turnStartReqId) {
    const turnId = `turn-${turnCount}`;
    emitLine(stdout, {
      jsonrpc: "2.0",
      method: "item/agentMessage/delta",
      params: {
        threadId,
        turnId,
        itemId: "msg-1",
        delta: opts.replyText ?? (opts.withPermission ? `reply-${turnCount}` : "hello"),
      },
    });
    emitLine(stdout, {
      jsonrpc: "2.0",
      method: "turn/completed",
      params: {
        threadId,
        turn: { id: turnId, status: "completed", items: [] },
      },
    });
    emitLine(stdout, {
      jsonrpc: "2.0",
      id: turnStartReqId,
      result: { turn: { id: turnId, status: "completed", items: [] } },
    });
  }

  stdin.on("data", (chunk) => {
    for (const line of String(chunk).split("\n").filter(Boolean)) {
      const msg = JSON.parse(line);

      const isResponse =
        msg.id != null &&
        !msg.method &&
        (Object.prototype.hasOwnProperty.call(msg, "result") || msg.error != null);
      if (isResponse && awaitingPermission) {
        awaitingPermission = false;
        if (pendingTurnStartId != null) {
          finishTurn(pendingTurnStartId);
          pendingTurnStartId = null;
        }
        continue;
      }

      const { id, method } = msg;

      if (method === CLIENT_METHODS.INITIALIZE) {
        emitLine(stdout, { jsonrpc: "2.0", id, result: { capabilities: {} } });
        continue;
      }
      if (method === CLIENT_METHODS.THREAD_START) {
        threadId = `thread-${Date.now()}`;
        emitLine(stdout, {
          jsonrpc: "2.0",
          id,
          result: {
            thread: { id: threadId },
            cwd: msg.params?.cwd ?? "/tmp/ws",
            model: "mock-model",
            modelProvider: "mock",
            sandbox: "workspace-write",
            approvalPolicy: "on-request",
            approvalsReviewer: "user",
          },
        });
        continue;
      }
      if (method === CLIENT_METHODS.TURN_START) {
        turnCount += 1;
        pendingTurnStartId = id;
        if (opts.withPermission) {
          awaitingPermission = true;
          emitLine(stdout, {
            jsonrpc: "2.0",
            id: turnCount,
            method: SERVER_APPROVAL_METHODS.COMMAND_EXECUTION_REQUEST_APPROVAL,
            params: {
              threadId,
              turnId: `turn-${turnCount}`,
              itemId: `tool-${turnCount}`,
              command: "npm test",
              startedAtMs: 1,
            },
          });
        } else {
          finishTurn(id);
          pendingTurnStartId = null;
        }
      }
    }
  });

  return proc;
}

/** @param {PassThrough} stdout @param {Record<string, unknown>} msg */
function emitLine(stdout, msg) {
  queueMicrotask(() => stdout.write(`${JSON.stringify(msg)}\n`));
}

test("spawn argv includes app-server and stdio transport", async () => {
  /** @type {string[][]} */
  const spawnArgs = [];
  const manager = createCodexAppServerSessionManager({
    resolveCodexBin: () => "/mock/codex",
    envPath: "/usr/bin",
    onPermission: () => {},
    spawnImpl: (_cmd, args) => {
      spawnArgs.push([...args]);
      return createMockCodexAppServerChild();
    },
  });

  await manager.prompt({
    instanceId: "inst-spawn",
    sessionId: "s",
    turnId: "t",
    workspace: "/tmp/ws",
    message: "hi",
  });

  assert.equal(spawnArgs.length, 1);
  assert.ok(spawnArgs[0].includes("app-server"));
  assert.ok(
    spawnArgs[0].some((a) => a.includes("stdio")),
    `expected stdio in argv: ${spawnArgs[0].join(" ")}`,
  );
  manager.stopAll();
});

test("createCodexAppServerSessionManager prompt returns buffered text", async () => {
  const manager = createCodexAppServerSessionManager({
    resolveCodexBin: () => "/mock/codex",
    envPath: "/usr/bin",
    onPermission: () => {},
    spawnImpl: () => createMockCodexAppServerChild(),
  });

  const result = await manager.prompt({
    instanceId: "inst-a",
    sessionId: "chat-1",
    turnId: "turn-1",
    cwd: "/tmp/ws",
    prompt: "hi",
  });

  assert.equal(result.text, "hello");
  manager.stopAll();
});

test("decidePermission once writes accept response to stdin", async () => {
  /** @type {string[]} */
  const stdinLines = [];
  /** @type {ReturnType<typeof createCodexAppServerSessionManager>} */
  let manager;
  /** @type {string | undefined} */
  let seenPermissionId;

  manager = createCodexAppServerSessionManager({
    resolveCodexBin: () => "/mock/codex",
    envPath: "/usr/bin",
    onPermission: (req) => {
      seenPermissionId = req.permissionId;
      assert.equal(req.source, "codex_app_server");
      assert.equal(req.instanceId, "inst-b");
      queueMicrotask(() => manager.decidePermission({ permissionId: req.permissionId, decision: "once" }));
    },
    spawnImpl: () => {
      const child = createMockCodexAppServerChild({ withPermission: true });
      const origWrite = child.stdin.write.bind(child.stdin);
      child.stdin.write = (chunk, ...rest) => {
        stdinLines.push(String(chunk));
        return origWrite(chunk, ...rest);
      };
      return child;
    },
  });

  const result = await manager.prompt({
    instanceId: "inst-b",
    sessionId: "chat-2",
    turnId: "turn-2",
    workspace: "/tmp/ws",
    message: "run tool",
  });

  assert.equal(seenPermissionId, "tool-1");
  assert.equal(result.text, "reply-1");

  const permissionResponses = stdinLines
    .flatMap((chunk) => chunk.split("\n").filter(Boolean))
    .map((line) => decodeLine(line))
    .filter((msg) => msg?.result && typeof msg.result === "object" && "decision" in msg.result);

  assert.ok(permissionResponses.length >= 1);
  assert.deepEqual(permissionResponses[0]?.result, { decision: ITEM_APPROVAL_DECISIONS.ACCEPT });

  manager.stopAll();
});

test("permission request with numeric id does not steal turn/start response", async () => {
  let manager;
  let uiCalls = 0;

  manager = createCodexAppServerSessionManager({
    resolveCodexBin: () => "/mock/codex",
    envPath: "/usr/bin",
    onPermission: (req) => {
      uiCalls += 1;
      queueMicrotask(() => manager.decidePermission({ permissionId: req.permissionId, decision: "once" }));
    },
    spawnImpl: () => createMockCodexAppServerChild({ withPermission: true }),
  });

  const result = await manager.prompt({
    instanceId: "inst-collide",
    sessionId: "chat-c",
    turnId: "turn-c",
    cwd: "/tmp/ws",
    prompt: "run",
  });

  assert.equal(uiCalls, 1);
  assert.equal(result.text, "reply-1");
  manager.stopAll();
});

test("sessionAllow cache does not bleed across instances", async () => {
  let uiCallsA = 0;
  let uiCallsB = 0;
  let manager;

  manager = createCodexAppServerSessionManager({
    resolveCodexBin: () => "/mock/codex",
    envPath: "/usr/bin",
    onPermission: (req) => {
      if (req.instanceId === "inst-x") {
        uiCallsA += 1;
        queueMicrotask(() =>
          manager.decidePermission({ permissionId: req.permissionId, decision: "session" }),
        );
      }
      if (req.instanceId === "inst-y") {
        uiCallsB += 1;
        queueMicrotask(() =>
          manager.decidePermission({ permissionId: req.permissionId, decision: "once" }),
        );
      }
    },
    spawnImpl: () => createMockCodexAppServerChild({ withPermission: true }),
  });

  await manager.prompt({
    instanceId: "inst-x",
    sessionId: "shared-session",
    turnId: "turn-1",
    workspace: "/tmp/ws",
    message: "first on x",
  });
  assert.equal(uiCallsA, 1);

  await manager.prompt({
    instanceId: "inst-x",
    sessionId: "shared-session",
    turnId: "turn-2",
    workspace: "/tmp/ws",
    message: "second on x",
  });
  assert.equal(uiCallsA, 1, "inst-x session cache should skip second UI prompt");

  await manager.prompt({
    instanceId: "inst-y",
    sessionId: "shared-session",
    turnId: "turn-3",
    workspace: "/tmp/ws",
    message: "first on y",
  });
  assert.equal(uiCallsB, 1, "inst-y must not inherit inst-x sessionAllow");

  manager.stopAll();
});

test("two instances use separate processes and do not cross-talk", async () => {
  let spawnSeq = 0;

  const manager = createCodexAppServerSessionManager({
    resolveCodexBin: () => "/mock/codex",
    envPath: "/usr/bin",
    onPermission: () => {},
    spawnImpl: () => {
      const n = ++spawnSeq;
      return createMockCodexAppServerChild({ replyText: `reply-from-proc-${n}` });
    },
  });

  const [a, b] = await Promise.all([
    manager.prompt({
      instanceId: "inst-1",
      sessionId: "s1",
      turnId: "t1",
      cwd: "/tmp/a",
      prompt: "a",
    }),
    manager.prompt({
      instanceId: "inst-2",
      sessionId: "s2",
      turnId: "t2",
      cwd: "/tmp/b",
      prompt: "b",
    }),
  ]);

  assert.equal(a.text, "reply-from-proc-1");
  assert.equal(b.text, "reply-from-proc-2");
  assert.notEqual(a.text, b.text);
  manager.stopAll();
});

test("stop kills process and allows restart", async () => {
  let spawnCount = 0;
  const manager = createCodexAppServerSessionManager({
    resolveCodexBin: () => "/mock/codex",
    envPath: "/usr/bin",
    onPermission: () => {},
    spawnImpl: () => {
      spawnCount += 1;
      return createMockCodexAppServerChild();
    },
  });

  await manager.prompt({
    instanceId: "inst-d",
    sessionId: "s",
    turnId: "t",
    workspace: "/tmp/ws",
    message: "a",
  });
  manager.stop("inst-d");
  await manager.prompt({
    instanceId: "inst-d",
    sessionId: "s",
    turnId: "t2",
    workspace: "/tmp/ws",
    message: "b",
  });
  assert.equal(spawnCount, 2);
  manager.stopAll();
});

test("pathWithCommonNodeBins prepends ~/.local/bin when present", async () => {
  const { pathWithCommonNodeBins } = await import("./codex_app_server_session.mjs");
  const localBin = path.join(os.homedir(), ".local", "bin");
  const result = pathWithCommonNodeBins("/usr/bin");
  if (existsSync(localBin)) {
    assert.ok(result.includes(localBin));
  }
});

test("module exports expected API", async () => {
  const mod = await import("./codex_app_server_session.mjs");
  assert.deepEqual(Object.keys(mod).sort(), [
    "createCodexAppServerSessionManager",
    "pathWithCommonNodeBins",
  ]);
});
