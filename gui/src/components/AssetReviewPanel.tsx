import { useCallback, useEffect, useMemo, useState } from "react";
import type { AssetReviewRow } from "../vite-env.d";

type ReviewStatusFilter = "all" | "pending" | "accepted" | "replaced";

interface Props {
  assetsManifestRel: string | null;
  pipelineManifestRel: string | null;
  busy: boolean;
  onOpenBoard?: () => void;
  onAfterRegenerate?: () => void;
}

const STATUS_LABEL: Record<AssetReviewRow["review"]["status"], string> = {
  pending: "待审",
  accepted: "已采纳",
  replaced: "已替换",
};

function statusClass(status: AssetReviewRow["review"]["status"]): string {
  if (status === "accepted") return "status-done";
  if (status === "replaced") return "status-running";
  return "status-pending";
}

function Thumb({
  pathRepo,
  updatedAt,
  className,
}: {
  pathRepo: string | null;
  updatedAt?: string;
  className?: string;
}) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setUrl(null);
    if (!pathRepo || !window.gameFactory?.getMediaPreview) return;
    void window.gameFactory
      .getMediaPreview(pathRepo)
      .then((res) => {
        if (cancelled) return;
        setUrl(res?.previewUrl || res?.posterUrl || null);
      })
      .catch(() => {
        if (!cancelled) setUrl(null);
      });
    return () => {
      cancelled = true;
    };
  }, [pathRepo, updatedAt]);

  if (!pathRepo) {
    return <div className={`asset-review-thumb asset-review-thumb--empty ${className || ""}`}>无图</div>;
  }
  if (!url) {
    return <div className={`asset-review-thumb asset-review-thumb--empty ${className || ""}`}>…</div>;
  }
  return (
    <img
      className={`asset-review-thumb ${className || ""}`}
      src={url}
      alt=""
      loading="lazy"
    />
  );
}

