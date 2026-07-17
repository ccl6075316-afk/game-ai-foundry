import { useEffect, useRef, useState } from "react";
import type { ChatAgentRole } from "../chat/roles";
import { CHAT_AGENT_LABELS } from "../chat/roles";
import type { ColleagueInstance } from "../chat/roster";
import type { ChatSession } from "../chat/sessions";

export interface HandoffSummary {
  id?: string;
  path?: string;
  status?: string;
  triage?: string;
  title?: string;
  task_id?: string;
  target_instance_id?: string | null;
}

interface Props {
  roster: ColleagueInstance[];
  activeInstanceId: string;
  sessions: ChatSession[];
  activeSessionId: string;
  openHandoffs: HandoffSummary[];
  onSelectColleague: (instanceId: string) => void;
  onHire: (roleKind: ChatAgentRole) => void;
  onRename: (instanceId: string, displayName: string) => void;
  onRemove: (instanceId: string) => void;
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
  onSwitchToProgrammer: (instanceId?: string) => void;
}

const HIRE_KINDS: ChatAgentRole[] = ["brief", "product_host", "programmer"];
const COLLAPSED_KEY = "gamefactory.colleagueSidebarCollapsed";

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

function writeCollapsed(value: boolean) {
  try {
    localStorage.setItem(COLLAPSED_KEY, value ? "1" : "0");
  } catch {
    /* ignore */
  }
}

