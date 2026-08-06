import type { ChatSessionStore } from "./sessions";

export type SessionTarget = { instanceId: string; sessionId: string };

/**
 * Where to put a chat bubble when callers omit an explicit target.
 * Long tasks pin an origin in `originByBusy` via markBusy; if the user switches
 * colleagues mid-flight, a single pin still routes to the origin session.
 */
export function resolveAppendTarget(
  explicit: SessionTarget | undefined,
  store: ChatSessionStore,
  originByBusy: ReadonlyMap<string, SessionTarget>,
): SessionTarget | null {
  if (explicit) return explicit;
  if (originByBusy.size === 0) return null;
  const forActive = originByBusy.get(store.activeInstanceId);
  if (forActive) return forActive;
  if (originByBusy.size === 1) {
    return originByBusy.values().next().value ?? null;
  }
  return null;
}

export function sessionTargetForInstance(
  store: ChatSessionStore,
  instanceId: string,
): SessionTarget | null {
  const sid =
    store.activeByInstance[instanceId] ||
    store.sessions.find((s) => s.instanceId === instanceId)?.id;
  if (!sid) return null;
  return { instanceId, sessionId: sid };
}
