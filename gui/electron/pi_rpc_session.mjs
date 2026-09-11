/**
 * Per-instance Pi RPC session manager (Foundry Electron).
 *
 * Spawns one Pi `--mode rpc` child per Foundry instanceId, reuses the process
 * for subsequent prompts, and routes NDJSON per pi_rpc_protocol.md (not ACP).
 */
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";

import { killChildTree } from "./process_kill.mjs";

const ID_PREFIX = "gaf-pi-";
const STDERR_TAIL_LINES = 20;
const STDERR_TAIL_CHARS = 2000;

/**
 * @param {Record<string, unknown>} event
 * @returns {string}
 */
function extractTextFromAgentChunk(event) {
  if (!event || typeof event !== "object") return "";
  const content = /** @type {Record<string, unknown>} */ (event).content;
  if (content && typeof content === "object" && !Array.isArray(content)) {
    const text = /** @type {Record<string, unknown>} */ (content).text;
    if (typeof text === "string") return text;
  }
  if (typeof /** @type {Record<string, unknown>} */ (event).text === "string") {
    return /** @type {Record<string, unknown>} */ (event).text;
  }
  return "";
}

/**
 * @param {unknown} msg
 * @returns {string}
 */
function extractAssistantMessageText(msg) {
  if (!msg || typeof msg !== "object") return "";
  const m = /** @type {Record<string, unknown>} */ (msg);
  if (typeof m.content === "string") return m.content;
  if (Array.isArray(m.content)) {
    return m.content
      .map((part) => {
        if (!part || typeof part !== "object") return "";
        const p = /** @type {Record<string, unknown>} */ (part);
        if (typeof p.text === "string") return p.text;
        return "";
      })
      .join("");
  }
  if (m.content && typeof m.content === "object" && !Array.isArray(m.content)) {
    const text = /** @type {Record<string, unknown>} */ (m.content).text;
    if (typeof text === "string") return text;
  }
  return "";
}

/**
 * @param {unknown[]} messages
 * @returns {string}
 */
export function getLastAssistantText(messages) {
  if (!Array.isArray(messages)) return "";
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const msg = messages[i];
    const role = msg && typeof msg === "object" ? /** @type {Record<string, unknown>} */ (msg).role : null;
    if (role === "assistant") {
      const text = extractAssistantMessageText(msg);
      if (text) return text;
    }
  }
  return "";
}

/**
 * @param {object} opts
 * @param {() => { entry: string, args: string[], cwd: string } | null} opts.getCliLaunch
 * @param {() => NodeJS.ProcessEnv} [opts.getSpawnEnv]
 * @param {(msg: string, ctx?: Record<string, unknown>) => void} [opts.onLog]
 * @param {typeof spawn} [opts.spawnFn]
 */
