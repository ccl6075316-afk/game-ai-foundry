/**
 * 会话存储 v2：按同事实例（instance）隔离。
 * 协作靠本地文件，不靠跨实例共享 messages — docs/HOST-CHAT-PRODUCT.md
 */

import type { ChatMessage } from "./types";
import { newMessageId } from "./types";
import { CHAT_AGENT_ROLES, type ChatAgentRole } from "./roles";
import {
  createColleague,
  createDefaultRoster,
  findColleague,
  nextHireName,
  type ColleagueInstance,
  type ExecutorKind,
} from "./roster";

const STORE_KEY = "gamefactory.activeChatSessions.v2";
const LEGACY_KEY = "gamefactory.activeChatSessions.v1";

export interface ChatSession {
  id: string;
  instanceId: string;
  role: ChatAgentRole;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

export interface ChatSessionStore {
  version: 2;
  roster: ColleagueInstance[];
  activeInstanceId: string;
  /** active session id per instance */
  activeByInstance: Record<string, string>;
  sessions: ChatSession[];
}

function newSessionId(): string {
  return `sess-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export function createEmptySession(
  instance: ColleagueInstance,
  title?: string,
): ChatSession {
  const now = Date.now();
  return {
    id: newSessionId(),
    instanceId: instance.id,
    role: instance.roleKind,
    title: title || `新对话 · ${instance.displayName}`,
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

export function createDefaultStore(): ChatSessionStore {
  const roster = createDefaultRoster();
  const sessions = roster.map((c) => createEmptySession(c));
  const activeByInstance: Record<string, string> = {};
  for (const s of sessions) {
    activeByInstance[s.instanceId] = s.id;
  }
  return {
    version: 2,
    roster,
    activeInstanceId: roster[0]!.id,
    activeByInstance,
    sessions,
  };
}

/** Migrate v1 (per-role) → v2 (per-instance). */
function migrateV1(raw: {
  activeRole?: ChatAgentRole;
  activeByRole?: Partial<Record<ChatAgentRole, string>>;
  sessions?: Array<{
    id: string;
    role: ChatAgentRole;
    title: string;
    messages: ChatMessage[];
    createdAt: number;
    updatedAt: number;
  }>;
}): ChatSessionStore {
  const roster = createDefaultRoster();
  const byKind = Object.fromEntries(roster.map((c) => [c.roleKind, c])) as Record<
    ChatAgentRole,
    ColleagueInstance
  >;
  const sessions: ChatSession[] = [];
  const activeByInstance: Record<string, string> = {};

  for (const role of CHAT_AGENT_ROLES) {
    const instance = byKind[role];
    const oldSessions = (raw.sessions || []).filter((s) => s.role === role);
    if (oldSessions.length === 0) {
      const s = createEmptySession(instance);
      sessions.push(s);
      activeByInstance[instance.id] = s.id;
      continue;
    }
    for (const old of oldSessions) {
      sessions.push({
        id: old.id,
        instanceId: instance.id,
        role: old.role,
        title: old.title,
        messages: old.messages || [],
        createdAt: old.createdAt,
        updatedAt: old.updatedAt,
      });
    }
    const preferred = raw.activeByRole?.[role];
    const pick =
      (preferred && sessions.find((s) => s.id === preferred && s.instanceId === instance.id)?.id) ||
      sessions.filter((s) => s.instanceId === instance.id).sort((a, b) => b.updatedAt - a.updatedAt)[0]
        ?.id;
    if (pick) activeByInstance[instance.id] = pick;
  }

  const activeRole = CHAT_AGENT_ROLES.includes(raw.activeRole as ChatAgentRole)
    ? (raw.activeRole as ChatAgentRole)
    : "brief";
  const activeInstanceId = byKind[activeRole].id;

  return {
    version: 2,
    roster,
    activeInstanceId,
    activeByInstance,
    sessions,
  };
}

function ensureStoreInvariants(store: ChatSessionStore): ChatSessionStore {
  let roster = Array.isArray(store.roster) ? [...store.roster] : createDefaultRoster();
  if (roster.length === 0) roster = createDefaultRoster();

  for (const role of CHAT_AGENT_ROLES) {
    if (!roster.some((c) => c.roleKind === role)) {
      roster.push(createColleague(role));
    }
  }

  let sessions = Array.isArray(store.sessions) ? [...store.sessions] : [];
  const activeByInstance: Record<string, string> = { ...(store.activeByInstance || {}) };

  for (const colleague of roster) {
    const has = sessions.some((s) => s.instanceId === colleague.id);
    if (!has) {
      const s = createEmptySession(colleague);
      sessions.push(s);
      activeByInstance[colleague.id] = s.id;
    } else if (
      !activeByInstance[colleague.id] ||
      !sessions.some((s) => s.id === activeByInstance[colleague.id] && s.instanceId === colleague.id)
    ) {
      const newest = sessions
        .filter((s) => s.instanceId === colleague.id)
        .sort((a, b) => b.updatedAt - a.updatedAt)[0];
      if (newest) activeByInstance[colleague.id] = newest.id;
    }
  }

  // Drop orphan sessions whose instance was removed
  const rosterIds = new Set(roster.map((c) => c.id));
  sessions = sessions.filter((s) => rosterIds.has(s.instanceId));

  let activeInstanceId = store.activeInstanceId;
  if (!rosterIds.has(activeInstanceId)) {
    activeInstanceId = roster[0]!.id;
  }

  return {
    version: 2,
    roster,
    activeInstanceId,
    activeByInstance,
    sessions,
  };
}

export function loadSessionStore(): ChatSessionStore {
  try {
    const rawV2 = localStorage.getItem(STORE_KEY);
    if (rawV2) {
      const parsed = JSON.parse(rawV2) as ChatSessionStore;
      if (parsed?.version === 2) return ensureStoreInvariants(parsed);
    }
    const rawV1 = localStorage.getItem(LEGACY_KEY);
    if (rawV1) {
      const legacy = JSON.parse(rawV1);
      if (legacy?.version === 1) {
        const migrated = ensureStoreInvariants(migrateV1(legacy));
        saveSessionStore(migrated);
        return migrated;
      }
    }
    return createDefaultStore();
  } catch {
    return createDefaultStore();
  }
}

export function saveSessionStore(store: ChatSessionStore): void {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(store));
  } catch {
    /* quota / private mode */
  }
}

export function getActiveColleague(store: ChatSessionStore): ColleagueInstance {
  return findColleague(store.roster, store.activeInstanceId) || store.roster[0]!;
}

export function getActiveSession(store: ChatSessionStore): ChatSession {
  const instanceId = store.activeInstanceId;
  const sid = store.activeByInstance[instanceId];
  const found = store.sessions.find((s) => s.id === sid && s.instanceId === instanceId);
  if (found) return found;
  const colleague = getActiveColleague(store);
  return createEmptySession(colleague);
}

export function listSessionsForInstance(store: ChatSessionStore, instanceId: string): ChatSession[] {
  return store.sessions
    .filter((s) => s.instanceId === instanceId)
    .sort((a, b) => b.updatedAt - a.updatedAt);
}

export function setActiveInstance(store: ChatSessionStore, instanceId: string): ChatSessionStore {
  if (!store.roster.some((c) => c.id === instanceId)) return store;
  return { ...store, activeInstanceId: instanceId };
}

export function setActiveSessionId(
  store: ChatSessionStore,
  instanceId: string,
  sessionId: string,
): ChatSessionStore {
  const ok = store.sessions.some((s) => s.id === sessionId && s.instanceId === instanceId);
  if (!ok) return store;
  return {
    ...store,
    activeInstanceId: instanceId,
    activeByInstance: { ...store.activeByInstance, [instanceId]: sessionId },
  };
}

export function startNewSession(store: ChatSessionStore, instanceId?: string): ChatSessionStore {
  const id = instanceId || store.activeInstanceId;
  const colleague = findColleague(store.roster, id);
  if (!colleague) return store;
  const session = createEmptySession(colleague);
  return {
    ...store,
    activeInstanceId: id,
    activeByInstance: { ...store.activeByInstance, [id]: session.id },
    sessions: [...store.sessions, session],
  };
}

export function hireColleague(
  store: ChatSessionStore,
  roleKind: ChatAgentRole,
  displayName?: string,
  executor: ExecutorKind = null,
): ChatSessionStore {
  const name = displayName?.trim() || nextHireName(store.roster, roleKind);
  const colleague = createColleague(roleKind, name, executor);
  const session = createEmptySession(colleague);
  return {
    ...store,
    roster: [...store.roster, colleague],
    activeInstanceId: colleague.id,
    activeByInstance: { ...store.activeByInstance, [colleague.id]: session.id },
    sessions: [...store.sessions, session],
  };
}

export function renameColleague(
  store: ChatSessionStore,
  instanceId: string,
  displayName: string,
): ChatSessionStore {
  const name = displayName.trim();
  if (!name) return store;
  return {
    ...store,
    roster: store.roster.map((c) => (c.id === instanceId ? { ...c, displayName: name } : c)),
  };
}

export function removeColleague(store: ChatSessionStore, instanceId: string): ChatSessionStore {
  const target = findColleague(store.roster, instanceId);
  if (!target) return store;
  const sameKind = store.roster.filter((c) => c.roleKind === target.roleKind);
  if (sameKind.length <= 1) return store; // keep at least one per kind

  const roster = store.roster.filter((c) => c.id !== instanceId);
  const sessions = store.sessions.filter((s) => s.instanceId !== instanceId);
  const activeByInstance = { ...store.activeByInstance };
  delete activeByInstance[instanceId];

  let activeInstanceId = store.activeInstanceId;
  if (activeInstanceId === instanceId) {
    activeInstanceId =
      roster.find((c) => c.roleKind === target.roleKind)?.id || roster[0]!.id;
  }

  return { version: 2, roster, sessions, activeByInstance, activeInstanceId };
}

export function updateActiveMessages(
  store: ChatSessionStore,
  updater: (messages: ChatMessage[]) => ChatMessage[],
): ChatSessionStore {
  const instanceId = store.activeInstanceId;
  const sid = store.activeByInstance[instanceId];
  const sessions = store.sessions.map((s) => {
    if (s.id !== sid || s.instanceId !== instanceId) return s;
    const messages = updater(s.messages);
    const titleFromUser = messages.find((m) => m.role === "user")?.content?.slice(0, 36);
    return {
      ...s,
      messages,
      updatedAt: Date.now(),
      title: titleFromUser ? titleFromUser.replace(/\s+/g, " ") : s.title,
    };
  });
  return { ...store, sessions };
}

export function appendMessage(
  store: ChatSessionStore,
  message: Omit<ChatMessage, "id" | "timestamp"> & Partial<Pick<ChatMessage, "id" | "timestamp">>,
): ChatSessionStore {
  const full: ChatMessage = {
    id: message.id || newMessageId(),
    timestamp: message.timestamp ?? Date.now(),
    role: message.role,
    content: message.content,
    attachments: message.attachments,
    choices: message.choices,
  };
  return updateActiveMessages(store, (msgs) => [...msgs, full]);
}
