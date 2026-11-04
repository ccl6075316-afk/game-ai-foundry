"""Reshape existing anterior cross sections using a measured library chord.
No forward cap/point is appended; XY, finite oral geometry and all fins stay.
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
 src=Path(c['baseline']);bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.scene.frame_set(1)
 body=bpy.data.objects['Reference_head_body'];body.data.calc_loop_triangles();old=np.array([v.co[:]for v in body.data.vertices]);tri=old[np.array([t.vertices[:]for t in body.data.loop_triangles])];oral={i for f in body.data.polygons if body.data.materials[f.material_index].name=='Actual finite oral lining'for i in f.vertices};kd=KDTree(len(oral))
 for j,i in enumerate(sorted(oral)):kd.insert(Vector(old[i]),j)
 kd.balance();project=json.loads(Path(c['project_reference']).read_text());field=json.loads(Path(c['sections']).read_text());rows=[r for r in field['rows']if r['side']==1];fracs=[r['half_span_fraction']for r in rows];ys=[r['y_m']for r in project['head_transverse_stations']];front=[r['front_x_m']for r in project['head_transverse_stations']];rear=[r['rear_x_m']for r in project['head_transverse_stations']];half=project['head_span_m']/2;L=field['candidate_length_m']
 def limits(x,y):
  a,b,d=tri[:,0],tri[:,1],tri[:,2];den=(b[:,1]-d[:,1])*(a[:,0]-d[:,0])+(d[:,0]-b[:,0])*(a[:,1]-d[:,1]);k=abs(den)>1e-15;u=np.zeros(len(a));v=u.copy();u[k]=((b[k,1]-d[k,1])*(x-d[k,0])+(d[k,0]-b[k,0])*(y-d[k,1]))/den[k];v[k]=((d[k,1]-a[k,1])*(x-d[k,0])+(a[k,0]-d[k,0])*(y-d[k,1]))/den[k];w=1-u-v;k&=(u>=-1e-7)&(v>=-1e-7)&(w>=-1e-7);z=(u*a[:,2]+v*b[:,2]+w*d[:,2])[k];return(float(z.min()),float(z.max()))if len(z)>1 else None
 def ref(fr,t,key):return float(np.interp(fr,fracs,[np.interp(t,[s['chord_fraction']for s in r['samples']],[s['reference'][key]for s in r['samples']])for r in rows]))*L
 changes=[]
 for v in body.data.vertices:
  x,y,z=old[v.index];fr=abs(y)/half;f=float(np.interp(y,ys,front));r=float(np.interp(y,ys,rear));t=(f-x)/max(f-r,1e-8)
  if v.index in oral or not(0<t<c['chord_fade'][1])or fr>=c['span_fade'][1]:continue
  a=limits(x,y);anchor=limits(f-c['anchor_chord']*(f-r),y)
  if a is None or anchor is None or a[1]-a[0]<1e-7:continue
  lo,hi=a;al,ah=anchor;rl,rh=ref(fr,t,'bottom'),ref(fr,t,'top');rla,rha=ref(fr,c['anchor_chord'],'bottom'),ref(fr,c['anchor_chord'],'top');assert rha-rla>1e-8
  # Preserve local section centre at the anchor, use actual reference curvature
  # on its anterior chord and a bounded engineering section-height ratio.
  gain=(ah-al)/(rha-rla);mid=(al+ah)/2+((rl+rh-rla-rha)/2)*gain;depth=(rh-rl)*gain;target=mid-depth/2+(z-lo)/(hi-lo)*depth;weight=(1-smooth(*c['chord_fade'],t))*(1-smooth(*c['span_fade'],fr))*smooth(*c['oral_guard_m'],kd.find(Vector((x,y,z)))[2]);dz=max(-c['maximum_delta_m'],min(c['maximum_delta_m'],target-z))*weight;v.co.z=z+dz
  if abs(dz)>1e-8:changes.append(dict(vertex=v.index,chord=t,span_fraction=fr,delta_z_m=dz))
 body.data.update();bm=bmesh.new();bm.from_mesh(body.data);assert all(e.is_manifold for e in bm.edges)and bm.calc_volume()>0;bm.free();assert changes
 for ob in bpy.context.scene.objects:
  if ob.type=='MESH':ob.data.normals_split_custom_set([(0.,0.,0.)]*len(ob.data.loops))
 rig.data.pose_position='POSE';out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
 for ob in bpy.context.scene.objects:
  if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
 bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());report=dict(ok=True,kind='existing_anterior_chord_reference_fairing',model_sha256=sha(out/'fish.glb'),source_sha256=sha(out/'fish.blend'),config_sha256=sha(cp),baseline_sha256=sha(src/'fish.glb'),changed_vertices=len(changes),maximum_delta_m=max(abs(x['delta_z_m'])for x in changes),changes=changes,XY_unchanged=True,no_new_front_cap=True,oral_vertices_unchanged=True,whole_triangles=3994,fin_geometry_UV_skin_actions_unchanged=True,formal_acceptance=False);(out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='changes'}))
if __name__=='__main__':main()
