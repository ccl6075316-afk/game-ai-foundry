/**
 * Per-instance Codex app-server session manager (Foundry Electron).
 *
 * Spawns one `codex app-server --listen stdio://` child per Foundry instanceId,
 * runs initialize once, reuses the process for subsequent prompts, and routes
 * approval requests through onPermission / decidePermission with turn/session caches.
 */
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { existsSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  CLIENT_METHODS,
  CodexAppServerProtocolError,
  createAdapter,
  decodeLine,
  encodeRequest,
  handleInboundLine,
  nextClientId,
  resetClientIdCounter,
} from "./codex_app_server_adapter.mjs";

/** @typedef {'once' | 'turn' | 'session' | 'deny'} FoundryPermissionDecision */

/** Server notification methods used by T3 session manager. */
const CODEX_SERVER_NOTIFICATION_METHODS = Object.freeze({
  TURN_COMPLETED: "turn/completed",
  AGENT_MESSAGE_DELTA: "item/agentMessage/delta",
});

const CLIENT_INFO = Object.freeze({
  name: "game-ai-foundry",
  version: "0.0.0",
});

/**
 * @param {string} [basePath]
 * @returns {string}
 */
export function pathWithCommonNodeBins(basePath) {
  const home = os.homedir();
  const extras = [
    path.join(home, ".local", "bin"),
    path.join(process.env.ProgramFiles || "C:\\Program Files", "nodejs"),
    path.join(process.env["ProgramFiles(x86)"] || "C:\\Program Files (x86)", "nodejs"),
    path.join(process.env.LOCALAPPDATA || path.join(home, "AppData", "Local"), "Programs", "node"),
    path.join(home, "scoop", "apps", "nodejs", "current"),
    "/opt/homebrew/bin",
    "/usr/local/bin",
  ];
  const parts = String(basePath || "")
    .split(path.delimiter)
    .filter(Boolean);
  const seen = new Set(parts.map((p) => p.toLowerCase()));
  for (const dir of extras) {
    const key = dir.toLowerCase();
    if (!seen.has(key) && existsSync(dir)) {
      parts.unshift(dir);
      seen.add(key);
    }
  }
  return parts.join(path.delimiter);
}

/**
 * @param {string} codexPath
 * @param {string} envPath
 * @returns {void}
 */
function assertCodexBinary(codexPath, envPath) {
  if (path.isAbsolute(codexPath) && !existsSync(codexPath)) {
    throw new Error(
      `Codex 未找到：${codexPath}。请安装 Codex CLI 并确保 codex 在 PATH（含 ~/.local/bin）中。`,
    );
  }
  if (!envPath.includes(path.join(os.homedir(), ".local", "bin")) && codexPath === "codex") {
    // PATH helper should have added ~/.local/bin when present; no throw — spawn may still resolve.
  }
}

/**
 * @param {Record<string, unknown>} msg
 * @returns {string}
 */
function extractTextDeltaFromNotification(msg) {
  if (!msg || typeof msg !== "object") return "";
  const method = String(msg.method ?? "");
  if (method !== CODEX_SERVER_NOTIFICATION_METHODS.AGENT_MESSAGE_DELTA) return "";
  const params = msg.params && typeof msg.params === "object" ? msg.params : {};
  const delta = /** @type {Record<string, unknown>} */ (params).delta;
  return typeof delta === "string" ? delta : "";
}

/**
 * @param {object} opts
 * @param {() => string} [opts.resolveCodexBin]
 * @param {string} [opts.envPath]
 * @param {(req: {
 *   permissionId: string;
 *   instanceId: string;
 *   sessionId: string;
 *   turnId: string;
 *   summary: string;
 *   kind?: string;
 *   source: 'codex_app_server';
 * }) => void | Promise<void>} opts.onPermission
 * @param {(msg: string, ctx?: Record<string, unknown>) => void} [opts.onLog]
 * @param {typeof spawn} [opts.spawnImpl]
 */
