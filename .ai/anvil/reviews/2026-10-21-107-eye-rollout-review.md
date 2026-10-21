# Review Report: `2026-10-21-107-eye-rollout`

## Metadata

| Field | Value |
|---|---|
| Reviewer | anvil-lead；独立material_repair_review |
| MR / Commit | 未提交的107局部试版 |
| Author | source_ink_sampler_doer |
| Review Date | 2026-10-21 |
| Status | APPROVED，限定局部眼睛试版；整鱼/正式替换BLOCKED |

Large变更：检查接口、原路径替换、拒绝合同、来源/几何保留及真实GPU。沿用106已审的取样parser，107保留独立版本以冻结旧实验。

## 1. Automated Pre-checks

| Check | Command | Result | Notes |
|---|---|---|---|
| Lint | 两仓库git diff --check | PASS | 该目录无独立GD lint配置 |
| Type Check | Godot check-only/真实装配；Python py_compile | PASS | 真实GPU最终14批无ERROR/WARNING |
| Unit Tests | check_eye_contract.gd | PASS | 0/1/2、全路/退役探针；非法输入拒绝 |
| Body contract | check_body_coverage_contract.gd | PASS | 3正例、22拒绝负例；106旧合同回归通过 |
| GPU identity | 标准47＋压力48 | PASS | 最终mode0对独立原版逐RGBA零差 |
| GPU preservation | 全路三基色＋退役单独三基色 | PASS | 候选并集外RGBA0，全部alpha0，退役探针域包含在全路并集 |
| Transitions | 实际四次切换24图 | PASS | set_action(false)、step0及transition状态断言 |
| Fin/body | 177根、490根/膜、16身体视图 | PASS | 原容差未改；几何输入未变 |
| LOD5 eye geometry | CPU＋实际粗压力 | FAIL | 原439面仍失败，保留全部LOD；不属于可放行的正式资产 |

独立审查额外重跑check_eye_contract成功；其headless启动有本机CA证书环境ERROR，不能称该日志全clean。主线程最终14批实际GPU日志clean。

## 2. Security Scan

| Category | Finding | Severity | Status |
|---|---|---|---|
| Hardcoded Secrets | 新文件无密钥 | — | CLEAN |
| Injection Risks | 无shell拼接/网络；shader替换绑定原代码及唯一项 | — | CLEAN |
| XSS Vulnerabilities | 非Web产品 | — | N/A |
| Dependency CVEs | 无新增依赖 | — | N/A |
| Sensitive Data in Logs | 只保留本任务来源/路径/像素/哈希与引擎结果 | — | CLEAN |

**Security Verdict:** CLEAN

## 3. Karpathy Adversarial Principles

| Principle | Adversarial Question | Answer | Verdict | Severity |
|---|---|---|---|---|
| Think Before Coding | 是否把所有条纹当眼纹？ | 23对象分类，实际来源反查，只新增梭鲈 | PASS | — |
| Simplicity First | 能否删一半而不丢约束？ | 大部分为来源/mesh/采样合同和诊断；单鱼版本未造全物种框架 | PASS | — |
| Surgical Changes | 有无顺手改几何/动作？ | 原GLB、数组、6＋2LOD、rig和fin保留，正式game不变 | PASS | — |
| Goal-Driven Execution | 检查能证结果还是只跑起来？ | 独立原版、实际白圈源坐标、RGB影响区和主动破坏负例 | PASS | — |

**Karpathy Score:** 4/4

## 4. Adversarial Dimension Review

### 4.1 Design — Should this exist at all?

| Line(s) | Question | Answer | Assessment | Severity |
|---|---|---|---|---|
| FishEyeOwnership.gd:202 | 为何不直接放宽106？ | 保留106已审代码，107只绑定实际梭鲈原装配/参数 | PASS | — |
| capture_body_coverage.gd:63、133 | 是否任意放行动态shader？ | 仅106黑鲷/107梭鲈分派；其余未知拒绝，固定原shader路径不改 | PASS | — |

**Dimension Verdict:** PASS

### 4.2 Functionality — What is missing?

