# 评审报告：`2026-07-22-style-img2img-stack`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | 工作区未提交：style_group + Phase1 enhance + Phase2 art_tokens |
| Author | anvil-code / doers |
| Review Date | 2026-07-22 |
| Status | `APPROVED` |
| Spec Trace | `docs/anvil/brainstorms/2026-07-22-style-group-img2img.md`；`…-style-ref-enhance.md` Phase1；`…-art-tokens.md` Phase2 |
| Loaded standards | Anvil review skill；无 domain backend 额外规则；历史 solutions 无同类条目 |

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | 无项目级 lint 门禁 |
| 类型检查 | N/A | N/A | 无 mypy 门禁 |
| 单元测试 | `python -m unittest test_style_group test_pipeline_manifest test_art_tokens test_image_strength test_brief_contract -q` | PASS | 54 OK（含 identity 接线回归） |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| docs/solutions（grep style_group/art_tokens/img2img） | 无历史条目 | N/A — 仅用当前 diff |

---

## 1.5 Harness / Merge Gate

| 检查 | 结果 |
|------|------|
| Spec → plan → diff 可追溯 | PASS（三份 brainstorm + art-tokens plan executed） |
| 验证证据匹配风险 | PASS（契约/manifest/strength 均有单测） |
| Resume / SoT | PASS（各 Spec/plan Code Status 已标） |
| 无平行状态源 | PASS |
| 非目标未越界 | PASS（无 Phase3 GUI、无 LoRA） |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | OK |
| 注入风险 | CLI 拼装 `--reference-image` 路径来自 brief/artifact；与既有 pose 路径同模式 | Low 既有模式 | OK |
| XSS | 无前端 | — | OK |
| 依赖 CVE | 无新依赖 | — | OK |
| 日志敏感数据 | `strength=` 打 stderr，非密钥 | — | OK |

**安全结论：** CLEAN

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 作者回答（显式或推断） | 结论 | 严重级别 |
|------|------------|--------------------------|------|----------|
| Think Before Coding | 假设？ | Gemini 常忽略 strength → prompt soft + best-effort API；identity 单槽优先 | PASS | — |
| Simplicity First | 能否删半？ | 解析/审计/manifest 接线为必要；无多余框架 | PASS | — |
| Surgical Changes | 每行有需求？ | 字段与 recipe/tokens 均对 Spec 目标 | PASS | — |
| Goal-Driven Execution | 测试证明行为？ | should_use / resolve / audit / strength / art_tokens / **manifest identity 接线** 均有断言 | PASS | — |

**Karpathy Score:** 4/4

---

## 4. 对抗式维度评审

### 4.1 设计

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| brief / pipeline | style 与 reference_asset 正交是否必要？ | Spec：pose/视频仍用 reference_asset；still 风格组另槽 | PASS | — |
| art_tokens | 为何并存 art_direction？ | 可选硬锁；旧 brief 兼容 | PASS | — |

**维度结论：** PASS

### 4.2 功能

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `pipeline_manifest.py` 初版 ~329–345 | identity 解析后是否仍用 style_anchor 产物？ | **初审发现 High**：是。已修：identity 优先 dep + `--reference-image`；回归 `test_follower_identity_anchor_wires_reference_and_dep` | 已修复 → PASS | was High |
| `gamefactory.apply_style_img2img_strength` | 任意 reference（含 pose）也注入 strength？ | Spec 写 style img2img；实现按 has_reference 通用 best-effort | 可接受；记 Nit | Low |

**已检查关键边界：**
- [x] 空 / 缺省 art_tokens、无 style_group
- [x] 非法类型 audit
- [x] identity 优先路径与 manifest 接线
- [ ] 竞态 — 修复后 identity 有 depends_on
- [x] icon_kit 排除 recipe
- [x] strength clamp / null opt-out

**维度结论：** PASS（修复后）

### 4.3 复杂度

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| normalize_art_tokens | 可否更短？ | 键类型分支与 Spec 对齐，可接受 | PASS | — |

**维度结论：** PASS

### 4.4 命名

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| should_use_style_img2img / resolve_style_img2img_path | 名是否撒谎？ | 与行为一致 | PASS | — |

**维度结论：** PASS

### 4.5 注释

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| — | 无掩盖复杂度的注释 | — | PASS | — |

**维度结论：** PASS

### 4.6 风格与一致性

| 行号 | 问题 | 类型 | 状态 |
|------|------|------|------|
| — | 与既有 brief/pipeline 风格一致 | — | OK |

**维度结论：** PASS

### 4.7 上下文

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| docs/skills | Phase2 文档是否过时？ | AI-HANDOFF / asset-gen 已标 shipped；generate.md 已改 | PASS | — |

**维度结论：** PASS

### 4.8 测试

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| test_style_group | 故意破坏 identity 接线会否失败？ | 新增 manifest 回归断言 hero_id_raw + dep | PASS | — |

**维度结论：** PASS

---

## 5. 发现项摘要

### Critical（阻塞提交）

（无）

### High（阻塞提交）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| H1 | 4.2 | `pipeline_manifest._static_asset_tasks` | identity 优先解析后仍接线 style_anchor | **已修**（doer `c79de3dd`）+ 回归测试 |

### Medium

（无）

### Low / Nit

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| L1 | 4.2 | `apply_style_img2img_strength` | pose 等非 style 参考也会注入 strength | 可选：仅 style 路径调用；本期不阻塞 |
| L2 | — | style 分支 | `style_path` 在 asset/identity 分支未直接使用 | 可留作 resolve 存在性校验；可选清理 |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有自动化检查通过 | [x] |
| 安全扫描干净 | [x] |
| Karpathy score = 4/4 | [x] |
| 无未解决 Critical 问题 | [x] |
| 无未解决 High 问题 | [x]（H1 已验证） |
| Spec 可追溯 | [x] |
| 评审文档完整 | [x] |

### 结论

- [x] **APPROVE** — 允许提交；建议随后 `/anvil:compound`（可选）

### 评审备注

用户确认「按 review → commit 顺序」；本批 **合并为一个 commit**（style_group + Phase1 + Phase2 + identity 修复）。未要求 MR/push。
