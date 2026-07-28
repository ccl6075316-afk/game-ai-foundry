import { useCallback, useEffect, useState } from "react";
import type { ConfigInfo, ConfigPatch } from "../../vite-env.d";
import { ModelCatalogPicker } from "../ModelCatalogPicker";
import {
  API_PROVIDERS,
  VIDEO_PROVIDERS,
  getApiProvider,
  getVideoProvider,
  isApiProviderId,
  isBuiltinProviderId,
  type VideoProviderId,
} from "../../settings/apiProviders";
import {
  NETWORK_SECTION,
  VIDEO_PROVIDER_SECTION,
  keyConfigured,
} from "../../settings/sections";
import {
  getProviderAccount,
  getVideoAccount,
  isProviderConfigured,
  isVideoConfigured,
  loadProviderAccountsFromConfig,
  resolveActiveImageSettings,
  resolveActiveTextSettings,
  resolveActiveVideoSettings,
  serializeProviderAccounts,
  serializeVideoAccounts,
  updateProviderAccount,
  updateVideoAccount as applyVideoAccountPatch,
  isValidProviderSlug,
  isUserProviderId,
  listUserAccounts,
  type ProviderAccountsMap,
  type VideoAccountsMap,
  type ProviderAccount,
} from "../../settings/providerAccounts";

interface Props {
  busy?: boolean;
  onSaved?: () => void;
}

interface ProviderFormState {
  providerAccounts: ProviderAccountsMap;
  activeTextProvider: string;
  activeImageProvider: string;
  activeBulkImageProvider: string;
  imageUseTextProvider: boolean;
  imageBulkModel: string;
  videoAccounts: VideoAccountsMap;
  activeVideoProvider: VideoProviderId;
  proxy: string;
}

interface ProviderOption {
  id: string;
  label: string;
}

interface NewAccountForm {
  id: string;
  label: string;
  apiBase: string;
  apiKey: string;
}

function listConfigurableProviders(accounts: ProviderAccountsMap): ProviderOption[] {
  const options: ProviderOption[] = API_PROVIDERS.map((p) => ({ id: p.id, label: p.label }));
  const knownIds = new Set(options.map((o) => o.id));
  for (const { id, account } of listUserAccounts(accounts)) {
    if (knownIds.has(id)) continue;
    options.push({ id, label: account.label?.trim() || id });
    knownIds.add(id);
  }
  return options;
}

function providerOptionLabel(id: string, accounts: ProviderAccountsMap): string {
  const preset = API_PROVIDERS.find((p) => p.id === id);
  if (preset) return preset.label;
  const acc = accounts[id];
  return acc?.label?.trim() || id;
}

function isProviderReferenced(form: ProviderFormState, id: string): boolean {
  if (form.activeTextProvider === id) return true;
  if (!form.imageUseTextProvider && form.activeImageProvider === id) return true;
  if (form.activeBulkImageProvider === id) return true;
  return false;
}

function fromConfig(data: ConfigInfo["data"]): ProviderFormState {
  const imageBlock = (data.image || {}) as Record<string, unknown>;
  const loaded = loadProviderAccountsFromConfig(data as Record<string, unknown>);

  const bulkRaw = imageBlock.bulk_provider;
  const activeBulkImageProvider =
    typeof bulkRaw === "string" && (isApiProviderId(bulkRaw) || isValidProviderSlug(bulkRaw))
      ? bulkRaw
      : loaded.activeImageProvider;

  return {
    ...loaded,
    activeBulkImageProvider,
    imageBulkModel: String(imageBlock.bulk_model || ""),
    proxy: String(
      data.proxy ||
        (data.host as Record<string, unknown> | undefined)?.proxy ||
        imageBlock.proxy ||
        (data.prompt as Record<string, unknown> | undefined)?.proxy ||
        "",
    ),
  };
}

