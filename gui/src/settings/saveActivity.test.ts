import assert from "node:assert/strict";
import test from "node:test";

import { transitionSaveActivity } from "./saveActivity";

test("transitionSaveActivity keeps the gate closed until all saves finish", () => {
  assert.deepEqual(transitionSaveActivity(0, 1), { active: 1, savingChangedTo: true });
  assert.deepEqual(transitionSaveActivity(1, 1), { active: 2 });
  assert.deepEqual(transitionSaveActivity(2, -1), { active: 1 });
  assert.deepEqual(transitionSaveActivity(1, -1), { active: 0, savingChangedTo: false });
});
