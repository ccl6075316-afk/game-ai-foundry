"""Final asset declarations and cold-load evidence, not an exporter or visual judge."""
from __future__ import annotations

import json


STATIC_PARTS = ('body', 'eyes', 'mouth', 'fins')
RUNTIME_PURPOSES = ('animation', 'behavior', 'environment', 'resource_loading')
COLD_CHECKS = ('independent_load', 'materials_complete', 'rig_and_motion',
               'export_matches_candidate')


def pending_finalization():
    return {'state': 'pending', 'editable_source_role': '', 'model_role': 'model',
            'entry_role': '', 'static_parts': {part: {} for part in STATIC_PARTS},
            'engine_resource_roles': [], 'runtime_behaviors': []}


def check_finalization(data, entry, candidates, artifact, fail):
    """Fail closed for missing exports, runtime construction, or stale cold tests.

    Declarations cannot prove that a scene never calls an undisclosed builder.
    A real fresh-process capture with builders disabled plus visual/specialized
    review remains necessary; this gate does not generate those observations.
    """
    declaration = entry.get('finalization')
    if not isinstance(declaration, dict) or declaration.get('state') != 'exported':
        fail('asset_not_finalized', 'runtime.finalization.state must be exported'); return

    def role_file(role, label, suffixes=None):
        if not isinstance(role, str) or role not in candidates:
            fail('missing_final_asset_role', label); return None
        path = artifact(candidates[role], label)
        if path is not None:
            if path.stat().st_size == 0:
                fail('empty_final_asset', label)
            if suffixes and path.suffix.lower() not in suffixes:
                fail('wrong_final_asset_format', label)
        return path

    role_file(declaration.get('editable_source_role'), 'finalization.editable_source', {'.blend'})
    model_role = declaration.get('model_role')
    if model_role != 'model':
        fail('wrong_final_model_role', 'Final exported GLB must be the candidate model')
    role_file(model_role, 'finalization.model', {'.glb'})
    role_file(declaration.get('entry_role'), 'finalization.entry', {'.glb', '.tscn', '.scn'})

    parts = declaration.get('static_parts', {})
    if not isinstance(parts, dict):
        fail('missing_static_part_inventory', 'finalization.static_parts'); parts = {}
    for part in STATIC_PARTS:
        row = parts.get(part)
        if not isinstance(row, dict) or row.get('geometry_uv_weights_role') != model_role or not (
                isinstance(row.get('observation'), str) and row['observation'].strip()):
            fail('static_part_not_in_model', 'finalization.static_parts.' + part)
    resources = declaration.get('engine_resource_roles')
    if not isinstance(resources, list):
        fail('invalid_engine_resources', 'finalization.engine_resource_roles')
    else:
        for role in resources:
            role_file(role, 'finalization.engine_resource',
                      {'.res', '.tres', '.tscn', '.scn', '.gdshader', '.gdshaderinc'})
    behaviors = declaration.get('runtime_behaviors')
    if not isinstance(behaviors, list):
        fail('invalid_runtime_behavior', 'finalization.runtime_behaviors')
    else:
        for row in behaviors:
            if not isinstance(row, dict) or row.get('purpose') not in RUNTIME_PURPOSES or not (
                    isinstance(row.get('observation'), str) and row['observation'].strip()):
                fail('invalid_runtime_behavior', 'Only motion, behavior, environment and loading remain at runtime')
            else:
                role_file(row.get('resource_role'), 'finalization.runtime_behavior')

    ids = entry.get('checks', {}).get('final_asset_cold_load', [])
    valid_reports = 0
    if not isinstance(ids, list):
        ids = []
    for eid in ids:
        if not isinstance(eid, str):
            continue
        evidence = data.get('evidence', {}).get(eid)
        path = artifact(evidence, 'finalization.cold_load')
        if path is None:
            continue
        try:
            report = json.loads(path.read_text(encoding='utf-8-sig'))
            expected = {k: v.get('sha256') for k, v in candidates.items() if isinstance(v, dict)}
            valid = (isinstance(report, dict) and report.get('ok') is True and
                     report.get('kind') == 'fish_final_asset_cold_load' and
                     report.get('species') == data['species'] and
                     report.get('bound_inputs') == expected and
                     report.get('entry_role') == declaration.get('entry_role') and
                     report.get('fresh_process') is True and
                     report.get('static_builders_disabled') is True and
                     type(report.get('runtime_static_build_calls')) is int and
                     report['runtime_static_build_calls'] == 0 and report.get('errors') == [] and
                     isinstance(report.get('checks'), dict) and
                     all(report['checks'].get(k) is True for k in COLD_CHECKS))
            if valid:
                valid_reports += 1
            else:
                fail('invalid_final_asset_cold_load', eid + ': current exported asset must load without static builders')
        except (ValueError, TypeError, AttributeError) as exc:
            fail('invalid_final_asset_cold_load', eid + ': ' + str(exc))
    if not valid_reports:
        fail('missing_final_asset_cold_load', 'A bound fresh-process final asset report is required')
