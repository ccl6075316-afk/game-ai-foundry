# Review Report: `2026-10-21-106-eye-ownership`

## Metadata

| Field | Value |
|---|---|
| Reviewer | anvil-lead，独立审查material_repair_review |
| MR / Commit | 未提交的106局部实验 |
| Author | source_ink_sampler_doer |
| Review Date | 2026-10-21 |
| Status | APPROVED，限定眼睛试修代码；整鱼交付BLOCKED |

范围为Large代码变更；检查接口、边界、运行时合同及真实图像，未以机械检查代替视觉。

## 1. Automated Pre-checks

| Check | Command | Result | Notes |
|---|---|---|---|
| Lint | 两仓库git diff --check | PASS | 本目录无独立GD lint配置 |
| Type Check | 实际Godot装配/脚本解析；Python py_compile | PASS | 使用真实引擎，不以文本解析替代 |
| Unit Tests | check_eye_contract.gd、check_body_coverage_contract.gd | PASS | 包括15项主动破坏负例 |
| GPU身份及保留 | 47 baseline/off/三探针/candidate | PASS | off全RGBA相等；允许并集外0变化，alpha0变化 |
| 额外身份/诊断 | 48 LOD-only对照、85有效owner图 | PASS | 0差异、无fault |
| 真实切换 | capture_eye_transitions.gd，24图 | PASS | transition状态和剩余时长断言 |
| 身体 | validate_body_integrity.py | PASS | 原算法16视图缺块0 |
| 完整鳍膜 | 原冻结门490姿态 | FAIL | 原有左胸鳍35姿态；不属于眼睛代码可覆盖的交付门 |

## 2. Security Scan

| Category | Finding | Severity | Status |
|---|---|---|---|
| Hardcoded Secrets | 本轮文件无密钥 | — | CLEAN |
| Injection Risks | 无shell拼接或网络调用；shader包装拒未知语法 | — | CLEAN |
| XSS Vulnerabilities | 非Web内容 | — | N/A |
| Dependency CVEs | 无新增依赖 | — | N/A |
| Sensitive Data in Logs | 最终保留日志只含本任务路径/引擎结果/哈希 | — | CLEAN |

**Security Verdict:** CLEAN

## 3. Karpathy Adversarial Principles

| Principle | Adversarial Question | Answer | Verdict | Severity |
|---|---|---|---|---|
| Think Before Coding | 域和LOD假设是否成立？ | r015/r017与原LOD5被实际射线/GPU否定后重新设计，明确记录例外 | PASS | — |
| Simplicity First | 能否删一半而不丢功能？ | 大部分为来源/像素/mesh保持与拒绝合同；独立眼层是已发生问题所需，无跨鱼泛化框架 | PASS | — |
| Surgical Changes | 每行是否对应本任务？ | 正式game未变；仅106helper/profile/freezer、严格身体门兼容 | PASS | — |
| Goal-Driven Execution | 测试证明效果还是只运行？ | 原baseline、RGB独立探针、真正动作切换与主动破坏反例证明可观察行为 | PASS | — |

**Karpathy Score:** 4/4

## 4. Adversarial Dimension Review

### 4.1 Design — Should this exist at all?

| Line(s) | Question | Answer | Assessment | Severity |
|---|---|---|---|---|
| FishEyeOwnership.gd:283–307 | 是否用复制材质掩盖错误网格？ | 只修改原RGB路径，LOD故障另显式修复；全图身份独立验证 | PASS | — |
| capture_body_coverage.gd:6–65 | 动态shader会否任意放行？ | 限鱼/mesh/surface/实际绑定，安装代码SHA与依赖完整匹配，再验不透明合同 | PASS | — |

**Dimension Verdict:** PASS

### 4.2 Functionality — What is missing?