export function createPiRpcSessionManager(opts) {
  const getCliLaunch = opts.getCliLaunch;
  const getSpawnEnv = opts.getSpawnEnv ?? (() => ({ ...process.env }));
  const onLog = opts.onLog ?? (() => {});
  const spawnFn = opts.spawnFn ?? spawn;

  /** @type {Map<string, InstanceState>} */
  const instances = new Map();

  /**
   * @typedef {object} InstanceState
   * @property {string} instanceId
   * @property {import("node:child_process").ChildProcessWithoutNullStreams | null} proc
   * @property {Promise<void> | null} ready
   * @property {number} nextId
   * @property {Map<string, { resolve: (v: unknown) => void, reject: (e: Error) => void, command: string }>} pendingRequests
   * @property {string[]} stderrTail
   * @property {boolean} stopped
   * @property {string | null} piSessionPath
   * @property {Record<string, string> | null} authEnv
   * @property {string | null} authEnvFp
   * @property {(() => void) | null} settleResolve
   * @property {Promise<void> | null} settledPromise
   * @property {string[] | undefined} textBuffer
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
        ready: null,
        nextId: 0,
        pendingRequests: new Map(),
        stderrTail: [],
        stopped: false,
        piSessionPath: null,
        authEnv: null,
        authEnvFp: null,
        settleResolve: null,
        settledPromise: null,
        textBuffer: undefined,
      };
      instances.set(key, state);
    }
    return state;
  }

  /**
   * @param {InstanceState} state
   * @param {string} line
   */
  function writeStdin(state, line) {
    if (!state.proc?.stdin?.writable) {
      throw new Error(`Pi RPC 进程不可用（instance=${state.instanceId}）`);
    }
    state.proc.stdin.write(line);
  }

  /**
   * @param {InstanceState} state
   * @param {Record<string, unknown>} command
   * @returns {Promise<Record<string, unknown>>}
   */
  function sendCommand(state, command) {
    const id = `${ID_PREFIX}${++state.nextId}`;
    const fullCommand = { ...command, id };
    return new Promise((resolve, reject) => {
      state.pendingRequests.set(id, {
        resolve: (v) => resolve(/** @type {Record<string, unknown>} */ (v)),
        reject,
        command: String(command.type ?? ""),
      });
      writeStdin(state, `${JSON.stringify(fullCommand)}\n`);
    });
  }

  /**
   * @param {InstanceState} state
   * @param {Record<string, unknown>} data
   */
  function handleExtensionUiRequest(state, data) {
    const reqId = data.id;
    onLog("pi rpc extension_ui_request auto-confirmed", {
      instanceId: state.instanceId,
      phase: "prompt",
      method: data.method,
      id: reqId,
    });
    if (reqId == null) return;
    writeStdin(
      state,
      `${JSON.stringify({ type: "extension_ui_response", id: reqId, confirmed: true })}\n`,
    );
  }

  /**
   * @param {InstanceState} state
   * @param {Record<string, unknown>} data
   */
  function handleEvent(state, data) {
    if (data.type === "agent_message_chunk") {
      const chunk = extractTextFromAgentChunk(data);
      if (chunk && state.textBuffer) {
        state.textBuffer.push(chunk);
      }
      return;
    }
    if (data.type === "agent_settled") {
      if (state.settleResolve) {
        const resolve = state.settleResolve;
        state.settleResolve = null;
        state.settledPromise = null;
        resolve();
      }
    }
  }

  /**
   * @param {InstanceState} state
   * @param {string} line
   */
  function handleLine(state, line) {
    /** @type {Record<string, unknown>} */
    let data;
    try {
      data = JSON.parse(line);
    } catch (err) {
      onLog(`pi rpc decode error: ${err instanceof Error ? err.message : String(err)}`, {
        instanceId: state.instanceId,
        phase: "handshake",
      });
      return;
    }

    if (data.type === "response" && data.id && state.pendingRequests.has(String(data.id))) {
      const pending = state.pendingRequests.get(String(data.id));
      state.pendingRequests.delete(String(data.id));
      if (data.success === false) {
        pending.reject(new Error(String(data.error || `Pi RPC ${data.command} failed`)));
      } else {
        pending.resolve(data);
      }
      return;
    }

    if (data.type === "extension_ui_request") {
      handleExtensionUiRequest(state, data);
      return;
    }

    handleEvent(state, data);
  }

  /**
   * @param {InstanceState} state
   * @returns {Promise<void>}
   */
  function waitForSettled(state) {
    if (!state.settledPromise) {
      state.settledPromise = new Promise((resolve) => {
        state.settleResolve = resolve;
      });
    }
    return state.settledPromise;
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

    state.ready = new Promise((resolve, reject) => {
      let settled = false;
      const fail = (err) => {
        if (settled) return;
        settled = true;
        reject(err instanceof Error ? err : new Error(String(err)));
      };

      const launch = getCliLaunch();
      if (!launch?.entry) {
        fail(new Error("pi_rpc_spawn_failed: Pi RPC launch config missing"));
        return;
      }

      try {
        state.proc = spawnFn(process.execPath, [launch.entry, ...launch.args], {
          cwd: launch.cwd,
          stdio: ["pipe", "pipe", "pipe"],
          env: {
            ...getSpawnEnv(),
            ...(state.authEnv || {}),
          },
          shell: false,
        });
        onLog("pi rpc spawn", {
          instanceId: state.instanceId,
          phase: "spawn",
          entry: launch.entry,
          args: launch.args,
        });
      } catch (err) {
        fail(
          new Error(
            `pi_rpc_spawn_failed: ${err instanceof Error ? err.message : String(err)}`,
          ),
        );
        return;
      }

      if (!state.proc.stdout || !state.proc.stdin || !state.proc.stderr) {
        fail(new Error("pi_rpc_spawn_failed: Pi RPC 子进程 stdio 不可用"));
        return;
      }

      state.proc.on("error", (err) => {
        onLog(`pi rpc process error: ${err.message}`, {
          instanceId: state.instanceId,
          phase: "error",
        });
        fail(err);
      });

      state.proc.stderr.on("data", (chunk) => {
        const text = String(chunk);
        state.stderrTail.push(text);
        if (state.stderrTail.length > STDERR_TAIL_LINES) {
          state.stderrTail.shift();
        }
      });

      const rl = createInterface({ input: state.proc.stdout });
      rl.on("line", (line) => {
        if (!line) return;
        handleLine(state, line);
      });

      state.proc.on("exit", (code, signal) => {
        onLog("pi rpc process exit", {
          instanceId: state.instanceId,
          phase: "error",
          code,
          signal,
        });
        state.proc = null;
        state.ready = null;
        state.piSessionPath = null;
        state.settleResolve = null;
        state.settledPromise = null;
        for (const [, pending] of state.pendingRequests) {
          pending.reject(new Error(`Pi RPC 进程已退出（code=${code}, signal=${signal}）`));
        }
        state.pendingRequests.clear();
      });

      if (!settled) {
        settled = true;
        onLog("pi rpc handshake complete", { instanceId: state.instanceId, phase: "handshake" });
        resolve();
      }
    });

    return state.ready;
  }

  /**
   * @param {InstanceState} state
   * @param {{ piSessionPath?: string | null }} opts
   * @returns {Promise<string | null>}
   */
  async function ensurePiSession(state, opts) {
    await ensureProcess(state);
    const desiredPath = opts.piSessionPath ? String(opts.piSessionPath) : null;

    if (desiredPath) {
      if (state.piSessionPath !== desiredPath) {
        await sendCommand(state, { type: "switch_session", sessionPath: desiredPath });
        state.piSessionPath = desiredPath;
        onLog("pi rpc switch_session", {
          instanceId: state.instanceId,
          phase: "handshake",
          piSessionPath: desiredPath,
        });
      }
      return state.piSessionPath;
    }

    if (!state.piSessionPath) {
      await sendCommand(state, { type: "new_session" });
      const stateResp = await sendCommand(state, { type: "get_state" });
      const data =
        stateResp.data && typeof stateResp.data === "object"
          ? /** @type {Record<string, unknown>} */ (stateResp.data)
          : null;
      state.piSessionPath = resolvePiSessionPathFromState(data);
      onLog("pi rpc new_session", {
        instanceId: state.instanceId,
        phase: "handshake",
        piSessionPath: state.piSessionPath,
        sessionFile: data?.sessionFile ?? null,
        sessionId: data?.sessionId ?? null,
      });
    }

    return state.piSessionPath;
  }

  /**
   * Kill child but keep InstanceState (auth / path) for respawn.
   * @param {InstanceState} state
   */
  function killProcessKeepState(state) {
    for (const [, pending] of state.pendingRequests) {
      pending.reject(new Error("Pi RPC 进程重启"));
    }
    state.pendingRequests.clear();
    state.settleResolve = null;
    state.settledPromise = null;
    delete state.textBuffer;
    if (state.proc && !state.proc.killed) {
      killChildTree(state.proc, { sync: false });
    }
    state.proc = null;
    state.ready = null;
  }

  /**
   * @param {InstanceState} state
   * @param {Record<string, string> | null | undefined} authEnv
   */
  function applyAuthEnv(state, authEnv) {
    if (!authEnv || typeof authEnv !== "object") return;
    const fp = JSON.stringify(authEnv);
    if (state.authEnvFp === fp) return;
    if (state.proc && !state.proc.killed) {
      killProcessKeepState(state);
    }
    state.authEnv = { ...authEnv };
    state.authEnvFp = fp;
  }

  /**
   * @param {InstanceState} state
   * @returns {Promise<unknown[]>}
   */
  async function getMessages(state) {
    const resp = await sendCommand(state, { type: "get_messages" });
    const data = resp.data;
    if (data && typeof data === "object" && Array.isArray(/** @type {Record<string, unknown>} */ (data).messages)) {
      return /** @type {unknown[]} */ (/** @type {Record<string, unknown>} */ (data).messages);
    }
    return [];
  }

  /**
   * @param {object} args
   * @param {string} args.instanceId
   * @param {string} [args.message]
   * @param {string} [args.text]
   * @param {string} [args.piSessionPath]
   * @param {Record<string, string>} [args.authEnv]
   * @returns {Promise<{ text: string, piSessionPath?: string, stderrTail?: string }>}
   */
  async function prompt(args) {
    const state = getOrCreateInstance(args.instanceId);
    applyAuthEnv(state, args.authEnv);
    /** @type {string[]} */
    state.textBuffer = [];
    state.settledPromise = new Promise((resolve) => {
      state.settleResolve = resolve;
    });

    const piSessionPath = await ensurePiSession(state, {
      piSessionPath: args.piSessionPath,
    });

    const userMessage = String(args.message ?? args.text ?? "");
    onLog("pi rpc prompt", { instanceId: state.instanceId, phase: "prompt" });

    const promptRespPromise = sendCommand(state, { type: "prompt", message: userMessage });
    const settledPromise = waitForSettled(state);

    await Promise.all([promptRespPromise, settledPromise]);

    let text = state.textBuffer.join("");
    if (!text) {
      const messages = await getMessages(state);
      text = getLastAssistantText(messages);
    }

    delete state.textBuffer;
    state.settleResolve = null;
    state.settledPromise = null;

    const stderrJoined = state.stderrTail.join("").trim();
    return {
      text,
      ...(piSessionPath ? { piSessionPath } : {}),
      ...(stderrJoined ? { stderrTail: stderrJoined.slice(-STDERR_TAIL_CHARS) } : {}),
    };
  }

  /**
   * @param {object} args
   * @param {string} args.instanceId
   * @param {string} [args.piSessionPath]
   * @param {Record<string, string>} [args.authEnv]
   * @returns {Promise<{ messages: unknown[], piSessionPath?: string | null }>}
   */
  async function listMessages(args) {
    const state = getOrCreateInstance(args.instanceId);
    applyAuthEnv(state, args.authEnv);
    const piSessionPath = await ensurePiSession(state, {
      piSessionPath: args.piSessionPath,
    });
    const messages = await getMessages(state);
    return {
      messages,
      piSessionPath: piSessionPath || state.piSessionPath,
    };
  }

  /**
   * @param {string} instanceId
   * @returns {Promise<void>}
   */
  async function abort(instanceId) {
    const state = instances.get(String(instanceId));
    if (!state?.proc || state.proc.killed) return;
    try {
      await sendCommand(state, { type: "abort" });
      onLog("pi rpc abort", { instanceId: state.instanceId, phase: "idle" });
    } catch (err) {
      onLog(`pi rpc abort failed: ${err instanceof Error ? err.message : String(err)}`, {
        instanceId: state.instanceId,
        phase: "error",
      });
    }
  }

  /**
   * @param {string} instanceId
   * @param {{ sync?: boolean }} [opts]
   */
  function stop(instanceId, opts = {}) {
    const state = instances.get(String(instanceId));
    if (!state) return;

    state.stopped = true;
    state.piSessionPath = null;
    state.settleResolve = null;
    state.settledPromise = null;
    delete state.textBuffer;

    for (const [, pending] of state.pendingRequests) {
      pending.reject(new Error("Pi RPC 实例已停止"));
    }
    state.pendingRequests.clear();

    if (state.proc && !state.proc.killed) {
      killChildTree(state.proc, { sync: Boolean(opts.sync) });
    }
    state.proc = null;
    state.ready = null;
    instances.delete(String(instanceId));
    onLog("pi rpc instance stopped", { instanceId, phase: "idle" });
  }

  /**
   * @param {{ sync?: boolean }} [opts]
   */
  function stopAll(opts = {}) {
    for (const instanceId of [...instances.keys()]) {
      stop(instanceId, opts);
    }
  }

  /**
   * @param {{ sync?: boolean }} [opts]
   */
  function disposeAll(opts = {}) {
    stopAll(opts);
  }

  return {
    prompt,
    listMessages,
    abort,
    stop,
    stopAll,
    disposeAll,
  };
}

/**
 * Prefer sessionFile for switch_session; fall back to sessionId.
 * @param {Record<string, unknown> | null | undefined} data
 * @returns {string | null}
 */
export function resolvePiSessionPathFromState(data) {
  if (!data || typeof data !== "object") return null;
  const sessionFile =
    data.sessionFile != null && String(data.sessionFile).trim()
      ? String(data.sessionFile).trim()
      : null;
  if (sessionFile) return sessionFile;
  const sessionId =
    data.sessionId != null && String(data.sessionId).trim()
      ? String(data.sessionId).trim()
      : null;
  return sessionId;
}
