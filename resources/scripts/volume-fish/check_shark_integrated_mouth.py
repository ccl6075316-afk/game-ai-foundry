"""Actual finite oral negative-space probes and source/candidate mouth review."""
import bpy,bmesh,sys,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));from rim_material_transport import ordered_boundary
import numpy as np
args=sys.argv[sys.argv.index('--')+1:];src=Path(args[0]).resolve();out=Path(args[1]).resolve();assert not out.exists();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));o=bpy.data.objects['Closed_body'];mesh=o.data;mesh.calc_loop_triangles();tree=BVHTree.FromPolygons([v.co for v in mesh.vertices],[t.vertices for t in mesh.loop_triangles],all_triangles=True);bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();bm.normal_update();coords=np.array([v.co[:]for v in bm.verts]);chains={}
for name,sign in [('upper',-1),('lower',1)]:
 edges=[tuple(v.index for v in e.verts)for e in bm.edges if len(e.link_faces)==2 and any(f.material_index!=1 for f in e.link_faces)and any(f.material_index==1 and f.normal.x*sign>.1 for f in e.link_faces)];chains[name]=ordered_boundary(coords,edges)
assert all(len(e.link_faces)==2 for e in bm.edges);bm.free();records=[]
for phase in np.linspace(.12,.88,9):
 points=[]
 for pts,arc in chains.values():points.append(np.array([np.interp(phase*arc[-1],arc,pts[:,i])for i in range(3)]))
 p,q=points;center=(p+q)/2;origin=Vector((float(center[0]),float(center[1]),-2));hit,n,fi,dist=tree.ray_cast(origin,Vector((0,0,1)),4);assert hit is not None;depth=hit.z-center[2];material=mesh.polygons[mesh.loop_triangles[fi].polygon_index].material_index;records.append(dict(phase=float(phase),rim_gap_native=float(np.linalg.norm(p-q)),roof_depth_native=float(depth),actual_hit_material=material,recess=bool(depth>.002 and material==1)))
result=dict(ok=all(r['recess']for r in records),kind='actual_integrated_shark_mouth_negative_space',body_watertight=True,source=str(src/'fish.blend'),mouth_rims={k:dict(points=pts.tolist(),arc=arc.tolist())for k,(pts,arc)in chains.items()},negative_space_probes=records,scope='Actual nine across-rim rays from below hit original finite oral roof beyond rim plane. Independent upper/lower skins, cavity walls and positive jaw body retained. Discrete static proof; local textured/gray side/front/under-oblique and source review required.');out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'ok':result['ok'],'probes':records}))