| Line(s) | Question | Answer | Assessment | Severity |
|---|---|---|---|---|
| helper:319–320 | 是否连嘴/secondary一并关闭？ | 精确唯一原眼项退役；后续逻辑保留，未知开启路径拒绝 | PASS | — |
| shaderinc:40、57、74 | 是否漏旧供体域外影响？ | source/fallback、新眼与实际retired返回路径均有RGB探针；退役单独探针另验 | PASS | — |
| body capture:63–131 | 实际纹理/mesh可否在安装后被改？ | code/template/依赖SHA、实际7纹理RGBA、全部arrays/LOD/binding、mode/projection均检查 | PASS | — |

空模型、错误模式/采样器、旧数据、缺receipt、代码/ALPHA/opaque/mode篡改均覆盖。无新增并发或外部服务。

**Dimension Verdict:** PASS

### 4.3 Complexity — Can this be simpler?

取样parser来自106已审合同；严格冻结材质uniform及全部mesh/LOD替代推测。107副本暂为独立实验，删除来源/拒绝代码会失去已验证的工程边界；未新增通用眼睛检测抽象。

**Dimension Verdict:** PASS

### 4.4 Naming — Does the name lie?

mode0身份、mode1局部颜色、mode2诊断，global与retired probes明确；安装receipt持续failed LOD5，未将CPU采样或body通过命名为整鱼接受。

**Dimension Verdict:** PASS

### 4.5 Comments — Do they explain why?

源码/README解释旧cleanup空间影响区、CPU完整源rim缺预像、rawPNG导出限制及缺失几何无法着色；没有把“无橙色”解释成全LOD通过。早期0/2快照与最终0/1/2区分。

**Dimension Verdict:** PASS

### 4.6 Style & Consistency

| Line(s) | Issue | Type | Status |
|---|---|---|---|
| freeze_eye_features_107.py | 沿用该工具目录简短实验CLI风格，部分长行 | Nit | 不阻断本地试版；无格式重写混入旧文件 |

**Dimension Verdict:** PASS

### 4.7 Context — System health

通用方法/单鱼数据保存在Foundry resources；Fish留全23对象清单、成功/失败、同姿态标注与冻结证据。未重新生成源图或伪造接受。共享body检查器改变后，106专有函数未变，旧负例和新16视图GPU回归通过，106报告SHA已刷新。

**Dimension Verdict:** PASS

### 4.8 Tests — Do they prove behavior?

源码身份/纹理/geometry主动篡改失败，22负例证明未知或污染输入被拒；基线由当前正式材质恢复，不冒用105 donor候选。RGB独立探针定义允许域后才比较候选；普通吻白来源控制点及实际多视保留。粗档仍坏的真实负例没有删除。

**Dimension Verdict:** PASS

## 5. Findings Summary

### Critical / High (Block Commit)

本次局部试版代码无未解决发现。资产层原LOD5仍是正式替换/整鱼接受阻断；代码批准不覆盖该失败。

### Medium (Strongly Recommend Fix)

| # | Dimension | Line(s) | Description | Required Action |
|---|---|---|---|---|
| M1 | Context | README export限制 | 本地试版未验证rawPNG导出包 | 正式集成前另验证export include和实际导出运行 |
| M2 | Complexity | 107独立helper/parser | 与106保留版本重复 | 多鱼验证后再考虑抽公共组件；当前不改已审106制造额外失效 |

### Low / Nit

原吻端白环、一般皮肤拖纹未解决，已单列其他根因；未借眼睛任务扩大处理范围。

## 6. Gate Decision

| Gate | Status |
|---|---|
| 局部试版相关自动检查 | PASS |
| Security scan | CLEAN |
| Karpathy score | 4/4 |
| Unresolved Critical/High code findings | NONE |
| 独立各阶段审查 | APPROVED |
| 完整资产/正式替换 | BLOCKED，LOD5失败 |
| Review document | COMPLETE |

**APPROVE** — 仅保留与展示梭鲈局部眼睛试版。没有volume accept、正式game改动或本轮提交/推送。知识见`docs/anvil/knowledge/2026-10-21-fish-eye-rollout.md`。
