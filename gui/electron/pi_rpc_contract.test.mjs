import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { PassThrough } from "node:stream";
import test from "node:test";

import {
  DEFAULT_RUNTIME,
  loadEmbedManifest,
  resolvePiCliJs,
  resolvePiRpcEntry,
  resolvePiRpcSpawnLaunch,
  resolvePiRuntimeRoot,
} from "./pi_rpc_paths.mjs";

/** @param {PassThrough} stdout @param {Record<string, unknown>} msg */
function emitLine(stdout, msg) {
  queueMicrotask(() => stdout.write(`${JSON.stringify(msg)}\n`));
}

/**
 * Minimal Pi RPC line client mirroring official RpcClient.handleLine.
 * Foundry uses string id prefix `gaf-pi-N` per critical-patterns.
 * @param {import("node:stream").Writable & { write: (chunk: string) => boolean }} stdin
 * @param {{ idPrefix?: string }} [opts]
 */
function createPiRpcLineClient(stdin, opts = {}) {
  const idPrefix = opts.idPrefix ?? "gaf-pi-";
  /** @type {Map<string, { resolve: (v: unknown) => void; reject: (e: Error) => void }>} */
  const pendingRequests = new Map();
  /** @type {Record<string, unknown>[]} */
  const events = [];
  let seq = 0;

  const handleLine = (line) => {
    const data = JSON.parse(line);
    if (data.type === "response" && data.id && pendingRequests.has(data.id)) {
      const pending = pendingRequests.get(data.id);
      pendingRequests.delete(data.id);
      pending.resolve(data);
      return;
    }
    events.push(data);
  };

  const send = (command) => {
    const id = `${idPrefix}${++seq}`;
    const fullCommand = { ...command, id };
    return new Promise((resolve, reject) => {
      pendingRequests.set(id, { resolve, reject });
      stdin.write(`${JSON.stringify(fullCommand)}\n`);
    });
  };

  return { send, handleLine, events, pendingRequests };
}

/** Minimal mock Pi RPC child: NDJSON over stdio. */
function createMockPiRpcChild() {
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
        emitLine(stdout, {
          type: "response",
          id,
          command: "get_messages",
          success: true,
          data: { messages: [] },
        });
        continue;
      }

      if (type === "prompt") {
        emitLine(stdout, {
          type: "agent_message_chunk",
          content: { type: "text", text: "hello from mock pi" },
        });
        emitLine(stdout, {
          type: "extension_ui_request",
          id: "1",
          method: "notify",
          message: "side channel",
        });
        emitLine(stdout, { type: "agent_settled" });
        emitLine(stdout, { type: "response", id, command: "prompt", success: true });
        continue;
      }

      if (type === "abort") {
        emitLine(stdout, { type: "response", id, command: "abort", success: true });
      }
    }
  });

  return proc;
}

/** @param {import("node:stream").Readable} stream @param {(line: string) => void} onLine */
function attachLineReader(stream, onLine) {
  let buffer = "";
  stream.on("data", (chunk) => {
    buffer += String(chunk);
    while (true) {
      const idx = buffer.indexOf("\n");
      if (idx === -1) {
        return;
      }
      const line = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 1);
      if (line) {
        onLine(line);
      }
    }
  });
}

test("resolvePiRuntimeRoot finds embed when present", () => {
  const root = resolvePiRuntimeRoot();
  if (existsSync(DEFAULT_RUNTIME)) {
    assert.equal(root, DEFAULT_RUNTIME);
    assert.ok(resolvePiCliJs(root));
    assert.ok(resolvePiRpcEntry(root));
  } else {
    assert.equal(root, null);
  }
});

test("loadEmbedManifest exposes package entry", () => {
  const root = resolvePiRuntimeRoot();
  if (!root) {
    return;
  }
  const manifest = loadEmbedManifest(root);
  assert.ok(manifest);
  assert.equal(manifest.package, "@earendil-works/pi-coding-agent");
  assert.match(String(manifest.entry || ""), /cli\.js$/);
});

test("resolvePiRpcSpawnLaunch covers rpc-entry and cli-rpc", () => {
  const root = resolvePiRuntimeRoot();
  if (!root) {
    return;
  }
  const viaEntry = resolvePiRpcSpawnLaunch({ root, mode: "rpc-entry" });
  assert.ok(viaEntry);
  assert.ok(viaEntry.entry.endsWith("rpc-entry.js"));
  assert.deepEqual(viaEntry.args, []);

  const viaCli = resolvePiRpcSpawnLaunch({ root, mode: "cli-rpc" });
  assert.ok(viaCli);
  assert.ok(viaCli.entry.endsWith("cli.js"));
  assert.deepEqual(viaCli.args.slice(0, 2), ["--mode", "rpc"]);
});

