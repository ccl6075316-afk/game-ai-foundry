"""Blender: freeze complete native cage basal selections for isolated A/B GLBs."""
import bpy,json,hashlib
from pathlib import Path
repo=Path(__file__).resolve().parents[3]
out=repo/'projects/fishing-2d/experiments/nile-dorsal-route-trial/round4-ab-textured'
roots=json.loads((out/'B-artifacts/fin-roots.json').read_text(encoding='utf8'))
items=[];reference={}
for route in ['B','A']:
    directory=out/(route+'-artifacts');bpy.ops.wm.open_mainfile(filepath=str(directory/'fish.blend'))
    fins={}
    for name,selection in roots.items():
        ob=bpy.data.objects[name];mesh=ob.data;n=len(mesh.vertices)//2
        # Compare all front/back source UVs before transferring the source-band IDs.
        source_uv={}
        for face in mesh.polygons:
            indices=list(face.vertices)
            if all(i<n for i in indices) or all(i>=n for i in indices):
                for li in face.loop_indices:source_uv[mesh.loops[li].vertex_index]=tuple(round(v,6) for v in mesh.uv_layers.active.data[li].uv)
        if route=='B':reference[name]=source_uv
        else:assert source_uv==reference[name],name+' cage source UV mapping differs'
        points=[]
        for index in selection['ids']:
            v=ob.matrix_world@mesh.vertices[index].co
            points.append([v.x,v.z,-v.y])
        fins[name]={'rest_points_gltf':points,'source_baseline':selection['source_baseline'],'source_size':selection['source_size'],'selection_method':'All cage vertices within four source pixels of complete anatomical baseline; both solid skins; all connected root-edge interiors sampled by exporter.'}
    model=directory/'fish.glb';items.append({'species':'nile_tilapia','route':route,'model':str(model.resolve()),'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),'body':'Closed_body_B' if route=='B' else 'Closed_body','length_native':1/.402819722890854*.4,'fins':fins})
    (directory/'fin-gate.plan.json').write_text(json.dumps({'items':[items[-1]]},indent=2),encoding='utf8')
print(json.dumps({'ok':True,'routes':[i['route'] for i in items],'fins':{name:len(row['rest_points_gltf']) for name,row in items[0]['fins'].items()}}))
