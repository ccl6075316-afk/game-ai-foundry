#!/usr/bin/env node
/**
 * Pin @earendil-works/pi-coding-agent into gui/runtime/pi for Release extraResources.
 * Does not vendor the Pi monorepo — npm install of the published package only.
 */
import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");
const DEFAULT_OUT = path.join(REPO_ROOT, "gui", "runtime", "pi");
const PI_PACKAGE = "@earendil-works/pi-coding-agent";
const PI_VERSION = process.env.PI_EMBED_VERSION || "0.80.10";

function parseArgs(argv) {
  const out = {
    output: DEFAULT_OUT,
    version: PI_VERSION,
    prune: true,
    maxMb: Number(process.env.PI_EMBED_MAX_MB || 100),
    warnMb: Number(process.env.PI_EMBED_WARN_MB || 80),
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--output" && argv[i + 1]) {
      out.output = path.resolve(argv[++i]);
    } else if (a === "--version" && argv[i + 1]) {
      out.version = String(argv[++i]).replace(/^v/, "");
    } else if (a === "--max-mb" && argv[i + 1]) {
      out.maxMb = Number(argv[++i]);
    } else if (a === "--warn-mb" && argv[i + 1]) {
      out.warnMb = Number(argv[++i]);
    } else if (a === "--no-prune") {
      out.prune = false;
    } else if (a === "--help" || a === "-h") {
      console.log(
        `Usage: prepare_embedded_pi.mjs [--output DIR] [--version X.Y.Z] [--max-mb N] [--warn-mb N] [--no-prune]`,
      );
      process.exit(0);
    }
  }
  return out;
}

function dirSizeBytes(root) {
  let total = 0;
  const stack = [root];
  while (stack.length) {
    const cur = stack.pop();
    let entries;
    try {
      entries = readdirSync(cur, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const ent of entries) {
      const p = path.join(cur, ent.name);
      if (ent.isDirectory()) {
        stack.push(p);
      } else if (ent.isFile()) {
        try {
          total += statSync(p).size;
        } catch {
          /* ignore */
        }
      }
    }
  }
  return total;
}

function shouldPruneFile(relPosix, platform) {
  const lower = relPosix.toLowerCase();
  if (lower.endsWith(".map")) return true;
  if (lower.includes("/docs/") || lower.endsWith(".md")) return true;
  if (lower.includes("/test/") || lower.includes("/tests/") || lower.includes("/__tests__/")) {
    return true;
  }
  // Drop native clipboard binaries for other platforms (keep current OS).
  // Only match optional native packages, not source files like clipboard-image.js.
  const nativeClip =
    /(?:^|\/)clipboard-(darwin|linux|win32|android)[^/]*\//.test(lower) ||
    /(?:^|\/)clipboard-(darwin|linux|win32)[^/]*\.(node|dylib|so|dll)$/.test(lower);
  if (nativeClip) {
    if (platform === "win32") {
      return !lower.includes("clipboard-win32");
    }
    if (platform === "darwin") {
      return !(
        lower.includes("clipboard-darwin") || lower.includes("clipboard-darwin-universal")
      );
    }
    if (platform === "linux") {
      return !lower.includes("clipboard-linux");
    }
  }
  return false;
}

function pruneTree(root, platform) {
  let removed = 0;
  const stack = [root];
  while (stack.length) {
    const cur = stack.pop();
    let entries;
    try {
      entries = readdirSync(cur, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const ent of entries) {
      const p = path.join(cur, ent.name);
      const rel = path.relative(root, p).split(path.sep).join("/");
      if (ent.isDirectory()) {
        stack.push(p);
        continue;
      }
      if (shouldPruneFile(rel, platform)) {
        try {
          rmSync(p, { force: true });
          removed += 1;
        } catch {
          /* ignore */
        }
      }
    }
  }
  return removed;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const output = args.output;
  const spec = `${PI_PACKAGE}@${args.version}`;

  console.log(`[pi-embed] Preparing ${spec} → ${output}`);
  if (existsSync(output)) {
    console.log(`[pi-embed] Removing existing ${output}`);
    try {
      rmSync(output, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
    } catch (err) {
      const code = err && typeof err === "object" && "code" in err ? err.code : null;
      if (code === "EPERM" || code === "EBUSY") {
        console.warn(
          `[pi-embed] Could not remove ${output} (${code}); installing in place. Close any node/pi using this tree and retry if needed.`,
        );
      } else {
        throw err;
      }
    }
  }
  mkdirSync(output, { recursive: true });

  const pkg = {
    name: "game-ai-foundry-embedded-pi",
    private: true,
    version: "0.0.0",
    description: "Pinned Pi runtime for Game AI Foundry Release (do not edit by hand)",
  };
  writeFileSync(path.join(output, "package.json"), JSON.stringify(pkg, null, 2) + "\n", "utf8");

  const npmCmd =
    process.platform === "win32"
      ? (spawnSync("where.exe", ["npm.cmd"], { encoding: "utf8" }).stdout || "")
          .split(/\r?\n/)
          .map((s) => s.trim())
          .find(Boolean) || "npm.cmd"
      : "npm";
  const install = spawnSync(
    npmCmd,
    ["install", spec, "--omit=dev", "--no-fund", "--no-audit", "--ignore-scripts"],
    {
      cwd: output,
      stdio: "inherit",
      env: { ...process.env, npm_config_fund: "false" },
    },
  );
  if (install.status !== 0) {
    console.error(`[pi-embed] npm install failed (exit ${install.status})`);
    process.exit(install.status || 1);
  }

  const cliJs = path.join(
    output,
    "node_modules",
    "@earendil-works",
    "pi-coding-agent",
    "dist",
    "cli.js",
  );
  if (!existsSync(cliJs)) {
    console.error(`[pi-embed] Missing entry: ${cliJs}`);
    process.exit(1);
  }

  const before = dirSizeBytes(output);
  let pruned = 0;
  if (args.prune) {
    pruned = pruneTree(output, process.platform);
  }
  const after = dirSizeBytes(output);

  const manifest = {
    package: PI_PACKAGE,
    version: args.version,
    prepared_at: new Date().toISOString(),
    platform: process.platform,
    arch: process.arch,
    entry: "node_modules/@earendil-works/pi-coding-agent/dist/cli.js",
    size_bytes_before_prune: before,
    size_bytes: after,
    pruned_files: pruned,
    size_gate_warn_mb: args.warnMb,
    size_gate_max_mb: args.maxMb,
  };
  writeFileSync(path.join(output, "embed-manifest.json"), JSON.stringify(manifest, null, 2) + "\n");

  const afterMb = after / (1024 * 1024);
  console.log(
    `[pi-embed] OK — ${afterMb.toFixed(1)} MB` +
      (args.prune ? ` (pruned ${pruned} files from ${(before / (1024 * 1024)).toFixed(1)} MB)` : ""),
  );
  console.log(`[pi-embed] entry: ${cliJs}`);

  if (Number.isFinite(args.warnMb) && afterMb > args.warnMb) {
    console.warn(
      `[pi-embed] WARN size ${afterMb.toFixed(1)} MB > warn gate ${args.warnMb} MB (trim providers / prune further)`,
    );
  }
  if (Number.isFinite(args.maxMb) && afterMb > args.maxMb) {
    console.error(
      `[pi-embed] FAIL size ${afterMb.toFixed(1)} MB exceeds max gate ${args.maxMb} MB. ` +
        `Override with --max-mb or PI_EMBED_MAX_MB if intentional.`,
    );
    process.exit(2);
  }
}

main();
