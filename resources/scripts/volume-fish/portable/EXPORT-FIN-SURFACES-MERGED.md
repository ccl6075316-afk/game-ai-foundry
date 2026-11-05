# Opt-in complete actual-pose fin surface export

Use `export_fin_poses_merged.gd` instead of `export_fin_poses.gd` only for a new/current candidate that requires complete same-name multi-surface sampling. The original file and its pose schedule, root selection, control limits, loaders and packed-part selection remain unchanged. This sidecar hard-pins base SHA `0dffe432a891ca54447c6138954c05c5ed0a6b5ab1bb9760e808fdac53ccaa99` and refuses a different base.

The inherited `prepare()` still validates full body/fin selection and nonempty root mapping. After that, the sidecar validates an explicit, model-bound inventory. Its `sample()` computes each surface with that surface's own actual skin bindings, inverse bind poses and joint transforms **before** concatenating world-metre vertices. It offsets triangle indices by the preceding vertex count and accumulates root vertices, all seven edge samples, root counts, diagnostic outward gains and native-rest arrays. Different native mesh binding spaces are never combined. Source/UV/weights/assets are not modified.

Add this declaration to each plan item (include the body and every logical fin, not just one failing fin):

```json
"surface_merge_inventory": {
  "model_sha256": "the same current item.model_sha256",
  "parts": {
    "Closed_body": {"surface_count": 2, "triangles": 990},
    "Example_fin": {"surface_count": 2, "triangles": 108}
  }
}
```

The example counts are illustrative, never species defaults. Mandatory exact counts are `surface_count` and `triangles`; optional exact counts are `vertices`, `root_vertex_count`, `root_edge_count`. All expected keys must match all actual prepared body/fin parts. Counts must be finite numeric values exactly equal to the actual integer counts; fractional truncation is not accepted. The declaration's model SHA must match the actual current input.

If the declaration is missing or incorrect, export writes `surface-inventory.actual.json` beside the planned output and stops **before** the first pose. This is read-only prepared inventory, not visual or anatomical approval. Review its full parts against the complete GLB/packed manifest, then bind the counts in the current plan. The final `export.validation.json` records actual/declared inventories, base SHA, revision and merge scope. Every emitted sample checks complete membrane vertex/triangle counts and root counts against the prepared inventory. Nonempty-root-per-surface behavior is inherited; this sidecar does not add support for a surface that the base selection rejects.

Failure handling uses an explicit readiness flag, not a callee assertion alone: a bad model/base/inventory requests nonzero exit, disallows every `sample()` call, and marks any final export receipt failed. This prevents the inherited caller from continuing to emit samples after a Godot child function returns from a failed assertion. No invalid inventory can produce a passing sample set.

The prepared inventory is also independently checked against the original logical source helper. The source must contain the complete body plus every planned fin; each original logical surface's vertex/triangle count and native mesh path must match the prepared sequence, and every prepared fin surface must have nonempty roots. A caller declaration matching an incomplete result cannot make it ready. Two direct negative fixtures cover a missing planned fin and a missing same-name second surface with a deliberately matching partial declaration: both write zero pose samples and an `ok=false` export receipt. The missing-fin fixture intentionally logs the production rejection error while the test suite itself completes successfully.

Use the same arguments/schedule as the base, for example:

```text
Godot --headless --path <game> --script <absolute portable/export_fin_poses_merged.gd> -- <current-plan.json> <isolated-output> envelope <species> --membranes
```

For full frozen gates the existing `full-fin <species> --membranes` schedule is inherited unchanged, and Python validators can receive this path through their existing `--exporter`. Do not run a full gate merely to discover missing inventory; use the small declaration preflight or existing current actual-rest inventory first. This change does not itself require replacing assets or repeating valid single-surface results, and must not be applied to the thirteen frozen fish.

Small actual Godot fixture validation:

```text
Godot --headless --path <game> --script <absolute portable/test_export_fin_poses_merged.gd> -- <absolute repository output/fin-surface-exporter-20261105>
```

`output/fin-surface-exporter-20261105/validation.json` records:

- Single-surface **`--membranes` complete sample**: every parsed value/key/root point/index/gain/rest array equals the original exporter; sample files are byte-identical.
- Two same-name logical surfaces from different native meshes with different bone/inverse-bind spaces: six vertices and both triangles retained with correct index offset, all eighteen root points, four root vertices/two root edges, all gains/rest values, and the second surface's actual transform independently verified.
- Wrong surface count, triangle count, missing body part, model SHA and fractional count rejected.
- Actual inherited preparation discovers both native surfaces and complete root selection, then validates the declaration.
- Independent original-source guards reject a missing planned fin and an omitted same-name second surface even when the caller's declaration matches the partial prepared result; neither can emit samples or a passing receipt.

No whole fish is loaded, edited or revalidated by these small memory fixtures. The single-surface equivalence claim is limited to the valid complete membrane sample used here. The old base's `axis>0` root-only path may access an uncreated membrane dictionary; this task does not edit or certify that old branch. Use `--membranes` when requesting diagnostic gain/rest arrays.
