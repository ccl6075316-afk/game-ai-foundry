import {
  CODEX_SANDBOX_OPTIONS,
  CURSOR_PERMISSION_OPTIONS,
  type CodexSandbox,
  type CursorPermissionMode,
} from "./agentExecutors";

/** Form select sentinel for「继承全局」. Must NOT be written to config JSON. */
export const INHERIT_SAFETY = "__inherit__";

export type InstanceSafetyField = "sandbox" | "permission_mode" | "yolo";

export type InstanceExecutorForSafety = "pi" | "hermes" | "codex" | "cursor";

export function safetyFieldForExecutor(
  executor: InstanceExecutorForSafety,
): InstanceSafetyField | null {
  switch (executor) {
    case "codex":
      return "sandbox";
    case "cursor":
      return "permission_mode";
    case "hermes":
      return "yolo";
    default:
      return null;
  }
}

function isValidCodexSandbox(value: unknown): value is CodexSandbox {
  const id = String(value ?? "");
  return CODEX_SANDBOX_OPTIONS.some((o) => o.id === id);
}

function isValidCursorPermissionMode(value: unknown): value is CursorPermissionMode {
  const id = String(value ?? "");
  return CURSOR_PERMISSION_OPTIONS.some((o) => o.id === id);
}

export function isInheritSafetyValue(value: unknown): boolean {
  return value === INHERIT_SAFETY || value === "";
}

export function parseInstanceSafetyFields(rec: Record<string, unknown>): {
  sandbox?: CodexSandbox;
  permission_mode?: CursorPermissionMode;
  yolo?: boolean;
} {
  const out: {
    sandbox?: CodexSandbox;
    permission_mode?: CursorPermissionMode;
    yolo?: boolean;
  } = {};

  if (rec.sandbox != null && !isInheritSafetyValue(rec.sandbox) && isValidCodexSandbox(rec.sandbox)) {
    out.sandbox = rec.sandbox;
  }
  if (
    rec.permission_mode != null &&
    !isInheritSafetyValue(rec.permission_mode) &&
    isValidCursorPermissionMode(rec.permission_mode)
  ) {
    out.permission_mode = rec.permission_mode;
  }
  if (typeof rec.yolo === "boolean") {
    out.yolo = rec.yolo;
  }

  return out;
}

/** Only include safety keys explicitly set on the record; inherit / undefined → omit. */
export function omitSafetyKeysForSerialize(record: {
  sandbox?: CodexSandbox;
  permission_mode?: CursorPermissionMode;
  yolo?: boolean;
}): Partial<{
  sandbox: CodexSandbox;
  permission_mode: CursorPermissionMode;
  yolo: boolean;
}> {
  const out: Partial<{
    sandbox: CodexSandbox;
    permission_mode: CursorPermissionMode;
    yolo: boolean;
  }> = {};

  if (record.sandbox !== undefined && !isInheritSafetyValue(record.sandbox)) {
    out.sandbox = record.sandbox;
  }
  if (record.permission_mode !== undefined && !isInheritSafetyValue(record.permission_mode)) {
    out.permission_mode = record.permission_mode;
  }
  if (record.yolo !== undefined && !isInheritSafetyValue(record.yolo)) {
    out.yolo = record.yolo;
  }

  return out;
}

/** Remove inherit sentinels and undefined safety keys before persisting a form-backed record. */
export function stripInheritedSafety<T extends Record<string, unknown>>(record: T): T {
  const out = { ...record };
  for (const key of ["sandbox", "permission_mode", "yolo"] as const) {
    const value = out[key];
    if (value === undefined || isInheritSafetyValue(value)) {
      delete out[key];
    }
  }
  return out;
}

export type SafetyFormValue = CodexSandbox | CursorPermissionMode | boolean | typeof INHERIT_SAFETY;

/** Form select value for the current executor's safety field (missing → inherit sentinel). */
export function safetyFormValue(
  record: {
    sandbox?: CodexSandbox;
    permission_mode?: CursorPermissionMode;
    yolo?: boolean;
  },
  executor: InstanceExecutorForSafety,
): SafetyFormValue {
  const field = safetyFieldForExecutor(executor);
  if (!field) return INHERIT_SAFETY;
  const value = record[field];
  return value !== undefined ? value : INHERIT_SAFETY;
}

/** Expand record with inherit sentinels on all three safety slots for form binding. */
export function recordWithSafetyForm(record: {
  sandbox?: CodexSandbox;
  permission_mode?: CursorPermissionMode;
  yolo?: boolean;
}): {
  sandbox: CodexSandbox | typeof INHERIT_SAFETY;
  permission_mode: CursorPermissionMode | typeof INHERIT_SAFETY;
  yolo: boolean | typeof INHERIT_SAFETY;
} {
  return {
    sandbox: record.sandbox !== undefined ? record.sandbox : INHERIT_SAFETY,
    permission_mode: record.permission_mode !== undefined ? record.permission_mode : INHERIT_SAFETY,
    yolo: record.yolo !== undefined ? record.yolo : INHERIT_SAFETY,
  };
}
