/**
 * Cursor Agent ACP protocol adapter (Foundry Electron).
 *
 * Locked method table — probed 2026-07-22 on agent 2026.07.20-8cc9c0b:
 *
 * | Phase            | Direction        | Method                         | Framing   |
 * |------------------|------------------|--------------------------------|-----------|
 * | Handshake        | client → agent   | initialize                     | NDJSON    |
 * | Auth             | client → agent   | authenticate (methodId: cursor_login) | NDJSON |
 * | Session create   | client → agent   | session/new                    | NDJSON    |
 * | Session resume   | client → agent   | session/load                   | NDJSON    |
 * | Turn / prompt    | client → agent   | session/prompt                 | NDJSON    |
 * | Set mode         | client → agent   | session/set_mode               | NDJSON    |
 * | Cancel turn      | client → agent   | session/cancel                 | NDJSON    |
 * | Stream updates   | agent → client   | session/update (notification)  | NDJSON    |
 * | Permission ask   | agent → client   | session/request_permission     | NDJSON    |
 * | Permission reply | client → agent   | JSON-RPC response { result }     | NDJSON    |
 *
 * Transport: stdio, one JSON-RPC 2.0 object per line (newline-delimited JSON).
 * NOT Content-Length framing (verified by live initialize probe).
 *
 * Cursor permission optionIds (https://cursor.com/docs/cli/acp):
 *   allow-once | allow-always | reject-once
 *
 * Foundry `session` decision maps to ACP allow-always for the ACP process lifetime
 * only — never persisted to ~/.gamefactory/config.json or any disk allow-list.
 *
 * Probe evidence:
 * - `agent acp --help` → stdio ACP server
 * - Live initialize → NDJSON response with protocolVersion 1, authMethods cursor_login
 * - Cursor docs + agent bundle strings confirm method names and optionIds
 */

/** @typedef {'once' | 'turn' | 'session' | 'deny'} FoundryPermissionDecision */

export const ACP_PROTOCOL_VERSION = 1;

/** @readonly */
export const ACP_METHODS = Object.freeze({
  INITIALIZE: "initialize",
  AUTHENTICATE: "authenticate",
  SESSION_NEW: "session/new",
  SESSION_LOAD: "session/load",
  SESSION_PROMPT: "session/prompt",
  SESSION_SET_MODE: "session/set_mode",
  SESSION_CANCEL: "session/cancel",
  SESSION_UPDATE: "session/update",
  SESSION_REQUEST_PERMISSION: "session/request_permission",
});

/** Foundry permission_mode → Cursor ACP modeId (session/new defaults to agent). */
export const FOUNDRY_TO_ACP_MODE = Object.freeze({
  plan: "plan",
  ask: "ask",
  // Smart Auto / mid-turn approvals still use agent tools; permissions come via request_permission.
  auto_review: "agent",
});

export function acpModeIdForFoundryPermissionMode(mode) {
  const key = String(mode || "").trim();
  return FOUNDRY_TO_ACP_MODE[key] || "agent";
}

/** Client capabilities so agent routes tool I/O through ACP (and can request permission). */
export const ACP_CLIENT_CAPABILITIES = Object.freeze({
  fs: { readTextFile: true, writeTextFile: true },
  terminal: true,
});

/** @readonly */
export const ACP_AUTH_METHODS = Object.freeze({
  CURSOR_LOGIN: "cursor_login",
});

/** @readonly */
export const ACP_PERMISSION_OPTION_IDS = Object.freeze({
  ALLOW_ONCE: "allow-once",
  ALLOW_ALWAYS: "allow-always",
  REJECT_ONCE: "reject-once",
});

export class AcpProtocolError extends Error {
  /**
   * @param {string} message
   * @param {Record<string, unknown>} [details]
   */
  constructor(message, details) {
    super(message);
    this.name = "AcpProtocolError";
    this.details = details;
  }
}

/**
 * @param {FoundryPermissionDecision} decision
 * @returns {string} ACP PermissionOptionId
 */
