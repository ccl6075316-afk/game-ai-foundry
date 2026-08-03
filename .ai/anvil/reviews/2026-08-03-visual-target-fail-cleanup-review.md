# 评审报告：`2026-08-03-visual-target-fail-cleanup`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | uncommitted（`cli/visual_target.py` + `cli/test_visual_target.py`） |
| Author | agent（本会话） |
| Review Date | 2026-08-03 |
| Re-review | 2026-08-03 19:48（用户再次 review；确认 H1 修复仍在） |
| Status | `APPROVED` |
| Scope | 轻量：北极星 generate 失败残留清理；非整仓其它脏改动 |

**变更规模：** Small–Medium · Code · 聚焦 generate 生命周期  
**Loaded standards：** Anvil lightweight + review template（无独立 Spec；用户需求明确）

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | Python 模块无强制 lint |
| 类型检查 | N/A | N/A | |
| 单元测试 | `python -m unittest test_visual_target -q` | PASS | 30（复审再跑仍绿） |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| 本会话 fishing `main_hub` 空目录 | 失败半成品干扰重试 / GUI | 已覆盖：开始清盘 + 失败回滚 |
| pick → `selected.png` → brief ref | 清盘不得弄断已选北极星 | 评审发现 High → 已修 |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | OK |
| 路径删除范围 | 仅 `candidate_*.png` / `manifest.json` / `candidate_*.json`；不递归删子场景目录 | — | OK |
| 注入 / XSS / CVE / 日志密钥 | 无 | — | OK |

**安全结论：** CLEAN

---

## 3. Karpathy 对抗式原则

| 原则 | 结论 | 严重级别 |
|------|------|----------|
| Think Before Coding | 初版误删 `selected.png`；已纠正「generate 产物 vs pick 产物」边界 | PASS（修复后） |
| Simplicity First | clear / rmdir / rollback 三个小函数可接受，未过度抽象 | PASS |
| Surgical Changes | 只动 visual-target generate 生命周期 | PASS |
| Goal-Driven Execution | 有 stale 清理、失败回滚、保留 sibling、保留 selected 测例 | PASS |

**Karpathy Score:** 4/4（修复后）

---

## 4. 对抗式维度（摘要）

### 已关闭 — High

| # | 描述 | 证据 | 修复 |
|---|------|------|------|
| H1 | `clear_visual_target_run_artifacts` 删除 `selected.png`，已 pick 的 brief `visual_reference` 会在「再次生成失败/成功」后断链 | 初版 clear 循环含 `selected.png` | 清盘不再删 `selected.png`；新增 `test_failed_regenerate_keeps_previous_selected_png` |

### Medium（不阻塞）

| # | 描述 | 建议 |
|---|------|------|
| M1 | **先 clear 再生成**：重新生成若中途失败，会丢掉上一轮成功的 `candidate_*.png` + manifest（`selected.png` 仍在）。比旧「半新旧混合」干净，但「换风格失败还想看上回候选」会变差。 | 后续可改为 temp 目录生成成功再原子替换；本轮不挡 |

### Low / Nit

| # | 描述 |
|---|------|
| N1 | 失败后若仍有 `selected.png`，场景目录不会被 `rmdir`（有意保留）；空 hollow 仅出现在从未 pick 的失败路径，已由回滚覆盖 |
| N2 | `except Exception` 后 best-effort `OSError: pass` 合理 |

**各维结论：** PASS（无未解决 Critical/High）

---

## 5. 发现项摘要

- Critical：无  
- High：H1 已修  
- Medium：M1 残余  
- Low/Nit：N1–N2  

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有自动化检查通过 | [x] |
| 安全扫描干净 | [x] |
| Karpathy score = 4/4 | [x] |
| 无未解决 Critical | [x] |
| 无未解决 High | [x] |
| 评审文档完整 | [x] |

### 结论

- [ ] **BLOCK**
- [x] **APPROVE**

### 评审备注

按用户 commit 规则：**尚未提交**。说一声 commit 再交。

残余：M1（失败 regenerate 丢掉上一轮候选）可另开 temp→swap 任务。
