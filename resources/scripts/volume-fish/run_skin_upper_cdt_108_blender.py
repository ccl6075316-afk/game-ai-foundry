"""108 one approved CPU event: one CDT per frozen upper chart, no assets."""
import sys,json,hashlib,argparse
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args(sys.argv[sys.argv.index('--')+1:]);data=json.loads(a.input.read_text());assert hashlib.sha256(a.input.read_bytes()).hexdigest()=='96f823e163a19f1cd976e4920d02a38d188dcf9a57a7246a7000520301512ed0';assert data['epsilon']==1e-9 and data['output_type']==1 and data['need_ids'] is True
out={'status':'single_upper_left_right_CPU_CDT_event','accepted':False,'asset_written':False,'input':str(a.input.resolve()),'input_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sheets':[],'cdt_invocations':0}
for sheet in data['sheets']:
 edges=sheet['boundary_edges'];adj={}
 for u,v in edges:adj.setdefault(u,set()).add(v);adj.setdefault(v,set()).add(u)
 assert all(len(nei)==2 for nei in adj.values());loop=[min(adj)];prev=None
 while True:
  nxt=min(adj[loop[-1]]-({prev} if prev is not None else set()));prev=loop[-1]
  if nxt==loop[0]:break
  assert nxt not in loop;loop.append(nxt)
 assert len(loop)==len(edges)
 # Exactly one invocation for this chart; no retry or coordinate replacement.
 vv,ee,ff,ov,oe,of=delaunay_2d_cdt([Vector(p['input_xy']) for p in sheet['points']],edges,[loop],1,1e-9,True);out['cdt_invocations']+=1
 origins=[list(x) for x in ov];flat=[x[0] for x in origins if len(x)==1];valid=len(origins)==len(sheet['points']) and len(flat)==len(origins) and sorted(flat)==list(range(len(sheet['points'])));newfaces=[]
 if valid:
  for f in ff:
   assert len(f)==3;ids=[origins[k][0] for k in f];xy=[sheet['points'][k]['input_xy'] for k in ids];area=(xy[1][0]-xy[0][0])*(xy[2][1]-xy[0][1])-(xy[1][1]-xy[0][1])*(xy[2][0]-xy[0][0]);assert area!=0
   if area*sheet['required_uniform_directed_XY_area_sign']<0:ids.reverse()
   newfaces.append(ids)
 used=set(k for f in newfaces for k in f);out['sheets'].append({'sheet':sheet['sheet'],'cdt_invocations':1,'origins_one_to_one':valid,'output_vertex_count':len(vv),'output_faces_count':len(ff),'output_orig_verts':origins,'output_orig_edges':[list(x) for x in oe],'output_orig_faces':[list(x) for x in of],'output_edges':[list(x) for x in ee],'returned_xy_diagnostic_only':[list(x) for x in vv],'returned_coordinates_used_for_geometry':False,'unused_input_point_ids':sorted(set(range(len(sheet['points'])))-used),'input_origin_faces':newfaces});a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'sheet':sheet['sheet'],'origins':valid,'faces':len(ff),'unused':out['sheets'][-1]['unused_input_point_ids']}))
