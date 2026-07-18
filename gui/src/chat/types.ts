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

export interface HostChatDraftBrief {
  project?: {
    title?: string;
    genre?: string;
    gameplay_loop?: string;
    description?: string;
    [key: string]: unknown;
  };
  assets?: Array<{
    name?: string;
    type?: string;
    usage?: string;
    description?: string;
    [key: string]: unknown;
  }>;
  animation_graphs?: unknown[];
  [key: string]: unknown;
}

export interface HostChatDraftDocument {
  title?: string;
  format?: string;
  body?: string;
}

export interface HostChatAssetSummary {
  name: string;
  type?: string;
  usage?: string;
}

export interface HostChatResult {
  session_path?: string;
  session_id?: string;
  assistant_message: string;
  choices?: string[];
  draft_brief?: HostChatDraftBrief | null;
  draft_document?: HostChatDraftDocument | null;
  ready_to_export?: boolean;
  gaps?: string[];
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
  genre?: string;
  gameplay_loop?: string;
  asset_count?: number;
  assets?: HostChatAssetSummary[];
  draft_brief?: HostChatDraftBrief | null;
  draft_document?: HostChatDraftDocument | null;
  document_title?: string;
  has_document?: boolean;
  last_choices?: string[];
  mode?: string;
  gaps?: string[];
  contract_complete?: boolean;
  has_summary?: boolean;
}

export interface ProjectDocItem {
  path: string;
  label: string;
  kind: "brief" | "markdown" | "json";
}

export function parseRunFlags(text: string): { runPrompts: boolean } {
  return { runPrompts: /\s--run-prompts\b/i.test(text.trim()) };
}

export function parseChatCommand(text: string): string | null {
  const t = text.trim();
  if (!t.startsWith("/")) return null;
  return t.split(/\s+/)[0]!.toLowerCase();
}
