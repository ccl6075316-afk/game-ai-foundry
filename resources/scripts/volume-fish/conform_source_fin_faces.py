"""Bounded static finite-face repair on persisted two-layer source cages.

Original source outline, full basal-domain threshold and body remain frozen.
Split matching source edges on both layers; translate each free foil pair
together, retaining its finite thickness. This is authoring, never a gate pass.
"""
import bpy,bmesh,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def conform(ob,fin,tree,inside,scale,cfg,skin_to_body,whole_triangle_limit):
    band=fin['root_attachment']['root_band'];paired=fin['paired']
    side=-1 if ob.name.endswith(('_left','_left_mesh'))else 1
    vertical=1 if fin['tip'][1]<fin['anchor'][1]else-1
    settings=cfg['fins'][fin['name']];collar=cfg['finite_face_repair']['root_collar_mm']
    trigger=cfg['finite_face_repair']['penetration_trigger_mm'];clearance=cfg['free_clearance_mm']
    assert 0<collar<=.6 and 0<=trigger<.02 and clearance>=.02
    limit=cfg['finite_face_repair'].get('max_added_vertices_per_fin',48)
    assert type(limit)is int and 0<limit<=64
    history=[];added=0
    mesh=ob.data
    if 'foundry_fin_layer'not in mesh.attributes:
        n=len(mesh.vertices)//2
        assert len(mesh.vertices)==2*n
        assert all(abs(mesh.attributes[k].data[i].value-mesh.attributes[k].data[i+n].value)<1e-7 for k in ['foundry_fin_source_u','foundry_fin_source_v']for i in range(n)),'Original ordered two-layer source required'
        attr=mesh.attributes.new('foundry_fin_layer','INT','POINT')
        for i in range(2*n):attr.data[i].value=int(i>=n)
    for iteration in range(10):
        mesh=ob.data;mesh.calc_loop_triangles();v=[p.co.copy()for p in mesh.vertices]
        attrs={n:[p.value for p in mesh.attributes[n].data]for n in ['foundry_fin_source_t','foundry_fin_source_u','foundry_fin_source_v']}
        ts=attrs['foundry_fin_source_t'];xy=list(zip(attrs['foundry_fin_source_u'],attrs['foundry_fin_source_v']))
        layers=[q.value for q in mesh.attributes['foundry_fin_layer'].data]
        root_ids=[i for i,t in enumerate(ts)if t<=band+1e-7]
        root_faces=[tuple(t.vertices)for t in mesh.loop_triangles if all(i in root_ids for i in t.vertices)]
        root_tree=BVHTree.FromPolygons(v,root_faces,all_triangles=True)if root_faces else None
        from mathutils.kdtree import KDTree
        kd=KDTree(len(root_ids))
        for k,i in enumerate(root_ids):kd.insert(v[i],k)
        kd.balance()
        def bad(p):
            if not inside(p):return False
            depth=tree.find_nearest(p)[3]*scale*1000
            if depth<=trigger:return False
            distance=kd.find(p)[2]
            if root_tree:distance=min(distance,root_tree.find_nearest(p)[3])
            return not(distance*scale*1000<=collar and depth<=collar)
        edges=set();faults=0
        for tri in mesh.loop_triangles:
            ids=tuple(tri.vertices);q=[v[i]for i in ids]
            if not any(bad(p)for p in [sum(q,Vector())/3]+[q[k]*.6+q[(k+1)%3]*.2+q[(k+2)%3]*.2 for k in range(3)]+[a.lerp(b,t)for a,b in zip(q,q[1:]+q[:1])for t in [.25,.5,.75]]):continue
            faults+=1
            options=[tuple(sorted((a,b)))for a,b in zip(ids,ids[1:]+ids[:1])if layers[a]==layers[b]and np.linalg.norm(np.array(xy[a])-xy[b])>1e-7]
            assert options,'Collapsed zero-source-area wall intersects body: '+ob.name
            # Source edge length chooses the coarse chord; close foil edges
            # cannot consume the budget through repeated thickness splits.
            edges.add(max(options,key=lambda e:np.linalg.norm(np.array(xy[e[0]])-xy[e[1]])))
        history.append({'iteration':iteration,'failed_faces':faults,'marked_edges':len(edges),'triangles':len(mesh.loop_triangles)})
        if not edges:return {'added_vertices':added,'history':history,'root_domain_unchanged':True,'source_paired_edge_splits':True}
        groups={}
        for i,p in enumerate(xy):groups.setdefault(tuple(round(x,7)for x in p),[]).append(i)
        assert all(len(ids)==2 for ids in groups.values()),'Exactly two persisted source layers required'
        mate={i:j for ids in groups.values()for i,j in [ids,ids[::-1]]}
        edges|={tuple(sorted((mate[a],mate[b])))for a,b in list(edges)}
        assert added+len(edges)<=limit,(ob.name,'Finite repair exceeded local vertex bound',history)
        current=0
        for other in bpy.data.objects:
            if other.type=='MESH':other.data.calc_loop_triangles();current+=len(other.data.loop_triangles)
        assert current+2*len(edges)<=whole_triangle_limit,'Finite repair exceeds whole-fish hard budget'
        bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();old=list(bm.verts);new={}
        source_faces=[(tuple(f.verts),f.material_index,f.smooth)for f in bm.faces]
        assert all(len(ids)==3 for ids,_,_ in source_faces),'Freeze source triangles before finite repair'
        uv_layers=list(bm.loops.layers.uv.values());uv_maps=[]
        for layer in uv_layers:
            mapping={}
            for f in bm.faces:
                for loop in f.loops:
                    value=loop[layer].uv.copy()
                    if loop.vert in mapping:assert (mapping[loop.vert]-value).length<1e-7,'Run finite repair before fin-wall color seams'
                    mapping[loop.vert]=value
            uv_maps.append(mapping)
        for a,b in sorted(edges):
            edge=bm.edges.get((old[a],old[b]));assert edge,(ob.name,'Paired source edge missing',iteration,a,b,layers[a],layers[b],xy[a],xy[b],history)
            _,vert=bmesh.utils.edge_split(edge,old[a],.5);new[(a,b)]=vert
            vert[bm.verts.layers.int['foundry_fin_layer']]=layers[a]
            for mapping in uv_maps:mapping[vert]=(mapping[old[a]]+mapping[old[b]])/2
        handled=set();root_hits=[]
        for edge,first in new.items():
            if edge in handled:continue
            other=tuple(sorted(mate[i]for i in edge));second=new[other];handled|={edge,other}
            t=sum(ts[i]for i in edge)/2;points=[first.co.copy(),second.co.copy()]
            if t<=band+1e-7:
                for i,vert in enumerate([first,second]):
                    if paired and settings.get('native_xz_foil'):
                        p=points[i];hit,normal,face,_=tree.ray_cast(Vector((p.x,side*2,p.z)),Vector((0,-side,0)),4)
                        assert hit is not None and abs(normal.y)>.1,'Native XZ root flank is undefined'
                    else:hit,normal,face,_=tree.find_nearest(points[i])
                    offsets=settings.get('root_layer_offsets_mm',[-cfg['root_inset_mm'],cfg.get('root_surface_offset_mm',.04)])
                    outboard=int((points[1]-points[0]).dot(normal)>0)
                    offset=offsets[int((i==1)==bool(outboard))]
                    vert.co=hit+(Vector((0,side*offset/1000/scale/abs(normal.y),0))if paired and settings.get('native_xz_foil')else normal*(offset/1000/scale));root_hits.append((vert,hit,face))
            else:
                lift=0.
                for p in points:
                    axis=1 if paired else 2;sign=side if paired else vertical;origin=p.copy();origin[axis]=sign*2;direction=Vector();direction[axis]=-sign
                    hit,normal,face,_=tree.ray_cast(origin,direction,4)
                    if hit is not None:lift=max(lift,sign*(hit[axis]-p[axis])+clearance/1000/scale)
                for vert,p in zip([first,second],points):
                    p[1 if paired else 2]+=(side if paired else vertical)*max(0,lift);vert.co=p
        # Split by source-edge identity, using the same order on both layers.
        # Beauty triangulation in physical space can choose different diagonals
        # on the two curved caps and destroy the paired-source edge contract.
        recipes=[]
        edge_order=sorted(new,key=lambda e:tuple(sorted((xy[e[0]],xy[e[1]]))))
        for original,material,smooth in source_faces:
            pieces=[original]
            for edge in edge_order:
                a,b=map(old.__getitem__,edge);mid=new[edge];split=[]
                for piece in pieces:
                    if a not in piece or b not in piece:split.append(piece);continue
                    for k in range(3):
                        x,y,z=piece[k],piece[(k+1)%3],piece[(k+2)%3]
                        if {x,y}=={a,b}:split.extend([(x,mid,z),(mid,y,z)]);break
                pieces=split
            recipes.extend((piece,material,smooth)for piece in pieces)
        for face in list(bm.faces):bm.faces.remove(face)
        for ids,material,smooth in recipes:
            face=bm.faces.new(ids);face.material_index=material;face.smooth=smooth
            for layer,mapping in zip(uv_layers,uv_maps):
                for loop in face.loops:loop[layer].uv=mapping[loop.vert]
        bm.verts.index_update();hits=[(v.index,h,f)for v,h,f in root_hits]
        assert all(e.is_manifold for e in bm.edges);bm.to_mesh(mesh);bm.free();mesh.update()
        for i,hit,face in hits:skin_to_body(ob,i,hit,face)
        added+=len(edges)
    raise AssertionError((ob.name,'Finite source-face repair did not converge',history))
