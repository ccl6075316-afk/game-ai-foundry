"""Blender prototype: welded geometric simplification and material/bone transport.

All targets are whole-fish triangle budgets, not percentages of a dense lip mesh.
No production output. Closed-body/fin/dynamic acceptance remains separate.
"""
import bpy,bmesh,json,sys,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
assert root.is_relative_to(Path('E:/game-ai-foundry/projects/fishing-2d/plans/reviews').resolve())
source=json.loads((root/'source.validation.json').read_text())
settings_path=Path(__file__).resolve().parents[2]/'volume-fish/zander-lowpoly-study-v2.json'
settings=json.loads(settings_path.read_text())
assert settings['species']==source['species']=='zander'
assert abs(sum(settings['node_budget_weights'].values())-1)<1e-9
def array(row,slot,dtype,stride):
    data=np.fromfile(root/row['attributes'][str(slot)],dtype=dtype)
    return data.reshape(-1,stride) if stride else data
def bary(point,tri):
    a,b,c=tri;u=b-a;v=c-a;w=point-a;den=(u@u)*(v@v)-(u@v)**2
    if abs(den)<1e-24:return np.array([1.,0.,0.])
    y=((v@v)*(w@u)-(u@v)*(w@v))/den;z=((u@u)*(w@v)-(u@v)*(w@u))/den
    weights=np.clip([1-y-z,y,z],0,1);return weights/weights.sum()
def allocation(name,total):
    return total*settings['node_budget_weights'][name]
prepared=[]
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
for budget in settings['whole_fish_triangle_budgets']:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    outputs=[];total=0
    for node,surfaces,verts,faces,mats in prepared:
        mesh=bpy.data.meshes.new(node['name']);mesh.from_pydata(verts,[],faces);mesh.update()
        obj=bpy.data.objects.new(node['name'],mesh);bpy.context.collection.objects.link(obj)
        for si in range(len(surfaces)):mesh.materials.append(bpy.data.materials.new('surface'+str(si)))
        for poly,mat in zip(mesh.polygons,mats):poly.material_index=mat
        # Geometry weld crosses material/UV duplicate vertices; references are
        # transported per final surface, never by the obsolete vertex IDs.
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=settings['weld_distance_native']);bm.to_mesh(mesh);bm.free();mesh.update()
        goal=max(settings['minimum_node_triangles'],int(allocation(node['name'],budget)))
        modifier=obj.modifiers.new('whole-fish-budget','DECIMATE');modifier.ratio=min(1,goal/max(1,len(mesh.polygons)));modifier.use_collapse_triangulate=True
        bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=modifier.name)
        mesh=obj.data;mesh.calc_loop_triangles()
        parts=[]
        for si,s in enumerate(surfaces):
            tris=[q for q in mesh.loop_triangles if q.material_index==si]
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
            total+=len(tris)
            parts.append({'surface':si,'positions':positions,'indices':indices,'uv':uvs,'uv2':uv2,'colors':colors,'normals':normals,'bones':bones,'weights':weights,'references':references,
              'source_projection_distance_native_max':max(errors,default=0),'triangles':len(tris)})
        outputs.append({'name':node['name'],'path':node['path'],'surfaces':parts})
    output={'schema_version':1,'species':'zander','budget':budget,'actual_triangles':total,'nodes':outputs,'accepted':False,
      'method':'Geometric seam weld, Blender collapse decimation, nearest original per-material barycentric UV/normal/bone/reference transport.',
      'settings_sha256':hashlib.sha256(settings_path.read_bytes()).hexdigest(),
      'source_sha256':hashlib.sha256((root/'source.validation.json').read_bytes()).hexdigest(),'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    path=root/('low-'+str(budget)+'.json');path.write_text(json.dumps(output,separators=(',',':')),encoding='utf8')
    print('WHOLE_LOW',budget,total,flush=True)
