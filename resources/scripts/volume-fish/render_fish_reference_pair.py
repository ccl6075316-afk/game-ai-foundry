"""Read-only complete-fish orthographic pair diagnostic. Run in Blender background.

--pair JSON --output DIRECTORY [--native]
Required assets: path, sha256, canonical_from_source_axes, uniform_scale, pose.
Canonical +X=noseward,+Y=up,+Z=declared lateral. Source GLB axes are glTF
file-native, OBJ axes are literal v coordinates, blend axes are saved world axes.
No PCA, component selection, mesh welding, tail straightening or anisotropic fit.
OBJ obj_materials are exact group bindings; absent alpha requires explicit warning.
"""
import argparse, hashlib, json, math, struct, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector, Quaternion
ROOT=Path(__file__).resolve().parents[3]
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def jwrite(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def used_points(obj):
    ids=sorted({i for p in obj.data.polygons for i in p.vertices});assert ids;return [obj.data.vertices[i] for i in ids]
def bounds(v):return [v.min(axis=0).tolist(),v.max(axis=0).tolist()]
def axis_matrix(tokens):
    assert len(tokens)==3 and {x[-1] for x in tokens}=={'X','Y','Z'}
    m=np.zeros((3,3))
    for i,t in enumerate(tokens):
        assert t in ['+X','-X','+Y','-Y','+Z','-Z'];m[i,'XYZ'.index(t[1])]=1 if t[0]=='+' else -1
    return Matrix(m.tolist()).to_4x4()

def glb_static_bounds(path):
    b=path.read_bytes();n=struct.unpack_from('<I',b,12)[0];d=json.loads(b[20:20+n]);binary=b[28+n:]
    def trs(node):
        if 'matrix'in node:return Matrix(np.array(node['matrix']).reshape(4,4).T.tolist())
        q=node.get('rotation',[0,0,0,1]);return Matrix.Translation(node.get('translation',[0,0,0]))@Quaternion((q[3],q[0],q[1],q[2])).to_matrix().to_4x4()@Matrix.Diagonal((*node.get('scale',[1,1,1]),1))
    points=[];worlds=[]
    def visit(i,parent):
        node=d['nodes'][i];world=parent@trs(node)
        if 'mesh'in node:
            assert not any(node.get('weights',d['meshes'][node['mesh']].get('weights',[]))),'Nonzero default morph requires explicit importer audit'
            worlds.append({'node':node.get('name',str(i)),'matrix':[list(r)for r in world]})
            for prim in d['meshes'][node['mesh']]['primitives']:
                acc=d['accessors'][prim['attributes']['POSITION']];assert acc['componentType']==5126 and not acc.get('sparse');view=d['bufferViews'][acc['bufferView']];offset=view.get('byteOffset',0)+acc.get('byteOffset',0);stride=view.get('byteStride',12)
                points.extend([list(world@Vector(struct.unpack_from('<3f',binary,offset+k*stride)))for k in range(acc['count'])])
        for child in node.get('children',[]):visit(child,world)
    for i in d['scenes'][d.get('scene',0)]['nodes']:visit(i,Matrix.Identity(4))
    return {'bounds':bounds(np.array(points)),'mesh_node_world_matrices':worlds,'materials':[{'name':m.get('name'),'alpha_mode':m.get('alphaMode','OPAQUE'),'alpha_cutoff':m.get('alphaCutoff',.5)}for m in d.get('materials',[])]}

def obj_material(recipe,grey=False):
    mode=recipe['alpha_mode'];assert mode in ['OPAQUE','MASK','BLEND']
    m=bpy.data.materials.new(recipe.get('name',recipe['group']));m.use_nodes=True;m.use_backface_culling=not recipe['double_sided'];nodes=m.node_tree.nodes;links=m.node_tree.links;bs=nodes.get('Principled BSDF');base=recipe.get('base_color',[1,1,1,1]);bs.inputs['Base Color'].default_value=base
    bs.inputs['Roughness'].default_value=1;bs.inputs['Metallic'].default_value=0
    texpath=recipe.get('texture_path');texture=None
    if texpath:
        p=Path(texpath).resolve();assert p.is_file()
        if recipe.get('texture_sha256'):assert SHA(p)==recipe['texture_sha256']
        texture=nodes.new('ShaderNodeTexImage');texture.image=bpy.data.images.load(str(p),check_existing=True);texture.interpolation=recipe.get('interpolation','Closest');texture.extension=recipe.get('extension','REPEAT')
        uv=nodes.new('ShaderNodeTexCoord');output=uv.outputs['UV']
        if recipe.get('flip_v',False):
            sep=nodes.new('ShaderNodeSeparateXYZ');links.new(output,sep.inputs[0]);sub=nodes.new('ShaderNodeMath');sub.operation='SUBTRACT';sub.inputs[0].default_value=1;links.new(sep.outputs['Y'],sub.inputs[1]);combine=nodes.new('ShaderNodeCombineXYZ');links.new(sep.outputs['X'],combine.inputs['X']);links.new(sub.outputs[0],combine.inputs['Y']);output=combine.outputs[0]
        mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY_ADD';mapping.inputs[1].default_value=(*recipe.get('uv_scale',[1,1]),1);mapping.inputs[2].default_value=(*recipe.get('uv_offset',[0,0]),0);links.new(output,mapping.inputs[0]);links.new(mapping.outputs[0],texture.inputs['Vector']);rgb=nodes.new('ShaderNodeMixRGB');rgb.blend_type='MULTIPLY';rgb.inputs[0].default_value=1;rgb.inputs[2].default_value=base;links.new(texture.outputs['Color'],rgb.inputs[1]);links.new(rgb.outputs[0],bs.inputs['Base Color'])
    if mode!='OPAQUE':
        alpha=nodes.new('ShaderNodeMath');alpha.operation='MULTIPLY';alpha.inputs[1].default_value=base[3]
        if texture:links.new(texture.outputs['Alpha'],alpha.inputs[0])
        else:alpha.inputs[0].default_value=1
        output=alpha.outputs[0]
        if mode=='MASK':
            cutoff=nodes.new('ShaderNodeMath');cutoff.operation='LESS_THAN';cutoff.inputs[1].default_value=recipe['alpha_cutoff'];links.new(output,cutoff.inputs[0]);keep=nodes.new('ShaderNodeMath');keep.operation='SUBTRACT';keep.inputs[0].default_value=1;links.new(cutoff.outputs[0],keep.inputs[1]);output=keep.outputs[0]
        links.new(output,bs.inputs['Alpha'])
        if hasattr(m,'surface_render_method'):m.surface_render_method='DITHERED'
    return m

def read_obj(path,asset):
    verts=[];uv=[];normals=[];faces=[];faceuv=[];facenormals=[];groups=[];group='default'
    for line in path.read_text(encoding='utf8').splitlines():
        q=line.split()
        if not q:continue
        if q[0]=='v':verts.append(tuple(map(float,q[1:4])))
        elif q[0]=='vt':uv.append(tuple(map(float,q[1:3])))
        elif q[0]=='vn':normals.append(tuple(map(float,q[1:4])))
        elif q[0]=='g':group=' '.join(q[1:])
        elif q[0]=='f':
            row=[x.split('/')for x in q[1:]];faces.append([int(x[0])-1 if int(x[0])>0 else len(verts)+int(x[0])for x in row]);faceuv.append([int(x[1])-1 if int(x[1])>0 else len(uv)+int(x[1])for x in row]if all(len(x)>1 and x[1]for x in row)else None);groups.append(group);facenormals.append([int(x[2])-1 if int(x[2])>0 else len(normals)+int(x[2])for x in row]if all(len(x)>2 and x[2]for x in row)else None)
    mesh=bpy.data.meshes.new(path.stem);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(path.stem,mesh);bpy.context.scene.collection.objects.link(o)
    if uv:
        layer=mesh.uv_layers.new(name='OBJ native vt')
        for poly,ids in zip(mesh.polygons,faceuv):
            if ids:
                for loop,index in zip(poly.loop_indices,ids):layer.data[loop].uv=uv[index]
    if normals and all(ids is not None for ids in facenormals):
        loop_normals=[normals[i]for ids in facenormals for i in ids]
        for poly in mesh.polygons:poly.use_smooth=True
        mesh.normals_split_custom_set(loop_normals)
    recipes={r['group']:r for r in asset.get('obj_materials',[])};names=list(dict.fromkeys(groups))
    if recipes:
        assert set(names)==set(recipes),(set(names),set(recipes));assert asset['alpha_policy']=='explicit_obj_recipe'
        for name in names:mesh.materials.append(obj_material(recipes[name]))
    else:
        assert asset['alpha_policy']=='raw_mesh_unverified','OBJ requires exact alpha recipe or explicit raw warning'
        for name in names:
            m=bpy.data.materials.new('RAW OPAQUE '+name);m.use_nodes=True;mesh.materials.append(m)
    for poly,group in zip(mesh.polygons,groups):poly.material_index=names.index(group)
    return [o],{'groups':{n:groups.count(n)for n in names},'obj_axis_import':'literal v; no Blender OBJ importer rotation','uv_import':'literal vt per polygon corner; flip_v only if recipe explicitly requests','native_bounds':bounds(np.array(verts)),'custom_OBJ_vn_restored':bool(normals and all(ids is not None for ids in facenormals)),'materials':list(recipes.values())}

def alpha_signature(material):
    records=[]
    for bs in material.node_tree.nodes:
        if bs.type!='BSDF_PRINCIPLED':continue
        sock=bs.inputs['Alpha'];seen=set();rows=[]
        def walk(node):
            if node.name in seen:return
            seen.add(node.name);rows.append({'node':node.name,'type':node.bl_idname,'operation':getattr(node,'operation',None),'image':node.image.name if node.type=='TEX_IMAGE'and node.image else None,'inputs':[(s.name,str(s.default_value)if hasattr(s,'default_value')else None,[(l.from_node.name,l.from_socket.name)for l in s.links])for s in node.inputs]})
            for s in node.inputs:
                for link in s.links:walk(link.from_node)
        for link in sock.links:walk(link.from_node)
        records.append({'bsdf':bs.name,'alpha_default':sock.default_value,'alpha_links':[(l.from_node.name,l.from_socket.name)for l in sock.links],'upstream':sorted(rows,key=lambda x:x['node'])})
    return {'alpha':records,'surface_render_method':getattr(material,'surface_render_method',None),'alpha_threshold':getattr(material,'alpha_threshold',None),'backface_culling':material.use_backface_culling}

def grey_material(source):
    assert source and source.use_nodes,'Native material without resolved alpha nodes'
    m=source.copy();m.name='PAIR GREY '+source.name;before=alpha_signature(m);bsdfs=[n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'];assert bsdfs,'Unsupported native shader; supply resolved alpha recipe'
    for bs in bsdfs:
        for name,value in [('Base Color',(.42,.42,.42,1)),('Metallic',0),('Roughness',.85),('Emission Color',(0,0,0,1)),('Emission Strength',0),('Normal',None)]:
            if name not in bs.inputs:continue
            for link in list(bs.inputs[name].links):m.node_tree.links.remove(link)
            if value is not None:bs.inputs[name].default_value=value
    after=alpha_signature(m);assert before==after,'Grey binding changed alpha'
    return m,before

def load_asset(asset,role):
    path=Path(asset['path']).resolve();assert SHA(path)==asset['sha256'];assert asset['pose']=='bind_rest';before=set(bpy.data.objects);kind=path.suffix.lower();audit={}
    if kind=='.obj':originals,audit=read_obj(path,asset);adapter=Matrix.Identity(4)
    else:
        assert asset['alpha_policy']=='preserve_embedded'
        if kind in ['.glb','.gltf']:
            assert kind=='.glb','Use self-contained GLB to bind every input byte';bpy.ops.import_scene.gltf(filepath=str(path),import_shading='NORMALS');adapter=Matrix(((1,0,0,0),(0,0,1,0),(0,-1,0,0),(0,0,0,1)));audit['gltf_raw_static']=glb_static_bounds(path)
        elif kind=='.blend':
            with bpy.data.libraries.load(str(path),link=False)as(src,dst):dst.objects=src.objects
            for obj in dst.objects:
                if obj:bpy.context.scene.collection.objects.link(obj)
            adapter=Matrix.Identity(4)
        else:raise ValueError('Expected OBJ/GLB/blend')
        loaded=set(bpy.data.objects)-before
        for o in loaded:
            if o.animation_data:o.animation_data_clear()
            if o.type=='ARMATURE':o.data.pose_position='REST'
        bpy.context.view_layer.update()
        generated_shapes={bone.custom_shape for armature in loaded if armature.type=='ARMATURE' for bone in armature.pose.bones if bone.custom_shape is not None}
        source_mesh_names={r['node']for r in audit.get('gltf_raw_static',{}).get('mesh_node_world_matrices',[])}
        excluded=[o for o in loaded if o.type=='MESH' and kind=='.glb' and o in generated_shapes and o.name not in source_mesh_names]
        audit['excluded_importer_custom_shapes']=[{'name':o.name,'reason':'Explicit bone.custom_shape object, not a GLB source mesh node; not fish geometry','hide_render':o.hide_render}for o in excluded]
        originals=[o for o in loaded if o.type=='MESH' and o not in excluded]
    assert originals,'Empty fish mesh set';mapping=axis_matrix(asset['canonical_from_source_axes']);uniform=float(asset['uniform_scale']);assert uniform>0 and math.isfinite(uniform);out=[];native=[];alpha=[]
    audit['source_objects']=[]
    for obj in sorted(originals,key=lambda o:o.name):
        transform=adapter@obj.matrix_world;points=np.array([list(transform@v.co)for v in used_points(obj)]);native.append(points);audit['source_objects'].append({'name':obj.name,'vertices':len(obj.data.vertices),'polygons':len(obj.data.polygons),'source_world_matrix':[list(r)for r in transform],'modifiers_not_baked':[m.type for m in obj.modifiers]})
        mesh=obj.data.copy();matrix=Matrix.Scale(uniform,4)@mapping@transform;mesh.transform(matrix)
        if matrix.to_3x3().determinant()<0:mesh.flip_normals()
        render=bpy.data.objects.new(role+' '+obj.name,mesh);bpy.context.scene.collection.objects.link(render);render['pair_role']=role;render['native_materials']=[m.name for m in mesh.materials];grey=[]
        for material in mesh.materials:
            clone,sig=grey_material(material);grey.append(clone);alpha.append({'source_material':material.name,'alpha_before_equals_after':True,'signature':sig})
        render['grey_materials']=[m.name for m in grey];out.append(render)
    native=np.concatenate(native);audit['imported_file_native_bounds']=bounds(native)
    if kind=='.glb':
        delta=float(np.max(np.abs(np.array(audit['gltf_raw_static']['bounds'])-np.array(bounds(native)))));span=float(np.ptp(native,axis=0).max());assert delta<max(1e-7,span*1e-5),(path,delta);audit['raw_node_world_vs_import_bounds_max_error']=delta
    for obj in set(bpy.data.objects)-before:
        if obj not in out:obj.hide_render=True
    vertices=np.concatenate([np.array([list(v.co)for v in used_points(o)])for o in out]);lo,hi=vertices.min(0),vertices.max(0);length=float(hi[0]-lo[0]);assert length>0;center=(lo+hi)*.5;factor=1/length
    normalize=Matrix.Scale(factor,4)@Matrix.Translation(-Vector(center))
    for o in out:o.data.transform(normalize)
    audit.update({'path':str(path),'sha256':SHA(path),'alpha_policy':asset['alpha_policy'],'pose':'raw mesh bind/rest; no animation sampled or tail straightened','source_axis_mapping':asset['canonical_from_source_axes'],'source_uniform_scale':uniform,'signed_axis_determinant':mapping.to_3x3().determinant(),'all_mesh_axis_span_before_normalize':length,'normalization_factor':factor,'center_before_normalize':center.tolist(),'canonical_bounds_before_normalize':[lo.tolist(),hi.tolist()],'applied_total_uniform_scale':uniform*factor,'definition':'Complete mesh + all fins longitudinal canonical X span normalized to1; engineering span, not biological TL','normalized_bounds':bounds((vertices-center)*factor),'alpha_audit':alpha,'mesh_filter':'all source mesh objects / all OBJ groups; no component or face exclusion'})
    return out,audit

def label(text,camera,x,y,size,color=(.08,.08,.08,1)):
    curve=bpy.data.curves.new('Annotation','FONT');curve.body=text;curve.size=size;curve.align_x='LEFT';o=bpy.data.objects.new('Annotation',curve);bpy.context.scene.collection.objects.link(o);o.matrix_world=camera.matrix_world@Matrix.Translation((x,y,-1));mat=bpy.data.materials.new('Annotation ink');mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();e=nodes.new('ShaderNodeEmission');e.inputs['Color'].default_value=color;out=nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(e.outputs[0],out.inputs[0]);curve.materials.append(mat);return o

def main(a):
    config=Path(a.pair).resolve();pair=json.loads(config.read_text(encoding='utf8'));out=Path(a.output).resolve();assert out.is_relative_to(ROOT/'output')and not out.exists();out.mkdir(parents=True);bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=False;scene.cycles.device='CPU';w,h=pair.get('resolution',[1280,800]);scene.render.resolution_x=w;scene.render.resolution_y=h;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=a.clean_rgba or bool(pair.get('transparent_background',False));scene.view_settings.view_transform='Standard';scene.view_settings.look='Medium High Contrast' if False else 'None'
    scene.world=bpy.data.worlds.new('Pair world');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.88,.88,.88,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7
    assets={};audits={}
    for role in ['ours','reference']:assets[role],audits[role]=load_asset(pair[role],role)
    allv=np.concatenate([np.array([list(v.co)for v in used_points(o)])for objects in assets.values()for o in objects]);lo,hi=allv.min(0),allv.max(0);center=(lo+hi)*.5;span=hi-lo;aspect=w/h;ortho=max(span[0]/.88,max(span[1],span[2])*aspect/.62)
    camdata=bpy.data.cameras.new('Common orthographic camera');camdata.type='ORTHO';camdata.sensor_fit='HORIZONTAL';camdata.ortho_scale=float(ortho);camdata.clip_start=.01;camdata.clip_end=100;camera=bpy.data.objects.new('Common camera',camdata);scene.collection.objects.link(camera);scene.camera=camera
    for pos,energy in [((-2,3,4),180),((2,1,-3),90)]:
        data=bpy.data.lights.new('Common light','AREA');data.energy=energy;data.shape='DISK';data.size=4;o=bpy.data.objects.new('Common light',data);scene.collection.objects.link(o);o.location=Vector(center)+Vector(pos);o.rotation_euler=(Vector(center)-o.location).to_track_quat('-Z','Y').to_euler()
    report={'ok':True,'kind':'read_only_full_fish_pair_renderer','pair_config':str(config),'pair_sha256':SHA(config),'assets_modified':False,'assets':audits,'common_bounds':[lo.tolist(),hi.tolist()],'resolution':[w,h],'camera_type':'ORTHO','clean_rgba':a.clean_rgba,'preflight_only':a.preflight_only,'rendered':not a.preflight_only,'transparent_background':scene.render.film_transparent,'same_ortho_scale_both_views':float(ortho),'normalization_not_biological':True,'reference_shader_limit':'Standard diffuse plus explicit source alpha diagnostic; original custom game shader not reproduced','views':[],'files':{}}
    for view in ['side','top']:
        camera.location=Vector(center)+Vector((0,0,5)if view=='side'else(0,5,0));camera.rotation_euler=(0,0,0)if view=='side'else(-math.pi/2,0,0);bpy.context.view_layer.update();projection=camera.calc_matrix_camera(bpy.context.evaluated_depsgraph_get(),x=w,y=h);pv=projection@camera.matrix_world.inverted()
        def project(v):
            p=pv@Vector((*v,1));return [(p[0]/p[3]+1)*w/2,(1-p[1]/p[3])*h/2]
        camera_local=[camera.matrix_world.inverted()@Vector(v)for v in allv];assert all(-camdata.clip_end<p.z<-camdata.clip_start for p in camera_local),'Geometry behind camera or outside depth clip'
        pp=np.array([project(v)for v in allv]);assert (pp[:,0]>0).all()and(pp[:,0]<w).all()and(pp[:,1]>0).all()and(pp[:,1]<h).all();px=abs(project((1,0,0))[0]-project((0,0,0))[0]);report['views'].append({'view':view,'screen_axes':{'right':'+X','up':'+Y' if view=='side'else'-Z','view_from':'+Z'if view=='side'else'+Y'},'camera_world_matrix':[list(r)for r in camera.matrix_world],'projection_matrix':[list(r)for r in projection],'pixel_per_normalized_X_unit':px,'all_geometry_pixel_bounds':bounds(pp),'all_fins_inside_frame':True})
        if a.preflight_only:continue
        for role in ['ours','reference']:
            for name,objects in assets.items():
                for obj in objects:obj.hide_render=name!=role
            raw=pair[role]['alpha_policy']=='raw_mesh_unverified';text=role.upper()+' | '+pair.get('id','fish pair')+' | '+view.upper();font=ortho*15/w;height=ortho/aspect;notes=[]if a.clean_rgba else[label(text,camera,-ortho*.47,height*.45,font*1.15),label('Equal full-mesh X span=1; engineering normalization, NOT biological TL',camera,-ortho*.47,-height*.41,font),label('Bind/rest pose retained; common camera/light; no tail straightening',camera,-ortho*.47,-height*.46,font)]
            for mode in ['grey','native']if a.native and not raw else ['grey']:
                caption='RAW MESH: alpha unknown; fin card edges are NOT visible cutout outlines' if raw else 'MATTE GREY + original/resolved alpha; standard diffuse diagnostic' if mode=='grey' else 'ORIGINAL BASECOLOR/ALPHA; diagnostic lighting, not original game shader'
                mode_note=None if a.clean_rgba else label(caption,camera,-ortho*.47,height*.39,font,(.75,.05,.02,1)if raw else(.08,.08,.08,1))
                for obj in assets[role]:
                    for i,name in enumerate(obj['grey_materials'if mode=='grey'else'native_materials']):obj.data.materials[i]=bpy.data.materials[name]
                file=out/f'{role}-{view}-{mode}.png';scene.render.filepath=str(file);bpy.ops.render.render(write_still=True);report['files'][file.name]=SHA(file)
                if mode_note is not None:bpy.data.objects.remove(mode_note,do_unlink=True)
            for obj in notes:bpy.data.objects.remove(obj,do_unlink=True)
    assert abs(report['views'][0]['pixel_per_normalized_X_unit']-report['views'][1]['pixel_per_normalized_X_unit'])<1e-6
    report['source_files_unchanged']=all(SHA(pair[r]['path'])==pair[r]['sha256']for r in ['ours','reference']);assert report['source_files_unchanged'];jwrite(out/('preflight.validation.json'if a.preflight_only else'render.validation.json'),report);print(('PAIR_PREFLIGHT_OK 'if a.preflight_only else'PAIR_RENDER_OK ')+str(out))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pair',required=True);p.add_argument('--output',required=True);p.add_argument('--native',action='store_true');p.add_argument('--preflight-only',action='store_true');p.add_argument('--clean-rgba',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);preexisting=Path(a.output).exists()
    try:main(a)
    except Exception as error:
        out=Path(a.output).resolve()
        if not preexisting and out.is_relative_to(ROOT/'output'):
            out.mkdir(parents=True,exist_ok=True);jwrite(out/('preflight.validation.json'if a.preflight_only else'render.validation.json'),{'ok':False,'failure_type':type(error).__name__,'failure':str(error),'pair_config':str(Path(a.pair).resolve()),'preflight_only':a.preflight_only,'assets_modified':False})
        raise
