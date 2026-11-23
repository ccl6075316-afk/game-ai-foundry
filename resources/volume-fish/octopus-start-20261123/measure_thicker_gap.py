import bpy,math,json,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent;reports=[]
for version in ['motion-r4','motion-r5']:
 O=R/version;build=json.loads((R/'motion-r3/rest/gray-build.validation.json').read_text());p=build['control_paths'][7];root=Vector(p[0]);end=Vector(p[-1]);L=(end-root).length;direction=(end-root).normalized();side=direction.cross(Vector((0,0,1))).normalized()
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(O/'octopus-actions.glb'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');skin=bpy.data.objects['Octopus_gray_skin']
 for tr in rig.animation_data.nla_tracks:tr.mute=True
 a=bpy.data.actions['TightRoll'];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0)
 bones=sorted([b for b in rig.pose.bones if b.name.startswith('R_IV_')],key=lambda b:int(b.name.rsplit('_',1)[1]));ss=[(b.bone.head_local-root).dot(direction) for b in bones];angle=[0.]
 for a,b in zip(bones,bones[1:]):angle.append(angle[-1]+a.vector.angle(b.vector))
 dg=bpy.context.evaluated_depsgraph_get();ev=skin.evaluated_get(dg);me=ev.to_mesh();verts=[];turn=[]
 for v in skin.data.vertices:
  s=(v.co-root).dot(direction);off=v.co-root-s*direction
  if .35*L<s<L+.01 and off.length<.2:
   verts.append(ev.matrix_world@me.vertices[v.index].co);turn.append(float(np.interp(s,ss,angle)))
 pts=np.array(verts);angles=np.array(turn);best=(100.,0,0)
 # Different layers, separated by >=270 degrees along the actual posed chain.
 for k in range(len(pts)):
  mask=np.abs(angles-angles[k])>1.5*math.pi
  dist=np.linalg.norm(pts-pts[k],axis=1);dist[~mask]=100.;j=int(np.argmin(dist))
  if dist[j]<best[0]:best=(float(dist[j]),k,j)
 ev.to_mesh_clear()
 tree=BVHTree.FromPolygons([v.co for v in skin.data.vertices],[list(f.vertices)for f in skin.data.polygons],all_triangles=True);widths=[]
 for f in [.50,.70,.80,.90,.95,.98,.99]:
  c=root+direction*(L*f);a=tree.ray_cast(c+side*.25,-side,.5)[0];b=tree.ray_cast(c-side*.25,side,.5)[0];widths.append({'arm_fraction':f,'actual_skin_width_ML':(a-b).length})
 reports.append({'version':version,'model_sha256':hashlib.sha256((O/'octopus-actions.glb').read_bytes()).hexdigest(),'width_samples':widths,'min_sampled_skin_vertex_gap_between_layers_ML':best[0],'nearest_pair':[list(verts[best[1]]),list(verts[best[2]])],'complete_curl_turns':angle[-1]/math.tau,'last_half_bone_bounds':[[min(b.head[k]for b in bones[len(bones)//2:]),max(b.head[k]for b in bones[len(bones)//2:])]for k in range(3)]})
checks={'rest_skin_widths_increased':all(b['actual_skin_width_ML']>a['actual_skin_width_ML'] for a,b in zip(reports[0]['width_samples'],reports[1]['width_samples'])),'finite_positive_layer_gap':0<reports[1]['min_sampled_skin_vertex_gap_between_layers_ML']<.03}
d={'ok':all(checks.values()),'checks':checks,'measurements':reports,'method':'Cold GLB R_IV: rest-surface opposing ray width; pose0 finite skin vertices from different curl layers identified by >=270deg bone turning separation. Vertex gap is an upper bound on true surface gap, not proof of skin contact.','limits':['No biological thickness calibration','No claimed suction attachment or exact zero-gap skin contact; gap value is descriptive, not a biological threshold']};(R/'motion-r5/shape-change.validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
