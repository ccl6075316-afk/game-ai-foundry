import assert from "node:assert/strict";
import test from "node:test";
import { makeabilityCardCopies } from "./makeabilityCopies";

test("makeabilityCardCopies does not repeat the summary on the intent bubble", () => {
  const head = "制作审查完成：1 条意图缺口，10 条施工细节缺口。";
  const copies = makeabilityCardCopies(head, true, true);
  assert.equal(copies.repairContent?.startsWith(head), true);
  assert.equal(copies.intentContent, "请在新卡片中点选选项并「写入草稿」。");
  assert.equal(copies.intentContent?.includes(head), false);
});
