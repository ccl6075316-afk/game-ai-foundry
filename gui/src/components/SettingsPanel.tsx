import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { ConfigInfo, ConfigPatch, DoctorReport } from "../vite-env.d";
import {
  API_PROVIDERS,
  VIDEO_PROVIDERS,
  detectApiProvider,
  detectVideoProvider,
  getApiProvider,
  getVideoProvider,
  resolveApiBase,
  resolveVideoBase,
  type ApiProviderId,
  type VideoProviderId,
} from "../settings/apiProviders";
import {
  CODE_EXECUTORS,
  DEFAULT_AGENT_SKILLS,
  HOST_EXECUTORS,
  executorAvailable,
  parseExecutor,
  type AgentExecutor,
} from "../settings/executors";
import {
  CODE_SECTION,
  GODOT_SECTION,
  HOST_SECTION,
  IMAGE_SECTION,
  PIPELINE_STEPS,
  PROMPT_SECTION,
  VIDEO_SECTION,
  keyConfigured,
  type SettingsSectionMeta,
  type SettingsTab,
} from "../settings/sections";

interface Props {
  busy: boolean;
  onSaved?: () => void;
}

interface FormState {
  hostProvider: ApiProviderId;
  hostApiBase: string;
  hostApiKey: string;
  hostModel: string;
  promptUseHost: boolean;
  promptProvider: ApiProviderId;
  promptApiBase: string;
  promptApiKey: string;
  promptModel: string;
  codeUseHost: boolean;
  codeProvider: ApiProviderId;
  codeApiBase: string;
  codeApiKey: string;
  codeModel: string;
  imageProvider: ApiProviderId;
  imageApiBase: string;
  imageApiKey: string;
  imageModel: string;
  proxy: string;
  videoProvider: VideoProviderId;
  videoApiBase: string;
  videoApiKey: string;
  godotPath: string;
  hostExecutor: AgentExecutor;
  codeExecutor: AgentExecutor;
}

function fromConfig(data: ConfigInfo["data"]): FormState {
  const host = data.host || {};
  const image = data.image || {};
  const prompt = data.prompt || {};
  const code = data.code || {};
  const video = data.video || {};
  const godot = data.godot || {};
  const agents = data.agents || {};
  const orchestrator = (agents.orchestrator || {}) as Record<string, unknown>;
  const godotDev = (agents["godot-developer"] || {}) as Record<string, unknown>;

  const hostKey = String(host.api_key || image.api_key || "");
  const hostBase = String(host.api_base || image.api_base || "");
  const hostProvider = detectApiProvider(hostBase);
  const promptKey = String(prompt.api_key || "");
  const codeKey = String(code.api_key || "");
  const promptProvider = detectApiProvider(String(prompt.api_base || hostBase));
  const codeProvider = detectApiProvider(String(code.api_base || hostBase));
  const imageProvider = detectApiProvider(String(image.api_base || ""));

  return {
    hostProvider,
    hostApiBase: hostBase || getApiProvider(hostProvider).apiBase,
    hostApiKey: hostKey,
    hostModel: String(host.model || getApiProvider(hostProvider).promptModelDefault),
    promptUseHost: !keyConfigured(promptKey),
    promptProvider,
    promptApiBase: String(prompt.api_base || getApiProvider(promptProvider).apiBase),
    promptApiKey: promptKey,
    promptModel: String(prompt.model || getApiProvider(promptProvider).promptModelDefault),
    codeUseHost: !keyConfigured(codeKey),
    codeProvider,
    codeApiBase: String(code.api_base || getApiProvider(codeProvider).apiBase),
    codeApiKey: codeKey,
    codeModel: String(code.model || getApiProvider(codeProvider).promptModelDefault),
    imageProvider,
    imageApiBase: String(image.api_base || getApiProvider(imageProvider).apiBase),
    imageApiKey: String(image.api_key || ""),
    imageModel: String(image.model || getApiProvider(imageProvider).imageModelDefault),
    proxy: String(host.proxy || image.proxy || prompt.proxy || ""),
    videoProvider: detectVideoProvider(String(video.api_base || "")),
    videoApiBase: String(video.api_base || getVideoProvider("seedance").apiBase),
    videoApiKey: String(video.api_key || ""),
    godotPath: String(godot.engine_path || ""),
    hostExecutor: parseExecutor(orchestrator.executor, "hermes"),
    codeExecutor: parseExecutor(godotDev.executor, "codex"),
  };
}

