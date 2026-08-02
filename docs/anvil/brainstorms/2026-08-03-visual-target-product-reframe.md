# 产品讨论：北极星应从「全局一张」改为「按场景效果靶」

## 执行元数据

- **Status**：draft（讨论定稿，**未**确认改产品/代码）
- **Workflow Stage**：brainstorm
- **Created**：2026-08-03
- **Updated**：2026-08-03
- **Source Of Truth Until**：用户用下一 AI 处理并确认后的 Spec/Plan；在此之前本文是产品意图备忘，不是实现契约
- **Confirmed By**：用户口述立场（2026-08-03）；书面 Spec 待下一轮
- **Requirements Source**：多场景北极星落地后的 Bugbot 连环问题复盘 + 产品方向讨论
- **Background Inputs**：
  - 已落地：多场景 `scenes[].visual_reference`、resolve/pick/assign、GUI soft-gate（代码在未提交/待 commit 的 visual-target 多场景改动中）
  - 前序：[`2026-07-31-brief-scenes-systems.md`](2026-07-31-brief-scenes-systems.md)（内容分层，未定义每场景视觉靶）
  - Godogen：[`PROJECT.md` Visual Target](https://github.com/htdt/godogen/blob/master/PROJECT.md)（一张 `reference.png` 锚定全项目）
  - Foundry 风格组：默认软对齐；硬参考需显式 `style_anchor_kind: visual_reference`；组内家族 img2img
- **Compounded Knowledge**：not yet
- **Resume Point（给下一 AI）**：读本文 → 与用户确认是否立项 Spec → 再写 plan；**不要**在未确认前大改 soft-gate / 文案 / 默认全局生成

---

## 一句话结论

**「全局北极星」在 Foundry 产品假设下是伪概念（或最多是可选封面），不是项目视觉真理。**  
效果靶应按**场景（或玩法核）**出；真正管风格统一的是 **`art_direction` / tokens + 资产家族 img2img**，不是整屏北极星默认进图生图。

---

## 产品分叉：Godogen vs Foundry

| | Godogen 系 | Foundry 应走的路（用户立场） |
|--|--|--|
| 目标 | 一句话 / 很少输入 → 能跑的 demo | 打磨过的玩法文档 + 视图基准 → 再施工 |
| 用户 | 要快原型 | 有作者意图、愿意迭代 brief 与资产 |
| 成功标准 | 短时内「像个游戏」 | 别人愿意玩、作者认得出自己的东西 |
| 北极星 | 一张图 = 全项目身份锚 | 按场景的「效果靶」；可多张；全局非必须 |
| 配置复杂度 | 可接受（管线本身也重） | 前期略复杂可接受——门票是打磨，不是一句话 |

用户判断：以当前 AI 水平，「一句话生成可给别人玩的游戏」不现实（除非 Flappy Bird 级玩具）。  
开发（脚手架/接线）相对 **玩法 + 视图** 更可替换；重活在前期产品文档与资产。

---

## 为什么「全局一张」站不住

1. **多玩法糅合**：例如模拟经营 + 钓鱼。主题、镜头、信息密度不同，硬合成一张要么假要么糊。
2. **多场景**：brief 已有 `scenes[]`；一屏代表不了多屏。
3. **职责错位**：整屏靶既当「作者脑内画面」、又当 soft-gate 通行证、又偶发当 style img2img——三份工叠在一个字段上，正是多场景改造连环 bug 的概念根因。
4. **行业习惯**：商业/独立制作更常见 mood board、分场景 keyframe、style guide、hero→家族；**不是**「永远一张全局 reference.png」。Godogen 的单图是 **AI demo 管线启动仪式**，不是 3A/中型项目通识。

上次 `scenes[]`/`systems[]` 分割：内容架构合理，但**没定义视觉契约**——这是欠账，不是上次失败；全局单图问题主要来自视觉管线仍按 Godogen 单核假设建模。

---

## 用户主张的目标模型（未实现）

Brief 定稿后告知用户：

> 你想为哪几个**场景**出北极星（效果靶）？

然后：

```text
场景效果靶（per-scene visual target）
  = 「这一屏大概长这样」——给作者看的基准
  ≠ 默认 style img2img 参考图

风格统一
  = art_direction / art_tokens（跨场景语言）
  + 资产家族（先出几张满意的 → 后面照着生）

全局图（可选）
  = 封面 / 主卖点一屏 / 营销 key art
  ≠ 强制；≠ 项目视觉真理
```

接受的代价：多场景靶可能导致风格略散——应用文字风格锁 + 后续选中的资产家族收敛，而不是假装一张全局图能收。

北极星的产品语义应是：

- **是**：作者脑内画面的外化、场景最终效果的预览靶。
- **不是**：最终像素契约；不是默认图生图锚；不保证资产 1:1 复刻该图。

---

## 与当前代码的关系（给下一 AI）

已做（实现层，多场景能力）：

- `project.scenes[].visual_reference` + 全局 fallback
- generate/pick/list/assign 支持 `--scene`；输出 `visual-target/<scene_dir>/`
- soft-gate：全局 **或** 任一场景 ref 即可
- pick 的 intentional `scene_ids` 与 `auto_matched_scene_ids` 分离；全局 generate 不被 auto_match 污染为场景 scope
- style img2img：绑定 `scene_ids` 的资产优先匹配场景 ref

**尚未按本文改产品语义**（明确非目标，除非用户确认 Spec）：

- 文案仍可能说「项目北极星」
- 仍可能默认引导生成全局一张
- Tester / skills / 文档仍大量全局-only
- 未把流程改成「Brief 后强制点名场景再出靶」

建议下一 AI 的改动方向（需用户确认后写 Spec）：

1. 话术：`选用项目北极星` → `为场景选效果靶`
2. Soft-gate：至少一个场景靶 **或** 明确跳过；全局非必须
3. 默认生成路径：引导选 scene chips，而不是先全局
4. 保持：北极星默认**不**进 still `--reference-image`；家族锚继续走 `style_group` / identity
5. 可选保留：`project.visual_reference` 仅作封面/主卖点

---

## 讨论中达成的共识 vs 仍开放

### 共识（用户 + 助手）

- Godogen 赌 demo 速度；Foundry 应赌前期玩法/视图密度。
- 全局单图不该当默认真理。
- 效果靶按场景；风格靠后续资产家族。
- 「必须打磨 brief」与「没有一句话生成」一致。

### 仍开放（写 Spec 前要问用户）

- 全局封面字段是否保留、叫什么、是否进 soft-gate
- auto_match 空场景是否保留（便利 vs 误匹配）
- 无 `scenes[]` 的老 brief：是否仍允许一张全局靶作为兼容
- Tester / VQA 对齐哪张靶（每场景？主场景？）

---

## 给下一 AI 的工作方式建议

1. **先读本文 + 当前 `cli/visual_target.py` / GUI 北极星相关文案**，不要从 Godogen「一张 reference.png」重新发明。
2. 与用户确认：本文是否升格为 confirmed Spec；若是，再写 `docs/anvil/plans/…`。
3. 改动优先产品语义与引导流；避免再在 `scene_id` / `scene_ids` / auto_match 上混 scope（不变量：`pick_targets` ≠ `auto_matched` ≠ `generate_scope`）。
4. fishing-2d 工程是多玩法反例载体（经营+钓鱼），产品决策应用它做思想实验，但改 Foundry 代码与改 fishing brief 分开提交。
