# Hermes + Codex 接入指南

| | |
|--|--|
| **读者** | 使用 Hermes Agent 或 Codex terminal 的人 |
| **侧重** | **`hermes sync/install`**、skill 列表、`pty=true`、pipeline run 与多会话分工 |
| **不写** | brief 字段、设计/施工契约、里程碑 |
| **姊妹文档** | 索引 → [`README.md`](README.md) · CLI → [`AI-HANDOFF.md`](AI-HANDOFF.md) |

编排层：[Hermes Agent](https://github.com/NousResearch/hermes-agent)。执行层：**`gamefactory` CLI**。

---

## 架构

```
用户
  │
  ▼
Hermes（会话 / 记忆 / skills / gateway）
  │
  ├─ skill: game-factory-orchestrator  ── 编排、委派
  ├─ skill: game-factory-prompt-crafter ─ terminal → prompt craft
  ├─ skill: game-factory-image-generator ─ terminal → image generate
  ├─ skill: game-factory-video-generator ─ terminal → video generate
  └─ skill: game-factory-godot-assembler ─ terminal → godot assemble
          │
          ▼
     gamefactory CLI（本仓库 cli/）
          │
          ▼
     output/  plans/  games/
```

**一个 Hermes 会话只加载一个 skill**（一个 agent 角色），与仓库内 **六角色** 设计一致。

混排说明见 [`docs/AGENT-ROUTING.md`](AGENT-ROUTING.md)。迭代与 Change Request 见 [`docs/ITERATIVE-PRODUCTION.md`](ITERATIVE-PRODUCTION.md)。

**配置前先探测**（Hermes/Codex/Cursor 不随仓库分发）：

```bash
cd cli
python gamefactory.py doctor
python gamefactory.py agents show --discover
```

---

## 1. 安装

### 1.1 依赖

```bash
cd cli && pip install -r requirements.txt
```

配置 `~/.gamefactory/config.json`（见 `resources/config.example.json`）。

### 1.2 安装 Hermes skills

```bash
cd cli
python gamefactory.py hermes sync      # 从 resources/skills/ 生成 SKILL.md
python gamefactory.py hermes install   # 链到 ~/.hermes/skills/
```

自定义目录：

```bash
python gamefactory.py hermes install --target ~/my-hermes-skills
# 或 export HERMES_SKILLS_DIR=~/my-hermes-skills
```

### 1.3 Skill 包列表

| 包名 | 角色 | 用途 |
|------|------|------|
| `game-factory-orchestrator` | orchestrator | 流水线编排、抠图、Godot |
| `game-factory-prompt-crafter` | prompt-crafter | 写 prompt / plan JSON |
| `game-factory-image-generator` | image-generator | OpenRouter 生图 |
| `game-factory-video-generator` | video-generator | Seedance 图生视频 |
| `game-factory-godot-assembler` | godot-assembler | Godot 4 .NET 组装（无 GDScript） |
| `game-factory-godot-developer` | godot-developer | Pass 4：读 dev-context 写 C# 玩法 |
| `game-factory-codex` | — | Hermes/Codex 调 terminal 约定 |

查看路径：

```bash
python gamefactory.py hermes paths
python gamefactory.py hermes list
```

---

## 2. Hermes 里怎么用

### 2.1 加载 skill

在 Hermes 会话中让 agent 加载对应 skill（或 `skill_view game-factory-orchestrator`）。

### 2.2 调 terminal（必须 `pty=true`）

```text
terminal(
  command="cd /path/to/game-ai-foundry/cli && python gamefactory.py context --brief ../resources/asset-brief.example.json --asset knight",
  workdir="/path/to/game-ai-foundry",
  pty=true,
)
```

`hermes paths` 输出的 `cli_dir` / `repo_root` 即 `workdir` 与 `cd` 目标。

### 2.3 推荐：程序 runner（默认）

批量资产与 Godot 组装 **不必逐步开 Hermes 会话**，一条 `pipeline run` 即可：

```bash
cd cli
python gamefactory.py pipeline plan --brief ../resources/asset-brief.example.json
python gamefactory.py pipeline run --manifest ../pipeline/asset-brief.example.json --jobs 4
```

### 2.4 多会话委派（仅 AI 阶段）

| 步骤 | Hermes 会话 skill | 命令 |
|------|-------------------|------|
| brief / 编排 | `game-factory-orchestrator` | `brief export`, `pipeline plan`, triage |
| 写 prompt | `game-factory-prompt-crafter` | `prompt craft -o plans/x.json` |
| Pass 4 玩法 | `game-factory-godot-developer` | 读 `plans/dev_*.json` 写 C# |

生图 / 生视频 / matte / assemble 由 **`pipeline run`** 执行（executor=`pipeline`），见 [`docs/AGENT-ROUTING.md`](AGENT-ROUTING.md)。

### 2.5 手动分步（调试用）

| 步骤 | skill | 命令 |
|------|-------|------|
| 生图 | `game-factory-image-generator` | `image generate --plan-file ... --validate` |
| 生视频 | `game-factory-video-generator` | `video generate --plan-file ... --reference-image <raw>` |
| Godot 组装 | `game-factory-godot-assembler` | `godot assemble --assemble-file ...` |

---

## 3. Codex 接入方式

### 3.1 Codex CLI（经 Hermes terminal 委派）

与 Hermes 内置 [codex skill](https://github.com/NousResearch/hermes-agent/tree/main/skills/autonomous-ai-agents/codex) 相同：

```text
terminal(
  command="codex exec --full-auto 'Run gamefactory pipeline for raptor idle per AGENTS.md'",
  workdir="/path/to/game-ai-foundry",
  pty=true,
)
```

要求：**git 仓库**（本仓库已满足）、Codex 已登录（`~/.codex/auth.json` 或 `OPENAI_API_KEY`）。

### 3.2 Codex App-Server Runtime（可选）

Hermes `/codex-runtime codex_app_server` 时，文件编辑走 Codex 沙箱，**资产生成仍应 terminal 调 gamefactory**（不走 apply_patch 拼 CLI）。

资产类任务：加载 `game-factory-orchestrator`，用 terminal 跑 `gamefactory`。

### 3.3 本仓库 Codex 直接开发

根目录 **`AGENTS.md`** 给 Codex 读：六角色边界、校验闸门、agent routing。

---

## 4. 端到端示例

完整命令块 → [`AI-HANDOFF.md`](AI-HANDOFF.md) §5。原则：**AI 阶段开 Hermes 会话，资产批量用 `pipeline run`**。

---

## 5. CLI 参考

```bash
python gamefactory.py hermes sync      # 重新生成 SKILL.md
python gamefactory.py hermes install   # 安装到 ~/.hermes/skills
python gamefactory.py hermes install --copy  # 复制而非 symlink
python gamefactory.py hermes paths
python gamefactory.py hermes list
python gamefactory.py pipeline run --manifest ../pipeline/foo.json --jobs 4
```

---

## 6. 相关文档

- [`README.md`](README.md) — 文档索引
- [`AI-HANDOFF.md`](AI-HANDOFF.md) — CLI、抠图
- [`AGENT-ROUTING.md`](AGENT-ROUTING.md) — 六角色 executor
- [`ROADMAP.md`](../ROADMAP.md) — M2 进度
