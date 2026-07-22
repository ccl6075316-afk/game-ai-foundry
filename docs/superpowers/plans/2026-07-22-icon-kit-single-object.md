# icon_kit Single-Object + Bulk Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand `icon_kit` into N single-object image generates (no grid slice); route kit items and `generate_tier: bulk` through `image.bulk_model`.

**Architecture:** Keep kit shell in brief; `pipeline_manifest` emits per-item prompt.craft + image.generate + trim/remove-bg; CLI `--model` already exists — pass bulk model on those commands. Slug item names for stable artifact paths.

**Tech Stack:** Python CLI (`brief`, `pipeline_manifest`, `asset_pipeline`, `prompt_cmds`, `gamefactory` image generate).

## Global Constraints

- No `image.slice` for icon_kit.
- `image.bulk_model` falls back to `image.model` with log if unset.
- `generate_tier: bulk` on any still also uses bulk_model.
- Do not rewrite user brief into N assets.
- icon_kit still does not get style img2img (unchanged).

## File map

| File | Change |
|------|--------|
| `cli/brief.py` | `generate_tier`; slug helper; soften grid validate |
| `cli/image_model_route.py` (new) | resolve default vs bulk model |
| `cli/asset_pipeline.py` | icon_kit meta = per-item pipeline (no slice); single-item prompt |
| `cli/pipeline_manifest.py` | expand kit tasks; `--model` on generate |
| `cli/prompt_cmds.py` | `--item` for kit craft |
| `resources/config.example.json` | `bulk_model` |
| skills + example brief | docs |

---

## Task 1: Slug + generate_tier + model route

- [ ] Tests for `slugify_item_label`, `resolve_image_model_for_tier`, AssetSpec.generate_tier
- [ ] Implement helpers + wire AssetSpec.from_dict
- [ ] Soften icon grid validation (warn/ignore, not fail on cells < items)

## Task 2: Pipeline expand icon_kit

- [ ] Test: plan for kit has N generate, zero slice; paths contain slug
- [ ] Rewrite icon_kit branch in asset_pipeline + `_static_asset_tasks` / dedicated expander
- [ ] Pass `--model <bulk>` when tier is bulk

## Task 3: Prompt craft `--item` + skills/docs

- [ ] `prompt craft --item sword` builds single-object plan
- [ ] Update prompt-crafter / image-generator / example brief / config.example
- [ ] Update Spec Source Of Truth line to this plan

## Task 4: Verify + commit

- [ ] `python -m unittest` relevant suites
- [ ] Commit + merge main + push
