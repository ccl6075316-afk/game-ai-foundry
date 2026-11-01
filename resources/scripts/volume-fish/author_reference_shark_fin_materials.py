"""Bind native per-fin charts on immutable reference-coordinate attributes."""
import bpy,json,sys,hashlib
from pathlib import Path
import numpy as np

args=sys.argv[sys.argv.index('--')+1:];src=Path(args[0]).resolve();charts=Path(args[1]).resolve();out=Path(args[2]).resolve();assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir();r=json.loads((charts/'validation.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();auth=json.loads((src/'fin-authoring.json').read_text());proof=[]
def fingerprint(ob):
    me=ob.data;return hashlib.sha256(repr(([(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in me.vertices],[tuple(f.vertices)for f in me.polygons])).encode()).hexdigest()
before={o.name:fingerprint(o)for o in bpy.context.scene.objects if o.type=='MESH'}
for row in auth['fins']:
    ob=bpy.data.objects[row['name']];me=ob.data;name=row['name'].removesuffix('_left').removesuffix('_right');records=[x for x in r['records']if x['name']==name];slots={};materials=[]
    for item in records:
        assert sha(item['path'])==item['sha256'];im=bpy.data.images.load(item['path'],check_existing=False);im.pack();m=bpy.data.materials.new('Own native '+name+' '+item['role']);m.use_nodes=True;m.use_backface_culling=True;bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Roughness'].default_value=1;bs.inputs['Specular IOR Level'].default_value=0;t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=im;t.interpolation='Closest';t.extension='EXTEND';m.node_tree.links.new(t.outputs['Color'],bs.inputs['Base Color']);slots[item['role']]=len(materials);materials.append(m)
    edge=next(item for item in r['sealed_edges']if item['name']==name);assert sha(edge['path'])==edge['sha256'];im=bpy.data.images.load(edge['path'],check_existing=False);im.pack();em=materials[0].copy();em.name='Derived continuous thickness skin '+name;tex=next(n for n in em.node_tree.nodes if n.type=='TEX_IMAGE');tex.image=im;tex.extension='REPEAT';edge_slot=len(materials);materials.append(em);edge_path=np.array(edge['reference_closed_contour_px']);edge_arc=np.array(edge['reference_arc_px']);edge_count=0
    def perimeter(q):
        aa=edge_path[:-1];delta=edge_path[1:]-aa;lens=(delta*delta).sum(1);t=np.clip(((q-aa)*delta).sum(1)/np.maximum(lens,1e-20),0,1);foot=aa+t[:,None]*delta;ids=np.argmin(((q-foot)**2).sum(1));return (edge_arc[ids]+t[ids]*(edge_arc[ids+1]-edge_arc[ids]))/edge_arc[-1]
    old=[f.material_index for f in me.polygons];me.materials.clear()
    for m in materials:me.materials.append(m)
    uv=me.uv_layers.active or me.uv_layers.new(name='ReferenceFinNativeUV');xs=me.attributes['source_mask_x_px'];ys=me.attributes['source_mask_y_px'];w,h=bpy.data.images.get(next(n.image.name for n in materials[0].node_tree.nodes if n.type=='TEX_IMAGE')).size
    for f,old_slot in zip(me.polygons,old):
        role='lower'if row['paired']and old_slot==1 else'upper'if row['paired']else'side';f.material_index=slots[role]
        q=np.array([[xs.data[i].value,ys.data[i].value]for i in f.vertices]);layer=np.array([me.attributes['source_layer_sign'].data[i].value for i in f.vertices]);area=abs(float(np.linalg.det(np.stack([q[1]-q[0],q[2]-q[0]]))))
        if area<.25 and layer.min()<-.5 and layer.max()>.5:
            phase=np.array([perimeter(p)for p in q]);phase[phase<.5]+=1 if phase.max()-phase.min()>.5 else 0;f.material_index=edge_slot;edge_count+=1
            for li,u,v in zip(f.loop_indices,phase,layer):uv.data[li].uv=(float(u),float((v+1)/2*.9375+.03125))
            continue
        for li in f.loop_indices:
            i=me.loops[li].vertex_index;uv.data[li].uv=((xs.data[i].value+.5)/w,1-(ys.data[i].value+.5)/h)
    proof.append(dict(name=row['name'],chart_roles=list(slots),native_source_sha256={x['role']:x['source_sha256']for x in records},actual_source_mask_coordinates=True,closed_surface_backface_culling=True,derived_seal_triangles=edge_count,seal_chart_sha256=edge['sha256']))
after={o.name:fingerprint(o)for o in bpy.context.scene.objects if o.type=='MESH'};assert before==after
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    if o.type in['MESH','ARMATURE']:o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());report=dict(ok=True,kind='own_native_reference_fin_uv_binding',model_sha256=sha(out/'fish.glb'),chart_receipt_sha256=sha(charts/'validation.json'),geometry_skin_weights_unchanged=True,records=proof,formal_acceptance=False,visual_review='pending');(out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(ok=True,actual_fins=len(proof))))
