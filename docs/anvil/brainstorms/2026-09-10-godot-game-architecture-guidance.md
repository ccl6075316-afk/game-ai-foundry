# 工程 Spec：Godot 可维护原型架构指导（全局 + fishing 映射）

## 执行元数据

- **Status**：confirmed（用户 2026-09-10 回复「确认」）
- **Workflow Stage**：req → 可进入 plan
- **Created**：2026-09-10
- **Updated**：2026-09-10
- **Source Of Truth Until**：replaced by a `/anvil:plan`, or the request is abandoned
- **Requirements Source**：用户确认架构选型 A + 文档落点 C；对话中对「可维护原型 / Main 仅入口 / 分场景 / 系统可单测 / 数据抽离」的约束；仓库证据见下；用户显式确认本 Spec
- **Background Inputs**：fishing 试玩反馈与代码审阅聊天（背景）；Godot 官方 Scene organization；Game Programming Patterns 常识（背景，非编码事实源）
- **Compounded Knowledge**：not yet compounded
- **Resume Point**：首刀 Plan 已 executed（`2026-09-10-fishing-godot-maintainable-prototype-plan`）。Follow-up：其余屏分场景、Catalog JSON、fg matte。

## 背景输入

- 用户需要 **可维护、可修改的 Godot 原型**，拒绝「能玩但无后续开发价值」的上帝 `Main`。
- 类比 App：`Main` ≈ AppDelegate，不应承载具体玩法实体逻辑。
- 文档落点 **C**：Foundry 全局规范 + fishing 一页映射。
- 架构选型 **A**：场景组合 + 可单测 System + Catalog/Session 数据驱动；进度写入可有纪律，但 **不全量** Redux 式单向流。

## 工程理解

### 当前证据

- `projects/fishing-2d/game/scenes/main.tscn` 仅挂 `Main.cs`；多屏 UI/逻辑在 `Main.cs` + `Main.Screens.cs`（约 1.6k+ 行）内代码拼装。
- `GameSession.cs` / `GameCatalog.cs` 已有数据轮廓，但 Catalog 手写三鱼；战斗与库存逻辑未成独立可测模块。
- `docs/CONSTRUCTION-SYSTEM.md` 要求 `scenes[]`/`systems[]` 脚本职责与 Pass 4 填逻辑，但 `resources/skills/godot-developer/implement.md` **缺少架构硬门禁**。
- `production-scope.json` wave1 只裁 **内容范围**，不授权无架构实现。

### 工程结论

交付物是 **架构纪律文档 + skill 必读挂钩**，不是本轮重写 fishing 玩法。事实源为本 Spec；落地指导见：

- `docs/GODOT-GAME-ARCHITECTURE.md`（全局）
- `projects/fishing-2d/GODOT-ARCHITECTURE.md`（映射）

## 目标

1. 定义 Foundry 产出/维护的 Godot C# 游戏的 **默认架构**（可维护原型标准）。
2. 明确 Main / Screen Scene / System / Catalog / Session 的职责与禁令。
3. 给出 fishing-2d 对照表：现状违规点 → 目标落点。
4. 让 godot-developer Agent **必须阅读** 全局架构文，避免再次只交「能玩糊糊」。

## 非目标

- 本轮不重写 fishing `Main` / 不拆场景实现。
- 不上 ECS、不全量 MVVM/MVC 作为总架构。
- 不改 pipeline / brief schema / 资产生成。
- 不在本轮把 `test unit` 门禁扩到强制覆盖所有 System（留给 plan）。

## 当前架构约束

- Godot 4 .NET（C#）；官方惯用 **Scene 组合 + 节点生命周期**。
- Foundry：`brief.systems[]` / `production.systems` 语义不同但都应映射到代码模块。
- 现有验收：`godot validate`、可选 `test unit` / `test play`。

## 方案选择

**A + 文档落点 C（已确认）**

