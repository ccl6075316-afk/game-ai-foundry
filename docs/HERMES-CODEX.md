# Hermes + Codex 接入指南

Game AI Foundry 的编排层是 **[Hermes Agent](https://github.com/NousResearch/hermes-agent)**，执行层是 **`gamefactory` CLI**。Codex 可作为 Hermes 的终端执行引擎（`codex exec`）或可选 Codex App-Server Runtime。

---

## 架构

```
用户
  │
  ▼
Hermes（会话 / 记忆 / skills / gateway）
  │
  ├─ skill: game-factory-orchestrator  ── 编排、后处理
  ├─ skill: game-factory-prompt-crafter ─ terminal → prompt craft
  ├─ skill: game-factory-image-generator ─ terminal → image generate
  └─ skill: game-factory-video-generator ─ terminal → video generate
          │
          ▼
     gamefactory CLI（本仓库 cli/）
          │
          ▼
     output/  plans/  games/
```

**一个 Hermes 会话只加载一个 skill**（一个 agent 角色），与仓库内四 Agent 设计一致。

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
  command="cd /path/to/game-ai-foundry/cli && python gamefactory.py context --brief ../resources/test-brief-dino.json --asset raptor_scavenger",
  workdir="/path/to/game-ai-foundry",
  pty=true,
)
```

`hermes paths` 输出的 `cli_dir` / `repo_root` 即 `workdir` 与 `cd` 目标。

### 2.3 多会话委派（推荐）

| 步骤 | Hermes 会话 skill | 命令 |
|------|-------------------|------|
| 写 prompt | `game-factory-prompt-crafter` | `prompt craft -o plans/x.json` |
| 生图 | `game-factory-image-generator` | `image generate --plan-file ... --validate` |
| 生视频 | `game-factory-video-generator` | `video generate --plan-file ... --reference-image <raw>` |
| 后处理 | `game-factory-orchestrator` | trim / remove-bg / split-frames / matte-frames |

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

根目录 **`AGENTS.md`** 给 Codex 读：目录结构、四 agent、校验闸门。

---

## 4. 示例：动画（推荐 `pipeline run`）

```bash
cd cli

# A. AI：brief + plans（可 Hermes prompt-crafter 会话）
python gamefactory.py prompt craft \
  --brief ../resources/test-brief-wasteland-boar-idle.json \
  --asset mutant_boar -o ../plans/mutant_boar.json
python gamefactory.py prompt craft --animation \
  --brief ../resources/test-brief-wasteland-boar-idle.json \
  --asset mutant_boar_idle -o ../plans/mutant_boar_idle.json

# B. 程序 runner（无需 Hermes 逐步 terminal）
python gamefactory.py pipeline plan \
  --brief ../resources/test-brief-wasteland-boar-idle.json \
  -o ../pipeline/wasteland-boar-idle.json \
  --output-dir ../output/wasteland5-boar-idle
python gamefactory.py pipeline run --manifest ../pipeline/wasteland-boar-idle.json --jobs 4
```

产物：`output/wasteland5-boar-idle/mutant_boar_idle.mp4`、`mutant_boar_idle_nobg/frame_*.png`。

### 4.1 手动分步（旧方式，仍可用）

见 `docs/AI-HANDOFF.md` §5 单条命令速查；多资产优先 `pipeline run`。

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

## 6. 里程碑状态（M2）

| 项 | 状态 |
|----|------|
| Hermes SKILL.md 包 | ✅ `resources/hermes/` |
| `hermes sync` / `install` | ✅ |
| `AGENTS.md`（Codex） | ✅ |
| 本文档 | ✅ |
| `pipeline run` 程序 runner | ✅ |
| Hermes Kanban / 自动多会话 | ⬜ 可选 |
| Electron GUI ↔ Hermes IPC | ⬜ 未来 |

---

## 7. 相关文档

- [`docs/AI-HANDOFF.md`](AI-HANDOFF.md) — 流水线细节、配置、抠图
- [`AGENTS.md`](../AGENTS.md) — Codex 速查
- [`resources/skills/`](../resources/skills/) — skill 源文件（`hermes sync` 会合并进 SKILL.md）