function toProviderPatch(form: ProviderFormState): ConfigPatch {
  const text = resolveActiveTextSettings(form);
  const image = resolveActiveImageSettings(form);
  const video = resolveActiveVideoSettings(form);

  return {
    proxy: form.proxy.trim() || null,
    provider_accounts: serializeProviderAccounts(form.providerAccounts),
    video_accounts: serializeVideoAccounts(form.videoAccounts),
    host: {
      provider: text.provider,
      api_key: text.api_key,
      model: text.model,
      api_base: text.api_base,
      proxy: null,
    },
    image: {
      provider: image.provider,
      use_text_provider: image.use_text_provider,
      api_key: image.api_key,
      model: image.model,
      bulk_provider: form.activeBulkImageProvider,
      bulk_model: form.imageBulkModel.trim() || null,
      api_base: image.api_base,
      proxy: null,
    },
    video: {
      provider: video.provider,
      api_key: video.api_key,
      api_base: video.api_base,
    },
  };
}

export function ProviderSettingsView({ busy = false, onSaved }: Props) {
  const [configInfo, setConfigInfo] = useState<ConfigInfo | null>(null);
  const [form, setForm] = useState<ProviderFormState>(() => fromConfig({}));
  const [editAccountId, setEditAccountId] = useState<string>("openrouter");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newAccount, setNewAccount] = useState<NewAccountForm>({
    id: "",
    label: "",
    apiBase: "",
    apiKey: "",
  });
  const [addAccountError, setAddAccountError] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const info = await window.gameFactory.getConfig();
      setConfigInfo(info);
      const next = fromConfig(info.data);
      setForm(next);
      setEditAccountId((prev) => {
        const options = listConfigurableProviders(next.providerAccounts);
        if (options.some((o) => o.id === prev)) return prev;
        return next.activeTextProvider || options[0]?.id || "openrouter";
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const disabled = busy || loading || saving;
  const options = listConfigurableProviders(form.providerAccounts);
  const editAccount = getProviderAccount(form.providerAccounts, editAccountId);
  const editPreset = getApiProvider(editAccountId, editAccount);
  const editConfigured = isProviderConfigured(form.providerAccounts, editAccountId);
  const textPreset = getApiProvider(form.activeTextProvider, getProviderAccount(form.providerAccounts, form.activeTextProvider));
  const bulkImageAccount = getProviderAccount(form.providerAccounts, form.activeBulkImageProvider);
  const bulkImagePreset = getApiProvider(form.activeBulkImageProvider, bulkImageAccount);
  const videoAccount = getVideoAccount(form.videoAccounts, form.activeVideoProvider);
  const videoPreset = getVideoProvider(form.activeVideoProvider);

  const setField = <K extends keyof ProviderFormState>(key: K, value: ProviderFormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setMessage(null);
  };

  const updateEditAccount = (patch: Partial<ProviderAccount>) => {
    setForm((prev) => ({
      ...prev,
      providerAccounts: updateProviderAccount(prev.providerAccounts, editAccountId, patch),
    }));
    setMessage(null);
  };

  const setActiveImageProvider = (id: string) => {
    setForm((prev) => ({ ...prev, activeImageProvider: id, imageUseTextProvider: false }));
    setMessage(null);
  };

  const updateBulkImageAccount = (patch: Partial<ProviderAccount>) => {
    setForm((prev) => ({
      ...prev,
      providerAccounts: updateProviderAccount(prev.providerAccounts, prev.activeBulkImageProvider, patch),
    }));
    setMessage(null);
  };

  const patchActiveVideoAccount = (patch: Partial<{ apiKey: string; apiBase: string }>) => {
    setForm((prev) => ({
      ...prev,
      videoAccounts: applyVideoAccountPatch(prev.videoAccounts, prev.activeVideoProvider, patch),
    }));
    setMessage(null);
  };

  const handleAddAccount = () => {
    const id = newAccount.id.trim();
    setAddAccountError(null);
    if (!isValidProviderSlug(id)) {
      setAddAccountError("id 须为小写字母开头，2–32 字符，仅 a-z、0-9、_、-");
      return;
    }
    if (isBuiltinProviderId(id)) {
      setAddAccountError(`「${id}」为内置 id，请换用其他 slug`);
      return;
    }
    if (form.providerAccounts[id]) {
      setAddAccountError(`账号「${id}」已存在`);
      return;
    }
    const label = newAccount.label.trim() || id;
    const apiBase = newAccount.apiBase.trim();
    const apiKey = newAccount.apiKey.trim();
    if (!apiBase) {
      setAddAccountError("自建账号须填写 API 地址");
      return;
    }
    setForm((prev) => ({
      ...prev,
      providerAccounts: updateProviderAccount(prev.providerAccounts, id, {
        kind: "user",
        label,
        apiBase,
        apiKey,
        textModel: "",
        imageModel: "",
      }),
    }));
    setEditAccountId(id);
    setNewAccount({ id: "", label: "", apiBase: "", apiKey: "" });
    setShowAddForm(false);
    setMessage(`已添加账号「${label}」，保存后写入配置`);
  };

  const handleDeleteAccount = (id: string) => {
    if (!isUserProviderId(id) || isBuiltinProviderId(id)) return;
    if (isProviderReferenced(form, id)) {
      setError("无法删除：该账号正被生文 / 主图 / 批量启用，请先切换到其他账号");
      return;
    }
    setForm((prev) => {
      const nextAccounts = { ...prev.providerAccounts };
      delete nextAccounts[id];
      return { ...prev, providerAccounts: nextAccounts };
    });
    if (editAccountId === id) {
      setEditAccountId(form.activeTextProvider);
    }
    setMessage(`已移除账号「${providerOptionLabel(id, form.providerAccounts)}」，保存后生效`);
    setError(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await window.gameFactory.getConfig();
      const patch = toProviderPatch(form);
      const res = await window.gameFactory.saveConfig(patch);
      if (!res.ok) throw new Error(res.error || "保存失败");
      setMessage("已保存 Provider 设置");
      await load();
      onSaved?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleInitExample = async () => {
    setSaving(true);
    setError(null);
    try {
      await window.gameFactory.initConfigFromExample();
      setMessage("已从示例创建，请填入你的账号密钥");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <p className="hint">加载中…</p>;
  }

  return (
    <div className="provider-settings">
      {configInfo && (
        <button
          type="button"
          className="settings-path"
          onClick={() => void window.gameFactory.openConfigFolder()}
          title={configInfo.path}
        >
          <span className="settings-path__label">配置文件</span>
          <span className="settings-path__value mono">{configInfo.path}</span>
          <span className={`settings-path__status ${configInfo.exists ? "ok" : "missing"}`}>
            {configInfo.exists ? "已存在" : "未创建 — 可先点「从示例创建」"}
          </span>
        </button>
      )}

      <div className="provider-settings__short-controls">
        <label className="field">
          <span>生文用账号</span>
          <select
            value={form.activeTextProvider}
            onChange={(e) => setField("activeTextProvider", e.target.value)}
            disabled={disabled}
          >
            {options.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
                {isProviderConfigured(form.providerAccounts, p.id) ? " ✓" : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="field field--checkbox">
          <input
            type="checkbox"
            checked={form.imageUseTextProvider}
            onChange={(e) => setField("imageUseTextProvider", e.target.checked)}
            disabled={disabled}
          />
          <span>生图沿用生文（{textPreset.label}）</span>
        </label>
        {!form.imageUseTextProvider && (
          <label className="field">
            <span>生图用账号</span>
            <select
              value={form.activeImageProvider}
              onChange={(e) => setActiveImageProvider(e.target.value)}
              disabled={disabled}
            >
              {options.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                  {isProviderConfigured(form.providerAccounts, p.id) ? " ✓" : ""}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      <div className="provider-settings__master-detail">
        <aside className="provider-settings__list" aria-label="Provider 账号列表">
          <ul className="provider-settings__list-items">
            {options.map((p) => {
              const configured = isProviderConfigured(form.providerAccounts, p.id);
              const active = p.id === editAccountId;
              return (
                <li key={p.id}>
                  <button
                    type="button"
                    className={`provider-settings__list-item ${active ? "active" : ""}`}
                    onClick={() => setEditAccountId(p.id)}
                    disabled={disabled}
                  >
                    <span className="provider-settings__list-label">{p.label}</span>
                    <span className={`provider-settings__list-status ${configured ? "ok" : "warn"}`}>
                      {configured ? "✓" : "—"}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          <div className="provider-settings__list-add">
            {!showAddForm ? (
              <button
                type="button"
                className="btn btn--secondary provider-settings__add-btn"
                onClick={() => setShowAddForm(true)}
                disabled={disabled}
              >
                + 添加账号
              </button>
            ) : (
              <div className="provider-settings__add-form">
                <label className="field">
                  <span>账号 id（slug）</span>
                  <input
                    type="text"
                    value={newAccount.id}
                    onChange={(e) => {
                      setNewAccount((prev) => ({ ...prev, id: e.target.value }));
                      setAddAccountError(null);
                    }}
                    placeholder="apilio"
                    disabled={disabled}
                  />
                </label>
                <label className="field">
                  <span>显示名称（可选）</span>
                  <input
                    type="text"
                    value={newAccount.label}
                    onChange={(e) => setNewAccount((prev) => ({ ...prev, label: e.target.value }))}
                    placeholder="Apilio 中转"
                    disabled={disabled}
                  />
                </label>
                <label className="field">
                  <span>API 地址</span>
                  <input
                    type="text"
                    value={newAccount.apiBase}
                    onChange={(e) => setNewAccount((prev) => ({ ...prev, apiBase: e.target.value }))}
                    placeholder="https://your-api.example.com/v1"
                    disabled={disabled}
                  />
                </label>
                <label className="field">
                  <span>API Key</span>
                  <input
                    type="password"
                    value={newAccount.apiKey}
                    onChange={(e) => setNewAccount((prev) => ({ ...prev, apiKey: e.target.value }))}
                    placeholder="sk-…"
                    autoComplete="off"
                    disabled={disabled}
                  />
                </label>
                {addAccountError && (
                  <p className="settings-feedback settings-feedback--error">{addAccountError}</p>
                )}
                <div className="field-row">
                  <button type="button" className="btn btn--primary" onClick={handleAddAccount} disabled={disabled}>
                    添加
                  </button>
                  <button
                    type="button"
                    className="btn btn--secondary"
                    onClick={() => {
                      setShowAddForm(false);
                      setAddAccountError(null);
                    }}
                    disabled={disabled}
                  >
                    取消
                  </button>
                </div>
              </div>
            )}
          </div>
        </aside>

        <main className="provider-settings__detail">
          <header className="provider-settings__detail-head">
            <h3 className="provider-settings__detail-title">{editPreset.label}</h3>
            <span className="mono provider-settings__detail-id">{editAccountId}</span>
            <span className={`settings-card__status ${editConfigured ? "ok" : "warn"}`}>
              {editConfigured ? "已配置" : "未配置"}
            </span>
          </header>

          {isUserProviderId(editAccountId) && !isBuiltinProviderId(editAccountId) && (
            <label className="field">
              <span>显示名称</span>
              <input
                type="text"
                value={editAccount.label ?? ""}
                onChange={(e) => updateEditAccount({ label: e.target.value })}
                placeholder={editAccountId}
                disabled={disabled}
              />
            </label>
          )}

          {isUserProviderId(editAccountId) ? (
            <label className="field">
              <span>API 地址</span>
              <input
                type="text"
                value={editAccount.apiBase}
                onChange={(e) => updateEditAccount({ apiBase: e.target.value })}
                placeholder="https://your-api.example.com/v1"
                disabled={disabled}
              />
            </label>
          ) : (
            <p className="field-hint">
              API 地址：<span className="mono">{editPreset.apiBase}</span>
            </p>
          )}

          <label className="field">
            <span>
              {editPreset.label} API Key
              {editConfigured ? "（已配置）" : "（未配置）"}
            </span>
            <input
              type="password"
              value={editAccount.apiKey}
              onChange={(e) => updateEditAccount({ apiKey: e.target.value })}
              placeholder={editConfigured ? "••••••••" : editPreset.keyPlaceholder}
              autoComplete="off"
              disabled={disabled}
            />
          </label>

          <label className="field">
            <span>默认生文 model</span>
            <ModelCatalogPicker
              providerId={editAccountId}
              value={editAccount.textModel}
              onChange={(v) => updateEditAccount({ textModel: v })}
              role="text"
              disabled={disabled}
              placeholder={editPreset.promptModelDefault}
            />
          </label>

          <label className="field">
            <span>默认生图 model</span>
            <ModelCatalogPicker
              providerId={editAccountId}
              value={editAccount.imageModel}
              onChange={(v) => updateEditAccount({ imageModel: v })}
              role="image"
              disabled={disabled}
              placeholder={editPreset.imageModelDefault}
            />
          </label>

          {isUserProviderId(editAccountId) && !isBuiltinProviderId(editAccountId) && (
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => handleDeleteAccount(editAccountId)}
              disabled={disabled || isProviderReferenced(form, editAccountId)}
              title={
                isProviderReferenced(form, editAccountId)
                  ? "该账号正被启用，无法删除"
                  : "从账号库移除（保存后生效）"
              }
            >
              删除此账号
            </button>
          )}
        </main>
      </div>

      <details
        className="provider-settings__advanced"
        open={advancedOpen}
        onToggle={(e) => setAdvancedOpen((e.target as HTMLDetailsElement).open)}
      >
        <summary className="provider-settings__advanced-summary">高级</summary>
        <div className="provider-settings__advanced-body">
          <section className="settings-card">
            <header className="settings-card__head">
              <div className="settings-card__title-row">
                <span className="settings-card__step">{NETWORK_SECTION.step}</span>
                <div>
                  <h3 className="settings-card__title">{NETWORK_SECTION.title}</h3>
                  <span className="settings-card__role-id">（{NETWORK_SECTION.roleId}）</span>
                </div>
              </div>
              <p className="settings-card__purpose">{NETWORK_SECTION.purpose}</p>
            </header>
            <div className="settings-card__body">
              <label className="field">
                <span>HTTP 代理（可选）</span>
                <input
                  type="text"
                  value={form.proxy}
                  onChange={(e) => setField("proxy", e.target.value)}
                  placeholder="http://127.0.0.1:7897"
                  disabled={disabled}
                />
              </label>
              <p className="field-hint">{NETWORK_SECTION.note}</p>
            </div>
          </section>

          <section className="settings-card">
            <header className="settings-card__head">
              <div className="settings-card__title-row">
                <span className="settings-card__step">批</span>
                <div>
                  <h3 className="settings-card__title">批量生图</h3>
                  <span className="settings-card__role-id">（icon_kit / bulk）</span>
                </div>
              </div>
              <p className="settings-card__purpose">
                icon_kit 与 brief <code>generate_tier: bulk</code> 走独立账号与模型
              </p>
            </header>
            <div className="settings-card__body">
              <label className="field">
                <span>批量用账号</span>
                <select
                  value={form.activeBulkImageProvider}
                  onChange={(e) => setField("activeBulkImageProvider", e.target.value)}
                  disabled={disabled}
                >
                  {options.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                      {isProviderConfigured(form.providerAccounts, p.id) ? " ✓" : ""}
                    </option>
                  ))}
                </select>
              </label>
              {isUserProviderId(form.activeBulkImageProvider) && (
                <label className="field">
                  <span>批量 API 地址</span>
                  <input
                    type="text"
                    value={bulkImageAccount.apiBase}
                    onChange={(e) => updateBulkImageAccount({ apiBase: e.target.value })}
                    placeholder="https://your-api.example.com/v1"
                    disabled={disabled}
                  />
                </label>
              )}
              <label className="field">
                <span>
                  {bulkImagePreset.label} 批量 Key
                  {isProviderConfigured(form.providerAccounts, form.activeBulkImageProvider)
                    ? "（已配置）"
                    : "（未配置）"}
                </span>
                <input
                  type="password"
                  value={bulkImageAccount.apiKey}
                  onChange={(e) => updateBulkImageAccount({ apiKey: e.target.value })}
                  placeholder={bulkImagePreset.keyPlaceholder}
                  autoComplete="off"
                  disabled={disabled}
                />
              </label>
              <label className="field">
                <span>批量 model</span>
                <ModelCatalogPicker
                  providerId={form.activeBulkImageProvider}
                  value={form.imageBulkModel}
                  onChange={(v) => setField("imageBulkModel", v)}
                  role="image"
                  disabled={disabled}
                  placeholder="留空则回退主图 model"
                />
              </label>
            </div>
          </section>

          <section className="settings-card">
            <header className="settings-card__head">
              <div className="settings-card__title-row">
                <span className="settings-card__step">{VIDEO_PROVIDER_SECTION.step}</span>
                <div>
                  <h3 className="settings-card__title">{VIDEO_PROVIDER_SECTION.title}</h3>
                  <span className="settings-card__role-id">（{VIDEO_PROVIDER_SECTION.roleId}）</span>
                </div>
                <span
                  className={`settings-card__status ${
                    isVideoConfigured(form.videoAccounts, form.activeVideoProvider) ? "ok" : "warn"
                  }`}
                >
                  {isVideoConfigured(form.videoAccounts, form.activeVideoProvider)
                    ? "已填写"
                    : "未填写"}
                </span>
              </div>
              <p className="settings-card__purpose">{VIDEO_PROVIDER_SECTION.purpose}</p>
            </header>
            <div className="settings-card__body">
              <label className="field">
                <span>视频平台</span>
                <select
                  value={form.activeVideoProvider}
                  onChange={(e) => setField("activeVideoProvider", e.target.value as VideoProviderId)}
                  disabled={disabled}
                >
                  {VIDEO_PROVIDERS.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                      {isVideoConfigured(form.videoAccounts, p.id) ? " ✓" : ""}
                    </option>
                  ))}
                </select>
                {form.activeVideoProvider !== "custom" && (
                  <span className="field-endpoint mono">{videoPreset.apiBase}</span>
                )}
              </label>
              {form.activeVideoProvider === "custom" && (
                <label className="field">
                  <span>自定义平台地址</span>
                  <input
                    type="text"
                    value={videoAccount.apiBase}
                    onChange={(e) => patchActiveVideoAccount({ apiBase: e.target.value })}
                    placeholder="https://…"
                    disabled={disabled}
                  />
                </label>
              )}
              <label className="field">
                <span>
                  {videoPreset.label} API Key
                  {isVideoConfigured(form.videoAccounts, form.activeVideoProvider)
                    ? "（已配置）"
                    : "（未配置）"}
                </span>
                <input
                  type="password"
                  value={videoAccount.apiKey}
                  onChange={(e) => patchActiveVideoAccount({ apiKey: e.target.value })}
                  placeholder={videoPreset.keyPlaceholder}
                  autoComplete="off"
                  disabled={disabled}
                />
              </label>
            </div>
          </section>
        </div>
      </details>

      {error && <p className="settings-feedback settings-feedback--error">{error}</p>}
      {message && <p className="settings-feedback settings-feedback--ok">{message}</p>}

      <div className="settings-actions">
        {!configInfo?.exists && (
          <button
            type="button"
            className="btn btn--secondary"
            onClick={() => void handleInitExample()}
            disabled={disabled}
          >
            从示例创建
          </button>
        )}
        <button
          type="button"
          className="btn btn--primary"
          onClick={() => void handleSave()}
          disabled={disabled}
        >
          {saving ? "保存中…" : "保存 Provider 设置"}
        </button>
      </div>
    </div>
  );
}
