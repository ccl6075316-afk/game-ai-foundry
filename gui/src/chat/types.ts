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

export interface BriefBrainstormResult {
  session_path?: string;
  assistant_message: string;
  choices?: string[];
  draft_brief?: { project?: Record<string, unknown>; assets?: unknown[] };
  ready_to_export?: boolean;
  message_count?: number;
}

export interface BriefBrainstormStatus {
  exists: boolean;
  id?: string;
  ready_to_export?: boolean;
  message_count?: number;
  title?: string;
  asset_count?: number;
  last_choices?: string[];
}

export function parseRunFlags(text: string): { runPrompts: boolean } {
  return { runPrompts: /\s--run-prompts\b/i.test(text.trim()) };
}

export const SUGGESTIONS = [
  { label: "策划 Brief", desc: "多轮对话澄清需求，生成 brief", cmd: "/brief" },
  { label: "检测环境", desc: "doctor 探测 Python / Godot / API", cmd: "/doctor" },
  { label: "生成流水线", desc: "基于当前 brief 生成 manifest", cmd: "/plan" },
  { label: "运行 Pipeline", desc: "执行资产生成；可加 --run-prompts", cmd: "/run" },
] as const;

export function parseChatCommand(text: string): string | null {
  const t = text.trim();
  if (!t.startsWith("/")) return null;
  return t.split(/\s+/)[0]!.toLowerCase();
}
