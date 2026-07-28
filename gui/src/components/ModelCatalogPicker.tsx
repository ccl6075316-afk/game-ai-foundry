import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const DISPLAY_LIMIT = 30;
const CUSTOM_OPTION = "__custom__";
const IMAGE_MODEL_RE = /image|dall-e|flux|gpt-image|imagen/i;

export interface ModelCatalogPickerProps {
  providerId: string;
  value: string;
  onChange: (value: string) => void;
  role: "text" | "image";
  disabled?: boolean;
  placeholder?: string;
  /** 对话顶栏等窄行：单行下拉 + 刷新 */
  compact?: boolean;
}

interface CatalogModel {
  id: string;
  label: string;
}

const catalogCache = new Map<string, CatalogModel[]>();

function normalizeModels(raw: unknown): CatalogModel[] {
  if (!Array.isArray(raw)) return [];
  const out: CatalogModel[] = [];
  const seen = new Set<string>();
  for (const item of raw) {
    if (!item || typeof item !== "object") continue;
    const id = String((item as { id?: unknown }).id || "").trim();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    const label = String((item as { label?: unknown }).label || id).trim() || id;
    out.push({ id, label });
  }
  return out;
}

function filterImageModels(models: CatalogModel[]): CatalogModel[] {
  return models.filter((m) => IMAGE_MODEL_RE.test(m.id));
}

function filterByQuery(models: CatalogModel[], query: string): CatalogModel[] {
  const q = query.trim().toLowerCase();
  if (!q) return models;
  return models.filter(
    (m) => m.id.toLowerCase().includes(q) || m.label.toLowerCase().includes(q),
  );
}

function buildDisplayList(models: CatalogModel[], value: string): CatalogModel[] {
  const sliced = models.slice(0, DISPLAY_LIMIT);
  const trimmed = value.trim();
  if (!trimmed) return sliced;
  if (sliced.some((m) => m.id === trimmed)) return sliced;
  return [{ id: trimmed, label: trimmed }, ...sliced].slice(0, DISPLAY_LIMIT + 1);
}

export function ModelCatalogPicker({
  providerId,
  value,
  onChange,
  role,
  disabled = false,
  placeholder,
  compact = false,
}: ModelCatalogPickerProps) {
  const [query, setQuery] = useState("");
  const [showAllModels, setShowAllModels] = useState(false);
  const [customOpen, setCustomOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [catalog, setCatalog] = useState<CatalogModel[]>(() =>
    providerId ? catalogCache.get(providerId) ?? [] : [],
  );
  const autoFetched = useRef<string | null>(null);

  useEffect(() => {
    setCatalog(providerId ? catalogCache.get(providerId) ?? [] : []);
    setQuery("");
    setError(null);
    setCustomOpen(false);
  }, [providerId]);

  const refresh = useCallback(async () => {
    if (!providerId || disabled) return;
    setLoading(true);
    setError(null);
    try {
      if (!window.gameFactory?.providerModels) {
        setError("当前环境无法拉取模型目录");
        return;
      }
      const res = await window.gameFactory.providerModels(providerId);
      const data = res.data;
      if (!data?.ok) {
        setError(data?.error || "拉取模型目录失败");
        return;
      }
      const models = normalizeModels(data.models);
      catalogCache.set(providerId, models);
      setCatalog(models);
      if (models.length === 0) {
        setError("目录为空");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [providerId, disabled]);

  // 首次进入某账号且无缓存时自动拉一次，方便直接下拉
  useEffect(() => {
    if (!providerId || disabled) return;
    if (catalogCache.has(providerId)) return;
    if (autoFetched.current === providerId) return;
    autoFetched.current = providerId;
    void refresh();
  }, [providerId, disabled, refresh]);

  const roleFiltered = useMemo(() => {
    if (role !== "image" || showAllModels) return catalog;
    return filterImageModels(catalog);
  }, [catalog, role, showAllModels]);

  const filtered = useMemo(
    () => filterByQuery(roleFiltered, compact ? "" : query),
    [roleFiltered, query, compact],
  );
  const displayList = useMemo(() => buildDisplayList(filtered, value), [filtered, value]);

  const trimmed = value.trim();
  const inList = displayList.some((m) => m.id === trimmed);
  const showCustomInput = customOpen || (trimmed !== "" && !inList) || catalog.length === 0;
  const selectValue = showCustomInput ? CUSTOM_OPTION : trimmed;

  const onSelectChange = (next: string) => {
    if (next === CUSTOM_OPTION) {
      setCustomOpen(true);
      return;
    }
    setCustomOpen(false);
    onChange(next);
  };

  const selectEl = (
    <select
      value={selectValue}
      disabled={disabled || loading}
      aria-label="模型"
      title={error || undefined}
      onChange={(e) => onSelectChange(e.target.value)}
    >
      {catalog.length === 0 ? (
        <option value={CUSTOM_OPTION}>
          {loading ? "拉取模型中…" : "手填 / 先刷新目录"}
        </option>
      ) : (
        <>
          {!trimmed && !showCustomInput ? <option value="">选择模型…</option> : null}
          {displayList.map((m) => (
            <option key={m.id} value={m.id}>
              {m.id}
            </option>
          ))}
          <option value={CUSTOM_OPTION}>自定义…</option>
        </>
      )}
    </select>
  );

  const refreshBtn = (
    <button
      type="button"
      className={compact ? "btn btn--sm btn--secondary" : "btn btn--secondary"}
      onClick={() => void refresh()}
      disabled={disabled || loading || !providerId}
      title={error || "拉取 /models"}
    >
      {loading ? (compact ? "…" : "刷新中…") : "刷新"}
    </button>
  );

  const customInput = showCustomInput ? (
    <input
      type="text"
      value={value}
      onChange={(e) => {
        setCustomOpen(true);
        onChange(e.target.value);
      }}
      placeholder={placeholder || (compact ? "模型 id" : "模型 ID（可手填）")}
      disabled={disabled}
      aria-label="自定义模型 ID"
    />
  ) : null;

  if (compact) {
    return (
      <span className="model-catalog-picker model-catalog-picker--compact">
        {selectEl}
        {customInput}
        {refreshBtn}
      </span>
    );
  }

  return (
    <div className="field model-catalog-picker">
      <div className="field-row model-catalog-picker__row">
        {selectEl}
        {refreshBtn}
      </div>
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="搜索过滤下拉选项…"
        disabled={disabled || catalog.length === 0}
        aria-label="搜索模型"
      />
      {customInput}
      {role === "image" && (
        <label className="field field--checkbox">
          <input
            type="checkbox"
            checked={showAllModels}
            onChange={(e) => setShowAllModels(e.target.checked)}
            disabled={disabled}
          />
          <span>显示全部模型（含非图像启发式）</span>
        </label>
      )}
      {catalog.length > 0 && filtered.length > DISPLAY_LIMIT && (
        <p className="field-hint">
          共 {filtered.length} 条匹配，下拉仅前 {DISPLAY_LIMIT} 条；请用搜索缩小或选「自定义…」手填。
        </p>
      )}
      {error && <p className="field-hint settings-feedback--error">{error}</p>}
      {!error && catalog.length === 0 && !loading && (
        <p className="field-hint">点「刷新」拉取目录后即可下拉选择；亦可直接手填。</p>
      )}
    </div>
  );
}