test("mock child: get_state and new_session roundtrip", async () => {
  const proc = createMockPiRpcChild();
  const client = createPiRpcLineClient(proc.stdin);
  attachLineReader(proc.stdout, client.handleLine);

  const stateResp = await client.send({ type: "get_state" });
  assert.equal(stateResp.command, "get_state");
  assert.equal(stateResp.success, true);
  assert.equal(stateResp.data.sessionId, "mock-pi-session");

  const newResp = await client.send({ type: "new_session" });
  assert.equal(newResp.command, "new_session");
  assert.equal(newResp.data.cancelled, false);

  const state2 = await client.send({ type: "get_state" });
  assert.notEqual(state2.data.sessionId, "mock-pi-session");
});

test("mock child: prompt response vs events are split by type", async () => {
  const proc = createMockPiRpcChild();
  const client = createPiRpcLineClient(proc.stdin);
  attachLineReader(proc.stdout, client.handleLine);

  const promptResp = await client.send({ type: "prompt", message: "hi" });
  assert.equal(promptResp.command, "prompt");
  assert.equal(promptResp.success, true);

  const types = client.events.map((e) => e.type);
  assert.ok(types.includes("agent_message_chunk"));
  assert.ok(types.includes("agent_settled"));
  assert.ok(types.includes("extension_ui_request"));
  assert.equal(client.pendingRequests.size, 0);
});

test("extension_ui_request id does not steal pending command response", async () => {
  const proc = createMockPiRpcChild();
  const client = createPiRpcLineClient(proc.stdin, { idPrefix: "gaf-pi-" });
  attachLineReader(proc.stdout, client.handleLine);

  const sendPromise = client.send({ type: "prompt", message: "run" });
  assert.equal(client.pendingRequests.size, 1);

  const promptResp = await sendPromise;
  assert.equal(promptResp.id, "gaf-pi-1");
  assert.equal(promptResp.command, "prompt");

  const uiEvent = client.events.find((e) => e.type === "extension_ui_request");
  assert.ok(uiEvent);
  assert.equal(uiEvent.id, "1");
  assert.notEqual(uiEvent.id, promptResp.id);
});

test("outbound commands carry gaf-pi- string id prefix", async () => {
  /** @type {string[]} */
  const written = [];
  const stdin = new PassThrough();
  stdin.write = (chunk) => {
    written.push(String(chunk));
    return true;
  };
  const client = createPiRpcLineClient(stdin);
  const stdout = new PassThrough();
  attachLineReader(stdout, client.handleLine);

  const pending = client.send({ type: "abort" });
  emitLine(stdout, { type: "response", id: "gaf-pi-1", command: "abort", success: true });
  const resp = await pending;

  assert.match(String(written[0]), /"id":"gaf-pi-1"/);
  assert.equal(resp.command, "abort");
});

test(
  "live spawn: rpc-entry accepts get_state when GAMEFACTORY_PI_RPC_LIVE=1",
  { skip: process.env.GAMEFACTORY_PI_RPC_LIVE !== "1" },
  async () => {
    const launch = resolvePiRpcSpawnLaunch({ mode: "rpc-entry" });
    assert.ok(launch, "embed rpc-entry missing");

    const child = spawn(process.execPath, [launch.entry, ...launch.args], {
      cwd: launch.cwd,
      stdio: ["pipe", "pipe", "pipe"],
      env: { ...process.env },
    });

    /** @type {Record<string, unknown>[]} */
    const lines = [];
    attachLineReader(child.stdout, (line) => lines.push(JSON.parse(line)));

    await new Promise((r) => setTimeout(r, 200));
    assert.equal(child.exitCode, null, "process exited before handshake");

    child.stdin.write(`${JSON.stringify({ type: "get_state", id: "gaf-pi-live-1" })}\n`);

    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("live get_state timeout")), 5000);
      const check = () => {
        const hit = lines.find(
          (l) => l.type === "response" && l.id === "gaf-pi-live-1" && l.command === "get_state"
        );
        if (hit) {
          clearTimeout(timer);
          assert.equal(hit.success, true);
          resolve();
        }
      };
      const iv = setInterval(() => {
        check();
        if (lines.some((l) => l.type === "response" && l.id === "gaf-pi-live-1")) {
          clearInterval(iv);
        }
      }, 50);
      setTimeout(() => {
        clearInterval(iv);
        check();
        reject(new Error("no get_state response"));
      }, 5000);
    });

    child.kill("SIGTERM");
  }
);

test("module exports expected pi_rpc_paths API", async () => {
  const mod = await import("./pi_rpc_paths.mjs");
  assert.deepEqual(Object.keys(mod).sort(), [
    "DEFAULT_RUNTIME",
    "ENTRY_REL",
    "REPO_ROOT",
    "RPC_ENTRY_REL",
    "loadEmbedManifest",
    "resolvePiCliJs",
    "resolvePiRpcEntry",
    "resolvePiRpcSpawnLaunch",
    "resolvePiRuntimeRoot",
  ]);
});
