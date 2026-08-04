# 评审报告：`2026-08-04-media-path-and-brief-tools`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | uncommitted |
| Author | 本会话 |
| Review Date | 2026-08-04 |
| Status | `APPROVED`（建议拆 2 个 commit） |

**变更规模：** Medium · 两主题同树  
**Loaded standards：** Anvil lightweight + 权限/路径对抗审查

---

## 主题拆分

| 桶 | 内容 | 文件 |
|----|------|------|
| A | `~/projects/<repo>` 下媒体预览路径误切 | `toRepoMediaRel.ts` + test、`main.mjs`、`test-media-paths.mjs` |
| B | 策划 FOUNDRY_TOOL 加宽（制作审查 / 查本地 / 只读看板） | `pi_foundry_tools.py`、`pi_runtime.py`、`test_pi_foundry_tools.py`、`host-chat.md` |

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 |
|--------|------|------|
| CLI | `python -m unittest test_pi_foundry_tools -q` | PASS（11） |
| GUI | `npx tsx --test src/chat/toRepoMediaRel.test.ts` | PASS（4） |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| Brief → shell / pipeline run / setup install|upsert | 仍拒绝（有测） | — | OK |
| Brief → inspect / conversations | 可读仓库 + `~/.gamefactory`（密钥脱敏）；**可跨 role 读 it 会话** | Medium | 接受（本机查日志诉求） |
| makeability 无 `--i-confirm` | 耗 LLM，与 GUI「制作审查」按钮同权 | Medium | 接受 |
| 硬编码密钥 | 无 | — | OK |

**安全结论：** CLEAN（相对产品意图）；残余见 Medium。

---

## 3. Karpathy

| 原则 | 结论 |
|------|------|
| Think Before Coding | A：父目录 `projects/` 误匹配 — 根因正确；B：按钮有、Pi 白名单无 — 对症 |
| Simplicity First | 正则认 `projects/<slug>/(output\|…)` + lastIndexOf 兜底，可接受 |
| Surgical Changes | 两主题未搅进无关文件；提交时应拆 |
| Goal-Driven Execution | 路径测 + brief allow/deny 测到位 |

**Karpathy Score:** 4/4

---

## 4. 对抗式发现

### High / Critical
无。

### Medium（不阻塞）

| # | 桶 | 描述 | 建议 |
|---|----|------|------|
| M1 | B | 策划可 `conversations show --role it` 读其它工种会话 | 若要工种隔离，后续限制 `--role`；本轮按「查日志」接受 |
| M2 | B | `makeability` 无确认即可烧 LLM | 与 GUI 按钮一致；可后续加确认 |
| M3 | A | 正则主路径不直接匹配 `brief.draft.json` / `makeability.json`，靠 `lastIndexOf` | 对 `~/projects/…` 仍正确；可扩展后缀表 |

### Low / Nit

| # | 描述 |
|---|------|
| N1 | brief `max_tool_rounds` 3→10，单回合成本上升（为多步 inspect 值得） |
| N2 | 协议文案含 `fishing-2d` 示例路径 — 仅示例 |

---

## 5. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 自动化检查 | [x] |
| 安全相对意图 | [x] |
| 无未解决 Critical/High | [x] |
| 单 commit 整树 | 建议 **拆 A/B**，不强制 BLOCK |

### 结论

- [x] **APPROVE**
- 提交建议：  
  1. `fix: resolve media preview when clone lives under ~/projects`  
  2. `feat: widen brief FOUNDRY_TOOL for review and local read`

### 评审备注

按用户规则 **未自动 commit**。说「提交」或「按桶提交」再交。
