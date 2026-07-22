import { API_PROVIDERS, type ApiProviderId } from "./apiProviders";

export type AgentExecutorId = "pi" | "hermes" | "codex" | "cursor";

export const AGENT_EXECUTOR_IDS: AgentExecutorId[] = ["pi", "hermes", "codex", "cursor"];

export type CodexSandbox = "read-only" | "workspace-write" | "danger-full-access";
export type CursorPermissionMode = "force" | "auto_review" | "plan" | "ask";

export const CODEX_SANDBOX_OPTIONS: { id: CodexSandbox; label: string }[] = [
  { id: "read-only", label: "只读（read-only）" },
  { id: "workspace-write", label: "工作区可写（默认）" },
  { id: "danger-full-access", label: "全权限（危险）" },
];

export const CURSOR_PERMISSION_OPTIONS: { id: CursorPermissionMode; label: string }[] = [
  { id: "force", label: "强制执行（默认，--force）" },
  { id: "auto_review", label: "Smart Auto（--auto-review）" },
  { id: "plan", label: "仅计划（--mode plan）" },
  { id: "ask", label: "询问（--mode ask）" },
];

export interface AgentExecutorPreset {
  provider?: ApiProviderId;
  model?: string;
  use_third_party?: boolean;
  /** Codex CLI --sandbox */
  sandbox?: CodexSandbox;
  /** Cursor Agent permission / mode */
  permission_mode?: CursorPermissionMode;
  /** Hermes --yolo; false refuses run until ACP exists */
  yolo?: boolean;
}

export type AgentExecutorsMap = Record<AgentExecutorId, AgentExecutorPreset>;

export interface ExecutorHireDefaults {
  provider: ApiProviderId;
  model: string;
  use_third_party: boolean;
}

function isApiProviderId(id: string): id is ApiProviderId {
  return API_PROVIDERS.some((p) => p.id === id);
}

function coerceProvider(value: unknown, fallback: ApiProviderId): ApiProviderId {
  const id = String(value || fallback);
  return isApiProviderId(id) ? id : fallback;
}

function inferPiPreset(agents: Record<string, unknown>): AgentExecutorPreset {
  const brief = (agents.brief || {}) as Record<string, unknown>;
  const it = (agents.it || {}) as Record<string, unknown>;
  const block =
    _normalizeStr(brief.provider) != null ||
    _normalizeStr(brief.model) != null ||
    brief.model === null
      ? brief
      : it;
  return {
    provider: coerceProvider(block.provider, "openrouter"),
    model: block.model != null ? String(block.model) : "",
    use_third_party: false,
  };
}

function inferHermesPreset(agents: Record<string, unknown>): AgentExecutorPreset {
  const orchestrator = (agents.orchestrator || {}) as Record<string, unknown>;
  const provider = agents.hermes_provider ?? orchestrator.provider;
  return {
    provider: coerceProvider(provider, "openrouter"),
    model: orchestrator.model != null ? String(orchestrator.model) : "",
    use_third_party: false,
    yolo: true,
  };
}

function inferCodexPreset(agents: Record<string, unknown>): AgentExecutorPreset {
  const roleBlock = (agents["godot-developer"] || {}) as Record<string, unknown>;
  return {
    provider: coerceProvider(roleBlock.provider, "openrouter"),
    model: roleBlock.model != null ? String(roleBlock.model) : "",
    use_third_party: Boolean(roleBlock.use_third_party ?? false),
    sandbox: "workspace-write",
  };
}

function inferCursorPreset(): AgentExecutorPreset {
  return { permission_mode: "force" };
}

function inferAllFromLegacy(agents: Record<string, unknown>): AgentExecutorsMap {
  return {
    pi: inferPiPreset(agents),
    hermes: inferHermesPreset(agents),
    codex: inferCodexPreset(agents),
    cursor: inferCursorPreset(),
  };
}

function _normalizeStr(value: unknown): string | undefined {
  if (value == null) return undefined;
  const text = String(value).trim();
  return text || undefined;
}

function parseExecutorPreset(
  raw: unknown,
  fallback: AgentExecutorPreset,
  executorId: AgentExecutorId,
): AgentExecutorPreset {
  if (!raw || typeof raw !== "object") return { ...fallback };
  const rec = raw as Record<string, unknown>;
  const preset: AgentExecutorPreset = {
    provider:
      rec.provider != null
        ? coerceProvider(rec.provider, fallback.provider ?? "openrouter")
        : fallback.provider,
    model: rec.model != null ? String(rec.model) : fallback.model,
  };
  if (executorId === "codex") {
    preset.use_third_party =
      rec.use_third_party != null
        ? Boolean(rec.use_third_party)
        : Boolean(fallback.use_third_party ?? false);
    const sandbox = String(rec.sandbox ?? fallback.sandbox ?? "workspace-write");
    preset.sandbox = CODEX_SANDBOX_OPTIONS.some((o) => o.id === sandbox)
      ? (sandbox as CodexSandbox)
      : "workspace-write";
  }
  if (executorId === "cursor") {
    const mode = String(rec.permission_mode ?? fallback.permission_mode ?? "force");
    preset.permission_mode = CURSOR_PERMISSION_OPTIONS.some((o) => o.id === mode)
      ? (mode as CursorPermissionMode)
      : "force";
  }
  if (executorId === "hermes") {
    preset.yolo = rec.yolo != null ? Boolean(rec.yolo) : Boolean(fallback.yolo ?? true);
  }
  return preset;
}

export function loadAgentExecutorsFromConfig(data: Record<string, unknown>): AgentExecutorsMap {
  const agents = (data.agents || {}) as Record<string, unknown>;
  const inferred = inferAllFromLegacy(agents);
  const raw = agents.executors;
  if (!raw || typeof raw !== "object") return inferred;

  const out = { ...inferred };
  for (const id of AGENT_EXECUTOR_IDS) {
    out[id] = parseExecutorPreset(
      (raw as Record<string, unknown>)[id],
      inferred[id],
      id,
    );
  }
  return out;
}

export function getExecutorPreset(
  map: AgentExecutorsMap,
  executorId: AgentExecutorId,
): AgentExecutorPreset {
  return map[executorId] ?? {};
}

export function defaultsFromExecutorPreset(
  map: AgentExecutorsMap,
  executorId: AgentExecutorId,
): ExecutorHireDefaults {
  const preset = getExecutorPreset(map, executorId);
  return {
    provider: coerceProvider(preset.provider, "openrouter"),
    model: preset.model != null ? String(preset.model) : "",
    use_third_party: executorId === "codex" ? Boolean(preset.use_third_party ?? false) : false,
  };
}

export function serializeAgentExecutors(
  map: AgentExecutorsMap,
): Record<string, Record<string, unknown>> {
  const out: Record<string, Record<string, unknown>> = {};
  for (const id of AGENT_EXECUTOR_IDS) {
    const rec = map[id];
    if (!rec) {
      out[id] = {};
      continue;
    }
    const entry: Record<string, unknown> = {};
    if (rec.provider) entry.provider = rec.provider;
    const model = rec.model != null ? String(rec.model).trim() : "";
    if (model) entry.model = model;
    else if (rec.model != null) entry.model = null;
    if (id === "codex") {
      entry.use_third_party = Boolean(rec.use_third_party ?? false);
      entry.sandbox = rec.sandbox ?? "workspace-write";
    }
    if (id === "cursor") {
      entry.permission_mode = rec.permission_mode ?? "force";
    }
    if (id === "hermes") {
      entry.yolo = rec.yolo != null ? Boolean(rec.yolo) : true;
    }
    out[id] = entry;
  }
  return out;
}
