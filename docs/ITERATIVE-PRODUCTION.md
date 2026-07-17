# Game AI Foundry — Iterative Production Contract

| | |
|--|--|
| **读者** | Host、全 Worker、验收方 |
| **侧重** | 设计 vs 施工、Change Request、切片、验收哲学、角色 **权责** |
| **不写** | CLI 命令表、Hermes 安装、抠图参数、里程碑 % |
| **姊妹文档** | 操作 → [`AI-HANDOFF.md`](AI-HANDOFF.md) · 角色路由 → [`AGENT-ROUTING.md`](AGENT-ROUTING.md) · 索引 → [`README.md`](README.md) |

## 0. Core Rule

Game AI Foundry must separate **what the player should experience** from **how the project is built**.

```text
User conversation
  -> Design Doc        # human-readable design intent and validation basis
  -> Production Doc    # machine-readable construction spec
  -> Pipeline Manifest # executable asset/Godot DAG
  -> Godot Project
  -> Validation Report
  -> next Change Request
```

The user should mostly describe play experience. AI fills production details. Workers execute only the current documents.

### 0.1 Relationship to `brief.json` (today)

The repo already ships a **frozen export contract**. Until Design Doc and Production Doc are split into separate files, map concepts like this:

| ITERATIVE concept | Current repo | Status |
|-------------------|--------------|--------|
| Design Doc | `brief.project` — `gameplay_loop`, `session_goal`, `description`, win/fail intent | Embedded in brief |
| Production Doc | Full `brief.json` after `brief export` (`brief_meta`) | ✅ `brief validate` / `export` |
| Pipeline Manifest | `pipeline/{slug}.json` | ✅ `pipeline plan` |
| Assets ledger | `output/{slug}/assets-manifest.json` | ✅ pipeline + assemble |
| Change Request / Production Delta | — | 📋 target; see §1.3–1.4, §7 |
| Validation Report | — | Partial: `godot validate` + manual playtest |
| `project-state.json` | — | 📋 recommended in §7 |

**MVP rule:** `brief.json` is the single frozen contract for workers today. Host interprets user intent into brief updates; iteration after demo follows §3.2 (Change Request → brief delta → `pipeline plan --merge` → `run`).

```text
Today:     brief.json (frozen) ──► pipeline manifest ──► output/ + games/
Target:    design.json + production.json ──► export ──► same pipeline
Iteration: changes/*.json + production-delta ──► plan --merge ──► run
```

## 1. Document Types

### 1.1 Design Doc

The Design Doc describes the game from the player's point of view. It is used for user confirmation and validation.

It should answer:

- What is the fantasy?
- What does the player do moment to moment?
- What is the core loop?
- What is the first playable slice?
- What are the win/fail conditions?
- What should the pacing, difficulty, and feel be?
- What visual/audio mood should the result match?

Example shape:

```json
{
  "design_doc": {
    "title": "Magic Prince",
    "pitch": "A light 2D fairy-tale platformer.",
    "player_fantasy": "Play as a young prince crossing an enchanted forest with jumps and magic.",
    "opening_moment": "The prince starts at the forest gate with a low platform and a slow slime ahead.",
    "core_loop": [
      "read the obstacle",
      "jump or cast magic",
      "avoid enemies",
      "collect star fragments",
      "reach the portal"
    ],
    "win_condition": "Collect at least five star fragments and enter the portal.",
    "fail_condition": "Health reaches zero or the player falls out of the level.",
    "difficulty_curve": "First 20 seconds teach jumping; then enemies, moving platforms, and narrower gaps appear.",
    "feel_targets": [
      "forgiving jumps",
      "short 2-3 minute run",
      "bright fairy-tale tone"
    ],
    "acceptance_criteria": [
      "Player can move, jump, collect, and reach the portal.",
      "The opening scene matches the described forest gate moment.",
      "The game feels forgiving rather than punishing."
    ]
  }
}
```

The Design Doc is not a place for low-level values unless the user explicitly cares about them.

Do not ask the user for `jump_velocity`, `collision_size`, `pivot`, `tile_size`, or similar construction details by default.

### 1.2 Production Doc

The Production Doc translates the Design Doc into concrete work for pipeline and code.

It should answer:

- Which genre preset is used?
- What assets must be generated?
- What source/display/collision sizes are required?
- Which maps/scenes are needed?
- Which runtime systems are needed?
- Which Godot tasks must be implemented?
- Which acceptance and regression checks must pass?

Example shape:

