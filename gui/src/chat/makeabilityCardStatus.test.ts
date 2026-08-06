import assert from "node:assert/strict";
import test from "node:test";

import {
  makeabilityCardLocalSubmitPatch,
  resolveMakeabilityCardStatus,
} from "./makeabilityCardStatus";

test("repair_failed_ids force repair_failed even with verified_ids", () => {
  assert.equal(
    resolveMakeabilityCardStatus({
      ok: false,
      verified_ids: ["a"],
      repair_failed_ids: ["b"],
    }),
    "repair_failed",
  );
});

test("partial verify with remaining intent is repair_failed not applied", () => {
  assert.equal(
    resolveMakeabilityCardStatus({
      ok: true,
      verified_ids: ["a"],
      remaining_intent_count: 1,
    }),
    "repair_failed",
  );
});

test("all verified and ok is applied", () => {
  assert.equal(
    resolveMakeabilityCardStatus({
      ok: true,
      verified_ids: ["a"],
      remaining_intent_count: 0,
    }),
    "applied",
  );
});

test("verifier incomplete flags repair_failed via repair_failed boolean", () => {
  assert.equal(
    resolveMakeabilityCardStatus({
      ok: false,
      repair_failed: true,
      verified_ids: [],
      repair_failed_ids: ["a", "b"],
    }),
    "repair_failed",
  );
});

test("draft_persisted false forces repair_failed", () => {
  assert.equal(
    resolveMakeabilityCardStatus({
      ok: false,
      verified_ids: [],
      draft_persisted: false,
      draft_persist_error: "cas",
    }),
    "repair_failed",
  );
});

test("local submit patch saves answers for crash retry", () => {
  const answers = [{ gap_id: "g1", choice: "B" }];
  const patch = makeabilityCardLocalSubmitPatch(answers);
  assert.equal(patch.status, "repair_failed");
  assert.deepEqual(patch.lastAnswers, answers);
});
