/**
 * Auto-update policy (product decision):
 * - Windows NSIS install (`*-setup.exe`): electron-updater + GitHub Releases
 * - Windows zip / portable, macOS, Linux: manual download only (no Apple notarization yet)
 */
import { app, ipcMain } from "electron";
import { autoUpdater } from "electron-updater";
import { isPackagedApp } from "./paths.mjs";

/** @typedef {"idle"|"checking"|"available"|"not-available"|"downloading"|"downloaded"|"error"|"unsupported"} UpdatePhase */

/** @type {{
 *   phase: UpdatePhase,
 *   currentVersion: string,
 *   availableVersion?: string,
 *   percent?: number,
 *   message?: string,
 *   releaseName?: string,
 *   releaseNotes?: string,
 *   error?: string,
 * }} */
let state = {
  phase: "idle",
  currentVersion: app.getVersion(),
};

/** @type {import("electron").BrowserWindow | null} */
let targetWindow = null;
let wired = false;
let startTimer = null;

function pushState(patch = {}) {
  state = { ...state, currentVersion: app.getVersion(), ...patch };
  if (targetWindow && !targetWindow.isDestroyed()) {
    targetWindow.webContents.send("app-update-status", state);
  }
  return state;
}

/** @returns {{ ok: boolean, message: string }} */
function autoUpdateEligibility() {
  if (!isPackagedApp()) {
    return { ok: false, message: "开发模式不检查更新" };
  }
  if (process.platform !== "win32") {
    return {
      ok: false,
      message:
        "macOS / Linux 请到 GitHub Releases 手动下载新包替换（暂不提供应用内自动更新；Mac 签名公证需付费开发者账号）",
    };
  }
  if (process.env.PORTABLE_EXECUTABLE_DIR) {
    return {
      ok: false,
      message: "portable 版不支持自动更新，请改用 Windows「*-setup.exe」安装版",
    };
  }
  return { ok: true, message: "" };
}

function wireUpdaterEvents() {
  if (wired) return;
  wired = true;

  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;
  autoUpdater.allowPrerelease = false;

  autoUpdater.on("checking-for-update", () => {
    pushState({ phase: "checking", message: "正在检查更新…", error: undefined });
  });

  autoUpdater.on("update-available", (info) => {
    pushState({
      phase: "available",
      availableVersion: info?.version,
      releaseName: info?.releaseName || info?.version,
      releaseNotes: typeof info?.releaseNotes === "string" ? info.releaseNotes : undefined,
      message: `发现新版本 ${info?.version || ""}，开始下载…`,
      error: undefined,
    });
  });

  autoUpdater.on("update-not-available", (info) => {
    pushState({
      phase: "not-available",
      availableVersion: info?.version || app.getVersion(),
      message: "已是最新版本",
      error: undefined,
    });
  });

  autoUpdater.on("download-progress", (p) => {
    const percent = Math.max(0, Math.min(100, Number(p?.percent) || 0));
    pushState({
      phase: "downloading",
      percent,
      message: `下载中 ${percent.toFixed(0)}%`,
      error: undefined,
    });
  });

  autoUpdater.on("update-downloaded", (info) => {
    pushState({
      phase: "downloaded",
      availableVersion: info?.version,
      releaseName: info?.releaseName || info?.version,
      percent: 100,
      message: `v${info?.version || ""} 已下载，重启后安装`,
      error: undefined,
    });
  });

  autoUpdater.on("error", (err) => {
    const raw = err instanceof Error ? err.message : String(err || "update error");
    const friendly = /zip|portable|No published versions|Cannot find channel|404|latest\.yml/i.test(raw)
      ? "自动更新失败。请确认使用的是 Windows「*-setup.exe」安装版，或到 GitHub Releases 手动下载。"
      : raw;
    pushState({
      phase: "error",
      error: friendly,
      message: friendly,
    });
  });
}

/**
 * @param {() => import("electron").BrowserWindow | null} getWindow
 */
export function initAutoUpdate(getWindow) {
  const win = getWindow?.() || null;
  targetWindow = win;

  const gate = autoUpdateEligibility();
  if (!gate.ok) {
    pushState({ phase: "unsupported", message: gate.message });
    return;
  }

  wireUpdaterEvents();

  if (startTimer) clearTimeout(startTimer);
  startTimer = setTimeout(() => {
    void checkForUpdates({ silent: true });
  }, 12_000);
}

export function getUpdateState() {
  return { ...state, currentVersion: app.getVersion() };
}

/**
 * @param {{ silent?: boolean }} [opts]
 */
export async function checkForUpdates(opts = {}) {
  const gate = autoUpdateEligibility();
  if (!gate.ok) {
    return pushState({ phase: "unsupported", message: gate.message });
  }
  wireUpdaterEvents();
  try {
    if (!opts.silent) {
      pushState({ phase: "checking", message: "正在检查更新…", error: undefined });
    }
    await autoUpdater.checkForUpdates();
    return getUpdateState();
  } catch (e) {
    const raw = e instanceof Error ? e.message : String(e);
    return pushState({
      phase: "error",
      error: raw,
      message: raw,
    });
  }
}

export function quitAndInstallUpdate() {
  if (state.phase !== "downloaded") {
    return { ok: false, error: "尚未下载完成" };
  }
  setImmediate(() => {
    autoUpdater.quitAndInstall(false, true);
  });
  return { ok: true };
}

export function registerAutoUpdateIpc() {
  ipcMain.handle("app-update-status", () => getUpdateState());
  ipcMain.handle("app-update-check", async () => checkForUpdates({ silent: false }));
  ipcMain.handle("app-update-install", () => quitAndInstallUpdate());
}