function toPatch(form: FormState): ConfigPatch {
  const hostBase = resolveApiBase(form.hostProvider, form.hostApiBase);
  const imageBase = resolveApiBase(form.imageProvider, form.imageApiBase);

  const promptPatch: ConfigPatch["prompt"] = {
    model: form.promptModel || undefined,
  };
  if (form.promptUseHost) {
    promptPatch.api_key = null;
    promptPatch.api_base = null;
  } else {
    promptPatch.api_key = form.promptApiKey || undefined;
    promptPatch.api_base = resolveApiBase(form.promptProvider, form.promptApiBase) || undefined;
  }

  const codePatch: ConfigPatch["code"] = {
    model: form.codeModel || undefined,
  };
  if (form.codeUseHost) {
    codePatch.api_key = null;
    codePatch.api_base = null;
  } else {
    codePatch.api_key = form.codeApiKey || undefined;
    codePatch.api_base = resolveApiBase(form.codeProvider, form.codeApiBase) || undefined;
  }

  return {
    host: {
      api_key: form.hostApiKey || undefined,
      model: form.hostModel || undefined,
      api_base: hostBase || undefined,
      proxy: form.proxy || undefined,
    },
    prompt: promptPatch,
    code: codePatch,
    image: {
      api_key: form.imageApiKey || undefined,
      model: form.imageModel || undefined,
      api_base: imageBase || undefined,
      proxy: form.proxy || undefined,
    },
    video: {
      api_key: form.videoApiKey || undefined,
      api_base: resolveVideoBase(form.videoProvider, form.videoApiBase) || undefined,
    },
    godot: {
      engine_path: form.godotPath || undefined,
    },
    agents: {
      orchestrator: {
        executor: form.hostExecutor,
        skill: DEFAULT_AGENT_SKILLS.orchestrator,
      },
      "godot-developer": {
        executor: form.codeExecutor,
        skill: DEFAULT_AGENT_SKILLS["godot-developer"],
      },
    },
  };
}