- 底座：一屏一 Scene、实体/零件子场景、Main 仅入口与路由。
- 规则：纯 C# System（尽量不依赖 `Control`），可 `dotnet test`。
- 数据：只读 Catalog（表/JSON/Resource）+ 可变 Session（跨屏进度）。
- 进度纪律（轻量）：View/屏发意图 → System 写 Session；禁止 UI 直接改金币等字段（指导级；硬校验可后续）。
- 文档：全局规范 + fishing 映射；`implement.md` 增加必读链接。

## 被排除方案

- **B MVC 总架构**：Controller 易二次上帝化。
- **C MVVM 总架构**：搏鱼状态机与绑定基础设施不匹配。
- **D ECS**：实体量与问题域不需要。
- **仅 fishing 文档**：无法约束后续 Foundry 游戏与 Agent。

## 边界与失败模式

- 指导被忽略 → 再次上帝 Main；缓解：skill 必读 + review 对照成功标准。
- 把每帧表现状态塞进 Session → 性能与复杂度爆炸；文档明确 Session 边界。
- Autoload 滥用装玩法 → 不可测；文档限制 Autoload 用途。

## 工程代价

- 文档 2～3 份 + 索引/skill 短链：低。
- 后续 fishing 按文档重铺：高（独立 plan）。
- skill 硬门禁与单测模板：中（plan 阶段）。

## 显式假设

1. 用户接受「引擎场景架构打底，而非 App MVC 总教义」。
2. wave1 内容范围不变；变的是实现质量标准。
3. 本轮以文档为交付；代码重铺需另开 `/anvil:plan`。

## 领域语言

| 术语 | 含义 |
|------|------|
| Main / App Shell | 根节点：启动、持有或解析 Session、切屏；无玩法分支丛林 |
| Screen Scene | 对应 brief 一屏的独立 `.tscn` |
| Part Scene | 可复用零件（船、竿、鱼演员） |
| System | 无 Godot 节点依赖（或极少）的规则模块，可单测 |
| Catalog | 只读配置/物种表 |
| Session | 跨屏可变进度（钱、仓库、天数） |
| Intent | 屏发出的「想做什么」；由 System 执行并写 Session |

## 功能需求

1. 存在全局架构指导文，含职责、目录建议、禁令、与 MVC/单向流关系说明。
2. 存在 fishing 映射文，指出当前违规与目标模块切分。
3. `docs/README.md`、`CONSTRUCTION-SYSTEM.md`、`godot-developer/implement.md` 互相链接。
4. Spec 确认后可进入 plan：重铺任务与 skill 验收条款。

## 非功能需求

- 中文为主；标识符/路径英文。
- Agent 可读：条目化、禁令可检查。
- 不要求本轮可运行代码变更。

## 安全关注点

- 无；纯文档与 skill 指针。不涉及密钥、存档加密策略（存档格式留给实现 plan）。

## 成功标准

1. 新人/Agent 只读全局文，能回答：Main 能否写卖鱼逻辑？（否）
2. fishing 映射文能指出 `Main.Screens.cs` 为违规集中点，并给出目标文件/场景切分。
3. `implement.md` 写明必读 `docs/GODOT-GAME-ARCHITECTURE.md`。
4. 用户确认 Spec 后 Status → confirmed。

## PR Review 关注点

- 文档是否把「内容 wave1」与「无架构」再次混淆。
- 是否暗含本轮必须重写代码。
- Autoload / Session 边界是否写清。

## 开放问题

| 项 | 状态 | 说明 |
|----|------|------|
| Session 用 Autoload 还是显式注入 | **已默认建议** Autoload 仅 Session+Catalog 访问器；玩法 System 不进 Autoload | plan 可推翻 |
| skill / CI 硬门禁（禁止 Main 新增玩法） | **延期** | 触发：Spec confirmed 后 `/anvil:plan`；owner：维护者 |
| fishing 重铺排期 | **延期** | 与船竿线场面、体型 cm 缩放可同一 plan |

## 决策账本

- **已确认**：架构 A；文档落点 C；可维护原型标准；Main 仅入口；分场景；系统可单测；数据抽离；不全量单向流。
- **默认建议（写入指导）**：Autoload 窄用；进度 Intent→System→Session。
- **已排除**：MVC/MVVM/ECS 总架构；本轮代码重写。
- **仍阻塞**：无。Spec 已 confirmed。
