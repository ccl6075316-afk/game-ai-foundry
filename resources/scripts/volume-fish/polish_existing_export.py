"""Versioned, bounded repairs of frozen existing game GLBs, including legacy exports.

This preserves the imported topology, rest bones, groups and animation. It does
not create a new volume acceptance or bypass source-generation gates for new fish.
"""
import bpy,bmesh,json,math,sys,hashlib,struct
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).parent))
from build_fish import export_native,binary_inspect
args=sys.argv[sys.argv.index('--')+1:];planpath=Path(args[0]).resolve();plan=json.loads(planpath.read_text(encoding='utf-8'));selected=args[1:]
sha=lambda q:hashlib.sha256(Path(q).read_bytes()).hexdigest()
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def inside(point,poly):
 x,y=point;odd=False
 for (ax,ay),(bx,by) in zip(poly,poly[1:]+poly[:1]):
  if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:odd=not odd
 return odd
def fingerprint(rig,meshes):
 return {'bones':[(b.name,tuple(b.head_local),tuple(b.tail_local),b.parent.name if b.parent else None) for b in rig.data.bones],
         'topology':{o.name:(len(o.data.vertices),[tuple(p.vertices) for p in o.data.polygons]) for o in meshes},
         'weights':{o.name:[[(o.vertex_groups[g.group].name,round(g.weight,7)) for g in v.groups] for v in o.data.vertices] for o in meshes}}
