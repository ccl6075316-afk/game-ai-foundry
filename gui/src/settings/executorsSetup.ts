export type ExecutorId = "codex" | "hermes" | "cursor";

export interface ExecutorStep {
  id: string;
  label: string;
  hint?: string;
  done: boolean;
  active?: boolean;
  optional?: boolean;
}

export interface ExecutorSetupInfo {
  id: ExecutorId;
  label: string;
  description: string;
  download_url?: string;
  ready: boolean;
  path?: string | null;
  steps: ExecutorStep[];
}

export interface ExecutorSetupReport {
  executors: Record<ExecutorId, ExecutorSetupInfo>;
}

export const EXECUTOR_ORDER: ExecutorId[] = ["cursor", "hermes", "codex"];

export function nextExecutorStep(info: ExecutorSetupInfo): ExecutorStep | undefined {
  return info.steps.find((s) => !s.done && !s.optional) || info.steps.find((s) => !s.done);
}
