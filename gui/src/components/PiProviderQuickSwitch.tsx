import { useCallback, useEffect, useRef, useState } from "react";
import type { ColleagueInstance } from "../chat/roster";
import type { ChatAgentRole } from "../chat/roles";
import { API_PROVIDERS, getApiProvider, type ApiProviderId } from "../settings/apiProviders";
import {
  loadAgentInstancesFromConfig,
  resolveInstanceRecord,
  serializeAgentInstances,
  upsertInstanceRecord,
  type AgentInstanceRecord,
} from "../settings/agentInstances";
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

export function PiProviderQuickSwitch({ colleague, disabled }: Props) {
  const [provider, setProvider] = useState<ApiProviderId>("openrouter");
  const [model, setModel] = useState("");
  const [providerAccounts, setProviderAccounts] = useState<ProviderAccountsMap>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const modelSaveTimer = useRef<number | null>(null);
  const pendingModel = useRef<{
    instanceId: string;
    roleKind: ChatAgentRole;
    model: string;
  } | null>(null);
  const providerRef = useRef(provider);
  const modelRef = useRef(model);
  const colleagueRef = useRef(colleague);

  providerRef.current = provider;
  modelRef.current = model;
  colleagueRef.current = colleague;

  const persist = useCallback(
    async (
      instanceId: string,
      roleKind: ChatAgentRole,
      patch: Partial<Pick<AgentInstanceRecord, "provider" | "model">>,
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
        const record: AgentInstanceRecord = {
          role_kind: roleKind,
          executor: "pi",
          provider:
            patch.provider ??
            (onScreen ? providerRef.current : existing?.provider) ??
            "openrouter",
          model:
            patch.model ?? (onScreen ? modelRef.current : existing?.model) ?? "",
          use_third_party: false,
        };
        const nextMap = upsertInstanceRecord(instances, instanceId, record);
        const res = await window.gameFactory.saveConfig({
          agents: {
            instances: serializeAgentInstances(nextMap),
          },
        });
        if (!res.ok) throw new Error(res.error || "保存失败");
        if (onScreen) {
          if (patch.provider !== undefined) setProvider(patch.provider);
          if (patch.model !== undefined) setModel(patch.model);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setSaving(false);
      }
    },
    [],
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
        const textAccount = getProviderAccount(loaded.providerAccounts, loaded.activeTextProvider);
        const record = resolveInstanceRecord(
          colleagueRef.current,
          instances,
          agents,
          loaded.activeTextProvider,
          textAccount.textModel,
        );
        setProviderAccounts(loaded.providerAccounts);
        setProvider(record.provider);
        setModel(record.model);
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
    // 只在实例切换时重载，避免父组件重渲染冲掉正在输入的模型
  }, [colleague.id, flushPendingModel]);

  useEffect(
    () => () => {
      flushPendingModel();
    },
    [flushPendingModel],
  );

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

  const providerOk = isProviderConfigured(providerAccounts, provider);
  const preset = getApiProvider(provider);
  const modelPlaceholder =
    getProviderAccount(providerAccounts, provider).textModel || preset.promptModelDefault || "模型 ID";

  const hint = error
    ? error
    : !providerOk
      ? "未填 Key，去设置 → Provider"
      : saving
        ? "保存中…"
        : null;

  return (
    <div
      className={"pi-model-chip" + (disabled || loading ? " is-disabled" : "")}
      role="group"
      aria-label="厂商与模型"
      title={hint || undefined}
    >
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
      {hint ? <span className="pi-model-chip__hint">{hint}</span> : null}
    </div>
  );
}
