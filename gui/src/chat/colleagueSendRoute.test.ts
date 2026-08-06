import assert from "node:assert/strict";
import test from "node:test";
import { isAgentChatRole, routeColleagueSend } from "./colleagueSendRoute";
import { CHAT_AGENT_ROLES } from "./roles";

test("advisor always routes to agent turn, never brief brainstorm", () => {
  assert.equal(routeColleagueSend("advisor", false), "agent");
  assert.equal(routeColleagueSend("advisor", true), "agent");
  assert.equal(isAgentChatRole("advisor"), true);
});

test("brief uses brainstormActive for turn vs start", () => {
  assert.equal(routeColleagueSend("brief", false), "brief_start");
  assert.equal(routeColleagueSend("brief", true), "brief_turn");
  assert.equal(isAgentChatRole("brief"), false);
});

test("all non-brief roles route to agent even when brainstormActive", () => {
  for (const role of CHAT_AGENT_ROLES) {
    if (role === "brief") continue;
    assert.equal(routeColleagueSend(role, true), "agent", role);
    assert.equal(isAgentChatRole(role), true, role);
  }
});