| Line(s) | Question | Answer | Assessment | Severity |
|---|---|---|---|---|
| gdshaderinc:22–31 | lookup失败会不会当无眼通过？ | mode2明确magenta；85张有效图无fault | PASS | — |
| gdshaderinc:39–70 | 是否改alpha/原调色？ | original.a返回，独立眼RGB保留modulation；GPU alpha0变化 | PASS | — |
| capture_body_coverage.gd:160–185 | 缺依赖是否被忽略？ | 只对单鱼106且实际未使用head/mouth列optional；required先exists | PASS | — |

边界覆盖：null、错误mode/probe、缺来源、旧SHA、错mesh、未知取样、模板改变及ALPHA/discard。无新增并发或外部服务。

**Dimension Verdict:** PASS

### 4.3 Complexity — Can this be simpler?

| Line(s) | Question | Answer | Assessment | Severity |
|---|---|---|---|---|
| FishEyeLod106.gd:35–66 | 为何操作packed surfaces？ | 解码再重建会改量化法线/LOD数据；现方法严格白名单拒未知字段，保持packed bytes | PASS | — |
| freeze_eye_features.py:26–48 | 为何镜像供体？ | 保留原生像素变化，不插值，不用灰常量大块填充 | PASS | — |

**Dimension Verdict:** PASS；无新增推测性抽象。

### 4.4 Naming — Does the name lie?

当前projection/repair为有效参数；profile的centers/radii/fade_q/proposal是历史数据，README已明确，不再暗示其控制当前shader。Medium跟进项见下。

**Dimension Verdict:** PASS，存在已说明的历史字段。

### 4.5 Comments — Do they explain why?

FishEyeLod106.gd:57–58解释保留packed数据原因；transition脚本解释restart与真实blend差异；README明确导出包未验证。无未归属TODO。

**Dimension Verdict:** PASS

### 4.6 Style & Consistency

| Line(s) | Issue | Type | Status |
|---|---|---|---|
| 当前新增GD脚本 | 沿用已有实验脚本风格，个别长行 | Nit | 不阻断本实验；无混入格式重写 |

**Dimension Verdict:** PASS

### 4.7 Context — System health

可复用代码留Foundry resources，物种数据独立；Fish保留来源、失败与当前报告。身体门仅补严格106兼容，旧固定路径行为保留。GLB和正式game不变；旧LOD故障、鳍膜失败均未掩盖。

**Dimension Verdict:** PASS

### 4.8 Tests — Do they prove behavior?

check_body_coverage_contract.gd:17–39主动移除回执、改五种SHA、改代码、破坏template、伪造SHA后注入ALPHA/discard，均被拒。GPU独立RGB探针先限定影响区，再比较候选；无用after定义允许范围。四动作切换使用实际transition语义。16身体视图与离散采样局限有记录。

**Dimension Verdict:** PASS

## 5. Findings Summary

### Critical / High (Block Commit)

无未解决代码发现。整鱼验收另有真实鳍膜阻断，不能因本代码门批准而覆盖。

### Medium (Strongly Recommend Fix)

| # | Dimension | Line(s) | Description | Required Action |
|---|---|---|---|---|
| M1 | Naming | eye-black-seabream-106.json:centers/radii/fade_q/proposal | 历史字段不控制当前投影 | 已在README说明；未来迁移schema时移出，不为整理触发本次重冻结 |
| M2 | Context | README导出限制 | rawPNG导出包未验证 | 只交本地试验；正式集成前验证export include及实际导出运行 |

### Low / Nit

capture_eye_transitions.gd:2仍称Temporary，含义为诊断非产品运行脚本，现已永久保存；不影响行为。

## 6. Gate Decision

| Gate | Status |
|---|---|
| 眼睛代码相关自动检查 | PASS |
| Security scan | CLEAN |
| Karpathy score | 4/4 |
| Critical / High unresolved | NONE |
| 独立Phase4审查 | APPROVED |
| 整鱼接受 | BLOCKED，原鳍膜失败 |
| Review document | COMPLETE |

**APPROVE** — 仅保留、展示106眼睛试修及严格身体门兼容补丁。本轮未提交或推送，未volume accept。知识已沉淀至`docs/anvil/knowledge/2026-10-21-fish-eye-ownership.md`。
