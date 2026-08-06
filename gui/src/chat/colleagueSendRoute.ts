import type { ChatAgentRole } from "./roles";

/** Where a free-text send should go for the active colleague. */
export type ColleagueSendRoute = "agent" | "brief_turn" | "brief_start";

/**
 * Route user free-text by role.
 *
 * Only `brief` may hit host-chat brainstorm. Every other colleague is an agent
 * turn. Defaulting unknown roles to brief previously dropped `advisor` into
 * 策划 replies when `brainstormActive` was true.
 */
export function routeColleagueSend(
  role: ChatAgentRole,
  brainstormActive: boolean,
): ColleagueSendRoute {
  if (role === "brief") {
    return brainstormActive ? "brief_turn" : "brief_start";
  }
  return "agent";
}

export function isAgentChatRole(role: ChatAgentRole): boolean {
  return role !== "brief";
}
