"""User-directed ventral prenarial flattening; dorsal snout is protected.

Raises the bulging underside to the straight bridge from actual leading lower
surface to the actual upper oral rim. It adds no forward point or mesh layer.
"""
import bpy,bmesh,sys,json,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def main():
 cp,out=map(lambda x:Path(x).resolve(),sys.argv[sys.argv.index('--')+1:]);c=json.loads(cp.read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert not out.exists()and'/experiments/'in str(out)
 for p,h in c['inputs'].items():assert sha(p)==h,p
 src=Path(c['baseline']);bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.scene.frame_set(1);body=bpy.data.objects['Reference_head_body'];body.data.calc_loop_triangles();old=np.array([v.co[:]for v in body.data.vertices]);ts=list(body.data.loop_triangles);ids=np.array([t.vertices[:]for t in ts]);tri=old[ids];oralfaces=np.array([body.data.materials[body.data.polygons[t.polygon_index].material_index].name=='Actual finite oral lining'for t in ts]);oralids=set(ids[oralfaces].ravel());oraltri=tri[oralfaces];kd=KDTree(len(oralids))
 for j,i in enumerate(sorted(oralids)):kd.insert(Vector(old[i]),j)
 kd.balance();project=json.loads(Path(c['project_reference']).read_text());ys=[r['y_m']for r in project['head_transverse_stations']];front=[r['front_x_m']for r in project['head_transverse_stations']]
 def limits(x,y):
  a,b,d=tri[:,0],tri[:,1],tri[:,2];den=(b[:,1]-d[:,1])*(a[:,0]-d[:,0])+(d[:,0]-b[:,0])*(a[:,1]-d[:,1]);k=abs(den)>1e-15;u=np.zeros(len(a));v=u.copy();u[k]=((b[k,1]-d[k,1])*(x-d[k,0])+(d[k,0]-b[k,0])*(y-d[k,1]))/den[k];v[k]=((d[k,1]-a[k,1])*(x-d[k,0])+(a[k,0]-d[k,0])*(y-d[k,1]))/den[k];w=1-u-v;k&=(u>=-1e-7)&(v>=-1e-7)&(w>=-1e-7);z=(u*a[:,2]+v*b[:,2]+w*d[:,2])[k];return(float(z.min()),float(z.max()))if len(z)>1 else None
 def oral_front(y):
  y=max(-.064,min(.064,y));a=oraltri;b=np.roll(a,-1,axis=1);k=(a[:,:,1]-y)*(b[:,:,1]-y)<0;q=a[k]+((y-a[:,:,1][k])/(b[:,:,1][k]-a[:,:,1][k]))[:,None]*(b[k]-a[k]);q=np.concatenate([q,a[abs(a[:,:,1]-y)<1e-7]]);assert len(q);x=float(q[:,0].max());top=float(q[q[:,0]>x-1e-6,2].max());return x,top
 changes=[];anchors=[]
 for v in body.data.vertices:
  i=v.index;x,y,z=old[i]
  if i in oralids or abs(y)>=c['span_fade_m'][1]:continue
  ox,oz=oral_front(y);fx=float(np.interp(y,ys,front))-c['leading_inset_m']
  if not ox<x<fx:continue
  lim=limits(x,y);end=limits(fx,y)
  if lim is None or end is None or lim[1]-lim[0]<1e-6:continue
  lo,hi=lim;t=(z-lo)/(hi-lo)
  if t>=c['lower_fraction_fade'][1]:continue
  line=oz+(end[0]-oz)*(x-ox)/(fx-ox);raise_by=max(0.,line-lo);weight=(1-smooth(*c['lower_fraction_fade'],t))*(1-smooth(*c['span_fade_m'],abs(y)))*smooth(*c['rim_guard_m'],kd.find(Vector((x,y,z)))[2]);dz=raise_by*weight
  if dz>1e-8:v.co.z+=dz;changes.append(dict(vertex=i,old=list(old[i]),delta_z_m=dz,section_height_fraction=t,target_lower_z_m=line));anchors.append(dict(y_m=y,oral_front_x_m=ox,upper_rim_z_m=oz,leading_x_m=fx,leading_lower_z_m=end[0]))
 assert changes;body.data.update();bm=bmesh.new();bm.from_mesh(body.data);assert all(e.is_manifold for e in bm.edges)and bm.calc_volume()>0;bm.free();body.data.normals_split_custom_set([(0.,0.,0.)]*len(body.data.loops));rig.data.pose_position='POSE';out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
 for ob in bpy.context.scene.objects:
  if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
 bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());r=dict(ok=True,kind='user_directed_ventral_prenasal_flatten',model_sha256=sha(out/'fish.glb'),blend_sha256=sha(out/'fish.blend'),config_sha256=sha(cp),baseline_sha256=sha(src/'fish.glb'),whole_triangles=3994,changed_vertices=len(changes),maximum_raise_m=max(x['delta_z_m']for x in changes),changes=changes,anchors=anchors,dorsal_snout_unchanged=True,XY_unchanged=True,oral_vertices_unchanged=True,eyes_fins_rig_materials_unchanged=True,formal_acceptance=False);(out/'authoring.validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k not in ['changes','anchors']}))
if __name__=='__main__':main()
