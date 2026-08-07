import assert from "node:assert/strict";
import test from "node:test";
import {
  extractSceneIdFromChoice,
  formatVtPickChoice,
  parseVtPickChoice,
  sanitizeVtChoiceTitle,
} from "./vtChoiceParse";

test("sanitizeVtChoiceTitle strips nested fullwidth parens", () => {
  assert.equal(sanitizeVtChoiceTitle("钓点选择（世界地图）"), "钓点选择");
  assert.equal(sanitizeVtChoiceTitle("主界面"), "主界面");
});

test("extractSceneIdFromChoice prefers pipe id even with nested title parens", () => {
  assert.equal(
    extractSceneIdFromChoice("（场景：钓点选择（世界地图）｜spot_select）"),
    "spot_select",
  );
  assert.equal(extractSceneIdFromChoice(" · 主界面（main_hub）"), "main_hub");
});

test("parseVtPickChoice survives nested scene titles", () => {
  const nested =
    "选用北极星 a（场景：钓点选择（世界地图）｜spot_select）";
  assert.deepEqual(parseVtPickChoice(nested), {
    hit: true,
    candidateId: "a",
    sceneId: "spot_select",
  });
  assert.equal(
    formatVtPickChoice("a", "spot_select", "钓点选择（世界地图）"),
    "选用北极星 a（场景：钓点选择｜spot_select）",
  );
  assert.deepEqual(parseVtPickChoice("选用北极星 b"), {
    hit: true,
    candidateId: "b",
    sceneId: null,
  });
});
