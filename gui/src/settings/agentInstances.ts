import type { ColleagueInstance } from "../chat/roster";
import type { ChatAgentRole } from "../chat/roles";
import { CHAT_AGENT_ROLES } from "../chat/roles";
import {
  defaultsFromExecutorPreset,
  type AgentExecutorsMap,
  type CodexSandbox,
  type CursorPermissionMode,
} from "./agentExecutors";
import {
  omitSafetyKeysForSerialize,
  parseInstanceSafetyFields,
} from "./instanceSafety";
import { API_PROVIDERS, type ApiProviderId } from "./apiProviders";
import { parseExecutor, type AgentExecutor } from "./executors";

export type PiExecutor = "pi";
export type InstanceExecutor = AgentExecutor | PiExecutor;

export interface AgentInstanceRecord {
  role_kind: ChatAgentRole;
  executor: InstanceExecutor;
  provider: ApiProviderId;
  model: string;
  use_third_party: boolean;
  /** Codex CLI --sandbox; omit = inherit agents.executors.codex */
  sandbox?: CodexSandbox;
  /** Cursor permission / mode; omit = inherit agents.executors.cursor */
  permission_mode?: CursorPermissionMode;
  /** Hermes --yolo; omit = inherit agents.executors.hermes */
  yolo?: boolean;
}

export type AgentInstancesMap = Record<string, AgentInstanceRecord>;

const ROLE_AGENT_KEYS: Record<ChatAgentRole, string> = {
  brief: "brief",
  it: "it",
  product_host: "orchestrator",
  programmer: "godot-developer",
};

function isApiProviderId(id: string): id is ApiProviderId {
  return API_PROVIDERS.some((p) => p.id === id);
}

function coerceProvider(value: unknown, fallback: ApiProviderId): ApiProviderId {
  const id = String(value || fallback);
  return isApiProviderId(id) ? id : fallback;
}

export function defaultExecutorForRole(
  roleKind: ChatAgentRole,
  roleBlock?: Record<string, unknown>,
): InstanceExecutor {
  if (roleKind === "brief" || roleKind === "it") return "pi";
  const raw = String(roleBlock?.executor || "");
  if (raw === "hermes" || raw === "cursor" || raw === "codex") return raw;
  return roleKind === "product_host" ? "hermes" : "codex";
}

function parseInstanceExecutor(
  value: unknown,
  roleKind: ChatAgentRole,
  fallback: InstanceExecutor,
): InstanceExecutor {
  if (roleKind === "brief" || roleKind === "it") return "pi";
  if (value === "pi") return fallback === "pi" ? "codex" : fallback;
  return parseExecutor(value, fallback === "pi" ? "codex" : (fallback as AgentExecutor));
}

export function loadAgentInstancesFromConfig(data: Record<string, unknown>): AgentInstancesMap {
  const agents = (data.agents || {}) as Record<string, unknown>;
  const raw = agents.instances;
  if (!raw || typeof raw !== "object") return {};

  const out: AgentInstancesMap = {};
  for (const [id, val] of Object.entries(raw as Record<string, unknown>)) {
    if (!val || typeof val !== "object") continue;
    const rec = val as Record<string, unknown>;
    const roleKind = String(rec.role_kind || "") as ChatAgentRole;
    if (!CHAT_AGENT_ROLES.includes(roleKind)) continue;

    const roleKey = ROLE_AGENT_KEYS[roleKind];
    const roleBlock = (agents[roleKey] || {}) as Record<string, unknown>;
    out[id] = {
      role_kind: roleKind,
      executor: parseInstanceExecutor(
        rec.executor,
        roleKind,
        defaultExecutorForRole(roleKind, roleBlock),
      ),
      provider: coerceProvider(rec.provider ?? roleBlock.provider, "openrouter"),
      model: rec.model != null ? String(rec.model) : String(roleBlock.model ?? ""),
      use_third_party: Boolean(rec.use_third_party ?? roleBlock.use_third_party ?? false),
      ...parseInstanceSafetyFields(rec),
    };
  }
  return out;
}

