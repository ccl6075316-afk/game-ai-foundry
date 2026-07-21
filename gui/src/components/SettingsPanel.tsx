import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { ConfigInfo, ConfigPatch } from "../vite-env.d";
import {
  API_PROVIDERS,
  VIDEO_PROVIDERS,
  getApiProvider,
  getVideoProvider,
  type ApiProviderId,
  type VideoProviderId,
} from "../settings/apiProviders";
import {
  DEFAULT_AGENT_SKILLS,
  EXECUTOR_LOGIN_HINTS,
} from "../settings/executors";
import {
  AGENT_SECTION,
  CODEX_AGENT_SECTION,
  CURSOR_AGENT_SECTION,
  GODOT_SECTION,
  HERMES_AGENT_SECTION,
  IMAGE_PROVIDER_SECTION,
  PI_AGENT_SECTION,
  TEXT_PROVIDER_SECTION,
  PIPELINE_STEPS,
  VIDEO_PROVIDER_SECTION,
  keyConfigured,
  type SettingsSectionMeta,
  type SettingsTab,
} from "../settings/sections";
import {
  getExecutorPreset,
  loadAgentExecutorsFromConfig,
  serializeAgentExecutors,
  type AgentExecutorId,
  type AgentExecutorPreset,
  type AgentExecutorsMap,
} from "../settings/agentExecutors";
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
  type ProviderAccountsMap,
  type VideoAccountsMap,
  type ProviderAccount,
} from "../settings/providerAccounts";
import { GODOT_DOWNLOAD_URL } from "../settings/toolchain";

interface Props {
  busy: boolean;
  roster?: import("../chat/roster").ColleagueInstance[];
  onSaved?: () => void;
}

interface FormState {
  providerAccounts: ProviderAccountsMap;
  activeTextProvider: ApiProviderId;
  activeImageProvider: ApiProviderId;
  imageUseTextProvider: boolean;
  videoAccounts: VideoAccountsMap;
  activeVideoProvider: VideoProviderId;
  promptUseHost: boolean;
  promptModel: string;
  codeUseHost: boolean;
  codeModel: string;
  proxy: string;
  godotPath: string;
  agentExecutors: AgentExecutorsMap;
}

function fromConfig(data: ConfigInfo["data"]): FormState {
  const prompt = data.prompt || {};
  const code = data.code || {};
  const godot = data.godot || {};

  const loaded = loadProviderAccountsFromConfig(data as Record<string, unknown>);
  const textAccount = getProviderAccount(loaded.providerAccounts, loaded.activeTextProvider);

  return {
    ...loaded,
    promptUseHost: !keyConfigured(String(prompt.api_key || "")),
    promptModel: String(prompt.model || textAccount.textModel),
    codeUseHost: !keyConfigured(String(code.api_key || "")),
    codeModel: String(code.model || textAccount.textModel),
    proxy: String(
      (data.host as Record<string, unknown> | undefined)?.proxy ||
        (data.image as Record<string, unknown> | undefined)?.proxy ||
        prompt.proxy ||
        "",
    ),
    godotPath: String(godot.engine_path || ""),
    agentExecutors: loadAgentExecutorsFromConfig(data as Record<string, unknown>),
  };
}

function toPatch(form: FormState): ConfigPatch {
  const text = resolveActiveTextSettings(form);
  const image = resolveActiveImageSettings(form);
  const video = resolveActiveVideoSettings(form);

  const promptPatch: ConfigPatch["prompt"] = {
    model: form.promptModel || undefined,
  };
  if (form.promptUseHost) {
    promptPatch.api_key = null;
    promptPatch.api_base = null;
  }

  const codePatch: ConfigPatch["code"] = {
    model: form.codeModel || undefined,
  };
  if (form.codeUseHost) {
    codePatch.api_key = null;
    codePatch.api_base = null;
  }

  const agents: NonNullable<ConfigPatch["agents"]> = {
    executors: serializeAgentExecutors(form.agentExecutors),
    brief: {
      executor: "pi",
    },
    it: {
      executor: "pi",
    },
    orchestrator: {
      skill: DEFAULT_AGENT_SKILLS.orchestrator,
    },
    "godot-developer": {
      skill: DEFAULT_AGENT_SKILLS["godot-developer"],
    },
  };

  return {
    provider_accounts: serializeProviderAccounts(form.providerAccounts),
    video_accounts: serializeVideoAccounts(form.videoAccounts),
    host: {
      provider: text.provider,
      api_key: text.api_key,
      model: text.model,
      api_base: text.api_base,
      proxy: text.proxy,
    },
    prompt: promptPatch,
    code: codePatch,
    image: {
      provider: image.provider,
      use_text_provider: image.use_text_provider,
      api_key: image.api_key,
      model: image.model,
      api_base: image.api_base,
      proxy: image.proxy,
    },
    video: {
      provider: video.provider,
      api_key: video.api_key,
      api_base: video.api_base,
    },
    godot: {
      engine_path: form.godotPath || undefined,
    },
    agents,
  };
}

