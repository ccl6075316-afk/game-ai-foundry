/**
 * Codex app-server protocol adapter (Foundry Electron).
 *
 * Locked method table — probed 2026-07-22 on codex 0.145 (`/opt/homebrew/bin/codex`):
 *
 * | Phase              | Direction        | Method                              | Framing |
 * |--------------------|------------------|-------------------------------------|---------|
 * | Handshake          | client → server  | initialize                          | NDJSON  |
 * | Thread create      | client → server  | thread/start                        | NDJSON  |
 * | Thread resume      | client → server  | thread/resume                       | NDJSON  |
 * | Turn / prompt      | client → server  | turn/start                          | NDJSON  |
 * | Turn steer         | client → server  | turn/steer                          | NDJSON  |
 * | Turn interrupt     | client → server  | turn/interrupt                      | NDJSON  |
 * | Stream updates     | server → client  | (ServerNotification methods)        | NDJSON  |
 * | Command approval   | server → client  | item/commandExecution/requestApproval | NDJSON |
 * | File approval      | server → client  | item/fileChange/requestApproval     | NDJSON  |
 * | Permissions approval | server → client | item/permissions/requestApproval  | NDJSON  |
 * | Legacy exec approval | server → client | execCommandApproval               | NDJSON  |
 * | Legacy patch approval | server → client | applyPatchApproval               | NDJSON  |
 * | Approval reply     | client → server  | JSON-RPC response { result }        | NDJSON  |
 *
 * Transport: stdio, one JSON-RPC 2.0 object per line (newline-delimited JSON).
 * NOT Content-Length framing (verified by live initialize probe 2026-07-22).
 *
 * Command/file approval decisions (item/* API):
 *   accept | acceptForSession | decline | cancel
 *   acceptWithExecpolicyAmendment { execpolicy_amendment: string[] }
 *   applyNetworkPolicyAmendment { network_policy_amendment: { action, host } }
 *
 * Legacy exec/patch decisions (ReviewDecision):
 *   approved | approved_for_session | denied { rejection } | abort | timed_out
 *   approved_execpolicy_amendment { proposed_execpolicy_amendment: string[] }
 *
 * Permissions approval response: { permissions: GrantedPermissionProfile, scope?: turn|session }
 *
 * Foundry decision mapping (v1):
 *   once    → accept / approved (never acceptWithExecpolicyAmendment — see below)
 *   turn    → accept / approved (protocol has no turn scope; Foundry turnAllow cache auto-accepts repeats)
 *   session → acceptForSession / approved_for_session (app-server process lifetime only — never disk)
 *   deny    → decline / denied
 *
 * acceptWithExecpolicyAmendment — v1 HARD POLICY:
 *   MUST NOT map Foundry「本会话」(session) to execpolicy amendment (permanent disk policy).
 *   v1 NEVER emits acceptWithExecpolicyAmendment or approved_execpolicy_amendment.
 *   Foundry once/turn/session all use plain accept/acceptForSession only.
 *
 * Client JSON-RPC ids use prefix `gaf-c-` to avoid colliding with server numeric request ids.
 *
 * Probe evidence:
 * - `codex app-server generate-json-schema --out /tmp/codex-app-schema`
 * - Live stdio initialize → NDJSON error/response line (missing clientInfo → -32600)
 * - Schema: ServerRequest.json, CommandExecutionRequestApprovalResponse.json
 */

/** @typedef {'once' | 'turn' | 'session' | 'deny'} FoundryPermissionDecision */

export const CODEX_APP_SERVER_CLIENT_ID_PREFIX = "gaf-c-";

/** @readonly — client → server (subset for T3; full list in schema ClientRequest.json) */
export const CLIENT_METHODS = Object.freeze({
  INITIALIZE: "initialize",
  THREAD_START: "thread/start",
  THREAD_RESUME: "thread/resume",
  TURN_START: "turn/start",
  TURN_STEER: "turn/steer",
  TURN_INTERRUPT: "turn/interrupt",
});

