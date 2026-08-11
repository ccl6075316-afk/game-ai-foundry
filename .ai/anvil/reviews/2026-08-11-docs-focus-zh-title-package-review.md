# 评审报告：`2026-08-11-docs-focus-zh-title-package`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | **uncommitted**（Foundry + fishing 子仓） |
| Author | 本会话（人侧文档预览 UX + makeability 闸 + 中文 title） |
| Review Date | 2026-08-11 |
| Status | `APPROVED`（复审后；见 §5 已关闭项） |
| Spec | `docs/superpowers/specs/2026-08-11-human-docs-preview-shards-design.md`；`docs/superpowers/specs/2026-08-10-document-focus-and-stable-ids.md` |
| Prior | `.ai/anvil/reviews/2026-08-11-human-docs-preview-shards-review.md`（APPROVED）；`.ai/anvil/reviews/2026-08-11-makeability-brief-shards-followup-audit.md` |

**Loaded standards:** Anvil review skill；frontend 域规则 `TBD`（无额外透镜）。Learnings researcher：[af569698](af569698-955d-4e8e-b028-190222fe09c3)。

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | — | N/A | GUI 无统一 lint script |
| 类型检查 | `cd gui && npm run typecheck` | 仓库既有无关错误 | 本 diff 路径无新增报错 |
| 单元测试 | `npx tsx --test src/components/briefPreviewFormat.test.ts` | **18 PASS** | |
| 单元测试 | `cd cli && python -m unittest test_makeability_critic -q` | **14 PASS** | 含 catalog 盲审拒 / bind 可见 notes |
| GUI 手工 | Spec §验收 | 未跑 | 下拉中文依赖会话 draft 刷新 |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| human-docs-preview review | preview ≠ focus；mergeStatusFocus；inline 回退 | 仍成立；本包 UX 改下拉后仍保持 value=kind:id |
| makeability followup audit | catalog 无 root 拒审；GUI bind | `_hydrate_for_makeability` + App bind 前审 → PASS |
| stable-ids spec | id 机器 / title 人读 | skill + fishing title 中文化 → PASS |
| fishing migrate review | 平台 ≠ 工程数据 | 发现 draft 曾误厚化 → **已修回薄目录** |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | OK |
| 注入风险 | `shardRelPath` 仍 strip `..` | — | OK |
| XSS 风险 | 预览仍为文本 / `<pre>` | — | OK |
| 依赖 CVE | 未改依赖 | — | N/A |
| 日志敏感数据 | 无 | — | OK |

**安全结论：** CLEAN

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 作者回答（显式或推断） | 结论 | 严重级别 |
|------|------------|--------------------------|------|----------|
| Think Before Coding | title 中文靠 GUI 还是源头？ | GUI 只展示；skill + fishing 数据写中文；`catalogDisplayTitle` 不翻译 | PASS | — |
| Simplicity First | `hasCjkText`「优先中文」是否骗人？ | 初版分支无差异；复审已删 helper，改为 title→id | PASS | — |
| Surgical Changes | fishing `brief.draft` 是否只改 title？ | 曾整份变成厚 hydrate（High）；已还原 HEAD 薄目录 + 仅改 system title | PASS | — |
| Goal-Driven Execution | 盲审 / 中文展示是否有测？ | makeability 拒审测 + display title 单测；Docs 交互仍无组件测 | PASS | — |

**Karpathy Score:** 4/4

---

## 4. 对抗式维度评审

### 4.1 设计

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| skills | 中文 title 写 skill 是否够？ | 不挡导出；与 stable-ids 一致；生图不强制中文 | PASS | — |
| App focus 下拉 | value=`kind:id`、label=展示名 | 符合符号表 | PASS | — |

**维度结论：** PASS

### 4.2 功能

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `DocsPreviewPanel` focus effect | 不可映射 focus（如 VT global）后同 scene 再钉是否跟不上？ | `!next` 时未消费 key → 卡住 | **FINDING→FIXED** | Medium |
| fishing `brief.draft.json` | 是否误把分册 hydrate 进 draft？ | HEAD 薄 `path` → 工作区厚 notes；与 brief.json 分叉 | **FINDING→FIXED** | High |
| 会话旧 draft | GUI 未 rebind 仍可能显示英文 title | 需用户刷新/绑定；skill 防新写 | 接受（Low） | Low |

