"""Locate B's actual skin/upper oral-roof boundary; export texture-bake input."""
import bpy,bmesh,json,hashlib,math
from pathlib import Path
from collections import defaultdict
from mathutils import Vector
repo=Path(__file__).resolve().parents[3];trial=repo/'projects/fishing-2d/experiments/nile-dorsal-route-trial';source=trial/'round6-reference-repair/B-artifacts/fish.blend';out=trial/'round7-upper-lip-continuity';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source));body=bpy.data.objects['Closed_body_B'];mesh=body.data
bm=bmesh.new();bm.from_mesh(mesh);bm.normal_update();bm.verts.ensure_lookup_table()
upper=[]
for edge in bm.edges:
 if len(edge.link_faces)!=2:continue
 skin=[f for f in edge.link_faces if f.material_index==0];roof=[f for f in edge.link_faces if f.material_index==1 and f.normal.z<-.1]
 if skin and roof:upper.append(tuple(v.index for v in edge.verts))
assert upper,'Actual upper lip boundary not found'
vs=[v.co.copy() for v in mesh.vertices];bm.free()
def near(p):
 best=(float('inf'),None,None)
 for ia,ib in upper:
  a,b=vs[ia],vs[ib];d=b-a;t=max(0.,min(1.,(p-a).dot(d)/max(d.length_squared,1e-15)));q=a+d*t;dist=(q-p).length
  if dist<best[0]:best=(dist,q,(ia,ib))
 return best
width=32/1961
faces=[]
for face in mesh.polygons:
 if face.material_index!=0:continue
 points=[vs[i] for i in face.vertices];center=sum(points,Vector())/len(points);d,q,edge=near(center)
 if max(v.x+.5 for v in points)<.938:continue
 if min(near(p)[0] for p in points)>width+.002:continue
 if center.z<q.z-.0002:continue
 faces.append({'index':face.index,'vertices':list(face.vertices),'positions':[list(p) for p in points],'old_uv':[list(mesh.uv_layers.active.data[li].uv) for li in face.loop_indices]})
other_uv=[tuple(mesh.uv_layers.active.data[li].uv) for face in mesh.polygons if face.material_index==0 and face.index not in {f['index'] for f in faces} for li in face.loop_indices]
assert min(p[0] for p in other_uv)>.145,'Left atlas gutter is not free'
adj=defaultdict(list)
for a,b in upper:adj[a].append(b);adj[b].append(a)
endpoints=[i for i,row in adj.items() if len(row)==1]
record={'kind':'actual_B_upper_lip_texture_guide','source_blend_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'geometry':'Actual shared skin/upper oral-roof mesh boundary, selected by material adjacency and roof normal; not an invented screen-space line.','upper_lip_edges':[list(x) for x in upper],'boundary_vertices':{str(i):list(vs[i]) for i in adj},'endpoints':endpoints,'degrees':{str(i):len(row) for i,row in adj.items()},'faces':faces,'texture_size':[1961,1024],'free_atlas_rectangle_px':[4,4,280,1020],'source_band_width_px':32,'front_blend_start_u':.974,'front_blend_full_u':.982,'source_extension_anchor_u':.97,'side_source':'round2/Closed_body-0-source_texture.png','geometry_changes':False,'notes':'Only upper-jaw skin faces are assigned unique UV islands in the unused left gutter; all non-band texels are baked from the previous atlas.'}
(out/'upper-lip-guide.json').write_text(json.dumps(record,indent=2),encoding='utf8')
print(json.dumps({'ok':True,'upper_edges':len(upper),'selected_faces':len(faces),'endpoints':len(endpoints),'degrees':sorted(set(map(len,adj.values())))}))
