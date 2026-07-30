import { useCallback, useEffect, useState } from "react";
import type { AppUpdateStatus } from "../vite-env";

const HIDDEN_PHASES = new Set(["idle", "not-available", "unsupported"]);

export function UpdateBanner() {
  const [status, setStatus] = useState<AppUpdateStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    void window.gameFactory?.appUpdateStatus?.().then((s) => {
      if (!cancelled) setStatus(s);
    });
    const off = window.gameFactory?.onAppUpdateStatus?.((s) => setStatus(s));
    return () => {
      cancelled = true;
      off?.();
    };
  }, []);

  const onInstall = useCallback(() => {
    void window.gameFactory?.appUpdateInstall?.();
  }, []);

  if (!status || HIDDEN_PHASES.has(status.phase)) return null;

  const busy =
    status.phase === "checking" ||
    status.phase === "available" ||
    status.phase === "downloading";
  const ready = status.phase === "downloaded";
  const isError = status.phase === "error";

  return (
    <div
      className={
        "update-banner" +
        (ready ? " update-banner--ready" : "") +
        (isError ? " update-banner--error" : "")
      }
      role="status"
    >
      <span className="update-banner__text">
        {status.message ||
          (ready
            ? `v${status.availableVersion || ""} 已就绪`
            : busy
              ? "检查 / 下载更新中…"
              : "更新")}
        {status.phase === "downloading" && typeof status.percent === "number"
          ? ` · ${status.percent.toFixed(0)}%`
          : ""}
      </span>
      {ready ? (
        <button type="button" className="btn btn--primary btn--sm" onClick={onInstall}>
          重启安装
        </button>
      ) : null}
    </div>
  );
}
