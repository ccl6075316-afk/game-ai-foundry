"""Sparse continuous section lofts, replacing corrugated inherited fin faces."""
import bpy,bmesh,json,sys,math,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[3];args=sys.argv[sys.argv.index('--')+1:];src=Path(args[0]).resolve();out=Path(args[1]).resolve();assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));old=json.loads((src/'fin-authoring.json').read_text());layout=json.loads((ROOT/'resources/volume-fish/blacktip-fin-cages-20261101.json').read_text());cfg=json.loads((ROOT/'resources/volume-fish/blacktip-review-repair-20261101.json').read_text());legacy=json.loads((ROOT/cfg['legacy_profile']).read_text());aspect=1/legacy['source_aspect_ratio'];body=bpy.data.objects['Closed_body'];body.data.calc_loop_triangles();tree=BVHTree.FromPolygons([v.co for v in body.data.vertices],[t.vertices for t in body.data.loop_triangles],all_triangles=True);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');material=bpy.data.objects['FirstDorsal'].data.materials[0];records=[]
def interp(path,t):
 lengths=[0.]
 for a,b in zip(path,path[1:]):lengths.append(lengths[-1]+(b-a).length)
 target=t*lengths[-1]
 for i in range(len(path)-1):
  if target<=lengths[i+1]:return path[i].lerp(path[i+1],(target-lengths[i])/max(lengths[i+1]-lengths[i],1e-9))
 return path[-1].copy()
def weights(p,name,gain):
 h,n,fi,d=tree.find_nearest(p);tri=body.data.loop_triangles[fi];mix={}
 # Exact local support selection; nearest vertex supplies a coherent root rig.
 vi=min(tri.vertices,key=lambda i:(body.data.vertices[i].co-h).length)
 for g in body.data.vertices[vi].groups:mix[body.vertex_groups[g.group].name]=g.weight*(1-gain)
 if gain:mix[name]=mix.get(name,0)+gain
 total=sum(mix.values());return {k:v/total for k,v in mix.items()if v>1e-7}