/** @readonly — server → client approval methods (ServerRequest.json) */
export const SERVER_APPROVAL_METHODS = Object.freeze({
  COMMAND_EXECUTION_REQUEST_APPROVAL: "item/commandExecution/requestApproval",
  FILE_CHANGE_REQUEST_APPROVAL: "item/fileChange/requestApproval",
  PERMISSIONS_REQUEST_APPROVAL: "item/permissions/requestApproval",
  EXEC_COMMAND_APPROVAL: "execCommandApproval",
  APPLY_PATCH_APPROVAL: "applyPatchApproval",
});

/** @readonly — item/* command/file decision strings */
export const ITEM_APPROVAL_DECISIONS = Object.freeze({
  ACCEPT: "accept",
  ACCEPT_FOR_SESSION: "acceptForSession",
  DECLINE: "decline",
  CANCEL: "cancel",
});

/** @readonly — legacy ReviewDecision strings */
export const LEGACY_REVIEW_DECISIONS = Object.freeze({
  APPROVED: "approved",
  APPROVED_FOR_SESSION: "approved_for_session",
  ABORT: "abort",
  TIMED_OUT: "timed_out",
});

/** Maps server approval method → Foundry permission kind label. */
export const APPROVAL_METHOD_KIND = Object.freeze({
  [SERVER_APPROVAL_METHODS.COMMAND_EXECUTION_REQUEST_APPROVAL]: "command",
  [SERVER_APPROVAL_METHODS.FILE_CHANGE_REQUEST_APPROVAL]: "fileChange",
  [SERVER_APPROVAL_METHODS.PERMISSIONS_REQUEST_APPROVAL]: "permissions",
  [SERVER_APPROVAL_METHODS.EXEC_COMMAND_APPROVAL]: "command",
  [SERVER_APPROVAL_METHODS.APPLY_PATCH_APPROVAL]: "patch",
});

/** @type {ReadonlySet<string>} */
export const KNOWN_SERVER_APPROVAL_METHODS = new Set(Object.values(SERVER_APPROVAL_METHODS));

/** @type {ReadonlySet<string>} */
const NEW_ITEM_APPROVAL_METHODS = new Set([
  SERVER_APPROVAL_METHODS.COMMAND_EXECUTION_REQUEST_APPROVAL,
  SERVER_APPROVAL_METHODS.FILE_CHANGE_REQUEST_APPROVAL,
]);

/** @type {ReadonlySet<string>} */
const LEGACY_REVIEW_APPROVAL_METHODS = new Set([
  SERVER_APPROVAL_METHODS.EXEC_COMMAND_APPROVAL,
  SERVER_APPROVAL_METHODS.APPLY_PATCH_APPROVAL,
]);

let clientIdCounter = 0;

/**
 * Reset module counter (tests only).
 */
export function resetClientIdCounter() {
  clientIdCounter = 0;
}

/**
 * @param {number} [counter] optional 1-based counter; when omitted uses module counter
 * @returns {string}
 */
export function nextClientId(counter) {
  const n = counter ?? ++clientIdCounter;
  return `${CODEX_APP_SERVER_CLIENT_ID_PREFIX}${n}`;
}

export class CodexAppServerProtocolError extends Error {
  /**
   * @param {string} message
   * @param {Record<string, unknown>} [details]
   */
  constructor(message, details) {
    super(message);
    this.name = "CodexAppServerProtocolError";
    this.details = details;
  }
}

/**
 * @param {string} method
 * @returns {boolean}
 */
export function isServerApprovalMethod(method) {
  return KNOWN_SERVER_APPROVAL_METHODS.has(String(method));
}

/**
 * @param {FoundryPermissionDecision} decision
 * @param {{ rawMethod?: string, proposedExecpolicyAmendment?: string[] | null, requestedPermissions?: Record<string, unknown> | null }} [requestMeta]
 * @returns {Record<string, unknown>}
 */
