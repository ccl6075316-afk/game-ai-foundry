import { app, BrowserWindow, ipcMain, shell, protocol, net } from "electron";
import { spawn } from "node:child_process";
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
  resolvePython,
} from "./paths.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isDev = !isPackagedApp();

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

function runCli(args, { cwd, onLine } = {}) {
  const root = repoRoot();
  const python = resolvePython(root);
  const workdir = cwd || cliDir(root);

  return new Promise((resolve, reject) => {
    const proc = spawn(python, ["gamefactory.py", ...args], {
      cwd: workdir,
      env: { ...process.env, GAMEFACTORY_ROOT: root, PYTHONIOENCODING: "utf-8" },
      shell: false,
    });

    let stdout = "";
    let stderr = "";

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
    proc.on("error", reject);
    proc.on("close", (code) => {
      resolve({ exitCode: code ?? 1, stdout, stderr });
    });
  });
}

function parseJsonFromOutput(text) {
  const trimmed = text.trim();
  if (!trimmed) return null;
  try {
    return JSON.parse(trimmed);
  } catch {
    const start = trimmed.indexOf("{");
    const arrStart = trimmed.indexOf("[");
    const idx =
      start >= 0 && arrStart >= 0 ? Math.min(start, arrStart) : Math.max(start, arrStart);
    if (idx < 0) return null;
    try {
      return JSON.parse(trimmed.slice(idx));
    } catch {
      return null;
    }
  }
}

function listBriefs() {
  const dir = path.join(repoRoot(), "resources");
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((f) => f.endsWith(".json") && f.includes("brief"))
    .map((f) => {
      const full = path.join(dir, f);
      const stat = statSync(full);
      return {
        id: f.replace(/\.json$/, ""),
        path: path.join("resources", f).replace(/\\/g, "/"),
        label: f,
        mtime: stat.mtimeMs,
      };
    })
    .sort((a, b) => b.mtime - a.mtime);
}

function listManifests() {
  const dir = path.join(repoRoot(), "pipeline");
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => {
      const full = path.join(dir, f);
      const stat = statSync(full);
      return {
        id: f.replace(/\.json$/, ""),
        path: path.join("pipeline", f).replace(/\\/g, "/"),
        label: f,
        mtime: stat.mtimeMs,
      };
    })
    .sort((a, b) => b.mtime - a.mtime);
}

function manifestMeta(relPath) {
  try {
    const manifest = loadManifest(relPath);
    const outputDir = manifest.paths?.output_dir || "";
    const godotProject = manifest.godot_project || "";
    const brief = manifest.brief || "";
    return {
      brief: String(brief).replace(/\\/g, "/"),
      output_dir: String(outputDir).replace(/\\/g, "/"),
      godot_project: String(godotProject).replace(/\\/g, "/"),
      project_title: manifest.project?.title || "",
    };
  } catch {
    return null;
  }
}

