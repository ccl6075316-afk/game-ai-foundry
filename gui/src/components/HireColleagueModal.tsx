import { useEffect, useState } from "react";
import type { ColleagueInstance } from "../chat/roster";
import { nextHireName } from "../chat/roster";
import type { ChatAgentRole } from "../chat/roles";
import { CHAT_AGENT_LABELS } from "../chat/roles";
import { API_PROVIDERS, getApiProvider, type ApiProviderId } from "../settings/apiProviders";
import { loadAgentExecutorsFromConfig } from "../settings/agentExecutors";
import type { InstanceExecutor } from "../settings/agentInstances";
import {
  buildHireRecord,
  defaultExecutorForHire,
  isPiLockedRole,
  prefillFromExecutorPreset,
  validateHireForm,
  type HireColleagueConfirmPayload,
  type HireFormState,
} from "../settings/hireColleague";
import {
  CODE_EXECUTORS,
  EXECUTOR_LOGIN_HINTS,
  HOST_EXECUTORS,
  type AgentExecutor,
} from "../settings/executors";
import {
  getProviderAccount,
  isProviderConfigured,
  loadProviderAccountsFromConfig,
  type ProviderAccountsMap,
} from "../settings/providerAccounts";

export type { HireColleagueConfirmPayload };

interface Props {
  roleKind: ChatAgentRole | null;
  roster: ColleagueInstance[];
  onCancel: () => void;
  onConfirm: (payload: HireColleagueConfirmPayload) => void;
}

function emptyForm(displayName = ""): HireFormState {
  return {
    executor: "codex",
    provider: "openrouter",
    model: "",
    use_third_party: false,
    displayName,
  };
}

