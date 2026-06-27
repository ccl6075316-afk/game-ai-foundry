import type { ChatAttachment } from "./types";

const IMAGE_EXT = new Set([".png", ".jpg", ".jpeg", ".webp", ".gif"]);
const VIDEO_EXT = new Set([".mp4", ".webm", ".mov", ".mkv"]);

const PATH_PATTERN =
  /(?:^|[\s"'`(])((?:[a-zA-Z]:[\\/]|\.{0,2}[\\/])[\w\s.\-/\\]+\.(?:png|jpe?g|webp|gif|mp4|webm|mov|mkv)|(?:output|games|plans)[/\\][\w\s.\-/\\]+\.(?:png|jpe?g|webp|gif|mp4|webm|mov|mkv))/gi;

function extKind(ext: string): ChatAttachment["kind"] | null {
  const lower = ext.toLowerCase();
  if (IMAGE_EXT.has(lower)) return "image";
  if (VIDEO_EXT.has(lower)) return "video";
  return null;
}

function normalizePath(raw: string): string {
  return raw.replace(/\\/g, "/").replace(/^\.\//, "");
}

export function extractMediaPaths(text: string): ChatAttachment[] {
  const out: ChatAttachment[] = [];
  const seen = new Set<string>();

  for (const match of text.matchAll(PATH_PATTERN)) {
    const raw = match[1];
    if (!raw) continue;
    const normalized = normalizePath(raw.trim());
    const ext = normalized.slice(normalized.lastIndexOf(".")).toLowerCase();
    const kind = extKind(ext);
    if (!kind || seen.has(normalized)) continue;
    seen.add(normalized);
    out.push({
      path: normalized,
      kind,
      label: normalized.split("/").pop() || normalized,
    });
  }
  return out;
}

export function mergeAttachments(
  existing: ChatAttachment[] | undefined,
  incoming: ChatAttachment[],
): ChatAttachment[] {
  if (!incoming.length) return existing || [];
  const map = new Map<string, ChatAttachment>();
  for (const a of existing || []) map.set(a.path, a);
  for (const a of incoming) map.set(a.path, a);
  return [...map.values()];
}
