import assert from "node:assert/strict";
import test from "node:test";

import {
  ACP_METHODS,
  ACP_PERMISSION_OPTION_IDS,
  AcpProtocolError,
  acpModeIdForFoundryPermissionMode,
  buildPermissionResult,
  createAdapter,
  decodeLine,
  encodePermissionResponse,
  encodeRequest,
  mapDecisionToAcp,
  normalizePermissionRequest,
} from "./cursor_acp_adapter.mjs";

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
  const line = encodeRequest(2, ACP_METHODS.INITIALIZE, { protocolVersion: 1 });
  assert.ok(line.endsWith("\n"));
  assert.equal(decodeLine(line)?.method, ACP_METHODS.INITIALIZE);
});

test("mapDecisionToAcp maps Foundry decisions to Cursor optionIds", () => {
  assert.equal(mapDecisionToAcp("once"), ACP_PERMISSION_OPTION_IDS.ALLOW_ONCE);
  assert.equal(mapDecisionToAcp("turn"), ACP_PERMISSION_OPTION_IDS.ALLOW_ONCE);
  assert.equal(mapDecisionToAcp("session"), ACP_PERMISSION_OPTION_IDS.ALLOW_ALWAYS);
  assert.equal(mapDecisionToAcp("deny"), ACP_PERMISSION_OPTION_IDS.REJECT_ONCE);
});

test("buildPermissionResult uses selected outcome shape", () => {
  assert.deepEqual(buildPermissionResult("once"), {
    outcome: { outcome: "selected", optionId: "allow-once" },
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
      options: [{ id: "allow-once", label: "Allow once" }],
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
  /** @type {import('./cursor_acp_adapter.mjs').normalizePermissionRequest extends (...args: any) => infer R ? R : never} */
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
    outcome: { outcome: "selected", optionId: "reject-once" },
  });
});
