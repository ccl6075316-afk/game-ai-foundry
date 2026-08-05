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

export interface ToolPermissionCard {
  permissionId: string;
  sessionId: string;
  turnId?: string;
  argvSummary: string;
  status: "pending" | "allowed_once" | "allowed_turn" | "allowed_session" | "denied";
  source?: "pi" | "cursor_acp" | "hermes_acp" | "codex_app_server";
}

export interface MakeabilityCardState {
  status: "pending" | "applied" | "repair_failed" | "dismissed";
  review: MakeabilityReview;
  /** Last submitted answers — used for repair_failed retry without re-picking. */
  lastAnswers?: MakeabilityGapAnswer[];
}

export interface MakeabilityGapAnswer {
  gap_id: string;
  choice?: string;
  note?: string;
}

export interface MakeabilityAnswerResult {
  ok?: boolean;
  repair_failed?: boolean;
  verified_ids?: string[];
  repair_failed_ids?: string[];
  remaining_intent_count?: number;
  closed_ids?: string[];
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: number;
  attachments?: ChatAttachment[];
  choices?: string[];
  toolPermission?: ToolPermissionCard;
  /** Structured Critic gap card (not main-LLM chat chips). */
  makeabilityCard?: MakeabilityCardState;
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
    art_tokens?: Record<string, unknown>;
    [key: string]: unknown;
  };
    assets?: Array<{
    name?: string;
    id?: string;
    type?: string;
    usage?: string;
    description?: string;
    style_group?: string;
    style_anchor_kind?: string;
    style_anchor?: string;
    identity_anchor?: string;
    use_style_img2img?: boolean;
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
  /** brief chat LLM backend: pi | host */
  llm_backend?: string | null;
  /** last Pi error when fallen back to host */
  llm_pi_error?: string | null;
  bound_brief_rel?: string | null;
  project_slug?: string | null;
  /** Makeability Critic review present on session */
  has_review?: boolean;
  intent_count?: number;
  detail_count?: number;
  makeability_fingerprint_match?: boolean;
}

export interface MakeabilityIntentGapOccurrence {
  path: string;
  relation: "canonical" | "duplicate" | "conflict";
  current_summary?: string;
}

export interface MakeabilityIntentGap {
  id?: string;
  decision_key?: string;
  target_paths?: string[];
  occurrences?: MakeabilityIntentGapOccurrence[];
  write_paths?: string[];
  question?: string;
  why_blocking?: string;
  choices?: string[];
}

export interface MakeabilityDetailGap {
  id?: string;
  topic?: string;
  suggested_table_shape?: string;
  example_keys?: string[];
}

export interface MakeabilityReview {
  schema_version?: number;
  reviewed_at?: string;
  draft_fingerprint?: string;
  intent_gaps?: MakeabilityIntentGap[];
  detail_gaps?: MakeabilityDetailGap[];
  /** Critic-verified failures with saved answers — GUI shows retry card. */
  repair_gaps?: MakeabilityIntentGap[];
  repair_answers?: MakeabilityGapAnswer[];
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