export function encodePermissionDecision(decision, requestMeta = {}) {
  const rawMethod = String(requestMeta.rawMethod ?? SERVER_APPROVAL_METHODS.COMMAND_EXECUTION_REQUEST_APPROVAL);

  if (rawMethod === SERVER_APPROVAL_METHODS.PERMISSIONS_REQUEST_APPROVAL) {
    return encodePermissionsApprovalDecision(decision, requestMeta);
  }

  if (NEW_ITEM_APPROVAL_METHODS.has(rawMethod)) {
    return { decision: mapDecisionToItemApproval(decision) };
  }

  if (LEGACY_REVIEW_APPROVAL_METHODS.has(rawMethod)) {
    return { decision: mapDecisionToLegacyReview(decision) };
  }

  throw new CodexAppServerProtocolError(`unsupported approval method for decision encoding: ${rawMethod}`, {
    rawMethod,
    decision,
  });
}

/**
 * @param {FoundryPermissionDecision} decision
 * @returns {string}
 */
export function mapDecisionToItemApproval(decision) {
  switch (decision) {
    case "once":
      // v1: plain accept only — never acceptWithExecpolicyAmendment (permanent disk policy).
      return ITEM_APPROVAL_DECISIONS.ACCEPT;
    case "turn":
      // Protocol has no turn scope; Foundry turnAllow cache handles repeat prompts in-process.
      return ITEM_APPROVAL_DECISIONS.ACCEPT;
    case "session":
      // Maps to acceptForSession for this app-server child process only — never write config.
      return ITEM_APPROVAL_DECISIONS.ACCEPT_FOR_SESSION;
    case "deny":
      return ITEM_APPROVAL_DECISIONS.DECLINE;
    default:
      throw new CodexAppServerProtocolError(`unknown permission decision: ${String(decision)}`);
  }
}

/**
 * @param {FoundryPermissionDecision} decision
 * @returns {string | Record<string, unknown>}
 */
export function mapDecisionToLegacyReview(decision) {
  switch (decision) {
    case "once":
      return LEGACY_REVIEW_DECISIONS.APPROVED;
    case "turn":
      return LEGACY_REVIEW_DECISIONS.APPROVED;
    case "session":
      return LEGACY_REVIEW_DECISIONS.APPROVED_FOR_SESSION;
    case "deny":
      return { denied: { rejection: "User denied" } };
    default:
      throw new CodexAppServerProtocolError(`unknown permission decision: ${String(decision)}`);
  }
}

/**
 * @param {FoundryPermissionDecision} decision
 * @param {{ requestedPermissions?: Record<string, unknown> | null }} requestMeta
 * @returns {Record<string, unknown>}
 */
