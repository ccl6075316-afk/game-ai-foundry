import type { DoctorReport } from "../vite-env.d";
import type { ToolchainReport } from "./toolchain";
import type { ExecutorSetupReport } from "./executorsSetup";

export type EnvIssueSeverity = "error" | "warn";

export interface EnvIssue {
  id: string;
  severity: EnvIssueSeverity;
  title: string;
  detail: string;
  fixHint: string;
}

export interface EnvHealth {
  ok: boolean;
  issues: EnvIssue[];
  blocking: EnvIssue[];
  /** Short lines for chat / copy-paste to support */
  summaryLines: string[];
}

function clip(text: string, max = 400): string {
  const t = (text || "").trim();
  if (!t) return "";
  return t.length > max ? `${t.slice(0, max)}…` : t;
}

/** Build a user-facing health report from doctor + toolchain + executors. */
export function summarizeEnvHealth(input: {
  doctor: DoctorReport | null;
  doctorExitCode?: number | null;
  doctorStderr?: string;
  doctorStdout?: string;
  toolchain: ToolchainReport | null;
  toolchainExitCode?: number | null;
  toolchainStderr?: string;
  toolchainStdout?: string;
  executors?: ExecutorSetupReport | null;
}): EnvHealth {
  const issues: EnvIssue[] = [];

  const docExit = input.doctorExitCode;
  if (!input.doctor) {
    issues.push({
      id: docExit != null && docExit !== 0 ? "doctor-exit" : "doctor-parse",
      severity: "error",
      title: docExit != null && docExit !== 0 ? "环境检测命令失败" : "环境检测无有效结果",
      detail:
        (docExit != null && docExit !== 0 ? `doctor 退出码 ${docExit}。` : "") +
        (clip(input.doctorStderr || input.doctorStdout || "") ||
          "doctor 没有返回可解析的 JSON（可能是 Python/CLI 路径不对）。"),
      fixHint: "打开「环境」点重新检测；把这段错误原文发给支持。",
    });
  } else {
    const cfg = input.doctor.config;
    if (!cfg?.exists) {
      issues.push({
        id: "config-missing",
        severity: "error",
        title: "缺少配置文件",
        detail: `未找到 ${cfg?.path || "~/.gamefactory/config.json"}`,
        fixHint: "打开「设置」初始化配置，并填入图像 API Key。",
      });
    }
    if (cfg?.openrouter_key !== "set") {
      issues.push({
        id: "image-api-key",
        severity: "error",
        title: "图像 API Key 未配置",
        detail: "生图 / 北极星图需要 OpenRouter（或等价）图像 API Key。",
        fixHint: "设置 → 在线服务 → 填入 API Key 后点「重新检测」。",
      });
    }
    if (cfg?.seedance_key !== "set") {
      issues.push({
        id: "video-api-key",
        severity: "warn",
        title: "视频 API Key 未配置",
        detail: "有角色动画（视频）任务时需要 Seedance / 视频 Key。",
        fixHint: "仅做静图可先忽略；要做动画请在设置里补视频 Key。",
      });
    }
    const caps = input.doctor.capabilities || {};
    if (caps.image_api === false && cfg?.openrouter_key === "set") {
      issues.push({
        id: "image-api-cap",
        severity: "warn",
        title: "图像能力标记为不可用",
        detail: "配置里似乎有 Key，但 doctor 仍报 image_api=false。",
        fixHint: "检查 Key 是否写在正确字段；保存配置后重新检测。",
      });
    }
  }

  const tcExit = input.toolchainExitCode;
  if (!input.toolchain) {
    issues.push({
      id: tcExit != null && tcExit !== 0 ? "toolchain-exit" : "toolchain-parse",
      severity: "error",
      title: tcExit != null && tcExit !== 0 ? "本机工具检测失败" : "本机工具检测无有效结果",
      detail:
        (tcExit != null && tcExit !== 0 ? `setup check 退出码 ${tcExit}。` : "") +
        (clip(input.toolchainStderr || input.toolchainStdout || "") ||
          "setup check 没有返回 JSON。"),
      fixHint: "重新检测；仍失败则把完整错误原文发给支持。",
    });
  } else {
    for (const id of input.toolchain.missing_required || []) {
      const comp = input.toolchain.components.find((c) => c.id === id);
      issues.push({
        id: `tool-missing-${id}`,
        severity: "error",
        title: `缺少必需工具：${comp?.label || id}`,
        detail: comp?.description || `${id} 未安装或不在 PATH`,
        fixHint: "顶部工具栏 / 环境面板可一键安装；或按下载链接手动安装。",
      });
    }
    for (const id of input.toolchain.missing_optional || []) {
      const comp = input.toolchain.components.find((c) => c.id === id);
      issues.push({
        id: `tool-optional-${id}`,
        severity: "warn",
        title: `缺少可选工具：${comp?.label || id}`,
        detail: comp?.description || `${id} 未安装`,
        fixHint: "部分流程可能用到；可按需安装。",
      });
    }
  }

  // Deduplicate by id
  const seen = new Set<string>();
  const unique = issues.filter((i) => {
    if (seen.has(i.id)) return false;
    seen.add(i.id);
    return true;
  });

  const blocking = unique.filter((i) => i.severity === "error");
  const summaryLines = unique.map(
    (i) => `${i.severity === "error" ? "✗" : "⚠"} ${i.title} — ${i.detail}（处理：${i.fixHint}）`,
  );

  return {
    ok: blocking.length === 0,
    issues: unique,
    blocking,
    summaryLines,
  };
}

export function formatEnvHealthChat(health: EnvHealth): string {
  if (health.ok && health.issues.length === 0) {
    return "**环境检测通过**\n\n本机工具与 API 配置可用。若后续某步失败，把该步的红色错误原文发给支持。";
  }
  if (health.ok) {
    return (
      "**环境检测通过（有提醒）**\n\n" +
      health.summaryLines.map((l) => `- ${l}`).join("\n") +
      "\n\n可先继续；动画相关流程可能受影响。"
    );
  }
  return (
    "**环境检测未通过 — 请先处理下列问题**\n\n" +
    health.summaryLines.map((l) => `- ${l}`).join("\n") +
    "\n\n打开顶部「环境」或点「设置」修复。把以上整段复制发给支持即可定位。"
  );
}