```json
{
  "production_doc": {
    "genre": "2d_platformer",
    "viewport": { "width": 960, "height": 540 },
    "world": {
      "tile_size": 16,
      "gravity": 980,
      "level_length": 2400,
      "ground_y": 480
    },
    "player": {
      "asset": "magic_prince",
      "move_speed": 180,
      "jump_velocity": -420,
      "health": 3,
      "hitbox": { "width": 28, "height": 44 }
    },
    "assets": [
      {
        "name": "magic_prince",
        "type": "character",
        "usage": "player",
        "source_size": { "width": 1024, "height": 1024 },
        "display_size": { "width": 64, "height": 64 },
        "collision_size": { "width": 28, "height": 44 },
        "anchor": "bottom_center",
        "animations": ["idle", "run", "jump", "cast"]
      }
    ],
    "godot_tasks": [
      "Implement PlayerController with left/right movement and jump.",
      "Bind magic_prince idle/run/jump/cast animations.",
      "Create collectible star fragments.",
      "Create portal win trigger.",
      "Add HUD for health and collected fragments."
    ],
    "validation": {
      "acceptance_criteria": [
        "main scene loads",
        "player can move and jump",
        "player can collect star fragments",
        "portal triggers win state"
      ],
      "regression_checks": []
    }
  }
}
```

The Production Doc is allowed to contain technical values inferred by AI or genre presets. These values must be traceable to the Design Doc or default presets.

### 1.3 Change Request

After a demo or validation run exists, new user intent must enter through a Change Request.

Example:

```json
{
  "change_request": {
    "source": "user_feedback",
    "user_intent": "Add a forest map with a charging boar enemy. Clearing it unlocks double jump.",
    "design_delta": {
      "new_location": "forest",
      "new_enemy": "charging boar",
      "new_reward": "double jump",
      "new_play_moment": "The player survives a more aggressive forest encounter and earns stronger movement."
    }
  }
}
```

Change Requests are not executed directly. The host must translate them into Production Doc deltas and task dispatch.

### 1.4 Production Delta

A Production Delta is the construction plan for one Change Request.

```json
{
  "production_delta": {
    "change_id": "002-add-forest-double-jump",
    "asset_tasks": [
      "forest_background",
      "boar_enemy",
      "double_jump_icon"
    ],
    "godot_tasks": [
      "Add Forest scene connected from current level exit.",
      "Add BoarEnemy patrol and charge behavior.",
      "Add double jump ability gated by forest completion.",
      "Update HUD to show ability unlock."
    ],
    "preserve": [
      "existing player movement except adding optional double jump",
      "existing first-level portal logic",
      "existing health HUD"
    ],
    "do_not_touch": [
      "unrelated input mappings",
      "existing asset import paths unless required"
    ],
    "acceptance_criteria": [
      "Player can enter the forest from the existing level.",
      "Boar patrols and charges when the player is near.",
      "Double jump is unavailable before clearing the forest.",
      "Double jump is available after the forest reward.",
      "Existing first-level win condition still works."
    ]
  }
}
```

## 2. Role Boundaries

Do not create a vague all-powerful "extender" worker role.

Iteration is a **host-orchestrated workflow**, not a new worker that invents requirements.

| Role | Owns | Must not do |
|------|------|-------------|
| host / orchestrator | user intent, Design Doc updates, Production Doc deltas, dispatch, triage, validation decisions | write large Godot features directly when worker dispatch is available |
| prompt-crafter | prompt plans from Production Doc / Production Delta | invent gameplay or assets outside the doc |
| image-generator | image generation from plan files | decide what assets should exist |
| video-generator | animation/video generation and frame processing | decide animation needs outside the doc |
| godot-assembler | import generated assets into Godot and update bindings | implement gameplay logic |
| godot-developer / coder | modify existing Godot C# project according to Production Doc / Production Delta | redesign features, expand scope, or rewrite unrelated systems |
| tester / validator | test against Design Doc and Production Doc criteria | change implementation targets during testing |

**tester / validator** is a **seventh Hermes skill** (`game-factory-tester`). CLI: `test run` / `test analyze` / `godot screenshot`.

Coder rule:

> godot-developer is a construction worker, not product owner. It must code according to the current Production Doc, Production Delta, assets-manifest, and validation criteria.

## 3. Standard Lifecycle

### 3.1 New Project

```text
1. Host asks user about play experience, not construction details.
2. Host drafts Design Doc (today: GUI `brief chat` / host-chat；CLI 兼容 brainstorm).
3. User confirms → brief export (`brief_meta` frozen).
4. prompt-crafter: prompt craft → plans/*.json
5. pipeline plan → pipeline/{slug}.json
6. pipeline run --jobs N → image / video / matte / godot.assemble
7. godot dev-context → plans/dev_*.json
8. godot-developer implements C# from dev-context.
9. Host / tester validates against Design + Production criteria.
```

**Commands** → [`AI-HANDOFF.md`](AI-HANDOFF.md) §5 · **Role routing** → [`AGENT-ROUTING.md`](AGENT-ROUTING.md)

### 3.2 Iteration After Demo

```text
1. User feedback or validation failure arrives.
2. Host writes Change Request.
3. Host updates Design Doc if the user intent changes play experience.
4. Host writes Production Delta.
5. Host dispatches workers:
   - prompt-crafter for new/changed asset plans
   - pipeline run for assets
   - godot-assembler for imports
   - godot-developer for C# changes
6. tester validates new acceptance criteria plus regression checks.
7. Host records Validation Report and decides next loop.
```

