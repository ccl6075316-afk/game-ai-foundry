# Godot 游戏架构指导（Foundry 默认）

| | |
|--|--|
| **读者** | godot-developer Agent、程序员同事、维护者 |
| **地位** | Foundry 产出的 Godot C# 游戏的 **默认可维护原型标准** |
| **姊妹** | 施工流程 → [`CONSTRUCTION-SYSTEM.md`](CONSTRUCTION-SYSTEM.md) · 角色 → godot-developer `implement.md` · 范例映射 → [`../projects/fishing-2d/GODOT-ARCHITECTURE.md`](../projects/fishing-2d/GODOT-ARCHITECTURE.md) |
| **事实源** | [`anvil/brainstorms/2026-09-10-godot-game-architecture-guidance.md`](anvil/brainstorms/2026-09-10-godot-game-architecture-guidance.md) |

---

## 0. 一句话

**引擎用场景树组装世界；用 System 算规则；用 Catalog/Session 管数据。`Main` 只做程序入口与切屏，不做玩法垃圾桶。**

交付标准是 **可维护可修改的原型**，不是「能点通的演示糊糊」。  
`production-scope` / wave1 只裁 **内容范围**，不授权无架构实现。

---

## 1. 为什么不是 App 式 MVC 总架构

游戏与典型 App 的交互形态不同：

- 大量实体 **不靠用户点击也会每帧更新**
- 时间模型是 **Game Loop**，不是请求/响应
- 「真相」常分散在节点变换、物理、动画与进度数据之间

因此：

| 做法 | 态度 |
|------|------|
| 场景组合 + System + 数据表 | **默认总架构** |
| MVC / MVVM | 可用于 **局部复杂 UI**（商店表单等），不作全局教义 |
| 全量单向数据流（一切进 Store） | **不作为**总架构；进度层可对 Session 采用「Intent → System 写入」纪律 |
| ECS | 仅海量同类实体/性能瓶颈时考虑 |

不必把 VC 强行一一对应到 Node/Scene；隐喻可辅助理解，不是规范本身。

---

## 2. 分层职责

```text
┌─────────────────────────────────────────┐
│ Main（App Shell）                        │
│  启动 · 解析 Session/Catalog · 切屏路由   │
└───────────────┬─────────────────────────┘
                │ 实例化 / 切换
┌───────────────▼─────────────────────────┐
│ Screen Scenes（一屏一 .tscn）              │
│  展示 · 收集输入 · 发 Intent · 读 Session  │
│  子树：Part Scenes（船、竿、鱼演员…）      │
└───────────────┬─────────────────────────┘
                │ 调用
┌───────────────▼─────────────────────────┐
│ Systems（纯逻辑，可单测）                  │
│  Combat / Economy / Inventory / Aquarium… │
└───────────────┬─────────────────────────┘
                │ 读/写
┌───────────────▼─────────────────────────┐
│ Data                                      │
│  Catalog（只读配置） · Session（跨屏进度）  │
└─────────────────────────────────────────┘
```

### 2.1 Main / App Shell

**可以**

- `_Ready` 初始化、注册输入、加载 Catalog
- 持有或解析 `SessionState`
- `ChangeScene` / 挂载当前 Screen Scene
- 转发「打开某屏」的路由

**禁止**

- 卖鱼、搏鱼公式、仓库整理、水族馆容量计算等 **玩法分支**
- 在 `Main` 里用巨大 `switch(screen)` 拼全游戏 UI（临时原型除外，且不得合入「完成」状态）

### 2.2 Screen Scene（整屏）

- 对应 brief / production 的 **一个 scene id** → 一个 `scenes/<id>.tscn`（或等价目录约定）
- 负责该屏的节点树、动画表现、按钮信号
- 读 Session/Catalog 刷新 UI；用户操作转为 **Intent**，交给 System
- 屏内局部表现状态（滚动位置、张力条动画）可留在屏内，**不必**写入 Session

### 2.3 Part Scene（零件）