export function resolveInstanceRecord(
  instance: ColleagueInstance,
  instances: AgentInstancesMap,
  agents: Record<string, unknown>,
  fallbackProvider: ApiProviderId,
  fallbackModel: string,
  executorsMap?: AgentExecutorsMap,
): AgentInstanceRecord {
  const saved = instances[instance.id];
  if (saved) return { ...saved, role_kind: instance.roleKind };

  const roleKey = ROLE_AGENT_KEYS[instance.roleKind];
  const roleBlock = (agents[roleKey] || {}) as Record<string, unknown>;
  let executor = defaultExecutorForRole(instance.roleKind, roleBlock);
  if (
    (instance.roleKind === "product_host" || instance.roleKind === "programmer") &&
    (instance.executor === "hermes" || instance.executor === "codex" || instance.executor === "cursor")
  ) {
    executor = instance.executor;
  }

  const fromRole: AgentInstanceRecord = {
    role_kind: instance.roleKind,
    executor,
    provider: coerceProvider(roleBlock.provider, fallbackProvider),
    model: roleBlock.model != null ? String(roleBlock.model) : fallbackModel,
    use_third_party: Boolean(roleBlock.use_third_party ?? false),
  };

  if (!executorsMap) return fromRole;

  const execId =
    executor === "pi" || executor === "hermes" || executor === "codex" || executor === "cursor"
      ? executor
      : "pi";
  const preset = defaultsFromExecutorPreset(executorsMap, execId);
  // Align GUI display with CLI: executors preset before legacy role block
  return {
    ...fromRole,
    provider: coerceProvider(preset.provider ?? roleBlock.provider, fallbackProvider),
    model: preset.model || fromRole.model,
    use_third_party:
      executor === "codex"
        ? Boolean(preset.use_third_party || roleBlock.use_third_party)
        : false,
  };
}

export function upsertInstanceRecord(
  map: AgentInstancesMap,
  id: string,
  record: AgentInstanceRecord,
): AgentInstancesMap {
  return { ...map, [id]: record };
}

/** Overlay settings-session dirty records onto latest disk map (quick-switch safe). */
export function mergeDirtyInstances(
  latest: AgentInstancesMap,
  formInstances: AgentInstancesMap,
  dirtyIds: string[],
): AgentInstancesMap {
  if (!dirtyIds.length) return { ...latest };
  const out = { ...latest };
  for (const id of dirtyIds) {
    const rec = formInstances[id];
    if (rec) out[id] = rec;
  }
  return out;
}

export function deleteInstanceRecord(map: AgentInstancesMap, id: string): AgentInstancesMap {
  const next = { ...map };
  delete next[id];
  return next;
}

export function serializeAgentInstances(
  map: AgentInstancesMap,
): Record<string, Record<string, unknown>> {
  const out: Record<string, Record<string, unknown>> = {};
  for (const [id, rec] of Object.entries(map)) {
    out[id] = {
      role_kind: rec.role_kind,
      executor: rec.executor,
      provider: rec.provider,
      model: rec.model.trim() || null,
      use_third_party: rec.executor === "codex" ? rec.use_third_party : false,
      ...omitSafetyKeysForSerialize(rec),
    };
  }
  return out;
}

export function rosterChatInstances(roster: ColleagueInstance[]): ColleagueInstance[] {
  return roster.filter((c) => CHAT_AGENT_ROLES.includes(c.roleKind));
}

export function shouldSyncCodexThirdParty(record: AgentInstanceRecord): boolean {
  return record.executor === "codex" && record.use_third_party;
}

/**
 * When Agent → Pi default Provider/model changes, update 策划/IT instances that
 * still match the previous default (so Settings change is visible in the chat bar).
 */
export function syncPiLockedInstancesToPreset(
  instances: AgentInstancesMap,
  previousPi: { provider?: ApiProviderId; model?: string },
  nextPi: { provider?: ApiProviderId; model?: string },
): AgentInstancesMap {
  const prevProvider = coerceProvider(previousPi.provider, "openrouter");
  const prevModel = String(previousPi.model ?? "").trim();
  const nextProvider = coerceProvider(nextPi.provider, "openrouter");
  const nextModel = String(nextPi.model ?? "").trim();
  if (prevProvider === nextProvider && prevModel === nextModel) {
    return instances;
  }

  let changed = false;
  const out: AgentInstancesMap = { ...instances };
  for (const [id, rec] of Object.entries(instances)) {
    if (rec.role_kind !== "brief" && rec.role_kind !== "it") continue;
    if (rec.executor !== "pi") continue;
    if (rec.provider !== prevProvider) continue;
    if (String(rec.model ?? "").trim() !== prevModel) continue;
    out[id] = { ...rec, provider: nextProvider, model: nextModel };
    changed = true;
  }
  return changed ? out : instances;
}
