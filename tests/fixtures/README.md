# Test fixtures (dev / CI only)

These files support unit tests and local E2E smoke runs. They are **not** release defaults and do not ship as game templates.

| Path | Purpose |
|------|---------|
| `briefs/` | Sample brief JSON (incl. legacy prison demos, e2e smoke) |
| `plans/prison/` | Archived plan/handoff artifacts from prison walk experiments |
| `manifests/` | Frozen pipeline manifest snapshots for smoke tests |

Run E2E smoke (requires API keys):

```bash
cd cli
python gamefactory.py pipeline plan \
  --brief ../tests/fixtures/briefs/e2e-smoke-brief.json \
  -o ../pipeline/e2e-smoke.json \
  --output-dir ../output/e2e-smoke \
  --godot-project ../games/e2e-smoke \
  --no-game-dev
python gamefactory.py pipeline run --manifest ../pipeline/e2e-smoke.json --run-prompts --jobs 2
```
