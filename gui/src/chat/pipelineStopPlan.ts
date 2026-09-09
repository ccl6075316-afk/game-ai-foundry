/** Pipeline pause copy + next-step chips — avoid heal↔run ping-pong. */

export type DiagnoseItem = {
  task_id?: string;
  kind?: string;
  summary?: string;
  pm_fit?: string;
  pm_tip?: string;
};

export type PmFitAdvice = {
  suitable: boolean;
  headline: string;
  detail: string;
  primaryFailure: { taskId: string; kind: string; message: string } | null;
};

export type PipelineRunPayload = {
  complete?: boolean;
  paused?: boolean;
  blocked?: boolean;
  message?: string;
  last_task?: string;
  last_exit_code?: number;
  summary?: {
    counts?: Record<string, number>;
    failed_ids?: string[];
    ready_ids?: string[];
    ready_count?: number;
    done?: boolean;
  };
};

export type PipelineStatusLike = {
  counts?: Record<string, number>;
  failed_ids?: string[];
  ready_ids?: string[];
  skipped_ids?: string[];
};

export const RETRY_FIX_AND_CONTINUE = "再试一次（修复并续跑）";
export const PM_HANDLE_FAILURE = "项目经理处理失败";
export const RUN_WITH_PROMPTS = "运行资产生成（含文案）";
/** Pass 4 — write godot-developer handoff (dev_*.json) */
export const GENERATE_DEV_HANDOFF = "生成程序员交接";
export const SWITCH_TO_PROGRAMMER = "切换到程序员";
export const START_FROM_HANDOFF = "按交接开工";

export function isGameDevHandoffReady(opts: {
  failedIds?: string[] | null;
  readyIds?: string[] | null;
  pending?: number;
  skippedIds?: string[] | null;
}): boolean {
  const failed = opts.failedIds || [];
  if (failed.length > 0) return false;
  const ready = (opts.readyIds || []).filter(Boolean);
  const skipped = (opts.skippedIds || []).filter(Boolean);
  const isDev = (id: string) => id.endsWith(".godot.dev-context");
  if (ready.length > 0 && ready.every(isDev)) return true;
  if (ready.length === 0 && skipped.length > 0 && skipped.every(isDev)) {
    return Number(opts.pending ?? 0) === 0;
  }
  return false;
}

const FAILURE_KIND_LABEL: Record<string, string> = {
  network: "网络/CDN 错误",
  billing: "API 余额不足",
  validation: "出图校验未通过",
  config_size: "出图尺寸配置",
  config_proxy: "代理配置",
  missing_file: "缺少上游产物",
  stale_plan: "Plan 与生成器不匹配",
  unknown: "运行失败",
};

function diagnoseItemTip(n: DiagnoseItem): string {
  const summary = String(n.summary || "").trim();
  const pmTip = String(n.pm_tip || "").trim();
  if (summary) return summary;
  return pmTip;
}

function taskStepFromId(taskId: string): string {
  const dot = taskId.lastIndexOf(".");
  return dot >= 0 ? taskId.slice(dot + 1) : "";
}

export function failureKindLabel(kind: string, taskId: string): string {
  const step = taskStepFromId(taskId);
  if (kind === "validation" && step === "prompt.craft") {
    return "Prompt/文案生成未通过";
  }
  if (kind === "validation" && step === "image.generate") {
    return "出图校验未通过";
  }
  return FAILURE_KIND_LABEL[kind] || kind || "运行失败";
}

export function formatPmFitAdvice(data: {
  pm_fit?: string;
  pm_suitable?: boolean;
  pm_advice?: string;
  pm_advice_short?: string;
  items?: DiagnoseItem[];
  needs_hermes?: DiagnoseItem[];
} | null | undefined): PmFitAdvice {
  if (!data) {
    return {
      suitable: false,
      headline: "未能诊断失败原因",
      detail: "可打开看板查看 failed 任务，或点「再试一次（修复并续跑）」。",
      primaryFailure: null,
    };
  }
  const items = (data.items?.length ? data.items : data.needs_hermes) || [];
  const lines = items.slice(0, 6).map((n) => {
    const fit =
      n.pm_fit === "yes"
        ? "适合"
        : n.pm_fit === "no"
          ? "不必"
          : n.pm_fit === "maybe"
            ? "可分诊"
            : "?";
    const tip = diagnoseItemTip(n);
    return `- \`${n.task_id || "?"}\`（${n.kind || "?"}）· **${fit}**${tip ? ` — ${tip}` : ""}`;
  });
  const first = items[0];
  const primaryFailure = first
    ? {
        taskId: String(first.task_id || "?"),
        kind: String(first.kind || "unknown"),
        message: diagnoseItemTip(first) || String(first.summary || "").trim() || "未知错误",
      }
    : null;
  const headline =
    data.pm_advice_short ||
    (data.pm_suitable ? "适合项目经理直接处理" : "不必找项目经理");
  const detail =
    (data.pm_advice ? `${data.pm_advice}\n\n` : "") +
    (lines.length ? `逐项：\n${lines.join("\n")}` : "");
  return { suitable: Boolean(data.pm_suitable), headline, detail, primaryFailure };
}

