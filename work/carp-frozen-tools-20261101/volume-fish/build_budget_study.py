"""Blender: bounded multi-species triangle study, not a production remesher.

Explicit per-species part budgets avoid copying zander's fin allocation to a
hammerhead. Preserve material identities and transport all skinning attributes.
"""
import bpy,bmesh,json,sys,hashlib
from pathlib import Path
from collections import defaultdict,deque
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
repo=Path(__file__).resolve().parents[3]
root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
assert root.is_relative_to((repo/'projects/fishing-2d/plans/reviews/fish-volume-budget-v3').resolve())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=json.loads((root/'source.validation.json').read_text())
config_path=repo/'resources/volume-fish/volume-budget-study-v3.json'
config=json.loads(config_path.read_text());settings=config['species'][source['species']]
assert abs(sum(settings['node_budget_weights'].values())-1)<1e-9
assert set(settings['node_budget_weights'])=={n['name'] for n in source['nodes']}
for name,digest in source['binary_sha256'].items():assert sha(root/name)==digest
def array(row,slot,dtype,stride):
    data=np.fromfile(root/row['attributes'][str(slot)],dtype=dtype)
    return data.reshape(-1,stride) if stride else data
def bary(point,tri):
    a,b,c=tri;u=b-a;v=c-a;w=point-a;den=(u@u)*(v@v)-(u@v)**2
    if abs(den)<1e-24:return np.array([1.,0.,0.])
    y=((v@v)*(w@u)-(u@v)*(w@v))/den;z=((u@u)*(w@v)-(u@v)*(w@u))/den
    weights=np.clip([1-y-z,y,z],0,1);return weights/weights.sum()
def volume(vertices,triangles):
    # Reorient independent components at the existing 077 seam identity
    # precision. Raw winding cannot be trusted for a signed volume sum.
    v,inv=np.unique(np.round(vertices,7),axis=0,return_inverse=True)
    t=inv[np.asarray(triangles,int)];owners=defaultdict(list)
    nondeg=np.array([len(set(q))==3 for q in t]);removed=int((~nondeg).sum());t=t[nondeg]
    for i,face in enumerate(t):
        for a,b in zip(face,np.roll(face,-1)):owners[tuple(sorted((int(a),int(b))))].append((i,bool(a<b)))
    bad=sum(len(q)!=2 for q in owners.values())
    if bad:return {'closed_at_seam_precision':False,'invalid_edges':bad,'degenerate_faces_excluded_from_measurement':removed,'native_volume':None}
    adjacent=defaultdict(list)
    for edges in owners.values():
        (a,da),(b,db)=edges;adjacent[a].append((b,da==db));adjacent[b].append((a,da==db))
    flip=np.full(len(t),-1,int);components=[]
    for start in range(len(t)):
        if flip[start]>=0:continue
        flip[start]=0;queue=deque([start]);component=[]
        while queue:
            a=queue.popleft();component.append(a)
            for b,same in adjacent[a]:
                expected=flip[a]^int(same)
                if flip[b]<0:flip[b]=expected;queue.append(b)
                elif flip[b]!=expected:return {'closed_at_seam_precision':False,'native_volume':None,'reason':'Nonorientable'}
        components.append(component)
    t[flip==1]=t[flip==1][:,[0,2,1]];total=0
    for ids in components:
        q=t[ids];total+=abs(np.einsum('ij,ij->i',v[q[:,0]],np.cross(v[q[:,1]],v[q[:,2]])).sum()/6)
    return {'closed_at_seam_precision':True,'components':len(components),'native_volume':float(total),'degenerate_faces_excluded_from_measurement':removed}
prepared=[];measurements=[]
for node in source['nodes']:
    surfaces=[];verts=[];faces=[];mats=[];offset=0
    for row in node['surfaces']:
        v=array(row,0,'<f4',3);t=array(row,12,'<i4',3)
        surfaces.append({'v':v,'t':t,'uv':array(row,4,'<f4',2),'normal':array(row,1,'<f4',3),
          'uv2':array(row,5,'<f4',2) if '5' in row['attributes'] else None,
          'colors':array(row,3,'<f4',4) if '3' in row['attributes'] else None,
          'bones':array(row,10,'<i4',4),'weights':array(row,11,'<f4',4),
          'tree':BVHTree.FromPolygons(v.tolist(),t.tolist(),all_triangles=True)})
        verts.extend(v);faces.extend(t+offset);mats.extend([row['surface']]*len(t));offset+=len(v)
    prepared.append((node,surfaces,verts,faces,mats))
    if node['name'] in settings['body_nodes']:
        measurement=volume(verts,faces);measurement['node']=node['name']
        measurement['standardized_volume_m3']=measurement['native_volume']*node['world_volume_scale'] if measurement['native_volume'] is not None else None
        measurement['native_aabb_dimensions']=np.ptp(np.array(verts),axis=0).tolist()
        measurement['standardized_local_axis_extents_m']=(np.ptp(np.array(verts),axis=0)*node['world_axis_scales']).tolist()
        measurements.append(measurement)
