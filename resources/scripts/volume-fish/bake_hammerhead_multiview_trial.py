"""Own-white-model multi-view paint trial, following whale shark R8 workflow.

Orthographic camera contract comes from capture_hammerhead_trial.gd. The four
generated quadrants are color donors, never geometric inputs. Body side uses
the fins-hidden panel. Paired surfaces use their top/bottom view. Native head,
mouth and eye pigment are protected. Independent closed shells use culling.
"""
import bpy,sys,json,hashlib,shutil
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)
def mesh_signature(o):
    m=o.data
    return repr(([(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in m.vertices],
                 [tuple(p.vertices)for p in m.polygons]))

def main():
    base,out=map(lambda p:Path(p).resolve(),sys.argv[sys.argv.index('--')+1:]);src=base/'tail-r41'
    assert not out.exists();out.mkdir()
    bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'))
    frozen={o.name:mesh_signature(o)for o in bpy.context.scene.objects if o.type=='MESH'}
    plan=json.loads((src/'review.plan.json').read_text());width=plan['whole_camera_size'];height=width*620/900
    cx,cz,ny=plan['whole_focus'];cy=-ny
    L=4. if base.name=='great'else 3.
    im=bpy.data.images.load(str(base/'paint-r41/generated.png'),check_existing=False)
    W,H=im.size;pixels=np.array(im.pixels[:],dtype=np.float32).reshape(H,W,4)[::-1,:,:3]
    # All sampling is at the generated resolution. Silhouette padding is only
    # a local boundary guard, never a narrow stripe stretched over a body.
    panels=[]
    for q in range(4):
        x0=round((q%2)*W/2);x1=round((q%2+1)*W/2);y0=round((q//2)*H/2);y1=round((q//2+1)*H/2)
        panel=pixels[y0:y1,x0:x1].copy();mask=panel.max(2)>.26
        # Find nearest valid same-column skin; allowed only for edge rounding.
        lo=np.full(panel.shape[1],-1,int);hi=lo.copy()
        for x in range(panel.shape[1]):
            ys=np.where(mask[:,x])[0]
            if len(ys):lo[x]=ys.min();hi[x]=ys.max()
        panels.append((panel,mask,lo,hi))
    fallback_counts=[0]*4;sample_counts=[0]*4
    def sample(q,p):
        panel,mask,lo,hi=panels[q];ph,pw=mask.shape
        x=(p[:,0]-cx)/width+.5
        if q==2:x=1-x
        z=p[:,2]-cz if q in [0,3]else p[:,1]-cy
        y=.5-z/height
        xx=np.clip((x*pw).astype(int),0,pw-1);yy=np.clip((y*ph).astype(int),0,ph-1)
        validxs=np.where(lo>=0)[0]
        # Maximum source silhouette displacement remains recorded, not hidden.
        missing=lo[xx]<0
        if missing.any():xx[missing]=validxs[np.abs(validxs[:,None]-xx[missing]).argmin(0)]
        invalid=~mask[yy,xx];fallback_counts[q]+=int(invalid.sum());sample_counts[q]+=len(p)
        for i in np.where(invalid)[0]:
            ys=np.where(mask[:,xx[i]])[0];yy[i]=ys[np.abs(ys-yy[i]).argmin()]
        return panel[yy,xx]
    body=bpy.data.objects['Reference_head_body'];headmax=max(v.co.x for v in body.data.vertices);rear=min(v.co.x for v in body.data.vertices)
    reports=[]
    for ob in list(bpy.context.scene.objects):
        if ob.type!='MESH' or ob.name.startswith('Eye'):continue
        m=ob.data;m.calc_loop_triangles();v=np.array([p.co[:]for p in m.vertices])
        normals=np.array([n.vector[:]for n in m.corner_normals]);old_uv=np.array([l.uv[:]for l in m.uv_layers.active.data])
        old_images={}
        for i,mat in enumerate(m.materials):
            imgs=[n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE']
            if imgs:
                img=imgs[0];iw,ih=img.size;old_images[i]=np.array(img.pixels[:],np.float32).reshape(ih,iw,4)
        bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.012,area_weight=.5)
        bpy.ops.object.mode_set(mode='OBJECT');m.calc_loop_triangles()
        new_uv=np.array([l.uv[:]for l in m.uv_layers.active.data]);N=2048 if ob==body else 1024 if ob.name=='Caudal'else 512
        atlas=np.empty((N,N,4),np.float32);atlas[:]=(.25,.30,.32,1);owned=np.zeros((N,N),bool)
        count=0
        for tri in m.loop_triangles:
            if tri.material_index not in old_images:continue
            ids=list(tri.vertices);lis=list(tri.loops);z=new_uv[lis]*N-.5
            A=np.column_stack((z[1]-z[0],z[2]-z[0]));det=np.linalg.det(A)
            if abs(det)<1e-9:continue
            a=np.maximum(np.floor(z.min(0)-2).astype(int),0);b=np.minimum(np.ceil(z.max(0)+2).astype(int),N-1)
            xx,yy=np.meshgrid(np.arange(a[0],b[0]+1),np.arange(a[1],b[1]+1));pts=np.c_[xx.ravel(),yy.ravel()]
            ab=(pts-z[0])@np.linalg.inv(A).T;beta=np.c_[1-ab.sum(1),ab]
            dist=np.full(len(pts),1e9)
            for p0,p1 in zip(z,np.roll(z,-1,axis=0)):
                e=p1-p0;t=np.clip(((pts-p0)*e).sum(1)/max(e@e,1e-20),0,1);dist=np.minimum(dist,np.linalg.norm(pts-(p0+t[:,None]*e),axis=1))
            take=(beta.min(1)>=0)|(dist<=1.5);pts=pts[take];beta=np.maximum(beta[take],0);beta/=beta.sum(1)[:,None]
            p=beta@v[ids];n=beta@normals[lis];n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-20)
            if ob.name.startswith(('Pectoral','Pelvic')):
                # Physical source layer identity is stable at the rounded rim.
                layer=np.array([m.attributes['source_layer_sign'].data[i].value for i in ids])
                lay=beta@layer;positive=[face.normal.z for face in m.polygons if np.mean([m.attributes['source_layer_sign'].data[i].value for i in face.vertices])>.9]
                sign=1 if np.mean(positive)>0 else -1
                up=smooth((lay*sign+1)/2)[:,None];color=sample(1,p)*up+sample(2,p)*(1-up)
            else:
                side=sample(3 if ob==body else 0,p)
                if ob==body:
                    # The visible peduncle is unobscured in the complete side
                    # plate. Use the SAME two-dimensional paint on BOTH sides
                    # of the caudal joint; blend to fins-hidden torso upstream.
                    donor=smooth((p[:,0]-rear-L*.05)/(L*.05))[:,None]
                    side=side*donor+sample(0,p)*(1-donor)
                # Only body turns from side into roof/belly. Median fins are
                # correctly represented by the side view, not a tiny top edge.
                if ob==body or ob.name=='Caudal':
                    top=smooth((n[:,2]-.35)/.50);bottom=smooth((-n[:,2]-.35)/.50)
                    if ob.name=='Caudal':
                        joint=1-smooth((rear-p[:,0])/(L*.035));top*=joint;bottom*=joint
                    color=side*(1-top-bottom)[:,None]+sample(1,p)*top[:,None]+sample(2,p)*bottom[:,None]
                else:color=side
            if ob==body:
                # Native anterior region includes complete mouth/gills and all
                # original face pixels. Generator eyes are never used there.
                keep=smooth((p[:,0]-(headmax-L*.30))/(L*.055))
                original=old_images[tri.material_index];ih,iw=original.shape[:2];uv=beta@old_uv[lis]
                ox=np.clip((uv[:,0]*iw).astype(int),0,iw-1);oy=np.clip((uv[:,1]*ih).astype(int),0,ih-1)
                color=color*(1-keep[:,None])+original[oy,ox,:3]*keep[:,None]
            atlas[pts[:,1],pts[:,0],:3]=color;owned[pts[:,1],pts[:,0]]=True;count+=len(pts)
        image=bpy.data.images.new(f'{base.name} {ob.name} multiview paint',width=N,height=N,alpha=True)
        image.pixels.foreach_set(atlas.ravel());image.update();image.pack()
        for i,mat in enumerate(list(m.materials)):
            new=mat.copy();new.name=f'Multiview {ob.name} {i}';new.use_backface_culling=True
            for node in new.node_tree.nodes:
                if node.type=='TEX_IMAGE':node.image=image;node.interpolation='Closest';node.extension='EXTEND'
                if node.type=='BSDF_PRINCIPLED':node.inputs['Roughness'].default_value=.85;node.inputs['Specular IOR Level'].default_value=.15
            m.materials[i]=new
        m.normals_split_custom_set(normals.tolist());m.update()
        reports.append(dict(mesh=ob.name,atlas_size=N,covered_pixels=int(owned.sum()),triangles=len(m.loop_triangles)))
    assert frozen=={o.name:mesh_signature(o)for o in bpy.context.scene.objects if o.type=='MESH'}
    bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
    for ob in bpy.context.scene.objects:
        if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
    bpy.context.view_layer.objects.active=body
    # Remove disconnected old material/image data only, not source assets.
    for mat in list(bpy.data.materials):
        if mat.users==0:bpy.data.materials.remove(mat)
    for image in list(bpy.data.images):
        if image.users==0:bpy.data.images.remove(image)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'))
    bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
    for name in ['fin-authoring.json','body-color-mask.npz']:shutil.copyfile(src/name,out/name)
    report=dict(ok=True,kind='own_white_model_multiview_color_trial',source_sha256=sha(src/'fish.glb'),generated_sha256=sha(base/'paint-r41/generated.png'),model_sha256=sha(out/'fish.glb'),geometry_topology_weights_exact=True,head_mouth_native_protection_x=[headmax-L*.30,headmax-L*.245],eye_objects_untouched=True,records=reports,source_sample_counts=sample_counts,source_boundary_fallback_counts=fallback_counts,formal_acceptance=False,visual_review='pending')
    (out/'multiview.validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
if __name__=='__main__':main()
