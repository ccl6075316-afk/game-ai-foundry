"""Bake body-matched fin albedo/undersides and a finite caudal normal bridge.

All positions, topology, skin weights, rig, body/eye UV and pixels are frozen.
Fin colors are declared 2D body-pixel derivatives, not original fin RGB copies.
"""
import bpy,json,sys,hashlib,math,shutil
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from source_snapshot import rig_action_snapshot
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(x):
 x=max(0.,min(1.,float(x)));return x*x*x*(10+x*(-15+6*x))
def fingerprint(ob):
 m=ob.data
 return hashlib.sha256(repr(([(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in m.vertices],[tuple(p.vertices)for p in m.polygons])).encode()).hexdigest()
class Body:
 def __init__(self,ob,L):
  self.L=L;self.ob=ob;m=ob.data;m.calc_loop_triangles();self.v=np.array([v.co[:]for v in m.vertices]);self.tr=[];self.proj=[];self.uv=[];self.norm=[];image=None
  for tri in m.loop_triangles:
   mat=m.materials[tri.material_index]
   if mat.name=='Actual finite oral lining':continue
   images=[n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE'];assert len(images)==1
   if image is None:image=images[0]
   assert image==images[0]
   ids=list(tri.vertices);p=self.v[ids];e=np.stack([p[1]-p[0],p[2]-p[0]]);A=np.linalg.pinv(e@e.T)@e;UV=np.array([m.uv_layers.active.data[i].uv[:]for i in tri.loops]);N=np.array([m.corner_normals[i].vector[:]for i in tri.loops]);self.tr.append(ids);self.proj.append(A);self.uv.append(UV);self.norm.append(N)
  self.tr=np.array(self.tr);self.proj=np.array(self.proj);self.uv=np.array(self.uv);self.norm=np.array(self.norm);self.image=image;self.W,self.H=image.size;self.pixels=np.array(image.pixels[:],dtype=np.float32).reshape(self.H,self.W,4)
  self.tree=BVHTree.FromPolygons([Vector(v)for v in self.v],self.tr.tolist(),all_triangles=True)
  # An internal closed end-cap is not the visible tube side. Sampling its
  # center creates both a false color stripe and an axial shading normal.
  rear=self.v[:,0].min();self.outer_map=[i for i,t in enumerate(self.tr)if not np.all(abs(self.v[t,0]-rear)<L*1e-6)]
  self.outer_tree=BVHTree.FromPolygons([Vector(v)for v in self.v],self.tr[self.outer_map].tolist(),all_triangles=True)
  self.xs=np.linspace(self.v[:,0].min()+L*.0005,self.v[:,0].max()-L*.005,256);bounds=[];tris=self.v[self.tr]
  for x in self.xs:
   ps=[]
   for i,j in [(0,1),(1,2),(2,0)]:
    a,b=tris[:,i],tris[:,j];sel=(a[:,0]-x)*(b[:,0]-x)<0
    if sel.any():ps.extend(a[sel]+(b[sel]-a[sel])*((x-a[sel,0])/(b[sel,0]-a[sel,0]))[:,None])
   p=np.array(ps);assert len(p);bounds.append([abs(p[:,1]).max(),p[:,2].min(),p[:,2].max()])
  self.bounds=np.array(bounds)
 def query(self,p,normal=False,outer=False):
  foot,_,i,_=(self.outer_tree if outer else self.tree).find_nearest(Vector(p));assert i is not None
  if outer:i=self.outer_map[i]
  p=np.array(foot);ab=self.proj[i]@(p-self.v[self.tr[i,0]]);beta=np.array([1-ab.sum(),*ab]);uv=beta@self.uv[i];x=min(self.W-1,max(0,int(uv[0]*self.W)));y=min(self.H-1,max(0,int(uv[1]*self.H)));rgb=self.pixels[y,x,:3].copy()
  if normal:
   n=beta@self.norm[i];n/=max(np.linalg.norm(n),1e-20);return rgb,n
  return rgb
 def pigment(self,p,spatial,ventral=False,tail=False,root_x=0):
  if tail:x=root_x+self.L*(.014+.10*spatial+.025*smooth((p[0]-self.tail_xmin)/max(self.tail_dx,1e-8)))
  else:x=p[0]
  x=float(np.clip(x,self.xs[0],self.xs[-1]));w,lo,hi=[float(np.interp(x,self.xs,self.bounds[:,k]))for k in range(3)];phi=.10+.55*spatial;theta=math.pi+phi if ventral else phi;sign=-1 if p[1]<0 else 1
  return self.query((x,sign*w*math.sin(theta),(hi+lo)/2+(hi-lo)/2*math.cos(theta)))
 def tail_surface(self,p,root_x,cap_mid,cap_w,cap_h,normal=False):
  # Continue TWO-dimensional body pigment. Repeating the one end-cap column
  # through a long collar freezes its stripes and leaves a visible material
  # band even when every contact vertex has identical RGB.
  theta=math.atan2(p[1]/max(cap_w,1e-8),(p[2]-cap_mid)/max(cap_h,1e-8))
  advance=0. if normal else max(0.,root_x-p[0])
  x=min(self.xs[-1],root_x+max(self.L*1e-6,advance))
  lo,hi=[float(np.interp(x,self.xs,self.bounds[:,k]))for k in [1,2]]
  width=float(np.interp(x,self.xs,self.bounds[:,0]));direction=Vector((0.,width*math.sin(theta),(hi-lo)/2*math.cos(theta))).normalized()
  hit,_,_,_=self.outer_tree.ray_cast(Vector((x,0.,(lo+hi)/2)),direction)
  assert hit is not None,'No visible finite-body angular donor'
  return self.query(tuple(hit),normal,True)
def main():
 args=sys.argv[sys.argv.index('--')+1:];base,out=map(lambda x:Path(x).resolve(),args[:2]);src=Path(args[2]).resolve()if len(args)>2 else base/'candidate-r27';assert not out.exists()and'/experiments/'in str(out);L=4. if base.name=='great'else 3.;great=base.name=='great';bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));body=bpy.data.objects['Reference_head_body'];S=Body(body,L);auth=json.loads((src/'fin-authoring.json').read_text());actions=rig_action_snapshot();frozen={o.name:fingerprint(o)for o in bpy.context.scene.objects if o.type=='MESH'};bodyUV=np.array([l.uv[:]for l in body.data.uv_layers.active.data]);bodyPixels=S.pixels.copy();out.mkdir();records=[];old_materials=set();normal_changes=[]
 for item in auth['fins']:
  ob=bpy.data.objects[item['name']];m=ob.data;m.calc_loop_triangles();v=np.array([p.co[:]for p in m.vertices]);oldUV=np.array([l.uv[:]for l in m.uv_layers.active.data]);layer=np.array([a.value for a in m.attributes['source_layer_sign'].data]);roots=set(item['root_ids']);caps=[list(t.vertices)for t in m.loop_triangles if all(i in roots for i in t.vertices)];assert caps,(ob.name,'No complete finite basal cap');root=BVHTree.FromPolygons([Vector(p)for p in v],caps,all_triangles=True);span=max(root.find_nearest(Vector(p))[3]for p in v);collar=min(.018*L,.22*span);paired=item['paired'];tail=ob.name=='Caudal';ventral=ob.name=='Anal';S.tail_xmin=float(v[:,0].min());S.tail_dx=float(np.ptp(v[:,0]));root_x=float(np.mean(v[list(roots),0]));sign=1.
  if paired:
   positive=[p.normal.z for p in m.polygons if np.mean(layer[list(p.vertices)])>.9 and not all(i in roots for i in p.vertices)];sign=1. if np.mean(positive)>0 else-1.
  cap_z=v[list(roots),2];cap_mid=float((cap_z.min()+cap_z.max())/2);cap_h=float(np.ptp(cap_z)/2);cap_w=float(abs(v[list(roots),1]).max())
  if tail:collar=L*.045
  native_image=next(n.image for n in m.materials[0].node_tree.nodes if n.type=='TEX_IMAGE');nw,nh=native_image.size;native_pixels=np.array(native_image.pixels[:],dtype=np.float32).reshape(nh,nw,4);maskxy=np.array([[m.attributes['source_mask_x_px'].data[i].value,m.attributes['source_mask_y_px'].data[i].value]for i in range(len(v))])
  def native(xy):return native_pixels[min(nh-1,max(0,nh-1-int(round(xy[1])))),min(nw-1,max(0,int(round(xy[0])))),:3].copy()
  ns=[];ds=[]
  for tri in m.loop_triangles:
   if tri.material_index!=0:continue
   ids=list(tri.vertices);p=v[ids].mean(0);dist=root.find_nearest(Vector(p))[3]
   if dist<span*.25:continue
   if paired and np.mean(layer[ids])*sign<.5:continue
   ns.append(native(maskxy[ids].mean(0)));ds.append(S.pigment(p,.5,ventral,tail,root_x))
  assert ns,(ob.name,'No free pigment domain');tint=np.clip(np.median(ds,axis=0)/np.maximum(np.median(ns,axis=0),.01),.60,1.50)
  def field(p,lay,xy):
   foot,_,_,dist=root.find_nearest(Vector(p));s=min(1.,dist/max(span,1e-8));q=.18+.70*s
   pigment=np.clip(native(xy)*tint,0,1)
   if paired:
    up=np.clip((lay*sign+1)/2,0,1)
    if up>.999:color=pigment
    elif up<.001:color=S.pigment(p,q,True)
    else:color=pigment*up+S.pigment(p,q,True)*(1-up)
    if great and ob.name.startswith('Pectoral')and up<.999:
     tip=.12*smooth((s-.86)/.14)*(1-up);color=color*(1-tip)+S.pigment(p,q)*tip
   else:color=pigment
   gain=smooth(dist/max(collar,1e-8))
   if gain<1 and(not paired or lay*sign>.5):
    root_color=S.tail_surface(p,root_x,cap_mid,cap_w,cap_h)if tail and dist>L*1e-6 else S.query(tuple(foot),outer=tail)
    color=root_color*(1-gain)+color*gain
   return color
  tris=list(m.loop_triangles);oldslots=list(m.materials);newUV=oldUV.copy();slot_reports=[]
  for slot,mat in enumerate(oldslots):
   old_materials.add(mat);ts=[t for t in tris if t.material_index==slot];assert ts
   image=next(n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE');ow,oh=image.size;loops=[li for t in ts for li in t.loops];q=oldUV[loops]*[ow,oh];lo=np.floor(q.min(0)).astype(int)-2;hi=np.ceil(q.max(0)).astype(int)+2;rawW,H=(hi-lo).tolist();copies=2 if not paired and slot==0 else 1;W=rawW*copies;assert 0<W<8192 and 0<H<4096,(ob.name,slot,W,H);deg=[]
   for t in ts:
    z=oldUV[list(t.loops)]*[ow,oh]-lo
    if abs(np.linalg.det(np.column_stack([z[1]-z[0],z[2]-z[0]])))<1e-6:deg.append(t)
   tile=24;columns=max(1,W//tile);extra=((len(deg)+columns-1)//columns)*tile;totalH=H+extra;pixels=np.empty((totalH,W,4),np.float32);pixels[:,:,:3]=S.query(tuple(np.mean(v[list(roots)],axis=0)));pixels[:,:,3]=1;owned=np.zeros((totalH,W),bool);dmap={t.index:i for i,t in enumerate(deg)}
   for t in ts:
    ids=list(t.vertices);lis=list(t.loops)
    if t.index in dmap:
     j=dmap[t.index];x=(j%columns)*tile;y=H+(j//columns)*tile;z=np.array([[x+1.,y+1.],[x+tile-2.,y+1.],[x+1.,y+tile-2.]])
    else:
     z=oldUV[lis]*[ow,oh]-lo
     if copies==2 and t.normal.y<0:z[:,0]+=rawW
    newUV[lis]=z/[W,totalH];z=z-.5;A=np.column_stack([z[1]-z[0],z[2]-z[0]]);assert abs(np.linalg.det(A))>1e-7
    a=np.maximum(np.floor(z.min(0)-1).astype(int),0);b=np.minimum(np.ceil(z.max(0)+1).astype(int),[W-1,totalH-1]);xx,yy=np.meshgrid(np.arange(a[0],b[0]+1),np.arange(a[1],b[1]+1));points=np.c_[xx.ravel(),yy.ravel()];bc=(points-z[0])@np.linalg.inv(A).T;beta=np.c_[1-bc.sum(1),bc];distance=np.full(len(points),1e9)
    for p0,p1 in zip(z,np.roll(z,-1,axis=0)):
     e=p1-p0;u=np.clip(((points-p0)*e).sum(1)/max(float(e@e),1e-20),0,1);distance=np.minimum(distance,np.linalg.norm(points-(p0+u[:,None]*e),axis=1))
    take=(beta.min(1)>=-1e-7)|(distance<=.8);points=points[take];beta=np.maximum(beta[take],0);beta/=beta.sum(1)[:,None];world=beta@v[ids];ls=beta@layer[ids];sxy=beta@maskxy[ids]
    for p,point,lay,xy in zip(points,world,ls,sxy):pixels[p[1],p[0],:3]=field(point,float(lay),xy)
    owned[points[:,1],points[:,0]]=True
   assert owned.sum()>10;im=bpy.data.images.new(f'{base.name} {ob.name} body-connected slot{slot}',width=W,height=totalH,alpha=True);im.colorspace_settings.name=image.colorspace_settings.name;im.pixels.foreach_set(pixels.ravel());im.update();im.pack();new=mat.copy();new.name=f'Body-connected {ob.name} {slot}';tex=next(n for n in new.node_tree.nodes if n.type=='TEX_IMAGE');tex.image=im;tex.interpolation='Closest';tex.extension='EXTEND';m.materials[slot]=new;slot_reports.append(dict(slot=slot,image=im.name,size=[W,totalH],owned_pixels=int(owned.sum()),dedicated_degenerate_root_UV_triangles=len(deg),source_chart_name=image.name,source_native_pixels_preserved=False,separate_median_side_UV=copies==2))
  for i,u in enumerate(newUV):m.uv_layers.active.data[i].uv=u
  m.update()
  if tail:
   original=np.array([n.vector[:]for n in m.corner_normals]);target=original.copy();changed=[]
   for p in m.polygons:
    if all(i in roots for i in p.vertices):continue
    for li in p.loop_indices:
     i=m.loops[li].vertex_index;foot,_,_,dist=root.find_nearest(Vector(v[i]));gain=1-smooth(dist/(L*.015))
     if gain<=0:continue
     _,n=S.query(tuple(foot),True,True)if dist<L*1e-6 else S.tail_surface(v[i],root_x,cap_mid,cap_w,cap_h,True);nn=original[li]*(1-gain)+n*gain;nn/=max(np.linalg.norm(nn),1e-20)
     if np.dot(nn,p.normal)<.015:nn=nn+np.array(p.normal)*(.015-np.dot(nn,p.normal));nn/=np.linalg.norm(nn)
     target[li]=nn;changed.append(li)
   m.normals_split_custom_set(target.tolist());normal_changes.append(dict(mesh=ob.name,loops=sorted(set(changed)),maximum_bridge_distance_m=L*.015,visible_outer_body_only=True,body_normals_unchanged=True,cap_normals_unchanged=True))
  records.append(dict(name=ob.name,paired=paired,actual_upper_layer_sign=sign if paired else None,root_collar_m=collar,span_m=span,source='Original fin painted grain retained with explicit RGB tint. Paired underside instead uses actual same-body two-dimensional ventral pigment, excluding contaminated old lower chart. Root collar uses actual visible finite body colors; tail excludes internal body end-cap.',native_to_body_RGB_tint=tint.tolist(),lower_rule='Own ventral body field'if paired else'Own belly palette calibrated native fin grain'if ventral else None,great_pectoral_apex='Only slight12% dorsal-palette admixture at last14%span on underside'if great and ob.name.startswith('Pectoral')else None,slots=slot_reports));print('FIN_COLOR',base.name,ob.name,flush=True)
 assert frozen=={o.name:fingerprint(o)for o in bpy.context.scene.objects if o.type=='MESH'}and actions==rig_action_snapshot();assert np.array_equal(bodyUV,np.array([l.uv[:]for l in body.data.uv_layers.active.data]));assert np.array_equal(bodyPixels,np.array(S.image.pixels[:],dtype=np.float32).reshape(S.H,S.W,4))
 for mat in old_materials:
  if mat.users==0:bpy.data.materials.remove(mat)
 for im in list(bpy.data.images):
  if im.users==0:bpy.data.images.remove(im)
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
 for ob in bpy.context.scene.objects:
  if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
 bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
 for name in ['fin-authoring.json','body-color-mask.npz']:shutil.copyfile(src/name,out/name)
 report=dict(ok=True,kind='body_connected_fin_countershading_and_tail_bridge',baseline_sha256=sha(src/'fish.glb'),model_sha256=sha(out/'fish.glb'),source_geometry_weights_topology_rig_actions_exact=True,body_UV_and_body_eye_pixels_untouched=True,fin_UV_materials_albedo_changed=True,tail_free_skin_shading_normals_changed=normal_changes,fin_position_changed=False,paired_upper_root_uses_actual_relocated_blue_body=True,records=records,reference='fin-color-r28-evidence/research.json: NOAA643/Museum for part/color correspondence, not measured RGB or fin position. Current own body atlas provides actual pixels.',scope='Body albedo unchanged; actual finite basal body colors blended through each fin collar. Upper/lower assigned by source layer plus actual rest normal. All whole roots retained. No geometry, thickness or motion adjustment; fresh current pose/GPU/visual gates pending.',formal_acceptance=False,visual_review='pending')
 (out/'fin-color-authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print('BODY_FIN_COLOR_CANDIDATE',base.name,flush=True)
if __name__=='__main__':main()