export function createCodexAppServerSessionManager(opts) {
  const resolveCodexBin = opts.resolveCodexBin ?? (() => "codex");
  const envPath = opts.envPath ?? pathWithCommonNodeBins(process.env.PATH);
  const onPermission = opts.onPermission;
  const onLog = opts.onLog ?? (() => {});
  const spawnImpl = opts.spawnImpl ?? spawn;
  const skipBinaryCheck = opts.spawnImpl != null;

  /** @type {Map<string, InstanceState>} */
  const instances = new Map();

  /**
   * @typedef {object} InstanceState
   * @property {string} instanceId
   * @property {import('node:child_process').ChildProcessWithoutNullStreams | null} proc
   * @property {ReturnType<typeof createAdapter>} adapter
   * @property {Set<string>} sessionAllow
   * @property {Set<string>} turnAllow
   * @property {string | null} codexThreadId
   * @property {string | null} workspaceCwd
   * @property {string | null} sandboxMode
   * @property {Promise<void> | null} ready
   * @property {number} nextRpcId
   * @property {Map<string | number, { resolve: (v: unknown) => void, reject: (e: Error) => void, method: string }>} pendingRpc
   * @property {Map<string, { resolve: (d: FoundryPermissionDecision) => void, foundrySessionId: string, foundryTurnId: string }>} pendingPermissions
   * @property {string[]} stderrTail
   * @property {boolean} stopped
   * @property {string | null} currentTurnId
   * @property {string | null} currentSessionId
   * @property {string[] | undefined} [_textBuffer]
   * @property {{ resolve: (v: Record<string, unknown>) => void, reject: (e: Error) => void, threadId: string } | null} [pendingTurnCompletion]
   */

  /**
   * @param {string} instanceId
   * @returns {InstanceState}
   */
  function getOrCreateInstance(instanceId) {
    const key = String(instanceId);
    let state = instances.get(key);
    if (!state) {
      state = {
        instanceId: key,
        proc: null,
        adapter: createAdapter({
          onPermission: (req) => handlePermission(state, req),
          onMessage: (msg) => handleAdapterMessage(state, msg),
          onError: (err, ctx) => {
            onLog(`codex app-server adapter error: ${err.message}`, { instanceId: key, ...ctx });
          },
        }),
        sessionAllow: new Set(),
        turnAllow: new Set(),
        codexThreadId: null,
        workspaceCwd: null,
        sandboxMode: null,
        ready: null,
        nextRpcId: 0,
        pendingRpc: new Map(),
        pendingPermissions: new Map(),
        stderrTail: [],
        stopped: false,
        currentTurnId: null,
        currentSessionId: null,
        pendingTurnCompletion: null,
      };
      instances.set(key, state);
    }
    return state;
  }

  /**
   * @param {InstanceState} state
   * @param {ReturnType<import('./codex_app_server_adapter.mjs').normalizePermissionRequest>} req
   */
  async function handlePermission(state, req) {
    const foundrySessionId = state.currentSessionId ?? req.sessionId ?? "";
    const foundryTurnId = state.currentTurnId ?? req.turnId ?? "";

    if (foundrySessionId && state.sessionAllow.has(foundrySessionId)) {
      onLog("codex app-server permission auto-allow session cache", {
        instanceId: state.instanceId,
        permissionId: req.permissionId,
        sessionId: foundrySessionId,
      });
      sendPermissionDecision(state, req.permissionId, "session");
      return;
    }
    if (foundryTurnId && state.turnAllow.has(foundryTurnId)) {
      onLog("codex app-server permission auto-allow turn cache", {
        instanceId: state.instanceId,
        permissionId: req.permissionId,
        turnId: foundryTurnId,
      });
      sendPermissionDecision(state, req.permissionId, "turn");
      return;
    }

    await new Promise((resolve) => {
      state.pendingPermissions.set(req.permissionId, {
        resolve: (decision) => {
          sendPermissionDecision(state, req.permissionId, decision);
          resolve();
        },
        foundrySessionId,
        foundryTurnId,
      });

      Promise.resolve(
        onPermission({
          permissionId: req.permissionId,
          instanceId: state.instanceId,
          sessionId: foundrySessionId,
          turnId: foundryTurnId,
          summary: req.summary,
          kind: req.kind,
          source: "codex_app_server",
        }),
      ).catch((err) => {
        onLog(`onPermission callback failed: ${err instanceof Error ? err.message : String(err)}`, {
          instanceId: state.instanceId,
          permissionId: req.permissionId,
        });
        if (state.pendingPermissions.has(req.permissionId)) {
          sendPermissionDecision(state, req.permissionId, "deny");
        }
      });
    });
  }

  /**
   * @param {InstanceState} state
   * @param {FoundryPermissionDecision} decision
   * @param {string} permissionId
   */
  function sendPermissionDecision(state, permissionId, decision) {
    const pending = state.pendingPermissions.get(permissionId);
    if (pending) {
      state.pendingPermissions.delete(permissionId);
      if (decision === "session" && pending.foundrySessionId) {
        state.sessionAllow.add(pending.foundrySessionId);
      }
      if (decision === "turn" && pending.foundryTurnId) {
        state.turnAllow.add(pending.foundryTurnId);
      }
    }

    const line = state.adapter.respondPermission(permissionId, decision);
    if (!line) {
      onLog("codex app-server permission response skipped — unknown permissionId", {
        instanceId: state.instanceId,
        permissionId,
      });
      return;
    }
    writeStdin(state, line);
    onLog("codex app-server permission decided", {
      instanceId: state.instanceId,
      permissionId,
      decision,
    });
  }

  /**
   * @param {InstanceState} state
   * @param {Record<string, unknown>} msg
   */
  function handleAdapterMessage(state, msg) {
    const chunk = extractTextDeltaFromNotification(msg);
    if (chunk && state._textBuffer) {
      state._textBuffer.push(chunk);
    }

    const method = String(msg.method ?? "");
    if (method === CODEX_SERVER_NOTIFICATION_METHODS.TURN_COMPLETED && state.pendingTurnCompletion) {
      const params = msg.params && typeof msg.params === "object" ? msg.params : {};
      const threadId = String(/** @type {Record<string, unknown>} */ (params).threadId ?? "");
      if (!state.pendingTurnCompletion.threadId || threadId === state.pendingTurnCompletion.threadId) {
        state.pendingTurnCompletion.resolve(/** @type {Record<string, unknown>} */ (params));
        state.pendingTurnCompletion = null;
      }
    }
  }

  /**
   * @param {InstanceState} state
   * @param {string} line
   */
  function writeStdin(state, line) {
    if (!state.proc?.stdin?.writable) {
      throw new Error(`Codex app-server 进程不可用（instance=${state.instanceId}）`);
    }
    state.proc.stdin.write(line);
  }

  /**
   * @param {InstanceState} state
   * @param {string} method
   * @param {Record<string, unknown>} [params]
   * @returns {Promise<unknown>}
   */
  function rpcRequest(state, method, params = {}) {
    const id = nextClientId(++state.nextRpcId);
    return new Promise((resolve, reject) => {
      state.pendingRpc.set(id, { resolve, reject, method });
      writeStdin(state, encodeRequest(id, method, params));
    });
  }

  /**
   * @param {InstanceState} state
   * @param {Record<string, unknown>} msg
   */
  function handleRpcLine(state, msg) {
    const routeResult = handleInboundLine(msg, {
      pendingRpc: state.pendingRpc,
      adapter: state.adapter,
      onError: (err, ctx) => {
        onLog(`codex app-server inbound rpc error: ${err.message}`, { instanceId: state.instanceId, ...ctx });
      },
    });

    if (routeResult.handled === "orphan" && msg.id != null) {
      onLog("codex app-server orphan rpc response", { instanceId: state.instanceId, id: msg.id });
    }
  }

  /**
   * @param {InstanceState} state
   * @returns {Promise<void>}
   */
  function ensureProcess(state) {
    if (state.stopped) {
      state.stopped = false;
    }
    if (state.proc && !state.proc.killed && state.ready) {
      return state.ready;
    }

    const codexPath = resolveCodexBin();
    if (!skipBinaryCheck) {
      assertCodexBinary(codexPath, envPath);
    }

    state.ready = new Promise((resolve, reject) => {
      let settled = false;
      const fail = (err) => {
        if (settled) return;
        settled = true;
        reject(err instanceof Error ? err : new Error(String(err)));
      };

      try {
        state.proc = spawnImpl(codexPath, ["app-server", "--listen", "stdio://"], {
          stdio: ["pipe", "pipe", "pipe"],
          env: { ...process.env, PATH: envPath },
          shell: false,
        });
        onLog("codex app-server spawn", {
          instanceId: state.instanceId,
          command: codexPath,
          args: ["app-server", "--listen", "stdio://"],
        });
      } catch (err) {
        fail(
          new Error(
            `无法启动 Codex app-server：${err instanceof Error ? err.message : String(err)}。请确认 codex 已安装并在 PATH 中。`,
          ),
        );
        return;
      }

      if (!state.proc.stdout || !state.proc.stdin || !state.proc.stderr) {
        fail(new Error("Codex app-server 子进程 stdio 不可用"));
        return;
      }

      state.proc.on("error", (err) => {
        onLog(`codex app-server process error: ${err.message}`, { instanceId: state.instanceId });
        if (err.code === "ENOENT") {
          fail(
            new Error(
              `Codex 未找到（${codexPath}）。请安装 Codex CLI 并确保 ~/.local/bin 在 PATH 中。`,
            ),
          );
        } else {
          fail(err);
        }
      });

      state.proc.stderr.on("data", (chunk) => {
        const text = String(chunk);
        state.stderrTail.push(text);
        if (state.stderrTail.length > 20) state.stderrTail.shift();
      });

      const rl = createInterface({ input: state.proc.stdout });
      rl.on("line", (line) => {
        let msg;
        try {
          msg = decodeLine(line);
        } catch (err) {
          onLog(`codex app-server decode error: ${err instanceof Error ? err.message : String(err)}`, {
            instanceId: state.instanceId,
          });
          return;
        }
        if (!msg) return;
        handleRpcLine(state, msg);
      });

      state.proc.on("exit", (code, signal) => {
        onLog("codex app-server process exit", { instanceId: state.instanceId, code, signal });
        state.proc = null;
        state.ready = null;
        state.codexThreadId = null;
        state.workspaceCwd = null;
        state.sandboxMode = null;
        state.adapter.clearPendingPermissions();
        if (state.pendingTurnCompletion) {
          state.pendingTurnCompletion.reject(
            new Error(`Codex app-server 进程已退出（code=${code}, signal=${signal}）`),
          );
          state.pendingTurnCompletion = null;
        }
        for (const [, entry] of state.pendingPermissions) {
          entry.resolve("deny");
        }
        state.pendingPermissions.clear();
        for (const [, pending] of state.pendingRpc) {
          pending.reject(new Error(`Codex app-server 进程已退出（code=${code}, signal=${signal}）`));
        }
        state.pendingRpc.clear();
      });

      (async () => {
        try {
          await rpcRequest(state, CLIENT_METHODS.INITIALIZE, {
            clientInfo: CLIENT_INFO,
          });
          if (!settled) {
            settled = true;
            onLog("codex app-server handshake complete", { instanceId: state.instanceId });
            resolve();
          }
        } catch (err) {
          fail(err);
        }
      })();
    });

    return state.ready;
  }

  /**
   * @param {InstanceState} state
   * @param {string} workspaceCwd
   * @param {string | undefined} sandbox
   * @param {string | undefined} model
   * @returns {Promise<string>}
   */
  async function ensureThread(state, workspaceCwd, sandbox, model) {
    await ensureProcess(state);
    const cwd = path.resolve(workspaceCwd);
    const sandboxKey = sandbox ? String(sandbox) : null;

    if (state.codexThreadId && state.workspaceCwd === cwd && state.sandboxMode === sandboxKey) {
      return state.codexThreadId;
    }

    /** @type {Record<string, unknown>} */
    const params = { cwd };
    if (sandboxKey) {
      params.sandbox = sandboxKey;
    }
    if (model) {
      params.model = model;
    }

    const result = /** @type {{ thread?: { id?: string } }} */ (
      await rpcRequest(state, CLIENT_METHODS.THREAD_START, params)
    );
    const threadId = String(result?.thread?.id ?? "");
    if (!threadId) {
      throw new CodexAppServerProtocolError("thread/start 未返回 thread.id");
    }

    state.codexThreadId = threadId;
    state.workspaceCwd = cwd;
    state.sandboxMode = sandboxKey;
    onLog("codex app-server thread created", {
      instanceId: state.instanceId,
      threadId,
      cwd,
      sandbox: sandboxKey,
    });
    return threadId;
  }

  /**
   * @param {InstanceState} state
   * @param {string} threadId
   * @returns {Promise<Record<string, unknown>>}
   */
  function waitForTurnCompleted(state, threadId) {
    return new Promise((resolve, reject) => {
      state.pendingTurnCompletion = { resolve, reject, threadId };
    });
  }

  /**
   * @param {object} args
   * @param {string} args.instanceId
   * @param {string} [args.sessionId] Foundry chat session id
   * @param {string} [args.turnId] Foundry turn id (for turnAllow scope)
   * @param {string} [args.cwd]
   * @param {string} [args.workspace]
   * @param {string} [args.message]
   * @param {string} [args.prompt]
   * @param {string} [args.model]
   * @param {string} [args.sandbox]
   * @returns {Promise<{ text: string, stderrTail?: string }>}
   */
  async function prompt(args) {
    const state = getOrCreateInstance(args.instanceId);
    state.currentSessionId = String(args.sessionId ?? "");
    state.currentTurnId = String(args.turnId ?? "");

    /** @type {string[]} */
    state._textBuffer = [];

    const workspace = args.cwd ?? args.workspace;
    if (!workspace) {
      throw new Error("prompt 需要 cwd 或 workspace");
    }

    const userText = String(args.message ?? args.prompt ?? "");
    const threadId = await ensureThread(state, workspace, args.sandbox, args.model);

    const turnCompletePromise = waitForTurnCompleted(state, threadId);

    /** @type {Record<string, unknown>} */
    const turnParams = {
      threadId,
      input: [{ type: "text", text: userText }],
    };
    if (args.model) {
      turnParams.model = args.model;
    }

    await rpcRequest(state, CLIENT_METHODS.TURN_START, turnParams);
    await turnCompletePromise;

    const text = state._textBuffer.join("");
    delete state._textBuffer;
    state.currentTurnId = null;

    const stderrJoined = state.stderrTail.join("").trim();
    return {
      text,
      ...(stderrJoined ? { stderrTail: stderrJoined.slice(-2000) } : {}),
    };
  }

  /**
   * @param {{ permissionId: string, decision: FoundryPermissionDecision | string }} args
   * @returns {boolean}
   */
  function decidePermission(args) {
    const permissionId = String(args?.permissionId ?? "");
    const decisionRaw = args?.decision;
    const d = /** @type {FoundryPermissionDecision} */ (
      ["once", "turn", "session", "deny"].includes(String(decisionRaw)) ? decisionRaw : "deny"
    );

    for (const state of instances.values()) {
      const pending = state.pendingPermissions.get(permissionId);
      if (!pending) continue;
      pending.resolve(d);
      return true;
    }
    return false;
  }

  /**
   * @param {string} instanceId
   */
  function stop(instanceId) {
    const state = instances.get(String(instanceId));
    if (!state) return;

    state.stopped = true;
    state.sessionAllow.clear();
    state.turnAllow.clear();
    state.adapter.clearPendingPermissions();
    for (const [, entry] of state.pendingPermissions) {
      entry.resolve("deny");
    }
    state.pendingPermissions.clear();
    if (state.pendingTurnCompletion) {
      state.pendingTurnCompletion.reject(new Error("Codex app-server 实例已停止"));
      state.pendingTurnCompletion = null;
    }
    state.codexThreadId = null;
    state.workspaceCwd = null;
    state.sandboxMode = null;
    state.currentSessionId = null;
    state.currentTurnId = null;

    if (state.proc && !state.proc.killed) {
      try {
        state.proc.kill("SIGTERM");
      } catch {
        /* ignore */
      }
    }
    state.proc = null;
    state.ready = null;
    instances.delete(String(instanceId));
    onLog("codex app-server instance stopped", { instanceId });
  }

  function stopAll() {
    for (const instanceId of [...instances.keys()]) {
      stop(instanceId);
    }
    resetClientIdCounter();
  }

  function disposeAll() {
    stopAll();
  }

  return {
    prompt,
    decidePermission,
    stop,
    stopAll,
    disposeAll,
  };
}
