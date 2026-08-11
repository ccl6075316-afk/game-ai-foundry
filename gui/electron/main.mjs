import { app, BrowserWindow, ipcMain, shell, protocol, net } from "electron";
import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import {
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  statSync,
  writeFileSync,
} from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import {
  cliDir,
  isPackagedApp,
  preloadPath,
  rendererIndexPath,
  repoRoot,
  resolvePiRuntimeRoot,
  resolvePython,
} from "./paths.mjs";
import { initAutoUpdate, registerAutoUpdateIpc } from "./autoUpdate.mjs";
import { createToolPermissionBridge } from "./tool_permission_bridge.mjs";
import { createCursorAcpSessionManager } from "./cursor_acp_session.mjs";
import { createHermesAcpSessionManager } from "./hermes_acp_session.mjs";
import { createCodexAppServerSessionManager } from "./codex_app_server_session.mjs";
import { killChildTree } from "./process_kill.mjs";
import {
  buildAgentTurnArgs,
  prepareRoleAwareAcpPrompt,
  resolveItExecutor,
} from "./agent_prompt.mjs";
import {
  absForResolved,
  cliArgForResolved,
  isExternalVirtualRel,
  manifestBelongsToBrief,
  normalizeRepoRel,
  pathUnderRoot,
  projectRootKeyFromBriefRel,
  resolveExternalAbs,
} from "./externalFs.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isDev = !isPackagedApp();

const ACP_PERMISSION_TIMEOUT_MS = 300_000;

/** @type {ReturnType<typeof createToolPermissionBridge> | null} */
let toolPermissionBridge = null;

/** @type {ReturnType<typeof createCursorAcpSessionManager> | null} */
let cursorAcpSessionManager = null;

/** @type {ReturnType<typeof createHermesAcpSessionManager> | null} */
let hermesAcpSessionManager = null;

/** @type {ReturnType<typeof createCodexAppServerSessionManager> | null} */
let codexAppServerSessionManager = null;

/** @type {Map<string, NodeJS.Timeout>} */
const acpPermissionTimers = new Map();

/** @returns {ReturnType<typeof createCursorAcpSessionManager> | null} */
export function getCursorAcpSessionManager() {
  return cursorAcpSessionManager;
}

/** @returns {ReturnType<typeof createHermesAcpSessionManager> | null} */
export function getHermesAcpSessionManager() {
  return hermesAcpSessionManager;
}

/** @param {string} permissionId */
function clearAcpPermissionTimer(permissionId) {
  const id = String(permissionId || "");
  const timer = acpPermissionTimers.get(id);
  if (!timer) return;
  clearTimeout(timer);
  acpPermissionTimers.delete(id);
}

/**
 * @param {object} payload
 * @param {string} payload.permissionId
 * @param {string} payload.sessionId
 * @param {string} [payload.turnId]
 * @param {string} payload.argvSummary
 * @param {"cursor_acp" | "hermes_acp" | "codex_app_server"} [payload.source]
 * @returns {boolean}
 */
function sendAgentToolPermission(payload) {
  const sender = mainWindow && !mainWindow.isDestroyed() ? mainWindow.webContents : null;
  if (!sender || sender.isDestroyed()) return false;
  sender.send("agent-tool-permission", payload);
  return true;
}

/** Notify renderer that a pending card timed out / was decided off-UI. */
function sendAgentToolPermissionResolved(permissionId, decision) {
  const sender = mainWindow && !mainWindow.isDestroyed() ? mainWindow.webContents : null;
  if (!sender || sender.isDestroyed()) return;
  sender.send("agent-tool-permission-resolved", {
    permissionId: String(permissionId || ""),
    decision: String(decision || "deny"),
  });
}

/**
 * Route Cursor/Hermes/Codex tool approvals to the UI (in-chat permission card).
 * Always sends IPC — never silently auto-allow here.
 *
 * @param {object} opts
 * @param {string} opts.permissionId
 * @param {string} opts.sessionId
 * @param {string} [opts.turnId]
 * @param {string} [opts.instanceId]
 * @param {string} opts.argvSummary
 * @param {"cursor_acp" | "hermes_acp" | "codex_app_server"} opts.source
 * @param {(permissionId: string, decision: string) => void} opts.decide
 */
function routeExternalToolPermission(opts) {
  const permissionId = String(opts.permissionId || "");
  const sessionId = String(opts.sessionId || "");
  const turnId = String(opts.turnId || "");
  const instanceId = String(opts.instanceId || "");
  const argvSummary = String(opts.argvSummary || "").slice(0, 500);
  const source = opts.source;

  console.log(`[${source}] permission requested`, {
    permissionId,
    sessionId,
    turnId,
    instanceId,
    argvSummary,
  });

  // Always surface UI — do not silently auto-allow here. Pi FOUNDRY_TOOL trust
  // stays on tool_permission_bridge only; Codex/Cursor need a visible in-chat card.

  const sent = sendAgentToolPermission({
    permissionId,
    sessionId,
    turnId,
    instanceId,
    argvSummary,
    source,
  });
  if (!sent) {
    console.log(`[${source}] permission deny — no renderer`, { permissionId });
    opts.decide(permissionId, "deny");
    return;
  }

  clearAcpPermissionTimer(permissionId);
  const timer = setTimeout(() => {
    acpPermissionTimers.delete(permissionId);
    console.log(`[${source}] permission timeout → deny`, { permissionId });
    opts.decide(permissionId, "deny");
    sendAgentToolPermissionResolved(permissionId, "deny");
  }, ACP_PERMISSION_TIMEOUT_MS);
  acpPermissionTimers.set(permissionId, timer);
}

const IMAGE_EXTS = new Set([".png", ".jpg", ".jpeg", ".webp", ".gif"]);
const VIDEO_EXTS = new Set([".mp4", ".webm", ".mov", ".mkv"]);

protocol.registerSchemesAsPrivileged([
  {
    scheme: "gamefactory-media",
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: true,
      bypassCSP: true,
      stream: true,
    },
  },
]);

/** Prepend common install dirs so CLI can find Node / agent / brew tools.
 * Electron.app PATH often omits ~/.local/bin (Cursor Agent) and Homebrew.
 */
function pathWithCommonNodeBins(basePath) {
  const home = os.homedir();
  const extras = [
    path.join(home, ".gamefactory", "toolchain", "bin"),
    path.join(home, ".local", "bin"),
    path.join(process.env.LOCALAPPDATA || path.join(home, "AppData", "Local"), "Programs", "OpenAI", "Codex", "bin"),
    path.join(home, ".codex", "packages", "standalone", "current"),
    path.join(home, ".local", "share", "cursor-agent", "versions"),
    path.join(process.env.APPDATA || path.join(home, "AppData", "Roaming"), "npm"),
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
  // Also prepend latest cursor-agent version dir if present (binary lives there).
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

/** @type {Map<string, import('node:child_process').ChildProcess>} */
const cliJobs = new Map();
/** All spawned CLI children (including those without a jobKey). */
/** @type {Set<import('node:child_process').ChildProcess>} */
const cliChildren = new Set();
/** Instance ids whose in-flight chat turn was user-aborted (ACP + CLI). */
const abortedChatInstances = new Set();

function chatJobKey(instanceId) {
  const id = String(instanceId || "").trim();
  return id ? `chat:${id}` : "";
}

function trackCliChild(child) {
  if (!child) return;
  cliChildren.add(child);
  const clear = () => {
    cliChildren.delete(child);
  };
  child.once("close", clear);
  child.once("exit", clear);
  child.once("error", clear);
}

function registerCliJob(jobKey, child) {
  if (!jobKey || !child) return;
  const prev = cliJobs.get(jobKey);
  if (prev && prev !== child && !prev.killed) {
    killChildTree(prev, { sync: false });
  }
  cliJobs.set(jobKey, child);
  const clear = () => {
    if (cliJobs.get(jobKey) === child) cliJobs.delete(jobKey);
  };
  child.once("close", clear);
  child.once("exit", clear);
  child.once("error", clear);
}

function abortCliJob(jobKey) {
  if (!jobKey) return false;
  const child = cliJobs.get(jobKey);
  if (!child || child.killed) return false;
  const ok = killChildTree(child, { sync: false });
  cliJobs.delete(jobKey);
  cliChildren.delete(child);
  return ok;
}

/** Kill every tracked CLI child (and Windows process trees). Prefer sync on app quit. */
function abortAllCliJobs(opts = {}) {
  const sync = Boolean(opts.sync);
  for (const child of [...cliChildren]) {
    killChildTree(child, { sync });
  }
  for (const key of [...cliJobs.keys()]) {
    const child = cliJobs.get(key);
    if (child) killChildTree(child, { sync });
  }
  cliChildren.clear();
  cliJobs.clear();
}

function stopChatRuntime(instanceId) {
  const id = String(instanceId || "").trim();
  if (!id) return { ok: false, error: "instanceId required" };
  abortedChatInstances.add(id);
  const killedCli = abortCliJob(chatJobKey(id));
  let stoppedAcp = false;
  try {
    if (cursorAcpSessionManager) {
      cursorAcpSessionManager.stop(id);
      stoppedAcp = true;
    }
  } catch {
    /* ignore */
  }
  try {
    if (hermesAcpSessionManager) {
      hermesAcpSessionManager.stop(id);
      stoppedAcp = true;
    }
  } catch {
    /* ignore */
  }
  try {
    if (codexAppServerSessionManager) {
      codexAppServerSessionManager.stop(id);
      stoppedAcp = true;
    }
  } catch {
    /* ignore */
  }
  return { ok: true, aborted: killedCli || stoppedAcp, killedCli, stoppedAcp };
}

function takeChatAbort(instanceId) {
  const id = String(instanceId || "").trim();
  if (!id || !abortedChatInstances.has(id)) return false;
  abortedChatInstances.delete(id);
  return true;
}

function abortedChatResult(extra = {}) {
  return {
    exitCode: 130,
    stdout: "",
    stderr: "已停止",
    aborted: true,
    data: { ok: false, aborted: true, error: "已停止" },
    ...extra,
  };
}

function withAbortMeta(result, instanceId) {
  const aborted = Boolean(result?.aborted) || takeChatAbort(instanceId);
  if (!aborted) return { ...result, aborted: false };
  const data =
    result?.data && typeof result.data === "object"
      ? { ...result.data, ok: false, aborted: true, error: result.data.error || "已停止" }
      : { ok: false, aborted: true, error: "已停止" };
  return {
    ...result,
    exitCode: 130,
    aborted: true,
    data,
  };
}

/**
 * Env for Codex / Cursor / Hermes child processes so shell tools can call
 * Foundry via GAMEFACTORY_PYTHON (embedded or venv), matching runCli.
 * @returns {NodeJS.ProcessEnv}
 */
function agentExecutorChildEnv() {
  const root = repoRoot();
  const python = resolvePython(root);
  const pythonDir = path.dirname(python);
  const pathEnv = pythonDir
    ? [pythonDir, pathWithCommonNodeBins(process.env.PATH)].filter(Boolean).join(path.delimiter)
    : pathWithCommonNodeBins(process.env.PATH);
  return {
    ...process.env,
    PATH: pathEnv,
    GAMEFACTORY_ROOT: root,
    GAMEFACTORY_PYTHON: python,
  };
}

function runCli(args, { cwd, onLine, jobKey } = {}) {
  const root = repoRoot();
  const python = resolvePython(root);
  const workdir = cwd || cliDir(root);
  const permissionEnv = toolPermissionBridge ? toolPermissionBridge.env() : {};
  const pythonDir = path.dirname(python);
  const pathWithPython = pythonDir
    ? [pythonDir, pathWithCommonNodeBins(process.env.PATH)].filter(Boolean).join(path.delimiter)
    : pathWithCommonNodeBins(process.env.PATH);

  return new Promise((resolve, reject) => {
    const proc = spawn(python, ["gamefactory.py", ...args], {
      cwd: workdir,
      env: {
        ...process.env,
        PATH: pathWithPython,
        GAMEFACTORY_ROOT: root,
        GAMEFACTORY_PYTHON: python,
        PYTHONIOENCODING: "utf-8",
        // Prefer system Node for Pi when present; Electron-as-Node is Release fallback
        // (see cli/pi_runtime._node_candidates). Still pass execPath for that fallback.
        GAMEFACTORY_ELECTRON_EXECUTABLE: process.execPath,
        ...(resolvePiRuntimeRoot()
          ? { GAMEFACTORY_PI_ROOT: resolvePiRuntimeRoot() }
          : {}),
        ...permissionEnv,
      },
      shell: false,
    });

    if (jobKey) registerCliJob(String(jobKey), proc);
    trackCliChild(proc);

    let stdout = "";
    let stderr = "";
    let aborted = false;

    const emit = (chunk, stream) => {
      const text = chunk.toString("utf-8");
      if (stream === "stdout") stdout += text;
      else stderr += text;
      if (onLine) {
        for (const line of text.split(/\r?\n/)) {
          if (line.trim()) onLine(line, stream);
        }
      }
    };

    proc.stdout.on("data", (c) => emit(c, "stdout"));
    proc.stderr.on("data", (c) => emit(c, "stderr"));
    proc.on("error", (err) => {
      const detail =
        err && typeof err === "object" && "code" in err && err.code === "ENOENT"
          ? `找不到 CLI Python：${python}（Release 应内嵌 resources/python；请重装最新安装包）`
          : err instanceof Error
            ? err.message
            : String(err);
      reject(new Error(detail));
    });
    proc.on("close", (code, signal) => {
      if (signal === "SIGTERM" || signal === "SIGKILL") aborted = true;
      if (code === 130 || code === 137 || code === 143) aborted = true;
      resolve({ exitCode: code ?? 1, stdout, stderr, aborted });
    });
  });
}

function extractBalancedJsonObject(text) {
  const start = text.indexOf("{");
  if (start < 0) return null;
  let depth = 0;
  let inString = false;
  let escape = false;
  for (let i = start; i < text.length; i += 1) {
    const ch = text[i];
    if (inString) {
      if (escape) escape = false;
      else if (ch === "\\") escape = true;
      else if (ch === '"') inString = false;
      continue;
    }
    if (ch === '"') inString = true;
    else if (ch === "{") depth += 1;
    else if (ch === "}") {
      depth -= 1;
      if (depth === 0) return text.slice(start, i + 1);
    }
  }
  return null;
}

function parseJsonFromOutput(text) {
  const trimmed = String(text || "")
    .replace(/^\uFEFF/, "")
    .trim();
  if (!trimmed) return null;
  try {
    const parsed = JSON.parse(trimmed);
    if (parsed && typeof parsed === "object") return parsed;
  } catch {
    /* fall through */
  }
  const balanced = extractBalancedJsonObject(trimmed);
  if (balanced) {
    try {
      return JSON.parse(balanced);
    } catch {
      /* fall through */
    }
  }
  // Last resort: from first { to last }
  const start = trimmed.indexOf("{");
  const end = trimmed.lastIndexOf("}");
  if (start >= 0 && end > start) {
    try {
      return JSON.parse(trimmed.slice(start, end + 1));
    } catch {
      return null;
    }
  }
  return null;
}

function listBriefs() {
  const root = repoRoot();
  const out = [];
  const seen = new Set();
  const pushEntry = (rel, label, mtime, status = "ready") => {
    const normRel = String(rel).replace(/\\/g, "/");
    if (seen.has(normRel)) return;
    seen.add(normRel);
    out.push({
      id: normRel.replace(/\.json$/i, "").replace(/[\\/]/g, "__"),
      path: normRel,
      label: label || path.basename(rel),
      mtime: mtime || 0,
      status,
    });
  };
  const pushFile = (abs, rel, label, status = "ready") => {
    if (!existsSync(abs) || !statSync(abs).isFile()) return;
    const normRel = String(rel).replace(/\\/g, "/");
    try {
      const data = JSON.parse(readFileSync(abs, "utf-8"));
      // Skip legacy redirect stubs (migrated games) — follow to projects/
      if (data?.brief_meta?.redirect_to || data?.brief_meta?.migrated) {
        const target = String(data.brief_meta.redirect_to || "").replace(/\\/g, "/");
        if (target) {
          const tAbs = path.join(root, target);
          if (existsSync(tAbs)) {
            pushFile(tAbs, target, path.basename(path.dirname(target)) + "/brief.json");
          }
        }
        return;
      }
    } catch {
      /* list anyway if not JSON-parseable */
    }
    const stat = statSync(abs);
    pushEntry(normRel, label, stat.mtimeMs, status);
  };

  const projectsDir = path.join(root, "projects");
  if (existsSync(projectsDir)) {
    for (const name of readdirSync(projectsDir)) {
      if (name.startsWith(".")) continue;
      const dir = path.join(projectsDir, name);
      if (!statSync(dir).isDirectory()) continue;
      const brief = path.join(dir, "brief.json");
      const alt = path.join(dir, `${name}-brief.json`);
      const draft = path.join(dir, "brief.draft.json");
      const meta = path.join(dir, "project.meta.json");
      if (existsSync(brief)) {
        pushFile(brief, path.join("projects", name, "brief.json"), `${name}/brief.json`, "ready");
      } else if (existsSync(alt)) {
        pushFile(alt, path.join("projects", name, `${name}-brief.json`), `${name}/${name}-brief.json`, "ready");
      } else if (existsSync(draft) || existsSync(meta)) {
        // Unfinished project: still selectable via canonical brief.json path
        const st = existsSync(draft) ? statSync(draft) : statSync(meta);
        pushEntry(
          path.join("projects", name, "brief.json").replace(/\\/g, "/"),
          `${name}（草稿）`,
          st.mtimeMs,
          "draft",
        );
      }
    }
  }

  for (const folder of ["resources", path.join("cli", "resources")]) {
    const dir = path.join(root, folder);
    if (!existsSync(dir)) continue;
    for (const f of readdirSync(dir)) {
      if (!f.endsWith(".json") || !f.includes("brief")) continue;
      if (f.toLowerCase().includes("example")) continue;
      pushFile(path.join(dir, f), path.join(folder, f), f);
    }
  }

  return out.sort((a, b) => b.mtime - a.mtime);
}

function loadExternalRegistry() {
  const regPath = path.join(repoRoot(), "external-projects.json");
  if (!existsSync(regPath)) {
    return { version: 1, projects: [] };
  }
  try {
    const data = JSON.parse(readFileSync(regPath, "utf-8"));
    const projects = Array.isArray(data?.projects) ? data.projects : [];
    return { version: Number(data?.version) || 1, projects };
  } catch {
    return { version: 1, projects: [] };
  }
}

function getExternalEntryById(extId) {
  const id = String(extId || "").trim();
  if (!id) return null;
  for (const entry of loadExternalRegistry().projects) {
    if (entry && typeof entry === "object" && entry.id === id) {
      return entry;
    }
  }
  return null;
}

/** Resolve virtual external:<id>/… keys to absolute paths under registered root_abs. */
function resolveExternalRel(relPath) {
  return resolveExternalAbs(relPath, getExternalEntryById);
}

/** CLI cwd is cli/ — external → absolute; repo → ../rel. */
function cliArgForRel(rel) {
  return cliArgForResolved(rel, {
    resolvedExternal: resolveExternalRel(rel),
    repoRoot: repoRoot(),
  });
}

/** Absolute filesystem path for mkdir/read/write. */
function absForRel(rel) {
  return absForResolved(rel, {
    resolvedExternal: resolveExternalRel(rel),
    repoRoot: repoRoot(),
  });
}

function resolveReadableRel(relPath) {
  const external = resolveExternalRel(relPath);
  if (external) return external;
  const repo = resolveRepoRel(relPath);
  if (repo) return { ...repo, entry: null, rootAbs: null };
  return null;
}

function resolveRepoRel(relPath) {
  if (!relPath || typeof relPath !== "string") return null;
  const root = path.resolve(repoRoot());
  const normalized = relPath.replace(/\\/g, "/").replace(/^\/+/, "");
  if (!normalized || normalized.includes("..")) return null;
  if (normalized.toLowerCase().startsWith("external:")) return null;
  const full = path.resolve(root, normalized);
  if (full !== root && !full.startsWith(root + path.sep)) return null;
  return { full, rel: normalized };
}

function readRepoText(relPath) {
  const resolved = resolveReadableRel(relPath);
  if (!resolved) return { ok: false, error: "invalid path" };
  if (!existsSync(resolved.full) || !statSync(resolved.full).isFile()) {
    return { ok: false, error: "file not found", path: resolved.rel };
  }
  try {
    const text = readFileSync(resolved.full, "utf-8");
    // Cap oversized files for GUI preview.
    const max = 400_000;
    return {
      ok: true,
      path: resolved.rel,
      text: text.length > max ? `${text.slice(0, max)}\n\n…(truncated)` : text,
    };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : String(e), path: resolved.rel };
  }
}

/** Merge fields into brief.project and rewrite the file (keeps rest of brief). */
function patchBriefProject(relPath, projectPatch) {
  const resolved = resolveReadableRel(relPath);
  if (!resolved) return { ok: false, error: "invalid path" };
  if (!existsSync(resolved.full) || !statSync(resolved.full).isFile()) {
    return { ok: false, error: "file not found", path: resolved.rel };
  }
  if (!projectPatch || typeof projectPatch !== "object" || Array.isArray(projectPatch)) {
    return { ok: false, error: "projectPatch must be an object" };
  }
  try {
    const data = JSON.parse(readFileSync(resolved.full, "utf-8"));
    if (!data || typeof data !== "object") {
      return { ok: false, error: "brief is not a JSON object" };
    }
    const project =
      data.project && typeof data.project === "object" && !Array.isArray(data.project)
        ? { ...data.project }
        : {};
    const changed = [];
    for (const [key, value] of Object.entries(projectPatch)) {
      if (value === undefined) continue;
      const prev = project[key];
      const nextStr = typeof value === "string" ? value : JSON.stringify(value);
      const prevStr = typeof prev === "string" ? prev : JSON.stringify(prev ?? null);
      if (prevStr === nextStr) continue;
      project[key] = value;
      changed.push(key);
    }
    if (!changed.length) {
      return { ok: true, path: resolved.rel, changed: [], skipped: true };
    }
    data.project = project;
    writeFileSync(resolved.full, `${JSON.stringify(data, null, 2)}\n`, "utf-8");
    return { ok: true, path: resolved.rel, changed, skipped: false };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : String(e), path: resolved.rel };
  }
}

