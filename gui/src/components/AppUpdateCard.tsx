import { useCallback, useEffect, useState } from "react";
import type { AppUpdateStatus } from "../vite-env";

export function AppUpdateCard({ disabled }: { disabled?: boolean }) {
  const [status, setStatus] = useState<AppUpdateStatus | null>(null);
  const [busy, setBusy] = useState(false);

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

  const check = useCallback(async () => {
    setBusy(true);
    try {
      const s = await window.gameFactory?.appUpdateCheck?.();
      if (s) setStatus(s);
    } finally {
      setBusy(false);
    }
  }, []);

  const install = useCallback(() => {
    void window.gameFactory?.appUpdateInstall?.();
  }, []);

  const version = status?.currentVersion || "—";
  const phase = status?.phase || "idle";

  return (
    <div className="settings-card settings-card--compact">
      <div className="settings-card__head">
        <div className="settings-card__title-row">
          <h3 className="settings-card__title">应用更新</h3>
          <span className="settings-card__status">{`v${version}`}</span>
        </div>
        <p className="settings-card__purpose">
          自动更新仅支持 Windows <code>*-setup.exe</code>（可选安装目录、卸载卸干净）。macOS / zip /
          portable 请到 GitHub Releases 手动换包。
        </p>
      </div>
      <div className="settings-card__body">
        <p className="hint" style={{ margin: 0 }}>
          {status?.message ||
            (phase === "unsupported"
              ? "当前环境不支持自动更新"
              : "启动约 12 秒后会自动检查；也可手动检查。")}
        </p>
        {phase === "downloading" && typeof status?.percent === "number" ? (
          <div className="update-progress" aria-hidden>
            <div className="update-progress__bar" style={{ width: `${status.percent}%` }} />
          </div>
        ) : null}
        <div className="settings-actions" style={{ justifyContent: "flex-start", paddingTop: 8 }}>
          <button
            type="button"
            className="btn btn--secondary"
            disabled={
              disabled || busy || phase === "downloading" || phase === "unsupported"
            }
            onClick={() => void check()}
          >
            {busy || phase === "checking" ? "检查中…" : "检查更新"}
          </button>
          {phase === "downloaded" ? (
            <button type="button" className="btn btn--primary" disabled={disabled} onClick={install}>
              重启并安装 v{status?.availableVersion || ""}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
