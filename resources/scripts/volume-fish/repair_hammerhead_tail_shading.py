"""Join outer caudal shading across separately closed shells, excluding caps.

No topology, position, weights, UV, pigment, rig or action edits. Only the
finite visible outer collar receives angle-weighted normals from BOTH shells.
Internal cap loops retain their own normals and never contribute to the skin.
"""
import bpy, sys, json, hashlib, shutil, math
from pathlib import Path
import numpy as np

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def unit(v): return v / max(float(np.linalg.norm(v)), 1e-20)
def smooth(t):
    t=float(np.clip(t,0,1)); return t*t*t*(10+t*(-15+6*t))
def snapshot(o):
    m=o.data
    return repr(([(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in m.vertices],
                 [tuple(p.vertices)for p in m.polygons], [tuple(l.uv)for l in m.uv_layers.active.data]))

def main():
    src,out=map(Path,sys.argv[sys.argv.index('--')+1:]);assert not out.exists()
    bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'))
    objects=[bpy.data.objects[n]for n in ['Reference_head_body','Caudal']]
    frozen={o.name:snapshot(o)for o in bpy.context.scene.objects if o.type=='MESH'}
    rear=min(v.co.x for v in objects[0].data.vertices)
    L=4. if src.parent.name=='great' else 3.
    # Angle weighting is independent of triangle size and internal cap density.
    combined={}; data=[]; eps=L*1e-7
    def key(p): return tuple(np.round(p/eps).astype(int))
    for ob in objects:
        m=ob.data;m.calc_loop_triangles();v=np.array([p.co[:]for p in m.vertices])
        old=np.array([n.vector[:]for n in m.corner_normals]);caps=set();acc={}
        for p in m.polygons:
            ids=list(p.vertices);points=v[ids]
            if np.max(abs(points[:,0]-rear))<eps: caps.add(p.index);continue
            for j,i in enumerate(ids):
                a=unit(points[j-1]-points[j]);b=unit(points[(j+1)%len(ids)]-points[j])
                angle=math.acos(float(np.clip(a@b,-1,1)));k=key(v[i])
                combined[k]=combined.get(k,np.zeros(3))+np.array(p.normal)*angle
                acc[k]=acc.get(k,np.zeros(3))+np.array(p.normal)*angle
        data.append((ob,v,old,caps,acc))
    records=[]
    for ob,v,old,caps,acc in data:
        m=ob.data;target=old.copy();edited=[]
        for p in m.polygons:
            if p.index in caps:continue
            for li in p.loop_indices:
                i=m.loops[li].vertex_index;d=abs(v[i,0]-rear)
                extent=L*(.045 if ob==objects[0] else .075)
                if d>=extent:continue
                n=unit(combined[key(v[i])]);w=1-smooth(d/extent)
                target[li]=unit(n*w+old[li]*(1-w));edited.append(li)
            if any(li in edited for li in p.loop_indices):p.use_smooth=True
        m.normals_split_custom_set(target.tolist());m.update()
        records.append(dict(mesh=ob.name,changed_loops=len(set(edited)),excluded_cap_faces=len(caps),maximum_angle_deg=float(np.rad2deg(np.arccos(np.clip((old*target).sum(1),-1,1))).max())))
    assert frozen=={o.name:snapshot(o)for o in bpy.context.scene.objects if o.type=='MESH'}
    out.mkdir(parents=True);bpy.context.preferences.filepaths.save_version=0
    bpy.ops.object.select_all(action='DESELECT')
    for ob in bpy.context.scene.objects:
        if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'))
    bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
    for name in ['fin-authoring.json','body-color-mask.npz']:shutil.copyfile(src/name,out/name)
    (out/'tail-shading.validation.json').write_text(json.dumps(dict(ok=True,baseline_sha256=sha(src/'fish.glb'),model_sha256=sha(out/'fish.glb'),geometry_uv_weights_unchanged=True,records=records,visual_review='pending',formal_acceptance=False),indent=2)+'\n')
if __name__=='__main__':main()
