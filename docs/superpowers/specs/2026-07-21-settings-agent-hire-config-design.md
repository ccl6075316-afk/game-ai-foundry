# Design: Settings Agent presets + hire/chat config

**Date:** 2026-07-21  
**Status:** approved by user（「没问题」）  
**Engineering fact source:** [`docs/anvil/brainstorms/2026-07-21-settings-agent-hire-config.md`](../../anvil/brainstorms/2026-07-21-settings-agent-hire-config.md)

## Summary

- Settings: **Provider | Agent | Local** — remove Roles.
- Agent tab: presets per tool (Pi / Hermes / Codex / Cursor), not per job title.
- Hire dialog (required fields by role kind C) + in-chat config; inherit Agent presets; instance edits do not write back presets.
- Runtime authority remains `agents.instances`; new `agents.executors` for tool presets.

## Out of scope

Save-as-default from chat; Cursor third-party keys; Pi/Electron Node runtime.
