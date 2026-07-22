import assert from "node:assert/strict";
import test from "node:test";

import {
  ACP_METHODS,
  ACP_PERMISSION_OPTION_IDS,
  AcpProtocolError,
  HERMES_ACP_CLIENT_ID_PREFIX,
  HERMES_ACP_SPAWN_ARGS,
  acpModeIdForFoundryPermissionMode,
  buildPermissionResult,
  createAdapter,
  createClientRpcId,
  decodeLine,
  encodePermissionResponse,
  encodeRequest,
  handleInboundRpcLine,
  mapDecisionToAcp,
  normalizePermissionRequest,
} from "./hermes_acp_adapter.mjs";

test("HERMES_ACP_SPAWN_ARGS includes --accept-hooks", () => {
  assert.deepEqual(HERMES_ACP_SPAWN_ARGS, ["--accept-hooks"]);
});

test("createClientRpcId uses gaf-h- prefix distinct from Cursor", () => {
  assert.equal(createClientRpcId(1), `${HERMES_ACP_CLIENT_ID_PREFIX}1`);
  assert.match(createClientRpcId(42), /^gaf-h-\d+$/);
});

test("acpModeIdForFoundryPermissionMode maps plan/ask/auto_review", () => {
  assert.equal(acpModeIdForFoundryPermissionMode("plan"), "plan");
  assert.equal(acpModeIdForFoundryPermissionMode("ask"), "ask");
  assert.equal(acpModeIdForFoundryPermissionMode("auto_review"), "agent");
  assert.equal(acpModeIdForFoundryPermissionMode("force"), "agent");
});

test("decodeLine parses NDJSON JSON-RPC", () => {
  const msg = decodeLine('{"jsonrpc":"2.0","id":1,"result":{"ok":true}}\n');
  assert.equal(msg?.id, 1);
  assert.deepEqual(msg?.result, { ok: true });
});

test("decodeLine rejects invalid JSON", () => {
  assert.throws(() => decodeLine("{not-json"), AcpProtocolError);
});

test("encodeRequest uses NDJSON newline framing", () => {
  const line = encodeRequest("gaf-h-1", ACP_METHODS.INITIALIZE, { protocolVersion: 1 });
  assert.ok(line.endsWith("\n"));
  assert.equal(decodeLine(line)?.method, ACP_METHODS.INITIALIZE);
});

test("mapDecisionToAcp maps Foundry decisions to Hermes optionIds", () => {
  assert.equal(mapDecisionToAcp("once"), ACP_PERMISSION_OPTION_IDS.ALLOW_ONCE);
  assert.equal(mapDecisionToAcp("turn"), ACP_PERMISSION_OPTION_IDS.ALLOW_ONCE);
  assert.equal(mapDecisionToAcp("session"), ACP_PERMISSION_OPTION_IDS.ALLOW_ALWAYS);
  assert.equal(mapDecisionToAcp("deny"), ACP_PERMISSION_OPTION_IDS.DENY);
});

test("mapDecisionToAcp rejects unknown decision", () => {
  assert.throws(() => mapDecisionToAcp(/** @type {any} */ ("bogus")), AcpProtocolError);
});

test("buildPermissionResult uses Hermes selected outcome shape", () => {
  assert.deepEqual(buildPermissionResult("once"), {
    outcome: { outcome: "selected", optionId: "allow_once" },
  });
  assert.deepEqual(buildPermissionResult("session"), {
    outcome: { outcome: "selected", optionId: "allow_always" },
  });
});

test("normalizePermissionRequest extracts permissionId and summary", () => {
  const raw = {
    jsonrpc: "2.0",
    id: 42,
    method: ACP_METHODS.SESSION_REQUEST_PERMISSION,
    params: {
      sessionId: "sess-1",
      toolCall: {
        toolCallId: "tc-9",
        title: "Run shell command",
        description: "npm test",
      },
      options: [{ optionId: "allow_once", name: "Allow once" }],
    },
  };
  const norm = normalizePermissionRequest(raw);
  assert.equal(norm.permissionId, "tc-9");
  assert.equal(norm.jsonRpcId, 42);
  assert.equal(norm.sessionId, "sess-1");
  assert.match(norm.summary, /Run shell command/);
  assert.equal(norm.raw, raw);
});

test("createAdapter emits permission callback and can respond", async () => {
  /** @type {import('./hermes_acp_adapter.mjs').normalizePermissionRequest extends (...args: any) => infer R ? R : never} */
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
      method: ACP_METHODS.SESSION_REQUEST_PERMISSION,
      params: {
        sessionId: "s1",
        toolCall: { toolCallId: "p1", title: "Write file" },
      },
    }),
  );

  assert.ok(captured);
  assert.equal(captured.permissionId, "p1");

  const responseLine = adapter.respondPermission("p1", "session");
  assert.ok(responseLine);
  const parsed = decodeLine(responseLine);
  assert.equal(parsed?.id, 7);
  assert.deepEqual(parsed?.result, buildPermissionResult("session"));
});

test("encodePermissionResponse round-trip", () => {
  const line = encodePermissionResponse(99, "deny");
  const parsed = decodeLine(line);
  assert.equal(parsed?.id, 99);
  assert.deepEqual(parsed?.result, {
    outcome: { outcome: "selected", optionId: "deny" },
  });
});

test("permission request with numeric id does not steal pending prompt response", async () => {
  const pendingRpc = new Map();
  let resolved = false;
  let permissionCaptured = false;

  pendingRpc.set(1, {
    resolve: () => {
      resolved = true;
    },
    reject: () => {},
    method: ACP_METHODS.SESSION_PROMPT,
  });

  const adapter = createAdapter({
    onPermission: () => {
      permissionCaptured = true;
    },
  });

  const permissionMsg = {
    jsonrpc: "2.0",
    id: 1,
    method: ACP_METHODS.SESSION_REQUEST_PERMISSION,
    params: {
      sessionId: "s1",
      toolCall: { toolCallId: "tool-1", title: "Run test" },
    },
  };

  const routeResult = handleInboundRpcLine(permissionMsg, { pendingRpc, adapter });
  await Promise.resolve();

  assert.equal(routeResult.handled, "request");
  assert.equal(pendingRpc.has(1), true);
  assert.equal(resolved, false);
  assert.equal(permissionCaptured, true);
});

test("handleInboundRpcLine resolves pendingRpc for genuine responses", () => {
  const pendingRpc = new Map();
  let result;

  pendingRpc.set("gaf-h-1", {
    resolve: (v) => {
      result = v;
    },
    reject: () => {},
    method: ACP_METHODS.SESSION_PROMPT,
  });

  const adapter = createAdapter();
  const routeResult = handleInboundRpcLine(
    { jsonrpc: "2.0", id: "gaf-h-1", result: { stopReason: "end_turn" } },
    { pendingRpc, adapter },
  );

  assert.equal(routeResult.handled, "response");
  assert.equal(pendingRpc.has("gaf-h-1"), false);
  assert.deepEqual(result, { stopReason: "end_turn" });
});

test("createAdapter reports unhandled inbound methods", async () => {
  const errors = [];
  const adapter = createAdapter({
    onError: (err) => errors.push(err),
  });

  await adapter.feedLine(
    JSON.stringify({
      jsonrpc: "2.0",
      method: "session/unknown_method",
      params: {},
    }),
  );

  assert.equal(errors.length, 1);
  assert.match(String(errors[0].message), /unhandled inbound ACP method/);
});
