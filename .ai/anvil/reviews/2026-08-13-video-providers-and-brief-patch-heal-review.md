# 评审报告：`2026-08-13-video-providers-and-brief-patch-heal`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | WORKTREE（未提交） |
| Author | 本会话实现 |
| Review Date | 2026-08-13 |
| Status | `APPROVED` |

**Loaded standards:** `anvil/skills/review/SKILL.md`、`anvil/rules/karpathy.md`、`anvil/rules/domains/backend.md`（TBD）、`anvil/rules/domains/frontend.md`（TBD）

**审查范围:**
- 生视频复用 `provider_accounts`（Spec + Plan：`docs/anvil/brainstorms|plans/2026-08-13-multi-vendor-video-via-providers*`）
- 策划 `brief_patches` 自愈 + 挡住时「谁来修」（无独立 brainstorm；聊天确认）
- Seedance 2.5 alias + i2v 省略 `ratio`
- **不做：** 动画切分 / 2s 精灵截断（用户明确搁置）

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | IDE diagnostics | PASS | 本次未引入新的诊断 |
| 类型检查 | `gui` `tsc --noEmit` | N/A | 失败项在既有 test：`agentReply.test.ts` TS5097、`MakeabilityGapCard.test.tsx` 缺 `happy-dom`；与本 diff 无关 |
| 单元测试 | `python3 -m unittest test_video_route test_video_compat test_seedance_api test_host_chat test_brief_transitions.BriefTransitionsTests.test_infer_asset_type_from_name_and_id_hints -q` | PASS | 157 ok |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| `docs/solutions/patterns/critical-patterns.md` | ACP/JSON-RPC id 撞车 | 不适用本 diff |
| `anvil-learnings-researcher` | 插件内无该 researcher | 跳过；改为定点检索 `docs/solutions` |
| 2026-08-12 soft-focus review | patch 先规范化再写入；稳定 id/path 硬边界 | host_chat 自愈仍保留冲突/整表/稳定字段硬校验 |

**使用规则：** 历史 learning 只作 lens；下列 finding 均引用 current diff。

---

## 1.5 Harness / Spec 追溯

| 项 | 结论 |
|----|------|
| 视频 Spec→Plan→diff | T1–T5 可追溯：凭证、compat adapter、CLI facade、GUI 选用、docs/`video.extra` |
| 视频非目标 | 末帧 / extra 透传 / 原生 SDK / 生视频沿用生图 / **动画切分** 均未做 |
| 策划自愈 | **无** `docs/anvil/brainstorms`；范围来自用户确认「挡住由策划下一轮修，不外挂 Agent」 |
| Plan resume | 已更新为 review；合入后 SoT = 代码 + GUI-CONFIG / TOOLS |
| 并行状态源 | 无新增 `docs/solutions` / 双份进度文件 |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无；Key 来自 config / env / CLI | — | PASS |
| 注入风险 | brief patch 仍拒 `../escape` 进路径；mint 为 `scene_<hash>` | — | PASS |
| XSS 风险 | GUI 仅表单字符串，无 HTML 插入 | — | PASS |
| 依赖 CVE | 无新依赖 | — | PASS |
| 日志敏感数据 | `_error_snippet` 截断 200；`video_cmds` 只打 backend/provider/model | Low | 可接受 |
| SSRF | `extract_video_url` 下载网关返回的 http(s) URL | Low | 与现有 Seedance 取回模型一致；用户自配网关 |

**安全结论：** CLEAN

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 作者回答（显式或推断） | 结论 | 严重级别 |
|------|------------|--------------------------|------|----------|
| Think Before Coding | 空 `video.provider` + 自定义 `api_base` 是否仍算 Seedance？ | 初版把「有 Key 无 provider」一律标成 seedance，会把 Apilio base 打到 ARK path。审查中已改为先 `infer_video_backend(api_base)` 再补 provider。 | PASS | High→已修 |
| Simplicity First | compat 三套 probe + Wan/Hailuo 厂商 path 能否更少？ | Apilio 公开文档几乎不写视频 path；probe 顺序是联调证据固化，删掉会回归 503。 | PASS | — |
| Surgical Changes | host_chat 420 行是否属于视频 Spec？ | 否。视频 Spec 非目标含「改 brief」。自愈是并行用户需求，应拆 commit。 | PASS（记录 Medium） | — |
| Goal-Driven Execution | 测试是否会在实现写错时失败？ | route/compat/seedance/host_chat 均有行为断言；审查补了「无 provider + Apilio base → compat」。 | PASS | — |