function failureLeadBlock(
  primary: { taskId: string; kind: string; message: string } | null,
): string {
  if (!primary?.message) return "";
  const label = failureKindLabel(primary.kind, primary.taskId);
  return `**失败原因**（${label} · \`${primary.taskId}\`）\n${primary.message}\n\n`;
}

/**
 * Stop notice after pipeline pause.
 * When alreadyAutoFixed, never bounce between「处理失败」and「运行」— Host already did both.
 */
export function planPipelineStop(opts: {
  exitCode: number;
  runData?: PipelineRunPayload | null;
  advice: PmFitAdvice;
  healed: string[];
  status?: PipelineStatusLike | null;
  /** Host/GUI already ran diagnose→heal→续跑（含文案） */
  alreadyAutoFixed?: boolean;
  stoppedReason?: string | null;
  /** Persist path for failure-log.jsonl (survives heal) */
  failureLogPath?: string | null;
}): { title: string; body: string; choices: string[] } {
  const summary = opts.status || opts.runData?.summary;
  const counts = summary?.counts || {};
  const done = Number(counts.done ?? 0);
  const pending = Number(counts.pending ?? 0);
  const failedN = Number(
    counts.failed ??
      opts.status?.failed_ids?.length ??
      opts.runData?.summary?.failed_ids?.length ??
      0,
  );
  const ready =
    opts.status?.ready_ids?.length ??
    opts.runData?.summary?.ready_ids?.length ??
    opts.runData?.summary?.ready_count ??
    0;
  const progress =
    `进度：完成 ${done} · 待跑 ${pending}` + (failedN ? ` · 失败 ${failedN}` : "");
  const last = opts.runData?.last_task
    ? `\n停在：\`${opts.runData.last_task}\`` +
      (opts.runData.last_exit_code != null ? `（exit ${opts.runData.last_exit_code}）` : "")
    : "";
  const paused = Boolean(opts.runData?.paused) || opts.exitCode === 2 || failedN > 0;
  const blocked = Boolean(opts.runData?.blocked);
  const failureLead = failureLeadBlock(opts.advice.primaryFailure);
  const pauseTitle = opts.advice.primaryFailure
    ? `流水线已暂停：${failureKindLabel(opts.advice.primaryFailure.kind, opts.advice.primaryFailure.taskId)}`
    : "流水线已暂停";
  const sameFailure = opts.stoppedReason === "same_failure";

  if (paused && failedN > 0) {
    if (opts.alreadyAutoFixed) {
      return {
        title: pauseTitle,
        body:
          failureLead +
          `默认遇失败即停，已完成的任务会保留。\n${progress}${last}\n\n` +
          (sameFailure
            ? `同一失败已反复出现，自动修复已停止空转。\n` +
              `再点「项目经理处理失败」或「运行资产生成」只会重复同一结果。\n\n`
            : `自动修复（diagnose → heal → 含文案续跑）已跑过仍失败。\n` +
              `不要在「项目经理处理失败」和「运行资产生成」之间来回点——两边都会再走同一套 Host 修复。\n\n`) +
          `**推荐下一步 → 打开看板** 看该任务 stderr（含 rejected_text / llm_raw_preview 时最有用）。` +
          (sameFailure
            ? ""
            : `\n确认根因后若要再试，点「${RETRY_FIX_AND_CONTINUE}」（仍是修复+续跑，不是换另一个空按钮）。`) +
          (opts.advice.primaryFailure
            ? `\n\n逐项：\n- \`${opts.advice.primaryFailure.taskId}\`（${opts.advice.primaryFailure.kind}）— ${opts.advice.primaryFailure.message}`
            : ""),
        choices: sameFailure
          ? ["打开看板"]
          : ["打开看板", RETRY_FIX_AND_CONTINUE],
      };
    }

    if (opts.advice.suitable) {
      return {
        title: pauseTitle,
        body:
          failureLead +
          `默认遇失败即停，已完成的任务会保留。\n${progress}${last}\n\n` +
          `**推荐下一步 → ${PM_HANDLE_FAILURE}**\n` +
          `（${opts.advice.headline}）\n\n${opts.advice.detail}` +
          `\n\n点一次将自动 diagnose → heal → **含文案续跑**；不必再另点「运行资产生成」。` +
          (opts.healed.length
            ? `\n\n另已自动复位 ${opts.healed.length} 项（网络/缺文件），会一并续跑。`
            : ""),
        choices: [PM_HANDLE_FAILURE, "打开看板"],
      };
    }

    if (opts.healed.length) {
      return {
        title: pauseTitle,
        body:
          failureLead +
          `${progress}${last}\n\n` +
          `已自动复位：${opts.healed.slice(0, 6).join(", ")}${opts.healed.length > 6 ? "…" : ""}\n` +
          `（${opts.advice.headline}）\n\n` +
          `**推荐下一步 → ${RETRY_FIX_AND_CONTINUE}**（修复并含文案续跑）`,
        choices: [RETRY_FIX_AND_CONTINUE, "打开看板"],
      };
    }

    return {
      title: pauseTitle,
      body:
        failureLead +
        `默认遇失败即停，已完成的任务会保留。\n${progress}${last}\n\n` +
        `**推荐下一步 → ${RETRY_FIX_AND_CONTINUE}**\n` +
        `（${opts.advice.headline}）\n\n${opts.advice.detail}`,
      choices: [RETRY_FIX_AND_CONTINUE, "打开看板"],
    };
  }

  if (blocked) {
    return {
      title: "流水线卡住了",
      body:
        `${progress}\n` +
        (opts.runData?.message ? `${opts.runData.message}\n` : "") +
        `\n常见原因：上游失败未清、缺文案 plan、或缺依赖产物。\n\n` +
        `**推荐下一步 → 打开看板** 看哪条红了；需要时点「${RETRY_FIX_AND_CONTINUE}」。`,
      choices: ["打开看板", RETRY_FIX_AND_CONTINUE],
    };
  }

  if (ready > 0 || pending > 0) {
    const readyIds =
      opts.status?.ready_ids ||
      opts.runData?.summary?.ready_ids ||
      [];
    if (
      isGameDevHandoffReady({
        failedIds: opts.status?.failed_ids || opts.runData?.summary?.failed_ids || [],
        readyIds,
        pending,
        skippedIds: opts.status?.skipped_ids || [],
      })
    ) {
      return {
        title: "资产已齐，可生成程序员交接",
        body:
          `${progress}` +
          (ready > 0 ? `（其中 ${ready} 个已就绪）` : "") +
          `${last}\n\n` +
          `资产流水线已就绪，Pass 4（\`godot.dev-context\`）默认未跑。\n\n` +
          `**推荐下一步 → ${GENERATE_DEV_HANDOFF}**（写出 \`plans/dev_*.json\` 给程序员）`,
        choices: [GENERATE_DEV_HANDOFF, "打开看板"],
      };
    }
    if (opts.alreadyAutoFixed) {
      const logHint = opts.failureLogPath
        ? `\n失败日志：\`${opts.failureLogPath}\``
        : "";
      return {
        title: "本轮已停下，还有任务未跑完",
        body:
          failureLead +
          `${progress}` +
          (ready > 0 ? `（其中 ${ready} 个已就绪）` : "") +
          `${last}\n\n` +
          (sameFailure
            ? `同一失败已反复出现，自动修复已停止空转。Host 复位后看板可能不再标红 failed。\n`
            : `自动修复已跑过仍未跑完。不要改点「运行资产生成」指望另一条路。\n`) +
          `\n**推荐下一步 → ${RETRY_FIX_AND_CONTINUE}** 或打开看板核对。` +
          (opts.advice.primaryFailure
            ? `\n\n（失败时：\`${opts.advice.primaryFailure.taskId}\` · ${opts.advice.primaryFailure.kind}）`
            : "") +
          logHint,
        choices: sameFailure
          ? ["打开看板", RETRY_FIX_AND_CONTINUE]
          : [RETRY_FIX_AND_CONTINUE, "打开看板"],
      };
    }
    return {
      title: "本轮已停下，还有任务未跑完",
      body:
        `${progress}` +
        (ready > 0 ? `（其中 ${ready} 个已就绪）` : "") +
        `${last}\n\n` +
        `**推荐下一步 → ${RUN_WITH_PROMPTS}**（续跑，已完成的会跳过）`,
      choices: [RUN_WITH_PROMPTS, "打开看板"],
    };
  }

  if (
    isGameDevHandoffReady({
      failedIds: opts.status?.failed_ids || opts.runData?.summary?.failed_ids || [],
      readyIds: [],
      pending: 0,
      skippedIds: opts.status?.skipped_ids || [],
    })
  ) {
    return {
      title: "资产已齐，可生成程序员交接",
      body:
        `${progress}${last}\n\n` +
        `Pass 4 先前被跳过。点 **${GENERATE_DEV_HANDOFF}** 写出程序员 handoff。`,
      choices: [GENERATE_DEV_HANDOFF, "打开看板"],
    };
  }

  return {
    title: "流水线已结束",
    body: `${progress}${last}\n\n可打开看板确认，或继续派工给程序员。`,
    choices: ["打开看板"],
  };
}
