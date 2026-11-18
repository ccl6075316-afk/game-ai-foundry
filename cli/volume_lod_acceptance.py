"""Bookkeeping for actual production LOD selection, visual and contact evidence."""
from __future__ import annotations

import json

CONTACT_CHECKS = frozenset(('mouth', 'fin_roots', 'fin_membrane'))


def text(value):
    return isinstance(value, str) and bool(value.strip())


def check_contact(contact, artifact, fail, label):
    if not isinstance(contact, dict):
        fail('missing_lod_contact', label)
        return
    scope = contact.get('scope')
    if not isinstance(scope, list) or not all(isinstance(part, str) for part in scope) or not CONTACT_CHECKS.issubset(scope):
        fail('missing_lod_contact_scope', label)
    method = contact.get('method')
    if method == 'retested':
        samples = contact.get('pose_samples')
        valid = type(samples) is int and samples > 0
    elif method == 'exact_preserved':
        valid = contact.get('interacting_geometry_exact') is True
    else:
        valid = False
    if not valid:
        fail('unverified_lod_contact', label)
    evidence = contact.get('evidence')
    if not isinstance(evidence, list) or not evidence:
        fail('missing_lod_contact_evidence', label)
        return
    for item in evidence:
        path = artifact(item, label)
        if path is None:
            continue
        try:
            result = json.loads(path.read_text(encoding='utf-8-sig'))
        except (ValueError, OSError):
            fail('invalid_lod_contact_report', label)
            continue
        if not isinstance(result, dict) or result.get('ok') is not True:
            fail('failed_lod_contact_report', label)


def check_entry(entry, spec, artifact, fail, label):
    if (not isinstance(entry, dict) or entry.get('entry_role') != spec['entry_role']
            or entry.get('fresh_process') is not True
            or entry.get('cache') not in ('verified', 'not_used_verified')
            or not text(entry.get('observation'))):
        fail('unverified_lod_entry', label)
        return
    levels = entry.get('levels')
    ids = spec['tiers']
    if (not isinstance(levels, list) or not all(isinstance(level, dict) for level in levels)
            or [level.get('id') for level in levels] != ids):
        fail('wrong_lod_tiers', label)
        return

    previous = None
    for level in levels:
        tier = label + '/' + level['id']
        triangles = level.get('triangles')
        if type(triangles) is not int or triangles <= 0 or (previous is not None and triangles >= previous):
            fail('invalid_lod_triangle_count', tier)
        else:
            previous = triangles
        if not all(level.get(field) is True for field in (
            'actual_gpu_selection', 'visual_passed', 'body_coverage_passed', 'material_anchor_passed'
        )):
            fail('unverified_lod_level', tier)
        check_contact(level.get('contact'), artifact, fail, tier)

    transitions = entry.get('transitions')
    adjacent = list(zip(ids, ids[1:]))
    if not isinstance(transitions, list) or not all(isinstance(switch, dict) for switch in transitions):
        fail('unverified_lod_transitions', label)
        return
    observed = [(switch.get('near'), switch.get('far')) for switch in transitions]
    if observed != adjacent or not all(
        switch.get('both_directions') is True and switch.get('visual_passed') is True for switch in transitions
    ):
        fail('unverified_lod_transitions', label)


def check_lod_acceptance(report, spec, species, bindings, artifact, fail, label):
    if (report.get('kind') != 'fish_runtime_lod_acceptance' or report.get('species') != species
            or report.get('bound_inputs') != bindings):
        fail('invalid_runtime_lod_report', label)
        return
    entries = report.get('entries')
    if not isinstance(spec, dict) or not spec:
        fail('missing_runtime_lod_declaration', label)
        return
    if not isinstance(entries, dict) or entries.keys() != spec.keys():
        fail('wrong_runtime_lod_entries', label)
        return
    for name, row in spec.items():
        entry_label = label + '/' + name
        tiers = row.get('tiers') if isinstance(row, dict) else None
        if (not text(name) or not isinstance(tiers, list) or not tiers
                or not all(text(tier) for tier in tiers) or len(set(tiers)) != len(tiers)
                or not text(row.get('entry_role')) or not bindings.get(row['entry_role'])):
            fail('invalid_runtime_lod_declaration', entry_label)
            continue
        mode = row.get('mode')
        if not (mode == 'tiered' and len(tiers) > 1 or
                mode == 'full_detail_only' and len(tiers) == 1 and text(row.get('reason'))):
            fail('invalid_runtime_lod_mode', entry_label)
            continue
        check_entry(entries[name], row, artifact, fail, entry_label)
