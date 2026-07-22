import assert from "node:assert/strict";
import test from "node:test";

import {
  CLIENT_METHODS,
  CODEX_APP_SERVER_CLIENT_ID_PREFIX,
  CodexAppServerProtocolError,
  ITEM_APPROVAL_DECISIONS,
  LEGACY_REVIEW_DECISIONS,
  SERVER_APPROVAL_METHODS,
  createAdapter,
  decodeLine,
  encodePermissionDecision,
  encodePermissionResponse,
  encodeRequest,
  handleInboundLine,
  isServerApprovalMethod,
  mapDecisionToItemApproval,
  mapDecisionToLegacyReview,
  nextClientId,
  normalizePermissionRequest,
  resetClientIdCounter,
} from "./codex_app_server_adapter.mjs";

test("nextClientId uses gaf-c- prefix and increments", () => {
  resetClientIdCounter();
  assert.equal(nextClientId(), `${CODEX_APP_SERVER_CLIENT_ID_PREFIX}1`);
  assert.equal(nextClientId(), `${CODEX_APP_SERVER_CLIENT_ID_PREFIX}2`);
  assert.equal(nextClientId(99), `${CODEX_APP_SERVER_CLIENT_ID_PREFIX}99`);
});

test("decodeLine parses NDJSON JSON-RPC", () => {
  const msg = decodeLine('{"jsonrpc":"2.0","id":"gaf-c-1","result":{"threadId":"t1"}}\n');
  assert.equal(msg?.id, "gaf-c-1");
  assert.deepEqual(msg?.result, { threadId: "t1" });
});

test("decodeLine rejects invalid JSON", () => {
  assert.throws(() => decodeLine("{not-json"), CodexAppServerProtocolError);
});

test("encodeRequest uses NDJSON newline framing", () => {
  const line = encodeRequest("gaf-c-1", CLIENT_METHODS.INITIALIZE, {
    clientInfo: { name: "game-ai-foundry", version: "0.0.0" },
  });
  assert.ok(line.endsWith("\n"));
  assert.equal(decodeLine(line)?.method, CLIENT_METHODS.INITIALIZE);
});

test("mapDecisionToItemApproval maps Foundry decisions", () => {
  assert.equal(mapDecisionToItemApproval("once"), ITEM_APPROVAL_DECISIONS.ACCEPT);
  assert.equal(mapDecisionToItemApproval("turn"), ITEM_APPROVAL_DECISIONS.ACCEPT);
  assert.equal(mapDecisionToItemApproval("session"), ITEM_APPROVAL_DECISIONS.ACCEPT_FOR_SESSION);
  assert.equal(mapDecisionToItemApproval("deny"), ITEM_APPROVAL_DECISIONS.DECLINE);
});

test("encodePermissionDecision never emits acceptWithExecpolicyAmendment", () => {
  const result = encodePermissionDecision("once", {
    rawMethod: SERVER_APPROVAL_METHODS.COMMAND_EXECUTION_REQUEST_APPROVAL,
    proposedExecpolicyAmendment: ["allow npm test"],
  });
  assert.deepEqual(result, { decision: ITEM_APPROVAL_DECISIONS.ACCEPT });
  assert.ok(!JSON.stringify(result).includes("acceptWithExecpolicyAmendment"));
  assert.ok(!JSON.stringify(result).includes("execpolicy"));
});

test("encodePermissionDecision maps session to acceptForSession for command approval", () => {
  const result = encodePermissionDecision("session", {
    rawMethod: SERVER_APPROVAL_METHODS.COMMAND_EXECUTION_REQUEST_APPROVAL,
  });
  assert.deepEqual(result, { decision: ITEM_APPROVAL_DECISIONS.ACCEPT_FOR_SESSION });
});

test("mapDecisionToLegacyReview maps legacy exec approval decisions", () => {
  assert.equal(mapDecisionToLegacyReview("once"), LEGACY_REVIEW_DECISIONS.APPROVED);
  assert.equal(mapDecisionToLegacyReview("session"), LEGACY_REVIEW_DECISIONS.APPROVED_FOR_SESSION);
  assert.deepEqual(mapDecisionToLegacyReview("deny"), { denied: { rejection: "User denied" } });
});

test("normalizePermissionRequest extracts commandExecution approval fields", () => {
  const raw = {
    jsonrpc: "2.0",
    id: 42,
    method: SERVER_APPROVAL_METHODS.COMMAND_EXECUTION_REQUEST_APPROVAL,
    params: {
      threadId: "thread-1",
      turnId: "turn-9",
      itemId: "item-abc",
      approvalId: "appr-xyz",
      command: "npm test",
      reason: "run tests",
      startedAtMs: 1,
    },
  };
  const norm = normalizePermissionRequest(raw);
  assert.equal(norm.permissionId, "appr-xyz");
  assert.equal(norm.jsonRpcId, 42);
  assert.equal(norm.threadId, "thread-1");
  assert.equal(norm.turnId, "turn-9");
  assert.equal(norm.kind, "command");
  assert.equal(norm.source, "codex_app_server");
  assert.equal(norm.rawMethod, SERVER_APPROVAL_METHODS.COMMAND_EXECUTION_REQUEST_APPROVAL);
  assert.match(norm.summary, /npm test/);
  assert.equal(norm.raw, raw);
});

