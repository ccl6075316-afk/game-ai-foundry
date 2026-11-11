from pathlib import Path
import sys,json,bpy
W=Path(__file__).resolve().parents[1];sys.path.insert(0,str(W))
from author_export import snapshot,export,sha,SOURCE_IMAGE_BY_INDEX
source,out,bake=map(Path,sys.argv[-3:]);out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source));before=snapshot();proof=json.loads((bake/'bake.validation.json').read_text())
for idx,row in proof['images'].items():
 name='Complete anterior mouth color chart.001' if idx=='2' else 'R5 finite oral cavity donor'
 old=bpy.data.images[name];path=Path(row['path']);assert sha(path)==row['sha256'];new=bpy.data.images.load(str(path),check_existing=False);new.colorspace_settings.name=old.colorspace_settings.name;new.alpha_mode=old.alpha_mode;new.pack()
 for m in bpy.data.materials:
  if m.node_tree:
   for n in m.node_tree.nodes:
    if n.type=='TEX_IMAGE' and n.image==old:n.image=new
 old.name=name+' old diagnostic';new.name=name
 if not old.users:bpy.data.images.remove(old)
assert snapshot()==before
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));r=export(out/'author-fish.glb');r.update(source_sha256=sha(out/'fish.blend'),input_source_sha256=sha(source),actual_bake_report_sha256=sha(bake/'bake.validation.json'),geometry_normal_uv_skin_rig_preserved_from_local_volume=True);(out/'source-authoring.validation.json').write_text(json.dumps(r,indent=2)+'\n')