export function AssetReviewPanel({
  assetsManifestRel,
  pipelineManifestRel,
  busy,
  onOpenBoard,
  onAfterRegenerate,
}: Props) {
  const [rows, setRows] = useState<AssetReviewRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<ReviewStatusFilter>("all");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  /** Path IPC actually used when list succeeds via pipeline resolve */
  const [listedManifest, setListedManifest] = useState<string | null>(null);

  const canRegenerate = Boolean(pipelineManifestRel?.trim());
  const panelBusy = busy || loading || actionBusy;
  const manifestForMutations = assetsManifestRel || listedManifest;

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (!window.gameFactory?.assetsReviewList) {
        setRows([]);
        setListedManifest(null);
        setError("资产审查 API 不可用（请重启应用）");
        return;
      }
      const res = await window.gameFactory.assetsReviewList(
        assetsManifestRel,
        pipelineManifestRel,
      );
      const next = res.data?.rows || [];
      setRows(next);
      if (res.exitCode !== 0 && next.length === 0) {
        setError(res.stderr?.trim() || "未能加载 assets-manifest（请先跑完 pipeline）");
        setListedManifest(null);
        return;
      }
      setError(null);
      if (assetsManifestRel) {
        setListedManifest(assetsManifestRel);
        return;
      }
      if (pipelineManifestRel) {
        try {
          const meta = await window.gameFactory.getManifestMeta(pipelineManifestRel);
          const out = String(meta?.output_dir || "")
            .replace(/\\/g, "/")
            .replace(/\/$/, "");
          setListedManifest(out ? `${out}/assets-manifest.json` : null);
        } catch {
          setListedManifest(null);
        }
      } else {
        setListedManifest(null);
      }
    } catch (e) {
      setRows([]);
      setListedManifest(null);
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [assetsManifestRel, pipelineManifestRel]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return rows.filter((row) => {
      if (filter !== "all" && row.review?.status !== filter) return false;
      if (!q) return true;
      const hay =
        `${row.label} ${row.asset_name} ${row.kit_item_slug || ""} ${row.usage || ""} ${row.type || ""}`.toLowerCase();
      return hay.includes(q);
    });
  }, [rows, filter, search]);

  useEffect(() => {
    if (selectedId && filtered.some((r) => r.row_id === selectedId)) return;
    setSelectedId(filtered[0]?.row_id ?? null);
  }, [filtered, selectedId]);

  const selected = filtered.find((r) => r.row_id === selectedId) || null;

  const accept = async () => {
    if (!selected || !manifestForMutations) return;
    setActionBusy(true);
    setError(null);
    try {
      const res = await window.gameFactory.assetsReviewAccept(
        manifestForMutations,
        selected.asset_name,
        selected.kit_item_slug ?? null,
      );
      if (res.exitCode !== 0) {
        setError(res.stderr?.trim() || "采纳失败");
      }
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setActionBusy(false);
    }
  };

  const replaceLocal = async () => {
    if (!selected || !manifestForMutations) return;
    setActionBusy(true);
    setError(null);
    try {
      const picked = await window.gameFactory.pickFile({
        title: "选择本地图片替换交付物",
        filters: [{ name: "Images", extensions: ["png", "webp", "jpg", "jpeg"] }],
      });
      if (!picked) return;
      const res = await window.gameFactory.assetsReviewReplace(
        manifestForMutations,
        selected.asset_name,
        selected.kit_item_slug ?? null,
        picked,
      );
      if (res.exitCode !== 0) {
        setError(res.stderr?.trim() || "本地替换失败");
      }
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setActionBusy(false);
    }
  };

  const regenerate = async () => {
    if (!selected || !pipelineManifestRel) return;
    const ok = window.confirm(
      `重生成「${selected.label}」？\n将 cascade 重置相关 image.generate 任务并重新跑 pipeline。`,
    );
    if (!ok) return;
    setActionBusy(true);
    setError(null);
    try {
      const res = await window.gameFactory.assetsReviewRegenerate(
        pipelineManifestRel,
        selected.asset_name,
        selected.kit_item_slug ?? null,
        4,
      );
      if (res.exitCode !== 0) {
        setError(res.stderr?.trim() || "重生成失败");
      }
      await refresh();
      onAfterRegenerate?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setActionBusy(false);
    }
  };

  const openPath = (rel: string | null) => {
    if (!rel) return;
    void window.gameFactory.openMedia(rel);
  };

  return (
    <aside className="side-panel board-panel asset-review-panel">
      <div className="side-panel__head board-head">
        <h2>资产</h2>
        <p className="hint">审查缩略图与 usage 映射；采纳 / 替换 / 重生成（软标注，不挡流水线）</p>
      </div>

      <div className={`board-meta mono ${manifestForMutations ? "board-meta--ready" : ""}`}>
        {manifestForMutations || "（未找到 assets-manifest — 先跑 pipeline）"}
      </div>

      <div className="board-actions">
        <button type="button" className="btn btn--secondary" onClick={() => void refresh()} disabled={panelBusy}>
          刷新
        </button>
        {onOpenBoard && (
          <button type="button" className="btn btn--ghost" onClick={onOpenBoard} disabled={panelBusy}>
            看板
          </button>
        )}
      </div>

      <div className="asset-review-filters">
        {(
          [
            ["all", "全部"],
            ["pending", "待审"],
            ["accepted", "已采纳"],
            ["replaced", "已替换"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`composer__chip ${filter === id ? "composer__chip--primary" : ""}`}
            onClick={() => setFilter(id)}
          >
            {label}
          </button>
        ))}
      </div>

      <input
        className="asset-review-search"
        type="search"
        placeholder="搜索名称 / id / usage…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {error && <p className="hint asset-review-error">{error}</p>}

      {!manifestForMutations && !loading && (
        <p className="brief-draft-empty">尚无 assets-manifest。请先生成流水线并运行资产生成。</p>
      )}

      <div className="asset-review-list">
        {filtered.map((row) => (
          <button
            key={row.row_id}
            type="button"
            className={`asset-review-row ${selectedId === row.row_id ? "is-active" : ""}`}
            onClick={() => setSelectedId(row.row_id)}
          >
            <Thumb
              key={`${row.preview_path_repo || ""}:${row.review?.updated_at || ""}`}
              pathRepo={row.preview_path_repo}
              updatedAt={row.review?.updated_at}
            />
            <div className="asset-review-row__body">
              <span className="asset-review-row__title">{row.label}</span>
              <span className="asset-review-row__meta">
                {row.type || "—"}
                {row.usage ? ` · ${row.usage}` : ""}
              </span>
            </div>
            <span className={`style-chip ${statusClass(row.review?.status || "pending")}`}>
              {STATUS_LABEL[row.review?.status || "pending"]}
            </span>
          </button>
        ))}
        {manifestForMutations && !loading && filtered.length === 0 && (
          <p className="brief-draft-empty">没有匹配的资产行。</p>
        )}
      </div>

      {selected && (
        <div className="asset-review-detail">
          <h3>{selected.label}</h3>
          <Thumb
            key={`${selected.preview_path_repo || ""}:${selected.review?.updated_at || ""}`}
            pathRepo={selected.preview_path_repo}
            updatedAt={selected.review?.updated_at}
            className="asset-review-thumb--lg"
          />
          <dl className="asset-review-dl">
            <div>
              <dt>id</dt>
              <dd className="mono">{selected.row_id}</dd>
            </div>
            <div>
              <dt>type / usage</dt>
              <dd>
                {selected.type || "—"}
                {selected.usage ? ` · ${selected.usage}` : ""}
              </dd>
            </div>
            <div>
              <dt>状态</dt>
              <dd>
                {STATUS_LABEL[selected.review?.status || "pending"]}
                {selected.review?.source ? ` · ${selected.review.source}` : ""}
              </dd>
            </div>
            <div>
              <dt>路径</dt>
              <dd className="mono">
                {selected.canonical_path_repo || "—"}
                {selected.canonical_path_repo && (
                  <>
                    {" "}
                    <button
                      type="button"
                      className="btn btn--ghost"
                      onClick={() => openPath(selected.canonical_path_repo)}
                    >
                      打开
                    </button>
                  </>
                )}
              </dd>
            </div>
            {selected.stages_summary && (
              <div>
                <dt>stages</dt>
                <dd className="mono">{selected.stages_summary}</dd>
              </div>
            )}
          </dl>
          <p className="hint">
            本地替换会覆盖当前交付物路径；若只换 nobg、raw 仍旧，后续从 raw 重跑可能冲掉替换。
          </p>
          <div className="board-actions asset-review-actions">
            <button
              type="button"
              className="btn btn--primary"
              disabled={panelBusy || !manifestForMutations}
              onClick={() => void accept()}
            >
              采纳
            </button>
            <button
              type="button"
              className="btn btn--secondary"
              disabled={panelBusy || !manifestForMutations}
              onClick={() => void replaceLocal()}
            >
              本地替换
            </button>
            <button
              type="button"
              className="btn btn--secondary"
              disabled={panelBusy || !canRegenerate}
              title={
                canRegenerate ? "重置并重跑相关生图任务" : "需要先选择 / 生成 pipeline manifest"
              }
              onClick={() => void regenerate()}
            >
              重生成
            </button>
          </div>
          {!canRegenerate && (
            <p className="hint">重生成已禁用：请先「① 生成流水线」得到 pipeline manifest。</p>
          )}
        </div>
      )}
    </aside>
  );
}
