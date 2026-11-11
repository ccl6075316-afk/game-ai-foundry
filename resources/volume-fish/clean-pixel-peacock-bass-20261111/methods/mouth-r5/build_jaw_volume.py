from pathlib import Path
import sys,json,math
import bpy,numpy as np
W=Path(__file__).resolve().parents[1];sys.path.insert(0,str(W))
from author_export import snapshot,export,sha,geometry_signature,normal_attribute_signature,EXACT_NORMAL_ATTRIBUTE,JOINT_ATTRIBUTES,WEIGHT_ATTRIBUTES
from sculpt_opening import to_gltf,to_blender,smooth

def field(p):
 x,y,z=p.T
 mid=np.interp(x,[.36,.40,.43,.447,.497],[-.08,-.071,-.057,-.055,-.04])
 near=1-smooth((np.abs(y-mid)-.012)/.026)
 rear=smooth((x-.369)/.079)*(1-smooth((x-.448)/.049))
 dx=-.021*near*rear;dy=-.0015*near*rear
 ridge=np.interp(x,[.36,.375,.405,.435,.46,.49],[-.080,-.081,-.067,-.047,-.037,-.031])
 bump=.0085*np.exp(-((y-ridge)/.015)**2)*smooth((x-.355)/.025)*(1-smooth((x-.485)/.012))
 dz=np.sign(z)*bump*smooth(np.abs(z)/.020)
 return p+np.c_[dx,dy,dz]

