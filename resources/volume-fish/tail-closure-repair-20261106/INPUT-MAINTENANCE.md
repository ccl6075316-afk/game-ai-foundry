# Complete root domains and the preserved-auxiliary 077 adapter

The eight recovered domains (`atlantic_salmon`, `red_emperor`, `sea_bass`, `rainbow_trout`, `carp`, `mahi_mahi`, `silver_arowana`, `african_catfish`) now bind the installed canonical source and GLB hashes. Each domain retains every current source fin point, its rest coordinate and directed triangles, the complete root membership, original anatomical parameters, and previous-to-current identities. Each accompanying `source-identity.validation.json` records the actual source/GLB comparison. These are maintained inputs, not replacement physical acceptance reports.

For the packed fish, `_FOUNDRY_SOURCE_VERTEX` is the global source identity. Current wall color UV is never an anatomical coordinate. Original cap UV/t and wall inheritance are retained in the domain. The earlier four fish's noncaudal native 17-pixel band remains distinct from `source_t_max`, the normalized membership parameter; the historical `1e-7` selection epsilon is explicit. The full original root bank remains represented, and new descendants inside that band are included. Current root points were read from the installed sources, including the final support corrections.

For ordinary sources, mesh vertex indices are the source identity. Native source u/v/t are retained when present. Silver arowana's original u/v and baseline remain unknown; its persisted t and original `.065` complete band remain authoritative. Mahi's reconstructed tail uses its frozen original-cap ancestry parameter; its separately retained float source t differs by at most `1.1648822462184683e-7`. That difference is disclosed rather than silently changing the validated root membership.

Recovery records identify retained original images, profiles, native baselines/crops, and their hashes. Historical model/source and retired authoring paths are marked as provenance rather than replayable inputs. Current values are embedded in the domains, so maintaining the current roots does not require recovering retired experiments.

## Body validation

Use `resources/scripts/volume-fish/portable/validate_preserved_auxiliary_body.py` for an explicit existing eye/barbel inventory over an independently complete `Closed_body`. The original `validate_standalone_body.py`, `capture_standalone_body.gd`, body closure/opacity calculations, and same-pose zero-missing-pixel algorithm are unchanged. The adapter counts every body, fin and auxiliary triangle; only the complete underlying body owns the body-coverage test.

The body plan retains the original standalone fields and adds:

- `baseline_inventory` and `baseline_inventory_sha256`: an immutable manifest containing the baseline species/model identity.
- `baseline_model` and `baseline_model_sha256`: actual readable baseline bytes. An explicitly declared snapshot uses `baseline_snapshot_root/<species>/baseline.glb` and `baseline_snapshot_path`; its SHA must still equal the manifest identity.
- `fin_inventory_plan` and its SHA: the complete frozen current fin inventory and candidate identity.
- `decorative_overlays`: each existing eye/barbel declares `kind: unchanged_baseline_auxiliary`, `underlying_body: Closed_body`, and its identical `baseline_name`.
- All source, model, manifest, runtime and helper dependencies in `frozen_inputs`.

The adapter independently compares actual baseline/current position, normal, UV, directed triangles, effective named weights, rig/bind/hierarchy, material bindings and actual non-tail texture payloads. Material defaults may be expanded only to their specified equivalent values; actual minification, magnification, clamp/repeat changes remain errors. The separate piranha 077 partition preserves every source array and triangle while assigning the existing `eyes` parts to auxiliary opacity responsibility. Its three original `Closed_body` surfaces remain complete.

The two recorded ordinary-source exports have a narrowly bound serialization exception, not a weight tolerance. Their original/current source groups are identical. Blender's stock `weight <= .0001` filtering and float32 sum/division independently reproduce every emitted named weight exactly. The proof binds the exact old/new model and source hashes and each expected encoded part signature; any additional unpredicted ULP is rejected. The actual emitted weights are explicitly reported as non-byte-exact against the old GLB. No physical or GPU threshold changes.

```sh
FOUNDRY_MANUAL_RENDER=1 .venv/bin/python resources/scripts/volume-fish/portable/validate_preserved_auxiliary_body.py --game projects/fishing-2d/game --godot /path/to/Godot --plan /absolute/path/body.plan.json --output /absolute/path/body077
```

`auxiliary-body-adapter.validation.json` records the unchanged kernel comparison, an actual positive current inventory inspection, and rejected wrong-auxiliary, missing-body-surface and unpredicted-weight controls. It also retains compact actual 16-view GPU results and transparent-body negative results. Historical baseline paths were replaced on installation; a historical rerun requires obtaining the exact baseline bytes by SHA. No old model package or dense capture set is retained here.
