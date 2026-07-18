/** Infer clickable chips when the model puts options in prose but omits JSON `choices`. */

const LINE_OPTION =
  /^(?:[-*•]|\d+[.)、]|[A-Da-d][.)、]|选项\s*[A-Da-d\d])\s*(.+)$/;

export function inferChoicesFromText(text: string, max = 6): string[] {
  const raw = (text || "").trim();
  if (!raw) return [];
  const lines = raw.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  const found: string[] = [];
  for (const line of lines) {
    const m = line.match(LINE_OPTION);
    if (!m) continue;
    let opt = (m[1] || "").trim();
    // Strip trailing punctuation / markdown bold
    opt = opt.replace(/^\*\*|\*\*$/g, "").replace(/[。；;]+$/g, "").trim();
    if (opt.length < 2 || opt.length > 80) continue;
    if (!found.includes(opt)) found.push(opt);
    if (found.length >= max) break;
  }
  // Need at least 2 option-like lines to avoid false positives
  return found.length >= 2 ? found : [];
}

export function mergeMessageChoices(
  explicit: string[] | undefined,
  content: string,
): string[] | undefined {
  if (explicit && explicit.length > 0) return explicit;
  const inferred = inferChoicesFromText(content);
  return inferred.length ? inferred : undefined;
}