test("normalizePermissionRequest falls back to itemId when approvalId absent", () => {
  const norm = normalizePermissionRequest({
    jsonrpc: "2.0",
    id: 1,
    method: SERVER_APPROVAL_METHODS.COMMAND_EXECUTION_REQUEST_APPROVAL,
    params: {
      threadId: "t",
      turnId: "u",
      itemId: "item-only",
      startedAtMs: 1,
    },
  });
  assert.equal(norm.permissionId, "item-only");
});

test("isServerApprovalMethod recognizes locked approval methods", () => {
  assert.equal(isServerApprovalMethod(SERVER_APPROVAL_METHODS.COMMAND_EXECUTION_REQUEST_APPROVAL), true);
  assert.equal(isServerApprovalMethod(SERVER_APPROVAL_METHODS.FILE_CHANGE_REQUEST_APPROVAL), true);
  assert.equal(isServerApprovalMethod("item/tool/call"), false);
});

test("createAdapter emits permission callback and can respond for command approval", async () => {
  /** @type {ReturnType<typeof normalizePermissionRequest> | undefined} */
  let captured;
  const adapter = createAdapter({
    onPermission: (req) => {
      captured = req;
    },
  });

  await adapter.feedLine(
    JSON.stringify({
      jsonrpc: "2.0",
      id: 7,
      method: SERVER_APPROVAL_METHODS.COMMAND_EXECUTION_REQUEST_APPROVAL,
      params: {
        threadId: "th1",
        turnId: "tu1",
        itemId: "p1",
        command: "echo hi",
        startedAtMs: 1,
      },
    }),
  );

  assert.ok(captured);
  assert.equal(captured.permissionId, "p1");

  const responseLine = adapter.respondPermission("p1", "session");
  assert.ok(responseLine);
  const parsed = decodeLine(responseLine);
  assert.equal(parsed?.id, 7);
  assert.deepEqual(parsed?.result, {
    decision: ITEM_APPROVAL_DECISIONS.ACCEPT_FOR_SESSION,
  });
});

test("encodePermissionResponse round-trip for deny", () => {
  const line = encodePermissionResponse(99, "deny", {
    rawMethod: SERVER_APPROVAL_METHODS.COMMAND_EXECUTION_REQUEST_APPROVAL,
  });
  const parsed = decodeLine(line);
  assert.equal(parsed?.id, 99);
  assert.deepEqual(parsed?.result, { decision: ITEM_APPROVAL_DECISIONS.DECLINE });
});

test("command approval with numeric id does not steal pending turn/start response", async () => {
  const pendingRpc = new Map();
  let resolved = false;
  let permissionCaptured = false;

  pendingRpc.set(1, {
    resolve: () => {
      resolved = true;
    },
    reject: () => {},
    method: CLIENT_METHODS.TURN_START,
  });

  const adapter = createAdapter({
    onPermission: () => {
      permissionCaptured = true;
    },
  });

  const approvalMsg = {
    jsonrpc: "2.0",
    id: 1,
    method: SERVER_APPROVAL_METHODS.COMMAND_EXECUTION_REQUEST_APPROVAL,
    params: {
      threadId: "th1",
      turnId: "tu1",
      itemId: "tool-1",
      command: "npm test",
      startedAtMs: 1,
    },
  };

  const routeResult = handleInboundLine(approvalMsg, { pendingRpc, adapter });
  await Promise.resolve();

  assert.equal(routeResult.handled, "request");
  assert.equal(pendingRpc.has(1), true);
  assert.equal(resolved, false);
  assert.equal(permissionCaptured, true);
});

test("handleInboundLine resolves pendingRpc for genuine client responses", () => {
  const pendingRpc = new Map();
  let result;

  pendingRpc.set("gaf-c-1", {
    resolve: (v) => {
      result = v;
    },
    reject: () => {},
    method: CLIENT_METHODS.TURN_START,
  });

  const adapter = createAdapter();
  const routeResult = handleInboundLine(
    { jsonrpc: "2.0", id: "gaf-c-1", result: { turnId: "turn-1" } },
    { pendingRpc, adapter },
  );

  assert.equal(routeResult.handled, "response");
  assert.equal(pendingRpc.has("gaf-c-1"), false);
  assert.deepEqual(result, { turnId: "turn-1" });
});

test("normalizePermissionRequest rejects non-approval methods", () => {
  assert.throws(
    () =>
      normalizePermissionRequest({
        jsonrpc: "2.0",
        id: 1,
        method: "item/tool/call",
        params: {},
      }),
    CodexAppServerProtocolError,
  );
});

test("encodePermissionDecision throws for permissions deny in v1", () => {
  assert.throws(
    () =>
      encodePermissionDecision("deny", {
        rawMethod: SERVER_APPROVAL_METHODS.PERMISSIONS_REQUEST_APPROVAL,
      }),
    CodexAppServerProtocolError,
  );
});

test("permissions approval once encodes turn scope grant", () => {
  const perms = { network: { enabled: true } };
  const result = encodePermissionDecision("once", {
    rawMethod: SERVER_APPROVAL_METHODS.PERMISSIONS_REQUEST_APPROVAL,
    requestedPermissions: perms,
  });
  assert.deepEqual(result, { permissions: perms, scope: "turn" });
});