export function mapDecisionToAcp(decision) {
  switch (decision) {
    case "once":
      return ACP_PERMISSION_OPTION_IDS.ALLOW_ONCE;
    case "turn":
      // ACP has no turn scope; Foundry turnAllow cache handles repeat prompts in-process.
      return ACP_PERMISSION_OPTION_IDS.ALLOW_ONCE;
    case "session":
      // Maps to allow-always for this ACP child process only — never write config.
      return ACP_PERMISSION_OPTION_IDS.ALLOW_ALWAYS;
    case "deny":
      return ACP_PERMISSION_OPTION_IDS.REJECT_ONCE;
    default:
      throw new AcpProtocolError(`unknown permission decision: ${String(decision)}`);
  }
}

/**
 * @param {FoundryPermissionDecision} decision
 * @returns {{ outcome: { outcome: 'selected', optionId: string } }}
 */
export function buildPermissionResult(decision) {
  return {
    outcome: {
      outcome: "selected",
      optionId: mapDecisionToAcp(decision),
    },
  };
}

/**
 * @param {unknown} line
 * @returns {Record<string, unknown> | null}
 */
export function decodeLine(line) {
  const text = String(line ?? "").trim();
  if (!text) return null;
  try {
    const msg = JSON.parse(text);
    if (!msg || typeof msg !== "object" || Array.isArray(msg)) {
      throw new AcpProtocolError("JSON-RPC message must be an object", { line: text.slice(0, 200) });
    }
    return /** @type {Record<string, unknown>} */ (msg);
  } catch (err) {
    if (err instanceof AcpProtocolError) throw err;
    throw new AcpProtocolError("invalid JSON-RPC line", {
      line: text.slice(0, 200),
      cause: err instanceof Error ? err.message : String(err),
    });
  }
}

/**
 * @param {Record<string, unknown>} msg
 * @returns {string}
 */
export function encodeMessage(msg) {
  return `${JSON.stringify(msg)}\n`;
}

/**
 * @param {number | string} id
 * @param {string} method
 * @param {Record<string, unknown>} [params]
 * @returns {string}
 */
export function encodeRequest(id, method, params = {}) {
  return encodeMessage({ jsonrpc: "2.0", id, method, params });
}

/**
 * @param {number | string} id
 * @param {unknown} result
 * @returns {string}
 */
export function encodeResponse(id, result) {
  return encodeMessage({ jsonrpc: "2.0", id, result });
}

/**
 * @param {number | string} id
 * @param {FoundryPermissionDecision} decision
 * @returns {string}
 */
export function encodePermissionResponse(id, decision) {
  return encodeResponse(id, buildPermissionResult(decision));
}

/**
 * @param {Record<string, unknown>} msg JSON-RPC request from agent
 * @returns {{ permissionId: string, summary: string, raw: Record<string, unknown>, jsonRpcId: number | string, sessionId: string }}
 */
export function normalizePermissionRequest(msg) {
  if (msg.method !== ACP_METHODS.SESSION_REQUEST_PERMISSION) {
    throw new AcpProtocolError("not a permission request", { method: msg.method });
  }
  if (msg.id === undefined || msg.id === null) {
    throw new AcpProtocolError("permission request missing JSON-RPC id");
  }

  const params = /** @type {Record<string, unknown>} */ (msg.params && typeof msg.params === "object" ? msg.params : {});
  const toolCall = /** @type {Record<string, unknown>} */ (
    params.toolCall && typeof params.toolCall === "object" ? params.toolCall : {}
  );
  const permissionId = String(
    toolCall.toolCallId ?? toolCall.id ?? params.toolCallId ?? msg.id,
  );
  const sessionId = String(params.sessionId ?? "");

  return {
    permissionId,
    summary: buildPermissionSummary(params, toolCall),
    raw: msg,
    jsonRpcId: /** @type {number | string} */ (msg.id),
    sessionId,
  };
}