report={'schema_version':1,'species':source['species'],'real_length_cm':source['real_length_cm'],'original_triangles':source['visible_triangles'],'body_measurements':measurements,'scope':'Current authored body shape volume; not a biological displacement measurement. Separate closed components may overlap; unclosed components have no asserted enclosed volume. Fins, eyes and lip relief excluded.','candidates':[],'accepted':False,'production_changed':False}
for budget in settings['whole_fish_triangle_budgets']:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    outputs=[];total=0;body_checks=[]
    for node,surfaces,verts,faces,mats in prepared:
        mesh=bpy.data.meshes.new(node['name']);mesh.from_pydata(verts,[],faces);mesh.update()
        obj=bpy.data.objects.new(node['name'],mesh);bpy.context.collection.objects.link(obj)
        for si in range(len(surfaces)):mesh.materials.append(bpy.data.materials.new('surface'+str(si)))
        for poly,mat in zip(mesh.polygons,mats):poly.material_index=mat
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=config['weld_distance_native']);bm.to_mesh(mesh);bm.free();mesh.update()
        goal=max(config['minimum_node_triangles'],int(budget*settings['node_budget_weights'][node['name']]))
        modifier=obj.modifiers.new('whole-fish-budget','DECIMATE');modifier.ratio=min(1,goal/max(1,len(mesh.polygons)));modifier.use_collapse_triangulate=True
        bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=modifier.name)
        mesh=obj.data;mesh.calc_loop_triangles();parts=[]
        if node['name'] in settings['body_nodes']:
            check=volume([tuple(v.co) for v in mesh.vertices],[tuple(t.vertices) for t in mesh.loop_triangles]);check['node']=node['name'];body_checks.append(check)
        for si,s in enumerate(surfaces):
            tris=[q for q in mesh.loop_triangles if q.material_index==si]
            assert tris,(node['name'],si,'Budget removed a required material role')
            used=sorted(set(int(i) for tri in tris for i in tri.vertices));mapping={v:i for i,v in enumerate(used)}
            positions=[];indices=[];uvs=[];uv2=[];colors=[];normals=[];bones=[];weights=[];references=[];errors=[]
            for vertex_id in used:
                p=np.array(mesh.vertices[vertex_id].co);hit,_,face,distance=s['tree'].find_nearest(Vector(p));assert hit is not None
                ids=s['t'][face];bw=bary(np.array(hit),s['v'][ids]);references.append([ids.tolist(),bw.tolist()]);errors.append(distance)
                positions.append(p.tolist());uvs.append((s['uv'][ids].T@bw).tolist())
                if s['uv2'] is not None:uv2.append((s['uv2'][ids].T@bw).tolist())
                if s['colors'] is not None:colors.append((s['colors'][ids].T@bw).tolist())
                normal=s['normal'][ids].T@bw;normal/=max(np.linalg.norm(normal),1e-20);normals.append(normal.tolist())
                merged={}
                for idx,factor in zip(ids,bw):
                    for b,w in zip(s['bones'][idx],s['weights'][idx]):merged[int(b)]=merged.get(int(b),0)+float(w*factor)
                order=sorted(merged,key=lambda x:-merged[x])[:4];ww=[merged[b] for b in order];amount=sum(ww);assert amount>0
                bones.append(order+[0]*(4-len(order)));weights.append([w/amount for w in ww]+[0]*(4-len(ww)))
            for tri in tris:indices.extend(mapping[int(i)] for i in tri.vertices)
            points=np.array(positions);tt=np.array(indices).reshape(-1,3);a=points[tt]
            zero=int((np.linalg.norm(np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]),axis=1)<=2e-17).sum())
            total+=len(tris)
            parts.append({'surface':si,'positions':positions,'indices':indices,'uv':uvs,'uv2':uv2,'colors':colors,'normals':normals,'bones':bones,'weights':weights,'references':references,'source_projection_distance_native_max':max(errors,default=0),'triangles':len(tris),'zero_area_triangles':zero})
        outputs.append({'name':node['name'],'path':node['path'],'surfaces':parts})
    result={'schema_version':1,'species':source['species'],'budget':budget,'actual_triangles':total,'nodes':outputs,'accepted':False,'method':'Weld native seams; collapse per authored part budget; barycentric transport from original per material surface.','settings_sha256':sha(config_path),'source_sha256':sha(root/'source.validation.json'),'builder_sha256':sha(__file__)}
    path=root/('low-'+str(budget)+'.json');path.write_text(json.dumps(result,separators=(',',':')),encoding='utf8')
    report['candidates'].append({'budget':budget,'actual_triangles':total,'vertices':sum(len(p['positions']) for n in outputs for p in n['surfaces']),'zero_area_triangles':sum(p['zero_area_triangles'] for n in outputs for p in n['surfaces']),'body_checks':body_checks,'recipe_sha256':sha(path),'part_triangles':{n['name']:sum(p['triangles'] for p in n['surfaces']) for n in outputs}})
    print('VOLUME_BUDGET',source['species'],budget,total,flush=True)
(root/'structure.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
