import assert from "node:assert/strict";
import test from "node:test";

import { mapPiMessagesToChat } from "./piSessionSync";

test("mapPiMessagesToChat keeps user/assistant text", () => {
  const mapped = mapPiMessagesToChat([
    { role: "system", content: "ignore" },
    { role: "user", content: "hello" },
    {
      role: "assistant",
      content: [{ type: "text", text: "hi " }, { type: "text", text: "there" }],
    },
    { role: "tool", content: "skip" },
  ]);
  assert.equal(mapped.length, 2);
  assert.equal(mapped[0]?.role, "user");
  assert.equal(mapped[0]?.content, "hello");
  assert.equal(mapped[1]?.role, "assistant");
  assert.equal(mapped[1]?.content, "hi there");
});

test("mapPiMessagesToChat ignores empty content", () => {
  assert.deepEqual(mapPiMessagesToChat([{ role: "user", content: "  " }]), []);
});
