/**
 * Loopback HTTP bridge: Python POSTs mutate-tool permission requests;
 * Electron holds the connection until the renderer decides (or timeout).
 */
import http from "node:http";
import crypto from "node:crypto";

const DEFAULT_TIMEOUT_MS = 300_000;

/**
 * @param {object} opts
 * @param {() => import('electron').WebContents | null} opts.getSender
 * @param {number} [opts.timeoutMs]
 */
export function createToolPermissionBridge(opts) {
  const getSender = opts.getSender;
  const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  /** @type {Map<string, { resolve: (d: string) => void, timer: NodeJS.Timeout, sessionId: string, turnId: string }>} */
  const pending = new Map();
  /** @type {Set<string>} */
  const sessionAllow = new Set();
  /** @type {Set<string>} */
  const turnAllow = new Set();
  const token = crypto.randomBytes(16).toString("hex");

  const server = http.createServer(async (req, res) => {
    if (req.method === "OPTIONS") {
      res.writeHead(204, corsHeaders());
      res.end();
      return;
    }
    if (req.method !== "POST" || req.url?.split("?")[0] !== "/tool-permission") {
      res.writeHead(404, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "not found" }));
      return;
    }
    const auth = String(req.headers.authorization || "");
    if (auth !== `Bearer ${token}`) {
      res.writeHead(401, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "unauthorized" }));
      return;
    }

    let body = "";
    for await (const chunk of req) {
      body += chunk.toString("utf8");
      if (body.length > 200_000) break;
    }
    let payload;
    try {
      payload = JSON.parse(body || "{}");
    } catch {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "invalid json" }));
      return;
    }

    const permissionId = String(payload.permission_id || crypto.randomUUID());
    const sessionId = String(payload.session_id || "");
    const turnId = String(payload.turn_id || "");
    const argvSummary = String(payload.argv_summary || "").slice(0, 500);

    if (sessionId && sessionAllow.has(sessionId)) {
      writeDecision(res, "session");
      return;
    }
    if (turnId && turnAllow.has(turnId)) {
      writeDecision(res, "turn");
      return;
    }

    const sender = getSender();
    if (!sender || sender.isDestroyed()) {
      writeDecision(res, "deny");
      return;
    }

    const decision = await new Promise((resolve) => {
      const timer = setTimeout(() => {
        pending.delete(permissionId);
        resolve("deny");
      }, timeoutMs);
      pending.set(permissionId, { resolve, timer, sessionId, turnId });
      try {
        sender.send("agent-tool-permission", {
          permissionId,
          sessionId,
          turnId,
          argvSummary,
          argv: Array.isArray(payload.argv) ? payload.argv.slice(0, 40) : [],
        });
      } catch {
        clearTimeout(timer);
        pending.delete(permissionId);
        resolve("deny");
      }
    });

    if (decision === "session" && sessionId) sessionAllow.add(sessionId);
    if (decision === "turn" && turnId) turnAllow.add(turnId);
    writeDecision(res, decision === "timeout" ? "deny" : decision);
  });

  server.listen(0, "127.0.0.1");

  function env() {
    const addr = server.address();
    if (!addr || typeof addr === "string") return {};
    return {
      GAMEFACTORY_TOOL_PERMISSION_URL: `http://127.0.0.1:${addr.port}/tool-permission`,
      GAMEFACTORY_TOOL_PERMISSION_TOKEN: token,
    };
  }

  function decide(permissionId, decision) {
    const entry = pending.get(String(permissionId || ""));
    if (!entry) return false;
    clearTimeout(entry.timer);
    pending.delete(String(permissionId));
    const d = ["once", "turn", "session", "deny"].includes(decision) ? decision : "deny";
    entry.resolve(d);
    return true;
  }

  function close() {
    for (const [, entry] of pending) {
      clearTimeout(entry.timer);
      entry.resolve("deny");
    }
    pending.clear();
    try {
      server.close();
    } catch {
      /* ignore */
    }
  }

  return { env, decide, close, server };
}

function writeDecision(res, decision) {
  res.writeHead(200, { "Content-Type": "application/json; charset=utf-8", ...corsHeaders() });
  res.end(JSON.stringify({ decision }));
}

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
  };
}
