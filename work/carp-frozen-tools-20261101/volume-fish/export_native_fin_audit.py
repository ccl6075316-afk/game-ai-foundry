"""Blender: freeze actual native fin images before independent boundary review."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--blend',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));rows=[]
for ob in bpy.data.objects:
 if ob.type!='MESH' or ob.name=='Closed_body':continue
 name=ob.name.removesuffix('_mesh').removesuffix('_left').removesuffix('_right')
 if any(r['fin']==name for r in rows):continue
 images=[n.image for m in ob.data.materials if m and m.use_nodes for n in m.node_tree.nodes if n.type=='TEX_IMAGE'and n.image];assert len(images)==1,(ob.name,len(images));image=images[0];path=out/(name+'-current-cutout.png');image.filepath_raw=str(path);image.file_format='PNG';image.save()
 rows.append({'fin':name,'object':ob.name,'image':str(path),'sha256':sha(path),'size':list(image.size),'triangles':sum(len(f.vertices)-2 for f in ob.data.polygons)})
report={'ok':True,'kind':'actual_native_fin_material_audit','blend':str(a.blend.resolve()),'blend_sha256':sha(a.blend),'fins':rows,'scope':'Actual original source RGB/alpha; not independently approved segmentation. No painting, resampling or acceptance.'};(out/'validation.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps({'ok':True,'fins':len(rows)}))
