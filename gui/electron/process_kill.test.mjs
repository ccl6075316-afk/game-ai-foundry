import assert from "node:assert/strict";
import test from "node:test";
import { killChildTree, killPidTree } from "./process_kill.mjs";

test("killPidTree rejects invalid pids", () => {
  assert.equal(killPidTree(0), false);
  assert.equal(killPidTree(-1), false);
  assert.equal(killPidTree(undefined), false);
  assert.equal(killPidTree(null), false);
});

test("killChildTree no-ops on missing child", () => {
  assert.equal(killChildTree(null), false);
  assert.equal(killChildTree(undefined), false);
  // killed + no usable pid: skip tree kill, do not call child.kill again
  assert.equal(killChildTree({ killed: true }), false);
  assert.equal(killChildTree({ killed: true, pid: 0 }), false);
});