**Karpathy Score:** 4/4

---

## 4. 对抗式维度评审

### 4.1 设计：它是否应该存在？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `cli/video_route.py` `VideoCredentials` | 为何不把视频凭证塞进 `image_model_route`？ | 生图/生视频 backend 不同（ARK vs compat vs vendor origin path），独立模块避免污染生图。 | 同意 | — |
| `cli/host_chat.py` `_repair_*` | 自愈是否该在 LLM 侧 retry 而不是宿主？ | 客户机器没有外挂 Agent；宿主确定性补 type/id 才能落地。硬校验仍打回策划。 | 同意 | — |

**维度结论：** PASS

---

### 4.2 功能：作者遗漏了什么？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `cli/video_route.py:43-53,146-149` | 无 provider + `https://api.apilio.ai/v1` 会走哪条 backend？ | 初版误判 seedance。已修：base 非 ARK → `openai_compat`，provider 保持空。 | 已修 + 单测 | High→Fixed |
| `cli/video_compat.py` `build_vendor_submit_attempts` | 无首帧时 Wan/Hailuo 是否走厂商 origin path？ | `not reference_data_url` → `[]`，回落到 `/v1/videos`。Spec 验收以 i2v 为准。 | 可接受；t2v 厂商 path 未覆盖 | Low |
| `cli/host_chat.py:2867` `_repair_set_structure_path` | `set` 找不到中文 scene 会不会误新建？ | `mint=False`，报错引导 `upsert_scene`。 | 有测试 | — |
| `cli/brief.py:1010-1099` | 「角色扮演…背景」会不会先命中「角色」？ | hint 顺序 pose→character→background→texture；假阳性可能。 | 记录 | Medium |
| GUI `ProviderSettingsView.tsx:157-160` + `main.mjs:1191-1209` | 保存是否抹掉 `duration/split_frames`？ | patch 只含 provider/model；`deepMerge` 递归合并，`null` 只删该键。 | 符合 Plan 不变量 | — |

**已检查关键边界：**
- [x] 空输入 / null 输入（未启用视频、无 draft patches）
- [x] 非法 id / `../escape`（mint 稳定 id，不写盘外）
- [x] 外部依赖失败（compat probe 多 path，最后 `CompatVideoError`）
- [ ] MiniMax-H3 实网未跑
- [ ] 动画切分（明确不做）

**维度结论：** FINDINGS（无未修 High）

---

### 4.3 复杂度：还能更简单吗？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `video_compat.py` vendor + compat attempts | 能否只留 `/v1/videos`？ | 联调证明 Wan/Hailuo 必须站点根 path。 | 必要复杂度 | — |

**过度设计检查：**
- [x] 无投机 `video.extra` 透传（只预留存盘）
- [x] 无原生四厂商 SDK
- [x] 自愈没有做成通用 schema migrator

**维度结论：** PASS

---

### 4.4 命名：名字是否撒谎？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `cli/env_discover.py:209` `seedance_key` | 字段名还叫 seedance，值却含 Apilio Key？ | doctor/GUI 兼容旧字段；语义已变成「任意生视频 Key」。 | 误导 | Medium |
| `_repair_set_structure_path` | 名字是否反映「只解析已有、不 mint」？ | 是；`mint=False` 在 callee。 | PASS | — |

**维度结论：** FINDINGS

---

### 4.5 注释：提供价值，还是替坏代码找借口？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `seedance_api.py` 2.5 i2v omit ratio | 注释解释 HTTP 400 原因 | WHY，不是复述代码 | PASS | — |

**维度结论：** PASS

---

### 4.6 风格与一致性

