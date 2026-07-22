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
  resolvePiRuntimeRoot,
  resolvePython,
} from "./paths.mjs";
import { createToolPermissionBridge } from "./tool_permission_bridge.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isDev = !isPackagedApp();

/** @type {ReturnType<typeof createToolPermissionBridge> | null} */
let toolPermissionBridge = null;

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

/** Prepend common Node install dirs so CLI can find Node 22+ (Electron PATH often omits them). */
function pathWithCommonNodeBins(basePath) {
  const home = os.homedir();
  const extras = [
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
  return parts.join(path.delimiter);
}

function runCli(args, { cwd, onLine } = {}) {
  const root = repoRoot();
  const python = resolvePython(root);
  const workdir = cwd || cliDir(root);
  const permissionEnv = toolPermissionBridge ? toolPermissionBridge.env() : {};

  return new Promise((resolve, reject) => {
    const proc = spawn(python, ["gamefactory.py", ...args], {
      cwd: workdir,
      env: {
        ...process.env,
        PATH: pathWithCommonNodeBins(process.env.PATH),
        GAMEFACTORY_ROOT: root,
        PYTHONIOENCODING: "utf-8",
        // Electron 39+ ships Node 22.19+ — same runtime as Pi (ELECTRON_RUN_AS_NODE).
        GAMEFACTORY_ELECTRON_EXECUTABLE: process.execPath,
        ...(resolvePiRuntimeRoot()
          ? { GAMEFACTORY_PI_ROOT: resolvePiRuntimeRoot() }
          : {}),
        ...permissionEnv,
      },
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
  const pushFile = (abs, rel, label) => {
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
    if (seen.has(normRel)) return;
    seen.add(normRel);
    const stat = statSync(abs);
    out.push({
      id: normRel.replace(/\.json$/i, "").replace(/[\\/]/g, "__"),
      path: normRel,
      label: label || path.basename(rel),
      mtime: stat.mtimeMs,
    });
  };

  const projectsDir = path.join(root, "projects");
  if (existsSync(projectsDir)) {
    for (const name of readdirSync(projectsDir)) {
      const dir = path.join(projectsDir, name);
      if (!statSync(dir).isDirectory()) continue;
      const brief = path.join(dir, "brief.json");
      const alt = path.join(dir, `${name}-brief.json`);
      if (existsSync(brief)) {
        pushFile(brief, path.join("projects", name, "brief.json"), `${name}/brief.json`);
      } else if (existsSync(alt)) {
        pushFile(alt, path.join("projects", name, `${name}-brief.json`), `${name}/${name}-brief.json`);
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

function resolveRepoRel(relPath) {
  if (!relPath || typeof relPath !== "string") return null;
  const root = path.resolve(repoRoot());
  const normalized = relPath.replace(/\\/g, "/").replace(/^\/+/, "");
  if (!normalized || normalized.includes("..")) return null;
  const full = path.resolve(root, normalized);
  if (full !== root && !full.startsWith(root + path.sep)) return null;
  return { full, rel: normalized };
}

function readRepoText(relPath) {
  const resolved = resolveRepoRel(relPath);
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
  const resolved = resolveRepoRel(relPath);
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
    const resolved = resolveRepoRel(rel);
    if (!resolved || !existsSync(resolved.full) || !statSync(resolved.full).isFile()) return;
    if (out.some((d) => d.path === resolved.rel)) return;
    out.push({ path: resolved.rel, label, kind });
  };

  if (briefRel) {
    const norm = String(briefRel).replace(/\\/g, "/");
    const projMatch = norm.match(/^(projects\/[^/]+)\//i);
    const slug = projMatch
      ? projMatch[1].split("/")[1]
      : path.basename(norm).replace(/\.json$/i, "").replace(/-brief$/i, "") || "game";

    pushIfExists(norm, `Brief · ${slug}`, "json");
    if (projMatch) {
      const root = projMatch[1];
      pushIfExists(`${root}/production.json`, "Production", "json");
      pushIfExists(`${root}/progress.json`, "Progress", "json");
      pushIfExists(`${root}/pipeline/manifest.json`, "Pipeline manifest", "json");
      // Project-local notes / GDD sitting next to brief (not under output/)
      const rootAbs = path.join(repoRoot(), root);
      if (existsSync(rootAbs) && statSync(rootAbs).isDirectory()) {
        for (const f of readdirSync(rootAbs)) {
          if (!/\.(md|txt)$/i.test(f)) continue;
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

  // No active project — only list recent briefs so the user can pick one.
  for (const b of listBriefs().slice(0, 12)) {
    pushIfExists(b.path, `Brief · ${b.label}`, "json");
  }
  return out;
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
        const tAbs = path.join(root, target);
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
 * Prefer projects/<slug>/ after migrate; follow redirect stubs. */
function resolveBriefRel(briefRel) {
  const root = repoRoot();
  const raw = String(briefRel || "")
    .replace(/\\/g, "/")
    .replace(/^\.\.\//, "")
    .replace(/^\.\//, "");
  if (!raw) return "";
  const base = path.basename(raw);
  const candidates = [];
  const push = (c) => {
    const n = String(c || "").replace(/\\/g, "/");
    if (n && !candidates.includes(n)) candidates.push(n);
  };

  // 1) Prefer isolated projects/ first (by slug / stem)
  const stem = base.replace(/\.json$/i, "").replace(/-brief$/i, "");
  if (stem) {
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
  push(`resources/${base}`);
  push(`cli/resources/${base}`);

  // Scan projects/*/brief.json for migrated_from / legacy_names
  const projectsDir = path.join(root, "projects");
  if (existsSync(projectsDir)) {
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
            migrated.endsWith(base) ||
            migrated === raw ||
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
  return path.join("..", resolveBriefRel(briefRel));
}

function looksLikeImagePath(ref) {
  const s = String(ref || "").trim().replace(/\\/g, "/");
  if (!s || s.length > 400 || s.includes("://")) return false;
  return /\.(png|jpe?g|webp|gif)$/i.test(s);
}

/** Find newest pipeline manifest whose brief matches (path or basename). */
function findManifestForBrief(briefRel) {
  const key = normalizeBriefKey(briefRel);
  if (!key) return null;
  const base = path.basename(key);
  for (const item of listManifests()) {
    const meta = manifestMeta(item.path);
    if (!meta?.brief) continue;
    const mb = normalizeBriefKey(meta.brief);
    if (mb === key || mb.endsWith("/" + base) || path.basename(mb) === base) {
      return { path: item.path, label: item.label, mtime: item.mtime, meta };
    }
  }
  return null;
}

function loadManifest(relPath) {
  const full = path.join(repoRoot(), relPath);
  const data = JSON.parse(readFileSync(full, "utf-8"));
  // Follow migrate pointer
  if (data?.migrated_to && !data?.tasks) {
    const next = String(data.migrated_to).replace(/\\/g, "/");
    return JSON.parse(readFileSync(path.join(repoRoot(), next), "utf-8"));
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

function relToRepo(absPath) {
  const root = repoRoot();
  const rel = path.relative(root, absPath);
  return rel.split(path.sep).join("/");
}

/** Resolve image/video path for preview/open. Accepts repo-relative or absolute. */
function resolveMediaAbs(relOrAbs) {
  const root = path.resolve(repoRoot());
  const raw = String(relOrAbs || "").trim();
  if (!raw) return null;

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
    push(path.join(root, rel));
    // Gallery sometimes truncated projects/<slug>/output/... → output/...
    if (rel.startsWith("output/") || rel.startsWith("plans/") || rel.startsWith("games/")) {
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
    }
  }

  for (const candidate of candidates) {
    if (!existsSync(candidate) || !statSync(candidate).isFile()) continue;
    const rel = path.relative(root, candidate);
    if (rel.startsWith("..") || path.isAbsolute(rel)) continue;
    return candidate;
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
    await shell.openExternal(url);
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
  ipcMain.handle("list-project-docs", (_e, briefRel) => listProjectDocs(briefRel));

  ipcMain.handle("pipeline-plan", async (_e, opts) => {
    const {
      briefRel,
      manifestRel,
      outputDirRel,
      godotProjectRel,
      plansDirRel,
    } = opts;
    const briefResolved = resolveBriefRel(briefRel);
    const args = [
      "pipeline",
      "plan",
      "--brief",
      path.join("..", briefResolved),
      "-o",
      path.join("..", manifestRel),
      "--output-dir",
      path.join("..", outputDirRel),
      "--godot-project",
      path.join("..", godotProjectRel),
    ];
    if (plansDirRel) {
      args.push("--plans-dir", path.join("..", plansDirRel));
    }
    // Ensure parent dirs exist for isolated projects
    for (const rel of [manifestRel, outputDirRel, godotProjectRel, plansDirRel]) {
      if (!rel) continue;
      const abs = path.join(repoRoot(), rel);
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

  ipcMain.handle("pipeline-diagnose", async (_e, manifestRel) => {
    const result = await runCli([
      "pipeline",
      "diagnose",
      "--manifest",
      path.join("..", manifestRel),
    ]);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("pipeline-heal", async (_e, manifestRel, apply = true) => {
    const args = [
      "pipeline",
      "heal",
      "--manifest",
      path.join("..", manifestRel),
      apply ? "--apply" : "--dry-run",
    ];
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("resolve-brief-rel", (_e, briefRel) => {
    const resolved = resolveBriefRel(briefRel);
    const abs = resolved ? path.join(repoRoot(), resolved) : "";
    return {
      input: String(briefRel || "").replace(/\\/g, "/"),
      path: resolved,
      exists: Boolean(resolved && existsSync(abs)),
    };
  });

  ipcMain.handle("visual-target-generate", async (event, briefRel, candidates) => {
    const sender = event.sender;
    const n = Math.max(1, Math.min(4, Number(candidates) || 3));
    const result = await runCli(
      [
        "brief",
        "visual-target",
        "generate",
        "--brief",
        briefCliArg(briefRel),
        "--candidates",
        String(n),
        "--json",
      ],
      {
        onLine: (line, stream) => {
          sender.send("pipeline-log", { line, stream });
        },
      },
    );
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("visual-target-list", async (_e, briefRel) => {
    const result = await runCli([
      "brief",
      "visual-target",
      "list",
      "--brief",
      briefCliArg(briefRel),
      "--json",
    ]);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("visual-target-pick", async (_e, briefRel, candidateId) => {
    const result = await runCli([
      "brief",
      "visual-target",
      "pick",
      "--brief",
      briefCliArg(briefRel),
      "--id",
      String(candidateId || "").trim(),
      "--json",
    ]);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("visual-target-status", (_e, briefRel) => {
    const root = repoRoot();
    const rel = resolveBriefRel(briefRel);
    if (!rel) {
      return { ok: false, ready: false, visual_reference: "", candidates: [] };
    }
    const briefAbs = path.join(root, rel);
    if (!existsSync(briefAbs)) {
      return {
        ok: false,
        ready: false,
        visual_reference: "",
        candidates: [],
        error: `brief not found: ${rel}`,
        brief_rel: rel,
      };
    }
    let visualReference = "";
    try {
      const data = JSON.parse(readFileSync(briefAbs, "utf-8"));
      visualReference = String(data?.project?.visual_reference || "").trim();
    } catch {
      return {
        ok: false,
        ready: false,
        visual_reference: "",
        candidates: [],
        error: "brief unreadable",
        brief_rel: rel,
      };
    }
    const pathOk = looksLikeImagePath(visualReference);
    let fileOk = false;
    if (pathOk) {
      const abs = path.isAbsolute(visualReference)
        ? visualReference
        : path.join(root, visualReference);
      fileOk = existsSync(abs) && statSync(abs).isFile();
    }
    const candidates = [];
    // Prefer manifest next to selected.png under common VT output dirs
    const tryManifests = [];
    if (rel.startsWith("projects/")) {
      const slug = rel.split("/")[1];
      tryManifests.push(path.join(root, "projects", slug, "output", "visual-target", "manifest.json"));
    }
    const stem = path.basename(rel).replace(/\.json$/i, "");
    tryManifests.push(path.join(root, "output", stem, "visual-target", "manifest.json"));
    // Title-slug folders are unknown here; also scan output/*/visual-target/manifest.json lightly
    const outputRoot = path.join(root, "output");
    if (existsSync(outputRoot)) {
      try {
        for (const name of readdirSync(outputRoot)) {
          const m = path.join(outputRoot, name, "visual-target", "manifest.json");
          if (existsSync(m)) tryManifests.push(m);
        }
      } catch {
        /* ignore */
      }
    }
    let selectedId = null;
    const seen = new Set();
    for (const mPath of tryManifests) {
      if (!existsSync(mPath) || seen.has(mPath)) continue;
      seen.add(mPath);
      try {
        const man = JSON.parse(readFileSync(mPath, "utf-8"));
        const briefInMan = String(man.brief_path || "").replace(/\\/g, "/");
        const briefNorm = briefAbs.replace(/\\/g, "/");
        if (briefInMan && !briefInMan.includes(path.basename(briefAbs)) && briefInMan !== briefNorm) {
          // keep scanning; weak match on basename below
        }
        selectedId = man.selected_id || selectedId;
        for (const c of man.candidates || []) {
          if (!c || !c.id) continue;
          const cAbs = String(c.path || "");
          const cRel = cAbs
            ? path.relative(root, path.isAbsolute(cAbs) ? cAbs : path.join(root, cAbs)).replace(/\\/g, "/")
            : "";
          candidates.push({
            id: String(c.id),
            label: c.label || c.id,
            path: cRel || cAbs,
            status: c.status,
          });
        }
        if (candidates.length) break;
      } catch {
        /* ignore */
      }
    }
    return {
      ok: true,
      ready: Boolean(pathOk && fileOk),
      visual_reference: visualReference,
      path_shaped: pathOk,
      file_ok: fileOk,
      selected_id: selectedId,
      candidates,
    };
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

  ipcMain.handle("host-chat-start", async (_e, sessionId, seed, _instanceId) => {
    const args = ["brief", "chat", "start", "--json", "--session-id", String(sessionId || "").trim()];
    if (seed && String(seed).trim()) {
      args.push("--seed", String(seed).trim());
    }
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("host-chat-turn", async (_e, sessionId, message, instanceId) => {
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
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("host-chat-reset", async (_e, sessionId, seed, _instanceId) => {
    const args = ["brief", "chat", "reset", "--json", "--session-id", String(sessionId || "").trim()];
    if (seed && String(seed).trim()) {
      args.push("--seed", String(seed).trim());
    }
    const result = await runCli(args);
    return { ...result, data: parseJsonFromOutput(result.stdout) };
  });

  ipcMain.handle("host-chat-export", async (_e, sessionId, outputRel, _instanceId) => {
    // CLI cwd is cli/ — write into repo via ../projects/... (not cli/resources/)
    const rel = String(outputRel || "").replace(/\\/g, "/").replace(/^\.\.\//, "");
    const abs = path.join(repoRoot(), rel);
    mkdirSync(path.dirname(abs), { recursive: true });
    const args = [
      "brief",
      "chat",
      "export",
      "--session-id",
      String(sessionId || "").trim(),
      "-o",
      path.join("..", rel),
      "--json",
    ];
    const result = await runCli(args);
    const data = parseJsonFromOutput(result.stdout) || {};
    if (!data.brief_path) data.brief_path = abs;
    data.brief_rel = rel;
    return { ...result, data };
  });

  ipcMain.handle("host-chat-autofix", async (_e, sessionId, maxRounds = 5, _instanceId) => {
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
    const result = await runCli(args);
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
      const b = String(opts.brief).replace(/\\/g, "/").replace(/^\.\.\//, "");
      args.push("--brief", path.join("..", b));
    }
    if (opts.progress) {
      const p = String(opts.progress).replace(/\\/g, "/").replace(/^\.\.\//, "");
      args.push("--progress", path.join("..", p));
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

  ipcMain.handle("agent-tool-permission-decision", async (_e, permissionId, decision) => {
    if (!toolPermissionBridge) return { ok: false };
    const ok = toolPermissionBridge.decide(permissionId, decision);
    return { ok };
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
  toolPermissionBridge?.close();
  toolPermissionBridge = null;
  if (process.platform !== "darwin") app.quit();
});
