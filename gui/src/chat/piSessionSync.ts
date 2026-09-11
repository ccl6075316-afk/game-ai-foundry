/**
 * Map Pi RPC get_messages payloads into Foundry ChatMessage rows (C1 sync).
 */
import type { ChatMessage } from "./types";
import { newMessageId } from "./types";

function extractText(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((part) => {
        if (!part || typeof part !== "object") return "";
        const p = part as Record<string, unknown>;
        if (typeof p.text === "string") return p.text;
        return "";
      })
      .join("");
  }
  if (content && typeof content === "object") {
    const text = (content as Record<string, unknown>).text;
    if (typeof text === "string") return text;
  }
  return "";
}

/** Convert Pi agent messages → GUI chat bubbles (user/assistant only). */
export function mapPiMessagesToChat(messages: unknown[]): ChatMessage[] {
  if (!Array.isArray(messages)) return [];
  const now = Date.now();
  const out: ChatMessage[] = [];
  for (let i = 0; i < messages.length; i += 1) {
    const msg = messages[i];
    if (!msg || typeof msg !== "object") continue;
    const m = msg as Record<string, unknown>;
    const role = m.role;
    if (role !== "user" && role !== "assistant") continue;
    const text = extractText(m.content).trim();
    if (!text) continue;
    out.push({
      id: newMessageId(),
      role,
      content: text,
      timestamp: now + i,
    });
  }
  return out;
}
