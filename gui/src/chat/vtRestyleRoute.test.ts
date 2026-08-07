import assert from "node:assert/strict";
import test from "node:test";
import {
  formatVtRestyleChoice,
  formatVtRegenAfterFeedbackChoice,
  parseVtRestyleChoice,
  parseVtRegenAfterFeedbackChoice,
  wrapVtRestyleUserMessage,
  isVtRestyleClarificationAsk,
} from "./vtRestyleRoute";

test("restyle choice encodes scene id; legacy 换风格 still parses", () => {
  const label = formatVtRestyleChoice("main_hub", "主界面");
  assert.equal(label, "都不满意，重做（场景：主界面｜main_hub）");
  assert.deepEqual(parseVtRestyleChoice(label), { hit: true, sceneId: "main_hub" });
  assert.equal(formatVtRestyleChoice(null), "都不满意，重做 · 全局");
  assert.deepEqual(parseVtRestyleChoice("都不满意，重做 · 全局"), {
    hit: true,
    sceneId: null,
  });
  assert.deepEqual(parseVtRestyleChoice("都不满意，换风格（场景：主界面｜main_hub）"), {
    hit: true,
    sceneId: "main_hub",
  });
  assert.deepEqual(
    parseVtRestyleChoice("都不满意，重做（场景：钓点选择（世界地图）｜spot_select）"),
    { hit: true, sceneId: "spot_select" },
  );
  assert.deepEqual(parseVtRestyleChoice("都不满意，换风格"), {
    hit: true,
    sceneId: undefined,
  });
});

test("regen-after-feedback choice parses scene id", () => {
  const label = formatVtRegenAfterFeedbackChoice("main_hub", "主界面");
  assert.equal(label, "我写好了 · 重新生成（场景：主界面｜main_hub）");
  assert.deepEqual(parseVtRegenAfterFeedbackChoice(label), {
    hit: true,
    sceneId: "main_hub",
  });
  assert.deepEqual(
    parseVtRegenAfterFeedbackChoice("我写好了 · 重新生成全局北极星"),
    { hit: true, sceneId: null },
  );
  // Explicit null must stay null (App must not fall back to focus.sceneId).
  const globalHit = parseVtRegenAfterFeedbackChoice("我写好了 · 重新生成全局北极星");
  assert.equal(globalHit.hit && globalHit.sceneId === null, true);
});

test("wrapVtRestyleUserMessage forbids speculative style changes", () => {
  const scene = wrapVtRestyleUserMessage(
    { active: true, sceneId: "aquarium_hall", sceneTitle: "水族馆大厅", kind: "restyle" },
    "太暗了，柜子要更清晰",
  );
  assert.match(scene, /仅场景 水族馆大厅（aquarium_hall）/);
  assert.match(scene, /不等于要换画风/);
  assert.match(scene, /禁止改 project\.art_direction/);
  assert.match(scene, /太暗了/);

  const global = wrapVtRestyleUserMessage(
    { active: true, sceneId: null, kind: "restyle" },
    "整体再卡通一点",
  );
  assert.match(global, /全局默认/);
  assert.match(global, /禁止擅自换风格/);

  const afterPick = wrapVtRestyleUserMessage(
    {
      active: true,
      sceneId: "tank_view",
      sceneTitle: "鱼缸",
      candidateId: "b",
      kind: "pick",
    },
    "再亮一点",
  );
  assert.match(afterPick, /刚选定北极星 · 场景 鱼缸（tank_view）/);
  assert.match(afterPick, /候选 b/);
  assert.match(afterPick, /再亮一点/);

  // After successful pick App clears focus — later turns must not stay wrapped.
  assert.equal(
    wrapVtRestyleUserMessage({ active: false, sceneId: null }, "继续聊玩法"),
    "继续聊玩法",
  );
});

test("isVtRestyleClarificationAsk prefers unlocking regen after absorption", () => {
  assert.equal(
    isVtRestyleClarificationAsk("已记下：你说哪里不对、柜子太暗。可以重新生成了。"),
    false,
  );
  assert.equal(
    isVtRestyleClarificationAsk("已记下你的反馈。还需要改别的吗？"),
    false,
  );
  assert.equal(isVtRestyleClarificationAsk("太暗了，我改 notes。还需要改别的吗？"), false);
  assert.equal(isVtRestyleClarificationAsk("太暗了，我改 notes。"), false);
  assert.equal(
    isVtRestyleClarificationAsk("我会在 notes 里记录柜子要更亮。哪里还需要调整？"),
    false,
  );
  assert.equal(
    isVtRestyleClarificationAsk("收到你的反馈。请再说清楚一点"),
    false,
  );
  assert.equal(isVtRestyleClarificationAsk("哪里不对？"), true);
  assert.equal(isVtRestyleClarificationAsk("能否再说具体一点"), true);
  assert.equal(isVtRestyleClarificationAsk("请具体说明想改成什么样"), true);
});
