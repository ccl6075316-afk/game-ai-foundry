"""SOP contracts for preserved native charts and source-owned packed fin evidence.

The original authored multi-object contracts remain separate. This adapter binds
actual packed rows, complete body UV/index preservation, original490 tolerances,
four-probe coverage, taper and finite same-plane tail sections; no generic pass.
"""
import hashlib,importlib.util,json,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def _load(ref):
 p=Path(ref['path']);p=p if p.is_absolute()else ROOT/p
 if hashlib.sha256(p.read_bytes()).hexdigest()!=ref['sha256']:raise ValueError('Stale packed evidence')
 return json.loads(p.read_text(encoding='utf8'))

def _arrays(path):
 spec=importlib.util.spec_from_file_location('_sop_packed_glb_io',ROOT/'resources/scripts/volume-fish/portable/glb_io.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 d,b=m.read_glb(Path(path));pr=d['meshes'][0]['primitives'][0]
 return d,b,pr,{k:m.arrays(d,b,a)for k,a in pr['attributes'].items()},m.arrays(d,b,pr['indices']).reshape(-1,3)

def check_preserved_chart(report,candidates,species,fail,label):
 try:
  assert report['ok']and report['species']==species
  assert report['model_sha256']==candidates['model']['sha256'] and report['source_sha256']==candidates['source_image']['sha256']
  baseline=_load(report['baseline_native_chart']);d,b,pr,a,ix=_arrays(candidates['model']['path'])
  assert baseline['source_sha256']==report['source_sha256']and baseline['accepted_material_scope']=='complete body and integrated mouth chart'
  rows=[p for p in d['extras']['geometry_parts']if p['role']in ['body_skin','mouth']]
  assert {p['role']for p in rows}=={'body_skin','mouth'}and len(rows)==len(baseline['parts'])==2
  for p,q in zip(rows,baseline['parts']):
   lo=p['vertex_start'];hi=lo+p['vertex_count'];faces=ix[p['index_start']//3:(p['index_start']+p['index_count'])//3]-lo
   assert p['role']==q['role']and np.array_equal(a['TEXCOORD_0'][lo:hi],q['uv'])and np.array_equal(faces,q['indices'])
  image=d['images'][0];iv=d['bufferViews'][image['bufferView']];png=b[iv.get('byteOffset',0):iv.get('byteOffset',0)+iv['byteLength']]
  assert hashlib.sha256(png).hexdigest()==baseline['embedded_image_sha256']
  assert d['materials'][0]==baseline['material']
  assert report['actual_3d_rim_transport']['upper_edges']>0 and report['actual_3d_rim_transport']['lower_edges']>0
  assert report['complete_body_chart_preserved']is True and report['auxiliary_color_contribution_changes']==0
 except (AssertionError,ValueError,KeyError,OSError,TypeError,IndexError):fail('invalid_preserved_native_lip_chart',label)

def check_packed_volume(report,candidates,species,fail,label,profile):
 try:
  assert report['ok']and report['species']==species and report['model_sha256']==candidates['model']['sha256']
  assert report['profile_sha256']==candidates['species_profile']['sha256']
  source=_load(report['source_correspondence']);assert source['ok']and source['kind']=='saved_packed_source_row_correspondence'
  assert source['model_sha256']==report['model_sha256']and source['blend_sha256']==candidates['editable_blend']['sha256']
  assert source['maximum_bidirectional_position_error_native']<=2e-6 and source['source_vertex_count']==source['export_vertex_count']>0
  roots=_load(report['root490']);membranes=_load(report['membrane490'])
  assert roots['ok']and membranes['ok']and roots['model_sha256']==membranes['model_sha256']==report['model_sha256']
  assert len(roots['samples'])==membranes['poses']==490 and roots['tolerance_cm']==.10 and roots['max_penetration_cm']==.60
  assert membranes['root_collar_mm']==.5 and membranes['penetration_tolerance_mm']==.02
  expected={f['name']for f in profile['fins']};rows=report['current']['fins'];assert len(rows)==len(expected)and {r['name']for r in rows}==expected==set(roots['summary'])==set(membranes['summary'])
  assert all(r['failed_contact_samples']==0 for r in roots['summary'].values())and all(r['failed_poses']==0 for r in membranes['summary'].values())
  for row in rows:
   rule=next(f for f in profile['fins']if f['name']==row['name']);assert row['closing_faces']==rule['closing_faces']and row['missing_rays']==[]
   assert row['source_baseline']==rule['source_baseline']and row['complete_original_root_domain_preserved']is True
   samples=row['actual_samples'];counts={i:0 for i in rule['skin_faces']}
   for q in samples:
    assert q['face']in counts and math.isfinite(q['normal_thickness_mm'])and q['normal_thickness_mm']>0 and 0<=q['source_t']<=1.000001;counts[q['face']]+=1
   for q in row['transparent_source_samples']:assert q['face']in counts;counts[q['face']]+=1
   assert counts and all(n==4 for n in counts.values())
   zones=[[q['normal_thickness_mm']for q in samples if lo<=q['source_t']<hi]for lo,hi in [(0,.4),(.4,.75),(.75,1.0001)]]
   assert all(zones)and np.median(zones[0])/np.median(zones[2])>=1.5
  tail=report['current']['tail_section'];assert len(tail['sections'])>=3 and tail['max_error_mm']<=.4
  assert tail['root_height_domain']==profile['tail_root_height_domain']and tail['same_declared_attachment_plane']is True
  negative=_load(report['rejected_original']);assert negative['ok']is False and negative['model_sha256']==profile['rejected_fin_model_sha256']!=report['model_sha256']
  assert {r['name']for r in negative['current']}==expected and any(r['missing_rays']for r in negative['current'])
 except (AssertionError,ValueError,KeyError,OSError,TypeError,IndexError):fail('invalid_packed_fin_volume',label)
