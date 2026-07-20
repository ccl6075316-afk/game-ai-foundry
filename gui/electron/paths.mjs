import { app } from "electron";
import { cpSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function devRepoRoot() {
  if (process.env.GAMEFACTORY_ROOT && existsSync(process.env.GAMEFACTORY_ROOT)) {
    return path.resolve(process.env.GAMEFACTORY_ROOT);
  }
  return path.resolve(__dirname, "..", "..");
}

function bundledFactoryRoot() {
  return path.join(process.resourcesPath, "gamefactory");
}

function embeddedPythonCandidates() {
  const base = path.join(process.resourcesPath, "python");
  if (process.platform === "win32") {
    return [path.join(base, "python.exe")];
  }
  return [path.join(base, "bin", "python3"), path.join(base, "bin", "python")];
}

function embeddedPiRootCandidates() {
  return [
    path.join(process.resourcesPath, "pi"),
    path.join(__dirname, "..", "runtime", "pi"),
  ];
}

export function resolvePiRuntimeRoot() {
  const env = process.env.GAMEFACTORY_PI_ROOT;
  if (env && existsSync(path.join(env, "node_modules", "@earendil-works", "pi-coding-agent", "dist", "cli.js"))) {
    return path.resolve(env);
  }
  for (const base of embeddedPiRootCandidates()) {
    const entry = path.join(base, "node_modules", "@earendil-works", "pi-coding-agent", "dist", "cli.js");
    if (existsSync(entry)) return path.resolve(base);
  }
  return null;
}

/** Path to Pi CLI entry (cli.js). Caller runs via Node or ELECTRON_RUN_AS_NODE. */
export function resolvePiCliJs() {
  const root = resolvePiRuntimeRoot();
  if (!root) return null;
  const entry = path.join(root, "node_modules", "@earendil-works", "pi-coding-agent", "dist", "cli.js");
  return existsSync(entry) ? entry : null;
}

function workspaceCandidates() {
  if (process.env.PORTABLE_EXECUTABLE_DIR) {
    return [path.join(process.env.PORTABLE_EXECUTABLE_DIR, "data")];
  }
  if (process.env.GAMEFACTORY_WORKSPACE) {
    return [path.resolve(process.env.GAMEFACTORY_WORKSPACE)];
  }
  return [path.join(app.getPath("userData"), "workspace")];
}

function seedWorkspace(root) {
  const bundled = bundledFactoryRoot();
  mkdirSync(root, { recursive: true });

  for (const dir of ["output", "games", "pipeline", "plans"]) {
    mkdirSync(path.join(root, dir), { recursive: true });
  }

  const versionFile = path.join(root, ".app-seed-version");
  const appVersion = app.getVersion();
  const needsReseed =
    !existsSync(versionFile) || readFileSync(versionFile, "utf-8").trim() !== appVersion;

  const cliDest = path.join(root, "cli");
  const bundledCli = path.join(bundled, "cli");
  if (existsSync(bundledCli) && (!existsSync(cliDest) || needsReseed)) {
    cpSync(bundledCli, cliDest, { recursive: true });
  }

  const resDest = path.join(root, "resources");
  const bundledRes = path.join(bundled, "resources");
  if (existsSync(bundledRes)) {
    mkdirSync(resDest, { recursive: true });
    if (!existsSync(path.join(resDest, "config.example.json"))) {
      cpSync(bundledRes, resDest, { recursive: true });
    } else if (needsReseed) {
      for (const name of ["config.example.json", "asset-brief.example.json", "agents.example.json"]) {
        const src = path.join(bundledRes, name);
        if (existsSync(src)) {
          cpSync(src, path.join(resDest, name));
        }
      }
      const skillsSrc = path.join(bundledRes, "skills");
      const skillsDest = path.join(resDest, "skills");
      if (existsSync(skillsSrc)) {
        cpSync(skillsSrc, skillsDest, { recursive: true });
      }
    }
  }

  if (needsReseed) {
    writeFileSync(versionFile, `${appVersion}\n`, "utf-8");
  }
}

export function isPackagedApp() {
  return app.isPackaged;
}

export function repoRoot() {
  if (!app.isPackaged) {
    return devRepoRoot();
  }
  for (const candidate of workspaceCandidates()) {
    seedWorkspace(candidate);
    return candidate;
  }
  const fallback = path.join(app.getPath("userData"), "workspace");
  seedWorkspace(fallback);
  return fallback;
}

export function cliDir(root = repoRoot()) {
  return path.join(root, "cli");
}

export function resolvePython(root = repoRoot()) {
  if (app.isPackaged) {
    for (const candidate of embeddedPythonCandidates()) {
      if (existsSync(candidate)) return candidate;
    }
  }

  const winVenv = path.join(root, ".venv", "Scripts", "python.exe");
  const unixVenv = path.join(root, ".venv", "bin", "python");
  if (existsSync(winVenv)) return winVenv;

  const devRuntime =
    process.platform === "win32"
      ? path.join(__dirname, "..", "runtime", "python", "python.exe")
      : path.join(__dirname, "..", "runtime", "python", "bin", "python3");
  if (existsSync(devRuntime)) return path.resolve(devRuntime);

  if (existsSync(unixVenv)) return unixVenv;
  return process.env.PYTHON || "python";
}

export function preloadPath() {
  return path.join(__dirname, "preload.cjs");
}

export function rendererIndexPath() {
  return path.join(__dirname, "..", "dist", "index.html");
}
