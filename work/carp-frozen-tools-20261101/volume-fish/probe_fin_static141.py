"""Diagnostic: locate exact failing finite face and independent closed-body sign."""
import json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from closed_body_index140 import build
args=sys.argv[sys.argv.index('--')+1:];r=Path(args[0]);sample=json.loads((r/'static-quick/nile_tilapia/sample-000.json').read_text());report=json.loads((r/'static-quick/membrane.validation.json').read_text());geometry=json.loads((r/'fins.bound.json').read_text());sign=build(sample['body_vertices_m'],sample['body_triangles']);body=BVHTree.FromPolygons(sample['body_vertices_m'],sample['body_triangles'],all_triangles=True);rootdata=json.loads((r/'root-selection.json').read_text());rows=[]
for name,record in report['samples'][0]['fins'].items():
 if not record['inside_samples']:continue
 point=Vector(record['worst_point_m']);mem=sample['membranes'][name];tri=[mem['triangles'][i:i+3] for i in range(0,len(mem['triangles']),3)];tree=BVHTree.FromPolygons(mem['vertices_m'],tri,all_triangles=True);hit,n,face,dist=tree.find_nearest(point);ids=tri[face];fin=next(x for x in geometry['fins'] if x['name']==name);part=fin['parts'][0];uv=[[part['uv'][i][0]*1961,part['uv'][i][1]*972] for i in ids];roots=set(rootdata[name]['ids']);row={'name':name,'reported_inside':record['inside_samples'],'independent_inside':bool(sign(point)),'worst_distance_mm':body.find_nearest(point)[3]*1000,'face':face,'ids':ids,'source_uv_px':uv,'all_selected_roots':all(i in roots for i in ids),'selected_root_vertices':[i in roots for i in ids],'vertices_m':[mem['vertices_m'][i] for i in ids],'longest_edge_mm':max((Vector(mem['vertices_m'][a])-Vector(mem['vertices_m'][b])).length for a,b in zip(ids,ids[1:]+ids[:1]))*1000};rows.append(row)
(r/'static-quick/probe.validation.json').write_text(json.dumps({'ok':True,'diagnostic_only':True,'records':rows},indent=2));print(json.dumps(rows))
