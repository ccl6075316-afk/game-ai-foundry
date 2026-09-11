import assert from "node:assert/strict";
import { PassThrough } from "node:stream";
import test from "node:test";

import { createPiRpcSessionManager, getLastAssistantText, resolvePiSessionPathFromState } from "./pi_rpc_session.mjs";

/** @param {PassThrough} stdout @param {Record<string, unknown>} msg */
function emitLine(stdout, msg) {
  queueMicrotask(() => stdout.write(`${JSON.stringify(msg)}\n`));
}

/**
 * Minimal mock Pi RPC child: NDJSON over stdio.
 * @param {object} [opts]
 * @param {boolean} [opts.crashAfterPrompt]
 * @param {boolean} [opts.fallbackMessages]
 * @param {string} [opts.assistantText]
 */
function createMockPiRpcChild(opts = {}) {
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

  let sessionId = "mock-pi-session";
  let promptCount = 0;

  stdin.on("data", (chunk) => {
    for (const line of String(chunk).split("\n").filter(Boolean)) {
      const cmd = JSON.parse(line);
      const { id, type } = cmd;

      if (type === "get_state") {
        emitLine(stdout, {
          type: "response",
          id,
          command: "get_state",
          success: true,
          data: {
            sessionId,
            sessionFile: `/tmp/${sessionId}.jsonl`,
            thinkingLevel: "off",
            isStreaming: false,
            isCompacting: false,
            steeringMode: "one-at-a-time",
            followUpMode: "one-at-a-time",
            autoCompactionEnabled: true,
            messageCount: 0,
            pendingMessageCount: 0,
          },
        });
        continue;
      }

      if (type === "new_session") {
        sessionId = `mock-pi-session-${Date.now()}`;
        emitLine(stdout, {
          type: "response",
          id,
          command: "new_session",
          success: true,
          data: { cancelled: false },
        });
        continue;
      }

      if (type === "switch_session") {
        sessionId = String(cmd.sessionPath || "switched-session");
        emitLine(stdout, {
          type: "response",
          id,
          command: "switch_session",
          success: true,
          data: { cancelled: false },
        });
        continue;
      }

      if (type === "get_messages") {
        const assistantText = opts.assistantText ?? "from get_messages";
        emitLine(stdout, {
          type: "response",
          id,
          command: "get_messages",
          success: true,
          data: {
            messages: opts.fallbackMessages
              ? [{ role: "assistant", content: assistantText }]
              : [],
          },
        });
        continue;
      }

      if (type === "prompt") {
        promptCount += 1;
        const reply = opts.assistantText ?? `hello from mock pi #${promptCount}`;
        if (!opts.fallbackMessages) {
          emitLine(stdout, {
            type: "agent_message_chunk",
            content: { type: "text", text: reply },
          });
        }
        emitLine(stdout, {
          type: "extension_ui_request",
          id: "1",
          method: "notify",
          message: "side channel",
        });
        emitLine(stdout, { type: "agent_settled" });
        emitLine(stdout, { type: "response", id, command: "prompt", success: true });
        if (opts.crashAfterPrompt) {
          queueMicrotask(() => proc.emit("exit", 1, null));
        }
        continue;
      }

      if (type === "abort") {
        emitLine(stdout, { type: "response", id, command: "abort", success: true });
      }

      if (type === "extension_ui_response") {
        // S1 auto-confirm — no reply expected
      }
    }
  });

  return proc;
}

const MOCK_LAUNCH = {
  entry: "/mock/rpc-entry.js",
  args: [],
  cwd: "/tmp/pi",
};

test("createPiRpcSessionManager prompt returns aggregated text", async () => {
  const manager = createPiRpcSessionManager({
    getCliLaunch: () => MOCK_LAUNCH,
    getSpawnEnv: () => ({ ...process.env }),
    spawnFn: () => createMockPiRpcChild(),
  });

  const result = await manager.prompt({
    instanceId: "inst-a",
    message: "hi",
  });

  assert.equal(result.text, "hello from mock pi #1");
  assert.ok(result.piSessionPath);
  manager.stopAll();
});

test("extension_ui_request numeric id does not steal pending prompt response", async () => {
  const manager = createPiRpcSessionManager({
    getCliLaunch: () => MOCK_LAUNCH,
    getSpawnEnv: () => ({ ...process.env }),
    spawnFn: () => createMockPiRpcChild(),
  });

  const result = await manager.prompt({
    instanceId: "inst-collide",
    message: "run",
  });

  assert.equal(result.text, "hello from mock pi #1");
  manager.stopAll();
});

test("prompt falls back to get_messages when no chunks", async () => {
  const manager = createPiRpcSessionManager({
    getCliLaunch: () => MOCK_LAUNCH,
    getSpawnEnv: () => ({ ...process.env }),
    spawnFn: () => createMockPiRpcChild({ fallbackMessages: true, assistantText: "fallback text" }),
  });

  const result = await manager.prompt({
    instanceId: "inst-fallback",
    message: "hi",
  });

  assert.equal(result.text, "fallback text");
  manager.stopAll();
});

