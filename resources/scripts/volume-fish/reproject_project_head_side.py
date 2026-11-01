"""Register a project head's vertical sections to its own original side bounds.

XY/top outline and the complete oral cut remain; the map is a positive affine
vertical transform at each X. Every static eye support is refreshed separately.
"""
import bpy,json,sys,hashlib
from pathlib import Path
import numpy as np
args=sys.argv[sys.argv.index('--')+1:];cp=Path(args[0]);out=Path(args[1]);assert not out.exists();out.mkdir();c=json.loads(cp.read_text());src=Path(c['baseline']);a=json.loads(Path(c['old_reference']).read_text());b=json.loads(Path(c['reference']).read_text());bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));records=[]
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    changed=0;maximum=0.
    for v in ob.data.vertices:
        t=(a['reference_body_axis_m']/2-v.co.x)/a['reference_body_axis_m'];oldtop=np.interp(t,[r['t']for r in a['body_stations']],[r['top_z_m']for r in a['body_stations']]);oldbottom=np.interp(t,[r['t']for r in a['body_stations']],[r['bottom_z_m']for r in a['body_stations']]);top=np.interp(t,[r['t']for r in b['body_stations']],[r['top_z_m']for r in b['body_stations']]);bottom=np.interp(t,[r['t']for r in b['body_stations']],[r['bottom_z_m']for r in b['body_stations']]);assert top>bottom and oldtop>oldbottom;z=bottom+(v.co.z-oldbottom)/(oldtop-oldbottom)*(top-bottom);delta=abs(z-v.co.z);maximum=max(maximum,delta)
        if delta>1e-8:changed+=1;v.co.z=z
    records.append(dict(mesh=ob.name,changed_vertices=changed,maximum_z_change_m=maximum))
    if changed:ob.data.update();ob.data.normals_split_custom_set([(0.,0.,0.)]*len(ob.data.loops))
bpy.ops.object.select_all(action='SELECT');bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());r=dict(ok=True,kind='own_side_head_vertical_registration',records=records,XY_topology_UV_weights_unchanged=True,reference_sha256=hashlib.sha256(Path(c['reference']).read_bytes()).hexdigest(),source_model_sha256=hashlib.sha256((src/'fish.glb').read_bytes()).hexdigest(),model_sha256=hashlib.sha256((out/'fish.glb').read_bytes()).hexdigest(),eyes='Existing lenses transformed consistently; reproject actual finite support before final export.',formal_acceptance=False);(out/'authoring.validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