function loadManifest(relPath) {
  const full = path.join(repoRoot(), relPath);
  return JSON.parse(readFileSync(full, "utf-8"));
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

function relToRepo(absPath) {
  const root = repoRoot();
  const rel = path.relative(root, absPath);
  return rel.split(path.sep).join("/");
}

function resolveMediaAbs(relOrAbs) {
  const root = repoRoot();
  let candidate = relOrAbs;
  if (!path.isAbsolute(candidate)) {
    candidate = path.join(root, candidate.split("/").join(path.sep));
  }
  candidate = path.normalize(candidate);
  if (!candidate.startsWith(root) || !existsSync(candidate)) return null;
  return candidate;
}

function mediaKind(ext) {
  const lower = ext.toLowerCase();
  if (IMAGE_EXTS.has(lower)) return "image";
  if (VIDEO_EXTS.has(lower)) return "video";
  return null;
}

function toMediaUrl(absPath) {
  return `gamefactory-media://local/?p=${encodeURIComponent(absPath)}`;
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
  protocol.handle("gamefactory-media", (request) => {
    try {
      const url = new URL(request.url);
      const abs = decodeURIComponent(url.searchParams.get("p") || "");
      const resolved = resolveMediaAbs(abs);
      if (!resolved) {
        return new Response("Not found", { status: 404 });
      }
      return net.fetch(pathToFileURL(resolved).href);
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
  }));

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

  ipcMain.handle("executor-step", async (event, executorId, stepId) => {
    const sender = event.sender;
    const result = await runCli(
      ["setup", "executor", "step", String(executorId), String(stepId), "--json"],
      {
        onLine: (line) => {
          sender.send("toolchain-log", { line });
        },
      },
    );
    const data = parseJsonFromOutput(result.stdout);
    return { ...result, data };
  });

  ipcMain.handle("open-external", async (_e, url) => {
    if (!url || typeof url !== "string") {
      return { ok: false, error: "invalid url" };
    }
    await shell.openExternal(url);
    return { ok: true };
  });

  ipcMain.handle("list-briefs", () => listBriefs());
  ipcMain.handle("list-manifests", () => listManifests());
  ipcMain.handle("manifest-meta", (_e, manifestRel) => manifestMeta(manifestRel));

  ipcMain.handle("pipeline-plan", async (_e, opts) => {
    const {
      briefRel,
      manifestRel,
      outputDirRel,
      godotProjectRel,
    } = opts;
    const args = [
      "pipeline",
      "plan",
      "--brief",
      path.join("..", briefRel),
      "-o",
      path.join("..", manifestRel),
      "--output-dir",
      path.join("..", outputDirRel),
      "--godot-project",
      path.join("..", godotProjectRel),
    ];
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("pipeline-status", async (_e, manifestRel) => {
    const result = await runCli([
      "pipeline",
      "status",
      "--manifest",
      path.join("..", manifestRel),
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
      path.join("..", manifestRel),
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

  ipcMain.handle("open-godot", async (_e, projectRel) => {
    const result = await runCli([
      "godot",
      "open",
      "--project",
      path.join("..", projectRel),
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

  ipcMain.handle("host-chat-start", async (_e, sessionId, seed) => {
    const args = ["brief", "chat", "start", "--json", "--session-id", String(sessionId || "").trim()];
    if (seed && String(seed).trim()) {
      args.push("--seed", String(seed).trim());
    }
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("host-chat-turn", async (_e, sessionId, message) => {
    const result = await runCli([
      "brief",
      "chat",
      "turn",
      "--session-id",
      String(sessionId || "").trim(),
      "--message",
      String(message),
      "--json",
    ]);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("host-chat-reset", async (_e, sessionId, seed) => {
    const args = ["brief", "chat", "reset", "--json", "--session-id", String(sessionId || "").trim()];
    if (seed && String(seed).trim()) {
      args.push("--seed", String(seed).trim());
    }
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("host-chat-export", async (_e, sessionId, outputRel) => {
    const result = await runCli([
      "brief",
      "chat",
      "export",
      "--session-id",
      String(sessionId || "").trim(),
      "-o",
      outputRel,
      "--json",
    ]);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

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

  ipcMain.handle("agent-turn", async (event, opts = {}) => {
    const role = String(opts.role || "").trim();
    const sessionId = String(opts.sessionId || "").trim();
    const message = String(opts.message || "");
    const args = [
      "agent",
      "turn",
      "--role",
      role,
      "--session-id",
      sessionId,
      "--message",
      message,
      "--json",
    ];
    if (opts.executor) {
      args.push("--executor", String(opts.executor));
    }
    if (opts.brief) {
      args.push("--brief", String(opts.brief));
    }
    if (opts.progress) {
      args.push("--progress", String(opts.progress));
    }
    if (opts.instanceId) {
      args.push("--instance-id", String(opts.instanceId));
    }
    if (opts.targetInstanceId) {
      args.push("--target-instance-id", String(opts.targetInstanceId));
    }
    if (opts.rosterJson) {
      args.push("--roster-json", String(opts.rosterJson));
    }
    if (opts.timeout) {
      args.push("--timeout", String(opts.timeout));
    }
    const sender = event.sender;
    const result = await runCli(args, {
      onLine: (line, stream) => {
        sender.send("pipeline-log", { line, stream, source: "agent" });
      },
    });
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

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
      args.push("--output", path.join("..", String(opts.output)));
    }
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("production-apply-delta", async (_e, opts = {}) => {
    const args = [
      "production",
      "apply-delta",
      "--delta",
      path.join("..", String(opts.delta || "")),
      "--production",
      path.join("..", String(opts.production || "")),
      "--json",
    ];
    if (opts.progress) {
      args.push("--progress", path.join("..", String(opts.progress)));
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

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
