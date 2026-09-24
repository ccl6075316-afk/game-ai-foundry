# Brainstorm: Pure Workflow Toolkit

> **删除说明：** 文中出现的桌面客户端、内置会话与品牌专属运行时均为已移除对象，不是当前操作入口。

## Problem Statement

The project currently mixes three concerns: deterministic game-production tooling, an embedded GUI, and multiple agent runtimes. The embedded GUI and agent-specific orchestration make external-agent integration expensive and difficult to maintain. The project must become a pure CLI/workflow toolkit whose pipeline and core design contracts are consumed by external agents.

## Assumptions (Explicit)

- The current `master` branch remains untouched; all changes occur on `codex/pure-workflow-toolkit`.
- The GUI layer is removed from this branch rather than retained as an optional viewer.
- Built-in colleague sessions, GUI roster/session state, Pi RPC, Hermes/Cursor/Codex runtime management, ACP orchestration, and GUI-side auto-repair are out of scope for the toolkit.
- The Python CLI remains the deterministic execution engine.
- `brief`, scene, system, asset, production, pipeline, Godot assembly, validation, and test concepts remain as first-class CLI/data contracts.
- External agents own conversation, planning, decisions, dispatch, and failure interpretation.
- The project owns command execution, file persistence, schema validation, DAG execution, retries, and machine-readable reports.
- Existing projects, generated assets, and pipeline artifacts are not rewritten merely to remove the GUI.
- Provider/API configuration remains supported because image and video generation still require external APIs; agent-executor configuration is removed.
- Existing skill documents are retained as external-agent protocols when they describe workflow usage; runtime-specific skill hooks are not retained as internal execution paths.

## Domain Language

- **Toolkit**: the repository as a deterministic CLI/workflow service for external agents.
- **External agent**: any agent outside this repository that reads project state, invokes commands, and submits results.
- **Brief**: frozen design contract containing project, scene, system, asset, and animation requirements.
- **Production document**: engineering blueprint derived from Brief, including Godot tasks and acceptance criteria.
- **Pipeline manifest**: dependency graph of deterministic production tasks.
- **Workflow stage**: a coarse externally visible phase such as design, assets, assemble, implement, or validate.
- **Handoff**: structured file describing work assigned to an external agent.
- **Progress**: persistent machine-readable project state.
- **Validation report**: structured result of an acceptance command.
- **Skill**: an external-agent-facing protocol document that maps user intent to toolkit commands and file contracts.

## Functional Requirements

### F1 — Remove embedded GUI

- Delete the GUI application and its Electron/React runtime from the toolkit branch.
- Remove GUI-specific startup scripts, packaging metadata, and GUI-only documentation from the default entry path.
- Do not leave hidden GUI orchestration as a required dependency of the CLI.

### F2 — Remove built-in agent runtime

- Remove built-in colleague sessions, roster management, ACP session managers, Pi RPC session management, and internal agent dispatch.
- Remove configuration and commands whose sole purpose is selecting or operating an embedded agent executor.
- Preserve deterministic commands that external agents need to invoke.
- Preserve read-only context and diagnostic commands that help an external agent inspect a project.

### F3 — Preserve the core production engine

- Preserve Brief validation/export and the Brief ↔ scene/system/asset contracts.
- Preserve `production derive`, `production validate`, and Production Delta operations.
- Preserve pipeline plan, run, status, reset, retry, and auto-repair behavior needed for deterministic asset production.
- Preserve image/video generation, matting, frame processing, Godot scaffold/assemble/validate, and test commands.
- Preserve structured exit codes and JSON output for external-agent automation.

### F4 — Expose a stable external-agent workflow contract

- Provide one discoverable workflow entry point or a documented equivalent command set.
- Every workflow command must identify its input files, output files, current stage, completion state, failure kind, and suggested next action.
- Workflow state must be persisted as files inside the project; it must not depend on GUI memory or chat history.
- External agents must be able to resume from persisted state after a process restart.

### F5 — Keep external-agent skills protocol-only

- Skills must describe which commands to run, which files to read/write, and which failures require human review.
- Skills must not duplicate implementation logic already owned by the CLI.
- Skills must not assume a particular embedded agent runtime.
- Skills must define a minimal contract for context discovery, execution, status reading, validation, and reporting.

### F6 — Preserve master isolation

- `master` must remain unchanged.
- The transformation branch must be independently buildable and testable.
- No generated release artifacts or unrelated project outputs may be committed as part of the transformation unless explicitly required by a later implementation task.

## Non-Functional Requirements

- CLI commands remain usable without GUI, Node, Electron, or an embedded agent process.
- All externally important outputs support JSON mode.
- File formats remain versionable and human-readable.
- Failure behavior remains deterministic: retryable failures, validation failures, blocked dependencies, and completed tasks are distinguishable.
- Existing tests for retained CLI behavior continue to pass.
- The default documentation entry point describes external-agent usage, not GUI colleague usage.
- The branch has a clear migration path; deleting GUI/agent runtime must not break retained pipeline commands.

## Security Concerns

- External agents may request shell or file mutations; retained commands must keep explicit confirmation or allowlist boundaries where destructive operations exist.
- API credentials remain sensitive configuration and must not be embedded in skill documents or committed project files.
- External agents must not be able to bypass Brief/Production/Pipeline validation by writing arbitrary state through a GUI-only path.
- Removing embedded runtimes must not silently widen access to `shell`, config mutation, or project-file writes.
- Skill documents must state whether a command is read-only, state-changing, destructive, or network-backed.

## Open Questions

- None blocking this requirements document: this branch chooses protocol-only skills, removes embedded runtimes, and retains deterministic CLI commands.

## Success Criteria

- `master` has no changes after the work begins on the dedicated branch.
- The branch contains no runnable GUI application and no embedded colleague/ACP/Pi/Hermes/Codex/Cursor orchestration path.
- A fresh external agent can inspect a project, discover the workflow, run a pipeline stage, read failure/status JSON, and submit or resume work using only CLI commands and skill documents.
- Brief, scene, system, asset, Production, pipeline, Godot, validation, and test contracts remain available through deterministic commands.
- Retained unit tests pass, and a smoke workflow can run without starting GUI or an embedded agent.
- Documentation describes the project as an external-agent toolkit rather than an AI-company GUI.
