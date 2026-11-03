"""Bind independent current mouth BVH result by actual saved body triangle parity."""
import sys,json,hashlib,itertools
from pathlib import Path
import bpy,numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays
q=ROOT/'projects/fishing-2d/experiments/six-fish-database-20261104/bluegill';model=q/'width-r6/fish.glb';source=q/'width-r6/mouth-diagnostic.blend';raw=q/'mouth-opening-r6.validation.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();ref=lambda p:{'path':str(p),'sha256':sha(p)};d,b=read_glb(model);pr=d['meshes'][0]['primitives'][0];v=arrays(d,b,pr['attributes']['POSITION']);idx=arrays(d,b,pr['indices']);wanted=[]
for part in d['extras']['geometry_parts']:
 if part['role']in ['body_skin','mouth']:wanted.extend(v[tri][:,[0,2,1]]*np.array([1,-1,1])for tri in idx[part['index_start']:part['index_start']+part['index_count']].reshape(-1,3))
expected=np.array(wanted);bpy.ops.wm.open_mainfile(filepath=str(source));o=bpy.data.objects['Closed_body'];o.data.calc_loop_triangles();actual=np.array([[o.matrix_world@o.data.vertices[i].co for i in t.vertices]for t in o.data.loop_triangles]);assert len(actual)==len(expected);centroids=actual.mean(1);used=set();errors=[]
for tri in expected:
 choices=np.flatnonzero(np.max(np.abs(centroids-tri.mean(0)),axis=1)<=2e-6);found=False
 for j in choices:
  if int(j)in used:continue
  e=min(float(np.max(np.abs(tri-actual[j,list(perm)])))for perm in itertools.permutations(range(3)))
  if e<=2e-6:used.add(int(j));errors.append(e);found=True;break
 assert found,'Unmatched actual body triangle'
assert len(used)==len(actual);rr=json.loads(raw.read_text(encoding='utf8'));assert rr['ok']and rr['results']['current']['sha256']==sha(source);report={'ok':True,'kind':'actual_current_mouth_opening_with_triangle_binding','species':'bluegill','model_sha256':sha(model),'source_triangle_parity':{'ok':True,'all_body_and_oral_triangles':len(expected),'actual_saved_source_triangles':len(actual),'maximum_matched_component_error_native':max(errors),'triangle_tolerance_native':2e-6,'every_triangle_unique_match':True,'source':ref(source)},'actual_independent_ray_report':ref(raw),'actual_current_stations':rr['results']['current']['rows'],'actual_rejected_old_source':rr['results']['rejected'],'scope':'Independent current saved-source mouth BVH remains unchanged, now bound by every actual body/oral triangle to final packedGLB; no report SHA relabeling.'};(q/'mouth-opening-current-r6.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'triangles':len(expected),'maximum_component_error':max(errors)}))
