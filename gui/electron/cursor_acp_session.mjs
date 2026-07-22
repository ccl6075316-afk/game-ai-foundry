/**
 * Per-instance Cursor ACP session manager (Foundry Electron).
 *
 * Spawns one `agent acp` child per Foundry instanceId, runs handshake once,
 * reuses the process for subsequent prompts, and routes permission requests
 * through onPermission / decidePermission with turn/session allow caches.
 */
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { existsSync, readdirSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  ACP_AUTH_METHODS,
  ACP_CLIENT_CAPABILITIES,
  ACP_METHODS,
  ACP_PROTOCOL_VERSION,
  AcpProtocolError,
  acpModeIdForFoundryPermissionMode,
  createAdapter,
  decodeLine,
  encodeRequest,
} from "./cursor_acp_adapter.mjs";

/** @typedef {'once' | 'turn' | 'session' | 'deny'} FoundryPermissionDecision */

/**
 * @param {string} [basePath]
 * @returns {string}
 */
export function pathWithCommonNodeBins(basePath) {
  const home = os.homedir();
  const extras = [
    path.join(home, ".local", "bin"),
    path.join(home, ".local", "share", "cursor-agent", "versions"),
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
  try {
    const versionsRoot = path.join(home, ".local", "share", "cursor-agent", "versions");
    if (existsSync(versionsRoot)) {
      const kids = readdirSync(versionsRoot)
        .map((name) => path.join(versionsRoot, name))
        .filter((p) => existsSync(path.join(p, "cursor-agent")) || existsSync(path.join(p, "agent")));
      kids.sort();
      for (const dir of kids.slice(-3)) {
        const key = dir.toLowerCase();
        if (!seen.has(key)) {
          parts.unshift(dir);
          seen.add(key);
        }
      }
    }
  } catch {
    /* ignore */
  }
  return parts.join(path.delimiter);
}

/**
 * @param {string} agentPath
 * @param {string} envPath
 * @returns {void}
 */
function assertAgentBinary(agentPath, envPath) {
  if (path.isAbsolute(agentPath) && !existsSync(agentPath)) {
    throw new Error(
      `Cursor Agent 未找到：${agentPath}。请安装 Cursor Agent CLI 并确保 agent 在 PATH（含 ~/.local/bin）中。`,
    );
  }
  const searchDir = path.dirname(agentPath);
  if (path.isAbsolute(agentPath) && searchDir && searchDir !== "." && !existsSync(agentPath)) {
    throw new Error(
      `Cursor Agent 未找到：${agentPath}。请运行 agent login 并确认 ~/.local/bin 在 PATH 中。`,
    );
  }
  if (!envPath.includes(path.join(os.homedir(), ".local", "bin")) && agentPath === "agent") {
    // PATH helper should have added ~/.local/bin when present; no throw — spawn may still resolve via shell PATH.
  }
}

/**
 * @param {Record<string, unknown>} update
 * @returns {string}
 */
function extractTextFromSessionUpdate(update) {
  if (!update || typeof update !== "object") return "";
  const u = /** @type {Record<string, unknown>} */ (update);
  if (u.sessionUpdate === "agent_message_chunk" || u.sessionUpdate === "assistant_message_chunk") {
    const content = u.content;
    if (content && typeof content === "object" && !Array.isArray(content)) {
      const text = /** @type {Record<string, unknown>} */ (content).text;
      if (typeof text === "string") return text;
    }
  }
  if (typeof u.text === "string") return u.text;
  return "";
}

/**
 * @param {object} opts
 * @param {() => string} [opts.getAgentPath]
 * @param {string} [opts.envPath]
 * @param {(req: {
 *   permissionId: string;
 *   instanceId: string;
 *   sessionId: string;
 *   turnId: string;
 *   summary: string;
 *   source: 'cursor_acp';
 * }) => void | Promise<void>} opts.onPermission
 * @param {(msg: string, ctx?: Record<string, unknown>) => void} [opts.onLog]
 * @param {typeof spawn} [opts.spawnFn] test hook
 */
export function createCursorAcpSessionManager(opts) {
  const getAgentPath = opts.getAgentPath ?? (() => "agent");
  const envPath = opts.envPath ?? pathWithCommonNodeBins(process.env.PATH);
  const onPermission = opts.onPermission;
  const onLog = opts.onLog ?? (() => {});
  const spawnFn = opts.spawnFn ?? spawn;
  const skipBinaryCheck = opts.spawnFn != null;

  /** @type {Map<string, InstanceState>} */
  const instances = new Map();

  /**
   * @typedef {object} InstanceState
   * @property {string} instanceId
   * @property {import('node:child_process').ChildProcessWithoutNullStreams | null} proc
   * @property {ReturnType<typeof createAdapter>} adapter
   * @property {Set<string>} sessionAllow
   * @property {Set<string>} turnAllow
   * @property {string | null} acpSessionId
   * @property {string | null} acpModeId
   * @property {string | null} workspaceCwd
   * @property {Promise<void> | null} ready
   * @property {number} nextRpcId
   * @property {Map<string | number, { resolve: (v: unknown) => void, reject: (e: Error) => void, method: string }>} pendingRpc
   * @property {Map<string, { resolve: (d: FoundryPermissionDecision) => void, foundrySessionId: string, foundryTurnId: string }>} pendingPermissions
   * @property {string[]} stderrTail
   * @property {boolean} stopped
   * @property {string | null} currentTurnId
   * @property {string | null} currentSessionId
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
            onLog(`acp adapter error: ${err.message}`, { instanceId: key, ...ctx });
          },
        }),
        sessionAllow: new Set(),
        turnAllow: new Set(),
        acpSessionId: null,
        acpModeId: null,
        workspaceCwd: null,
        ready: null,
        nextRpcId: 0,
        pendingRpc: new Map(),
        pendingPermissions: new Map(),
        stderrTail: [],
        stopped: false,
        currentTurnId: null,
        currentSessionId: null,
      };
      instances.set(key, state);
    }
    return state;
  }

  /**
   * @param {InstanceState} state
   * @param {ReturnType<import('./cursor_acp_adapter.mjs').normalizePermissionRequest>} req
   */
  async function handlePermission(state, req) {
    const foundrySessionId = state.currentSessionId ?? req.sessionId ?? "";
    const foundryTurnId = state.currentTurnId ?? "";

    if (foundrySessionId && state.sessionAllow.has(foundrySessionId)) {
      onLog("acp permission auto-allow session cache", {
        instanceId: state.instanceId,
        permissionId: req.permissionId,
        sessionId: foundrySessionId,
      });
      sendPermissionDecision(state, req.permissionId, "session");
      return;
    }
    if (foundryTurnId && state.turnAllow.has(foundryTurnId)) {
      onLog("acp permission auto-allow turn cache", {
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
          source: "cursor_acp",
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
      onLog("acp permission response skipped — unknown permissionId", {
        instanceId: state.instanceId,
        permissionId,
      });
      return;
    }
    writeStdin(state, line);
    onLog("acp permission decided", {
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
    if (msg.method === ACP_METHODS.SESSION_UPDATE) {
      const params = msg.params && typeof msg.params === "object" ? msg.params : {};
      const update = /** @type {Record<string, unknown>} */ (params).update;
      const chunk = extractTextFromSessionUpdate(update);
      if (chunk && state._textBuffer) {
        state._textBuffer.push(chunk);
      }
    }
  }

  /**
   * @param {InstanceState} state
   * @param {string} line
   */
  function writeStdin(state, line) {
    if (!state.proc?.stdin?.writable) {
      throw new Error(`ACP 进程不可用（instance=${state.instanceId}）`);
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
    // String client ids avoid colliding with agent-assigned numeric request ids
    // (e.g. session/request_permission).
    const id = `gaf-${++state.nextRpcId}`;
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
    // Inbound requests/notifications from agent MUST be handled before response matching.
    // Agent uses numeric JSON-RPC ids that can collide with ours; a permission request
    // must never be treated as the reply to session/prompt.
    if (typeof msg.method === "string") {
      state.adapter.feedLine(JSON.stringify(msg)).catch((err) => {
        onLog(`adapter feed failed: ${err instanceof Error ? err.message : String(err)}`, {
          instanceId: state.instanceId,
        });
      });
      return;
    }

    const rpcId = msg.id;
    const isResponse =
      rpcId != null && (Object.prototype.hasOwnProperty.call(msg, "result") || msg.error != null);
    if (isResponse && state.pendingRpc.has(rpcId)) {
      const pending = state.pendingRpc.get(rpcId);
      state.pendingRpc.delete(rpcId);
      if (msg.error) {
        const errObj = msg.error && typeof msg.error === "object" ? msg.error : {};
        const message = String(/** @type {Record<string, unknown>} */ (errObj).message ?? "ACP RPC error");
        pending.reject(new AcpProtocolError(message, { method: pending.method, error: msg.error }));
      } else {
        pending.resolve(msg.result);
      }
      return;
    }

    if (msg.id != null) {
      onLog("acp orphan rpc response", { instanceId: state.instanceId, id: msg.id });
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

    const agentPath = getAgentPath();
    if (!skipBinaryCheck) {
      assertAgentBinary(agentPath, envPath);
    }

    state.ready = new Promise((resolve, reject) => {
      let settled = false;
      const fail = (err) => {
        if (settled) return;
        settled = true;
        reject(err instanceof Error ? err : new Error(String(err)));
      };

      try {
        state.proc = spawnFn(agentPath, ["acp"], {
          stdio: ["pipe", "pipe", "pipe"],
          env: { ...process.env, PATH: envPath },
          shell: false,
        });
      } catch (err) {
        fail(
          new Error(
            `无法启动 Cursor Agent ACP：${err instanceof Error ? err.message : String(err)}。请确认 agent 已安装并在 PATH 中。`,
          ),
        );
        return;
      }

      if (!state.proc.stdout || !state.proc.stdin || !state.proc.stderr) {
        fail(new Error("ACP 子进程 stdio 不可用"));
        return;
      }

      state.proc.on("error", (err) => {
        onLog(`acp process error: ${err.message}`, { instanceId: state.instanceId });
        if (err.code === "ENOENT") {
          fail(
            new Error(
              `Cursor Agent 未找到（${agentPath}）。请安装 Cursor Agent CLI 并确保 ~/.local/bin 在 PATH 中。`,
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
          onLog(`acp decode error: ${err instanceof Error ? err.message : String(err)}`, {
            instanceId: state.instanceId,
          });
          return;
        }
        if (!msg) return;
        handleRpcLine(state, msg);
      });

      state.proc.on("exit", (code, signal) => {
        onLog("acp process exit", { instanceId: state.instanceId, code, signal });
        state.proc = null;
        state.ready = null;
        state.acpSessionId = null;
        state.acpModeId = null;
        state.adapter.clearPendingPermissions();
        for (const [, entry] of state.pendingPermissions) {
          entry.resolve("deny");
        }
        state.pendingPermissions.clear();
        for (const [, pending] of state.pendingRpc) {
          pending.reject(new Error(`ACP 进程已退出（code=${code}, signal=${signal}）`));
        }
        state.pendingRpc.clear();
      });

      (async () => {
        try {
          await rpcRequest(state, ACP_METHODS.INITIALIZE, {
            protocolVersion: ACP_PROTOCOL_VERSION,
            clientCapabilities: ACP_CLIENT_CAPABILITIES,
          });
          await rpcRequest(state, ACP_METHODS.AUTHENTICATE, { methodId: ACP_AUTH_METHODS.CURSOR_LOGIN });
          if (!settled) {
            settled = true;
            onLog("acp handshake complete", { instanceId: state.instanceId });
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
   * @param {string} [foundryPermissionMode]
   */
  async function ensureAcpSession(state, workspaceCwd, foundryPermissionMode) {
    await ensureProcess(state);
    const cwd = path.resolve(workspaceCwd);
    const desiredMode = acpModeIdForFoundryPermissionMode(foundryPermissionMode);
    if (state.acpSessionId && state.workspaceCwd === cwd) {
      if (state.acpModeId !== desiredMode) {
        await rpcRequest(state, ACP_METHODS.SESSION_SET_MODE, {
          sessionId: state.acpSessionId,
          modeId: desiredMode,
        });
        state.acpModeId = desiredMode;
        onLog("acp mode updated", { instanceId: state.instanceId, modeId: desiredMode });
      }
      return state.acpSessionId;
    }
    const result = /** @type {{ sessionId?: string, modes?: { currentModeId?: string } }} */ (
      await rpcRequest(state, ACP_METHODS.SESSION_NEW, { cwd, mcpServers: [] })
    );
    const acpSessionId = String(result?.sessionId ?? "");
    if (!acpSessionId) {
      throw new AcpProtocolError("session/new 未返回 sessionId");
    }
    state.acpSessionId = acpSessionId;
    state.workspaceCwd = cwd;
    const current = String(result?.modes?.currentModeId || "agent");
    if (desiredMode !== current) {
      await rpcRequest(state, ACP_METHODS.SESSION_SET_MODE, {
        sessionId: acpSessionId,
        modeId: desiredMode,
      });
    }
    state.acpModeId = desiredMode;
    onLog("acp session created", {
      instanceId: state.instanceId,
      acpSessionId,
      cwd,
      modeId: desiredMode,
    });
    return acpSessionId;
  }

  /**
   * @param {object} args
   * @param {string} args.instanceId
   * @param {string} args.sessionId Foundry chat session id
   * @param {string} args.turnId Foundry turn id (for turnAllow scope)
   * @param {string} args.workspaceCwd
   * @param {string} args.text
   * @param {string} [args.model]
   * @param {string} [args.permissionMode] Foundry permission_mode (plan|ask|auto_review)
   * @returns {Promise<{ text: string, stderrTail?: string }>}
   */
  async function prompt(args) {
    const state = getOrCreateInstance(args.instanceId);
    state.currentSessionId = String(args.sessionId ?? "");
    state.currentTurnId = String(args.turnId ?? "");

    /** @type {string[]} */
    state._textBuffer = [];

    const acpSessionId = await ensureAcpSession(
      state,
      args.workspaceCwd,
      args.permissionMode,
    );
    const params = {
      sessionId: acpSessionId,
      prompt: [{ type: "text", text: String(args.text ?? "") }],
    };
    if (args.model) {
      params.model = args.model;
    }

    await rpcRequest(state, ACP_METHODS.SESSION_PROMPT, params);

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
   * @param {string} permissionId
   * @param {FoundryPermissionDecision} decision
   * @returns {boolean}
   */
  function decidePermission(permissionId, decision) {
    const d = /** @type {FoundryPermissionDecision} */ (
      ["once", "turn", "session", "deny"].includes(decision) ? decision : "deny"
    );

    for (const state of instances.values()) {
      const pending = state.pendingPermissions.get(String(permissionId));
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
    state.acpSessionId = null;
    state.acpModeId = null;
    state.workspaceCwd = null;
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
    onLog("acp instance stopped", { instanceId });
  }

  function stopAll() {
    for (const instanceId of [...instances.keys()]) {
      stop(instanceId);
    }
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
