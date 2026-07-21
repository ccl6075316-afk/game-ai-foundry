import { useCallback, useEffect, useRef, useState } from "react";
import type { ColleagueInstance } from "../chat/roster";
import type { ChatAgentRole } from "../chat/roles";
import { API_PROVIDERS, getApiProvider, type ApiProviderId } from "../settings/apiProviders";
import {
  loadAgentExecutorsFromConfig,
  defaultsFromExecutorPreset,
  type AgentExecutorsMap,
} from "../settings/agentExecutors";
import {
  loadAgentInstancesFromConfig,
  resolveInstanceRecord,
  serializeAgentInstances,
  shouldSyncCodexThirdParty,
  upsertInstanceRecord,
  type AgentInstanceRecord,
  type InstanceExecutor,
} from "../settings/agentInstances";
import {
  CODE_EXECUTORS,
  HOST_EXECUTORS,
  type AgentExecutor,
} from "../settings/executors";
import { isPiLockedRole } from "../settings/hireColleague";
import {
  getProviderAccount,
  isProviderConfigured,
  loadProviderAccountsFromConfig,
  type ProviderAccountsMap,
} from "../settings/providerAccounts";

interface Props {
  colleague: ColleagueInstance;
  disabled?: boolean;
}

const MODEL_SAVE_DEBOUNCE_MS = 400;

function executorOptionsForRole(roleKind: ChatAgentRole): { id: AgentExecutor; label: string }[] {
  if (roleKind === "product_host") {
    return HOST_EXECUTORS.map((o) => ({ id: o.id, label: o.label }));
  }
  if (roleKind === "programmer") {
    return CODE_EXECUTORS.map((o) => ({ id: o.id, label: o.label }));
  }
  return [];
}

function missingConfigHint(
  roleKind: ChatAgentRole,
  provider: ApiProviderId,
  executor: InstanceExecutor,
  useThirdParty: boolean,
  providerOk: boolean,
): string | null {
  if (isPiLockedRole(roleKind)) {
    if (!provider) return "请选择 Provider";
    if (!providerOk) return "未填 Key · 设置 → Provider";
    return null;
  }
  if (!executor || executor === "pi") return "请选择执行器";
  if (executor === "codex" && useThirdParty) {
    if (!provider) return "Codex 第三方需 Provider";
    if (!providerOk) return "Codex 第三方需 Key · 设置 → Provider";
  }
  return null;
}

