import { useCallback, useEffect, useState } from "react";
import type { ConfigInfo, ConfigPatch } from "../../vite-env.d";
import { ModelCatalogPicker } from "../ModelCatalogPicker";
import type { ApiProviderId } from "../../settings/apiProviders";
import { EXECUTOR_LOGIN_HINTS } from "../../settings/executors";
import { ExecutorIcon } from "../../settings/ExecutorIcon";
import {
  CODEX_AGENT_SECTION,
  CURSOR_AGENT_SECTION,
  HERMES_AGENT_SECTION,
  PI_AGENT_SECTION,
  type SettingsSectionMeta,
} from "../../settings/sections";
import {
  AGENT_EXECUTOR_IDS,
  CODEX_SANDBOX_OPTIONS,
  CURSOR_PERMISSION_OPTIONS,
  getExecutorPreset,
  loadAgentExecutorsFromConfig,
  serializeAgentExecutors,
  type AgentExecutorId,
  type AgentExecutorPreset,
  type AgentExecutorsMap,
  type CodexSandbox,
  type CursorPermissionMode,
} from "../../settings/agentExecutors";
import {
  loadAgentInstancesFromConfig,
  serializeAgentInstances,
  syncPiLockedInstancesToPreset,
} from "../../settings/agentInstances";
import {
  getProviderAccount,
  isProviderConfigured,
  loadProviderAccountsFromConfig,
  listBuiltinProviders,
  type ProviderAccountsMap,
} from "../../settings/providerAccounts";

interface Props {
  busy?: boolean;
  providerAccountsRevision?: number;
  onSaved?: () => void;
}

const EXECUTOR_SECTIONS: Record<AgentExecutorId, SettingsSectionMeta> = {
  pi: PI_AGENT_SECTION,
  hermes: HERMES_AGENT_SECTION,
  codex: CODEX_AGENT_SECTION,
  cursor: CURSOR_AGENT_SECTION,
};

interface FormState {
  agentExecutors: AgentExecutorsMap;
  providerAccounts: ProviderAccountsMap;
}

function fromConfig(data: ConfigInfo["data"]): FormState {
  const loaded = loadProviderAccountsFromConfig(data as Record<string, unknown>);
  return {
    providerAccounts: loaded.providerAccounts,
    agentExecutors: loadAgentExecutorsFromConfig(data as Record<string, unknown>),
  };
}

