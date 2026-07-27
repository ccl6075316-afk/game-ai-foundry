# 工程 Spec：外置工程根一等公民（可读可绑，不强制进 projects/）

## 执行元数据

- **Status**：confirmed
- **Workflow Stage**：req
- **Created**：2026-07-27
- **Updated**：2026-07-27（user「确认」）
- **Confirmed By**：user「确认」
- **Source Of Truth Until**：replaced by confirmed `/anvil:plan`
- **Requirements Source**：用户确认：不强制进 `projects/`；外置根一等公民（方案 2）；布局双形态探测（方案 1）；工作区 `external-projects.json` 索引（方案 1）；GUI 仅目录选择器添加（方案 1）
- **Background Inputs**：现有 `projects/<slug>/` 隔离布局；`planTargetsFromBrief` / `project_paths.py`；CLI `--project` 任意 Godot；fish2d 类「仓根即 Godot」
- **Compounded Knowledge**：not yet compounded

## 背景输入

用户纠正：外置工程（如独立 fish2d 仓）**不一定要拷进 / 链进 `projects/`**，但 Foundry **要能读、能绑定为当前工程**。

今日缺口：GUI 工程切换只扫工作区内 `projects/`（及旧扁平）；绝对路径外置根无法作为 brief/看板/流水线的绑定目标。

## 工程理解

Foundry 工程 = **brief 契约 + Godot 树 + 可选 pipeline/output/plans**。  
新建游戏继续默认 `projects/<slug>/`。  
外置工程 = 用户磁盘上已有目录，经索引登记后与内置工程在切换/绑定上等价（路径解析走绝对根）。

## 目标

1. **工作区索引**（推荐路径名：`external-projects.json`，位于 Foundry workspace 根，与 `projects/` 同级）：登记外置工程条目。
2. **GUI「打开外置工程…」**：仅 `showOpenDialog` 选目录；探测布局；写入索引；设为当前工程。
3. **双形态 Godot 探测**：
   - 根目录存在 `project.godot` → `godot_root = external_root`
   - 否则 `game/project.godot` → `godot_root = external_root/game`
   - 两者皆无 → 可登记但标 `godot_missing`；打开 Godot / validate 给出明确错误
4. **Brief / 产物**：
   - `brief.json` 优先 `external_root/brief.json`
   - `pipeline/`、`output/`、`plans/`、`production.json`、`progress.json`、`makeability.json` 写在 **external_root** 下（与 brief 同级）
   - 无 brief：允许绑定工程并出现在切换列表，状态「无 brief」；策划导出目标指向该根的 `brief.json`（不强制先迁到 `projects/`）
5. **路径模型扩展**：`bound_brief_rel` / active brief 除 `projects/...` 相对路径外，支持外置标识（如 `external:<id>/brief.json` 或索引 id + 绝对 brief 路径）；`planTargetsFromBrief` / CLI `project_paths` 能解析到绝对路径。
6. **顶栏切换**：内置 `projects/*` + 索引中的外置工程同一列表（外置可标注「外置」）。
7. **文档**：AI-HANDOFF / GUI 说明：新建仍推荐 `projects/`；外置不拷贝。

## 非目标

- 强制拷贝或软链进 `projects/`（用户已否）
- GUI 自由文本粘贴任意路径（v1）
- 自动为无 Godot 目录 scaffold 完整游戏（可后续）
- 改写外置仓的 git 远程 / 强制改其目录结构
- 多工作区同步同一外置索引到云端
- v1 必须交付 CLI `project external add`（**允许**同版或紧随；GUI 为门禁；CLI 若做须写同一索引、同一探测）

## 当前架构约束

- GUI：`projectPaths.ts`、`ProjectSwitcher`、`activeBrief` localStorage
- CLI：`project_paths.py`、`host_chat.bound_brief_rel`
- Electron：已有 workspace 根与对话框能力

## 方案选择

**采用：外置根一等公民 + workspace 索引 + 双形态探测 + 仅目录选择器添加。**

### 索引条目（概念）

```json
{
  "version": 1,
  "projects": [
    {
      "id": "ext_a1b2c3",
      "display_name": "fishing-2d",
      "root_abs": "/Users/…/fishing-2d",
      "godot_rel": ".",
      "brief_rel": "brief.json",
      "added_at": "ISO-8601"
    }
  ]
}
```

- `godot_rel`：`.` 或 `game`
- `brief_rel`：相对根；文件可不存在

