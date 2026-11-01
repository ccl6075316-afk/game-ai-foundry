"""Repair diagnosed basal fin bands on frozen existing exports.

Body, jaws, rest bones, source pixels and distal fin vertices are preserved.
Basal edges are subdivided for curved contact; roots copy actual body triangle
skin weights, with a smooth blend into the original distal fin animation.
"""
import bpy,bmesh,json,sys,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils.geometry import barycentric_transform
sys.path.insert(0,str(Path(__file__).parent))
from build_fish import export_native,binary_inspect
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def weights(o,v):return {o.vertex_groups[g.group].name:g.weight for g in v.groups}
def main():
 args=sys.argv[sys.argv.index('--')+1:];plan=json.loads(Path(args[0]).read_text());root=Path(args[1]).resolve();audit=Path(args[2]).resolve();result={'kind':'existing_fin_attachment_repair','items':[]}
 for row in plan['items']:
  sp=row['species'];baseline=json.loads((audit/sp/'contact.validation.json').read_text());targets={name for name,s in baseline['summary'].items() if s['failed_contact_samples']}
  assert sha(row['model'])==row['model_sha256'];bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=row['model']);scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE');meshes=[o for o in scene.objects if o.type=='MESH'];body=bpy.data.objects[row['body']]
  data=rig.animation_data
  if not data.action:
   strips=[s for t in data.nla_tracks for s in t.strips];action=strips[0].action;slot=strips[0].action_slot
   for track in list(data.nla_tracks):data.nla_tracks.remove(track)
   data.action=action
   if slot:data.action_slot=slot
  scene.frame_start=round(data.action.frame_range[0]);scene.frame_end=round(data.action.frame_range[1]);scene.render.fps=24;rig.data.pose_position='REST';bpy.context.view_layer.update()
  body.data.calc_loop_triangles();points=[body.matrix_world@v.co for v in body.data.vertices];tri=[tuple(t.vertices) for t in body.data.loop_triangles];volume=sum(points[a].dot(points[b].cross(points[c])) for a,b,c in tri)/6
  if volume<0:tri=[(c,b,a) for a,b,c in tri]
  bvh=BVHTree.FromPolygons(points,tri,all_triangles=True);bw=[weights(body,v) for v in body.data.vertices];out=root/sp/'candidate-b';out.mkdir(parents=True,exist_ok=True);newrow=dict(row);newrow['fins']={};changes={}
  tail_x=min(p.x for p in points);tail_tri=[t for t in tri if max(points[i].x for i in t)<=tail_x+row['length_native']*.025 and (points[t[1]]-points[t[0]]).cross(points[t[2]]-points[t[0]]).normalized().x<-.5]
  assert tail_tri,'No posterior body attachment surface'
  tail_bvh=BVHTree.FromPolygons(points,tail_tri,all_triangles=True)
  for name,selection in row['fins'].items():
   o=bpy.data.objects[name];ids=selection['ids'];maxshift=0.;original_count=len(o.data.vertices)
   if name in targets:
    attr=o.data.attributes.new('foundry_fin_root','FLOAT','POINT')
    for i in ids:attr.data[i].value=1
    # Subdivide every basal edge long enough to bridge body curvature. Blender
    # interpolates UVs and deform weights; free distal topology stays untouched.
    bm=bmesh.new();bm.from_mesh(o.data);layer=bm.verts.layers.float['foundry_fin_root'];edges=[edge for edge in bm.edges if all(v[layer]>.99999 for v in edge.verts)];maxedge=max((e.calc_length() for e in edges),default=0)
    cuts=min(48,max(0,math.ceil(maxedge/(.35/row['scale_cm']))-1))
    if cuts:bmesh.ops.subdivide_edges(bm,edges=edges,cuts=cuts,use_grid_fill=False)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
    ids=[v.index for v in o.data.vertices if o.data.attributes['foundry_fin_root'].data[v.index].value>.99999]
    coords=[o.matrix_world@v.co for v in o.data.vertices];old=[weights(o,v) for v in o.data.vertices];tree=KDTree(len(ids))
    for j,i in enumerate(ids):tree.insert(coords[i],j)
    tree.balance();rootset=set(ids);extent=max((max(p[k] for p in coords)-min(p[k] for p in coords)) for k in range(3));blend=extent*.28;inset=.05/row['scale_cm'];updated=[]
    for i,p in enumerate(coords):
     distance=tree.find(p)[2];gain=1. if i in rootset else 1-smooth(distance/max(blend,1e-8))
     if gain<1e-8:updated.append((p,old[i]));continue
     posterior=name.startswith('Caudal')
     hit,n,face,_=(tail_bvh if posterior else bvh).find_nearest(p);assert n.length>.5;target=hit-n*inset;q=p.lerp(target,gain);a,b,c=(tail_tri if posterior else tri)[face]
     bary=barycentric_transform(hit,points[a],points[b],points[c],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));bodyweights={}
     for vi,amount in zip((a,b,c),bary):
      for group,w in bw[vi].items():bodyweights[group]=bodyweights.get(group,0)+w*max(0,amount)
     wts={group:w*(1-gain) for group,w in old[i].items()}
     for group,w in bodyweights.items():wts[group]=wts.get(group,0)+w*gain
     total=sum(wts.values());wts={g:w/total for g,w in wts.items() if w>1e-8};updated.append((q,wts));maxshift=max(maxshift,(q-p).length*row['scale_cm'])
    # Cache all Blender RNA data before adding groups (CustomData can invalidate references).
    names=set(g for _,w in updated for g in w)
    for group in names:
     if not o.vertex_groups.get(group):o.vertex_groups.new(name=group)
    inv=o.matrix_world.inverted()
    for i,(p,wts) in enumerate(updated):
     o.data.vertices[i].co=inv@p
     for g in o.vertex_groups:g.remove([i])
     for g,w in wts.items():o.vertex_groups[g].add([i],w,'REPLACE')
    o.data.update();changes[name]={'original_vertices':original_count,'new_vertices':len(o.data.vertices),'root_vertices':len(ids),'basal_edge_subdivision_cuts':cuts,'maximum_shift_cm':maxshift,'inset_cm':.05,'distal_blend_fraction':.28}
   rootcoords=[o.matrix_world@o.data.vertices[i].co for i in ids];sel=dict(selection);sel['ids']=ids;sel['rest_points_gltf']=[[p.x,p.z,-p.y] for p in rootcoords];sel['vertices']=len(o.data.vertices);newrow['fins'][name]=sel
  # Unmodified body/jaw vertices and rest bones are frozen witnesses.
  unchanged={o.name:hashlib.sha256(str([(tuple(v.co),weights(o,v)) for v in o.data.vertices]).encode()).hexdigest() for o in meshes if o.name not in targets};rig.data.pose_position='POSE';scene.frame_set(scene.frame_start);bpy.context.view_layer.update();outputs={'blend':out/'fish.blend','glb':out/'fish.glb'};export_native(outputs,rig,meshes);checks=binary_inspect(outputs['glb'])
  newrow['model']=str(outputs['glb']);newrow['model_sha256']=sha(outputs['glb']);newrow['changes']=changes;newrow['preserved_mesh_witnesses']=unchanged;result['items'].append(newrow);(out/'repair.validation.json').write_text(json.dumps({'ok':True,'status':'done','next_action':'human_review','species':sp,'changes':changes,'checks':checks,'runtime_contact_status':'pending'},indent=2));print('REPAIR_DONE',sp,list(changes),flush=True)
 Path(args[3]).write_text(json.dumps(result,indent=2))
if __name__=='__main__':main()
