import { useEffect, useRef } from "react";
import type { ChatMessage } from "../chat/types";
import type { ChatAgentRole, RoleSuggestion } from "../chat/roles";
import { CHAT_AGENT_AVATAR, CHAT_AGENT_LABELS } from "../chat/roles";
import { MessageMedia } from "./MessageMedia";
import { mergeMessageChoices } from "../chat/inferChoices";

interface Props {
  messages: ChatMessage[];
  busy: boolean;
  /** Shown under typing dots while waiting (e.g. elapsed seconds). */
  busyHint?: string;
  onSuggestion: (cmd: string) => void;
  onToolPermissionDecision?: (
    permissionId: string,
    decision: "once" | "turn" | "session" | "deny",
  ) => void;
  heroTitle?: string;
  heroSubtitle?: string;
  suggestions?: RoleSuggestion[];
  agentRole?: ChatAgentRole;
  agentLabel?: string;
}

function RoleAvatar({ role, label }: { role?: ChatAgentRole; label?: string }) {
  const letter = role ? CHAT_AGENT_AVATAR[role] : "AI";
  const title = label || (role ? CHAT_AGENT_LABELS[role] : "助手");
  return (
    <div
      className={`message__avatar message__avatar--role ${role ? `message__avatar--${role}` : ""}`}
      aria-hidden
      title={title}
    >
      {letter}
    </div>
  );
}

export function ChatView({
  messages,
  busy,
  busyHint,
  onSuggestion,
  onToolPermissionDecision,
  heroTitle = "今天想做什么游戏？",
  heroSubtitle = "从 brief 到资产生成、Godot 组装与玩法开发 — 在下方描述想法，或用快捷入口驱动 pipeline。",
  suggestions = [],
  agentRole,
  agentLabel,
}: Props) {
  const endRef = useRef<HTMLDivElement>(null);
  const hasConversation = messages.some((m) => m.role === "user" || m.role === "log");
  const showHero = !hasConversation && !busy;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  return (
    <div className="chat-view">
      {showHero ? (
        <div className="chat-hero">
          <div className={`chat-hero__icon chat-hero__icon--${agentRole || "brief"}`} aria-hidden>
            {agentRole ? CHAT_AGENT_AVATAR[agentRole] : "◇"}
          </div>
          <h1 className="chat-hero__title">{heroTitle}</h1>
          <p className="chat-hero__subtitle">{heroSubtitle}</p>
          {suggestions.length > 0 && (
            <div className="chat-hero__suggestions">
              {suggestions.map(({ label, desc, cmd }) => (
                <button
                  key={cmd}
                  type="button"
                  className="suggestion"
                  disabled={busy}
                  onClick={() => onSuggestion(cmd)}
                >
                  <span className="suggestion__label">{label}</span>
                  <span className="suggestion__desc">{desc}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      ) : (
        <>
          <div className="chat-messages">
            {messages.map((m) => {
              const clickChoices =
                m.role === "assistant"
                  ? mergeMessageChoices(m.choices, m.content)
                  : undefined;
              return (
              <article key={m.id} className={`message message--${m.role}`}>
                {m.role === "assistant" && <RoleAvatar role={agentRole} label={agentLabel} />}
                {m.role === "user" && (
                  <div className="message__avatar message__avatar--user" aria-hidden>
                    U
                  </div>
                )}
                <div className="message__content">
                  {m.role === "log" && <span className="message__tag">终端</span>}
                  {m.role === "assistant" && agentLabel && (
                    <span className="message__tag message__tag--role">{agentLabel}</span>
                  )}
                  {m.attachments && m.attachments.length > 0 && (
                    <MessageMedia attachments={m.attachments} />
                  )}
                  {m.content ? (
                    <div className="message__text">{renderContent(m.content)}</div>
                  ) : null}
                  {m.toolPermission ? (
                    <div className="tool-permission-card">
                      <div className="tool-permission-card__title">
                        {m.toolPermission.source === "cursor_acp"
                          ? "Cursor 需要批准"
                          : m.toolPermission.source === "hermes_acp"
                            ? "Hermes 需要批准"
                            : "需要批准的变更"}
                      </div>
                      <code className="tool-permission-card__cmd">
                        {m.toolPermission.argvSummary || "gamefactory …"}
                      </code>
                      {m.toolPermission.status === "pending" ? (
                        <div className="tool-permission-card__actions">
                          <button
                            type="button"
                            className="tool-permission-card__btn"
                            onClick={() =>
                              onToolPermissionDecision?.(m.toolPermission!.permissionId, "once")
                            }
                          >
                            允许一次
                          </button>
                          <button
                            type="button"
                            className="tool-permission-card__btn"
                            onClick={() =>
                              onToolPermissionDecision?.(m.toolPermission!.permissionId, "turn")
                            }
                          >
                            本回合允许
                          </button>
                          <button
                            type="button"
                            className="tool-permission-card__btn"
                            onClick={() =>
                              onToolPermissionDecision?.(m.toolPermission!.permissionId, "session")
                            }
                          >
                            本会话允许
                          </button>
                          <button
                            type="button"
                            className="tool-permission-card__btn tool-permission-card__btn--deny"
                            onClick={() =>
                              onToolPermissionDecision?.(m.toolPermission!.permissionId, "deny")
                            }
                          >
                            拒绝
                          </button>
                        </div>
                      ) : (
                        <div className="tool-permission-card__status">
                          {statusLabel(m.toolPermission.status)}
                        </div>
                      )}
                    </div>
                  ) : null}
                  {clickChoices && clickChoices.length > 0 && (
                    <div className="message__choices">
                      {clickChoices.map((c) => (
                        <button
                          key={c}
                          type="button"
                          className="message__choice"
                          disabled={busy}
                          onClick={() => onSuggestion(c)}
                        >
                          {c}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </article>
              );
            })}
            {busy && (
              <article className="message message--assistant message--typing">
                <RoleAvatar role={agentRole} label={agentLabel} />
                <div className="message__content">
                  <span className="typing-indicator">
                    <span />
                    <span />
                    <span />
                  </span>
                  {busyHint ? (
                    <div className="message__busy-hint">{busyHint}</div>
                  ) : null}
                </div>
              </article>
            )}
            <div ref={endRef} />
          </div>
          <div className="chat-view__fade" aria-hidden />
        </>
      )}
    </div>
  );
}

function statusLabel(
  status: NonNullable<ChatMessage["toolPermission"]>["status"],
): string {
  switch (status) {
    case "allowed_once":
      return "已允许（一次）";
    case "allowed_turn":
      return "已允许（本回合）";
    case "allowed_session":
      return "已允许（本会话）";
    case "denied":
      return "已拒绝 / 超时";
    default:
      return status;
  }
}

function renderContent(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\n)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={i}>{part.slice(1, -1)}</code>;
    }
    if (part === "\n") return <br key={i} />;
    return <span key={i}>{part}</span>;
  });
}
