# 评审报告：`2026-07-24-content-class-structured-craft`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 工作区未提交 → 本评审后提交 |
| Author | anvil-code / doers |
| Review Date | 2026-07-24 |
| Status | `APPROVED` |
| Spec Trace | `docs/anvil/brainstorms/2026-07-24-content-class-structured-craft.md` |
| Loaded standards | Anvil review；style-group compound（resolve≠wire） |

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | |
| 类型检查 | N/A（CLI Python） | N/A | |
| 单元测试 | `unittest` content_class / structured / stateful / skill_loader / pipeline_manifest / art_tokens / VT | PASS | 53 OK |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| identity resolve vs wire | stateful 后续态 depends_on + ref 同源 | PASS |
| art_tokens | assemble 强制合并 | PASS |
| visual-target assemble | 同模式 labeled 组装 | PASS |

---

## 1.5 Harness / Merge Gate

| 检查 | 结果 |
|------|------|
| Spec 可追溯 | PASS（view/class/states/assemble/skills/docs） |
| 非目标未越界 | PASS（无布局 JSON、无新 AssetType 枚举爆炸、无背景 vision） |
| Resume | PASS |

---

## 2. 安全扫描

CLEAN — 无密钥；prompt 组装为本地字符串。

---

## 3. Karpathy

| 原则 | 结论 |
|------|------|
| Think Before Coding | content_class⊥usage、view⊥camera；pipeline kind 少映射 | PASS |
| Simplicity First | 未扩 AssetType；stateful 仿 pose/style 接线 | PASS |
| Surgical Changes | 变更对齐 Spec 任务 | PASS |
| Goal-Driven | 契约/组装/展开/loader/文档均有测或 grep | PASS |

**Karpathy Score:** 4/4

---

## 4. 对抗式维度（摘要）

### 4.1–4.2 设计/功能 — PASS
- `assemble_asset_prompt` 强制 tokens/view/technical/negatives
- `expand_stateful_assets` + manifest follow-on 用 `prop_stateful` 过滤，避免与 icon_kit `__` 撞车
- 旧 brief 无字段兼容

### 4.3–4.7 — PASS
- skill 拆分清晰；asset-gen stub 可接受
- test_pipeline_manifest layer 断言改为 max(deps)+1（kit img2img 回归）合理

### 4.8 测试 — PASS
53 OK；含 stateful ref 与 assemble 强制注入

---

## 5. 发现项

### Critical / High
（无）

### Low / Nit
| # | 描述 | 动作 |
|---|------|------|
| L1 | DocsPreview 未展示 content_class/view | Spec 非必须；可选后续 |
| L2 | `isometric` 未进 PROJECT_VIEWS | Spec v1 三值；可后续扩展 |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 自动化通过 | [x] |
| 安全干净 | [x] |
| Karpathy 4/4 | [x] |
| 无未解决 Critical/High | [x] |
| Spec 可追溯 | [x] |

### 结论

- [x] **APPROVE** — 允许提交

### 评审备注

用户要求 review 并提交；单 commit 覆盖 T1–T5 + review 报告。
