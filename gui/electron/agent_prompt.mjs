export function normalizeItExecutor(value) {
  const executor = String(value || "")
    .trim()
    .toLowerCase();
  return executor === "codex" || executor === "cursor" || executor === "pi" ? executor : "pi";
}

export function resolveItExecutor({ override, instanceExecutor, roleExecutor }) {
  const instance = String(instanceExecutor || "").trim();
  if (instance) return normalizeItExecutor(instance);
  const requested = String(override || "").trim();
  if (requested) return normalizeItExecutor(requested);
  return normalizeItExecutor(roleExecutor);
}

/**
 * Build CLI arguments for the shared role-aware Agent prompt builder.
 *
 * @param {object} opts
 * @param {string} opts.roleKind
 * @param {string} opts.sessionId
 * @param {string} opts.message
 * @param {string} opts.executor
 * @param {string} [opts.instanceId]
 * @param {string} [opts.briefArg]
 * @param {string} [opts.progressArg]
 * @returns {string[]}
 */
export function buildAgentPromptArgs(opts) {
  const args = [
    "agent",
    "prompt",
    "--role",
    String(opts.roleKind),
    "--session-id",
    String(opts.sessionId),
    "--message",
    String(opts.message),
    "--executor",
    String(opts.executor),
  ];
  const instanceId = String(opts.instanceId || "").trim();
  if (instanceId) args.push("--instance-id", instanceId);
  const briefArg = String(opts.briefArg || "").trim();
  if (briefArg) args.push("--brief", briefArg);
  const progressArg = String(opts.progressArg || "").trim();
  if (progressArg) args.push("--progress", progressArg);
  args.push("--json");
  return args;
}

export function buildAgentTurnArgs(opts) {
  const args = [
    "agent",
    "turn",
    "--role",
    String(opts.roleKind),
    "--session-id",
    String(opts.sessionId),
    "--message",
    String(opts.message),
    "--executor",
    String(opts.effectiveExecutor),
  ];
  const optionalArgs = [
    ["--brief", opts.briefArg],
    ["--progress", opts.progressArg],
    ["--instance-id", opts.instanceId],
    ["--target-instance-id", opts.targetInstanceId],
    ["--roster-json", opts.rosterJson],
    ["--timeout", opts.timeout],
  ];
  for (const [flag, value] of optionalArgs) {
    const text = String(value || "").trim();
    if (text) args.push(flag, text);
  }
  args.push("--json");
  return args;
}

/**
 * Resolve the executor text for an ACP turn, using the shared CLI prompt for IT.
 *
 * @param {object} opts
 * @param {string} opts.roleKind
 * @param {string} opts.message
 * @param {object} opts.promptOptions
 * @param {(args: string[]) => Promise<{exitCode: number, stdout: string, stderr: string}>} opts.runPromptCommand
 * @param {(text: string) => Record<string, unknown> | null} opts.parseJsonOutput
 * @returns {Promise<string>}
 */
export async function prepareRoleAwareAcpPrompt(opts) {
  if (opts.roleKind !== "it") return String(opts.message);

  const result = await opts.runPromptCommand(buildAgentPromptArgs(opts.promptOptions));
  const data = opts.parseJsonOutput(result.stdout) || {};
  const prompt = String(data.prompt || "").trim();
  if (result.exitCode !== 0 || data.ok === false || !prompt) {
    throw new Error(
      String(data.error || "").trim() ||
        String(result.stderr || "").trim() ||
        "无法构建 IT 角色提示词",
    );
  }
  return prompt;
}