def main():
 source,out=map(Path,sys.argv[-2:]);out.mkdir(exist_ok=True)
 bpy.ops.wm.open_mainfile(filepath=str(source));before=snapshot();ob=bpy.data.objects['Closed_body'];old=ob.data
 verts0=to_gltf(np.array([v.co[:] for v in old.vertices]));verts=field(verts0);n0=np.array([d.vector[:] for d in old.attributes[EXACT_NORMAL_ATTRIBUTE].data]);uv0=np.array([d.uv[:] for d in old.uv_layers.active.data]);attrs={a:np.array([d.value for d in old.attributes[a].data]) for a in JOINT_ATTRIBUTES+WEIGHT_ATTRIBUTES}
 group_names=[g.name for g in ob.vertex_groups]
 vg=[[(g.group,g.weight) for g in v.groups] for v in old.vertices]
 changed=np.linalg.norm(verts-verts0,axis=1)>1e-12
 faces=[];mats=[];records=[];edge={};border_records={}
 for poly in old.polygons:
  ids=list(poly.vertices);loops=list(poly.loop_indices)
  if poly.material_index!=3:
   faces.append(ids);mats.append(poly.material_index);records.append(loops)
  else:
   for a,b,li in zip(ids,ids[1:]+ids[:1],loops):
    key=tuple(sorted((a,b)));edge.setdefault(key,[]).append((a,b));border_records[a]=li
 directed=[e[0] for e in edge.values() if len(e)==1];successor=dict(directed);start=directed[0][0];boundary=[start]
 while successor[boundary[-1]]!=start:boundary.append(successor[boundary[-1]])
 assert len(boundary)==77 and len(boundary)==len(directed)
 # A recessed inner ring lies behind the real anterior opening, while the
 # solid maxillary fold still covers the rear side; no external slit to eye.
 n=24;bp=verts[boundary];step=np.linalg.norm(np.roll(bp,-1,axis=0)-bp,axis=1);arc=np.r_[0,np.cumsum(step)];fractions=arc[:-1]/arc[-1];inner=[]
 center=np.array([.405,-.046,0.]);ring_uv=[]
 for j in range(n):
  t=j/n;i=min(len(boundary)-1,int(np.searchsorted(fractions,t,side='right')-1));u=(t-fractions[i])/(arc[i+1]/arc[-1]-fractions[i]);p=bp[i]*(1-u)+bp[(i+1)%len(bp)]*u
  p[0]=.407;p[1:]=center[1:]+.55*(p[1:]-center[1:]);inner.append(len(verts)+j);ring_uv.append(np.array([.5,.5])+np.array([math.cos(2*math.pi*t),math.sin(2*math.pi*t)])*.20)
  # retain a small inner opening cross-section, not a flat lip-spanning disk
  if j==0:newpoints=[]
  newpoints.append(p)
 cap=len(verts)+n;verts=np.vstack([verts,newpoints,[.392,-.046,0.]])
 # Merge the two ordered parameter loops without copying source triangulation.
 i=j=0
 while i<len(boundary) or j<n:
  ni=(fractions[i+1] if i+1<len(boundary) else 1.) if i<len(boundary) else float('inf');nj=(j+1)/n if j<n else float('inf')
  if ni<=nj:
   a=boundary[i%len(boundary)];b=boundary[(i+1)%len(boundary)];c=inner[j%n];i+=1
  else:
   a=boundary[i%len(boundary)];b=inner[(j+1)%n];c=inner[j%n];j+=1
  faces.append([a,b,c]);mats.append(3);records.append(None)
 for j in range(n):faces.append([inner[j],inner[(j+1)%n],cap]);mats.append(3);records.append(None)
 new=bpy.data.meshes.new('Integrated maxillary fold and recessed oral cavity R5');new.from_pydata(to_blender(verts).tolist(),[],faces);new.update()
 for m in old.materials:new.materials.append(m)
 for p,mi in zip(new.polygons,mats):p.material_index=mi;p.use_smooth=True
 new.uv_layers.new(name='UVMap')
 for a in JOINT_ATTRIBUTES+WEIGHT_ATTRIBUTES:new.attributes.new(name=a,type='FLOAT',domain='CORNER')
 new.attributes.new(name=EXACT_NORMAL_ATTRIBUTE,type='FLOAT_VECTOR',domain='CORNER')
 # Deformation gradient transports skin normals; inner-wall normals come from
 # the actual newly recessed surface, with hard distinction at the lip.
 eps=1e-5;basis=np.eye(3)*eps;normal_rows=[];oral_acc={}
 for face,mi in zip(faces,mats):
  if mi!=3:continue
  p=verts[face];nn=np.cross(p[1]-p[0],p[2]-p[0])
  for v in face:oral_acc[v]=oral_acc.get(v,np.zeros(3))+nn
 for poly,rec in zip(new.polygons,records):
  for k,li in enumerate(poly.loop_indices):
   vi=poly.vertices[k]
   if rec is not None:
    oi=rec[k];p=verts0[vi:vi+1];J=np.stack([(field(p+e)-field(p-e))[0]/(2*eps) for e in basis],axis=1);nn=np.linalg.solve(J.T,n0[oi]);uv=uv0[oi];vals={a:attrs[a][oi] for a in attrs}
   else:
    nn=oral_acc[vi];t=fractions[boundary.index(vi)] if vi in boundary else ((vi-len(verts0))/n if vi!=cap else 0)
    rad=.47 if vi in boundary else (.20 if vi!=cap else 0.);uv=np.array([.5,.5])+rad*np.array([math.cos(2*math.pi*t),math.sin(2*math.pi*t)])
    if vi<len(verts0):oi=border_records[vi];vals={a:attrs[a][oi] for a in attrs}
    else:vals={a:float(k==0) for k,a in enumerate(WEIGHT_ATTRIBUTES)}|{a:float(1 if k==0 else 0) for k,a in enumerate(JOINT_ATTRIBUTES)}
   nn/=max(np.linalg.norm(nn),1e-15);normal_rows.append(nn);new.uv_layers.active.data[li].uv=uv
   for a,val in vals.items():new.attributes[a].data[li].value=float(val)
   new.attributes[EXACT_NORMAL_ATTRIBUTE].data[li].vector=nn
 ob.data=new
 for name in group_names:
  if name not in ob.vertex_groups:ob.vertex_groups.new(name=name)
 for vi,groups in enumerate(vg):
  for gi,wt in groups:ob.vertex_groups[gi].add([vi],wt,'REPLACE')
 for vi in range(len(vg),len(verts)):ob.vertex_groups['body_00'].add([vi],1.,'REPLACE')
 new.normals_split_custom_set(to_blender(np.array(normal_rows)).tolist());new['foundry_normal_geometry_sha256']=geometry_signature(ob);new['foundry_exact_normal_sha256']=normal_attribute_signature(ob);new['foundry_normal_provenance_sha256']=sha(source)
 # Diagnostic source-colored oral chart, replaced by actual palette transport
 # before a textured final review. Exterior original atlas remains untouched.
 material=new.materials[3].copy();material.name='Recessed actual mouth cavity R5';new.materials[3]=material
 image=bpy.data.images.new('R5 finite oral cavity donor',width=64,height=64,alpha=True)
 colors=np.zeros((64,64,4),np.float32)
 yy,xx=np.mgrid[:64,:64];rr=np.clip(np.hypot(xx-31.5,yy-31.5)/45,0,1)
 colors[:,:,0]=.11+.15*rr;colors[:,:,1]=.055+.08*rr;colors[:,:,2]=.018+.025*rr;colors[:,:,3]=1
 image.pixels=colors.ravel();image.pack()
 for node in material.node_tree.nodes:
  if node.type=='TEX_IMAGE':node.image=image;node.interpolation='Closest';node.extension='EXTEND'
 new["foundry_normal_geometry_sha256"]=geometry_signature(ob)
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));r=export(out/'fish.glb');r.update(triangles=1842+50,source_vertices_changed=int(changed.sum()),inner_vertices=25,outer_boundary_vertices=77,source_sha256=sha(out/'fish.blend'),input_source_sha256=sha(source),status='local_gray_candidate_not_final_material')
 (out/'build.validation.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
