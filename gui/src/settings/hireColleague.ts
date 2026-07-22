import type { ChatAgentRole } from "../chat/roles";
import {
  defaultExecutorForRole,
  type AgentInstanceRecord,
  type InstanceExecutor,
} from "./agentInstances";
import {
  defaultsFromExecutorPreset,
  type AgentExecutorId,
  type AgentExecutorsMap,
  type CodexSandbox,
  type CursorPermissionMode,
} from "./agentExecutors";
import type { ApiProviderId } from "./apiProviders";
import type { AgentExecutor } from "./executors";
import {
  INHERIT_SAFETY,
  isInheritSafetyValue,
  omitSafetyKeysForSerialize,
  safetyFieldForExecutor,
} from "./instanceSafety";

export interface HireFormState {
  executor: InstanceExecutor;
  provider: ApiProviderId;
  model: string;
  use_third_party: boolean;
  displayName: string;
  sandbox: CodexSandbox | typeof INHERIT_SAFETY;
  permission_mode: CursorPermissionMode | typeof INHERIT_SAFETY;
  yolo: boolean | typeof INHERIT_SAFETY;
}

export function defaultSafetyFormFields(): Pick<
  HireFormState,
  "sandbox" | "permission_mode" | "yolo"
> {
  return {
    sandbox: INHERIT_SAFETY,
    permission_mode: INHERIT_SAFETY,
    yolo: INHERIT_SAFETY,
  };
}

export interface HireColleagueConfirmPayload {
  roleKind: ChatAgentRole;
  displayName?: string;
  record: AgentInstanceRecord;
}

const HIRE_AGENT_EXECUTORS: AgentExecutor[] = ["hermes", "codex", "cursor"];

export function isPiLockedRole(roleKind: ChatAgentRole): boolean {
  return roleKind === "brief" || roleKind === "it";
}

export function defaultExecutorForHire(
  roleKind: ChatAgentRole,
  agents: Record<string, unknown>,
): InstanceExecutor {
  if (isPiLockedRole(roleKind)) return "pi";
  const roleKey =
    roleKind === "product_host" ? "orchestrator" : roleKind === "programmer" ? "godot-developer" : roleKind;
  const roleBlock = (agents[roleKey] || {}) as Record<string, unknown>;
  return defaultExecutorForRole(roleKind, roleBlock);
}

export function prefillFromExecutorPreset(
  executor: InstanceExecutor,
  executorsMap: AgentExecutorsMap,
): Pick<HireFormState, "provider" | "model" | "use_third_party"> {
  const execId = (executor === "pi" ? "pi" : executor) as AgentExecutorId;
  return defaultsFromExecutorPreset(executorsMap, execId);
}

export function validateHireForm(roleKind: ChatAgentRole, form: HireFormState): string | null {
  if (isPiLockedRole(roleKind)) {
    if (!String(form.provider || "").trim()) return "请选择 Provider";
    return null;
  }
  if (!HIRE_AGENT_EXECUTORS.includes(form.executor as AgentExecutor)) {
    return "请选择执行器";
  }
  return null;
}

export function buildHireRecord(roleKind: ChatAgentRole, form: HireFormState): AgentInstanceRecord {
  const executor = isPiLockedRole(roleKind) ? "pi" : form.executor;
  const base: AgentInstanceRecord = {
    role_kind: roleKind,
    executor,
    provider: form.provider,
    model: form.model,
    use_third_party: executor === "codex" ? form.use_third_party : false,
  };

  const field = safetyFieldForExecutor(executor);
  if (!field) return base;

  const safetyInput: {
    sandbox?: CodexSandbox;
    permission_mode?: CursorPermissionMode;
    yolo?: boolean;
  } = {};

  if (field === "sandbox" && !isInheritSafetyValue(form.sandbox)) {
    safetyInput.sandbox = form.sandbox as CodexSandbox;
  } else if (field === "permission_mode" && !isInheritSafetyValue(form.permission_mode)) {
    safetyInput.permission_mode = form.permission_mode as CursorPermissionMode;
  } else if (field === "yolo" && !isInheritSafetyValue(form.yolo)) {
    safetyInput.yolo = form.yolo as boolean;
  }

  return { ...base, ...omitSafetyKeysForSerialize(safetyInput) };
}

export function executorKindForHire(record: AgentInstanceRecord): "pi" | AgentExecutor | null {
  if (record.executor === "pi") return "pi";
  if (record.role_kind === "brief") return null;
  return record.executor as AgentExecutor;
}
