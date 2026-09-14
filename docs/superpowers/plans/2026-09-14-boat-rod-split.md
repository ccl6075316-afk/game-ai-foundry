# 船/竿拆分 + 抛竿拉杆 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 战斗前景船与鱼竿分资产生成；船完整生图、运行时裁切入画；Space 抛竿、按住拉杆循环动画（只要竿、不要手）。

**Architecture:** brief 退役旧合成前景，新增船 texture + 鱼竿 character + cast/reel character_pose；pipeline 出图后 assemble 进 `game/assets`；`FishingBattleScreen` 叠船静图 + `AnimatedSprite2D` 切 idle/cast/reel。

**Tech Stack:** fishing-2d brief/specs、`gamefactory` pipeline、Godot 4 C#、现有 `SpriteFrames`（`*_frames.tres`）惯例。

**Spec:** `docs/superpowers/specs/2026-09-14-boat-rod-split-design.md`

## Global Constraints

- 竿动画无手、无人。
- 不改 `CombatSystem` 数值规则。
- 待抛/WaitingBite/松手/Result 共用鱼竿角色静帧。
- 旧 `fg_5a1f8c3e7b` 退役，战斗不再引用。
- 稳定 ID（`brief.suggest_asset_id` 规则）：`tex_f0ba589c6f`、`char_87df66e2f4`、`pose_822b8b47f8`（抛竿）、`pose_ac475d1d8e`（拉杆）。
- 勿主动 git commit，除非用户明确要求。

---

### Task 1: Brief + specs

**Files:**
- Create: `projects/fishing-2d/assets/tex_f0ba589c6f.spec.json`
- Create: `projects/fishing-2d/assets/char_87df66e2f4.spec.json`
- Create: `projects/fishing-2d/assets/pose_822b8b47f8.spec.json`
- Create: `projects/fishing-2d/assets/pose_ac475d1d8e.spec.json`
- Modify: `projects/fishing-2d/assets/fg_5a1f8c3e7b.spec.json`（notes 标明退役）
- Modify: `projects/fishing-2d/brief.json`（catalog：placeholder 旧项 + 登记 4 新项，`production_wave: 1`）

**Produces:** 可被 `pipeline plan` 解析的 4 个新资产 + 旧资产 `availability: placeholder`。

- [x] **Step 1: 写船 spec**
- [x] **Step 2: 写鱼竿角色 + 两 pose specs**
- [x] **Step 3: 退役旧合成前景**
- [x] **Step 4: 校验** (`brief validate` ok)
---

### Task 2: Pipeline plan + run（新资产）

**Files:**
- Modify: `projects/fishing-2d/pipeline/manifest.json`（或项目实际 manifest 名；以 `pipeline plan` 输出为准）
- Create under `projects/fishing-2d/output/`：船 raw/nobg、竿 raw/nobg、抛竿/拉杆 frames + nobg 序列

**Consumes:** Task 1 specs  
**Produces:** gameplay_ready 图与帧；assemble 后 `game/assets/foregrounds/`、`game/assets/sprites/`

- [x] **Step 1: plan merge**
- [x] **Step 2: 跑新任务**（默认模型 503 → 改用 `openai/gpt-image-2` + `1536x864`；船额外手跑 remove-bg）
- [x] **Step 3: assemble**（拷贝前景 + 安装 `*_frames.tres`）

### Task 3: Godot 叠层与动画切换

- [x] 常量/节点/裁切/抛竿拉杆切换（`FishingBattleScreen.cs` + `fishing_battle.tscn`）
- [ ] **手测**（需用户在 Godot 开战斗看裁切与 tip）

### Task 4: 验收对照 spec §7

- [ ] 用户手测勾选

---

## Spec coverage

| Spec | Task |
|------|------|
| 资产拆分 / 退役旧图 | 1 |
| 完整船 + 运行时裁切 | 2+3 |
| 抛竿 / 拉杆视频 | 2+3 |
| 无手 | 1 descriptions + 3 验收 |
| 不改 CombatSystem | 3 |
| 鱼线跟 tip | 3 |

## Execution

默认 **Inline**（本会话连续做完）；用户嫌问太多时不要再拆确认轮次。
