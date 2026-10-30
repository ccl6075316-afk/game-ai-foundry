"""Production SOP evidence completeness/freshness; never substitutes visual review."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from volume_finalization import check_finalization, pending_finalization

# Each key names an observation/evidence obligation, not a generic success score.
STAGES = {
    'preparation': {'research_and_measurements':'data','source_views_and_purposes':'data','accepted_source_provenance':'data','landmarks_and_part_inventory':'image','native_fin_cutouts_and_part_ownership':'data'},
    'head': {'source_pose_comparison':'image','clay_side':'image','clay_front':'image','clay_top':'image','clay_bottom':'image','clay_oblique':'image','transverse_constraints':'data'},
    'mouth': {'structure_branch_and_constraints':'data','whole_snout_and_chin':'image','integrated_upper_lower_jaws_and_cut':'image','misplaced_outline_ownership':'image','native_pixel_cover_and_actual_uv_joins':'image','source_donors_and_mouth_gap':'data'},
    'eyes': {'source_eye_and_ownership_domains':'image','opposite_and_top_views':'image','overlay_attachment_and_lod':'data'},
    'skin': {'dorsal_material':'image','ventral_material':'image','hidden_fin_skin':'image','native_2d_donors_and_exclusions':'data','surface_opacity_inventory':'data','body_owned_fin_base_marks':'image'},
    'fins': {'complete_species_fin_inventory_and_roots':'data','source_cutout_and_shape_comparison':'image','installed_visibility_and_body_occlusion':'data','all_fin_root_gate':'report','whole_fin_membrane_gate':'report','expanded_fin_visual_review':'image'},
    'motion': {'native_loop':'report','swim':'image','turn':'image','ascend':'image','dive':'image','real_transitions_and_control_ranges':'report','jaw_or_other_action_branch':'data'},
    'runtime': {'body_integrity_gpu_gate':'report','material_anchor_and_actual_lod':'report','motion_and_surface_gate':'report','cold_import_and_install_binding':'report','final_asset_cold_load':'report','exported_vs_experiment_comparison':'image'},
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
    """Require an actual body/jaw resource and a documented cut construction.

    Geometry, animation and appearance are checked by separate evidence gates.
    """
    impl = entry.get('implementation', {})
    if not isinstance(impl, dict):
        fail('missing_mouth_implementation', 'mouth.implementation'); return
    branch = impl.get('branch')
    if branch == 'source_lip_bands' or any(k in impl for k in ('upper', 'lower', 'lip_resource_role')):
        fail('retired_lip_layer', 'Independent lip bands are retired from all fish')
        return
    if branch == 'anatomical_alternative':
        if not all(isinstance(impl.get(k), str) and impl[k].strip()
                   for k in ('reason', 'method_reference')):
            fail('missing_anatomical_basis', 'Explicit species basis and method reference required')
        # Separate articulated jaw structures still need species evidence.
        return
    if branch != 'integrated_jaw_cut':
        fail('missing_mouth_implementation', 'Choose integrated_jaw_cut or a justified anatomical_alternative'); return
    role = impl.get('body_resource_role')
    if not isinstance(role, str) or not role.strip():
        fail('missing_integrated_body', 'mouth.implementation.body_resource_role'); return
    body = artifact(candidates.get(role), 'mouth.implementation.body_resource_role')
    if body is not None and body.stat().st_size == 0:
        fail('empty_integrated_body', role)
    for key in ('cut_line', 'upper_jaw', 'lower_jaw', 'method_reference'):
        if not isinstance(impl.get(key), str) or not impl[key].strip():
            fail('missing_integrated_jaw_detail', 'mouth.implementation.' + key)

def initialize(species: str, output: Path):
    if output.exists():raise ValueError('Review already exists; update its evidence without overwriting it')
    if not species.strip():raise ValueError('Species is required')
    data={'schema_version':1,'kind':'fish_production_sop_review','species':species,
          'candidate_files':{k:{'path':'','sha256':''} for k in INPUT_ROLES},
          'evidence':{},'stages':{stage:{'result':'pending','method':'','reviewer':'','observations':'','checks':{k:[] for k in checks}} for stage,checks in STAGES.items()},
          'scope':'Operator evidence record. No asset acceptance or user approval is created by initialization.'}
    data['stages']['mouth']['implementation'] = {'branch':'pending','body_resource_role':'',
        'cut_line':'','upper_jaw':'','lower_jaw':'','method_reference':''}
    data['stages']['runtime']['finalization'] = pending_finalization()
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
        if stage == 'runtime':check_finalization(data,entry,candidates,artifact,fail)
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
                # Species cards have a stable repository identity. Rebinding all
                # candidate hashes must not make another fish's card valid.
                if stage == 'preparation' and criterion == 'research_and_measurements':
                    identity = lambda value: value.lower().replace('-', '_')
                    if path.parent.name == 'species' and identity(path.stem) != identity(data['species']):
                        fail('wrong_species_research', label+': '+path.stem+' != '+data['species'])
                    if evidence.get('species', data['species']) != data['species']:
                        fail('wrong_species_research', label+': declared species mismatch')
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
            'review_sha256':sha(review),'checker_sha256':sha(Path(__file__)),
            'finalization_checker_sha256':sha(Path(__file__).with_name('volume_finalization.py')), 'candidate_files':candidates,
            'stages':rows,'evidence_count':len(used),'failures':failures,
            'scope':'Checks required evidence, declared candidate bindings, integrated jaw-cut resource and description or justified anatomical branch, final asset declarations and bound fresh-process/no-static-builder report fields, file freshness and operator observations. Does not export assets, run Godot, prove undisclosed-builder absence, report semantics or visual quality. Actual cold-load capture, specialized gates and visual review remain required. No asset/user acceptance.'}
    if output:write(output,report)
    return report
