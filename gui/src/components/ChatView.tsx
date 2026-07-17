import { useEffect, useRef } from "react";
import type { ChatMessage } from "../chat/types";
import type { RoleSuggestion } from "../chat/roles";
import { MessageMedia } from "./MessageMedia";

interface Props {
  messages: ChatMessage[];
  busy: boolean;
  onSuggestion: (cmd: string) => void;
  heroTitle?: string;
  heroSubtitle?: string;
  suggestions?: RoleSuggestion[];
}

export function ChatView({
  messages,
  busy,
  onSuggestion,
  heroTitle = "今天想做什么游戏？",
  heroSubtitle = "从 brief 到资产生成、Godot 组装与玩法开发 — 在下方描述想法，或用快捷入口驱动 pipeline。",
  suggestions = [],
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
          <div className="chat-hero__icon" aria-hidden>
            <svg viewBox="0 0 24 24" fill="none" width="24" height="24">
              <path
                d="M12 2L4 7v10l8 5 8-5V7l-8-5z"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinejoin="round"
              />
            </svg>
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
            {messages.map((m) => (
              <article key={m.id} className={`message message--${m.role}`}>
                {m.role === "assistant" && (
                  <div className="message__avatar" aria-hidden>
                    <svg viewBox="0 0 24 24" fill="none">
                      <path
                        d="M12 2L4 7v10l8 5 8-5V7l-8-5z"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </div>
                )}
                {m.role === "user" && (
                  <div className="message__avatar message__avatar--user" aria-hidden>
                    U
                  </div>
                )}
                <div className="message__content">
                  {m.role === "log" && <span className="message__tag">终端</span>}
                  {m.attachments && m.attachments.length > 0 && (
                    <MessageMedia attachments={m.attachments} />
                  )}
                  {m.content ? (
                    <div className="message__text">{renderContent(m.content)}</div>
                  ) : null}
                </div>
              </article>
            ))}
            {busy && (
              <article className="message message--assistant message--typing">
                <div className="message__avatar" aria-hidden>
                  <svg viewBox="0 0 24 24" fill="none">
                    <path
                      d="M12 2L4 7v10l8 5 8-5V7l-8-5z"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <div className="message__content">
                  <span className="typing-indicator">
                    <span />
                    <span />
                    <span />
                  </span>
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