test("getLastAssistantText extracts trailing assistant message", () => {
  const text = getLastAssistantText([
    { role: "user", content: "q" },
    { role: "assistant", content: [{ type: "text", text: "part1" }, { type: "text", text: "part2" }] },
    { role: "user", content: "q2" },
    { role: "assistant", content: "final" },
  ]);
  assert.equal(text, "final");
});

test("switch_session when piSessionPath provided", async () => {
  /** @type {string[]} */
  const written = [];
  const child = createMockPiRpcChild();
  const origWrite = child.stdin.write.bind(child.stdin);
  child.stdin.write = (chunk) => {
    written.push(String(chunk));
    return origWrite(chunk);
  };

  const manager = createPiRpcSessionManager({
    getCliLaunch: () => MOCK_LAUNCH,
    getSpawnEnv: () => ({ ...process.env }),
    spawnFn: () => child,
  });

  const result = await manager.prompt({
    instanceId: "inst-switch",
    message: "hi",
    piSessionPath: "/tmp/custom-session.json",
  });

  assert.equal(result.piSessionPath, "/tmp/custom-session.json");
  assert.ok(written.some((line) => line.includes('"type":"switch_session"')));
  manager.stopAll();
});

test("crash rebuild spawns new process on next prompt", async () => {
  let spawnCount = 0;
  const manager = createPiRpcSessionManager({
    getCliLaunch: () => MOCK_LAUNCH,
    getSpawnEnv: () => ({ ...process.env }),
    spawnFn: () => {
      spawnCount += 1;
      return createMockPiRpcChild({ crashAfterPrompt: spawnCount === 1 });
    },
  });

  const first = await manager.prompt({
    instanceId: "inst-crash",
    message: "first",
  });
  assert.equal(first.text, "hello from mock pi #1");
  assert.equal(spawnCount, 1);

  const second = await manager.prompt({
    instanceId: "inst-crash",
    message: "second",
  });
  assert.equal(second.text, "hello from mock pi #1");
  assert.equal(spawnCount, 2, "should respawn after crash");
  manager.stopAll();
});

test("stop clears instance and allows restart", async () => {
  let spawnCount = 0;
  const manager = createPiRpcSessionManager({
    getCliLaunch: () => MOCK_LAUNCH,
    getSpawnEnv: () => ({ ...process.env }),
    spawnFn: () => {
      spawnCount += 1;
      return createMockPiRpcChild();
    },
  });

  await manager.prompt({
    instanceId: "inst-d",
    message: "a",
  });
  manager.stop("inst-d");
  await manager.prompt({
    instanceId: "inst-d",
    message: "b",
  });
  assert.equal(spawnCount, 2);
  manager.stopAll();
});

test("module exports expected API", async () => {
  const mod = await import("./pi_rpc_session.mjs");
  assert.deepEqual(Object.keys(mod).sort(), [
    "createPiRpcSessionManager",
    "getLastAssistantText",
    "resolvePiSessionPathFromState",
  ]);
});

test("resolvePiSessionPathFromState prefers sessionFile", () => {
  assert.equal(
    resolvePiSessionPathFromState({
      sessionId: "sid-1",
      sessionFile: "/tmp/pi-sess.jsonl",
    }),
    "/tmp/pi-sess.jsonl",
  );
  assert.equal(resolvePiSessionPathFromState({ sessionId: "sid-only" }), "sid-only");
  assert.equal(resolvePiSessionPathFromState(null), null);
});

test("new_session stores sessionFile path", async () => {
  const manager = createPiRpcSessionManager({
    getCliLaunch: () => MOCK_LAUNCH,
    getSpawnEnv: () => ({ ...process.env }),
    spawnFn: () => createMockPiRpcChild(),
  });
  const result = await manager.prompt({
    instanceId: "inst-file-path",
    message: "hi",
  });
  assert.match(String(result.piSessionPath || ""), /\/tmp\/mock-pi-session.*\.jsonl/);
  manager.stopAll();
});

test("authEnv change respawns process", async () => {
  let spawnCount = 0;
  /** @type {NodeJS.ProcessEnv[]} */
  const envs = [];
  const manager = createPiRpcSessionManager({
    getCliLaunch: () => MOCK_LAUNCH,
    getSpawnEnv: () => ({ BASE: "1" }),
    spawnFn: (_cmd, _args, opts) => {
      spawnCount += 1;
      envs.push({ ...(opts?.env || {}) });
      return createMockPiRpcChild();
    },
  });

  await manager.prompt({
    instanceId: "inst-auth",
    message: "a",
    authEnv: { KEY: "one" },
  });
  await manager.prompt({
    instanceId: "inst-auth",
    message: "b",
    authEnv: { KEY: "two" },
  });
  assert.equal(spawnCount, 2);
  assert.equal(envs[0]?.KEY, "one");
  assert.equal(envs[1]?.KEY, "two");
  manager.stopAll();
});

test("listMessages returns mapped history", async () => {
  const manager = createPiRpcSessionManager({
    getCliLaunch: () => MOCK_LAUNCH,
    getSpawnEnv: () => ({ ...process.env }),
    spawnFn: () =>
      createMockPiRpcChild({
        fallbackMessages: true,
        assistantText: "hist",
      }),
  });
  const out = await manager.listMessages({ instanceId: "inst-list" });
  assert.equal(out.messages.length, 1);
  assert.ok(out.piSessionPath);
  manager.stopAll();
});
