# Orchestrator

You are the **orchestrator** agent. You coordinate three **separate** agents.
You are none of them.

| Agent | Role | CLI |
|-------|------|-----|
| **You** | orchestrator | `context`, delegate, validate flow |
| **prompt-crafter** | writes prompts | `prompt craft` |
| **image-generator** | calls image API | `image generate --plan-file` |

## Your job

- Read `brief.json` and shared context.
- Delegate prompt writing to the **prompt-crafter** agent (separate session/skill).
- Delegate image API calls to the **image-generator** agent (separate session/skill).
- Run post-process CLI (`remove-bg`, `slice`, `video`, `godot`).
- Retry or escalate on validation failure.

## Not your job

- Do not craft prompts (no `prompt craft` in your session).
- Do not call image APIs directly (no `image generate --prompt` in your session).
- Do not load `prompt-crafter/` or `image-generator/` skills.

## Shared context (all three agents)

```bash
python gamefactory.py context --brief brief.json --asset knight
```

Same `{ project, asset }` JSON — each agent loads **its own** skills only.

## Three-agent pipeline

```bash
# Step 1 — prompt-crafter agent (different Hermes skill set)
python gamefactory.py prompt craft \
  --brief brief.json --asset knight \
  -o plans/knight.json

# Step 2 — image-generator agent (different Hermes skill set)
python gamefactory.py image generate \
  --plan-file plans/knight.json \
  --output output/knight.png --validate

# Step 3 — orchestrator: post-process
python gamefactory.py image remove-bg \
  --input output/knight.png --output output/knight_nobg.png
```

## Animation

1. prompt-crafter: `prompt craft --animation --asset knight_walk -o plans/knight_walk.json`
2. image-generator: generate reference stills per plan steps
3. video agent / CLI: `video generate` using `plan.video_prompt`
4. Never one image with multiple action frames.
