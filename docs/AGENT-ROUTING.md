# Agent Routing — 混排执行器

主 Agent（Hermes / Cursor Agent / Codex）**只负责编排与异常**；资产与 Godot 组装由专职 Worker Agent 通过 CLI 或 `pipeline run` 执行。

---

## 五 Agent 角色

| Role ID | 默认 executor | Hermes skill | 职责 |
|---------|---------------|--------------|------|
| `orchestrator` | `hermes` | `game-factory-orchestrator` | brief、委派、失败 triage |
| `prompt-crafter` | `hermes` | `game-factory-prompt-crafter` | `prompt craft` → plan JSON |
| `image-generator` | `pipeline` | `game-factory-image-generator` | `image generate --plan-file` |
| `video-generator` | `pipeline` | `game-factory-video-generator` | `video generate` + 拆帧/抠图链 |
| `godot-assembler` | `pipeline` | `game-factory-godot-assembler` | `godot assemble` / `import-sprites`（**不写 GDScript**） |

---

## 执行器选择

| Executor | 适用场景 | 实现 |
|----------|----------|------|
| **`pipeline`** | 批量资产 + Godot 组装（无 LLM） | `pipeline run` subprocess |
| **`hermes`** | 多会话委派、brief、prompt craft | `hermes install` + 单 skill 会话 |
| **`cursor`** | 本地 Cursor Agent | 读 `resources/skills/<role>/` 或 `.cursor/rules` |
| **`codex`** | `codex exec` 一次性任务 | `AGENTS.md` + Hermes skill |

默认配置见 `resources/agents.example.json`；用户可在 `~/.gamefactory/config.json` 的 `agents` 段覆盖。

```json
{
  "agents": {
    "orchestrator": { "executor": "hermes", "skill": "game-factory-orchestrator" },
    "godot-assembler": { "executor": "pipeline", "skill": "game-factory-godot-assembler" },
    "image-generator": { "executor": "pipeline", "skill": "game-factory-image-generator" }
  }
}
```

---

## CLI：解析路由

```bash
cd cli
python gamefactory.py agents show
python gamefactory.py agents resolve --role godot-assembler
```

输出包含 `executor`、`skill`（Hermes 包名）、`skills_dir`（Cursor 可读 skill 源）。

---

## 推荐混排流程

```mermaid
flowchart TB
    subgraph main [MainAgent]
        Hermes[Hermes / Cursor / Codex]
    end
    subgraph workers [Workers]
        PC[prompt-crafter]
        PR[pipeline run]
    end
    subgraph cli [CLI]
        IG[image-generator]
        VG[video-generator]
        GA[godot-assembler]
    end
    Hermes -->|brief / prompts| PC
    Hermes -->|assets + Godot| PR
    PR --> IG
    PR --> VG
    PR --> GA
    Hermes -->|异常 / 手动| GA
```

1. **Phase A** — 主 Agent + `prompt-crafter`：定 brief、`prompt craft` → `plans/`
2. **Phase B** — `pipeline plan` + `pipeline run`（默认 `--jobs 4`）：静图 / 视频 / matte；Pass 3 含 `godot.assemble`
3. **Phase C** — 失败时主 Agent triage；`exit 2` → 改 plan → `pipeline reset` → 再 `run`
4. **Phase D（可选）** — 资产已就绪但未走 pipeline Godot 任务时：

```bash
python gamefactory.py godot assemble --assemble-file ../plans/godot_prison_demo.json
python gamefactory.py godot validate --project ../games/prison-demo
```

---

## godot-assembler 边界

- **做**：从 handoff 复制 PNG → `res://`，生成 `SpriteFrames` `.tres`，挂载 C# `Player.cs`（Godot 4 .NET 模板）
- **不做**：GDScript、LLM 写 C#、Godot MCP
- **入口**：`godot assemble --assemble-file`（`consumer_role: godot-assembler`）
- **子命令**：`godot import-sprites`（单资产调试）

Handoff 示例：`plans/godot_prison_demo.json`

---

## 相关文档

- [`docs/AI-HANDOFF.md`](AI-HANDOFF.md) — 命令速查、配置、抠图规则
- [`docs/HERMES-CODEX.md`](HERMES-CODEX.md) — Hermes 安装与 terminal 约定
- [`AGENTS.md`](../AGENTS.md) — Codex 速查
- [`resources/skills/godot-assembler/`](../resources/skills/godot-assembler/) — skill 源文件