for row in old['fins']:
 name=row['name'];f=next(f for f in layout['rows']if name==f['name']or name.startswith(f['name']+'_'));paired=f['paired'];side=-1 if name.endswith('_left')else 1;contour=[Vector(p)for p in f['contour']];base=[p for p,r in zip(contour,f['root'])if r];start=next(i for i in range(len(contour))if not f['root'][i]and f['root'][(i-1)%len(contour)]);run=[];i=start
 while not f['root'][i]:run.append(i);i=(i+1)%len(contour)
 first=(start-1)%len(contour);last=i;free=[contour[first]]+[contour[i]for i in run]+[contour[last]];rootpath=[contour[first]];i=(first-1)%len(contour)
 while i!=last:rootpath.append(contour[i]);i=(i-1)%len(contour)
 rootpath.append(contour[last]);tip=min(range(1,len(free)-1),key=lambda i:(free[i]-Vector(f['source']['tip'])).length);left=free[:tip+1];right=list(reversed(free[tip:]));rootcurve=rootpath;spanlevels=[0,.15,.37,.62,.84,.985]if '--compact'in args else[0,.12,.30,.52,.74,.90,.985];chords=[0,.20,.40,.65,.85,1.]if '--compact'in args else[0,.15,.32,.50,.72,.90,1.];nc=len(chords);ns=len(spanlevels);verts=[];qs=[];wts=[];rootids=[];anchor=Vector(f['source']['anchor']);normal=Vector((0,0,1))if paired else Vector((0,1,0));tr,tm,te=cfg['fin_full_thickness_native'][f['name']]
 def nominal(q,s):
  v=anchor.y+(q.y-anchor.y)*f['vertical_scale'];return Vector((q.x-.5,side*(f['source']['root_depth']+(f['source']['tip_depth']-f['source']['root_depth'])*s)if paired else 0,(.5-v)*aspect))
 roots={}
 for layer in[-1,1]:
  for j,t in enumerate(chords):
   q=interp(rootcurve,t);p=nominal(q,0);half=te/2+(tr-te)/2*math.sin(math.pi*t)**.7;p+=normal*layer*half
   if paired:
    low,_,_,_=tree.ray_cast(Vector((p.x,0,-2)),Vector((0,0,1)),4)
    high,_,_,_=tree.ray_cast(Vector((p.x,0,2)),Vector((0,0,-1)),4)
    assert low is not None and high is not None
    p.z=max(low.z+.002,min(high.z-.002,p.z))
   direction=Vector((0,side,0))if paired else Vector((0,0,-1 if name in['Anal','CaudalLower']else 1))
   origin=p+direction*2;h,n,fi,d=tree.ray_cast(origin,-direction,4)
   if h is None:h,n,fi,d=tree.find_nearest(p)
   roots[layer,j]=(h+n*.00008,q)
 maxy=max(abs(p.y)for p,q in roots.values());maxz=max(p.z for p,q in roots.values());minz=min(p.z for p,q in roots.values())
 for layer in[-1,1]:
  for k,s in enumerate(spanlevels):
   a,b=interp(left,s),interp(right,s)
   for j,t in enumerate(chords):
    q=interp(rootcurve,t)if k==0 else a.lerp(b,t);p=nominal(q,s);full=te+(tr*(1-s)**1.25-te)*max(0,math.sin(math.pi*t))**.7
    if k==0:p,q=roots[layer,j];rootids.append(len(verts))
    else:
     if paired:p.y=side*(maxy+.0015+(f['source']['tip_depth']-maxy-.0015)*s)
     elif not name.startswith('Caudal'):
      tipz=nominal(free[tip],1).z
      p.z=(minz+s*(tipz-minz))if name=='Anal'else(maxz+s*(tipz-maxz))
     p+=normal*layer*full/2
    verts.append(p);qs.append(q.copy());gain=0 if k==0 else .8*s*s;wts.append(weights(p,name,gain))
 faces=[];offset=nc*ns
 for layer in range(2):
  off=layer*offset
  for k in range(ns-1):
   for j in range(nc-1):
    ids=(off+k*nc+j,off+k*nc+j+1,off+(k+1)*nc+j+1,off+(k+1)*nc+j);faces.append(tuple(reversed(ids))if layer==0 else ids)
 boundary=list(range(nc))+[k*nc+nc-1 for k in range(1,ns)]+list(range((ns-1)*nc+nc-2,(ns-1)*nc-1,-1))+[k*nc for k in range(ns-2,0,-1)]
 for a,b in zip(boundary,boundary[1:]+boundary[:1]):faces.append((a,b,b+offset,a+offset))
 oldob=bpy.data.objects[name];bpy.data.objects.remove(oldob,do_unlink=True);mesh=bpy.data.meshes.new(name+' continuous span-chord loft');mesh.from_pydata(verts,[],faces);mesh.update();ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);ob.parent=rig;mesh.materials.append(material);uv=mesh.uv_layers.new()
 for poly in mesh.polygons:
  lower=paired and all(i<offset for i in poly.vertices);poly.use_smooth=True
  for li in poly.loop_indices:q=qs[mesh.loops[li].vertex_index];uv.data[li].uv=(q.x*.5+(.5 if lower else 0),1-q.y)
 for i,w in enumerate(wts):
  for n,g in w.items():(ob.vertex_groups.get(n)or ob.vertex_groups.new(name=n)).add([i],g,'REPLACE')
 mod=ob.modifiers.new('Original rig','ARMATURE');mod.object=rig;bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces));assert all(len(e.link_faces)==2 for e in bm.edges);bm.to_mesh(mesh);bm.free();mesh.calc_loop_triangles();records.append(dict(row,triangles=len(mesh.loop_triangles),vertices=len(mesh.vertices),root_ids=rootids,root_points_native=[list(verts[i])for i in rootids],source_root_curve=[list(q)for q in rootcurve],construction='Continuous7x7 section loft, both finite layers and complete original basal extent'))
body.data.calc_loop_triangles();total=len(body.data.loop_triangles)+sum(r['triangles']for r in records);assert total<=4000,total;bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
 if o.type in['MESH','ARMATURE']:o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_text(json.dumps({'body_triangles':len(body.data.loop_triangles),'whole_triangles':total,'fins':records},indent=2)+'\n');print('LOFT_TRIANGLES',total)
