"""Blender4.5 CPU-only single CDT evaluation; outputs diagnostic JSON, never a mesh."""
import sys,json,hashlib,argparse
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);d=json.loads(a.input.read_text());assert d['epsilon']==1e-9 and d['sheet']=='upper_only' and d['need_ids'] is True
# This is the only CDT invocation, with the pre-frozen epsilon. Returned coordinates are diagnostic only.
vertices,edges,faces,orig_verts,orig_edges,orig_faces=delaunay_2d_cdt([Vector(p['input_xz']) for p in d['points']],d['edges'],[d['loop']],d['output_type'],d['epsilon'],True)
origin=[list(x) for x in orig_verts];flat=[x[0] for x in origin if len(x)==1];valid=len(origin)==len(d['points']) and len(flat)==len(origin) and sorted(flat)==list(range(len(d['points'])))
newfaces=[]
if valid:
 for face in faces:
  if len(face)!=3:raise ValueError('CDT returned nontriangle')
  # Originalupper XZ winding is negative; returned Delaunay faces are CCW.
  ids=[orig_verts[i][0] for i in face];points=[d['points'][i]['input_xz'] for i in ids];area=(points[1][0]-points[0][0])*(points[2][1]-points[0][1])-(points[1][1]-points[0][1])*(points[2][0]-points[0][0]);
  if area>0:ids.reverse()
  newfaces.append(ids)
used=sorted(set(i for f in newfaces for i in f));out={'status':'single_cpu_cdt_only','accepted':False,'input':str(a.input.resolve()),'input_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),'blender_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'epsilon':d['epsilon'],'cdt_invocations':1,'output_vertex_count':len(vertices),'output_faces_count':len(faces),'output_orig_verts':origin,'output_orig_edges':[list(x) for x in orig_edges],'output_orig_faces':[list(x) for x in orig_faces],'output_edges':[list(x) for x in edges],'origins_one_to_one':valid,'unused_input_point_ids':sorted(set(range(len(d['points'])))-set(used)),'input_origin_faces':newfaces,'returned_xz_diagnostic_only':[list(x) for x in vertices],'returned_coordinates_used_for_geometry':False,'model_uv_runtime_written':False};a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'origin_valid':valid,'faces':len(faces),'unused':out['unused_input_point_ids'],'epsilon':d['epsilon']}))
