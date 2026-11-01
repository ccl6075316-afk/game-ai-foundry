"""Read a body from an editable source into an exact material/UV transfer receipt."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
p=argparse.ArgumentParser();p.add_argument('--blend',type=Path,required=True);p.add_argument('--body',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);ROOT=Path(__file__).resolve().parents[3];out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();out.mkdir(parents=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));ob=bpy.data.objects[a.body];materials=[];used=sorted({f.material_index for f in ob.data.polygons});remap={old:new for new,old in enumerate(used)}
for i in used:
 m=ob.data.materials[i]
 bsdf=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');node=bsdf.inputs['Base Color'].links[0].from_node;assert node.type=='TEX_IMAGE';image=node.image;raw=bytes(image.packed_file.data);assert raw.startswith(b'\x89PNG');dest=out/f'material-{i}.png';dest.write_bytes(raw);materials.append({'name':m.name,'image':str(dest),'sha256':sha(dest),'size':list(image.size)})
data={'ok':True,'kind':'exact_body_material_UV_receipt','blend':str(a.blend.resolve()),'blend_sha256':sha(a.blend),'body':a.body,'positions':[list(v.co)for v in ob.data.vertices],'faces':[list(f.vertices)for f in ob.data.polygons],'material_indices':[remap[f.material_index]for f in ob.data.polygons],'uv':[list(u.uv)for u in ob.data.uv_layers.active.data],'materials':materials};(out/'body-materials.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'materials':len(materials),'faces':len(data['faces'])}))
