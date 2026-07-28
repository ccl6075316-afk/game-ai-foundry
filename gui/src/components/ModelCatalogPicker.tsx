import { useCallback, useEffect, useMemo, useState } from "react";

const DISPLAY_LIMIT = 30;
const IMAGE_MODEL_RE = /image|dall-e|flux|gpt-image|imagen/i;

export interface ModelCatalogPickerProps {
  providerId: string;
  value: string;
  onChange: (value: string) => void;
  role: "text" | "image";
  disabled?: boolean;
  placeholder?: string;
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
}: ModelCatalogPickerProps) {
  const [query, setQuery] = useState("");
  const [showAllModels, setShowAllModels] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [catalog, setCatalog] = useState<CatalogModel[]>(() =>
    providerId ? catalogCache.get(providerId) ?? [] : [],
  );

  useEffect(() => {
    setCatalog(providerId ? catalogCache.get(providerId) ?? [] : []);
    setQuery("");
    setError(null);
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

  const roleFiltered = useMemo(() => {
    if (role !== "image" || showAllModels) return catalog;
    return filterImageModels(catalog);
  }, [catalog, role, showAllModels]);

  const filtered = useMemo(() => filterByQuery(roleFiltered, query), [roleFiltered, query]);
  const displayList = useMemo(() => buildDisplayList(filtered, value), [filtered, value]);

  return (
    <div className="field model-catalog-picker">
      <div className="field-row">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder || "模型 ID（可手填）"}
          disabled={disabled}
          aria-label="模型 ID"
        />
        <button
          type="button"
          className="btn btn--secondary"
          onClick={() => void refresh()}
          disabled={disabled || loading || !providerId}
        >
          {loading ? "刷新中…" : "刷新"}
        </button>
      </div>
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="搜索模型…"
        disabled={disabled || catalog.length === 0}
        aria-label="搜索模型"
      />
      {role === "image" && (
        <label className="field field--checkbox">
          <input
            type="checkbox"
            checked={showAllModels}
            onChange={(e) => setShowAllModels(e.target.checked)}
            disabled={disabled}
          />
          <span>显示全部模型</span>
        </label>
      )}
      {catalog.length > 0 && (
        <div className="provider-account-chips__row" role="listbox" aria-label="模型列表">
          {displayList.map((m) => (
            <button
              key={m.id}
              type="button"
              role="option"
              aria-selected={m.id === value}
              className={`provider-chip ${m.id === value ? "active configured" : ""}`}
              onClick={() => onChange(m.id)}
              disabled={disabled}
              title={m.label !== m.id ? m.label : m.id}
            >
              <span className="mono">{m.id}</span>
            </button>
          ))}
        </div>
      )}
      {catalog.length > 0 && filtered.length > DISPLAY_LIMIT && (
        <p className="field-hint">
          共 {filtered.length} 条匹配，仅展示前 {DISPLAY_LIMIT} 条；请用搜索缩小范围或手填。
        </p>
      )}
      {error && <p className="field-hint settings-feedback--error">{error}</p>}
      {!error && catalog.length === 0 && !loading && (
        <p className="field-hint">点「刷新」从 Provider 拉取 /models 目录；失败时仍可手填。</p>
      )}
    </div>
  );
}