Workers must not skip back to user intent or reinterpret the design. They read the current docs and execute.

## 4. Complex Games

Complex games require slicing. Do not turn a large vision into one giant Production Doc.

Use this hierarchy:

```text
Vision Doc      # full imagined game/world
Slice Design    # current playable slice, user-confirmable
Production Doc  # current slice construction spec
Change Request  # one iteration of intent
Production Delta # one iteration of construction
```

For RPG/open-world/metroidvania-like ideas, ask scope questions first:

- What is the full world fantasy?
- What is the first playable slice?
- Which 1-3 locations must exist first?
- What is the first quest line?
- What level or upgrade range should the first slice cover?
- Which systems are mandatory now and which can wait?

Example complex scope:

```json
{
  "vision_doc": {
    "title": "Ashen Kingdom",
    "genre": "topdown_action_rpg",
    "fantasy": "Explore a ruined kingdom, take quests, level up, and uncover the disaster."
  },
  "slice_design": {
    "slice_id": "001-village-forest-mine",
    "locations": ["ashen_village", "deadwood_forest", "old_mine"],
    "quest_lines": ["missing_miners"],
    "player_level_range": [1, 3],
    "duration_target": "10 minutes",
    "systems": ["movement", "combat", "dialogue", "quest_log", "leveling_1_to_3"]
  }
}
```

The Production Doc must only build the current slice. Future regions, factions, equipment systems, and long-term progression can stay in Vision Doc until selected for a slice.

## 5. Asset Size And Usage

Asset specs should be derived from usage. Ask the user about use and feel; infer the technical sizes.

Recommended production fields:

```json
{
  "name": "hero",
  "type": "character",
  "usage": "player",
  "source_size": { "width": 1024, "height": 1024 },
  "display_size": { "width": 64, "height": 64 },
  "collision_size": { "width": 28, "height": 44 },
  "anchor": "bottom_center",
  "pivot": { "x": 0.5, "y": 1.0 },
  "safe_padding": 8
}
```

Default usage rules should live in genre presets. Example defaults:

| usage | display_size | anchor | collision |
|-------|--------------|--------|-----------|
| player | 64x64 | bottom_center | 28x44 |
| enemy | 48x48 | bottom_center | 32x28 |
| projectile | 16x16 | center | 12x12 |
| pickup | 24x24 | center | 20x20 |
| ui_icon | 32x32 | center | none |
| background | viewport or larger | top_left | none |

These are defaults, not user-facing questions.

## 6. Validation

Validation must look back to the Design Doc, not only to compile/build success.

Minimum validation layers:

- Build validation: Godot/.NET build succeeds.
- Scene validation: main scene loads.
- Functional validation: controls, win/fail, core loop work.
- Visual validation: screenshot/video matches important design criteria.
- Regression validation: existing accepted behavior still works after a Change Request.

Validation Reports should say which document rule failed.

Example:

```json
{
  "validation_report": {
    "status": "failed",
    "failed_criteria": [
      {
        "source": "design_doc.acceptance_criteria[2]",
        "criterion": "The game feels forgiving rather than punishing.",
        "evidence": "Player misses short jumps frequently due to strict jump timing.",
        "recommended_change": "Add coyote time and jump buffer in Production Delta."
      }
    ],
    "regressions": []
  }
}
```

The host decides the next Change Request or Production Delta. The tester does not alter implementation goals.

## 7. Project State

After the first playable project exists, maintain project state as files, not chat memory.

Recommended local project structure:

```text
resources/<slug>/
  vision.json
  slices/
    001.design.json
    001.production.json
  changes/
    002-add-fireball.change.json
    002-add-fireball.production-delta.json
  validation/
    001-report.json
    002-report.json

games/<slug>/
  gamefactory/
    project-state.json
    applied-changes.json
```

`project-state.json` should summarize implemented systems, scenes, scripts, input actions, known extension points, and regression checks.

Workers should prefer these files over conversation memory.

## 8. Non-Negotiable Rules

1. User-facing questions should focus on play experience, not implementation numbers.
2. Design Doc describes desired experience and validation basis.
3. Production Doc describes implementation details for workers.
4. Complex games must be sliced; build only the current slice.
5. After demo, every change starts as a Change Request and becomes a Production Delta.
6. Host/orchestrator owns interpretation and dispatch.
7. Coder/godot-developer only implements documented tasks.
8. Workers must preserve existing accepted behavior unless the Change Request explicitly changes it.
9. Validation must check both new acceptance criteria and old regressions.
10. Chat memory is not a contract; documents are the contract.

---

## 9. Related documents

| Document | Focus |
|----------|--------|
| [`docs/README.md`](README.md) | Documentation index |
| [`AI-HANDOFF.md`](AI-HANDOFF.md) | CLI, brief schema, matting (中文) |
| [`AGENT-ROUTING.md`](AGENT-ROUTING.md) | Six roles, executors |
| [`../ROADMAP.md`](../ROADMAP.md) | Milestones, backlog |
| [`../AGENTS.md`](../AGENTS.md) | Codex one-pager |