function encodePermissionsApprovalDecision(decision, requestMeta) {
  switch (decision) {
    case "once":
    case "turn":
      return {
        permissions: requestMeta.requestedPermissions ?? {},
        scope: "turn",
      };
    case "session":
      return {
        permissions: requestMeta.requestedPermissions ?? {},
        scope: "session",
      };
    case "deny":
      throw new CodexAppServerProtocolError(
        "item/permissions/requestApproval deny is not encoded in v1 — use explicit session-manager deny path",
        { decision },
      );
    default:
      throw new CodexAppServerProtocolError(`unknown permission decision: ${String(decision)}`);
  }
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
      throw new CodexAppServerProtocolError("JSON-RPC message must be an object", { line: text.slice(0, 200) });
    }
    return /** @type {Record<string, unknown>} */ (msg);
  } catch (err) {
    if (err instanceof CodexAppServerProtocolError) throw err;
    throw new CodexAppServerProtocolError("invalid JSON-RPC line", {
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
 * @param {{ rawMethod?: string, proposedExecpolicyAmendment?: string[] | null, requestedPermissions?: Record<string, unknown> | null }} [requestMeta]
 * @returns {string}
 */
export function encodePermissionResponse(id, decision, requestMeta = {}) {
  return encodeResponse(id, encodePermissionDecision(decision, requestMeta));
}

/**
 * @param {Record<string, unknown>} msg JSON-RPC request from codex app-server
 * @returns {{
 *   permissionId: string,
 *   summary: string,
 *   kind: string,
 *   source: 'codex_app_server',
 *   rawMethod: string,
 *   raw: Record<string, unknown>,
 *   jsonRpcId: number | string,
 *   threadId: string,
 *   turnId: string,
 *   sessionId: string,
 * }}
 */
export function normalizePermissionRequest(msg) {
  const method = String(msg.method ?? "");
  if (!isServerApprovalMethod(method)) {
    throw new CodexAppServerProtocolError("not a server approval request", { method });
  }
  if (msg.id === undefined || msg.id === null) {
    throw new CodexAppServerProtocolError("approval request missing JSON-RPC id", { method });
  }

  const params = /** @type {Record<string, unknown>} */ (msg.params && typeof msg.params === "object" ? msg.params : {});
  const permissionId = String(
    params.approvalId ?? params.itemId ?? params.callId ?? msg.id,
  );
  const threadId = String(params.threadId ?? params.conversationId ?? "");
  const turnId = String(params.turnId ?? "");
  const kind = APPROVAL_METHOD_KIND[method] ?? "unknown";

  return {
    permissionId,
    summary: buildPermissionSummary(method, params),
    kind,
    source: "codex_app_server",
    rawMethod: method,
    raw: msg,
    jsonRpcId: /** @type {number | string} */ (msg.id),
    threadId,
    turnId,
    sessionId: threadId,
  };
}

/**
 * @param {string} method
 * @param {Record<string, unknown>} params
 * @returns {string}
 */
function buildPermissionSummary(method, params) {
  const parts = [];

  if (method === SERVER_APPROVAL_METHODS.COMMAND_EXECUTION_REQUEST_APPROVAL) {
    if (params.command) parts.push(String(params.command));
    if (params.reason) parts.push(String(params.reason));
    if (params.cwd) parts.push(`cwd: ${String(params.cwd)}`);
  } else if (method === SERVER_APPROVAL_METHODS.EXEC_COMMAND_APPROVAL) {
    const cmd = Array.isArray(params.command) ? params.command.join(" ") : "";
    if (cmd) parts.push(cmd);
    if (params.reason) parts.push(String(params.reason));
    if (params.cwd) parts.push(`cwd: ${String(params.cwd)}`);
  } else if (method === SERVER_APPROVAL_METHODS.FILE_CHANGE_REQUEST_APPROVAL) {
    parts.push("文件变更");
    if (params.reason) parts.push(String(params.reason));
    if (params.grantRoot) parts.push(`grantRoot: ${String(params.grantRoot)}`);
  } else if (method === SERVER_APPROVAL_METHODS.APPLY_PATCH_APPROVAL) {
    parts.push("补丁应用");
    if (params.reason) parts.push(String(params.reason));
    const changes = params.fileChanges && typeof params.fileChanges === "object" ? params.fileChanges : {};
    const paths = Object.keys(/** @type {Record<string, unknown>} */ (changes)).slice(0, 3);
    if (paths.length) parts.push(paths.join(", "));
  } else if (method === SERVER_APPROVAL_METHODS.PERMISSIONS_REQUEST_APPROVAL) {
    parts.push("额外权限");
    if (params.reason) parts.push(String(params.reason));
  }

  const summary = parts.filter(Boolean).join(" — ").slice(0, 500);
  return summary || "Codex 请求批准";
}

/**
 * Route one inbound JSON-RPC message from codex app-server stdout.
 * Inbound requests/notifications MUST be handled before response matching.
 *
 * @param {Record<string, unknown>} msg
 * @param {object} state
 * @param {Map<string | number, { resolve: (v: unknown) => void, reject: (e: Error) => void, method: string }>} state.pendingRpc
 * @param {ReturnType<typeof createAdapter>} state.adapter
 * @param {(err: Error, ctx?: Record<string, unknown>) => void} [state.onError]
 * @returns {{ handled: 'request' | 'response' | 'orphan' | 'ignored' }}
 */
export function handleInboundLine(msg, state) {
  if (typeof msg.method === "string") {
    state.adapter.feedLine(JSON.stringify(msg)).catch((err) => {
      if (state.onError) {
        state.onError(err instanceof Error ? err : new Error(String(err)), { phase: "adapter.feedLine" });
      }
    });
    return { handled: "request" };
  }

  const rpcId = msg.id;
  const isResponse =
    rpcId != null && (Object.prototype.hasOwnProperty.call(msg, "result") || msg.error != null);
  if (isResponse && state.pendingRpc.has(rpcId)) {
    const pending = state.pendingRpc.get(rpcId);
    state.pendingRpc.delete(rpcId);
    if (msg.error) {
      const errObj = msg.error && typeof msg.error === "object" ? msg.error : {};
      const message = String(/** @type {Record<string, unknown>} */ (errObj).message ?? "Codex app-server RPC error");
      pending.reject(new CodexAppServerProtocolError(message, { method: pending.method, error: msg.error }));
    } else {
      pending.resolve(msg.result);
    }
    return { handled: "response" };
  }

  if (msg.id != null) {
    return { handled: "orphan" };
  }

  return { handled: "ignored" };
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

  /** @type {Map<string, { jsonRpcId: number | string, rawMethod: string, threadId: string, turnId: string, params: Record<string, unknown> }>} */
  const pendingPermissions = new Map();

  /**
   * @param {string} line stdout line from `codex app-server`
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
      if (isServerApprovalMethod(msg.method)) {
        try {
          const normalized = normalizePermissionRequest(msg);
          const params = /** @type {Record<string, unknown>} */ (
            msg.params && typeof msg.params === "object" ? msg.params : {}
          );
          pendingPermissions.set(normalized.permissionId, {
            jsonRpcId: normalized.jsonRpcId,
            rawMethod: normalized.rawMethod,
            threadId: normalized.threadId,
            turnId: normalized.turnId,
            params,
          });
          await onPermission(normalized);
        } catch (err) {
          onError(err instanceof Error ? err : new Error(String(err)), { method: msg.method });
        }
        return;
      }

      // Non-permission server requests are forwarded; T3 session manager handles them.
      return;
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
    return encodePermissionResponse(pending.jsonRpcId, decision, {
      rawMethod: pending.rawMethod,
      proposedExecpolicyAmendment: /** @type {string[] | null | undefined} */ (pending.params.proposedExecpolicyAmendment),
      requestedPermissions: /** @type {Record<string, unknown> | null | undefined} */ (pending.params.permissions),
    });
  }

  /**
   * @param {number | string} jsonRpcId
   * @param {FoundryPermissionDecision} decision
   * @param {{ rawMethod?: string, proposedExecpolicyAmendment?: string[] | null, requestedPermissions?: Record<string, unknown> | null }} [requestMeta]
   * @returns {string}
   */
  function respondPermissionByRpcId(jsonRpcId, decision, requestMeta = {}) {
    for (const [permissionId, pending] of pendingPermissions) {
      if (pending.jsonRpcId === jsonRpcId) {
        pendingPermissions.delete(permissionId);
        return encodePermissionResponse(jsonRpcId, decision, {
          rawMethod: requestMeta.rawMethod ?? pending.rawMethod,
          proposedExecpolicyAmendment:
            requestMeta.proposedExecpolicyAmendment ?? pending.params.proposedExecpolicyAmendment,
          requestedPermissions: requestMeta.requestedPermissions ?? pending.params.permissions,
        });
      }
    }
    return encodePermissionResponse(jsonRpcId, decision, requestMeta);
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
