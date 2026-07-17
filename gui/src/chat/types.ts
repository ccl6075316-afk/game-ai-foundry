export type ChatRole = "user" | "assistant" | "system" | "log";

export type ChatAttachmentKind = "image" | "video";

export interface ChatAttachment {
  path: string;
  kind: ChatAttachmentKind;
  label?: string;
  posterPath?: string;
}

export interface MediaPreview {
  kind: ChatAttachmentKind;
  name: string;
  path: string;
  previewUrl?: string;
  posterUrl?: string;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: number;
  attachments?: ChatAttachment[];
  choices?: string[];
}

let seq = 0;
export function newMessageId(): string {
  seq += 1;
  return `msg-${Date.now()}-${seq}`;
}

export interface HostChatResult {
  session_path?: string;
  session_id?: string;
  assistant_message: string;
  choices?: string[];
  draft_brief?: { project?: Record<string, unknown>; assets?: unknown[] };
  ready_to_export?: boolean;
  message_count?: number;
  mode?: string;
  intent_hint?: string;
}

export interface HostChatStatus {
  exists: boolean;
  id?: string;
  ready_to_export?: boolean;
  message_count?: number;
  title?: string;
  asset_count?: number;
  last_choices?: string[];
  mode?: string;
  has_summary?: boolean;
}

export function parseRunFlags(text: string): { runPrompts: boolean } {
  return { runPrompts: /\s--run-prompts\b/i.test(text.trim()) };
}

export function parseChatCommand(text: string): string | null {
  const t = text.trim();
  if (!t.startsWith("/")) return null;
  return t.split(/\s+/)[0]!.toLowerCase();
}
