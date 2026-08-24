import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { AssetReviewRow } from "../vite-env.d";
import { MediaLightbox } from "./MediaLightbox";

type ReviewStatusFilter = "all" | "pending" | "accepted" | "replaced";

interface Props {
  briefRel: string | null;
  assetsManifestRel: string | null;
  pipelineManifestRel: string | null;
  busy: boolean;
  onOpenBoard?: () => void;
  onAfterRegenerate?: () => void;
  onPinForBriefEdit?: (payload: {
    briefId: string;
    label: string;
    assetName: string;
    specPathRel?: string;
  }) => void;
  style?: React.CSSProperties;
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
  onActivate,
}: {
  pathRepo: string | null;
  updatedAt?: string;
  className?: string;
  onActivate?: (url: string) => void;
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
  if (onActivate) {
    return (
      <button
        type="button"
        className="asset-review-thumb-btn"
        onClick={(e) => {
          e.stopPropagation();
          onActivate(url);
        }}
        title="点开预览"
      >
        <img className={`asset-review-thumb ${className || ""}`} src={url} alt="" loading="lazy" />
      </button>
    );
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
  briefRel,
  assetsManifestRel,
  pipelineManifestRel,
  busy,
  onOpenBoard,
  onAfterRegenerate,
  onPinForBriefEdit,
  style,
}: Props) {
  type ScopeMeta = {
    id: string;
    name: string;
    productionWave: number;
    availability: "ready" | "placeholder";
    placeholderReason: string;
  };
  const [rows, setRows] = useState<AssetReviewRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [filter, setFilter] = useState<ReviewStatusFilter>("all");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [checkedIds, setCheckedIds] = useState<Set<string>>(() => new Set());
  const [lightbox, setLightbox] = useState<{ url: string; title: string; path: string } | null>(
    null,
  );
  const [actionBusy, setActionBusy] = useState(false);
  const [scopeMap, setScopeMap] = useState<Record<string, ScopeMeta>>({});
  const [waveFilter, setWaveFilter] = useState<"all" | "1" | "2" | "3+">("all");
  const [availabilityFilter, setAvailabilityFilter] = useState<"all" | "ready" | "placeholder">("all");
  const [manifestMaxWave, setManifestMaxWave] = useState<number>(1);
  const [batchWave, setBatchWave] = useState("1");
  const [detailWave, setDetailWave] = useState("1");
  const [placeholderReason, setPlaceholderReason] = useState("");
  /** Path IPC actually used when list succeeds via pipeline resolve */
  const [listedManifest, setListedManifest] = useState<string | null>(null);

  const canRegenerate = Boolean(pipelineManifestRel?.trim());
  const panelBusy = busy || loading || actionBusy;
  const manifestForMutations = assetsManifestRel || listedManifest;

  const scopeForRow = useCallback(
    (row: AssetReviewRow): ScopeMeta | null =>
      scopeMap[row.asset_name] || (row.brief_id ? scopeMap[row.brief_id] : null) || null,
    [scopeMap],
  );

  const writableBriefCandidate = useMemo(() => {
    const rel = String(briefRel || "").replace(/\\/g, "/").trim();
    if (!rel) return "";
    const slash = rel.lastIndexOf("/");
    const parent = slash >= 0 ? rel.slice(0, slash) : "";
    return parent ? `${parent}/brief.draft.json` : "brief.draft.json";
  }, [briefRel]);

  const refreshScope = useCallback(async () => {
    const next: Record<string, ScopeMeta> = {};
    const readJson = async (rel: string | null) => {
      if (!rel || !window.gameFactory?.readRepoText) return null;
      const res = await window.gameFactory.readRepoText(rel);
      if (!res?.ok || !res.text) return null;
      return JSON.parse(res.text);
    };
    try {
      const draftData = (await readJson(writableBriefCandidate)) || (await readJson(briefRel));
      const assets = Array.isArray(draftData?.assets) ? draftData.assets : [];
      for (const item of assets) {
        if (!item || typeof item !== "object") continue;
        const id = String(item.id || "").trim();
        const name = String(item.name || "").trim() || id;
        if (!name) continue;
        const meta: ScopeMeta = {
          id,
          name,
          productionWave: Math.max(1, Number(item.production_wave) || 1),
          availability:
            String(item.availability || "ready").trim().toLowerCase() === "placeholder"
              ? "placeholder"
              : "ready",
          placeholderReason: String(item.placeholder_reason || "").trim(),
        };
        next[name] = meta;
        if (id) next[id] = meta;
      }
    } catch {
      // ignore parse errors; asset review remains usable
    }
    setScopeMap(next);
    if (pipelineManifestRel && window.gameFactory?.getManifestMeta) {
      try {
        const meta = await window.gameFactory.getManifestMeta(pipelineManifestRel);
        const wave = Math.max(1, Number(meta?.production_max_wave) || 1);
        setManifestMaxWave(wave);
        setBatchWave(String(wave));
      } catch {
        setManifestMaxWave(1);
      }
    }
  }, [briefRel, pipelineManifestRel, writableBriefCandidate]);

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

  useEffect(() => {
    void refreshScope();
  }, [refreshScope]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return rows.filter((row) => {
      if (filter !== "all" && row.review?.status !== filter) return false;
      const scope = scopeForRow(row);
      if (availabilityFilter !== "all" && (scope?.availability || "ready") !== availabilityFilter) {
        return false;
      }
      const wave = scope?.productionWave || 1;
      if (waveFilter === "1" && wave !== 1) return false;
      if (waveFilter === "2" && wave !== 2) return false;
      if (waveFilter === "3+" && wave < 3) return false;
      if (!q) return true;
      const hay =
        `${row.label} ${row.asset_name} ${row.kit_item_slug || ""} ${row.usage || ""} ${row.type || ""} wave${wave} ${scope?.availability || "ready"}`.toLowerCase();
      return hay.includes(q);
    });
  }, [rows, filter, search, scopeForRow, availabilityFilter, waveFilter]);

  // Keep selection only while it still matches the filter; do not auto-pick
  // the first row (that trapped users in detail with no clear way back).
  useEffect(() => {
    if (!selectedId) return;
    if (!filtered.some((r) => r.row_id === selectedId)) {
      setSelectedId(null);
    }
  }, [filtered, selectedId]);

  useEffect(() => {
    const visible = new Set(filtered.map((r) => r.row_id));
    setCheckedIds((prev) => {
      const next = new Set([...prev].filter((id) => visible.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [filtered]);

  const toggleChecked = (rowId: string, checked: boolean) => {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(rowId);
      else next.delete(rowId);
      return next;
    });
  };

  const toggleAllFiltered = () => {
    const allSelected =
      filtered.length > 0 && filtered.every((r) => checkedIds.has(r.row_id));
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (allSelected) {
        for (const r of filtered) next.delete(r.row_id);
      } else {
        for (const r of filtered) next.add(r.row_id);
      }
      return next;
    });
  };

  const selected = filtered.find((r) => r.row_id === selectedId) || null;
  const selectedScope = selected ? scopeForRow(selected) : null;

  useEffect(() => {
    if (!selectedScope) return;
    setDetailWave(String(selectedScope.productionWave || 1));
    setPlaceholderReason(selectedScope.placeholderReason || "");
  }, [selectedScope?.id, selectedScope?.productionWave, selectedScope?.placeholderReason]);

  const replanCurrentManifest = async (maxWaveOverride?: number) => {
    if (!pipelineManifestRel || !window.gameFactory?.getManifestMeta || !window.gameFactory?.pipelinePlan) {
      return;
    }
    const meta = await window.gameFactory.getManifestMeta(pipelineManifestRel);
    if (!meta?.brief || !meta.output_dir || !meta.godot_project) return;
    const wave = Math.max(1, Number(maxWaveOverride || meta.production_max_wave || manifestMaxWave || 1));
    const result = await window.gameFactory.pipelinePlan({
      briefRel: meta.brief,
      manifestRel: pipelineManifestRel,
      outputDirRel: meta.output_dir,
      godotProjectRel: meta.godot_project,
      plansDirRel: meta.plans_dir,
      mergeRel: pipelineManifestRel,
      maxWave: wave,
    });
    if (result.exitCode !== 0) {
      throw new Error(result.stderr?.trim() || "重排 manifest 失败");
    }
    setManifestMaxWave(wave);
  };

  const updateScope = async (
    targets: AssetReviewRow[],
    patch: { productionWave?: number; availability?: "ready" | "placeholder"; placeholderReason?: string },
    opts?: { replan?: boolean; maxWave?: number },
  ) => {
    if (!briefRel || !window.gameFactory?.patchBriefAssets || targets.length === 0) return;
    setActionBusy(true);
    setError(null);
    setMessage(null);
    try {
      const updates = targets.map((row) => ({
        id: row.brief_id || undefined,
        name: row.asset_name,
        assetName: row.asset_name,
        productionWave: patch.productionWave,
        availability: patch.availability,
        placeholderReason: patch.placeholderReason,
      }));
      const res = await window.gameFactory.patchBriefAssets(briefRel, updates);
      if (!res?.ok) {
        throw new Error(res?.error || "更新资产标记失败");
      }
      if (opts?.replan !== false) {
        await replanCurrentManifest(opts?.maxWave);
      }
      await refreshScope();
      await refresh();
      onAfterRegenerate?.();
      setMessage(`已更新 ${updates.length} 项资产施工标记`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setActionBusy(false);
    }
  };

  const checkedRows = filtered.filter((r) => checkedIds.has(r.row_id));

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

  const regenerateBatch = async (resetOnly: boolean) => {
    if (!pipelineManifestRel || checkedIds.size === 0) return;
    const n = checkedIds.size;
    const ok = window.confirm(
      resetOnly
        ? `仅重置选中的 ${n} 项？\n任务会变为 pending，之后点「运行资产生成」续跑。`
        : `重生成选中的 ${n} 项？\n将重置并重跑（含 prompt 重制，若适用）。`,
    );
    if (!ok) return;
    setActionBusy(true);
    setError(null);
    try {
      if (!window.gameFactory?.assetsReviewRegenerateBatch) {
        setError("批量重生成 API 不可用（请重启应用）");
        return;
      }
      const res = await window.gameFactory.assetsReviewRegenerateBatch(pipelineManifestRel, {
        rowIds: [...checkedIds],
        assetsManifestRel: manifestForMutations,
        jobs: 4,
        resetOnly,
        recraftPrompt: true,
      });
      if (res.exitCode !== 0) {
        setError(res.stderr?.trim() || "批量操作失败");
      } else {
        setCheckedIds(new Set());
      }
      await refresh();
      onAfterRegenerate?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setActionBusy(false);
    }
  };

  const regenerate = async () => {
    if (!selected || !pipelineManifestRel) return;
    const useHost = Boolean(window.gameFactory?.hostRetryAsset) && !selected.kit_item_slug;
    const ok = window.confirm(
      useHost
        ? `重生成「${selected.label}」？\n将通过 Host 重置并重跑该资产（含 prompt 重制）。`
        : `重生成「${selected.label}」？\n将 cascade 重置相关 image.generate 任务并重新跑 pipeline。`,
    );
    if (!ok) return;
    setActionBusy(true);
    setError(null);
    try {
      if (useHost) {
        const res = await window.gameFactory.hostRetryAsset!(
          pipelineManifestRel,
          selected.asset_name,
          { recraftPrompt: true, jobs: 4 },
        );
        if (res.exitCode !== 0) {
          setError(res.stderr?.trim() || "重生成失败");
        }
      } else {
        const res = await window.gameFactory.assetsReviewRegenerate(
          pipelineManifestRel,
          selected.asset_name,
          selected.kit_item_slug ?? null,
          4,
        );
        if (res.exitCode !== 0) {
          setError(res.stderr?.trim() || "重生成失败");
        }
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

  const copyHint = async (text: string, label: string) => {
    const value = String(text || "").trim();
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setError(null);
      setMessage(`已复制 ${label}`);
    } catch {
      setError(`无法复制到剪贴板，请手动复制：${value}`);
    }
  };

  return (
    <aside className="side-panel board-panel asset-review-panel" style={style}>
      <div className="side-panel__head board-head">
        <h2>资产</h2>
        <p className="hint">改说明用 brief id +「送入策划」；不满意图用勾选 → 重生成</p>
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
      <div className="asset-review-filters">
        {(
          [
            ["all", "全部波次"],
            ["1", "第 1 波"],
            ["2", "第 2 波"],
            ["3+", "第 3 波+"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`composer__chip ${waveFilter === id ? "composer__chip--primary" : ""}`}
            onClick={() => setWaveFilter(id)}
          >
            {label}
          </button>
        ))}
        {(
          [
            ["all", "全部状态"],
            ["ready", "已就绪"],
            ["placeholder", "暂空占位"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`composer__chip ${availabilityFilter === id ? "composer__chip--primary" : ""}`}
            onClick={() => setAvailabilityFilter(id)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="asset-scope-toolbar">
        <span className="asset-scope-toolbar__label">当前施工波次</span>
        <input
          className="asset-scope-toolbar__input"
          type="number"
          min={1}
          value={batchWave}
          onChange={(e) => setBatchWave(e.target.value)}
          disabled={panelBusy}
        />
        <button
          type="button"
          className="btn btn--secondary btn--sm"
          disabled={panelBusy || !pipelineManifestRel}
          onClick={() => void replanCurrentManifest(Math.max(1, Number(batchWave) || 1)).then(() => setMessage("已按新波次重排 manifest")).catch((e) => setError(e instanceof Error ? e.message : String(e)))}
        >
          重排 manifest
        </button>
        <span className="hint">manifest 当前为第 {manifestMaxWave} 波</span>
      </div>

      <input
        className="asset-review-search"
        type="search"
        placeholder="搜索名称 / id / usage…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {error && <p className="hint asset-review-error">{error}</p>}
      {message && !error && <p className="hint asset-review-ok">{message}</p>}

      {!manifestForMutations && !loading && (
        <p className="brief-draft-empty">尚无 assets-manifest。请先生成流水线并运行资产生成。</p>
      )}

      {checkedIds.size > 0 && canRegenerate && (
        <div className="asset-review-batch">
          <span className="asset-review-batch__count">已选 {checkedIds.size} 项</span>
          <input
            className="asset-scope-toolbar__input"
            type="number"
            min={1}
            value={batchWave}
            onChange={(e) => setBatchWave(e.target.value)}
            disabled={panelBusy}
            title="批量改到第几波"
          />
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            disabled={panelBusy || !briefRel}
            onClick={() =>
              void updateScope(checkedRows, { productionWave: Math.max(1, Number(batchWave) || 1) })
            }
          >
            改波次
          </button>
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            disabled={panelBusy || !briefRel}
            onClick={() =>
              void updateScope(checkedRows, {
                availability: "placeholder",
                placeholderReason: "GUI 暂空",
              })
            }
          >
            标记暂空
          </button>
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            disabled={panelBusy || !briefRel}
            onClick={() => void updateScope(checkedRows, { availability: "ready", placeholderReason: "" })}
          >
            恢复就绪
          </button>
          <button
            type="button"
            className="btn btn--primary btn--sm"
            disabled={panelBusy}
            onClick={() => void regenerateBatch(false)}
          >
            重生成选中
          </button>
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            disabled={panelBusy}
            onClick={() => void regenerateBatch(true)}
            title="只打回 pending，不立刻跑 pipeline"
          >
            仅重置
          </button>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            disabled={panelBusy}
            onClick={() => {
              const ids = filtered
                .filter((r) => checkedIds.has(r.row_id))
                .map((r) => r.brief_id || r.asset_name);
              void copyHint(ids.join("\n"), `${ids.length} 个 brief id`);
            }}
          >
            复制 brief id
          </button>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            disabled={panelBusy}
            onClick={() => setCheckedIds(new Set())}
          >
            取消选择
          </button>
        </div>
      )}

      <div className="asset-review-list-head">
        <label className="asset-review-check-all">
          <input
            type="checkbox"
            checked={filtered.length > 0 && filtered.every((r) => checkedIds.has(r.row_id))}
            onChange={() => toggleAllFiltered()}
            disabled={panelBusy || filtered.length === 0}
          />
          <span>全选当前列表</span>
        </label>
      </div>

      <div className="asset-review-list">
        {filtered.map((row) => (
          <div
            key={row.row_id}
            className={`asset-review-row ${selectedId === row.row_id ? "is-active" : ""}`}
          >
            <input
              type="checkbox"
              className="asset-review-row__check"
              checked={checkedIds.has(row.row_id)}
              onChange={(e) => toggleChecked(row.row_id, e.target.checked)}
              disabled={panelBusy}
              aria-label={`选择 ${row.label}`}
            />
            <button
              type="button"
              className="asset-review-row__open"
              onClick={() => setSelectedId(row.row_id)}
            >
              <Thumb
                key={`${row.preview_path_repo || ""}:${row.review?.updated_at || ""}`}
                pathRepo={row.preview_path_repo}
                updatedAt={row.review?.updated_at}
                onActivate={(url) =>
                  setLightbox({
                    url,
                    title: row.label,
                    path: row.preview_path_repo || row.canonical_path_repo || "",
                  })
                }
              />
              <div className="asset-review-row__body">
                <span className="asset-review-row__title">{row.label}</span>
                <span className="asset-review-row__meta">
                  {row.type || "—"}
                  {row.usage ? ` · ${row.usage}` : ""}
                  {scopeForRow(row) ? ` · W${scopeForRow(row)?.productionWave || 1}` : ""}
                  {scopeForRow(row)?.availability === "placeholder" ? " · 暂空" : ""}
                </span>
              </div>
              <span className={`style-chip ${statusClass(row.review?.status || "pending")}`}>
                {STATUS_LABEL[row.review?.status || "pending"]}
              </span>
            </button>
          </div>
        ))}
        {manifestForMutations && !loading && filtered.length === 0 && (
          <p className="brief-draft-empty">没有匹配的资产行。</p>
        )}
      </div>

      {selected && (
        <div className="asset-review-detail">
          <div className="asset-review-detail__head">
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setSelectedId(null)}
            >
              ← 返回列表
            </button>
            <h3>{selected.label}</h3>
          </div>
          <Thumb
            key={`${selected.preview_path_repo || ""}:${selected.review?.updated_at || ""}`}
            pathRepo={selected.preview_path_repo}
            updatedAt={selected.review?.updated_at}
            className="asset-review-thumb--lg"
            onActivate={(url) =>
              setLightbox({
                url,
                title: selected.label,
                path: selected.preview_path_repo || selected.canonical_path_repo || "",
              })
            }
          />
          <dl className="asset-review-dl">
            <div>
              <dt>改 brief 用（id）</dt>
              <dd className="mono">
                {selected.brief_id || selected.asset_name}
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() =>
                    void copyHint(selected.brief_id || selected.asset_name, "brief id")
                  }
                >
                  复制
                </button>
                {onPinForBriefEdit && !selected.kit_item_slug ? (
                  <button
                    type="button"
                    className="btn btn--secondary"
                    onClick={() =>
                      onPinForBriefEdit({
                        briefId: selected.brief_id || selected.asset_name,
                        label: selected.label,
                        assetName: selected.asset_name,
                      })
                    }
                  >
                    送入策划
                  </button>
                ) : null}
              </dd>
            </div>
            <div>
              <dt>流水线名（asset_name）</dt>
              <dd className="mono">
                {selected.asset_name}
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void copyHint(selected.asset_name, "流水线名")}
                >
                  复制
                </button>
              </dd>
            </div>
            <div>
              <dt>审查行 id</dt>
              <dd className="mono">{selected.row_id}</dd>
            </div>
            <div>
              <dt>施工控制</dt>
              <dd>
                W{selectedScope?.productionWave || 1}
                {selectedScope?.availability === "placeholder" ? " · 暂空占位" : " · 已就绪"}
                {selectedScope?.placeholderReason ? ` · ${selectedScope.placeholderReason}` : ""}
              </dd>
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
                      系统打开
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
          <div className="asset-scope-editor">
            <label className="asset-scope-editor__field">
              <span>波次</span>
              <input
                className="asset-scope-toolbar__input"
                type="number"
                min={1}
                value={detailWave}
                onChange={(e) => setDetailWave(e.target.value)}
                disabled={panelBusy}
              />
            </label>
            <label className="asset-scope-editor__field asset-scope-editor__field--grow">
              <span>暂空原因</span>
              <input
                className="asset-review-search"
                type="text"
                placeholder="例如：玩法未启用 / 下一波再补"
                value={placeholderReason}
                onChange={(e) => setPlaceholderReason(e.target.value)}
                disabled={panelBusy}
              />
            </label>
            <button
              type="button"
              className="btn btn--secondary"
              disabled={panelBusy || !briefRel || !selected}
              onClick={() =>
                void updateScope(
                  [selected],
                  { productionWave: Math.max(1, Number(detailWave) || 1) },
                  { maxWave: manifestMaxWave },
                )
              }
            >
              保存波次
            </button>
            <button
              type="button"
              className="btn btn--secondary"
              disabled={panelBusy || !briefRel || !selected}
              onClick={() =>
                void updateScope(
                  [selected],
                  { availability: "placeholder", placeholderReason },
                  { maxWave: manifestMaxWave },
                )
              }
            >
              设为暂空
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              disabled={panelBusy || !briefRel || !selected}
              onClick={() =>
                void updateScope(
                  [selected],
                  { availability: "ready", placeholderReason: "" },
                  { maxWave: manifestMaxWave },
                )
              }
            >
              恢复就绪
            </button>
          </div>
          <p className="hint">
            改 <code>description</code> / 尺寸：点 <strong>送入策划</strong>（锁定 brief 分册 + 对话焦点），直接说怎么改即可，不必手抄 id。
            icon_kit 子项请用流水线名或在文档里改父资产。
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
                canRegenerate
                  ? "重置并重跑（含 prompt 重制）"
                  : "需要先选择 / 生成 pipeline manifest"
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
      {lightbox && (
        <MediaLightbox
          url={lightbox.url}
          title={lightbox.title}
          pathHint={lightbox.path}
          onClose={() => setLightbox(null)}
          onOpenExternal={
            lightbox.path
              ? () => {
                  void window.gameFactory?.openMedia?.(lightbox.path);
                }
              : undefined
          }
        />
      )}
    </aside>
  );
}
