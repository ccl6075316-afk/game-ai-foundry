# 回家交接：待办 + 能否发 0.0.7

> 给其他 AI / 明天的自己用。人话版。  
> **日期**：2026-07-25（续）  
> **当前 main**：本提交后含 layout→Godot + 示例 brief + DocsPreview class/view  
> **GUI 包版本仍是**：`gui/package.json` → **0.0.6**（还没升到 0.0.7）

---

## 1. 今天刚合上、已在 main 上的东西（相对 0.0.6）

这些都已进仓库，但**还没打成 0.0.7 安装包 / 还没写 RELEASE-NOTES-0.0.7**：

| 主题 | 提交（约） | 一句话 |
|------|------------|--------|
| 双图 Provider / 顶层 proxy / 资产审图 | `0340b8e` `008907d` | 设置更完整，侧栏可审图 |
| 看板 style chips、icon_kit 套内 img2img | `25ce8c5` | 看板能看见风格关系 |
| icon_kit 条目对象 + collectible | `13b8a9d` | 道具绑定更细 |
| GUI bulk_model | `5868092` 一带 | 批量图模型配置 |
| style_group / identity / art_tokens / DocsPreview | 更早 `dfcbf5e` `9c27486` | 风格组 + 硬锁 + 预览只读 |
| **content_class / project.view / 结构化 prompt / 分 skill / 多状态 img2img** | `04da6fb` | 出图文案按类型组装 |
| **production.layout 区域+摆放（规则生成）** | `653dc44` | 积木放哪的施工说明 |
| **layout→Godot + 示例 class/view + DocsPreview** | （本提交） | scaffold/assemble 写 World props；示例有 placements |

**重要**：很多能力主要在 **CLI + skill**；纯 GUI 用户未必「点得到」layout / content_class（靠策划 LLM 填 brief + derive）。

---

## 2. 待做事项（给其他 AI 接着做）

按优先级，**不是全都要进 0.0.7**。

### P0 — 发版前建议做完（否则 0.0.7 名不正）

1. **升版本号**  
   - `gui/package.json` `0.0.6` → `0.0.7`  
   - 按 `docs/RELEASE.md` 打包 Win（及你需要的 mac）  
   - 新建 `docs/RELEASE-NOTES-0.0.7.md`（从 UNRELEASED + 上表整理）  
   - 清空/改写 `docs/RELEASE-NOTES-UNRELEASED.md`

2. **冒烟清单（人测或 AI 按步骤）**  
   - 新工程：策划 → 导出 brief（带 view/content_class 若 LLM 会填）→ 北极星 → pipeline plan/run  
   - `production derive` 打开 JSON，确认有 `layout.regions`（有 prop class 时还有 placements）  
   - 资产审图面板能开  
   - Provider / proxy / bulk_model 设置保存再打开还在  
   - DocsPreview：有 style_group / art_tokens / **view / content_class** 的 brief 能看见标注  

3. **回归**：`cd cli && python -m unittest test_content_class test_prompt_craft_structured test_stateful_expand test_skill_loader_content_class test_production_layout test_godot_layout test_godot_scaffold test_pipeline_manifest -q`（本地已绿过，发版机再跑一遍）

### P1 — 产品缺口

4. ~~**layout 真正进 Godot**~~ ✅  
   - `godot scaffold` / `godot assemble` 按 `layout.placements` 写 `World` 下 Sprite2D  
   - `godot_tasks.layout_props` 校验/绑纹理；只消费 layout 数据，不二次 genre 猜摆  

5. ~~**brief 示例补 content_class + view**~~ ✅  
   - `resources/asset-brief.example.json`：`view: side` + `wooden_crate`/`mossy_rock` + sparse 背景  

6. ~~**DocsPreview 显示 content_class / view**~~ ✅  
   - `briefPreviewFormat` + chips  

7. **端到端「一局模拟游戏」验收**（仍开）  
   - 从聊天到可玩：稀疏背景 + 积木 + layout → 场景里真看见摆好的道具（需真实出图/assemble）

### P2 — 已明确延后（不要默认塞进 0.0.7）

8. 用 vision **看生成背景**再摆积木（已否决作默认）  
9. LLM **精修** layout 坐标  
10. LoRA / 本地 SD 等新图像后端  
11. GUI **可编辑** style / content_class 写回 brief  
12. Windows 路径 / Hermes venv 加固（若还没做完）  
13. `project.view` 增加 `isometric` 等枚举  

### P3 — 体验与债

14. compound 知识库再沉一条「layout 启发式」  
15. prompt craft 线上抽检：结构化组装后 Gemini 出图质量对比  
16. 打包体积 / 签名 / mac 包（0.0.6 已知限制仍在）

---

## 3. 能不能发 0.0.7？评估结论

### 可以发「功能增量预览版」——条件是

- 接受定位：**CLI/管线/技能明显变强**，不是「从零用户零学习就能拼出模拟场景」  
- 完成上面 **P0**（版本号 + 发布说明 + 冒烟）  
- 发布说明里写清：layout **会**进 scaffold/assemble 的 World 节点；坐标仍可手写覆盖；`content_class` 靠 brief LLM/示例填

### 叙事上仍缺

| 缺口 | 为什么 |
|------|--------|
| 未做 **一整局** 真实出图+assemble 验收 | 风险在集成/纹理路径，单测已覆盖放置 |
| GUI 仍不可编辑 class/view | 只读预览已有；写回是 P2 |

### 建议话术

- **可以发 0.0.7**：强调「类型化出图 + 审图 + layout 契约 + scaffold/assemble 自动摆 prop」  
- **里程碑 0.0.8**：一整局模拟验收 +（可选）GUI 可编辑 class  

---

## 4. 给其他 AI 的开工提示

```text
仓库：game-ai-foundry，branch main @ 653dc44（或更新）
人话沟通；提交前要用户明确说才 commit/push。
发 0.0.7：先读 docs/RELEASE.md 与 docs/RELEASE-NOTES-0.0.6.md，写 0.0.7 notes，升 gui/package.json。
待办权威列表：本文档 docs/HANDOFF-TODO-0.0.7.md
下一产品刀优先：端到端一整局验收（P1-7），或发 0.0.7；不要先做背景 vision。
Spec 事实源：
- docs/anvil/brainstorms/2026-07-24-content-class-structured-craft.md
- docs/anvil/brainstorms/2026-07-24-production-logical-layout.md
```

---

## 5. 一句话

**技术上够格打一个 0.0.7（预览）**，但先做版本号/说明/冒烟；**场景积木「看见摆好」还没闭环**，那是下一版主菜，别在 0.0.7 里吹满。
