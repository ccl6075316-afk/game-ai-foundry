/** Sanitize / classify product-host executor replies for GUI display. */

export function redactSecrets(text: string): string {
  return text
    .replace(/\bsk-[a-zA-Z0-9_-]{12,}\b/g, "sk-***")
    .replace(/\bsk-or-[a-zA-Z0-9_-]{12,}\b/g, "sk-or-***")
    .replace(/("api_key"\s*:\s*")[^"]{8,}(")/gi, "$1***$2");
}

/** Hermes sometimes dumps config review diffs instead of advancing the project. */
export function isConfigNoiseReply(text: string): boolean {
  const t = text || "";
  if (!/review diff|config\.json/i.test(t)) return false;
  return t.length > 600 || (t.match(/review diff/gi) || []).length >= 2;
}

export function isResumeOnlyReply(text: string): boolean {
  const t = (text || "").trim();
  if (!t) return true;
  if (/^↻?\s*Resumed session/i.test(t)) return true;
  return (
    /session_id:\s*\S+/i.test(t) &&
    t.length < 280 &&
    !/分诊|下一步|brief|pipeline|handoff/i.test(t)
  );
}

export function prepareAgentDisplay(text: string): {
  display: string;
  weak: boolean;
  reason: "resume" | "config_noise" | null;
} {
  const redacted = redactSecrets(text || "");
  if (isResumeOnlyReply(redacted)) {
    return {
      display: redacted,
      weak: true,
      reason: "resume",
    };
  }
  if (isConfigNoiseReply(redacted)) {
    return {
      display:
        "执行器输出了大量配置 diff，**未按用户要求改配置时不应自行改 config**。\n\n" +
        "若你并未点名要改设置，请忽略这次输出，直接点下方「生成流水线 / 运行资产生成」。\n" +
        "若确实要改配置，请明确说例如：「把 proxy 改成 …」。\n\n" +
        "（原始 diff 已折叠，密钥已脱敏。）",
      weak: true,
      reason: "config_noise",
    };
  }
  return { display: redacted.slice(0, 8000), weak: false, reason: null };
}