function SectionCard({
  meta,
  configured,
  statusOk = "已填写",
  statusWarn = "未填写",
  children,
}: {
  meta: SettingsSectionMeta;
  configured?: boolean;
  statusOk?: string;
  statusWarn?: string;
  children: ReactNode;
}) {
  return (
    <section className="settings-card">
      <header className="settings-card__head">
        <div className="settings-card__title-row">
          <span className="settings-card__step">{meta.step}</span>
          <div>
            <h3 className="settings-card__title">{meta.title}</h3>
            <span className="settings-card__role-id">（{meta.roleId}）</span>
          </div>
          {configured !== undefined && (
            <span className={`settings-card__status ${configured ? "ok" : "warn"}`}>
              {configured ? statusOk : statusWarn}
            </span>
          )}
        </div>
        <p className="settings-card__purpose">{meta.purpose}</p>
        {meta.note && <p className="settings-card__note">{meta.note}</p>}
      </header>
      <div className="settings-card__body">{children}</div>
    </section>
  );
}

function ProviderAccountChips({
  accounts,
  activeId,
  onSelect,
  disabled,
}: {
  accounts: ProviderAccountsMap;
  activeId: ApiProviderId;
  onSelect: (id: ApiProviderId) => void;
  disabled: boolean;
}) {
  return (
    <div className="provider-account-chips" aria-label="Provider 账号库">
      <span className="provider-account-chips__label">可配置多家，已配显示 ✓；点击切换编辑</span>
      <div className="provider-account-chips__row">
        {API_PROVIDERS.map((p) => {
          const configured = isProviderConfigured(accounts, p.id);
          const active = p.id === activeId;
          return (
            <button
              key={p.id}
              type="button"
              className={`provider-chip ${active ? "active" : ""} ${configured ? "configured" : "empty"}`}
              onClick={() => onSelect(p.id)}
              disabled={disabled}
              title={configured ? `${p.label} 已配置` : `${p.label} 未配置`}
            >
              {p.label}
              <span className="provider-chip__status">{configured ? "✓" : "—"}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function VideoAccountChips({
  accounts,
  activeId,
  onSelect,
  disabled,
}: {
  accounts: VideoAccountsMap;
  activeId: VideoProviderId;
  onSelect: (id: VideoProviderId) => void;
  disabled: boolean;
}) {
  return (
    <div className="provider-account-chips" aria-label="视频 Provider 账号库">
      <span className="provider-account-chips__label">视频平台（可选多家）</span>
      <div className="provider-account-chips__row">
        {VIDEO_PROVIDERS.map((p) => {
          const configured = isVideoConfigured(accounts, p.id);
          const active = p.id === activeId;
          return (
            <button
              key={p.id}
              type="button"
              className={`provider-chip ${active ? "active" : ""} ${configured ? "configured" : "empty"}`}
              onClick={() => onSelect(p.id)}
              disabled={disabled}
            >
              {p.label}
              <span className="provider-chip__status">{configured ? "✓" : "—"}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function ProviderSelect({
  value,
  onChange,
  disabled,
}: {
  value: ApiProviderId;
  onChange: (id: ApiProviderId) => void;
  disabled: boolean;
}) {
  const preset = getApiProvider(value);
  return (
    <label className="field">
      <span>在线平台</span>
      <select value={value} onChange={(e) => onChange(e.target.value as ApiProviderId)} disabled={disabled}>
        {API_PROVIDERS.map((p) => (
          <option key={p.id} value={p.id}>
            {p.label}
          </option>
        ))}
      </select>
      <span className="field-hint">{preset.description}</span>
      {value !== "custom" && (
        <span className="field-endpoint mono">{preset.apiBase}</span>
      )}
    </label>
  );
}

function AgentProviderSelect({
  value,
  accounts,
  onChange,
  disabled,
}: {
  value: ApiProviderId;
  accounts: ProviderAccountsMap;
  onChange: (id: ApiProviderId) => void;
  disabled: boolean;
}) {
  return (
    <label className="field">
      <span>Provider（账号库 id）</span>
      <select value={value} onChange={(e) => onChange(e.target.value as ApiProviderId)} disabled={disabled}>
        {API_PROVIDERS.map((p) => {
          const ok = isProviderConfigured(accounts, p.id);
          return (
            <option key={p.id} value={p.id}>
              {p.label}
              {ok ? " ✓" : "（未填 Key）"}
            </option>
          );
        })}
      </select>
      {!isProviderConfigured(accounts, value) && (
        <span className="settings-card__note">
          所选 Provider 尚未填 Key，回合可能失败；请先到 Provider 页补全。
        </span>
      )}
    </label>
  );
}

export function SettingsPanel({ busy, onSaved }: Props) {
  const [tab, setTab] = useState<SettingsTab>("providers");
  const [configInfo, setConfigInfo] = useState<ConfigInfo | null>(null);
  const [form, setForm] = useState<FormState>(() => fromConfig({}));
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const info = await window.gameFactory.getConfig();
      setConfigInfo(info);
      setForm(fromConfig(info.data));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const setField = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setMessage(null);
  };

  const setActiveTextProvider = (id: ApiProviderId) => {
    setForm((prev) => ({ ...prev, activeTextProvider: id }));
    setMessage(null);
  };

  const updateTextAccount = (patch: Partial<ProviderAccount>) => {
    setForm((prev) => ({
      ...prev,
      providerAccounts: updateProviderAccount(prev.providerAccounts, prev.activeTextProvider, patch),
    }));
    setMessage(null);
  };

  const setActiveImageProvider = (id: ApiProviderId) => {
    setForm((prev) => ({ ...prev, activeImageProvider: id, imageUseTextProvider: false }));
    setMessage(null);
  };

  const updateImageAccount = (patch: Partial<ProviderAccount>) => {
    setForm((prev) => {
      const providerId = prev.imageUseTextProvider ? prev.activeTextProvider : prev.activeImageProvider;
      return {
        ...prev,
        providerAccounts: updateProviderAccount(prev.providerAccounts, providerId, patch),
      };
    });
    setMessage(null);
  };

  const setActiveVideoProvider = (id: VideoProviderId) => {
    setForm((prev) => ({ ...prev, activeVideoProvider: id }));
    setMessage(null);
  };

  const patchActiveVideoAccount = (patch: Partial<{ apiKey: string; apiBase: string }>) => {
    setForm((prev) => ({
      ...prev,
      videoAccounts: applyVideoAccountPatch(prev.videoAccounts, prev.activeVideoProvider, patch),
    }));
    setMessage(null);
  };

  const updateAgentExecutor = (executorId: AgentExecutorId, patch: Partial<AgentExecutorPreset>) => {
    setForm((prev) => ({
      ...prev,
      agentExecutors: {
        ...prev.agentExecutors,
        [executorId]: {
          ...getExecutorPreset(prev.agentExecutors, executorId),
          ...patch,
        },
      },
    }));
    setMessage(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    const codexPreset = getExecutorPreset(form.agentExecutors, "codex");
    try {
      const res = await window.gameFactory.saveConfig(toPatch(form));
      if (!res.ok) throw new Error(res.error || "保存失败");

      let syncNote = "";
      if (window.gameFactory.executorStep && codexPreset.use_third_party) {
        const syncRes = await window.gameFactory.executorStep("codex", "sync_api");
        if (!syncRes.data?.ok) {
          syncNote = `；Codex 第三方同步失败：${syncRes.data?.error || syncRes.stderr || "未知错误"}`;
        } else if (syncRes.data?.skipped) {
          syncNote = "";
        } else {
          syncNote = "；已同步 Codex 第三方 API";
        }
      }

      setMessage(`已保存${syncNote}`);
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

  const handleBrowseGodot = async () => {
    const picked = await window.gameFactory.pickFile({
      title: "选择 Godot 可执行文件",
      filters: [{ name: "Godot", extensions: ["exe"] }, { name: "All", extensions: ["*"] }],
    });
    if (picked) setField("godotPath", picked);
  };

  const disabled = busy || loading || saving;
  const textAccount = getProviderAccount(form.providerAccounts, form.activeTextProvider);
  const textPreset = getApiProvider(form.activeTextProvider);
  const imageProviderId = form.imageUseTextProvider ? form.activeTextProvider : form.activeImageProvider;
  const imageAccount = getProviderAccount(form.providerAccounts, imageProviderId);
  const imagePreset = getApiProvider(imageProviderId);
  const videoAccount = getVideoAccount(form.videoAccounts, form.activeVideoProvider);
  const videoPreset = getVideoProvider(form.activeVideoProvider);

  const hostKeyOk = isProviderConfigured(form.providerAccounts, form.activeTextProvider);
  const piPreset = getExecutorPreset(form.agentExecutors, "pi");
  const hermesPreset = getExecutorPreset(form.agentExecutors, "hermes");
  const codexPreset = getExecutorPreset(form.agentExecutors, "codex");
  const piProvider = (piPreset.provider || "openrouter") as ApiProviderId;
  const hermesProvider = (hermesPreset.provider || "openrouter") as ApiProviderId;
  const codexProvider = (codexPreset.provider || "openrouter") as ApiProviderId;

  return (
    <aside className="side-panel settings-panel">
      <div className="side-panel__head">
        <h2>设置</h2>
        <p className="hint">各角色用什么工具、哪个在线账号——保存后整条制作流程共用。</p>
      </div>

      <div className="settings-flow" aria-label="制作流程">
        {PIPELINE_STEPS.map((s, i) => (
          <span key={s.label} className="settings-flow__item">
            {i > 0 && <span className="settings-flow__arrow">→</span>}
            <span className="settings-flow__label">{s.label}</span>
            <span className="settings-flow__desc">{s.desc}</span>
          </span>
        ))}
      </div>

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

      <div className="settings-tabs">
        <button
          type="button"
          className={`settings-tab ${tab === "providers" ? "active" : ""}`}
          onClick={() => setTab("providers")}
        >
          Provider
        </button>
        <button
          type="button"
          className={`settings-tab ${tab === "agents" ? "active" : ""}`}
          onClick={() => setTab("agents")}
        >
          Agent
        </button>
        <button
          type="button"
          className={`settings-tab ${tab === "local" ? "active" : ""}`}
          onClick={() => setTab("local")}
        >
          本机工具
        </button>
      </div>

      {loading ? (
        <p className="hint">加载中…</p>
      ) : (
        <form
          className="settings-form"
          onSubmit={(e) => {
            e.preventDefault();
            void handleSave();
          }}
        >
          {tab === "providers" && (
            <>
              <SectionCard meta={TEXT_PROVIDER_SECTION} configured={hostKeyOk}>
                <ProviderAccountChips
                  accounts={form.providerAccounts}
                  activeId={form.activeTextProvider}
                  onSelect={setActiveTextProvider}
                  disabled={disabled}
                />
                <ProviderSelect
                  value={form.activeTextProvider}
                  onChange={setActiveTextProvider}
                  disabled={disabled}
                />
                {form.activeTextProvider === "custom" && (
                  <label className="field">
                    <span>API 地址</span>
                    <input
                      type="text"
                      value={textAccount.apiBase}
                      onChange={(e) => updateTextAccount({ apiBase: e.target.value })}
                      placeholder="https://your-api.example.com/v1"
                      disabled={disabled}
                    />
                  </label>
                )}
                <label className="field">
                  <span>
                    {textPreset.label} API Key
                    {hostKeyOk ? "（已配置）" : "（未配置）"}
                  </span>
                  <input
                    type="password"
                    value={textAccount.apiKey}
                    onChange={(e) => updateTextAccount({ apiKey: e.target.value })}
                    placeholder={hostKeyOk ? "••••••••" : textPreset.keyPlaceholder}
                    autoComplete="off"
                    disabled={disabled}
                  />
                </label>
                <p className="field-hint">
                  每家平台独立保存；切换到未配置的平台时密钥框为空，填好后点保存即可。
                </p>
                <label className="field">
                  <span>生文 model（当前启用：{textPreset.label}）</span>
                  <input
                    type="text"
                    value={textAccount.textModel}
                    onChange={(e) => updateTextAccount({ textModel: e.target.value })}
                    placeholder={textPreset.promptModelDefault}
                    disabled={disabled}
                  />
                </label>
                <p className="field-hint">
                  OpenRouter 靠 <code>model</code> 路由（如 <code>deepseek/deepseek-chat</code>）；官方 API 用
                  平台自己的模型名（如 <code>deepseek-chat</code>）。
                </p>
                <label className="field">
                  <span>代理（可选，生文/生图共用）</span>
                  <input
                    type="text"
                    value={form.proxy}
                    onChange={(e) => setField("proxy", e.target.value)}
                    placeholder="http://127.0.0.1:7897"
                    disabled={disabled}
                  />
                </label>
              </SectionCard>

              <SectionCard
                meta={IMAGE_PROVIDER_SECTION}
                configured={
                  form.imageUseTextProvider
                    ? hostKeyOk && Boolean(imageAccount.imageModel.trim())
                    : isProviderConfigured(form.providerAccounts, form.activeImageProvider)
                }
              >
                <label className="field field--checkbox">
                  <input
                    type="checkbox"
                    checked={form.imageUseTextProvider}
                    onChange={(e) => setField("imageUseTextProvider", e.target.checked)}
                    disabled={disabled}
                  />
                  <span>沿用当前生文平台（{textPreset.label}）</span>
                </label>
                {!form.imageUseTextProvider && (
                  <>
                    <ProviderAccountChips
                      accounts={form.providerAccounts}
                      activeId={form.activeImageProvider}
                      onSelect={setActiveImageProvider}
                      disabled={disabled}
                    />
                    <ProviderSelect
                      value={form.activeImageProvider}
                      onChange={setActiveImageProvider}
                      disabled={disabled}
                    />
                    <label className="field">
                      <span>
                        {imagePreset.label} 生图 Key
                        {isProviderConfigured(form.providerAccounts, form.activeImageProvider)
                          ? "（已配置）"
                          : "（未配置）"}
                      </span>
                      <input
                        type="password"
                        value={imageAccount.apiKey}
                        onChange={(e) => updateImageAccount({ apiKey: e.target.value })}
                        placeholder={imagePreset.keyPlaceholder}
                        autoComplete="off"
                        disabled={disabled}
                      />
                    </label>
                  </>
                )}
                <label className="field">
                  <span>生图 model</span>
                  <input
                    type="text"
                    value={imageAccount.imageModel}
                    onChange={(e) => updateImageAccount({ imageModel: e.target.value })}
                    placeholder={imagePreset.imageModelDefault}
                    disabled={disabled}
                  />
                </label>
                <p className="field-hint">
                  OpenRouter 生图请填完整 slug。GPT Image 2：
                  <code>openai/gpt-image-2</code>（专用 Images API）。
                  Gemini 图模：
                  <code>google/gemini-3.1-flash-image</code>。
                  可与生文用不同平台。
                </p>
              </SectionCard>

              <SectionCard
                meta={VIDEO_PROVIDER_SECTION}
                configured={isVideoConfigured(form.videoAccounts, form.activeVideoProvider)}
              >
                <VideoAccountChips
                  accounts={form.videoAccounts}
                  activeId={form.activeVideoProvider}
                  onSelect={setActiveVideoProvider}
                  disabled={disabled}
                />
                <label className="field">
                  <span>当前启用的视频平台</span>
                  <select
                    value={form.activeVideoProvider}
                    onChange={(e) => setActiveVideoProvider(e.target.value as VideoProviderId)}
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
              </SectionCard>
            </>
          )}

          {tab === "agents" && (
            <>
              <SectionCard meta={AGENT_SECTION}>
                <p className="settings-linked">
                  <strong>Provider 页</strong>：填各平台 API Key；此处仅为各 Agent 工具选择默认账号库 id 与模型。
                  <br />
                  <strong>雇人 / 对话</strong>：同事实例可单独覆盖；保存实例不会回写此处预设。
                </p>
              </SectionCard>

              <SectionCard
                meta={PI_AGENT_SECTION}
                configured={isProviderConfigured(form.providerAccounts, piProvider)}
              >
                <AgentProviderSelect
                  value={piProvider}
                  accounts={form.providerAccounts}
                  disabled={disabled}
                  onChange={(id) => updateAgentExecutor("pi", { provider: id })}
                />
                <label className="field">
                  <span>默认模型（可选）</span>
                  <input
                    type="text"
                    value={piPreset.model ?? ""}
                    disabled={disabled}
                    placeholder={
                      getProviderAccount(form.providerAccounts, piProvider).textModel || "留空则用账号默认"
                    }
                    onChange={(e) => updateAgentExecutor("pi", { model: e.target.value })}
                  />
                </label>
                <p className="settings-card__note">
                  策划 / IT 固定使用内置 Pi；需 Node ≥22.19 与 Provider Key。
                </p>
              </SectionCard>

              <SectionCard
                meta={HERMES_AGENT_SECTION}
                configured={isProviderConfigured(form.providerAccounts, hermesProvider)}
              >
                <AgentProviderSelect
                  value={hermesProvider}
                  accounts={form.providerAccounts}
                  disabled={disabled}
                  onChange={(id) => updateAgentExecutor("hermes", { provider: id })}
                />
                <p className="settings-card__note">
                  保存后到「环境 → Hermes → 同步 API」将所选 Provider 写入 Hermes。
                </p>
              </SectionCard>

              <SectionCard meta={CODEX_AGENT_SECTION}>
                <label className="field field--checkbox">
                  <input
                    type="checkbox"
                    checked={Boolean(codexPreset.use_third_party)}
                    disabled={disabled}
                    onChange={(e) =>
                      updateAgentExecutor("codex", { use_third_party: e.target.checked })
                    }
                  />
                  <span>用第三方（账号库 Key，保存时同步到 Codex）</span>
                </label>
                {codexPreset.use_third_party ? (
                  <>
                    <AgentProviderSelect
                      value={codexProvider}
                      accounts={form.providerAccounts}
                      disabled={disabled}
                      onChange={(id) => updateAgentExecutor("codex", { provider: id })}
                    />
                    <label className="field">
                      <span>模型（可选）</span>
                      <input
                        type="text"
                        value={codexPreset.model ?? ""}
                        disabled={disabled}
                        placeholder={
                          getProviderAccount(form.providerAccounts, codexProvider).textModel ||
                          "账号默认模型"
                        }
                        onChange={(e) => updateAgentExecutor("codex", { model: e.target.value })}
                      />
                    </label>
                  </>
                ) : (
                  <p className="settings-card__note">{EXECUTOR_LOGIN_HINTS.codex}</p>
                )}
              </SectionCard>

              <SectionCard meta={CURSOR_AGENT_SECTION}>
                <p className="settings-card__note">
                  Cursor 仅支持本机登录/订阅，<strong>第三方不可用</strong>。
                </p>
                <p className="settings-card__note">{EXECUTOR_LOGIN_HINTS.cursor}</p>
              </SectionCard>
            </>
          )}

          {tab === "local" && (
            <SectionCard meta={GODOT_SECTION} configured={Boolean(form.godotPath.trim())}>
              <label className="field">
                <span>Godot 可执行文件</span>
                <div className="field-row">
                  <input
                    type="text"
                    value={form.godotPath}
                    onChange={(e) => setField("godotPath", e.target.value)}
                    placeholder="Godot_v4.x_mono_console.exe"
                    disabled={disabled}
                  />
                  <button
                    type="button"
                    className="btn btn--secondary"
                    onClick={() => void handleBrowseGodot()}
                    disabled={disabled}
                  >
                    浏览
                  </button>
                </div>
                <span className="field-hint">用于打开工程、导入素材、检查项目是否正常</span>
              </label>
              <div className="field-row field-row--wrap">
                <button
                  type="button"
                  className="btn btn--secondary"
                  disabled={disabled}
                  onClick={() => void window.gameFactory.openExternal(GODOT_DOWNLOAD_URL)}
                >
                  下载 Godot .NET（官方）
                </button>
                <span className="field-hint">
                  选 <strong>.NET / Mono</strong> 版 zip，解压即用；Windows 填 <code>*_console.exe</code>
                </span>
              </div>
            </SectionCard>
          )}

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
            <button type="submit" className="btn btn--primary" disabled={disabled}>
              {saving ? "保存中…" : "保存设置"}
            </button>
          </div>
        </form>
      )}
    </aside>
  );
}
