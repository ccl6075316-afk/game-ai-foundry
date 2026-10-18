"""Blender full membrane rest repair, preserving the full frozen basal selection.
Append only replacement POSITION/NORMAL accessors; rig/skin/animation/original
binary prefix remain untouched. Paired fins retain source X/Y silhouette.
"""
import copy,hashlib,json,struct,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from patch_existing_fin_meshes import read,write

def values(d,b,index):
    a=d['accessors'][index];v=d['bufferViews'][a['bufferView']];count={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];fmt={5126:'f',5125:'I',5123:'H',5121:'B'}[a['componentType']];size=struct.calcsize(fmt);start=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',count*size)
    return [struct.unpack_from('<'+fmt*count,b,start+i*stride) for i in range(a['count'])]

def main():
    args=sys.argv[sys.argv.index('--')+1:];plan=json.loads(Path(args[0]).read_text(encoding='utf8'));spec=next(i for i in plan['items'] if i['species']==args[1]);out=Path(args[2]);out.mkdir(parents=True,exist_ok=True)
    d,b=read(spec['model']);original=bytes(b);positions=[];triangles=[]
    body=next(n for n in d['nodes'] if n.get('name')==spec['body'] and 'mesh' in n)
    for prim in d['meshes'][body['mesh']]['primitives']:
        vs=values(d,b,prim['attributes']['POSITION']);ids=[x[0] for x in values(d,b,prim['indices'])];base=len(positions);positions.extend(Vector(v) for v in vs);triangles.extend(tuple(base+j for j in ids[i:i+3]) for i in range(0,len(ids),3))
    volume=sum(positions[a].dot(positions[c].cross(positions[e])) for a,c,e in triangles)/6
    if volume<0:triangles=[tuple(reversed(t)) for t in triangles]
    bvh=BVHTree.FromPolygons(positions,triangles,all_triangles=True)
    def append_vectors(source,rows):
        a=copy.deepcopy(d['accessors'][source]);b.extend(b'\0'*(-len(b)%4));offset=len(b)
        for row in rows:b.extend(struct.pack('<fff',*row))
        a.update(bufferView=len(d['bufferViews']),byteOffset=0,min=[min(v[j] for v in rows) for j in range(3)],max=[max(v[j] for v in rows) for j in range(3)])
        d['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(rows)*12,'target':34962});d['accessors'].append(a);return len(d['accessors'])-1
    settings=spec['membrane_clearance'];changes={};native_scale=float(spec['length_native']);clearance=float(settings['rest_clearance_fraction'])*native_scale;root_inset=float(settings['root_inset_fraction'])*native_scale
    rear=min(v.x for v in positions);span=max(v.x for v in positions)-rear
    posterior=[f for f in triangles if max(positions[j].x for j in f)<=rear+.025*span and (positions[f[1]]-positions[f[0]]).cross(positions[f[2]]-positions[f[0]]).normalized().x<-.5]
    posterior_bvh=BVHTree.FromPolygons(positions,posterior,all_triangles=True)
    for node in d['nodes']:
        if 'mesh' not in node:continue
        name=node.get('name','')
        if name not in settings['targets']:continue
        clearance=float(settings.get('per_fin_clearance_fraction',{}).get(name,settings['rest_clearance_fraction']))*native_scale
        roots=[Vector(v) for v in spec['fins'][name]['rest_points_gltf']];changed=0;maximum=0.
        new_roots=[]
        for prim in d['meshes'][node['mesh']]['primitives']:
            source=prim['attributes']['POSITION'];vs=[Vector(v) for v in values(d,b,source)];ids=[x[0] for x in values(d,b,prim['indices'])]
            for i,pt in enumerate(vs):
                is_root=any((pt-root).length<native_scale*.00002 for root in roots)
                if is_root:
                    tree=posterior_bvh if name in settings['posterior_fins'] else bvh
                    near,normal,_,_=tree.find_nearest(pt);q=near-normal*root_inset
                    if name in ['Dorsal','Adipose','Anal']:
                        vertical=-1 if name=='Anal' else 1
                        hit,n,_,_=bvh.ray_cast(Vector((pt.x,vertical*native_scale,pt.z)),Vector((0,-vertical,0)),native_scale*2)
                        if hit is not None:q=hit-n*root_inset
                    new_roots.append(list(q));maximum=max(maximum,(q-pt).length);vs[i]=q;changed+=1;continue
                bias=float(settings.get('outward_bias_fraction',{}).get(name,0))*native_scale
                if bias:
                    assert name.startswith('Pectoral') or name.startswith('Pelvic'),'Outward bias requires a paired fin'
                    side=1 if name.endswith('_left') else -1
                    start=pt.copy();pt=pt.copy();pt.z+=side*bias;vs[i]=pt;maximum=max(maximum,(pt-start).length)
                near,normal,_,dist=bvh.find_nearest(pt);signed=dist*(1 if (pt-near).dot(normal)>=0 else -1)
                if signed>=clearance:
                    if bias:changed+=1
                    continue
                if name.startswith('Pectoral') or name.startswith('Pelvic'):
                    side=1 if name.endswith('_left') else -1
                    origin=Vector((pt.x,pt.y,side*native_scale));hit,_,_,_=bvh.ray_cast(origin,Vector((0,0,-side)),native_scale*2)
                    q=pt.copy()
                    if hit is not None:q.z=side*max(abs(pt.z),abs(hit.z)+clearance)
                    else:q=near+normal*clearance
                elif name in ['Dorsal','Adipose','Anal']:
                    vertical=-1 if name=='Anal' else 1
                    hit,_,_,_=bvh.ray_cast(Vector((pt.x,vertical*native_scale,pt.z)),Vector((0,-vertical,0)),native_scale*2)
                    q=pt.copy()
                    if hit is not None:q.y=vertical*max(vertical*pt.y,vertical*hit.y+clearance)
                    else:q=near+normal*clearance
                else:
                    # Tail attachment lies at the posterior cap. Keep the free
                    # membrane behind that cap rather than pushing it laterally.
                    origin=Vector((-native_scale,pt.y,pt.z));hit,_,_,_=bvh.ray_cast(origin,Vector((1,0,0)),native_scale*2)
                    q=pt.copy()
                    if hit is not None:q.x=min(pt.x,hit.x-clearance)
                    else:q=near+normal*clearance
                maximum=max(maximum,(q-pt).length);vs[i]=q;changed+=1
            normals=[Vector() for _ in vs]
            for k in range(0,len(ids),3):
                aa,cc,ee=ids[k:k+3];normal=(vs[cc]-vs[aa]).cross(vs[ee]-vs[aa])
                for j in [aa,cc,ee]:normals[j]+=normal
            for i in range(len(normals)):
                if normals[i].length>1e-12:normals[i].normalize()
                else:normals[i]=Vector((0,0,1))
            prim['attributes']['POSITION']=append_vectors(source,vs)
            if 'NORMAL' in prim['attributes']:prim['attributes']['NORMAL']=append_vectors(prim['attributes']['NORMAL'],normals)
        changes[name]={'changed_vertices':changed,'maximum_offset_native':maximum,'rest_clearance_native':clearance,'outward_bias_native':float(settings.get('outward_bias_fraction',{}).get(name,0))*native_scale}
        spec['fins'][name]['rest_points_gltf']=new_roots
    assert bytes(b[:len(original)])==original
    write(out/'fish.glb',d,b)
    report={'ok':True,'source':spec['model'],'source_sha256':hashlib.sha256(Path(spec['model']).read_bytes()).hexdigest(),'output_sha256':hashlib.sha256((out/'fish.glb').read_bytes()).hexdigest(),'root_points_unchanged':False,'roots_reprojected_to_surface':True,'tail_roots_on_posterior_cap':True,'original_binary_prefix_preserved':True,'rest_clearance_native':clearance,'changes':changes}
    spec['model']=str((out/'fish.glb').resolve());spec['model_sha256']=report['output_sha256'];(out/'candidate.plan.json').write_text(json.dumps({'items':[spec]},indent=2),encoding='utf8')
    (out/'repair.validation.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
if __name__=='__main__':main()