function toAgentsPatch(form: FormState): ConfigPatch {
  return {
    agents: {
      executors: serializeAgentExecutors(form.agentExecutors),
    },
  };
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
      <span>Provider（内置账号库 id）</span>
      <select value={value} onChange={(e) => onChange(e.target.value as ApiProviderId)} disabled={disabled}>
        {listBuiltinProviders().map((p) => {
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

function executorListStatus(
  executorId: AgentExecutorId,
  preset: AgentExecutorPreset,
  accounts: ProviderAccountsMap,
): "ok" | "warn" | "neutral" {
  if (executorId === "cursor") return "neutral";
  if (executorId === "codex" && !preset.use_third_party) return "neutral";
  const provider = (preset.provider || "openrouter") as ApiProviderId;
  return isProviderConfigured(accounts, provider) ? "ok" : "warn";
}

export function AgentSettingsView({
  busy = false,
  providerAccountsRevision = 0,
  onSaved,
}: Props) {
  const [configInfo, setConfigInfo] = useState<ConfigInfo | null>(null);
  const [form, setForm] = useState<FormState>(() => fromConfig({}));
  const [selectedId, setSelectedId] = useState<AgentExecutorId>("pi");
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

  useEffect(() => {
    if (providerAccountsRevision === 0) return;
    void (async () => {
      try {
        const info = await window.gameFactory.getConfig();
        setForm((prev) => ({
          ...prev,
          providerAccounts: loadProviderAccountsFromConfig(info.data as Record<string, unknown>)
            .providerAccounts,
        }));
      } catch {
        /* ignore refresh errors */
      }
    })();
  }, [providerAccountsRevision]);

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
      const info = await window.gameFactory.getConfig();
      const data = (info.data || {}) as Record<string, unknown>;
      const previousPi = loadAgentExecutorsFromConfig(data).pi;
      const syncedInstances = syncPiLockedInstancesToPreset(
        loadAgentInstancesFromConfig(data),
        previousPi,
        form.agentExecutors.pi,
      );
      const patch = toAgentsPatch(form);
      patch.agents = {
        ...patch.agents,
        instances: serializeAgentInstances(syncedInstances),
      };
      const res = await window.gameFactory.saveConfig(patch);
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

      setMessage(`已保存 Agent 设置${syncNote}`);
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

  const disabled = busy || loading || saving;
  const selectedMeta = EXECUTOR_SECTIONS[selectedId];
  const piPreset = getExecutorPreset(form.agentExecutors, "pi");
  const hermesPreset = getExecutorPreset(form.agentExecutors, "hermes");
  const codexPreset = getExecutorPreset(form.agentExecutors, "codex");
  const cursorPreset = getExecutorPreset(form.agentExecutors, "cursor");
  const piProvider = (piPreset.provider || "openrouter") as ApiProviderId;
  const hermesProvider = (hermesPreset.provider || "openrouter") as ApiProviderId;
  const codexProvider = (codexPreset.provider || "openrouter") as ApiProviderId;

  if (loading) {
    return <p className="hint">加载中…</p>;
  }

  return (
    <div className="agent-settings">
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

      <p className="settings-linked agent-settings__intro">
        <strong>Provider 页</strong>：填各平台 API Key；此处仅为各 Agent 工具选择默认内置 Provider 与模型。
        <br />
        <strong>雇人 / 对话</strong>：同事实例可单独覆盖。保存时，仍等于「旧 Pi 默认」的策划/IT
        实例会跟随新的 Agent · Pi Provider/模型。
      </p>

      <div className="agent-settings__master-detail">
        <aside className="agent-settings__list" aria-label="Agent 工具列表">
          <ul className="agent-settings__list-items">
            {AGENT_EXECUTOR_IDS.map((id) => {
              const meta = EXECUTOR_SECTIONS[id];
              const preset = getExecutorPreset(form.agentExecutors, id);
              const status = executorListStatus(id, preset, form.providerAccounts);
              const active = id === selectedId;
              return (
                <li key={id}>
                  <button
                    type="button"
                    className={`agent-settings__list-item ${active ? "active" : ""}`}
                    onClick={() => setSelectedId(id)}
                    disabled={disabled}
                  >
                    <span className="agent-settings__list-icon">
                      {meta.icon ? (
                        <ExecutorIcon id={meta.icon} className="executor-icon executor-icon--badge" />
                      ) : (
                        meta.step
                      )}
                    </span>
                    <span className="agent-settings__list-label">{meta.title}</span>
                    <span
                      className={`agent-settings__list-status ${
                        status === "ok" ? "ok" : status === "warn" ? "warn" : ""
                      }`}
                    >
                      {status === "ok" ? "✓" : status === "warn" ? "—" : ""}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        <main className="agent-settings__detail">
          <header className="agent-settings__detail-head">
            {selectedMeta.icon ? (
              <ExecutorIcon id={selectedMeta.icon} className="executor-icon executor-icon--badge" />
            ) : (
              <span className="settings-card__step">{selectedMeta.step}</span>
            )}
            <div>
              <h3 className="agent-settings__detail-title">{selectedMeta.title}</h3>
              <span className="settings-card__role-id">（{selectedMeta.roleId}）</span>
            </div>
          </header>
          <p className="settings-card__purpose">{selectedMeta.purpose}</p>
          {selectedMeta.note && <p className="settings-card__note">{selectedMeta.note}</p>}

          {selectedId === "pi" && (
            <>
              <AgentProviderSelect
                value={piProvider}
                accounts={form.providerAccounts}
                disabled={disabled}
                onChange={(providerId) => updateAgentExecutor("pi", { provider: providerId })}
              />
              <label className="field">
                <span>默认模型（可选）</span>
                <ModelCatalogPicker
                  providerId={piProvider}
                  value={piPreset.model ?? ""}
                  onChange={(model) => updateAgentExecutor("pi", { model })}
                  role="text"
                  disabled={disabled}
                  placeholder={
                    getProviderAccount(form.providerAccounts, piProvider).textModel || "留空则用账号默认"
                  }
                />
              </label>
              <p className="settings-card__note">
                策划 / IT 固定使用内置 Pi；需 Node ≥22.19 与 Provider Key。
              </p>
            </>
          )}

          {selectedId === "hermes" && (
            <>
              <AgentProviderSelect
                value={hermesProvider}
                accounts={form.providerAccounts}
                disabled={disabled}
                onChange={(providerId) => updateAgentExecutor("hermes", { provider: providerId })}
              />
              <label className="field field--checkbox">
                <input
                  type="checkbox"
                  checked={hermesPreset.yolo !== false}
                  disabled={disabled}
                  onChange={(e) => updateAgentExecutor("hermes", { yolo: e.target.checked })}
                />
                <span>YOLO（--yolo，默认开）</span>
              </label>
              <p className="settings-card__note">
                保存后到「环境 → Hermes → 同步 API」将所选 Provider 写入 Hermes。
                关闭 YOLO 会在开跑时报错（未接 ACP 前不可在无 TTY 路径关 YOLO）。
              </p>
            </>
          )}

          {selectedId === "codex" && (
            <>
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
              <label className="field">
                <span>沙箱（--sandbox）</span>
                <select
                  value={codexPreset.sandbox ?? "workspace-write"}
                  disabled={disabled}
                  onChange={(e) =>
                    updateAgentExecutor("codex", {
                      sandbox: e.target.value as CodexSandbox,
                    })
                  }
                >
                  {CODEX_SANDBOX_OPTIONS.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              {codexPreset.use_third_party ? (
                <>
                  <AgentProviderSelect
                    value={codexProvider}
                    accounts={form.providerAccounts}
                    disabled={disabled}
                    onChange={(providerId) => updateAgentExecutor("codex", { provider: providerId })}
                  />
                  <label className="field">
                    <span>模型（可选）</span>
                    <ModelCatalogPicker
                      providerId={codexProvider}
                      value={codexPreset.model ?? ""}
                      onChange={(model) => updateAgentExecutor("codex", { model })}
                      role="text"
                      disabled={disabled}
                      placeholder={
                        getProviderAccount(form.providerAccounts, codexProvider).textModel ||
                        "账号默认模型"
                      }
                    />
                  </label>
                </>
              ) : (
                <p className="settings-card__note">{EXECUTOR_LOGIN_HINTS.codex}</p>
              )}
            </>
          )}

          {selectedId === "cursor" && (
            <>
              <label className="field">
                <span>权限模式</span>
                <select
                  value={cursorPreset.permission_mode ?? "force"}
                  disabled={disabled}
                  onChange={(e) =>
                    updateAgentExecutor("cursor", {
                      permission_mode: e.target.value as CursorPermissionMode,
                    })
                  }
                >
                  {CURSOR_PERMISSION_OPTIONS.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <p className="settings-card__note">
                Cursor 仅支持本机登录/订阅，<strong>第三方不可用</strong>。
              </p>
              <p className="settings-card__note">{EXECUTOR_LOGIN_HINTS.cursor}</p>
            </>
          )}
        </main>
      </div>

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
          {saving ? "保存中…" : "保存 Agent 设置"}
        </button>
      </div>
    </div>
  );
}
