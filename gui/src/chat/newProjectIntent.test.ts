import assert from "node:assert/strict";
import test from "node:test";

import { parseNewProjectIntent } from "./newProjectIntent";

test("matches bare 新建 / 新项目", () => {
  assert.deepEqual(parseNewProjectIntent("新建"), {});
  assert.deepEqual(parseNewProjectIntent("新项目"), {});
  assert.deepEqual(parseNewProjectIntent("新游戏"), {});
});

test("captures seed after trigger", () => {
  assert.deepEqual(parseNewProjectIntent("新建项目，做一个塔防"), { seed: "做一个塔防" });
  assert.deepEqual(parseNewProjectIntent("换个游戏 竖屏跑酷"), { seed: "竖屏跑酷" });
});

test("extracts english slug hint", () => {
  assert.deepEqual(parseNewProjectIntent("新建项目 fishing-jam"), { slugHint: "fishing-jam" });
  assert.deepEqual(parseNewProjectIntent("新建项目 fishing-jam 海钓玩法"), {
    slugHint: "fishing-jam",
    seed: "海钓玩法",
  });
});

test("ignores /brief and unrelated lines", () => {
  assert.equal(parseNewProjectIntent("/brief reset"), null);
  assert.equal(parseNewProjectIntent("我想在关卡里新建一个敌人"), null);
  assert.equal(parseNewProjectIntent("继续完善 brief"), null);
});
