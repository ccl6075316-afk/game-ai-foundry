# Vision analysis

Use when `test run` is too heavy or you already have a screenshot.

## Analyze vs brief

```bash
python gamefactory.py test analyze \
  --image ../output/my-game/validation/screenshots/latest.png \
  --brief ../resources/my-game-brief.json \
  -o ../output/my-game/validation/analysis.json
```

## Custom criteria file

```json
[
  {
    "source": "design_doc.acceptance_criteria[0]",
    "criterion": "Player can see the forest gate and a slime enemy at start."
  }
]
```

```bash
python gamefactory.py test analyze \
  --image path/to.png \
  --criteria-file criteria.json
```

## What to check visually

| Layer | Look for |
|-------|----------|
| Build | N/A — use `godot validate` first |
| Scene | Main scene loaded; no grey void / missing textures |
| Functional hints | HUD, player sprite, enemies visible if brief says so |
| Art | Matches `art_direction` in brief |

Model returns JSON: `status`, `summary`, `failed_criteria`, `visual_notes`.

**Exit 2** when `status` is `failed` — hand off to orchestrator, not godot-developer directly unless dispatched.