export function ColleagueConfigBar({ colleague, disabled }: Props) {
  const piLocked = isPiLockedRole(colleague.roleKind);
  const executorOptions = executorOptionsForRole(colleague.roleKind);

  const [executor, setExecutor] = useState<InstanceExecutor>("pi");
  const [provider, setProvider] = useState<ApiProviderId>("openrouter");
  const [model, setModel] = useState("");
  const [useThirdParty, setUseThirdParty] = useState(false);
  const [providerAccounts, setProviderAccounts] = useState<ProviderAccountsMap>({});
  const [executorsMap, setExecutorsMap] = useState<AgentExecutorsMap | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const modelSaveTimer = useRef<number | null>(null);
  const pendingModel = useRef<{
    instanceId: string;
    roleKind: ChatAgentRole;
    model: string;
  } | null>(null);
  const executorRef = useRef(executor);
  const providerRef = useRef(provider);
  const modelRef = useRef(model);
  const useThirdPartyRef = useRef(useThirdParty);
  const colleagueRef = useRef(colleague);

  executorRef.current = executor;
  providerRef.current = provider;
  modelRef.current = model;
  useThirdPartyRef.current = useThirdParty;
  colleagueRef.current = colleague;

  const syncCodexApi = useCallback(async (instanceId: string) => {
    if (!window.gameFactory?.executorStep) return;
    try {
      const syncRes = await window.gameFactory.executorStep("codex", "sync_api", { instanceId });
      if (syncRes.data && syncRes.data.ok === false) {
        setError(`Codex 同步失败：${syncRes.data.error || syncRes.stderr || "未知错误"}`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Codex 同步失败");
    }
  }, []);

  const persist = useCallback(
    async (
      instanceId: string,
      roleKind: ChatAgentRole,
      patch: Partial<Pick<AgentInstanceRecord, "executor" | "provider" | "model" | "use_third_party">>,
    ) => {
      if (!window.gameFactory?.getConfig || !window.gameFactory?.saveConfig) return;
      setSaving(true);
      setError(null);
      try {
        const info = await window.gameFactory.getConfig();
        const data = info.data as Record<string, unknown>;
        const instances = loadAgentInstancesFromConfig(data);
        const existing = instances[instanceId];
        const onScreen = instanceId === colleagueRef.current.id;
        const resolvedExecutor = piLocked
          ? "pi"
          : (patch.executor ??
            (onScreen ? executorRef.current : existing?.executor) ??
            "codex");
        const record: AgentInstanceRecord = {
          role_kind: roleKind,
          executor: resolvedExecutor,
          provider:
            patch.provider ??
            (onScreen ? providerRef.current : existing?.provider) ??
            "openrouter",
          model:
            patch.model ?? (onScreen ? modelRef.current : existing?.model) ?? "",
          use_third_party:
            resolvedExecutor === "codex"
              ? (patch.use_third_party ??
                (onScreen ? useThirdPartyRef.current : existing?.use_third_party) ??
                false)
              : false,
        };
        const nextMap = upsertInstanceRecord(instances, instanceId, record);
        const res = await window.gameFactory.saveConfig({
          agents: {
            instances: serializeAgentInstances(nextMap),
          },
        });
        if (!res.ok) throw new Error(res.error || "保存失败");
        if (shouldSyncCodexThirdParty(record)) {
          await syncCodexApi(instanceId);
        }
        if (onScreen) {
          if (patch.executor !== undefined) setExecutor(patch.executor);
          if (patch.provider !== undefined) setProvider(patch.provider);
          if (patch.model !== undefined) setModel(patch.model);
          if (patch.use_third_party !== undefined) setUseThirdParty(patch.use_third_party);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setSaving(false);
      }
    },
    [piLocked, syncCodexApi],
  );

  const flushPendingModel = useCallback(() => {
    if (modelSaveTimer.current != null) {
      window.clearTimeout(modelSaveTimer.current);
      modelSaveTimer.current = null;
    }
    const pending = pendingModel.current;
    if (!pending) return;
    pendingModel.current = null;
    void persist(pending.instanceId, pending.roleKind, { model: pending.model });
  }, [persist]);

  useEffect(() => {
    flushPendingModel();
    let cancelled = false;
    (async () => {
      if (!window.gameFactory?.getConfig) return;
      setLoading(true);
      try {
        const info = await window.gameFactory.getConfig();
        if (cancelled) return;
        const data = info.data as Record<string, unknown>;
        const loaded = loadProviderAccountsFromConfig(data);
        const instances = loadAgentInstancesFromConfig(data);
        const agents = (data.agents || {}) as Record<string, unknown>;
        const execMap = loadAgentExecutorsFromConfig(data);
        const textAccount = getProviderAccount(loaded.providerAccounts, loaded.activeTextProvider);
        const saved = instances[colleagueRef.current.id];
        const record = resolveInstanceRecord(
          colleagueRef.current,
          instances,
          agents,
          loaded.activeTextProvider,
          textAccount.textModel,
          execMap,
        );
        setProviderAccounts(loaded.providerAccounts);
        setExecutorsMap(execMap);
        setExecutor(record.executor);
        setProvider(record.provider);
        setModel(saved ? String(saved.model ?? "") : record.model ? String(record.model) : "");
        setUseThirdParty(record.use_third_party);
        setError(null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [colleague.id, flushPendingModel]);

  useEffect(
    () => () => {
      flushPendingModel();
    },
    [flushPendingModel],
  );

  const applyExecutorPreset = useCallback(
    (nextExecutor: InstanceExecutor) => {
      if (piLocked || !executorsMap) return;
      const preset = defaultsFromExecutorPreset(
        executorsMap,
        nextExecutor === "pi" ? "pi" : nextExecutor,
      );
      setExecutor(nextExecutor);
      setProvider(preset.provider);
      setModel(preset.model);
      setUseThirdParty(preset.use_third_party);
      void persist(colleague.id, colleague.roleKind, {
        executor: nextExecutor,
        provider: preset.provider,
        model: preset.model,
        use_third_party: preset.use_third_party,
      });
    },
    [colleague.id, colleague.roleKind, executorsMap, persist, piLocked],
  );

  const handleExecutorChange = (id: AgentExecutor) => {
    flushPendingModel();
    applyExecutorPreset(id);
  };

  const handleProviderChange = (id: ApiProviderId) => {
    flushPendingModel();
    setProvider(id);
    void persist(colleague.id, colleague.roleKind, { provider: id });
  };

  const handleModelChange = (value: string) => {
    setModel(value);
    pendingModel.current = {
      instanceId: colleague.id,
      roleKind: colleague.roleKind,
      model: value,
    };
    if (modelSaveTimer.current != null) {
      window.clearTimeout(modelSaveTimer.current);
    }
    modelSaveTimer.current = window.setTimeout(() => {
      modelSaveTimer.current = null;
      const pending = pendingModel.current;
      if (!pending) return;
      pendingModel.current = null;
      void persist(pending.instanceId, pending.roleKind, { model: pending.model });
    }, MODEL_SAVE_DEBOUNCE_MS);
  };

  const handleThirdPartyChange = (checked: boolean) => {
    flushPendingModel();
    setUseThirdParty(checked);
    void persist(colleague.id, colleague.roleKind, { use_third_party: checked });
  };

  const providerOk = isProviderConfigured(providerAccounts, provider);
  const preset = getApiProvider(provider);
  const execPreset =
    executorsMap && !piLocked && executor !== "pi"
      ? defaultsFromExecutorPreset(executorsMap, executor as AgentExecutor)
      : null;
  const modelPlaceholder =
    getProviderAccount(providerAccounts, provider).textModel ||
    execPreset?.model ||
    preset.promptModelDefault ||
    "模型 ID";

  const configHint = missingConfigHint(
    colleague.roleKind,
    provider,
    executor,
    useThirdParty,
    providerOk,
  );

  const hint = error
    ? error
    : configHint
      ? configHint
      : saving
        ? "保存中…"
        : null;

  const showThirdParty = !piLocked && executor === "codex";

  return (
    <div
      className={"pi-model-chip" + (disabled || loading ? " is-disabled" : "")}
      role="group"
      aria-label="同事配置"
      title={hint || undefined}
    >
      {!piLocked && executorOptions.length > 0 ? (
        <>
          <select
            value={executor === "pi" ? "" : executor}
            disabled={disabled || loading || saving}
            aria-label="执行器"
            onChange={(e) => handleExecutorChange(e.target.value as AgentExecutor)}
          >
            {executorOptions.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label}
              </option>
            ))}
          </select>
          <span className="pi-model-chip__dot" aria-hidden>
            ·
          </span>
        </>
      ) : null}
      <select
        value={provider}
        disabled={disabled || loading || saving}
        aria-label="厂商"
        onChange={(e) => handleProviderChange(e.target.value as ApiProviderId)}
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
      <span className="pi-model-chip__dot" aria-hidden>
        ·
      </span>
      <input
        type="text"
        value={model}
        disabled={disabled || loading || saving}
        placeholder={modelPlaceholder}
        spellCheck={false}
        autoComplete="off"
        aria-label="模型"
        onChange={(e) => handleModelChange(e.target.value)}
        onBlur={() => flushPendingModel()}
      />
      {showThirdParty ? (
        <>
          <span className="pi-model-chip__dot" aria-hidden>
            ·
          </span>
          <label className="pi-model-chip__check">
            <input
              type="checkbox"
              checked={useThirdParty}
              disabled={disabled || loading || saving}
              onChange={(e) => handleThirdPartyChange(e.target.checked)}
            />
            第三方
          </label>
        </>
      ) : null}
      {hint ? <span className="pi-model-chip__hint">{hint}</span> : null}
    </div>
  );
}