function initials(name: string): string {
  const t = name.trim();
  if (!t) return "?";
  const parts = t.split(/[\s·・]+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return t.slice(0, 2).toUpperCase();
}

export function ColleagueRoster({
  roster,
  activeInstanceId,
  sessions,
  activeSessionId,
  openHandoffs,
  onSelectColleague,
  onHire,
  onRename,
  onRemove,
  onNewChat,
  onSelectSession,
  onSwitchToProgrammer,
}: Props) {
  const active = roster.find((c) => c.id === activeInstanceId);
  const sameKindCount = active
    ? roster.filter((c) => c.roleKind === active.roleKind).length
    : 0;
  const handoffsFor = (instanceId: string) =>
    openHandoffs.filter((h) => {
      const tid = h.target_instance_id;
      return !tid || tid === instanceId;
    });
  const openCount =
    active?.roleKind === "programmer"
      ? handoffsFor(active.id).length
      : openHandoffs.length;
  const isProgrammer = active?.roleKind === "programmer";
  const bannerHandoffs =
    active?.roleKind === "programmer" ? handoffsFor(active.id) : openHandoffs;

  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [renaming, setRenaming] = useState(false);
  const [renameDraft, setRenameDraft] = useState("");
  const [confirmRemove, setConfirmRemove] = useState(false);
  const renameInputRef = useRef<HTMLInputElement>(null);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      writeCollapsed(next);
      if (next) {
        setRenaming(false);
        setConfirmRemove(false);
      }
      return next;
    });
  };

  useEffect(() => {
    setRenaming(false);
    setConfirmRemove(false);
  }, [activeInstanceId]);

  useEffect(() => {
    if (renaming) {
      renameInputRef.current?.focus();
      renameInputRef.current?.select();
    }
  }, [renaming]);

  const startRename = () => {
    if (!active) return;
    setConfirmRemove(false);
    setRenameDraft(active.displayName);
    setRenaming(true);
  };

  const commitRename = () => {
    if (!active) return;
    const next = renameDraft.trim();
    setRenaming(false);
    if (next && next !== active.displayName) {
      onRename(active.id, next);
    }
  };

  const cancelRename = () => {
    setRenaming(false);
    setRenameDraft(active?.displayName || "");
  };

  return (
    <aside
      className={`colleague-sidebar ${collapsed ? "colleague-sidebar--collapsed" : ""}`}
      aria-label="同事列表"
    >
      <div className="colleague-sidebar__head">
        {!collapsed && <h2 className="colleague-sidebar__title">同事</h2>}
        <div className="colleague-sidebar__head-actions">
          {!collapsed && (
            <select
              className="colleague-hire"
              aria-label="雇佣工种"
              defaultValue=""
              onChange={(e) => {
                const v = e.target.value as ChatAgentRole | "";
                e.target.value = "";
                if (v) onHire(v);
              }}
            >
              <option value="" disabled>
                + 雇佣
              </option>
              {HIRE_KINDS.map((k) => (
                <option key={k} value={k}>
                  {CHAT_AGENT_LABELS[k]}
                </option>
              ))}
            </select>
          )}
          <button
            type="button"
            className="colleague-sidebar__toggle"
            title={collapsed ? "展开同事栏" : "收起同事栏"}
            aria-expanded={!collapsed}
            aria-label={collapsed ? "展开同事栏" : "收起同事栏"}
            onClick={toggleCollapsed}
          >
            {collapsed ? "»" : "«"}
          </button>
        </div>
      </div>

      <div className="colleague-people" role="list">
        {roster.map((c) => {
          const mine = handoffsFor(c.id).length;
          const showBadge = c.roleKind === "programmer" && mine > 0;
          const selected = c.id === activeInstanceId;
          return (
            <button
              key={c.id}
              type="button"
              role="listitem"
              className={`colleague-person colleague-person--${c.roleKind} ${
                selected ? "colleague-person--active" : ""
              }`}
              title={`${c.displayName} · ${CHAT_AGENT_LABELS[c.roleKind]}`}
              aria-current={selected ? "true" : undefined}
              onClick={() => onSelectColleague(c.id)}
            >
              <span className="colleague-person__avatar" aria-hidden>
                {initials(c.displayName)}
                {showBadge && collapsed && (
                  <span className="colleague-person__badge colleague-person__badge--dot">{mine}</span>
                )}
              </span>
              {!collapsed && (
                <span className="colleague-person__meta">
                  <span className="colleague-person__name">
                    {c.displayName}
                    {showBadge && <span className="colleague-person__badge">{mine}</span>}
                  </span>
                  <span className="colleague-person__role">{CHAT_AGENT_LABELS[c.roleKind]}</span>
                </span>
              )}
            </button>
          );
        })}
      </div>

      {!collapsed && (
        <div className="colleague-sidebar__foot">
          {renaming && active ? (
            <div className="colleague-rename">
              <input
                ref={renameInputRef}
                className="colleague-rename__input"
                value={renameDraft}
                aria-label="同事显示名"
                placeholder="显示名"
                onChange={(e) => setRenameDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    commitRename();
                  } else if (e.key === "Escape") {
                    e.preventDefault();
                    cancelRename();
                  }
                }}
                onBlur={() => commitRename()}
              />
              <div className="colleague-rename__actions">
                <button
                  type="button"
                  className="btn btn--sm"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={commitRename}
                >
                  保存
                </button>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={cancelRename}
                >
                  取消
                </button>
              </div>
            </div>
          ) : confirmRemove && active ? (
            <div className="colleague-remove-confirm">
              <p className="colleague-remove-confirm__text">
                解雇「{active.displayName}」？会话会从本机列表移除。
              </p>
              <div className="colleague-rename__actions">
                <button
                  type="button"
                  className="btn btn--sm colleague-remove-confirm__yes"
                  onClick={() => {
                    setConfirmRemove(false);
                    onRemove(active.id);
                  }}
                >
                  确认解雇
                </button>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => setConfirmRemove(false)}
                >
                  取消
                </button>
              </div>
            </div>
          ) : (
            <>
              {active && (
                <p className="colleague-sidebar__with">
                  正在与 <strong>{active.displayName}</strong> 对话
                </p>
              )}
              <div className="colleague-sidebar__tools">
                <select
                  className="chat-session-select"
                  aria-label="会话历史"
                  value={activeSessionId}
                  onChange={(e) => onSelectSession(e.target.value)}
                >
                  {sessions.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.title || "未命名"}
                    </option>
                  ))}
                </select>
                <button type="button" className="btn btn--ghost btn--sm" onClick={onNewChat}>
                  新对话
                </button>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  title="重命名当前同事"
                  onClick={startRename}
                >
                  改名
                </button>
                {sameKindCount > 1 && (
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    title="解雇当前同事（同工种至少保留一位）"
                    onClick={() => {
                      setRenaming(false);
                      setConfirmRemove(true);
                    }}
                  >
                    解雇
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {!collapsed && openCount > 0 && (
        <div className="handoff-banner" role="status">
          <div className="handoff-banner__text">
            <strong>{openCount}</strong> 个未读派工
            {bannerHandoffs[0]?.title ? ` · ${bannerHandoffs[0].title}` : ""}
          </div>
          {!isProgrammer && (
            <button
              type="button"
              className="btn btn--sm handoff-banner__btn"
              onClick={() =>
                onSwitchToProgrammer(bannerHandoffs[0]?.target_instance_id || undefined)
              }
            >
              找程序员
            </button>
          )}
        </div>
      )}
    </aside>
  );
}