/**
 * @param {Record<string, unknown>} params
 * @param {Record<string, unknown>} toolCall
 * @returns {string}
 */
function buildPermissionSummary(params, toolCall) {
  const parts = [];
  const title = toolCall.title ?? toolCall.name ?? toolCall.kind;
  if (title) parts.push(String(title));

  const toolName = toolCall.toolName ?? toolCall.tool ?? params.toolName;
  if (toolName) parts.push(String(toolName));

  const description = toolCall.description ?? toolCall.summary ?? params.description;
  if (description) parts.push(String(description));

  const options = Array.isArray(params.options) ? params.options : [];
  if (options.length && parts.length === 0) {
    parts.push(
      options
        .slice(0, 3)
        .map((o) => (o && typeof o === "object" ? String(/** @type {Record<string, unknown>} */ (o).label ?? "") : ""))
        .filter(Boolean)
        .join(" / "),
    );
  }

  const summary = parts.filter(Boolean).join(" — ").slice(0, 500);
  return summary || "Cursor 请求工具权限";
}

/**
 * @param {object} opts
 * @param {(req: ReturnType<typeof normalizePermissionRequest>) => void | Promise<void>} [opts.onPermission]
 * @param {(msg: Record<string, unknown>) => void} [opts.onMessage]
 * @param {(err: Error, ctx?: Record<string, unknown>) => void} [opts.onError]
 */
export function createAdapter(opts = {}) {
  const onPermission = opts.onPermission ?? (() => {});
  const onMessage = opts.onMessage ?? (() => {});
  const onError = opts.onError ?? (() => {});

  /** @type {Map<string, { jsonRpcId: number | string, sessionId: string }>} */
  const pendingPermissions = new Map();

  /**
   * @param {string} line stdout line from `agent acp`
   */
  async function feedLine(line) {
    let msg;
    try {
      msg = decodeLine(line);
    } catch (err) {
      onError(err instanceof Error ? err : new Error(String(err)));
      return;
    }
    if (!msg) return;

    onMessage(msg);

    if (typeof msg.method === "string") {
      if (msg.method === ACP_METHODS.SESSION_REQUEST_PERMISSION) {
        try {
          const normalized = normalizePermissionRequest(msg);
          pendingPermissions.set(normalized.permissionId, {
            jsonRpcId: normalized.jsonRpcId,
            sessionId: normalized.sessionId,
          });
          await onPermission(normalized);
        } catch (err) {
          onError(err instanceof Error ? err : new Error(String(err)), { method: msg.method });
        }
        return;
      }

      if (msg.method === ACP_METHODS.SESSION_UPDATE) {
        return;
      }

      onError(new AcpProtocolError(`unhandled inbound ACP method: ${msg.method}`), { method: msg.method });
    }
  }

  /**
   * @param {string} permissionId
   * @param {FoundryPermissionDecision} decision
   * @returns {string | null} encoded response line for stdin, or null if unknown id
   */
  function respondPermission(permissionId, decision) {
    const pending = pendingPermissions.get(String(permissionId));
    if (!pending) return null;
    pendingPermissions.delete(String(permissionId));
    return encodePermissionResponse(pending.jsonRpcId, decision);
  }

  /**
   * @param {number | string} jsonRpcId
   * @param {FoundryPermissionDecision} decision
   * @returns {string}
   */
  function respondPermissionByRpcId(jsonRpcId, decision) {
    for (const [permissionId, pending] of pendingPermissions) {
      if (pending.jsonRpcId === jsonRpcId) {
        pendingPermissions.delete(permissionId);
        break;
      }
    }
    return encodePermissionResponse(jsonRpcId, decision);
  }

  function clearPendingPermissions() {
    pendingPermissions.clear();
  }

  return {
    feedLine,
    respondPermission,
    respondPermissionByRpcId,
    clearPendingPermissions,
    encodeRequest,
    encodeResponse,
    encodePermissionResponse,
    decodeLine,
    encodeMessage,
    pendingPermissions,
  };
}