**已检查关键边界：**
- [x] 空 title → 回退 id
- [x] catalog 无 root → 拒审
- [x] focus value 仍英 id
- [ ] Docs 面板组件级自动化（仍缺）

**维度结论：** PASS（修复后）

### 4.3 复杂度

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `catalogDisplayTitle` | 是否过度抽象？ | 多处下拉/看板复用，合理 | PASS | — |

**维度结论：** PASS

### 4.4 命名

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `catalogDisplayTitle` | 名暗示「中文优先」？ | 已改为「有 title 用 title」；中文靠数据/skill | PASS | — |

**维度结论：** PASS

### 4.5 注释

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| DocsPreviewPanel | `!next` 消费 key 的 WHY 注释 | 已补 | PASS | — |

**维度结论：** PASS

### 4.6 风格与一致性

| 行号 | 问题 | 类型 | 状态 |
|------|------|------|------|
| 整包 | 人侧文档 UX + makeability + 中文 title + fishing 同树 | Nit：建议分 commit | 开放 |
| fishing `brief.zh.md` | 除 title 外 art_direction 再瘦 | Nit：与 content 同步可接受 | 开放 |

**维度结论：** PASS（Nit 不挡）

### 4.7 上下文

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| — | 系统是否更健康？ | 展示中文 + 盲审闸 + 薄 draft 恢复；skill 源头约定 | PASS | — |

**维度结论：** PASS

### 4.8 测试

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| — | Docs 下拉 / focus follow 有组件测吗？ | 仅 helper；交互靠手工 | Suggestion | Low |

**维度结论：** PASS

---

## 5. 发现项摘要

### Critical（阻塞提交）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| — | — | — | 无 | — |

### High（阻塞提交）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| H1 | 4.2 | fishing `brief.draft.json` | 工作区曾把 scenes/systems 从薄 `path` 目录写成内联 notes/summary（与 `brief.json` catalog 契约冲突）；疑似 hydrate 落盘混进「改 title」 | **CLOSED**：从 `HEAD:brief.draft.json` 恢复薄目录，仅更新 system 中文 `title` |

### Medium（强烈建议修复）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| M1 | 4.2 | `DocsPreviewPanel.tsx` focus effect | 不可映射 focus 时 `!next` 直接 return，未更新 `lastFollowedFocusRef`，同 scene 再钉可能不跟文档 | **CLOSED**：`!next` 时消费 key |
| M2 | 4.4 | `catalogDisplayTitle` / `hasCjkText` | 「优先中文」名不副实 | **CLOSED**：删 `hasCjkText`，helper 改为 title→id |

### Low / Nit（可选）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| L1 | 4.8 | Docs 面板 | 无组件测 | 后置 |
| L2 | 4.6 | 提交切分 | Foundry / fishing / skills 建议分 commit | 提交时执行 |
| L3 | 4.2 | 会话 draft | 已开会话可能仍持旧英文 title | 重绑/刷新 |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有自动化检查通过 | [x] |
| 安全扫描干净 | [x] |
| Karpathy score = 4/4 | [x] |
| 无未解决 Critical 问题 | [x] |
| 无未解决 High 问题 | [x] |
| 评审文档完整 | [x] |
| Spec 追溯（预览≠focus；id/title；makeability hydrate） | [x] |

### 结论

- [x] **APPROVE** — High/Medium 已在复审中关闭；允许提交（**本回合未自动 commit**：等你明确说再提）

### 评审备注

**本包范围（建议拆 commit）：**

1. **Foundry GUI/CLI**：文档下拉 + 焦点下拉、`catalogDisplayTitle`、makeability bind/拒审、`mergeStatusFocus` 等  
2. **Skills**：`host-chat` / `enrich` / `commit-brief` / `brief-brainstorm` 中文 title 约定  
3. **fishing**：`systems/*.json` + `brief.json` / `brief.draft.json` / `brief.zh.md` 系统中文 title  

**Resume：** 用户确认后分仓 commit；可选 `/anvil:compound`（中文 title 源头 + catalog 盲审闸可沉淀）。