- 可复用的船、竿、鱼、槽位等
- 自带进入树 / 每帧 / 退出树生命周期
- 不直接改全局金币；需要时发信号或回调给 Screen / System

### 2.4 System（规则）

- 优先 **普通 C# 类**（不继承 `Node`），输入输出都是数据
- 一个 brief `systems[]` id 应对应一个（或一组）System 类型
- **必须能在无 Godot 编辑器的 `dotnet test` 下测核心公式与状态转移**
- 不要把 System 做成「第二个 Main」

### 2.5 Catalog 与 Session

| | Catalog | Session |
|--|---------|---------|
| 可变性 | 运行时只读（加载后） | 可变 |
| 内容 | 鱼种、钓点、商品、`real_length_cm`… | 金币、仓库、鱼缸、天数、图鉴… |
| 来源 | JSON / Godot `Resource` / 导出表 | 开局新建；日后可存档 |
| 谁写 | 工具链 / 策划表 | **仅 System**（或明确的 Session API） |

**进度纪律（推荐）**

1. View/Screen 不直接 `_session.Coins += …`
2. Screen 调用 `economy.SellFish(session, fish)` 等
3. System 返回结果；Screen 再刷新

每帧仿真数据（张力瞬时值）留在 CombatSystem 或战斗屏局部；**结算成功**后再写入 Session。

---

## 3. 场景与目录约定（建议）

```text
game/
  project.godot          # main_scene → scenes/main.tscn
  scenes/
    main.tscn            # 仅 App Shell
    main_hub.tscn
    fishing_battle.tscn
    …                    # 一屏一文件
    parts/               # 可选：船、竿、鱼演员
  scripts/
    app/Main.cs
    data/SessionState.cs
    data/FishCatalog.cs
    systems/CombatSystem.cs
    systems/EconomySystem.cs
    screens/…            # 与屏场景脚本
  data/                  # JSON 表（可选）
  tests/                 # 或独立测试工程：测 systems/
```

名称可按项目调整，但 **「一屏一场景 + systems 独立 + data 抽离」** 不可弃。

---

## 4. Autoload

**允许（窄）**

- 全局音频、设置
- Session / Catalog 的访问入口（若团队同意）

**禁止**

- 把 Combat、Economy、整页 UI 做成巨型 Autoload「管理器」
- 隐藏依赖导致 System 无法单测

优先：Screen 构造时注入 System 与 Session 引用。

---

## 5. 与 Foundry 施工产物的对齐

| Foundry 概念 | 代码落点 |
|--------------|----------|
| `project.scenes[]` / 分册 scene | Screen `.tscn` + screen 脚本 |
| `project.systems[]` / 分册 system | `scripts/systems/*` |
| `assets[]` + `real_length_cm` | Catalog 字段；显示缩放由此推导 |
| `production.godot_tasks[]` | 按模块拆任务，禁止单任务「实现全部 UI 于 Main」 |
| `godot scaffold` | 应生成 Screen stub 与 System stub，而不仅是空 Main |

---

## 6. Agent / 人工禁令清单（审查用）

合入前自检：

- [ ] 新增玩法是否落在 System 或 Screen，而非 `Main`？
- [ ] 是否为一屏新增/使用独立 `.tscn`，而非只在 `Main` 里 `BuildXxx`？
- [ ] 鱼种/数值是否进 Catalog 表，而非再抄一段静态 C#？
- [ ] System 是否有（或可补）不依赖场景树的单元测试？
- [ ] Session 字段是否仅由 System/API 修改？

任一项为否 → **未达到可维护原型标准**。

---

## 7. 参考

- Godot 官方：[Scene organization](https://docs.godotengine.org/en/stable/tutorials/best_practices/scene_organization.html)
- 模式词汇：Game Loop、Scene Manager、State、Component、Data-driven（见 Game Programming Patterns 等）
- 本仓库施工：[`CONSTRUCTION-SYSTEM.md`](CONSTRUCTION-SYSTEM.md)
