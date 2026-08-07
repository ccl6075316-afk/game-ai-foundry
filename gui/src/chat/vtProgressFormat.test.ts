import assert from "node:assert/strict";
import test from "node:test";
import {
  formatVtGlobalChoiceLabel,
  formatVtProgressBoard,
  formatVtSceneChoiceLabel,
  formatVtStickyHint,
  vtIsMarked,
  vtMarkBadge,
} from "./vtProgressFormat";

test("vtMarkBadge encodes selected candidate", () => {
  assert.equal(vtMarkBadge({}), "○");
  assert.equal(vtMarkBadge({ ready: true }), "✓");
  assert.equal(vtMarkBadge({ has_selected_image: true, selected_id: "b" }), "✓b");
  assert.equal(vtIsMarked({ has_selected_image: true }), true);
});

test("choice labels keep scene id in trailing paren for App regex", () => {
  const label = formatVtSceneChoiceLabel({
    id: "main_hub",
    title: "主界面",
    selected_id: "c",
    has_selected_image: true,
  });
  assert.equal(label, "生成北极星 · ✓c 主界面（main_hub）");
  assert.match(label, /^生成北极星(?:图)?\s*[·•]\s*.+?（([^）]+)）$/);
  assert.equal(formatVtGlobalChoiceLabel({ ready: true, selected_id: "a" }), "生成北极星 · ✓a 全局");
});

test("progress board and sticky hint summarize marks", () => {
  const scenes = [
    { id: "main_hub", title: "主界面", selected_id: "c", has_selected_image: true },
    { id: "shop", title: "商店" },
  ];
  const board = formatVtProgressBoard({ selected_id: "b", has_selected_image: true }, scenes);
  assert.match(board, /主界面/);
  assert.match(board, /✓c/);
  assert.match(board, /1\/2/);
  assert.equal(
    formatVtStickyHint({ selected_id: "b", has_selected_image: true }, scenes),
    "北极星 1/2 场景 · 全局✓b",
  );
});
