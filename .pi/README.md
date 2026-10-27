# Secondary model tooling in Game AI Foundry

Pi discovers `extensions/fish-asset-tools.ts` in this project. It exposes two read-only tools:

- `inspect_blender_fish` opens a workspace `.blend` or `.glb` with Blender and returns mesh, UV, material, weight, rig and action counts.
- `inspect_godot_fish` starts Godot headlessly and reads the actual imported fish GLB arrays, materials, skeleton and animations for one species. It does not invoke runtime shape builders.

The tools call the local Blender/Godot CLIs directly. Pi does not include built-in MCP; a separate MCP server is unnecessary for these two deterministic inspections. Its built-in `read`, `grep`, `find`, `ls`, `edit`, `write` and `bash` tools remain available when explicitly enabled. On this Windows host, `C:/Users/admin/.pi/agent/settings.json` sets `shellPath` to `E:/Git/bin/bash.exe` so Pi's `bash` tool can launch Blender, Godot and the repository CLI.

Example read-only calls from PowerShell (quote comma-separated tool names):

```powershell
pi --provider deepseek --model deepseek-v4-flash --tools 'read,grep,find,ls,inspect_blender_fish,inspect_godot_fish' -p 'Inspect one fish and report evidence.'
pi --provider moonshot --model kimi-k3 --tools 'read,grep,find,ls,inspect_blender_fish,inspect_godot_fish' -p 'Inspect one fish and report evidence.'
```

For bounded editing tasks, explicitly add `edit`, `write` and, when a command is needed, `bash`. Keep the repository's AGENTS.md and fish SOP in context for production work. Use `--no-context-files --no-session` only for tiny isolated probes; it omits required project instructions.

Verified on 2026-10-27: both models called `read`; Kimi K3 called `edit` on an isolated `work/` probe and launched Blender 5.0.1 through `bash`; DeepSeek launched Godot 4.6.1 through `bash`; DeepSeek called `inspect_godot_fish` and Kimi K3 called `inspect_blender_fish` on the African catfish assets. The two inspectors returned 18 actual mesh nodes. These checks prove tool access, not autonomous fish acceptance.

Production experience through 2026-10-28: bound each model to one fish and one testable question. DeepSeek supplied useful salmon scripts but required review; its bluegill tool call produced malformed DSML and no edit. Kimi K3's salmon tool task stalled beyond five minutes and was interrupted, though short review identified the small-weight export problem. Both models' brown trout reviews speculated about separate jaw/head meshes that the source and runtime inventory disproved. Inspect the actual Blender/Godot assets and cold-load output before applying advice. No measured token savings were recorded. The six-fish case record is `projects/fishing-2d/docs/3d-fish/STATIC-MERGE-20261028.md`.
