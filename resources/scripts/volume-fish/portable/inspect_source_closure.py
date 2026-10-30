"""Read-only Blender closure witness; record failed edges in source coordinates."""
import bpy,bmesh,json,sys
from pathlib import Path

args=sys.argv[sys.argv.index('--')+1:]
source,output=map(Path,args)
assert source.is_file() and not output.exists()
bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
meshes={}
for obj in bpy.data.objects:
    if obj.type!='MESH':continue
    bm=bmesh.new();bm.from_mesh(obj.data);bm.edges.ensure_lookup_table()
    bad=[e for e in bm.edges if not e.is_manifold]
    meshes[obj.name]={'vertices':len(bm.verts),'faces':len(bm.faces),'nonmanifold_edges':len(bad),
        'witnesses':[{'edge':e.index,'linked_faces':len(e.link_faces),'length':e.calc_length(),
          'source_u':[v.co.x+.5 for v in e.verts],
          'coordinates':[list(v.co)for v in e.verts]}for e in bad]}
    bm.free()
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps({'ok':all(not m['nonmanifold_edges']for m in meshes.values()),'source':str(source.resolve()),'meshes':meshes},indent=2)+'\n',encoding='utf8')
print(json.dumps({name:{'nonmanifold_edges':m['nonmanifold_edges'],'witnesses':m['witnesses'][:4]}for name,m in meshes.items()}))
