"""Production SOP evidence completeness/freshness; never substitutes visual review."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

# Each key names an observation/evidence obligation, not a generic success score.
STAGES = {
    'preparation': {'research_and_measurements':'data','source_views_and_purposes':'data','accepted_source_provenance':'data','landmarks_and_part_inventory':'image','native_fin_cutouts_and_part_ownership':'data'},
    'head': {'source_pose_comparison':'image','clay_side':'image','clay_front':'image','clay_top':'image','clay_bottom':'image','clay_oblique':'image','transverse_constraints':'data'},
    'mouth': {'structure_branch_and_constraints':'data','whole_snout_and_chin':'image','upper_lower_lip_bands_or_anatomical_branch':'image','misplaced_outline_ownership':'image','native_pixel_cover_and_actual_uv_joins':'image','source_donors_and_mouth_gap':'data'},
    'eyes': {'source_eye_and_ownership_domains':'image','opposite_and_top_views':'image','overlay_attachment_and_lod':'data'},
    'skin': {'dorsal_material':'image','ventral_material':'image','hidden_fin_skin':'image','native_2d_donors_and_exclusions':'data','surface_opacity_inventory':'data','body_owned_fin_base_marks':'image'},
    'fins': {'complete_species_fin_inventory_and_roots':'data','source_cutout_and_shape_comparison':'image','installed_visibility_and_body_occlusion':'data','all_fin_root_gate':'report','whole_fin_membrane_gate':'report','expanded_fin_visual_review':'image'},
    'motion': {'native_loop':'report','swim':'image','turn':'image','ascend':'image','dive':'image','real_transitions_and_control_ranges':'report','jaw_or_other_action_branch':'data'},
    'runtime': {'body_integrity_gpu_gate':'report','material_anchor_and_actual_lod':'report','motion_and_surface_gate':'report','cold_import_and_install_binding':'report'},
    'presentation': {'source_style_final_comparison':'image','normal_and_close_game_views':'image','water_readability':'image','orbit_and_motion_video':'video','final_files_and_remaining_limits':'data'},
}
INPUT_ROLES = ('source_image','model','species_profile','runtime_manifest','motion_config')

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write(path: Path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def check_mouth_implementation(entry, candidates, artifact, fail):
    """Check declared actual layer exports, not their visual/anatomical quality.

    Runtime export equivalence is still a separate cold-import gate. An image
    alone must no longer stand in for the two missing lip geometries.
    """
    impl = entry.get('implementation', {})
    if not isinstance(impl, dict):
        fail('missing_mouth_implementation', 'mouth.implementation'); return
    branch = impl.get('branch')
    if branch == 'anatomical_alternative':
        if not all(isinstance(impl.get(k), str) and impl[k].strip()
                   for k in ('reason', 'method_reference')):
            fail('missing_anatomical_basis', 'Explicit species basis and method reference required')
        # These criteria are independently checked for bound, nonempty evidence.
        # This declaration does not automatically approve the anatomical choice.
        return
    if branch != 'source_lip_bands':
        fail('missing_mouth_implementation', 'Choose source_lip_bands or a justified anatomical_alternative'); return
    identities = []
    for side in ('upper', 'lower'):
        row = impl.get(side, {})
        label = 'mouth.implementation.' + side
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k].strip()
                for k in ('resource_role', 'geometry_role', 'part', 'node')):
            fail('missing_lip_layer', label); continue
        resource = artifact(candidates.get(row['resource_role']), label + '.resource')
        geometry = artifact(candidates.get(row['geometry_role']), label + '.geometry')
        if resource is not None and resource.stat().st_size == 0:
            fail('empty_lip_resource', label)
        if geometry is None: continue
        try:
            parts = read(geometry)['parts']
            matches = [p for p in parts if p.get('name') == row['part']]
            if len(matches) != 1: raise ValueError('Expected exactly one named lip part')
            part = matches[0]; vertices = part['vertices']; indices = part['triangles']
            if not isinstance(vertices, list) or len(vertices) < 3:
                raise ValueError('Empty lip vertices')
            if not all(isinstance(v, list) and len(v) == 3 and
                       all(type(x) in (int, float) and math.isfinite(x) for x in v) for v in vertices):
                raise ValueError('Invalid lip vertices')
            if not isinstance(indices, list) or not indices or len(indices) % 3 or not all(
                    type(i) is int and 0 <= i < len(vertices) for i in indices):
                raise ValueError('Empty or invalid lip triangles')
            for i in range(0, len(indices), 3):
                a, b, c = [vertices[j] for j in indices[i:i+3]]
                u = [b[j]-a[j] for j in range(3)]; v = [c[j]-a[j] for j in range(3)]
                cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
                if not any(x != 0 for x in cross): raise ValueError('Collapsed lip triangle')
            identities.append((geometry.resolve(), row['part']))
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            fail('invalid_lip_geometry', label + ': ' + str(exc))
    if len(identities) == 2 and identities[0] == identities[1]:
        fail('duplicate_lip_layer', 'Upper and lower cannot both name the same geometry part')

def initialize(species: str, output: Path):
    if output.exists():raise ValueError('Review already exists; update its evidence without overwriting it')
    if not species.strip():raise ValueError('Species is required')
    data={'schema_version':1,'kind':'fish_production_sop_review','species':species,
          'candidate_files':{k:{'path':'','sha256':''} for k in INPUT_ROLES},
          'evidence':{},'stages':{stage:{'result':'pending','method':'','reviewer':'','observations':'','checks':{k:[] for k in checks}} for stage,checks in STAGES.items()},
          'scope':'Operator evidence record. No asset acceptance or user approval is created by initialization.'}
    data['stages']['mouth']['implementation'] = {'branch':'pending','upper':{},'lower':{}}
    write(output,data)
    return data

def check(review: Path, output: Path | None=None):
    if output and output.resolve() == review.resolve():
        raise ValueError('Output must not overwrite the review')
    failures=[];rows=[]
    def fail(code,message):failures.append({'kind':'validation','code':code,'message':message})
    def resolve(value):
        p=Path(value);return p if p.is_absolute() else review.parent/p
    def artifact(row,label):
        if not isinstance(row,dict) or not row.get('path') or not row.get('sha256'):
            fail('missing_artifact',label);return None
        p=resolve(row['path'])
        if not p.is_file():fail('missing_artifact',label+': '+str(p));return None
        if sha(p)!=row['sha256']:fail('stale_artifact',label+': '+str(p));return None
        return p
    data=read(review)
    if not isinstance(data,dict):raise ValueError('Review must be an object')
    if data.get('kind')!='fish_production_sop_review' or data.get('schema_version')!=1 or not data.get('species'):
        raise ValueError('Unsupported/incomplete SOP review')
    candidates=data.get('candidate_files',{})
    if not isinstance(candidates,dict) or not isinstance(data.get('evidence'),dict) or not isinstance(data.get('stages'),dict):
        raise ValueError('Candidate files, evidence and stages must be objects')
    if output:
        for row in [*candidates.values(),*data['evidence'].values()]:
            if isinstance(row,dict) and row.get('path') and resolve(row['path']).resolve()==output.resolve():
                raise ValueError('Output must not overwrite candidate or evidence files')
    for role in INPUT_ROLES:artifact(candidates.get(role),role)
    for role,row in candidates.items():
        if role not in INPUT_ROLES:artifact(row,role)
    frozen={k:v.get('sha256') for k,v in candidates.items() if isinstance(v,dict)}
    used=set()
    for stage,checks in STAGES.items():
        start=len(failures);entry=data.get('stages',{}).get(stage,{})
        if not isinstance(entry,dict) or not isinstance(entry.get('checks',{}),dict):
            raise ValueError('Stage and checks must be objects: '+stage)
        if entry.get('result')!='passed':fail('stage_incomplete',stage)
        if stage == 'mouth':check_mouth_implementation(entry,candidates,artifact,fail)
        for key in ['method','reviewer','observations']:
            if not isinstance(entry.get(key),str) or not entry[key].strip():fail('missing_review',stage+'.'+key)
        for criterion,kind in checks.items():
            ids=entry.get('checks',{}).get(criterion)
            if not isinstance(ids,list) or not ids:
                fail('missing_evidence',stage+'.'+criterion);continue
            for eid in ids:
                if not isinstance(eid,str):
                    fail('invalid_evidence_id',stage+'.'+criterion);continue
                evidence=data.get('evidence',{}).get(eid,{})
                if not isinstance(evidence,dict):
                    fail('invalid_evidence',eid);continue
                label=stage+'.'+criterion+': '+str(eid);path=artifact(evidence,label)
                if evidence.get('kind')!=kind:fail('wrong_evidence_kind',label+' requires '+kind)
                if evidence.get('bound_inputs')!=frozen:fail('stale_binding',label+' does not bind the full current candidate snapshot')
                if not isinstance(evidence.get('observation'),str) or not evidence['observation'].strip():fail('missing_observation',label)
                if path is None:continue
                used.add(eid)
                if kind=='report':
                    try:
                        if read(path).get('ok') is not True:fail('failed_report',label)
                    except (ValueError,AttributeError):fail('invalid_report',label)
                elif kind=='image':
                    from PIL import Image
                    try:
                        with Image.open(path) as im:im.verify()
                    except Exception:fail('invalid_image',label)
                elif kind=='video' and (path.suffix.lower() not in ['.mp4','.webm','.mov','.mkv'] or path.stat().st_size==0):
                    fail('invalid_video',label)
        rows.append({'stage':stage,'ok':len(failures)==start})
    report={'schema_version':1,'ok':not failures,'command':'volume.sop-check','status':'done' if not failures else 'blocked',
            'next_action':'human_review' if not failures else 'fix_input','species':data['species'],
            'review_sha256':sha(review),'checker_sha256':sha(Path(__file__)), 'candidate_files':candidates,
            'stages':rows,'evidence_count':len(used),'failures':failures,
            'scope':'Checks required evidence, declared candidate bindings, actual named nonempty lip geometry exports, file freshness, successful report status and operator observations. Does not prove exported lip/runtime equivalence, anatomical alternatives, report semantics or visual quality; cold-import/specialized gates and visual review remain required. No asset/user acceptance.'}
    if output:write(output,report)
    return report