function ExecutorPicker({
  name,
  options,
  value,
  executors,
  disabled,
  onChange,
}: {
  name: string;
  options: typeof HOST_EXECUTORS;
  value: AgentExecutor;
  executors: DoctorReport["executors"] | undefined;
  disabled: boolean;
  onChange: (id: AgentExecutor) => void;
}) {
  const selected = options.find((o) => o.id === value);
  const selectedOk = executorAvailable(executors, value);
  const selectedInfo = executors?.[value];

  return (
    <div className="executor-picker">
      <div className="executor-picker__options">
        {options.map((opt) => {
          const ok = executorAvailable(executors, opt.id);
          return (
            <label
              key={opt.id}
              className={`executor-option ${value === opt.id ? "active" : ""} ${ok ? "" : "unavailable"}`}
            >
              <input
                type="radio"
                name={name}
                value={opt.id}
                checked={value === opt.id}
                onChange={() => onChange(opt.id)}
                disabled={disabled}
              />
              <span className="executor-option__label">{opt.label}</span>
              <span className={`executor-option__dot ${ok ? "ok" : "no"}`} title={ok ? "本机可用" : "本机未检测到"} />
            </label>
          );
        })}
      </div>
      {selected && <p className="field-hint">{selected.description}</p>}
      {selected && !selectedOk && selectedInfo?.hints?.[0] && (
        <p className="settings-card__note">{selectedInfo.hints[0]}</p>
      )}
    </div>
  );
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

export function SettingsPanel({ busy, onSaved }: Props) {
  const [tab, setTab] = useState<SettingsTab>("ai");
  const [configInfo, setConfigInfo] = useState<ConfigInfo | null>(null);
  const [doctor, setDoctor] = useState<DoctorReport | null>(null);
  const [form, setForm] = useState<FormState>(() => fromConfig({}));
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [info, docRes] = await Promise.all([
        window.gameFactory.getConfig(),
        window.gameFactory.doctor(),
      ]);
      setConfigInfo(info);
      setDoctor(docRes.data ?? null);
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

  const applyHostProvider = (id: ApiProviderId) => {
    const preset = getApiProvider(id);
    setForm((prev) => ({
      ...prev,
      hostProvider: id,
      hostApiBase: id === "custom" ? prev.hostApiBase : preset.apiBase,
      hostModel: prev.hostModel || preset.promptModelDefault,
    }));
    setMessage(null);
  };

  const applyImageProvider = (id: ApiProviderId) => {
    const preset = getApiProvider(id);
    setForm((prev) => ({
      ...prev,
      imageProvider: id,
      imageApiBase: id === "custom" ? prev.imageApiBase : preset.apiBase,
      imageModel: prev.imageModel || preset.imageModelDefault,
    }));
    setMessage(null);
  };

  const applyPromptProvider = (id: ApiProviderId) => {
    const preset = getApiProvider(id);
    setForm((prev) => ({
      ...prev,
      promptProvider: id,
      promptApiBase: id === "custom" ? prev.promptApiBase : preset.apiBase,
      promptModel: prev.promptModel || preset.promptModelDefault,
    }));
    setMessage(null);
  };

  const applyVideoProvider = (id: VideoProviderId) => {
    const preset = getVideoProvider(id);
    setForm((prev) => ({
      ...prev,
      videoProvider: id,
      videoApiBase: id === "custom" ? prev.videoApiBase : preset.apiBase,
    }));
    setMessage(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const res = await window.gameFactory.saveConfig(toPatch(form));
      if (!res.ok) throw new Error(res.error || "保存失败");
      setMessage("已保存");
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
  const videoPreset = getVideoProvider(form.videoProvider);
  const hostProviderPreset = getApiProvider(form.hostProvider);

  const hostKeyOk = keyConfigured(form.hostApiKey);
  const promptKeyOk = form.promptUseHost ? hostKeyOk : keyConfigured(form.promptApiKey);
  const codeKeyOk = form.codeUseHost ? hostKeyOk : keyConfigured(form.codeApiKey);

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
          className={`settings-tab ${tab === "ai" ? "active" : ""}`}
          onClick={() => setTab("ai")}
        >
          在线服务
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
          {tab === "ai" && (
            <>
              <SectionCard meta={HOST_SECTION} configured={hostKeyOk}>
                <p className="settings-linked">谁来对话（本机工具）</p>
                <ExecutorPicker
                  name="host-executor"
                  options={HOST_EXECUTORS}
                  value={form.hostExecutor}
                  executors={doctor?.executors}
                  disabled={disabled}
                  onChange={(id) => setField("hostExecutor", id)}
                />
                <p className="settings-linked">在线账号（文案 / 程序未单独配置时共用）</p>
                <ProviderSelect
                  value={form.hostProvider}
                  onChange={applyHostProvider}
                  disabled={disabled}
                />
                {form.hostProvider === "custom" && (
                  <label className="field">
                    <span>自定义平台地址</span>
                    <input
                      type="text"
                      value={form.hostApiBase}
                      onChange={(e) => setField("hostApiBase", e.target.value)}
                      placeholder="https://your-api.example.com/v1"
                      disabled={disabled}
                    />
                  </label>
                )}
                <label className="field">
                  <span>账号密钥</span>
                  <input
                    type="password"
                    value={form.hostApiKey}
                    onChange={(e) => setField("hostApiKey", e.target.value)}
                    placeholder={hostProviderPreset.keyPlaceholder}
                    autoComplete="off"
                    disabled={disabled}
                  />
                </label>
                <label className="field">
                  <span>对话模型</span>
                  <input
                    type="text"
                    value={form.hostModel}
                    onChange={(e) => setField("hostModel", e.target.value)}
                    placeholder={hostProviderPreset.promptModelDefault}
                    disabled={disabled}
                  />
                  <span className="field-hint">项目经理自己对话、以及回退给文案/程序时使用</span>
                </label>
              </SectionCard>

              <p className="settings-subheading">创作团队 · 在线账号与模型</p>

              <SectionCard meta={PROMPT_SECTION} configured={promptKeyOk}>
                <label className="field field--checkbox">
                  <input
                    type="checkbox"
                    checked={form.promptUseHost}
                    onChange={(e) => setField("promptUseHost", e.target.checked)}
                    disabled={disabled}
                  />
                  <span>沿用项目经理的在线账号（推荐）</span>
                </label>
                {!form.promptUseHost && (
                  <>
                    <ProviderSelect
                      value={form.promptProvider}
                      onChange={applyPromptProvider}
                      disabled={disabled}
                    />
                    {form.promptProvider === "custom" && (
                      <label className="field">
                        <span>自定义平台地址</span>
                        <input
                          type="text"
                          value={form.promptApiBase}
                          onChange={(e) => setField("promptApiBase", e.target.value)}
                          placeholder="https://your-api.example.com/v1"
                          disabled={disabled}
                        />
                      </label>
                    )}
                    <label className="field">
                      <span>账号密钥</span>
                      <input
                        type="password"
                        value={form.promptApiKey}
                        onChange={(e) => setField("promptApiKey", e.target.value)}
                        placeholder={getApiProvider(form.promptProvider).keyPlaceholder}
                        autoComplete="off"
                        disabled={disabled}
                      />
                    </label>
                  </>
                )}
                {form.promptUseHost && (
                  <p className="settings-linked">未单独配置时，运行时会自动使用项目经理（host）的账号与平台。</p>
                )}
                <label className="field">
                  <span>文案模型</span>
                  <input
                    type="text"
                    value={form.promptModel}
                    onChange={(e) => setField("promptModel", e.target.value)}
                    placeholder={getApiProvider(form.promptProvider).promptModelDefault}
                    disabled={disabled}
                  />
                </label>
              </SectionCard>

              <SectionCard meta={IMAGE_SECTION} configured={keyConfigured(form.imageApiKey)}>
                <ProviderSelect
                  value={form.imageProvider}
                  onChange={applyImageProvider}
                  disabled={disabled}
                />
                {form.imageProvider === "custom" && (
                  <label className="field">
                    <span>自定义平台地址</span>
                    <input
                      type="text"
                      value={form.imageApiBase}
                      onChange={(e) => setField("imageApiBase", e.target.value)}
                      placeholder="https://your-api.example.com/v1"
                      disabled={disabled}
                    />
                  </label>
                )}
                <label className="field">
                  <span>账号密钥</span>
                  <input
                    type="password"
                    value={form.imageApiKey}
                    onChange={(e) => setField("imageApiKey", e.target.value)}
                    placeholder={getApiProvider(form.imageProvider).keyPlaceholder}
                    autoComplete="off"
                    disabled={disabled}
                  />
                </label>
                <label className="field">
                  <span>绘画模型</span>
                  <input
                    type="text"
                    value={form.imageModel}
                    onChange={(e) => setField("imageModel", e.target.value)}
                    placeholder={getApiProvider(form.imageProvider).imageModelDefault}
                    disabled={disabled}
                  />
                  <span className="field-hint">需支持「对话式出图」的模型</span>
                </label>
              </SectionCard>

              <SectionCard meta={VIDEO_SECTION} configured={keyConfigured(form.videoApiKey)}>
                <label className="field">
                  <span>在线平台</span>
                  <select
                    value={form.videoProvider}
                    onChange={(e) => applyVideoProvider(e.target.value as VideoProviderId)}
                    disabled={disabled}
                  >
                    {VIDEO_PROVIDERS.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                  {form.videoProvider !== "custom" && (
                    <span className="field-endpoint mono">{videoPreset.apiBase}</span>
                  )}
                </label>
                {form.videoProvider === "custom" && (
                  <label className="field">
                    <span>自定义平台地址</span>
                    <input
                      type="text"
                      value={form.videoApiBase}
                      onChange={(e) => setField("videoApiBase", e.target.value)}
                      placeholder="https://…"
                      disabled={disabled}
                    />
                  </label>
                )}
                <label className="field">
                  <span>账号密钥</span>
                  <input
                    type="password"
                    value={form.videoApiKey}
                    onChange={(e) => setField("videoApiKey", e.target.value)}
                    placeholder={videoPreset.keyPlaceholder}
                    autoComplete="off"
                    disabled={disabled}
                  />
                </label>
              </SectionCard>

              <SectionCard meta={CODE_SECTION} configured={codeKeyOk}>
                <p className="settings-linked">谁来写代码（本机工具）</p>
                <ExecutorPicker
                  name="code-executor"
                  options={CODE_EXECUTORS}
                  value={form.codeExecutor}
                  executors={doctor?.executors}
                  disabled={disabled}
                  onChange={(id) => setField("codeExecutor", id)}
                />
                <label className="field field--checkbox">
                  <input
                    type="checkbox"
                    checked={form.codeUseHost}
                    onChange={(e) => setField("codeUseHost", e.target.checked)}
                    disabled={disabled}
                  />
                  <span>沿用项目经理的在线账号（推荐）</span>
                </label>
                {!form.codeUseHost && (
                  <>
                    <ProviderSelect
                      value={form.codeProvider}
                      onChange={(id) => {
                        const preset = getApiProvider(id);
                        setForm((prev) => ({
                          ...prev,
                          codeProvider: id,
                          codeApiBase: id === "custom" ? prev.codeApiBase : preset.apiBase,
                        }));
                      }}
                      disabled={disabled}
                    />
                    {form.codeProvider === "custom" && (
                      <label className="field">
                        <span>自定义平台地址</span>
                        <input
                          type="text"
                          value={form.codeApiBase}
                          onChange={(e) => setField("codeApiBase", e.target.value)}
                          placeholder="https://your-api.example.com/v1"
                          disabled={disabled}
                        />
                      </label>
                    )}
                    <label className="field">
                      <span>账号密钥</span>
                      <input
                        type="password"
                        value={form.codeApiKey}
                        onChange={(e) => setField("codeApiKey", e.target.value)}
                        placeholder={getApiProvider(form.codeProvider).keyPlaceholder}
                        autoComplete="off"
                        disabled={disabled}
                      />
                    </label>
                  </>
                )}
                {form.codeUseHost && (
                  <p className="settings-linked">未单独配置时，写代码相关 LLM 调用会回退到项目经理（host）账号。</p>
                )}
                <label className="field">
                  <span>编程模型</span>
                  <input
                    type="text"
                    value={form.codeModel}
                    onChange={(e) => setField("codeModel", e.target.value)}
                    placeholder={getApiProvider(form.codeProvider).promptModelDefault}
                    disabled={disabled}
                  />
                </label>
              </SectionCard>

              <section className="settings-card settings-card--compact">
                <header className="settings-card__head">
                  <h3 className="settings-card__title">网络代理</h3>
                  <p className="settings-card__purpose">访问国外平台时可填；国内视频平台通常不需要。</p>
                </header>
                <div className="settings-card__body">
                  <label className="field">
                    <span>代理地址（可选）</span>
                    <input
                      type="text"
                      value={form.proxy}
                      onChange={(e) => setField("proxy", e.target.value)}
                      placeholder="http://127.0.0.1:7897"
                      disabled={disabled}
                    />
                  </label>
                </div>
              </section>
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