for e in plan['items']:
 if selected and e['species'] not in selected:continue
 assert sha(e['baseline_glb'])==e['glb_sha256'];assert sha(e['source'])==e['source_actual_sha256'];assert sha(e['baseline_side'])==e['baseline_render_sha256']
 out=Path(e['output_directory']);out.mkdir(parents=True,exist_ok=True);bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=e['baseline_glb'])
 scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE');meshes=[o for o in scene.objects if o.type=='MESH'];before=fingerprint(rig,meshes)
 # glTF import restores NLA actions. Make the same clip active for native export.
 data=rig.animation_data
 if data and not data.action:
  strips=[s for t in data.nla_tracks for s in t.strips]
  if strips:
   action=strips[0].action;slot=strips[0].action_slot
   for track in list(data.nla_tracks):data.nla_tracks.remove(track)
   data.action=action
   if slot:data.action_slot=slot
 action=data.action if data else None;assert action is not None,'Missing original exported animation'
 frames=action.frame_range;scene.frame_start=round(frames[0]);scene.frame_end=round(frames[1]);scene.render.fps=24
 original_action=action.copy();original_action.name='Polish immutable clip witness'
 mapping=e['pixel_mapping'];s=mapping['pixels_per_unit'];cx=mapping['center_x'];cy=mapping['center_y'];w=mapping['width'];h=mapping['height']
 source=bpy.data.images.load(e['source'],check_existing=True);source.pack();src=np.array(source.pixels[:]).reshape(h,w,4)[::-1,:,3]>.5
 old_image=bpy.data.images.load(e['baseline_side'],check_existing=False);old=np.array(old_image.pixels[:]).reshape(h,w,4)[::-1,:,3]>.5
 ys,xs=np.where(src);xmin,xmax=int(xs.min()),int(xs.max());span=xmax-xmin
 top=np.full(w,np.nan);bottom=np.full(w,np.nan);ot=top.copy();ob=top.copy()
 for x in range(w):
  a=np.flatnonzero(src[:,x]);b=np.flatnonzero(old[:,x])
  if len(a):top[x]=a[0];bottom[x]=a[-1]
  if len(b):ot[x]=b[0];ob[x]=b[-1]
 for arr in [top,bottom,ot,ob]:
  valid=np.flatnonzero(np.isfinite(arr));arr[:]=np.interp(np.arange(w),valid,arr[valid])
 # Smooth pixel stair steps; the target is the recognizable shape, not every voxel.
 for arr in [top,bottom,ot,ob]:arr[:]=np.convolve(np.pad(arr,(3,3),mode='edge'),np.ones(7)/7,mode='valid')
 change=e['change'];mode=change['mode'];moved={};uv_loops=0;maxshift=0.
 def map_point(point):
  q=point.copy();px=point.x*s+cx
  if mode=='head_affine':
   t=(px-xmin)/span;gain=change['gain']*smooth((t-change['start'])/(change['full']-change['start']))
   if t>change['end']:gain*=1-smooth((t-change['end'])/max(.001,1-change['end']))
  elif mode=='tail_affine':
   u=px/w;gain=change['gain']*(1-smooth((u-change['fade_start_u'])/(change['end_u']-change['fade_start_u'])))
  else:return q
  if gain<=0 or not 0<=px<w:return q
  x=int(px);oldtop=(cy-ot[x])/s;oldbottom=(cy-ob[x])/s;newtop=(cy-top[x])/s;newbottom=oldbottom if change.get('top_only') else (cy-bottom[x])/s
  if oldtop-oldbottom<2/s:return q
  target=newbottom+(q.z-oldbottom)*(newtop-newbottom)/(oldtop-oldbottom);q.z+=(target-q.z)*gain
  return q
 for obj in meshes:
  if mode=='head_affine':
   if obj.name.startswith(('Textured_eye','Sphere','Eye_','Iris','Pupil','Lower_jaw_barbel')):
    center=sum((obj.matrix_world@v.co for v in obj.data.vertices),Vector())/len(obj.data.vertices);delta=map_point(center)-center
    values=[obj.matrix_world@v.co+delta for v in obj.data.vertices]
   else:values=[map_point(obj.matrix_world@v.co) for v in obj.data.vertices]
  elif mode=='tail_affine' and obj.name.startswith(change['mesh']):values=[map_point(obj.matrix_world@v.co) for v in obj.data.vertices]
  elif mode=='pectoral_cant' and obj.name.startswith('Pectoral_'):
   bone=rig.data.bones.get(obj.name);assert bone is not None
   anchor=rig.matrix_world@bone.head_local;own=obj.vertex_groups.get(bone.name);assert own is not None;values=[]
   for v in obj.data.vertices:
    weight=sum(g.weight for g in v.groups if g.group==own.index);gain=smooth((weight-change['fixed_own_weight_max'])/(change['full_own_weight']-change['fixed_own_weight_max']))
    angle=(-1 if anchor.y>0 else 1)*math.radians(change['degrees'])*gain
    point=obj.matrix_world@v.co;values.append(anchor+Matrix.Rotation(angle,3,'X')@(point-anchor))
  else:continue
  inv=obj.matrix_world.inverted();n=0
  for v,q in zip(obj.data.vertices,values):
   delta=(q-obj.matrix_world@v.co).length;maxshift=max(maxshift,delta);n+=delta>1e-9;v.co=inv@q
  obj.data.update();moved[obj.name]=n
 # Restore the unmodified side pixels on lateral head faces. No image rewriting.
 if mode=='side_uv' or change.get('reproject'):
  body=next(o for o in meshes if o.name.startswith(change['body']));body.data.update();patches=[]
  if e.get('profile'):patches=json.loads(Path(e['profile']).read_text(encoding='utf-8')).get('body_uv_patches',[])
  first=body.data.materials[0]
  donors=[n.image for n in first.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] if first and first.use_nodes else []
  if any(tuple(image.size)==(w,h) for image in donors):
   # Reuse the existing side material, including its authored emission. A new
   # material with different lighting would create an artificial head seam.
   mi=0
  else:
   material=bpy.data.materials.new('071 original side donor');material.use_nodes=True;nodes=material.node_tree.nodes;bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');tex=nodes.new('ShaderNodeTexImage');tex.image=source;tex.interpolation='Closest';material.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color']);bsdf.inputs['Roughness'].default_value=1.;body.data.materials.append(material);mi=len(body.data.materials)-1
  start=change['start'];startx=xmin+start*span if mode=='head_affine' else start*w
  for poly in body.data.polygons:
   center=sum((body.matrix_world@body.data.vertices[i].co for i in poly.vertices),Vector())/len(poly.vertices)
   if center.x*s+cx<startx or abs(poly.normal.y)<change.get('normal_y_min',.5):continue
   poly.material_index=mi
   for li in poly.loop_indices:
    co=body.matrix_world@body.data.vertices[body.data.loops[li].vertex_index].co;px=co.x*s+cx;py=cy-co.z*s;ix=max(0,min(w-1,int(px)));py=max(top[ix]+1,min(bottom[ix]-1,py));uv=[px/w,py/h]
    for patch in patches:
     if change.get('source_eye_on_body') and sum(p[0] for p in patch['polygon'])/len(patch['polygon'])>.90:continue
     if inside(uv,patch['polygon']):uv=[uv[0]+patch['offset'][0],uv[1]+patch['offset'][1]];break
    body.data.uv_layers.active.data[li].uv=(uv[0],1-uv[1]);uv_loops+=1
  if change.get('eye_uv'):
   for obj in meshes:
    if not obj.name.startswith('Textured_eye_'):continue
    obj.data.materials.clear();obj.data.materials.append(body.data.materials[mi])
    for poly in obj.data.polygons:
     poly.material_index=0
     for li in poly.loop_indices:
      point=obj.matrix_world@obj.data.vertices[obj.data.loops[li].vertex_index].co
      obj.data.uv_layers.active.data[li].uv=((point.x*s+cx)/w,1-(cy-point.z*s)/h)
  if change.get('source_eye_on_body'):
   transparent=bpy.data.materials.new('071 preserve source eye; suppress opaque auxiliary patch');transparent.use_nodes=True
   bsdf=next(n for n in transparent.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bsdf.inputs['Alpha'].default_value=0.;transparent.surface_render_method='DITHERED'
   for obj in meshes:
    if obj.name.startswith('Textured_eye_'):
     obj.data.materials.clear();obj.data.materials.append(transparent)
     for poly in obj.data.polygons:poly.material_index=0
 for mat in bpy.data.materials:
  if not mat.use_nodes:continue
  for node in mat.node_tree.nodes:
   if node.type=='TEX_IMAGE':node.interpolation='Closest'
   if node.type=='BSDF_PRINCIPLED':
    node.inputs['Metallic'].default_value=0.;node.inputs['Roughness'].default_value=1.;node.inputs['Specular IOR Level'].default_value=0.
 after=fingerprint(rig,meshes);assert before==after,'Topology, bone rest or groups changed'
 # Save only the imported clip; the witness action is comparison data, not a new clip.
 assert list(action.frame_range)==list(original_action.frame_range)
 bpy.data.actions.remove(original_action);scene.frame_set(scene.frame_start)
 outputs={'blend':out/'fish.blend','glb':out/'fish.glb'};export_native(outputs,rig,meshes)
 if mode=='pixel_material_only':
  # Sampler/PBR-only repairs retain the original BIN byte-for-byte. Importing
  # and resampling a67-bone legacy clip would add avoidable float drift.
  raw=Path(e['baseline_glb']).read_bytes();size=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+size]);tail=raw[20+size:]
  for sampler in doc.get('samplers',[]):sampler.update(magFilter=9728,minFilter=9728)
  for material in doc.get('materials',[]):
   material.setdefault('pbrMetallicRoughness',{}).update(metallicFactor=0.,roughnessFactor=1.)
   if 'KHR_materials_specular' in material.get('extensions',{}):material['extensions']['KHR_materials_specular']['specularFactor']=0.
  encoded=json.dumps(doc,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
  outputs['glb'].write_bytes(struct.pack('<4sII',b'glTF',2,20+len(encoded)+len(tail))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+tail)
  revised=outputs['glb'].read_bytes();newsize=struct.unpack_from('<I',revised,12)[0];assert revised[20+newsize:]==tail
 info=binary_inspect(outputs['glb']);checks={'original_sources_unchanged':sha(e['source'])==e['source_actual_sha256'],'topology_weights_rest_bones_preserved':before==after,'finite_glb':info['nonfinite_components']==0,'animation_exported':bool(info['animation_tracks']),'animation_loop':all(t['seam_delta']<1e-5 for t in info['animation_tracks']),'nearest':info['nearest'],'roughness':info['roughness']}
 result={'ok':all(checks.values()),'status':'done' if all(checks.values()) else 'failed','next_action':'human_review' if all(checks.values()) else 'fix_input','species':e['species'],'scope':'Bounded repair of frozen existing GLB, retaining imported topology and bone rest/groups; not a new species source acceptance.','plan_sha256':sha(planpath),'baseline_glb_sha256':e['glb_sha256'],'source_sha256':e['source_actual_sha256'],'glb_sha256':sha(outputs['glb']),'blend_sha256':sha(outputs['blend']),'checks':checks,'change':change,'moved_vertices':moved,'maximum_shift_native':maxshift,'reprojected_uv_loops':uv_loops,'glb':info}
 (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print('POLISH071',e['species'],result['ok'],flush=True)
 if not result['ok']:raise RuntimeError(result)