export function HireColleagueModal({ roleKind, roster, onCancel, onConfirm }: Props) {
  const [form, setForm] = useState<HireFormState>(() => emptyForm());
  const [providerAccounts, setProviderAccounts] = useState<ProviderAccountsMap>({});
  const [loading, setLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (!roleKind) return;
    let cancelled = false;
    const suggestedName = nextHireName(roster, roleKind);
    setValidationError(null);
    setForm(emptyForm(suggestedName));

    (async () => {
      if (!window.gameFactory?.getConfig) {
        const executor = roleKind === "brief" || roleKind === "it" ? "pi" : "codex";
        setForm((prev) => ({ ...prev, executor: executor as HireFormState["executor"] }));
        return;
      }
      setLoading(true);
      try {
        const info = await window.gameFactory.getConfig();
        if (cancelled) return;
        const data = info.data as Record<string, unknown>;
        const agents = (data.agents || {}) as Record<string, unknown>;
        const executorsMap = loadAgentExecutorsFromConfig(data);
        const accounts = loadProviderAccountsFromConfig(data);
        const executor = defaultExecutorForHire(roleKind, agents);
        const preset = prefillFromExecutorPreset(executor, executorsMap);
        setProviderAccounts(accounts.providerAccounts);
        setForm({
          executor,
          provider: preset.provider,
          model: preset.model,
          use_third_party: preset.use_third_party,
          displayName: suggestedName,
        });
      } catch {
        if (!cancelled) {
          setForm((prev) => ({ ...prev, displayName: suggestedName }));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [roleKind, roster]);

  if (!roleKind) return null;

  const piLocked = isPiLockedRole(roleKind);
  const executorOptions =
    roleKind === "product_host" ? HOST_EXECUTORS : roleKind === "programmer" ? CODE_EXECUTORS : [];
  const providerOk = isProviderConfigured(providerAccounts, form.provider);
  const providerPreset = getApiProvider(form.provider);
  const modelPlaceholder =
    getProviderAccount(providerAccounts, form.provider).textModel ||
    providerPreset.promptModelDefault ||
    "模型 ID（可选）";

  const applyExecutorPreset = (nextExecutor: InstanceExecutor) => {
    if (!window.gameFactory?.getConfig) {
      setForm((prev) => ({ ...prev, executor: nextExecutor }));
      return;
    }
    void (async () => {
      try {
        const info = await window.gameFactory.getConfig();
        const executorsMap = loadAgentExecutorsFromConfig(info.data as Record<string, unknown>);
        const preset = prefillFromExecutorPreset(nextExecutor, executorsMap);
        setForm((prev) => ({
          ...prev,
          executor: nextExecutor,
          provider: preset.provider,
          model: preset.model,
          use_third_party: preset.use_third_party,
        }));
      } catch {
        setForm((prev) => ({ ...prev, executor: nextExecutor }));
      }
    })();
  };

  const handleExecutorChange = (id: AgentExecutor) => {
    applyExecutorPreset(id);
  };

  const handleConfirm = () => {
    const err = validateHireForm(roleKind, form);
    if (err) {
      setValidationError(err);
      return;
    }
    const record = buildHireRecord(roleKind, form);
    const name = form.displayName.trim();
    onConfirm({
      roleKind,
      displayName: name || undefined,
      record,
    });
  };

  const canConfirm = validateHireForm(roleKind, form) == null && !loading;

  return (
    <div
      className="toolchain-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="hire-colleague-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="toolchain-modal">
        <header className="toolchain-modal__head">
          <h2 id="hire-colleague-title">雇佣{CHAT_AGENT_LABELS[roleKind]}</h2>
          <p className="toolchain-modal__lead">
            配置将写入该同事实例；API Key 请在设置 → Provider 填写。
          </p>
        </header>

        <div className="toolchain-modal__issues" style={{ paddingBottom: 16 }}>
          <label className="field">
            <span>显示名（可选）</span>
            <input
              type="text"
              value={form.displayName}
              disabled={loading}
              placeholder={nextHireName(roster, roleKind)}
              onChange={(e) => setForm((prev) => ({ ...prev, displayName: e.target.value }))}
            />
          </label>

          {piLocked ? (
            <p className="settings-card__note">
              {CHAT_AGENT_LABELS[roleKind]} 使用<strong>内置 Pi</strong>；Provider 必填，模型可选。
            </p>
          ) : (
            <>
              <div className="field">
                <span>执行器（必填）</span>
                <div className="executor-picker">
                  <div className="executor-picker__options">
                    {executorOptions.map((opt) => (
                      <label
                        key={opt.id}
                        className={`executor-option ${form.executor === opt.id ? "active" : ""}`}
                      >
                        <input
                          type="radio"
                          name="hire-executor"
                          value={opt.id}
                          checked={form.executor === opt.id}
                          disabled={loading}
                          onChange={() => handleExecutorChange(opt.id)}
                        />
                        <span className="executor-option__label">{opt.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
              {executorOptions.find((o) => o.id === form.executor)?.description && (
                <p className="field-hint">
                  {executorOptions.find((o) => o.id === form.executor)!.description}
                </p>
              )}
            </>
          )}

          <label className="field">
            <span>
              Provider{piLocked ? "（必填）" : "（可选）"}
            </span>
            <select
              value={form.provider}
              disabled={loading}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, provider: e.target.value as ApiProviderId }))
              }
            >
              {API_PROVIDERS.map((p) => {
                const ok = isProviderConfigured(providerAccounts, p.id);
                return (
                  <option key={p.id} value={p.id}>
                    {p.label}
                    {ok ? "" : " · 无 Key"}
                  </option>
                );
              })}
            </select>
            {!providerOk && (
              <span className="settings-card__note">
                所选 Provider 尚未填 Key，回合可能失败；请先到 Provider 页补全。
              </span>
            )}
          </label>

          <label className="field">
            <span>模型（可选）</span>
            <input
              type="text"
              value={form.model}
              disabled={loading}
              placeholder={modelPlaceholder}
              spellCheck={false}
              autoComplete="off"
              onChange={(e) => setForm((prev) => ({ ...prev, model: e.target.value }))}
            />
          </label>

          {!piLocked && form.executor === "codex" && (
            <label className="field field--checkbox">
              <input
                type="checkbox"
                checked={form.use_third_party}
                disabled={loading}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, use_third_party: e.target.checked }))
                }
              />
              <span>用第三方（账号库 Key，保存时同步到 Codex）</span>
            </label>
          )}

          {!piLocked && form.executor === "cursor" && (
            <p className="settings-card__note">
              Cursor 仅支持本机登录/订阅，<strong>第三方不可用</strong>。
            </p>
          )}

          {!piLocked && form.executor === "hermes" && (
            <p className="settings-card__note">{EXECUTOR_LOGIN_HINTS.hermes}</p>
          )}

          {!piLocked && form.executor === "codex" && !form.use_third_party && (
            <p className="settings-card__note">{EXECUTOR_LOGIN_HINTS.codex}</p>
          )}

          {validationError ? (
            <p className="settings-card__note" role="alert">
              {validationError}
            </p>
          ) : null}
        </div>

        <footer className="toolchain-modal__foot">
          <button type="button" className="btn btn--primary" disabled={!canConfirm} onClick={handleConfirm}>
            确认雇佣
          </button>
          <button type="button" className="btn btn--ghost" onClick={onCancel}>
            取消
          </button>
        </footer>
      </div>
    </div>
  );
}