### 解析

| 能力 | 行为 |
|------|------|
| 切换外置 | 读索引 → 绝对 brief / godot 路径 |
| pipeline plan/run | 产物目录 = `root_abs/{pipeline,output,plans}` |
| 打开 Godot | `root_abs / godot_rel` |
| 移除外置 | 只删索引条目，**不删**磁盘文件 |

## 被排除方案

| 方案 | 原因 |
|------|------|
| 必须进 `projects/` | 用户否决 |
| 仅 localStorage | CLI/备份弱 |
| GUI 粘贴任意路径 | 安全面；v1 用对话框 |
| brief 仍只写 workspace、Godot 外置 | 读写分裂 |

## 边界与失败模式

| 模式 | 处理 |
|------|------|
| 根路径消失 / 无权限 | 切换时错误提示；可从列表移除 |
| 无 project.godot | 允许绑定；Godot 操作失败并说明 |
| 无 brief.json | 可切换；export/流水线前引导创建 brief 到该根 |
| 与 `projects/<同名>` 冲突 | 用稳定 `id` 区分；display_name 可重复 |
| portable 工作区换机 | 绝对路径可能失效 → 提示重新选择目录 |
| Agent 写任意路径 | v1 不开放 GUI 文本框；CLI 若加需显式命令 |

## 工程代价

| 模块 | 量级 |
|------|------|
| 索引读写 CLI/GUI | 中 |
| `projectPaths` / `project_paths` 解析扩展 | 中–高 |
| ProjectSwitcher + 打开对话框 | 中 |
| host-chat bind 外置 brief | 中 |
| 探测 + 单测 | 中 |
| 文档 | 小 |

## 显式假设

- Workspace 根可写索引文件。
- 外置根用户有意授予写权限（pipeline 会写 output）。
- 新建游戏 UX 不变（仍 `projects/<slug>/`）。

## 领域语言

| 术语 | 含义 |
|------|------|
| **external root** | 用户磁盘上的工程根绝对路径 |
| **external registry** | `external-projects.json` |
| **godot_rel** | 相对根的 Godot 位置（`.` 或 `game`） |
| **内置工程** | `projects/<slug>/` |

## 功能需求

### FR-1 索引

- 读写 `external-projects.json`；schema_version；增删改查
- 幂等：同一 `root_abs`（归一化）不重复添加

### FR-2 探测

- `detect_external_layout(root) -> { godot_rel, has_brief, errors[] }`

### FR-3 GUI

- 「打开外置工程…」→ 目录选择器 → 探测 → 写入索引 → 切换
- 切换列表含外置项（徽标/后缀「外置」）
- 「从列表移除」不删磁盘

### FR-4 路径与流水线

- 当前工程为外置时：brief/production/progress/pipeline/output/makeability 均解析到 `root_abs`
- 现有 `projects/` 行为回归不变

### FR-5 缺 brief

- 可绑定；保存 Brief / export 目标为 `root_abs/brief.json`
- 无 brief 时「生成流水线」给出明确阻断文案

### FR-6 文档

- AI-HANDOFF、GUI 文案更新

## 非功能需求

- 探测纯本地、无网络
- 单测覆盖双形态与索引去重
- 打开不存在的 root 不崩溃

## 安全关注点

- GUI v1 仅目录选择器添加
- 不对索引外路径默认授权
- 展示绝对路径给用户确认

## 成功标准

1. 选中「根含 project.godot」的仓 → 可切换、可开 Godot（路径正确）。
2. 选中 Foundry 式 `game/project.godot` 外置拷贝 → `godot_rel=game`，产物写在外置根下。
3. 无 brief 外置根可出现在列表；export 后 brief 落在该根。
4. `projects/` 内置工程回归：切换/plan 路径与改前一致。
5. 移除索引项不删除外置磁盘文件。

## PR Review 关注点

- 是否又强制拷进 `projects/`
- 相对路径假设是否泄漏到外置绝对根
- 是否引入自由文本路径入口
- Windows 路径归一化与盘符

## 开放问题

| 项 | 状态 | 说明 |
|----|------|------|
| CLI `project external add` 是否同版 | deferred → plan | Spec 允许同版或紧随 |
| 索引文件名/字段精命名 | deferred → plan | |
| activeBrief localStorage 对外置的键格式 | deferred → plan | |

---

请回复 **确认** 以把本 Spec 标为 `confirmed` 并进入 `/anvil:plan`；或指出要改的点。