function listProjectDocs(briefRel) {
  const out = [];
  const pushIfExists = (rel, label, kind) => {
    const resolved = resolveReadableRel(rel);
    if (!resolved || !existsSync(resolved.full) || !statSync(resolved.full).isFile()) return;
    if (out.some((d) => d.path === resolved.rel)) return;
    out.push({ path: resolved.rel, label, kind });
  };

  if (briefRel) {
    const norm = String(briefRel).replace(/\\/g, "/");
    const extMatch = norm.match(/^(external:[^/]+)\//i);
    if (extMatch) {
      const root = extMatch[1];
      const extId = root.slice("external:".length);
      const entry = getExternalEntryById(extId);
      const slug =
        String(entry?.display_name || "").trim() ||
        extId.replace(/^ext_/, "") ||
        "external";
      pushIfExists(norm, `Brief · ${slug}`, "json");
      pushIfExists(`${root}/brief.zh.md`, "中文说明 · Brief（全文镜像）", "markdown");
      pushIfExists(`${root}/brief.draft.json`, "工作草稿 · Brief（机器 JSON）", "brief");
      pushIfExists(`${root}/工程说明.md`, "工程说明（目录导读）", "markdown");
      pushIfExists(`${root}/策划笔记.md`, "策划笔记（手写要点）", "markdown");
      pushIfExists(`${root}/production.json`, "Production", "json");
      pushIfExists(`${root}/progress.json`, "Progress", "json");
      pushIfExists(`${root}/pipeline/manifest.json`, "Pipeline manifest", "json");
      const external = resolveExternalRel(root);
      if (external) {
        const rootAbs = external.full;
        if (existsSync(rootAbs) && statSync(rootAbs).isDirectory()) {
          for (const f of readdirSync(rootAbs)) {
            if (!/\.(md|txt)$/i.test(f)) continue;
            if (/^brief\.zh\.md$/i.test(f)) continue;
            if (/^工程说明\.md$/i.test(f)) continue;
            if (/^策划笔记\.md$/i.test(f)) continue;
            if (/\.pre-shard\./i.test(f) || /\.pre-slim\./i.test(f)) continue;
            pushIfExists(`${root}/${f}`, f, "markdown");
          }
          const docsSub = path.join(rootAbs, "docs");
          if (existsSync(docsSub) && statSync(docsSub).isDirectory()) {
            for (const f of readdirSync(docsSub)) {
              if (!/\.(md|txt)$/i.test(f)) continue;
              pushIfExists(`${root}/docs/${f}`, `docs/${f}`, "markdown");
            }
          }
        }
      }
      return out;
    }
    const projMatch = norm.match(/^(projects\/[^/]+)\//i);
    const slug = projMatch
      ? projMatch[1].split("/")[1]
      : path.basename(norm).replace(/\.json$/i, "").replace(/-brief$/i, "") || "game";

      pushIfExists(norm, `Brief · ${slug}`, "json");
      if (projMatch) {
      const root = projMatch[1];
      // Prefer a friendly label for the Chinese companion written on export.
      pushIfExists(`${root}/brief.zh.md`, "中文说明 · Brief（全文镜像）", "markdown");
      pushIfExists(`${root}/brief.draft.json`, "工作草稿 · Brief（机器 JSON）", "brief");
      pushIfExists(`${root}/工程说明.md`, "工程说明（目录导读）", "markdown");
      pushIfExists(`${root}/策划笔记.md`, "策划笔记（手写要点）", "markdown");
      pushIfExists(`${root}/production.json`, "Production", "json");
      pushIfExists(`${root}/progress.json`, "Progress", "json");
      pushIfExists(`${root}/pipeline/manifest.json`, "Pipeline manifest", "json");
      // Project-local notes / GDD sitting next to brief (not under output/)
      const rootAbs = path.join(repoRoot(), root);
      if (existsSync(rootAbs) && statSync(rootAbs).isDirectory()) {
        for (const f of readdirSync(rootAbs)) {
          if (!/\.(md|txt)$/i.test(f)) continue;
          if (/^brief\.zh\.md$/i.test(f)) continue;
          if (/^工程说明\.md$/i.test(f)) continue;
          if (/^策划笔记\.md$/i.test(f)) continue;
          // Migration / slim backups — hide from docs list
          if (/\.pre-shard\./i.test(f) || /\.pre-slim\./i.test(f)) continue;
          if (/\.pre-shard$/i.test(f.replace(/\.(md|txt)$/i, ""))) continue;
          pushIfExists(`${root}/${f}`, f, "markdown");
        }
        const docsSub = path.join(rootAbs, "docs");
        if (existsSync(docsSub) && statSync(docsSub).isDirectory()) {
          for (const f of readdirSync(docsSub)) {
            if (!/\.(md|txt)$/i.test(f)) continue;
            pushIfExists(`${root}/docs/${f}`, `docs/${f}`, "markdown");
          }
        }
      }
    } else {
      pushIfExists(`plans/production_${slug}.json`, "Production", "json");
      pushIfExists(`plans/progress_${slug}.json`, "Progress", "json");
      pushIfExists(`pipeline/${slug}.json`, "Pipeline manifest", "json");
    }
    return out;
  }

  // No active project: do not leak other projects' briefs into the Docs panel.
  return out;
}

function sanitizeProjectSlug(raw) {
  const t = String(raw || "")
    .trim()
    .toLowerCase();
  if (!t) return "";
  if (/[\u4e00-\u9fff]/.test(t) && !/[a-z0-9]/.test(t)) return "";
  return t
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 64);
}

/** Create projects/<slug>/ early so Docs can scope before brief.json exists. */
function ensureProject(slugRaw) {
  const slug = sanitizeProjectSlug(slugRaw);
  if (!slug) {
    return { ok: false, error: "工程目录名需为英文小写与短横线，例如 my-cool-game" };
  }
  const rootRel = `projects/${slug}`;
  const rootAbs = path.join(repoRoot(), rootRel);
  const briefRel = `${rootRel}/brief.json`;
  mkdirSync(rootAbs, { recursive: true });
  for (const sub of ["output", "game", "pipeline", "plans", "docs"]) {
    mkdirSync(path.join(rootAbs, sub), { recursive: true });
  }
  const guideRel = `${rootRel}/工程说明.md`;
  const guideAbs = path.join(repoRoot(), guideRel);
  if (!existsSync(guideAbs)) {
    writeFileSync(
      guideAbs,
      [
        `# ${slug}`,
        "",
        "本工程目录已创建。顶栏会绑定到这里；右侧「文档」**只显示本工程文件**。",
        "",
        "## 文件约定",
        "",
        "| 文件 | 用途 |",
        "|------|------|",
        "| `brief.json` | 英文 brief，给流水线（导出后生成） |",
        "| `brief.zh.md` | 中文说明，给人看（导出 brief 时同步生成） |",
        "| `game/` | Godot 工程 |",
        "| `output/` | 资产生成产物 |",
        "| `pipeline/` | 流水线 manifest |",
        "",
        "先与策划把玩法聊清楚，再在文档面板点「导出 Brief」。",
        "",
      ].join("\n"),
      "utf-8",
    );
  }
  return {
    ok: true,
    slug,
    projectRootRel: rootRel,
    briefRel,
    guideRel,
    existed: existsSync(path.join(rootAbs, "brief.json")),
  };
}

function listManifests() {
  const root = repoRoot();
  const out = [];
  const seen = new Set();
  const pushManifest = (abs, rel) => {
    if (!existsSync(abs) || !statSync(abs).isFile()) return;
    let norm = rel.replace(/\\/g, "/");
    try {
      const data = JSON.parse(readFileSync(abs, "utf-8"));
      if (data?.migrated_to && !data?.tasks) {
        const target = String(data.migrated_to).replace(/\\/g, "/");
        const tAbs = absForRel(target);
        if (existsSync(tAbs)) {
          pushManifest(tAbs, target);
        }
        return;
      }
    } catch {
      /* ignore */
    }
    if (seen.has(norm)) return;
    seen.add(norm);
    const stat = statSync(abs);
    out.push({
      id: norm.replace(/\.json$/i, "").replace(/[\\/]/g, "__"),
      path: norm,
      label: path.basename(norm),
      mtime: stat.mtimeMs,
    });
  };

  // Prefer isolated projects/*/pipeline first
  const projectsDir = path.join(root, "projects");
  if (existsSync(projectsDir)) {
    for (const name of readdirSync(projectsDir)) {
      const pipe = path.join(projectsDir, name, "pipeline");
      if (!existsSync(pipe) || !statSync(pipe).isDirectory()) continue;
      for (const f of readdirSync(pipe)) {
        if (!f.endsWith(".json")) continue;
        pushManifest(
          path.join(pipe, f),
          path.join("projects", name, "pipeline", f),
        );
      }
    }
  }

  const flat = path.join(root, "pipeline");
  if (existsSync(flat)) {
    for (const f of readdirSync(flat)) {
      if (!f.endsWith(".json")) continue;
      pushManifest(path.join(flat, f), path.join("pipeline", f));
    }
  }

  for (const entry of loadExternalRegistry().projects) {
    if (!entry?.id || !entry?.root_abs) continue;
    const pipe = path.join(path.resolve(String(entry.root_abs)), "pipeline");
    if (!existsSync(pipe) || !statSync(pipe).isDirectory()) continue;
    for (const f of readdirSync(pipe)) {
      if (!f.endsWith(".json")) continue;
      pushManifest(path.join(pipe, f), `external:${entry.id}/pipeline/${f}`);
    }
  }

  return out.sort((a, b) => b.mtime - a.mtime);
}

function manifestMeta(relPath) {
  try {
    const manifest = loadManifest(relPath);
    const outputDir = manifest.paths?.output_dir || "";
    const godotProject = manifest.godot_project || "";
    const brief = manifest.brief || "";
    const tasks = Array.isArray(manifest.tasks) ? manifest.tasks : [];
    const counts = {};
    for (const t of tasks) {
      const st = String(t?.status || "pending");
      counts[st] = (counts[st] || 0) + 1;
    }
    return {
      brief: String(brief).replace(/\\/g, "/"),
      output_dir: String(outputDir).replace(/\\/g, "/"),
      godot_project: String(godotProject).replace(/\\/g, "/"),
      project_title: manifest.project?.title || "",
      task_count: tasks.length,
      counts,
    };
  } catch {
    return null;
  }
}

function normalizeBriefKey(p) {
  return String(p || "")
    .replace(/\\/g, "/")
    .replace(/^\.\.\//, "")
    .toLowerCase();
}

/** Map stored/legacy brief paths (resources/ vs cli/resources/) to an existing file.
 * Prefer projects/<slug>/ after migrate; follow redirect stubs.
 * Never remap projects/A/… to projects/B/… — empty new projects must stay bound. */
function resolveBriefRel(briefRel) {
  const root = repoRoot();
  const raw = String(briefRel || "")
    .replace(/\\/g, "/")
    .replace(/^\.\.\//, "")
    .replace(/^\.\//, "");
  if (!raw) return "";

  // Isolated project path: keep the slug even if brief.json is not written yet.
  const projMatch = raw.match(/^(projects\/([^/]+))\//i);
  if (projMatch) {
    const projectRootRel = projMatch[1].replace(/\\/g, "/");
    const preferred = `${projectRootRel}/brief.json`;
    const projectAbs = path.join(root, projectRootRel);
    if (existsSync(projectAbs) && statSync(projectAbs).isDirectory()) {
      const preferredAbs = path.join(root, preferred);
      if (existsSync(preferredAbs)) {
        try {
          const data = JSON.parse(readFileSync(preferredAbs, "utf-8"));
          const redirect = String(data?.brief_meta?.redirect_to || "").replace(/\\/g, "/");
          // Only follow redirects that stay inside the same project
          if (
            redirect &&
            redirect.startsWith(`${projectRootRel}/`) &&
            existsSync(path.join(root, redirect))
          ) {
            return redirect;
          }
        } catch {
          /* use preferred */
        }
        return preferred;
      }
      return preferred;
    }
  }

  const base = path.basename(raw);
  const candidates = [];
  const push = (c) => {
    const n = String(c || "").replace(/\\/g, "/");
    if (n && !candidates.includes(n)) candidates.push(n);
  };

  // 1) Prefer isolated projects/ first (by slug / stem) — skip bare "brief"
  const stem = base.replace(/\.json$/i, "").replace(/-brief$/i, "");
  if (stem && stem.toLowerCase() !== "brief") {
    push(`projects/${stem}/brief.json`);
    push(`projects/${stem}/${stem}-brief.json`);
  }
  // Known game aliases
  if (/mrqbshf2|black.?whistle/i.test(raw + base)) {
    push("projects/black-whistle/brief.json");
  }

  push(raw);
  if (raw.startsWith("resources/") && !raw.startsWith("cli/")) {
    push(`cli/${raw}`);
  }
  if (raw.startsWith("cli/resources/")) {
    push(raw.slice("cli/".length));
  }
  if (base.toLowerCase() !== "brief.json") {
    push(`resources/${base}`);
    push(`cli/resources/${base}`);
  }

  // Scan projects/*/brief.json for migrated_from / legacy_names
  const projectsDir = path.join(root, "projects");
  if (existsSync(projectsDir) && stem && stem.toLowerCase() !== "brief") {
    try {
      for (const name of readdirSync(projectsDir)) {
        const briefAbs = path.join(projectsDir, name, "brief.json");
        if (!existsSync(briefAbs)) continue;
        try {
          const data = JSON.parse(readFileSync(briefAbs, "utf-8"));
          const meta = data?.brief_meta || {};
          const migrated = String(meta.migrated_from || "").replace(/\\/g, "/");
          const names = Array.isArray(meta.legacy_names) ? meta.legacy_names : [];
          if (
            migrated === raw ||
            migrated.endsWith(`/${base}`) ||
            names.includes(base) ||
            names.includes(stem) ||
            names.includes(raw)
          ) {
            push(`projects/${name}/brief.json`);
          }
        } catch {
          /* ignore */
        }
      }
    } catch {
      /* ignore */
    }
  }

  for (const c of candidates) {
    const abs = path.join(root, c);
    if (!existsSync(abs)) continue;
    try {
      const data = JSON.parse(readFileSync(abs, "utf-8"));
      const redirect = String(data?.brief_meta?.redirect_to || "").replace(/\\/g, "/");
      if (redirect && existsSync(path.join(root, redirect))) {
        return redirect;
      }
      // Skip empty redirect stubs without target
      if (data?.brief_meta?.migrated && redirect) continue;
    } catch {
      /* use path as-is */
    }
    return c;
  }
  return raw;
}

function briefCliArg(briefRel) {
  if (isExternalVirtualRel(briefRel)) {
    return cliArgForRel(briefRel);
  }
  return cliArgForRel(resolveBriefRel(briefRel));
}

function manifestCliArg(manifestRel) {
  return cliArgForRel(manifestRel);
}

/** Resolve assets-manifest.json from direct rel or pipeline manifest output_dir. */
function resolveAssetsManifestRel(assetsManifestRel, pipelineManifestRel) {
  const direct = normalizeRepoRel(assetsManifestRel);
  if (direct) {
    const abs = absForRel(direct);
    if (existsSync(abs)) return direct;
  }
  const pipeRel = normalizeRepoRel(pipelineManifestRel);
  if (pipeRel) {
    const meta = manifestMeta(pipeRel);
    const outputDir = String(meta?.output_dir || "").replace(/\\/g, "/");
    if (outputDir) {
      const candidate = path.join(outputDir, "assets-manifest.json").replace(/\\/g, "/");
      if (existsSync(absForRel(candidate))) return candidate;
    }
  }
  return direct || null;
}

function looksLikeImagePath(ref) {
  const s = String(ref || "").trim().replace(/\\/g, "/");
  if (!s || s.length > 400 || s.includes("://")) return false;
  return /\.(png|jpe?g|webp|gif)$/i.test(s);
}

/** Find newest pipeline manifest for the same project (exact brief first, then same root). */
function findManifestForBrief(briefRel) {
  const key = normalizeBriefKey(briefRel);
  if (!key) return null;
  const projectRoot = (() => {
    const m = key.match(/^(projects\/[^/]+)\//i);
    if (m) return m[1].toLowerCase();
    const em = key.match(/^(external:[^/]+)\//i);
    return em ? em[1].toLowerCase() : null;
  })();
  let exact = null;
  let sameRootBest = null;
  for (const item of listManifests()) {
    const meta = manifestMeta(item.path);
    if (!meta?.brief) continue;
    const mb = normalizeBriefKey(meta.brief);
    if (mb === key) {
      if (!exact || (item.mtime || 0) > (exact.mtime || 0)) {
        exact = { path: item.path, label: item.label, mtime: item.mtime, meta };
      }
      continue;
    }
    if (!projectRoot) continue;
    const briefSameRoot =
      mb === projectRoot || mb.startsWith(projectRoot + "/");
    const manifestUnder = normalizeBriefKey(item.path).startsWith(projectRoot + "/");
    if (briefSameRoot || manifestUnder) {
      if (!sameRootBest || (item.mtime || 0) > (sameRootBest.mtime || 0)) {
        sameRootBest = { path: item.path, label: item.label, mtime: item.mtime, meta };
      }
    }
  }
  return exact || sameRootBest;
}

function loadManifest(relPath) {
  const full = absForRel(relPath);
  const data = JSON.parse(readFileSync(full, "utf-8"));
  // Follow migrate pointer
  if (data?.migrated_to && !data?.tasks) {
    const next = String(data.migrated_to).replace(/\\/g, "/");
    return JSON.parse(readFileSync(absForRel(next), "utf-8"));
  }
  return data;
}

function configPath() {
  return path.join(os.homedir(), ".gamefactory", "config.json");
}

function loadUserConfig() {
  const cfgPath = configPath();
  if (!existsSync(cfgPath)) {
    return { path: cfgPath, exists: false, data: {} };
  }
  try {
    const data = JSON.parse(readFileSync(cfgPath, "utf-8"));
    return { path: cfgPath, exists: true, data: data && typeof data === "object" ? data : {} };
  } catch {
    return { path: cfgPath, exists: true, data: {} };
  }
}

function deepMerge(target, source) {
  const out = { ...target };
  for (const key of Object.keys(source || {})) {
    const value = source[key];
    if (value === null) {
      delete out[key];
      continue;
    }
    if (key === "provider_accounts" || key === "video_accounts") {
      out[key] = value && typeof value === "object" ? { ...value } : value;
      continue;
    }
    if (value && typeof value === "object" && !Array.isArray(value)) {
      out[key] = deepMerge(out[key] && typeof out[key] === "object" ? out[key] : {}, value);
    } else if (value !== undefined && value !== "") {
      out[key] = value;
    }
  }
  return out;
}

function saveUserConfig(patch) {
  const cfgPath = configPath();
  mkdirSync(path.dirname(cfgPath), { recursive: true });
  const current = loadUserConfig().data;
  const merged = deepMerge(current, patch || {});
  writeFileSync(cfgPath, `${JSON.stringify(merged, null, 2)}\n`, "utf-8");
  return { ok: true, path: cfgPath };
}

const CURSOR_PERMISSION_MODES = new Set(["force", "auto_review", "plan", "ask"]);
const CODEX_SANDBOXES = new Set(["read-only", "workspace-write", "danger-full-access"]);
const DEFAULT_CODEX_SANDBOX = "workspace-write";
const VALID_AGENT_EXECUTORS = new Set(["hermes", "codex", "cursor", "pi"]);
const ROLE_TO_AGENT_KEY = {
  product_host: "orchestrator",
  programmer: "godot-developer",
  it: "it",
  advisor: "advisor",
};

/**
 * @param {Record<string, unknown>} config
 * @param {string | undefined | null} instanceId
 * @returns {Record<string, unknown>}
 */
function agentInstanceRecord(config, instanceId) {
  const instances = config?.agents?.instances;
  if (!instanceId || typeof instances !== "object" || instances == null) return {};
  const rec = instances[String(instanceId)];
  return rec && typeof rec === "object" ? rec : {};
}

/**
 * @param {Record<string, unknown>} config
 * @param {string | undefined | null} instanceId
 * @returns {string}
 */
function resolveCursorPermissionMode(config, instanceId) {
  const inst = agentInstanceRecord(config, instanceId);
  const fromInst = String(inst.permission_mode || "").trim();
  if (CURSOR_PERMISSION_MODES.has(fromInst)) return fromInst;
  const cursorPreset = config?.agents?.executors?.cursor;
  const fromPreset =
    cursorPreset && typeof cursorPreset === "object"
      ? String(cursorPreset.permission_mode || "").trim()
      : "";
  if (CURSOR_PERMISSION_MODES.has(fromPreset)) return fromPreset;
  return "force";
}

/**
 * @param {Record<string, unknown>} config
 * @param {string | undefined | null} instanceId
 * @returns {boolean}
 */
function resolveHermesYolo(config, instanceId) {
  const inst = agentInstanceRecord(config, instanceId);
  if ("yolo" in inst) {
    return Boolean(inst.yolo);
  }
  const hermesPreset = config?.agents?.executors?.hermes;
  if (!hermesPreset || typeof hermesPreset !== "object" || !("yolo" in hermesPreset)) {
    return true;
  }
  return Boolean(hermesPreset.yolo);
}

/**
 * @param {Record<string, unknown>} config
 * @param {string | undefined | null} instanceId
 * @returns {string}
 */
function resolveCodexSandbox(config, instanceId) {
  const inst = agentInstanceRecord(config, instanceId);
  const fromInst = String(inst.sandbox || "").trim();
  if (CODEX_SANDBOXES.has(fromInst)) return fromInst;
  const codexPreset = config?.agents?.executors?.codex;
  const fromPreset =
    codexPreset && typeof codexPreset === "object"
      ? String(codexPreset.sandbox || "").trim()
      : "";
  if (CODEX_SANDBOXES.has(fromPreset)) return fromPreset;
  return DEFAULT_CODEX_SANDBOX;
}

/** Foundry provider id → Hermes ACP authenticate methodId / CLI --provider */
const HERMES_AUTH_METHOD_BY_FOUNDRY = Object.freeze({
  openrouter: "openrouter",
  openai: "openai-api",
  deepseek: "custom",
  kimi: "custom",
  glm: "custom",
  gemini: "custom",
  custom: "custom",
});

/**
 * @param {Record<string, unknown>} config
 * @param {string | undefined | null} instanceId
 * @returns {string}
 */
function resolveHermesAuthMethodId(config, instanceId) {
  const inst = agentInstanceRecord(config, instanceId);
  const fromInst = String(inst.provider || "").trim().toLowerCase();
  const agents = config?.agents && typeof config.agents === "object" ? config.agents : {};
  const fromHermesPreset =
    agents.hermes_provider != null
      ? String(agents.hermes_provider).trim().toLowerCase()
      : "";
  const hermesExec =
    agents.executors && typeof agents.executors === "object" ? agents.executors.hermes : null;
  const fromExec =
    hermesExec && typeof hermesExec === "object" && hermesExec.provider != null
      ? String(hermesExec.provider).trim().toLowerCase()
      : "";
  const host = config?.host && typeof config.host === "object" ? config.host : {};
  const fromHost = String(host.provider || "").trim().toLowerCase();
  const foundry = fromInst || fromHermesPreset || fromExec || fromHost || "openrouter";
  return HERMES_AUTH_METHOD_BY_FOUNDRY[foundry] || "custom";
}

/**
 * @param {Record<string, unknown>} config
 * @param {string} roleKind
 * @param {Record<string, unknown>} opts
 * @returns {string}
 */
function resolveExecutorForAgentTurn(config, roleKind, opts) {
  const override = String(opts.executor || "").trim().toLowerCase();
  const inst = agentInstanceRecord(config, opts.instanceId);
  const fromInst = String(inst.executor || "").trim().toLowerCase();
  if (roleKind === "advisor") {
    return "pi";
  }
  if (roleKind === "it") {
    const itCfg = config?.agents?.it;
    const fromRole =
      itCfg && typeof itCfg === "object"
        ? String(itCfg.executor || "pi").trim().toLowerCase()
        : "pi";
    return resolveItExecutor({
      override,
      instanceExecutor: fromInst,
      roleExecutor: fromRole,
    });
  }

  if (VALID_AGENT_EXECUTORS.has(override)) {
    return override;
  }

  if (VALID_AGENT_EXECUTORS.has(fromInst)) {
    return fromInst;
  }

  const agentKey = ROLE_TO_AGENT_KEY[roleKind] || "orchestrator";
  const roleBlock = config?.agents?.[agentKey];
  let executor =
    roleBlock && typeof roleBlock === "object"
      ? String(roleBlock.executor || "hermes").trim().toLowerCase()
      : "hermes";
  if (executor === "pipeline") executor = "hermes";
  return VALID_AGENT_EXECUTORS.has(executor) ? executor : "hermes";
}

function relToRepo(absPath) {
  const root = repoRoot();
  const rel = path.relative(root, absPath);
  return rel.split(path.sep).join("/");
}

/** Resolve image/video path for preview/open. Accepts repo-relative, external:, or absolute. */
function resolveMediaAbs(relOrAbs) {
  const root = path.resolve(repoRoot());
  const raw = String(relOrAbs || "").trim();
  if (!raw) return null;

  const externalRoots = () =>
    loadExternalRegistry().projects
      .map((e) => (e?.root_abs ? path.resolve(String(e.root_abs)) : ""))
      .filter(Boolean);

  const allowedAbs = (candidate) => {
    if (!existsSync(candidate) || !statSync(candidate).isFile()) return false;
    if (pathUnderRoot(candidate, root)) return true;
    return externalRoots().some((er) => pathUnderRoot(candidate, er));
  };

  const extResolved = resolveExternalRel(raw);
  if (extResolved?.full && allowedAbs(extResolved.full)) {
    return extResolved.full;
  }

  const candidates = [];
  const push = (p) => {
    if (!p) return;
    const n = path.normalize(p);
    if (!candidates.includes(n)) candidates.push(n);
  };

  if (path.isAbsolute(raw)) {
    push(raw);
  } else {
    const rel = raw.replace(/\\/g, "/");
    try {
      push(absForRel(rel));
    } catch {
      /* fall through */
    }
    push(path.join(root, rel));
    const nestedProjects = rel.lastIndexOf("projects/");
    if (nestedProjects > 0 && rel.startsWith("projects/")) {
      push(path.join(root, rel.slice(nestedProjects)));
    }
    if (rel.startsWith("output/") || rel.startsWith("plans/") || rel.startsWith("game/")) {
      const projectsDir = path.join(root, "projects");
      if (existsSync(projectsDir)) {
        try {
          for (const name of readdirSync(projectsDir)) {
            push(path.join(projectsDir, name, rel));
          }
        } catch {
          /* ignore */
        }
      }
      for (const er of externalRoots()) {
        push(path.join(er, rel));
      }
    }
  }

  for (const candidate of candidates) {
    if (allowedAbs(candidate)) return candidate;
  }
  return null;
}

function mediaKind(ext) {
  const lower = ext.toLowerCase();
  if (IMAGE_EXTS.has(lower)) return "image";
  if (VIDEO_EXTS.has(lower)) return "video";
  return null;
}

function toMediaUrl(absPath) {
  // Bust Chromium cache when the same path is overwritten (e.g. regenerating
  // visual-target candidate_a.png) — otherwise thumbnails show stale bytes
  // while shell.openPath shows the new file on disk.
  let version = 0;
  try {
    version = Math.trunc(statSync(absPath).mtimeMs);
  } catch {
    version = Date.now();
  }
  return `gamefactory-media://local/?p=${encodeURIComponent(absPath)}&v=${version}`;
}

function findVideoPosterAbs(videoAbs) {
  const dir = path.dirname(videoAbs);
  const base = path.basename(videoAbs, path.extname(videoAbs));
  const candidates = [
    path.join(dir, `${base}_poster.png`),
    path.join(dir, `${base}_frames`, "frame_0001.png"),
    path.join(dir, `${base}_frames`, "frame_0000.png"),
  ];
  const framesDir = path.join(dir, `${base}_frames`);
  if (existsSync(framesDir)) {
    const pngs = readdirSync(framesDir)
      .filter((f) => f.toLowerCase().endsWith(".png"))
      .sort();
    if (pngs[0]) candidates.unshift(path.join(framesDir, pngs[0]));
  }
  const matteDir = path.join(dir, `${base.replace(/_walk$/, "")}_walk_frames`);
  if (existsSync(matteDir)) {
    const pngs = readdirSync(matteDir)
      .filter((f) => f.toLowerCase().endsWith(".png"))
      .sort();
    if (pngs[0]) candidates.push(path.join(matteDir, pngs[0]));
  }
  for (const c of candidates) {
    if (existsSync(c)) return c;
  }
  return null;
}

function buildMediaPreview(absPath, posterAbs = null) {
  const kind = mediaKind(path.extname(absPath));
  if (!kind) return null;
  const name = path.basename(absPath);
  const rel = relToRepo(absPath);
  if (kind === "image") {
    return { kind, name, path: rel, previewUrl: toMediaUrl(absPath) };
  }
  const poster = posterAbs || findVideoPosterAbs(absPath);
  return {
    kind: "video",
    name,
    path: rel,
    posterUrl: poster ? toMediaUrl(poster) : undefined,
  };
}

function walkMediaFiles(dirAbs, bucket, depth = 0) {
  if (depth > 4 || !existsSync(dirAbs)) return;
  let entries;
  try {
    entries = readdirSync(dirAbs, { withFileTypes: true });
  } catch {
    return;
  }
  for (const entry of entries) {
    const full = path.join(dirAbs, entry.name);
    if (entry.isDirectory()) {
      walkMediaFiles(full, bucket, depth + 1);
      continue;
    }
    const kind = mediaKind(path.extname(entry.name));
    if (!kind) continue;
    let mtime = 0;
    try {
      mtime = statSync(full).mtimeMs;
    } catch {
      /* ignore */
    }
    bucket.push({ abs: full, kind, mtime, name: entry.name });
  }
}

let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 780,
    minWidth: 900,
    minHeight: 600,
    title: "Game AI Foundry",
    backgroundColor: "#0f1419",
    show: false,
    webPreferences: {
      preload: preloadPath(),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.webContents.on("did-fail-load", (_e, code, desc, url) => {
    console.error("did-fail-load", code, desc, url);
  });

  mainWindow.webContents.on("preload-error", (_e, preloadPath, error) => {
    console.error("preload-error", preloadPath, error);
  });

  if (isDev) {
    const devUrl = "http://127.0.0.1:5173";
    mainWindow.loadURL(devUrl).catch((err) => {
      console.error("loadURL failed:", err);
    });
  } else {
    mainWindow.loadFile(rendererIndexPath());
  }

  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
  });
}

app.whenReady().then(() => {
  toolPermissionBridge = createToolPermissionBridge({
    getSender: () => (mainWindow && !mainWindow.isDestroyed() ? mainWindow.webContents : null),
  });

  cursorAcpSessionManager = createCursorAcpSessionManager({
    getSpawnEnv: agentExecutorChildEnv,
    getAgentPath: () => {
      const home = os.homedir();
      const local = process.env.LOCALAPPDATA || path.join(home, "AppData", "Local");
      const names = process.platform === "win32"
        ? ["agent.CMD", "agent.cmd", "cursor-agent.CMD", "cursor-agent.cmd", "agent.exe", "agent"]
        : ["agent", "cursor-agent"];
      const dirs = [
        path.join(local, "cursor-agent"),
        path.join(home, ".local", "bin"),
        path.join(home, ".local", "share", "cursor-agent", "versions"),
      ];
      // Prefer newest version dir if present.
      try {
        const versionsRoot = path.join(home, ".local", "share", "cursor-agent", "versions");
        if (existsSync(versionsRoot)) {
          const kids = readdirSync(versionsRoot)
            .map((name) => path.join(versionsRoot, name))
            .filter((p) =>
              names.some((n) => existsSync(path.join(p, n))),
            );
          kids.sort();
          dirs.unshift(...kids.slice(-3).reverse());
        }
      } catch {
        /* ignore */
      }
      for (const dir of dirs) {
        for (const name of names) {
          const cand = path.join(dir, name);
          if (existsSync(cand)) return cand;
        }
      }
      return "agent";
    },
    onPermission: (req) => {
      const permissionId = String(req.permissionId || "");
      routeExternalToolPermission({
        permissionId,
        sessionId: String(req.sessionId || ""),
        turnId: String(req.turnId || ""),
        instanceId: String(req.instanceId || ""),
        argvSummary: String(req.summary || "").slice(0, 500),
        source: "cursor_acp",
        decide: (id, decision) => {
          cursorAcpSessionManager?.decidePermission(id, decision);
        },
      });
    },
    onLog: (msg, ctx) => {
      console.log(`[cursor-acp] ${msg}`, ctx ?? "");
    },
  });

  hermesAcpSessionManager = createHermesAcpSessionManager({
    getSpawnEnv: agentExecutorChildEnv,
    getHermesPath: () => {
      const home = os.homedir();
      const local = process.env.LOCALAPPDATA || path.join(home, "AppData", "Local");
      const cands = [
        path.join(local, "hermes", "hermes-agent", "venv", "Scripts", "hermes.EXE"),
        path.join(local, "hermes", "hermes-agent", "venv", "Scripts", "hermes.exe"),
        path.join(home, ".hermes", "hermes-agent", "venv", "Scripts", "hermes.EXE"),
        path.join(home, ".hermes", "hermes-agent", "venv", "bin", "hermes"),
      ];
      for (const cand of cands) {
        if (existsSync(cand)) return cand;
      }
      return "hermes";
    },
    getAuthMethodId: (instanceId) => {
      const config = loadUserConfig().data || {};
      return resolveHermesAuthMethodId(config, instanceId);
    },
    onPermission: (req) => {
      const permissionId = String(req.permissionId || "");
      routeExternalToolPermission({
        permissionId,
        sessionId: String(req.sessionId || ""),
        turnId: String(req.turnId || ""),
        instanceId: String(req.instanceId || ""),
        argvSummary: String(req.summary || "").slice(0, 500),
        source: "hermes_acp",
        decide: (id, decision) => {
          hermesAcpSessionManager?.decidePermission(id, decision);
        },
      });
    },
    onLog: (msg, ctx) => {
      console.log(`[hermes-acp] ${msg}`, ctx ?? "");
    },
  });

  codexAppServerSessionManager = createCodexAppServerSessionManager({
    getSpawnEnv: agentExecutorChildEnv,
    resolveCodexBin: () => {
      const home = os.homedir();
      const win = process.platform === "win32";
      const names = win ? ["codex.exe", "codex.cmd", "codex"] : ["codex"];
      const dirs = [
        path.join(home, ".gamefactory", "toolchain", "bin"),
        path.join(process.env.LOCALAPPDATA || path.join(home, "AppData", "Local"), "Programs", "OpenAI", "Codex", "bin"),
        path.join(home, ".local", "bin"),
        path.join(home, ".codex", "packages", "standalone", "current"),
        path.join(process.env.APPDATA || path.join(home, "AppData", "Roaming"), "npm"),
      ];
      for (const dir of dirs) {
        for (const name of names) {
          const cand = path.join(dir, name);
          if (existsSync(cand)) return cand;
        }
      }
      return "codex";
    },
    onPermission: (req) => {
      const permissionId = String(req.permissionId || "");
      const summary = String(req.summary || "").slice(0, 500);
      const kind = req.kind ? String(req.kind) : "";
      const argvSummary = kind ? `[${kind}] ${summary}`.slice(0, 500) : summary;
      routeExternalToolPermission({
        permissionId,
        sessionId: String(req.sessionId || ""),
        turnId: String(req.turnId || ""),
        instanceId: String(req.instanceId || ""),
        argvSummary,
        source: "codex_app_server",
        decide: (id, decision) => {
          codexAppServerSessionManager?.decidePermission({ permissionId: id, decision });
        },
      });
    },
    onLog: (msg, ctx) => {
      console.log(`[codex-app-server] ${msg}`, ctx ?? "");
    },
  });

  protocol.handle("gamefactory-media", (request) => {
    try {
      const url = new URL(request.url);
      // searchParams.get already percent-decodes; do not decodeURIComponent again.
      const abs = url.searchParams.get("p") || "";
      const resolved = resolveMediaAbs(abs);
      if (!resolved) {
        return new Response("Not found", { status: 404 });
      }
      return net.fetch(pathToFileURL(resolved).href).then((res) => {
        const headers = new Headers(res.headers);
        headers.set("Cache-Control", "no-store, max-age=0");
        return new Response(res.body, { status: res.status, headers });
      });
    } catch {
      return new Response("Error", { status: 500 });
    }
  });

  ipcMain.handle("get-paths", () => ({
    repoRoot: repoRoot(),
    cliDir: cliDir(repoRoot()),
    python: resolvePython(repoRoot()),
    isDev,
    isPackaged: isPackagedApp(),
    appVersion: app.getVersion(),
  }));

  registerAutoUpdateIpc();

  ipcMain.handle("doctor", async () => {
    const result = await runCli(["doctor", "--json"]);
    const data = parseJsonFromOutput(result.stdout);
    return { ...result, data };
  });

  ipcMain.handle("toolchain-check", async () => {
    const result = await runCli(["setup", "check", "--json"]);
    const data = parseJsonFromOutput(result.stdout);
    return { ...result, data };
  });

  ipcMain.handle("toolchain-install", async (event, componentId) => {
    const sender = event.sender;
    const result = await runCli(["setup", "install", String(componentId), "--json"], {
      onLine: (line) => {
        sender.send("toolchain-log", { line });
      },
    });
    const data = parseJsonFromOutput(result.stdout);
    return { ...result, data };
  });

  ipcMain.handle("executor-status", async () => {
    const result = await runCli(["setup", "executor", "status", "--json"]);
    const data = parseJsonFromOutput(result.stdout);
    return { ...result, data };
  });

  ipcMain.handle("executor-models", async (_event, executorId) => {
    const result = await runCli([
      "setup",
      "executor",
      "models",
      "--executor",
      String(executorId || ""),
      "--json",
    ]);
    const data = parseJsonFromOutput(result.stdout);
    return { ...result, data };
  });

  ipcMain.handle("provider-models", async (_event, providerId) => {
    const result = await runCli([
      "setup",
      "provider",
      "models",
      "--provider",
      String(providerId || ""),
      "--json",
    ]);
    const data = parseJsonFromOutput(result.stdout);
    return { ...result, data };
  });

  ipcMain.handle("executor-step", async (event, executorId, stepId, opts = {}) => {
    const sender = event.sender;
    const args = ["setup", "executor", "step", String(executorId), String(stepId)];
    if (opts?.provider) {
      args.push("--provider", String(opts.provider));
    }
    if (opts?.instanceId) {
      args.push("--instance-id", String(opts.instanceId));
    }
    args.push("--json");
    const result = await runCli(args, {
      onLine: (line) => {
        sender.send("toolchain-log", { line });
      },
    });
    const data = parseJsonFromOutput(result.stdout);
    return { ...result, data };
  });

  ipcMain.handle("open-external", async (_e, url) => {
    if (!url || typeof url !== "string") {
      return { ok: false, error: "invalid url" };
    }
    let parsed;
    try {
      parsed = new URL(url);
    } catch {
      return { ok: false, error: "invalid url" };
    }
    const protocol = parsed.protocol.toLowerCase();
    const host = (parsed.hostname || "").toLowerCase();
    const httpsOk = protocol === "https:";
    const localHttpOk =
      protocol === "http:" && (host === "localhost" || host === "127.0.0.1");
    if (!httpsOk && !localHttpOk) {
      return {
        ok: false,
        error: "only https: or http://localhost|127.0.0.1 allowed",
      };
    }
    await shell.openExternal(parsed.toString());
    return { ok: true };
  });

  ipcMain.handle("list-briefs", () => listBriefs());
  ipcMain.handle("list-manifests", () => listManifests());
  ipcMain.handle("manifest-meta", (_e, manifestRel) => manifestMeta(manifestRel));
  ipcMain.handle("find-manifest-for-brief", (_e, briefRel) => findManifestForBrief(briefRel));
  ipcMain.handle("read-repo-text", (_e, relPath) => readRepoText(relPath));
  ipcMain.handle("patch-brief-project", (_e, relPath, projectPatch) =>
    patchBriefProject(relPath, projectPatch),
  );
  ipcMain.handle("list-project-docs", (_e, briefRel) => {
    const docs = listProjectDocs(briefRel);
    if (!app.isPackaged) {
      console.info("[docs] list-project-docs", {
        briefRel: briefRel || null,
        count: docs.length,
        paths: docs.map((d) => d.path),
        repoRoot: repoRoot(),
      });
    }
    return docs;
  });
  ipcMain.handle("ensure-project", (_e, slug) => ensureProject(slug));

  ipcMain.handle("external-project-open", async () => {
    const { dialog } = await import("electron");
    const result = await dialog.showOpenDialog(mainWindow, {
      title: "打开外置工程",
      properties: ["openDirectory"],
    });
    if (result.canceled || !result.filePaths[0]) {
      return { ok: false, canceled: true };
    }
    const rootPath = result.filePaths[0];
    const cliResult = await runCli([
      "project",
      "external",
      "add",
      "--root",
      rootPath,
      "--json",
    ]);
    const data = parseJsonFromOutput(cliResult.stdout);
    if (cliResult.exitCode !== 0 || !data?.entry?.id) {
      return {
        ok: false,
        error: cliResult.stderr.trim() || "external add failed",
        exitCode: cliResult.exitCode,
      };
    }
    const entry = data.entry;
    const briefRel = `external:${entry.id}/brief.json`;
    return {
      ok: true,
      entry,
      briefRel,
      detect: data.layout || null,
    };
  });

  ipcMain.handle("external-projects-list", async () => {
    const result = await runCli(["project", "external", "list", "--json"]);
    const data = parseJsonFromOutput(result.stdout);
    return {
      ok: result.exitCode === 0,
      exitCode: result.exitCode,
      projects: Array.isArray(data?.projects) ? data.projects : [],
      count: typeof data?.count === "number" ? data.count : 0,
    };
  });

  ipcMain.handle("external-project-remove", async (_e, extId) => {
    const id = String(extId || "").trim();
    if (!id) {
      return { ok: false, error: "missing id" };
    }
    const result = await runCli(["project", "external", "remove", "--id", id]);
    return {
      ok: result.exitCode === 0,
      exitCode: result.exitCode,
      stderr: result.stderr,
    };
  });

  ipcMain.handle("pipeline-plan", async (_e, opts) => {
    const {
      briefRel,
      manifestRel,
      outputDirRel,
      godotProjectRel,
      plansDirRel,
    } = opts;
    const briefResolved = isExternalVirtualRel(briefRel)
      ? normalizeRepoRel(briefRel)
      : resolveBriefRel(briefRel);
    const args = [
      "pipeline",
      "plan",
      "--brief",
      cliArgForRel(briefResolved),
      "-o",
      cliArgForRel(manifestRel),
      "--output-dir",
      cliArgForRel(outputDirRel),
      "--godot-project",
      cliArgForRel(godotProjectRel),
    ];
    if (plansDirRel) {
      args.push("--plans-dir", cliArgForRel(plansDirRel));
    }
    // Ensure parent dirs exist for isolated projects
    for (const rel of [manifestRel, outputDirRel, godotProjectRel, plansDirRel]) {
      if (!rel) continue;
      const abs = absForRel(rel);
      const dir = path.extname(abs) ? path.dirname(abs) : abs;
      mkdirSync(dir, { recursive: true });
    }
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("pipeline-status", async (_e, manifestRel) => {
    const result = await runCli([
      "pipeline",
      "status",
      "--manifest",
      cliArgForRel(manifestRel),
      "--json",
    ]);
    const status = parseJsonFromOutput(result.stdout);
    let tasks = [];
    try {
      const manifest = loadManifest(manifestRel);
      tasks = manifest.tasks || [];
    } catch {
      /* ignore */
    }
    return { ...result, status, tasks };
  });

  ipcMain.handle("pipeline-run", async (event, manifestRel, jobs, runPrompts) => {
    const sender = event.sender;
    const args = [
      "pipeline",
      "run",
      "--manifest",
      cliArgForRel(manifestRel),
      "--jobs",
      String(jobs || 4),
    ];
    if (runPrompts) args.push("--run-prompts");
    const result = await runCli(args, {
      onLine: (line, stream) => {
        sender.send("pipeline-log", { line, stream });
      },
    });
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("pipeline-diagnose", async (_e, manifestRel) => {
    const result = await runCli([
      "pipeline",
      "diagnose",
      "--manifest",
      cliArgForRel(manifestRel),
    ]);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("pipeline-heal", async (_e, manifestRel, apply = true) => {
    const args = [
      "pipeline",
      "heal",
      "--manifest",
      cliArgForRel(manifestRel),
      apply ? "--apply" : "--dry-run",
    ];
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("assets-review-list", async (_e, assetsManifestRel, pipelineManifestRel) => {
    const rel = resolveAssetsManifestRel(assetsManifestRel, pipelineManifestRel);
    if (!rel) {
      return {
        exitCode: 1,
        stdout: "",
        stderr: "assets-manifest path not resolved",
        data: { rows: [] },
      };
    }
    const result = await runCli([
      "assets",
      "review",
      "list",
      "--manifest",
      manifestCliArg(rel),
      "--json",
    ]);
    const parsed = parseJsonFromOutput(result.stdout);
    const rows = Array.isArray(parsed) ? parsed : [];
    return { ...result, data: { rows } };
  });

  ipcMain.handle("assets-review-accept", async (_e, assetsManifestRel, assetName, itemSlug) => {
    const rel = resolveAssetsManifestRel(assetsManifestRel);
    if (!rel) {
      return { exitCode: 1, stdout: "", stderr: "assets-manifest path not resolved" };
    }
    const args = [
      "assets",
      "review",
      "accept",
      "--manifest",
      manifestCliArg(rel),
      "--asset",
      String(assetName || "").trim(),
      "--json",
    ];
    const slug = String(itemSlug || "").trim();
    if (slug) args.push("--item", slug);
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle(
    "assets-review-replace",
    async (_e, assetsManifestRel, assetName, itemSlug, absFilePath) => {
      const rel = resolveAssetsManifestRel(assetsManifestRel);
      if (!rel) {
        return { exitCode: 1, stdout: "", stderr: "assets-manifest path not resolved" };
      }
      const args = [
        "assets",
        "review",
        "replace",
        "--manifest",
        manifestCliArg(rel),
        "--asset",
        String(assetName || "").trim(),
        "--file",
        String(absFilePath || "").trim(),
        "--json",
      ];
      const slug = String(itemSlug || "").trim();
      if (slug) args.push("--item", slug);
      const result = await runCli(args);
      return { ...result, data: parseJsonFromOutput(result.stdout) };
    },
  );

  ipcMain.handle(
    "assets-review-regenerate",
    async (event, pipelineManifestRel, assetName, itemSlug, jobs) => {
      const sender = event.sender;
      const pipeRel = normalizeRepoRel(pipelineManifestRel);
      if (!pipeRel) {
        return { exitCode: 1, stdout: "", stderr: "pipeline manifest path required" };
      }
      const jobCount = Math.max(1, Number(jobs) || 4);
      const onLine = (line, stream) => {
        sender.send("pipeline-log", { line, stream });
      };
      const planArgs = [
        "assets",
        "review",
        "regenerate-plan",
        "--pipeline-manifest",
        manifestCliArg(pipeRel),
        "--asset",
        String(assetName || "").trim(),
        "--jobs",
        String(jobCount),
        "--json",
      ];
      const slug = String(itemSlug || "").trim();
      if (slug) planArgs.push("--item", slug);
      const planResult = await runCli(planArgs);
      const plan = parseJsonFromOutput(planResult.stdout);
      if (planResult.exitCode !== 0) {
        return { ...planResult, data: { plan } };
      }

      const resetTaskId = String(plan?.reset_task_id || "").trim();
      if (!resetTaskId) {
        return {
          exitCode: 1,
          stdout: "",
          stderr:
            "no reset_task_id for asset; cannot regenerate without a matching pipeline task",
          data: { plan },
        };
      }

      const resetResult = await runCli(
        [
          "pipeline",
          "reset",
          "--manifest",
          manifestCliArg(pipeRel),
          "--task-id",
          resetTaskId,
          "--cascade",
        ],
        { onLine },
      );
      if (resetResult.exitCode !== 0) {
        return { ...resetResult, data: { plan, reset: resetResult } };
      }

      const runResult = await runCli(
        [
          "pipeline",
          "run",
          "--manifest",
          manifestCliArg(pipeRel),
          "--jobs",
          String(jobCount),
        ],
        { onLine },
      );
      if (runResult.exitCode !== 0) {
        return {
          ...runResult,
          data: {
            plan,
            reset: resetResult,
            run: parseJsonFromOutput(runResult.stdout),
          },
        };
      }

      // Soft review only after full reset+run success
      const assetsRel = resolveAssetsManifestRel(null, pipeRel);
      let markResult = null;
      if (assetsRel) {
        const markArgs = [
          "assets",
          "review",
          "mark-replaced",
          "--manifest",
          manifestCliArg(assetsRel),
          "--asset",
          String(assetName || "").trim(),
          "--source",
          "regenerate",
          "--json",
        ];
        if (slug) markArgs.push("--item", slug);
        markResult = await runCli(markArgs);
      }

      return {
        ...runResult,
        exitCode: markResult && markResult.exitCode !== 0 ? markResult.exitCode : runResult.exitCode,
        stderr:
          markResult && markResult.exitCode !== 0
            ? markResult.stderr || runResult.stderr
            : runResult.stderr,
        data: {
          plan,
          reset: resetResult,
          run: parseJsonFromOutput(runResult.stdout),
          mark: markResult
            ? { ...markResult, data: parseJsonFromOutput(markResult.stdout) }
            : null,
          assets_manifest: assetsRel,
        },
      };
    },
  );

  ipcMain.handle("resolve-brief-rel", (_e, briefRel) => {
    const external = resolveExternalRel(briefRel);
    if (external) {
      return {
        input: String(briefRel || "").replace(/\\/g, "/"),
        path: external.rel,
        exists: existsSync(external.full),
      };
    }
    const resolved = resolveBriefRel(briefRel);
    const abs = resolved ? absForRel(resolved) : "";
    return {
      input: String(briefRel || "").replace(/\\/g, "/"),
      path: resolved,
      exists: Boolean(resolved && existsSync(abs)),
    };
  });

  ipcMain.handle("visual-target-generate", async (event, briefRel, candidates, sceneId) => {
    const sender = event.sender;
    const n = Math.max(1, Math.min(4, Number(candidates) || 3));
    const sid = String(sceneId || "").trim();
    const args = [
      "brief",
      "visual-target",
      "generate",
      "--brief",
      briefCliArg(briefRel),
      "--candidates",
      String(n),
      "--json",
    ];
    if (sid) {
      args.push("--scene", sid);
    }
    const result = await runCli(args, {
      onLine: (line, stream) => {
        sender.send("pipeline-log", { line, stream });
      },
    });
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("visual-target-list", async (_e, briefRel, sceneId) => {
    const sid = String(sceneId || "").trim();
    const args = [
      "brief",
      "visual-target",
      "list",
      "--brief",
      briefCliArg(briefRel),
      "--json",
    ];
    if (sid) args.push("--scene", sid);
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("visual-target-pick", async (_e, briefRel, candidateId, sceneId, manifestPath) => {
    const sids = Array.isArray(sceneId)
      ? sceneId.map((s) => String(s || "").trim()).filter(Boolean)
      : String(sceneId || "").trim()
        ? [String(sceneId).trim()]
        : [];
    const args = [
      "brief",
      "visual-target",
      "pick",
      "--brief",
      briefCliArg(briefRel),
      "--id",
      String(candidateId || "").trim(),
      "--json",
    ];
    for (const sid of sids) args.push("--scene", sid);
    const mp = String(manifestPath || "").trim();
    if (mp) {
      // generate returns absolute path; absolute is fine for Click Path from cli/
      args.push("--manifest", path.isAbsolute(mp) ? mp : cliArgForRel(mp));
    }
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("visual-target-assign", async (_e, briefRel, sceneIds, opts) => {
    const sids = (Array.isArray(sceneIds) ? sceneIds : [sceneIds])
      .map((s) => String(s || "").trim())
      .filter(Boolean);
    const options = opts && typeof opts === "object" ? opts : {};
    const args = [
      "brief",
      "visual-target",
      "assign",
      "--brief",
      briefCliArg(briefRel),
      "--json",
    ];
    for (const sid of sids) args.push("--scene", sid);
    if (options.fromScene) args.push("--from-scene", String(options.fromScene).trim());
    if (options.fromGlobal) args.push("--from-global");
    if (options.ref) args.push("--ref", String(options.ref).trim());
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("visual-target-status", (_e, briefRel, sceneId) => {
    const root = repoRoot();
    const external = resolveExternalRel(briefRel);
    const rel = external ? external.rel : resolveBriefRel(briefRel);
    const sid = String(sceneId || "").trim() || null;
    if (!rel) {
      return { ok: false, ready: false, visual_reference: "", candidates: [], scenes: [] };
    }
    let briefAbs;
    try {
      briefAbs = absForRel(rel);
    } catch (err) {
      return {
        ok: false,
        ready: false,
        visual_reference: "",
        candidates: [],
        scenes: [],
        error: err instanceof Error ? err.message : String(err),
        brief_rel: rel,
      };
    }
    if (!existsSync(briefAbs)) {
      return {
        ok: false,
        ready: false,
        visual_reference: "",
        candidates: [],
        scenes: [],
        error: `brief not found: ${rel}`,
        brief_rel: rel,
      };
    }
    let visualReference = "";
    let projectScenes = [];
    try {
      const data = JSON.parse(readFileSync(briefAbs, "utf-8"));
      visualReference = String(data?.project?.visual_reference || "").trim();
      projectScenes = Array.isArray(data?.project?.scenes) ? data.project.scenes : [];
    } catch {
      return {
        ok: false,
        ready: false,
        visual_reference: "",
        candidates: [],
        scenes: [],
        error: "brief unreadable",
        brief_rel: rel,
      };
    }
    const projectRootAbs = external
      ? external.rootAbs
      : (() => {
          const key = projectRootKeyFromBriefRel(rel);
          return key && key.startsWith("projects/")
            ? path.join(root, key)
            : path.dirname(briefAbs);
        })();
    const refFileOk = (ref) => {
      const pathOk = looksLikeImagePath(ref);
      if (!pathOk) return { pathOk: false, fileOk: false };
      let abs = null;
      if (path.isAbsolute(ref)) {
        abs = ref;
      } else {
        try {
          abs = absForRel(ref);
        } catch {
          abs = path.join(projectRootAbs, ref);
        }
        // Relative refs are often stored vs repo root (projects/slug/output/...).
        if ((!abs || !existsSync(abs)) && !ref.replace(/\\/g, "/").startsWith("projects/")) {
          const underProj = path.join(projectRootAbs, ref);
          if (existsSync(underProj)) abs = underProj;
        }
      }
      return {
        pathOk: true,
        fileOk: Boolean(abs && existsSync(abs) && statSync(abs).isFile()),
      };
    };
    const globalCheck = refFileOk(visualReference);
    /** scene_id -> { selected_id, has_selected_image, preview_path } from VT manifests */
    const selectionByScene = new Map();
    let globalSelectedId = null;
    let globalHasSelectedImage = false;
    let globalPreviewPath = null;
    const toPreviewRel = (absPath) => {
      if (!absPath) return null;
      try {
        const r = path.relative(root, absPath).replace(/\\/g, "/");
        if (r && !r.startsWith("..")) return r;
        if (external?.rootAbs && pathUnderRoot(absPath, external.rootAbs)) {
          return `external:${external.entry?.id || ""}/${path
            .relative(external.rootAbs, absPath)
            .replace(/\\/g, "/")}`;
        }
      } catch {
        /* ignore */
      }
      return absPath;
    };
    const noteManifestSelection = (manPath, man) => {
      const manScene = String(man?.scene_id || "").trim() || null;
      const selRaw = man?.selected_id;
      const sel =
        selRaw === null || selRaw === undefined || selRaw === ""
          ? null
          : String(selRaw).trim().toLowerCase();
      const selectedAbs = path.join(path.dirname(manPath), "selected.png");
      const hasImg = existsSync(selectedAbs);
      const previewPath = hasImg ? toPreviewRel(selectedAbs) : null;
      if (!manScene) {
        if (sel || hasImg) {
          globalSelectedId = sel;
          globalHasSelectedImage = hasImg;
          if (previewPath) globalPreviewPath = previewPath;
        }
        return;
      }
      // Prefer entries that already have a pick; don't let empty manifests wipe.
      const prev = selectionByScene.get(manScene);
      if (prev && (prev.selected_id || prev.has_selected_image) && !(sel || hasImg)) {
        return;
      }
      selectionByScene.set(manScene, {
        selected_id: sel,
        has_selected_image: hasImg,
        preview_path: previewPath,
      });
    };
    const scenes = [];
    let anySceneReady = false;
    // First pass manifests later — scenes filled after tryManifests scan.
    const projectSceneRows = [];
    for (const row of projectScenes) {
      if (!row || typeof row !== "object") continue;
      const id = String(row.id || "").trim();
      const title = String(row.title || "").trim();
      if (!id) continue;
      const sref = String(row.visual_reference || "").trim();
      const check = refFileOk(sref);
      const ready = Boolean(check.pathOk && check.fileOk);
      if (ready) anySceneReady = true;
      projectSceneRows.push({ id, title, visual_reference: sref, ready });
    }
    const globalReady = Boolean(globalCheck.pathOk && globalCheck.fileOk);
    const candidates = [];
    const tryManifests = [];
    const pushVtManifestTree = (vtDir) => {
      tryManifests.push(path.join(vtDir, "manifest.json"));
      if (!existsSync(vtDir)) return;
      try {
        for (const name of readdirSync(vtDir)) {
          const sub = path.join(vtDir, name, "manifest.json");
          if (existsSync(sub)) tryManifests.push(sub);
        }
      } catch {
        /* ignore */
      }
    };
    // Prefer this project's visual-target tree only (no cross-project basename match).
    if (external?.rootAbs) {
      pushVtManifestTree(path.join(external.rootAbs, "output", "visual-target"));
    } else if (rel.startsWith("projects/")) {
      const slug = rel.split("/")[1];
      pushVtManifestTree(path.join(root, "projects", slug, "output", "visual-target"));
    } else {
      const stem = path.basename(rel).replace(/\.json$/i, "");
      pushVtManifestTree(path.join(root, "output", stem, "visual-target"));
    }
    let selectedId = null;
    const seen = new Set();
    const scored = [];
    for (const mPath of tryManifests) {
      if (!existsSync(mPath) || seen.has(mPath)) continue;
      seen.add(mPath);
      try {
        const man = JSON.parse(readFileSync(mPath, "utf-8"));
        noteManifestSelection(mPath, man);
        const manScene = String(man.scene_id || "").trim() || null;
        if (sid && manScene && manScene !== sid) continue;
        const briefInMan = String(man.brief_path || "").replace(/\\/g, "/");
        // Local tree already scoped; if manifest names a brief, require real match.
        if (
          briefInMan &&
          !manifestBelongsToBrief({
            briefAbs,
            briefRel: rel,
            manBriefPath: briefInMan,
            repoRoot: root,
          })
        ) {
          continue;
        }
        scored.push({
          mPath,
          man,
          manScene,
          mtime: statSync(mPath).mtimeMs || 0,
        });
      } catch {
        /* ignore */
      }
    }
    for (const row of projectSceneRows) {
      const pick = selectionByScene.get(row.id) || {};
      let previewPath = null;
      if (row.ready && row.visual_reference) {
        previewPath = row.visual_reference.replace(/\\/g, "/");
      } else if (pick.preview_path) {
        previewPath = pick.preview_path;
      }
      scenes.push({
        id: row.id,
        title: row.title,
        visual_reference: row.visual_reference,
        ready: row.ready,
        selected_id: pick.selected_id || null,
        has_selected_image: Boolean(pick.has_selected_image),
        marked: Boolean(row.ready || pick.has_selected_image),
        preview_path: previewPath,
      });
    }
    scored.sort((a, b) => b.mtime - a.mtime);
    if (sid) {
      scored.sort((a, b) => {
        const aHit = a.manScene === sid ? 1 : 0;
        const bHit = b.manScene === sid ? 1 : 0;
        if (aHit !== bHit) return bHit - aHit;
        return b.mtime - a.mtime;
      });
    }
    const best = scored[0];
    if (best) {
      selectedId = best.man.selected_id || null;
      for (const c of best.man.candidates || []) {
        if (!c || !c.id) continue;
        const cAbs = String(c.path || "");
        let cRel = cAbs;
        if (cAbs) {
          const abs = path.isAbsolute(cAbs) ? cAbs : path.join(root, cAbs);
          try {
            const r = path.relative(root, abs).replace(/\\/g, "/");
            if (r && !r.startsWith("..")) cRel = r;
            else if (external?.rootAbs && pathUnderRoot(abs, external.rootAbs)) {
              cRel = `external:${external.entry?.id || ""}/${path
                .relative(external.rootAbs, abs)
                .replace(/\\/g, "/")}`;
            } else {
              cRel = abs;
            }
          } catch {
            cRel = abs;
          }
        }
        candidates.push({
          id: String(c.id),
          label: c.label || c.id,
          path: cRel || cAbs,
          status: c.status,
        });
      }
    }
    if (!selectedId && globalSelectedId) selectedId = globalSelectedId;
    let globalPreview = null;
    if (globalReady && visualReference) {
      globalPreview = visualReference.replace(/\\/g, "/");
    } else if (globalPreviewPath) {
      globalPreview = globalPreviewPath;
    }
    return {
      ok: true,
      // Run gate: brief must bind a real visual_reference path (not disk-only selected.png).
      ready: globalReady || anySceneReady,
      disk_marked: globalHasSelectedImage || scenes.some((s) => s.marked),
      global_ready: globalReady,
      global_selected_id: globalSelectedId,
      global_has_selected_image: globalHasSelectedImage,
      global_preview_path: globalPreview,
      visual_reference: visualReference,
      path_shaped: globalCheck.pathOk,
      file_ok: globalCheck.fileOk,
      selected_id: selectedId,
      scene_id: sid,
      scenes,
      candidates,
    };
  });

  ipcMain.handle("open-godot", async (_e, projectRel) => {
    const result = await runCli([
      "godot",
      "open",
      "--project",
      cliArgForRel(projectRel),
    ]);
    return result;
  });

  ipcMain.handle("get-config", () => loadUserConfig());

  ipcMain.handle("save-config", (_e, patch) => {
    try {
      return saveUserConfig(patch);
    } catch (err) {
      return { ok: false, error: err instanceof Error ? err.message : String(err) };
    }
  });

  ipcMain.handle("init-config-from-example", () => {
    const example = path.join(repoRoot(), "resources", "config.example.json");
    if (!existsSync(example)) {
      throw new Error(`示例配置不存在: ${example}`);
    }
    const cfgPath = configPath();
    mkdirSync(path.dirname(cfgPath), { recursive: true });
    cpSync(example, cfgPath);
    return loadUserConfig();
  });

  ipcMain.handle("open-config-folder", () => {
    const dir = path.dirname(configPath());
    mkdirSync(dir, { recursive: true });
    shell.openPath(dir);
    return { ok: true };
  });

  ipcMain.handle("pick-file", async (_e, opts) => {
    const { dialog } = await import("electron");
    const result = await dialog.showOpenDialog(mainWindow, {
      title: opts?.title || "选择文件",
      properties: ["openFile"],
      filters: opts?.filters || [{ name: "All", extensions: ["*"] }],
    });
    return result.canceled ? null : result.filePaths[0] || null;
  });

  ipcMain.handle("get-media-preview", (_e, relPath, posterRel) => {
    const abs = resolveMediaAbs(relPath);
    if (!abs) return null;
    const posterAbs = posterRel ? resolveMediaAbs(posterRel) : null;
    return buildMediaPreview(abs, posterAbs || undefined);
  });

  ipcMain.handle("open-media", (_e, relPath) => {
    const abs = resolveMediaAbs(relPath);
    if (!abs) return { ok: false, error: "文件不存在" };
    shell.openPath(abs);
    return { ok: true, path: relToRepo(abs) };
  });

  ipcMain.handle("host-chat-start", async (_e, sessionId, seed, instanceId, briefRel) => {
    const args = ["brief", "chat", "start", "--json", "--session-id", String(sessionId || "").trim()];
    if (seed && String(seed).trim()) {
      args.push("--seed", String(seed).trim());
    }
    if (briefRel && String(briefRel).trim()) {
      args.push("--brief-rel", String(briefRel).replace(/\\/g, "/").trim());
    }
    abortedChatInstances.delete(String(instanceId || "").trim());
    const result = await runCli(args, { jobKey: chatJobKey(instanceId) });
    return withAbortMeta({ ...result, data: parseJsonFromOutput(result.stdout) }, instanceId);
  });

  ipcMain.handle("host-chat-turn", async (_e, sessionId, message, instanceId, briefRel) => {
    const args = [
      "brief",
      "chat",
      "turn",
      "--session-id",
      String(sessionId || "").trim(),
      "--message",
      String(message),
      "--json",
    ];
    if (instanceId) {
      args.push("--instance-id", String(instanceId));
    }
    if (briefRel && String(briefRel).trim()) {
      args.push("--brief-rel", String(briefRel).replace(/\\/g, "/").trim());
    }
    abortedChatInstances.delete(String(instanceId || "").trim());
    const result = await runCli(args, { jobKey: chatJobKey(instanceId) });
    return withAbortMeta({ ...result, data: parseJsonFromOutput(result.stdout) }, instanceId);
  });

  ipcMain.handle("host-chat-reset", async (_e, sessionId, seed, instanceId, briefRel) => {
    const args = ["brief", "chat", "reset", "--json", "--session-id", String(sessionId || "").trim()];
    if (seed && String(seed).trim()) {
      args.push("--seed", String(seed).trim());
    }
    if (briefRel && String(briefRel).trim()) {
      args.push("--brief-rel", String(briefRel).replace(/\\/g, "/").trim());
    }
    abortedChatInstances.delete(String(instanceId || "").trim());
    const result = await runCli(args, { jobKey: chatJobKey(instanceId) });
    return withAbortMeta({ ...result, data: parseJsonFromOutput(result.stdout) }, instanceId);
  });

  ipcMain.handle("host-chat-bind", async (_e, sessionId, briefRel) => {
    const args = [
      "brief",
      "chat",
      "bind",
      "--json",
      "--session-id",
      String(sessionId || "").trim(),
      "--brief-rel",
      String(briefRel || "").replace(/\\/g, "/").trim(),
    ];
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("host-chat-export", async (_e, sessionId, outputRel, instanceId) => {
    const rel = String(outputRel || "").replace(/\\/g, "/").replace(/^\.\.\//, "");
    const abs = absForRel(rel);
    mkdirSync(path.dirname(abs), { recursive: true });
    const args = [
      "brief",
      "chat",
      "export",
      "--session-id",
      String(sessionId || "").trim(),
      "-o",
      cliArgForRel(rel),
      "--json",
    ];
    abortedChatInstances.delete(String(instanceId || "").trim());
    const result = await runCli(args, { jobKey: chatJobKey(instanceId) });
    if (result.aborted || takeChatAbort(instanceId)) {
      return abortedChatResult({ stdout: result.stdout, stderr: result.stderr });
    }
    const data = parseJsonFromOutput(result.stdout) || {};
    if (!data.brief_path) data.brief_path = abs;
    data.brief_rel = rel;
    if (data.zh_doc_path) {
      const zhAbs = String(data.zh_doc_path).replace(/\\/g, "/");
      const root = repoRoot().replace(/\\/g, "/");
      const external = resolveExternalRel(rel);
      if (external) {
        const extRoot = external.rootAbs.replace(/\\/g, "/");
        if (zhAbs.toLowerCase().startsWith(extRoot.toLowerCase() + "/")) {
          const sub = zhAbs.slice(extRoot.length + 1);
          data.zh_doc_rel = `external:${external.entry.id}/${sub}`;
        } else {
          data.zh_doc_rel = `${path.posix.dirname(rel)}/brief.zh.md`;
        }
      } else if (zhAbs.toLowerCase().startsWith(root.toLowerCase() + "/")) {
        data.zh_doc_rel = zhAbs.slice(root.length + 1);
      } else {
        const parentRel = path.posix.dirname(rel);
        data.zh_doc_rel = `${parentRel}/brief.zh.md`;
      }
    }
    return { ...result, data };
  });

  ipcMain.handle("host-chat-zh-doc", async (_e, sessionId, briefRel, skeletonOnly = false) => {
    const rel = String(briefRel || "").replace(/\\/g, "/").replace(/^\.\.\//, "");
    const args = [
      "brief",
      "chat",
      "zh-doc",
      "--session-id",
      String(sessionId || "").trim(),
      "--brief-rel",
      rel,
      "--json",
    ];
    if (skeletonOnly) args.push("--skeleton-only");
    const result = await runCli(args);
    const data = parseJsonFromOutput(result.stdout) || {};
    if (data.zh_doc_path) {
      const zhAbs = String(data.zh_doc_path).replace(/\\/g, "/");
      const root = repoRoot().replace(/\\/g, "/");
      const external = resolveExternalRel(rel);
      if (external) {
        const extRoot = external.rootAbs.replace(/\\/g, "/");
        if (zhAbs.toLowerCase().startsWith(extRoot.toLowerCase() + "/")) {
          const sub = zhAbs.slice(extRoot.length + 1);
          data.zh_doc_rel = `external:${external.entry.id}/${sub}`;
        } else {
          data.zh_doc_rel = `${path.posix.dirname(rel)}/brief.zh.md`;
        }
      } else if (zhAbs.toLowerCase().startsWith(root.toLowerCase() + "/")) {
        data.zh_doc_rel = zhAbs.slice(root.length + 1);
      } else {
        data.zh_doc_rel = `${path.posix.dirname(rel)}/brief.zh.md`;
      }
    }
    return { ...result, data };
  });

  ipcMain.handle("host-chat-ui-wireframe", async (_e, sessionId, briefRel) => {
    const rel = String(briefRel || "").replace(/\\/g, "/").replace(/^\.\.\//, "");
    const args = [
      "brief",
      "chat",
      "ui-wireframe",
      "--session-id",
      String(sessionId || "").trim(),
      "--brief-rel",
      rel,
      "--json",
    ];
    const result = await runCli(args);
    const data = parseJsonFromOutput(result.stdout) || {};
    if (data.path) {
      const wireAbs = String(data.path).replace(/\\/g, "/");
      const root = repoRoot().replace(/\\/g, "/");
      const external = resolveExternalRel(rel);
      if (external) {
        const extRoot = external.rootAbs.replace(/\\/g, "/");
        if (wireAbs.toLowerCase().startsWith(extRoot.toLowerCase() + "/")) {
          const sub = wireAbs.slice(extRoot.length + 1);
          data.ui_wireframe_rel = `external:${external.entry.id}/${sub}`;
        } else {
          data.ui_wireframe_rel = `${path.posix.dirname(rel)}/ui-wireframe.md`;
        }
      } else if (wireAbs.toLowerCase().startsWith(root.toLowerCase() + "/")) {
        data.ui_wireframe_rel = wireAbs.slice(root.length + 1);
      } else {
        data.ui_wireframe_rel = `${path.posix.dirname(rel)}/ui-wireframe.md`;
      }
    }
    return { ...result, data };
  });

  ipcMain.handle("host-chat-autofix", async (_e, sessionId, maxRounds = 5, instanceId) => {
    const rounds = Math.max(1, Math.min(12, Number(maxRounds) || 5));
    const args = [
      "brief",
      "chat",
      "autofix",
      "--session-id",
      String(sessionId || "").trim(),
      "--max-rounds",
      String(rounds),
      "--json",
    ];
    abortedChatInstances.delete(String(instanceId || "").trim());
    const result = await runCli(args, { jobKey: chatJobKey(instanceId) });
    return withAbortMeta({ ...result, data: parseJsonFromOutput(result.stdout) }, instanceId);
  });

  ipcMain.handle("host-chat-makeability", async (_e, sessionId, instanceId) => {
    const args = [
      "brief",
      "chat",
      "makeability",
      "--session-id",
      String(sessionId || "").trim(),
      "--json",
    ];
    abortedChatInstances.delete(String(instanceId || "").trim());
    const result = await runCli(args, { jobKey: chatJobKey(instanceId) });
    return withAbortMeta({ ...result, data: parseJsonFromOutput(result.stdout) }, instanceId);
  });

  ipcMain.handle("host-chat-makeability-answer", async (_e, sessionId, answers, instanceId) => {
    const args = [
      "brief",
      "chat",
      "makeability-answer",
      "--session-id",
      String(sessionId || "").trim(),
      "--answers",
      JSON.stringify(answers || []),
      "--json",
    ];
    abortedChatInstances.delete(String(instanceId || "").trim());
    const result = await runCli(args, { jobKey: chatJobKey(instanceId) });
    return withAbortMeta({ ...result, data: parseJsonFromOutput(result.stdout) }, instanceId);
  });

  ipcMain.handle("host-chat-enrich", async (_e, sessionId, hint, instanceId) => {
    const args = [
      "brief",
      "chat",
      "enrich",
      "--session-id",
      String(sessionId || "").trim(),
      "--json",
    ];
    const h = String(hint || "").trim();
    if (h) {
      args.push("--hint", h);
    }
    abortedChatInstances.delete(String(instanceId || "").trim());
    const result = await runCli(args, { jobKey: chatJobKey(instanceId) });
    return withAbortMeta({ ...result, data: parseJsonFromOutput(result.stdout) }, instanceId);
  });

  ipcMain.handle(
    "host-chat-topic-brainstorm",
    async (_e, sessionId, topic, constraints, multiModel, instanceId) => {
      const args = [
        "brief",
        "chat",
        "topic-brainstorm",
        "--session-id",
        String(sessionId || "").trim(),
        "--topic",
        String(topic || "").trim(),
        "--json",
      ];
      const c = String(constraints || "").trim();
      if (c) args.push("--constraints", c);
      if (multiModel) args.push("--multi-model");
      abortedChatInstances.delete(String(instanceId || "").trim());
      const result = await runCli(args, { jobKey: chatJobKey(instanceId) });
      return withAbortMeta({ ...result, data: parseJsonFromOutput(result.stdout) }, instanceId);
    },
  );

  ipcMain.handle(
    "host-chat-brainstorm-apply",
    async (_e, sessionId, proposalIds, fuse, instanceId) => {
      const args = [
        "brief",
        "chat",
        "brainstorm-apply",
        "--session-id",
        String(sessionId || "").trim(),
        "--json",
      ];
      const ids = Array.isArray(proposalIds) ? proposalIds : [proposalIds];
      for (const id of ids) {
        const s = String(id || "").trim();
        if (s) args.push("--proposal-id", s);
      }
      if (fuse) args.push("--fuse");
      abortedChatInstances.delete(String(instanceId || "").trim());
      const result = await runCli(args, { jobKey: chatJobKey(instanceId) });
      return withAbortMeta({ ...result, data: parseJsonFromOutput(result.stdout) }, instanceId);
    },
  );

  ipcMain.handle("host-chat-status", async (_e, sessionId) => {
    const sid = String(sessionId || "").trim();
    if (!sid) {
      return { exitCode: 0, data: { exists: false } };
    }
    const result = await runCli(["brief", "chat", "status", "--session-id", sid, "--json"]);
    const data = parseJsonFromOutput(result.stdout);
    if (!data) {
      return { ...result, data: { exists: false, id: sid } };
    }
    return { ...result, data: { exists: data.exists !== false, ...data } };
  });

  ipcMain.handle("host-chat-focus", async (_e, sessionId, opts = {}) => {
    const sid = String(sessionId || "").trim();
    const args = ["brief", "chat", "focus", "--session-id", sid, "--json"];
    if (opts && opts.clear) {
      args.push("--clear");
    } else {
      const kind = String(opts.kind || "").trim();
      if (kind) args.push("--kind", kind);
      const id = String(opts.id || "").trim();
      if (id) args.push("--id", id);
      if (opts.extra && typeof opts.extra === "object") {
        args.push("--extra", JSON.stringify(opts.extra));
      }
    }
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("agent-turn", async (event, opts = {}) => {
    const role = String(opts.role || "").trim();
    const sessionId = String(opts.sessionId || "").trim();
    const message = String(opts.message || "");
    const config = loadUserConfig().data || {};
    const effectiveExecutor = resolveExecutorForAgentTurn(config, role, opts);
    const permissionMode = resolveCursorPermissionMode(config, opts.instanceId);
    const hermesYolo = resolveHermesYolo(config, opts.instanceId);
    const codexSandbox = resolveCodexSandbox(config, opts.instanceId);
    const instanceKey = String(opts.instanceId || sessionId).trim();
    abortedChatInstances.delete(instanceKey);
    let preparedAcpPrompt;
    const acpPrompt = async () => {
      if (role !== "it") return message;
      if (!preparedAcpPrompt) {
        const brief = String(opts.brief || "")
          .replace(/\\/g, "/")
          .replace(/^\.\.\//, "");
        const progress = String(opts.progress || "")
          .replace(/\\/g, "/")
          .replace(/^\.\.\//, "");
        preparedAcpPrompt = prepareRoleAwareAcpPrompt({
          roleKind: role,
          message,
          promptOptions: {
            roleKind: role,
            sessionId,
            message,
            executor: effectiveExecutor,
            instanceId: opts.instanceId,
            briefArg: brief ? cliArgForRel(brief) : "",
            progressArg: progress ? cliArgForRel(progress) : "",
          },
          runPromptCommand: (args) =>
            runCli(args, { jobKey: chatJobKey(instanceKey) }),
          parseJsonOutput: parseJsonFromOutput,
        });
      }
      return preparedAcpPrompt;
    };

    // IT home-ops: default session trust (skip per-tool cards) unless explicitly off
    if (role === "it" && sessionId && toolPermissionBridge) {
      const trust =
        opts.piSessionTrust === undefined || opts.piSessionTrust === null
          ? true
          : Boolean(opts.piSessionTrust);
      if (trust) toolPermissionBridge.trustSession(sessionId);
      else toolPermissionBridge.untrustSession(sessionId);
    }

    if (effectiveExecutor === "cursor" && permissionMode !== "force") {
      if (!cursorAcpSessionManager) {
        const errMsg = "Cursor ACP 会话管理器未初始化，请重启 GUI。";
        return {
          exitCode: 1,
          stdout: "",
          stderr: errMsg,
          data: { ok: false, error: errMsg },
        };
      }

      const turnId = randomUUID();
      try {
        const out = await cursorAcpSessionManager.prompt({
          instanceId: instanceKey,
          sessionId,
          turnId,
          workspaceCwd: repoRoot(),
          text: await acpPrompt(),
          permissionMode,
        });

        if (takeChatAbort(instanceKey)) {
          return abortedChatResult();
        }

        const recordArgs = [
          "agent",
          "record-turn",
          "--role",
          role,
          "--session-id",
          sessionId,
          "--message",
          message,
          "--assistant-message",
          out.text,
          "--executor",
          "cursor",
          "--json",
        ];
        const recordResult = await runCli(recordArgs, { jobKey: chatJobKey(instanceKey) });
        if (recordResult.aborted || takeChatAbort(instanceKey)) {
          return abortedChatResult({ stdout: recordResult.stdout, stderr: recordResult.stderr });
        }
        const recordData = parseJsonFromOutput(recordResult.stdout) || {};
        if (recordResult.exitCode !== 0 || recordData.ok === false) {
          const errMsg =
            String(recordData.error || "").trim() ||
            recordResult.stderr.trim() ||
            "无法持久化 ACP 对话回合";
          return {
            exitCode: 1,
            stdout: recordResult.stdout,
            stderr: recordResult.stderr || errMsg,
            data: { ok: false, error: errMsg },
          };
        }

        const payload = {
          ...recordData,
          ok: true,
          assistant_message: out.text,
          executor: "cursor",
          stderr_tail: out.stderrTail || "",
        };
        const stdout = JSON.stringify(payload, null, 2);
        return {
          exitCode: 0,
          stdout,
          stderr: out.stderrTail || "",
          data: payload,
        };
      } catch (err) {
        if (takeChatAbort(instanceKey)) {
          return abortedChatResult();
        }
        const errMsg = err instanceof Error ? err.message : "Cursor ACP 回合失败";
        return {
          exitCode: 1,
          stdout: "",
          stderr: errMsg,
          data: { ok: false, error: errMsg },
        };
      }
    }

    if (effectiveExecutor === "hermes" && !hermesYolo) {
      if (!hermesAcpSessionManager) {
        const errMsg = "Hermes ACP 会话管理器未初始化，请重启 GUI。";
        return {
          exitCode: 1,
          stdout: "",
          stderr: errMsg,
          data: { ok: false, error: errMsg },
        };
      }

      const turnId = randomUUID();
      try {
        const out = await hermesAcpSessionManager.prompt({
          instanceId: instanceKey,
          sessionId,
          turnId,
          workspaceCwd: repoRoot(),
          text: await acpPrompt(),
        });

        if (takeChatAbort(instanceKey)) {
          return abortedChatResult();
        }

        const recordArgs = [
          "agent",
          "record-turn",
          "--role",
          role,
          "--session-id",
          sessionId,
          "--message",
          message,
          "--assistant-message",
          out.text,
          "--executor",
          "hermes",
          "--json",
        ];
        const recordResult = await runCli(recordArgs, { jobKey: chatJobKey(instanceKey) });
        if (recordResult.aborted || takeChatAbort(instanceKey)) {
          return abortedChatResult({ stdout: recordResult.stdout, stderr: recordResult.stderr });
        }
        const recordData = parseJsonFromOutput(recordResult.stdout) || {};
        if (recordResult.exitCode !== 0 || recordData.ok === false) {
          const errMsg =
            String(recordData.error || "").trim() ||
            recordResult.stderr.trim() ||
            "无法持久化 ACP 对话回合";
          return {
            exitCode: 1,
            stdout: recordResult.stdout,
            stderr: recordResult.stderr || errMsg,
            data: { ok: false, error: errMsg },
          };
        }

        const payload = {
          ...recordData,
          ok: true,
          assistant_message: out.text,
          executor: "hermes",
          stderr_tail: out.stderrTail || "",
        };
        const stdout = JSON.stringify(payload, null, 2);
        return {
          exitCode: 0,
          stdout,
          stderr: out.stderrTail || "",
          data: payload,
        };
      } catch (err) {
        if (takeChatAbort(instanceKey)) {
          return abortedChatResult();
        }
        const errMsg = err instanceof Error ? err.message : "Hermes ACP 回合失败";
        return {
          exitCode: 1,
          stdout: "",
          stderr: errMsg,
          data: { ok: false, error: errMsg },
        };
      }
    }

    if (effectiveExecutor === "codex" && codexSandbox !== "danger-full-access") {
      if (!codexAppServerSessionManager) {
        const errMsg = "Codex app-server 会话管理器未初始化，请重启 GUI。";
        return {
          exitCode: 1,
          stdout: "",
          stderr: errMsg,
          data: { ok: false, error: errMsg },
        };
      }

      const turnId = randomUUID();
      const codexInst = agentInstanceRecord(config, opts.instanceId);
      const codexPreset = config?.agents?.executors?.codex;
      const codexModel =
        String(codexInst.model || (codexPreset && typeof codexPreset === "object" ? codexPreset.model : "") || "")
          .trim() || undefined;

      try {
        /** @type {Record<string, unknown>} */
        const promptArgs = {
          instanceId: instanceKey,
          sessionId,
          turnId,
          cwd: repoRoot(),
          message: await acpPrompt(),
          sandbox: codexSandbox,
        };
        if (codexModel) {
          promptArgs.model = codexModel;
        }

        const out = await codexAppServerSessionManager.prompt(promptArgs);

        if (takeChatAbort(instanceKey)) {
          return abortedChatResult();
        }

        const recordArgs = [
          "agent",
          "record-turn",
          "--role",
          role,
          "--session-id",
          sessionId,
          "--message",
          message,
          "--assistant-message",
          out.text,
          "--executor",
          "codex",
          "--json",
        ];
        const recordResult = await runCli(recordArgs, { jobKey: chatJobKey(instanceKey) });
        if (recordResult.aborted || takeChatAbort(instanceKey)) {
          return abortedChatResult({ stdout: recordResult.stdout, stderr: recordResult.stderr });
        }
        const recordData = parseJsonFromOutput(recordResult.stdout) || {};
        if (recordResult.exitCode !== 0 || recordData.ok === false) {
          const errMsg =
            String(recordData.error || "").trim() ||
            recordResult.stderr.trim() ||
            "无法持久化 Codex app-server 对话回合";
          return {
            exitCode: 1,
            stdout: recordResult.stdout,
            stderr: recordResult.stderr || errMsg,
            data: { ok: false, error: errMsg },
          };
        }

        const payload = {
          ...recordData,
          ok: true,
          assistant_message: out.text,
          executor: "codex",
          stderr_tail: out.stderrTail || "",
        };
        const stdout = JSON.stringify(payload, null, 2);
        return {
          exitCode: 0,
          stdout,
          stderr: out.stderrTail || "",
          data: payload,
        };
      } catch (err) {
        if (takeChatAbort(instanceKey)) {
          return abortedChatResult();
        }
        const errMsg = err instanceof Error ? err.message : "Codex app-server 回合失败";
        return {
          exitCode: 1,
          stdout: "",
          stderr: errMsg,
          data: { ok: false, error: errMsg },
        };
      }
    }

    if (effectiveExecutor === "cursor" && permissionMode === "force") {
      cursorAcpSessionManager?.stop(instanceKey);
    }

    if (effectiveExecutor === "hermes" && hermesYolo) {
      hermesAcpSessionManager?.stop(instanceKey);
    }

    if (effectiveExecutor === "codex" && codexSandbox === "danger-full-access") {
      codexAppServerSessionManager?.stop(instanceKey);
    }

    const brief = String(opts.brief || "")
      .replace(/\\/g, "/")
      .replace(/^\.\.\//, "");
    const progress = String(opts.progress || "")
      .replace(/\\/g, "/")
      .replace(/^\.\.\//, "");
    const args = buildAgentTurnArgs({
      roleKind: role,
      sessionId,
      message,
      effectiveExecutor,
      briefArg: brief ? cliArgForRel(brief) : "",
      progressArg: progress ? cliArgForRel(progress) : "",
      instanceId: opts.instanceId,
      targetInstanceId: opts.targetInstanceId,
      rosterJson: opts.rosterJson,
      timeout: opts.timeout,
    });
    const sender = event.sender;
    const result = await runCli(args, {
      jobKey: chatJobKey(instanceKey),
      onLine: (line, stream) => {
        sender.send("pipeline-log", { line, stream, source: "agent" });
      },
    });
    return withAbortMeta({ ...result, data: parseJsonFromOutput(result.stdout) }, instanceKey);
  });

  ipcMain.handle("agent-tool-permission-decision", async (_e, permissionId, decision) => {
    const id = String(permissionId || "");
    if (cursorAcpSessionManager?.decidePermission(id, decision)) {
      clearAcpPermissionTimer(id);
      return { ok: true };
    }
    if (hermesAcpSessionManager?.decidePermission(id, decision)) {
      clearAcpPermissionTimer(id);
      return { ok: true };
    }
    if (codexAppServerSessionManager?.decidePermission({ permissionId: id, decision })) {
      clearAcpPermissionTimer(id);
      return { ok: true };
    }
    if (!toolPermissionBridge) return { ok: false };
    const ok = toolPermissionBridge.decide(id, decision);
    return { ok };
  });

  ipcMain.handle("pi-session-trust", async (_e, sessionId, trusted) => {
    if (!toolPermissionBridge) return { ok: false, error: "bridge unavailable" };
    const sid = String(sessionId || "").trim();
    if (!sid) return { ok: false, error: "missing sessionId" };
    if (trusted) toolPermissionBridge.trustSession(sid);
    else toolPermissionBridge.untrustSession(sid);
    return { ok: true, trusted: Boolean(trusted) };
  });

  ipcMain.handle("agent-acp-stop-instance", async (_e, instanceId) => {
    const key = String(instanceId || "").trim();
    if (!key) return { ok: false, error: "missing instanceId" };
    cursorAcpSessionManager?.stop(key);
    hermesAcpSessionManager?.stop(key);
    codexAppServerSessionManager?.stop(key);
    return { ok: true };
  });

  ipcMain.handle("chat-stop", async (_e, instanceId) => stopChatRuntime(instanceId));

  ipcMain.handle("agent-status", async (_e, role, sessionId) => {
    const result = await runCli([
      "agent",
      "status",
      "--role",
      String(role || "").trim(),
      "--session-id",
      String(sessionId || "").trim(),
      "--json",
    ]);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("handoff-list", async (_e, status = "open", targetInstanceId = null) => {
    const st = String(status || "open");
    const args = ["project", "handoff", "list", "--json"];
    if (st && st !== "open") {
      args.push("--status", st);
    } else {
      args.push("--status", "open");
    }
    if (targetInstanceId) {
      args.push("--target-instance-id", String(targetInstanceId));
    }
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("production-delta", async (_e, opts = {}) => {
    const changeId = String(opts.changeId || "").trim();
    const intent = String(opts.intent || "").trim();
    const args = [
      "production",
      "delta",
      "--change-id",
      changeId,
      "--intent",
      intent,
      "--json",
    ];
    for (const t of opts.tasks || []) {
      args.push("--task", String(t));
    }
    if (opts.output) {
      args.push("--output", cliArgForRel(String(opts.output)));
    }
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("production-apply-delta", async (_e, opts = {}) => {
    const args = [
      "production",
      "apply-delta",
      "--delta",
      cliArgForRel(String(opts.delta || "")),
      "--production",
      cliArgForRel(String(opts.production || "")),
      "--json",
    ];
    if (opts.progress) {
      args.push("--progress", cliArgForRel(String(opts.progress)));
    }
    if (opts.dryRun) {
      args.push("--dry-run");
    }
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("run-safe-action", async (event, command) => {
    const cmd = String(command || "").trim();
    const sender = event.sender;
    const result = await runCli(
      [
        "project",
        "action",
        "--cmd",
        cmd,
        "--json",
      ],
      {
        onLine: (line, stream) => {
          sender.send("pipeline-log", { line, stream, source: "action" });
        },
      },
    );
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("list-output-media", (_e, dirRel, limit = 24) => {
    const absDir = resolveMediaAbs(dirRel);
    if (!absDir) return [];
    const bucket = [];
    walkMediaFiles(absDir, bucket);
    bucket.sort((a, b) => b.mtime - a.mtime);
    const picked = [];
    const seenVideo = new Set();
    for (const item of bucket) {
      if (picked.length >= limit) break;
      if (item.kind === "video") {
        if (seenVideo.has(item.name)) continue;
        seenVideo.add(item.name);
      }
      if (item.kind === "image" && /_raw\.|_trimmed\.|frame_/i.test(item.name)) {
        continue;
      }
      const rel = relToRepo(item.abs);
      const posterAbs = item.kind === "video" ? findVideoPosterAbs(item.abs) : null;
      picked.push({
        path: rel,
        kind: item.kind,
        label: item.name,
        posterPath: posterAbs ? relToRepo(posterAbs) : undefined,
      });
    }
    return picked;
  });

  createWindow();
  initAutoUpdate(() => mainWindow);

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
      initAutoUpdate(() => mainWindow);
    }
  });
});

app.on("before-quit", () => {
  for (const [, timer] of acpPermissionTimers) {
    clearTimeout(timer);
  }
  acpPermissionTimers.clear();
  // Sync kill so orphans cannot lock install-dir files during NSIS upgrade.
  abortAllCliJobs({ sync: true });
  cursorAcpSessionManager?.disposeAll({ sync: true });
  cursorAcpSessionManager = null;
  hermesAcpSessionManager?.disposeAll({ sync: true });
  hermesAcpSessionManager = null;
  codexAppServerSessionManager?.disposeAll({ sync: true });
  codexAppServerSessionManager = null;
  toolPermissionBridge?.close();
  toolPermissionBridge = null;
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
