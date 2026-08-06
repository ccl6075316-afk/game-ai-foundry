/**
 * Cross-platform process-tree kill helpers.
 * On Windows, child.kill() often leaves grandchildren (python/codex trees) alive —
 * use taskkill /T so NSIS upgrades are not blocked by orphaned locks.
 */
import { spawn, spawnSync } from "node:child_process";

/**
 * @param {number | undefined | null} pid
 * @param {{ sync?: boolean }} [opts]
 * @returns {boolean}
 */
export function killPidTree(pid, opts = {}) {
  const id = Number(pid);
  if (!Number.isFinite(id) || id <= 0) return false;
  const sync = Boolean(opts.sync);

  try {
    if (process.platform === "win32") {
      const args = ["/pid", String(id), "/T", "/F"];
      if (sync) {
        spawnSync("taskkill", args, { windowsHide: true, stdio: "ignore" });
      } else {
        spawn("taskkill", args, { windowsHide: true, stdio: "ignore" });
      }
      return true;
    }

    try {
      process.kill(id, "SIGTERM");
    } catch {
      return false;
    }
    if (!sync) {
      setTimeout(() => {
        try {
          process.kill(id, "SIGKILL");
        } catch {
          /* already gone */
        }
      }, 1500);
    } else {
      try {
        process.kill(id, "SIGKILL");
      } catch {
        /* already gone */
      }
    }
    return true;
  } catch {
    return false;
  }
}

/**
 * @param {import('node:child_process').ChildProcess | null | undefined} child
 * @param {{ sync?: boolean }} [opts]
 * @returns {boolean}
 */
export function killChildTree(child, opts = {}) {
  if (!child || child.killed) return false;
  const ok = killPidTree(child.pid, opts);
  if (!ok) {
    try {
      child.kill(process.platform === "win32" ? undefined : "SIGTERM");
      return true;
    } catch {
      return false;
    }
  }
  return true;
}
