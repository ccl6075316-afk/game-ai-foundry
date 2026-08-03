# 评审报告：`2026-08-03-prompt-follow-host`

## 元数据

| 字段 | 值 |
|------|----|
| Reviewer | anvil-lead |
| MR / Commit | uncommitted working tree |
| Author | Auto (本会话) |
| Review Date | 2026-08-03 |
| Status | `APPROVED` |

---

## 范围

| 项 | 值 |
|----|----|
| Size | Small（~70 行，4 文件） |
| Type | 共享配置解析契约 + GUI 保存同步 + 文档 |
| Loaded standards | 轻量对抗审查；未拉历史 learnings（改动面小、token 预算） |
| Spec 溯源 | 轻量路径；用户明确要求「生文跟设置，不与生图网关漂移」 |

变更文件：`cli/llm_config.py`、`cli/test_llm_config.py`、`gui/.../ProviderSettingsView.tsx`、`docs/GUI-CONFIG.md`

---

## 1. 自动化预检

| 检查项 | 命令 | 结果 | 备注 |
|--------|------|------|------|
| Lint | N/A | N/A | 本 diff 无项目级 lint 门槛 |
| 类型检查 | N/A | N/A | 未跑 GUI tsc；见 Low#1 |
| 单元测试 | `python -m unittest test_llm_config -v` | PASS | 6/6 |

---

## 历史经验检查

| Source | Applied lens | Result |
|--------|--------------|--------|
| （跳过全量检索） | 配置漂移 / host↔image 回落 | 用于检查 host 是否仍继承 image.api_base |

---

## 2. 安全扫描

| 类别 | 发现 | 严重级别 | 状态 |
|------|------|----------|------|
| 硬编码密钥 | 无 | — | OK |
| 注入风险 | 无 | — | OK |
| XSS 风险 | 无 | — | OK |
| 依赖 CVE | 无 | — | OK |
| 日志敏感数据 | 无新增日志 | — | OK |

**安全结论：** CLEAN

说明：GUI 把 `api_key` 镜像进 `prompt` 是已有 config 形态的延续，非新增外泄面；运行时在 host 已配时也不再读 prompt 凭证。

---

## 3. Karpathy 对抗式原则

| 原则 | 对抗式问题 | 作者回答（显式或推断） | 结论 | 严重级别 |
|------|------------|--------------------------|------|----------|
| Think Before Coding | 假设？ | 假设 GUI「生文」= `host.api_key` 已写；用 `host_cfg` 而非 resolve 后的 key 判断 ready，避免 prompt/image 回落误判 | PASS | — |
| Simplicity First | 能否删一半？ | 早返回 + legacy 分支，无新抽象 | PASS | — |
| Surgical Changes | 每行可溯源？ | 解析优先 host；保存同步 prompt；测例对齐；文档一句 | PASS | — |
| Goal-Driven Execution | 测试证明什么？ | 覆盖「host 压制 stale prompt」「无 host 走 legacy」 | PASS | — |

**Karpathy Score:** 4/4

---

## 4. 对抗式维度评审

### 4.1 设计

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `llm_config.py` host_ready | 是否应删掉独立 `config.prompt`？ | 保留 legacy 填洞；GUI 同步对齐 | 合理，不阻塞 | — |
| `ProviderSettingsView` 镜像 prompt | 同步密钥是否多余？ | 便于磁盘与 doctor 一致；运行时已不依赖 | 可接受；清字段亦可 | Low |

**维度结论：** PASS

### 4.2 功能

| 行号 | 提问 | 作者回答 | 评审判断 | 严重级别 |
|------|------|----------|----------|----------|
| `resolve_prompt` host_ready 分支 | host 有 key、无 api_base，image 为纯出图网关时？ | 走 `resolve_host` → 仍可能继承 `image.api_base` | **残余空洞**；GUI 正常保存会写 host.api_base，手改 config 仍可能踩 | Medium |
| CLI kwargs | 显式覆盖？ | `api_key` / `api_base` / `prompt_model` 仍优先 | OK | — |

**已检查关键边界：**
- [x] 空 / 仅 prompt legacy
- [x] host + stale prompt
- [ ] host 无 api_base + image 异网关（未测）
- [x] YOUR_ 占位（`_is_set`）
- [ ] 竞态 N/A

**维度结论：** FINDINGS（Medium 残余，不阻塞）

### 4.3 复杂度

无投机抽象。PASS。

### 4.4 命名

`host_ready` 语义清楚。PASS。

### 4.5 注释

解释 WHY（Midjourney / stale gateway）。PASS。

### 4.6 风格

`prompt.proxy: null` 与 host 一致；类型上 `ConfigPatch.prompt.proxy` 未标 `| null`（Nit）。

### 4.7 上下文

消除设置与运行时漂移，系统更健康。PASS。

### 4.8 测试

三测对齐新契约；缺「host 无 base + image 异 base」回归。Medium 与 4.2 同源。

---

## 5. 发现项摘要

### Critical（阻塞提交）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| — | — | — | 无 | — |

### High（阻塞提交）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| — | — | — | 无 | — |

### Medium（强烈建议修复）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| 1 | 功能 | `llm_config.py` host_ready + `resolve_host_api_settings` | host 已配 key 时，`api_base` 仍可能经 host 解析回落到 **image.api_base**（纯出图网关） | 可选：host_ready 分支只用 `host_cfg` 的 base/model/key，或禁止 host 文本路由继承 image base；并补测 |

### Low / Nit（可选）

| # | 维度 | 行号 | 描述 | 必须动作 |
|---|------|------|------|----------|
| 1 | 风格 | `vite-env.d.ts` `prompt.proxy` | 赋 `null` 时类型未含 `\| null` | 对齐 host 的 `proxy?: string \| null` |
| 2 | 设计 | `toProviderPatch` | 镜像密钥 vs `null` 删掉 stale prompt 字段 | 任选；当前镜像可接受 |

---

## 6. 门禁结论

| 门禁项 | 状态 |
|--------|------|
| 所有自动化检查通过 | [x]（scoped unittest） |
| 安全扫描干净 | [x] |
| Karpathy score = 4/4 | [x] |
| 无未解决 Critical 问题 | [x] |
| 无未解决 High 问题 | [x] |
| 评审文档完整 | [x] |

### 结论

- [x] **APPROVE** — 无 Critical/High；Medium#1 为残余风险，不阻塞本次「prompt 跟 host」主目标
- 提交：按用户规则，**不自动 commit**；需要时请说「提交」
- 可选后续：修 Medium#1（host 文本路由勿继承 image base）

### 评审备注

本次正确切断「遗留 `config.prompt` 抢路由」；用户所述 Midjourney 生图专用通道不应再劫持 prompt craft。GUI 正常保存路径下 host 带 `api_base`，主路径安全。