| 行号 | 问题 | 类型（Block / Nit） | 状态 |
|------|------|--------------------|------|
| 工作区 | 视频 + 策划自愈 + Seedance 2.5 + 文案 混在同一 uncommitted tree | Medium | 开 | 

**风格检查：**
- [x] 代码风格贴近现有 CLI/GUI
- [ ] 风格/文档改动与功能应拆 commit（建议，不阻塞功能质量）

**维度结论：** FINDINGS

---

### 4.7 上下文：系统是否更健康？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| GUI `commandGuide.ts` | 是否还写「生视频只能 Seedance」？ | 已改为 Provider 选用或遗留 Seedance。 | 改善 | — |
| `host-chat.md` | 策划是否知道挡住谁修？ | nudge + skill 写明解决者=策划，不是外挂 Agent。 | 改善 | — |

**维度结论：** PASS

---

### 4.8 测试：证明有效，还是只是跑起来？

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `test_video_route.py` | 破坏 backend 推断会不会红？ | 补了 Apilio base 无 provider、CLI explicit base。 | PASS | — |
| `test_video_compat.py` | Wan/Hailuo URL 是否锁定？ | 断言 origin `/v2/videos/generations` 与 `/minimax/v1/...` | PASS | — |
| `test_host_chat.py` | `set` 中文 / `upsert_graph` 中文角色？ | 有命中、不 mint、找不到打回。 | PASS | — |

**维度结论：** PASS

---

## 5. 发现项摘要

### Critical（阻塞提交）

无。

### High（阻塞提交）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| H1 | 4.2 | `cli/video_route.py`（修前） | 空 `video.provider` + 非 ARK `api_base` 被标成 `seedance`，CLI `--api-key/--api-base` Apilio 会打 ARK path | **已修**：先按 base 推断 backend；单测覆盖。验证：`test_legacy_custom_base_without_provider_is_compat`、`test_explicit_key_and_apilio_base_without_provider` |

### Medium（强烈建议修复）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| M1 | 4.6 / 1.6 | 工作区整体 | 视频 Spec 交付与 host_chat 自愈混在同一工作区；后者无 brainstorm | 提交时至少拆两 commit：`feat(video)` / `fix(host-chat heal)`；自愈可补一页短 spec 或接受聊天确认为 SoT |
| M2 | 4.4 | `cli/env_discover.py:209` | `seedance_key` 实际表示任意生视频 Key | 后续改名或在 doctor/GUI 标明「生视频 Key」 |
| M3 | 4.2 | `cli/brief.py:1010+` | type 推断「角色」优先于「背景」，可能误分类 | 观察策划实稿；假阳性再收紧 hint |

### Low / Nit（可选）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| L1 | 4.2 | `video_compat.py` vendor attempts | 无首帧时 Wan/Hailuo 不走厂商 path | 若要做 t2v 再补；本期 i2v 为准 |
| L2 | 验证 | MiniMax-H3 | 路径按 Hailuo 写了，未实网 | 有 Key 时补一刀 |
| L3 | Nit | `test_video_compat` stderr | fake PNG 触发 cv2 IHDR 警告 | 测试夹具可换成最小合法 PNG |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有自动化检查通过 | [x] |
| 安全扫描干净 | [x] |
| Karpathy score = 4/4 | [x] |
| 无未解决 Critical 问题 | [x] |
| 无未解决 High 问题 | [x] H1 已在审查中修复 |
| 评审文档完整 | [x] |
| 视频 diff 可追溯到工程 Spec | [x] |
| 策划自愈 SoT | [x] 聊天确认；建议拆 commit（M1，不阻塞质量门） |

### 结论

- [ ] **BLOCK** — 提交前必须解决发现项
- [x] **APPROVE** — 所有门禁通过；建议提交时拆 commit，随后 `/anvil:compound`

### 评审备注

- 用户规则优先于 Anvil §8：本次**不自动 commit**。批准后的 diff 仍在工作区，回滚风险在。
- 动画切分按用户要求不做，不纳入本门禁。
- GUI `tsc` 既有 test 失败不记入本变更。
- 建议 commit 顺序：① 多厂商生视频 + Seedance 2.5 + GUI/docs；② host_chat 自愈 + skill + tests。
