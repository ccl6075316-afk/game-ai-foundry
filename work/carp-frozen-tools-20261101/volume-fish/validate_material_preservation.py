"""Blender: prove a declared material edit preserved geometry/skin/fin UV/rig.

This does not approve color, anatomy, animation clearance or user appearance.
"""
import argparse,hashlib,json,sys
from array import array
from pathlib import Path
import bpy

def digest(value):return hashlib.sha256(repr(value).encode()).hexdigest()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def capture(path):
    bpy.ops.wm.open_mainfile(filepath=str(path.resolve()));meshes={};rigs={};images={}
    def material(mat):
        textures=[]
        if mat and mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type=='TEX_IMAGE'and node.image:
                    im=node.image
                    if im.name not in images:images[im.name]=hashlib.sha256(repr(list(im.size)).encode()+array('f',im.pixels[:]).tobytes()).hexdigest()
                    textures.append(images[im.name])
        return digest((mat.name if mat else None,textures))
    for ob in bpy.data.objects:
        if ob.type=='MESH':
            meshes[ob.name]={'geometry_weights':digest(([(tuple(v.co),[(ob.vertex_groups[g.group].name,g.weight)for g in v.groups])for v in ob.data.vertices],[tuple(f.vertices)for f in ob.data.polygons],list(ob.matrix_world))),'uv':digest([[tuple(x.uv)for x in l.data]for l in ob.data.uv_layers]),'materials':digest([material(m)for m in ob.data.materials])}
        elif ob.type=='ARMATURE':rigs[ob.name]=digest([(b.name,b.parent.name if b.parent else None,list(b.matrix_local))for b in ob.data.bones])
    return meshes,rigs

def run(a):
    assert not a.output.exists();before,br=capture(a.before);after,ar=capture(a.after)
    same_inventory=set(before)==set(after);geometry=same_inventory and all(before[n]['geometry_weights']==after[n]['geometry_weights']for n in before)
    fins=[n for n in before if n!=a.body];assert a.body in before and fins
    fin_uv=same_inventory and all(before[n]['uv']==after[n]['uv']for n in fins)
    fin_materials=same_inventory and all(before[n]['materials']==after[n]['materials']for n in fins)
    report={'ok':same_inventory and geometry and fin_uv and fin_materials and br==ar,'kind':'actual_material_only_preservation','before':{'path':str(a.before.resolve()),'sha256':sha(a.before)},'after':{'path':str(a.after.resolve()),'sha256':sha(a.after)},'same_mesh_inventory':same_inventory,'geometry_weights_transforms_equal':geometry,'all_fin_uv_equal':fin_uv,'all_fin_material_images_equal':fin_materials,'rest_rig_equal':br==ar,'body':a.body,'fins':fins,'before_meshes':before,'after_meshes':after,'scope':'Actual editable-source preservation only. Body UV/material may differ. Does not replace current cold export, body opacity, complete fin/action or actual image review.'}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':report['ok'],'meshes':len(before),'geometry_weights_and_fin_uv_materials_preserved':geometry and fin_uv and fin_materials}));return 0 if report['ok']else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['before','after','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--body',required=True);args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);raise SystemExit(run(args))
