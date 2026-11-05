"""Replace whole chest basal patches with the corresponding finite body skin.

Relocating cap vertices does not make the triangles between them follow a new
body facet. Clip each complete original footprint into the current body mesh,
split its free-fin boundary consistently, and share the body's exact skin
weights. This edits only touched body triangulation, never its surface/pixels.
"""
import bpy,bmesh,json,sys,hashlib,shutil
from pathlib import Path
from collections import Counter
import numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from finite_triangle_constraints import constrain

def bary2(p,t):
    u=np.linalg.solve(np.column_stack((t[1]-t[0],t[2]-t[0])),p-t[0])
    return np.array([1-u.sum(),*u])

def inside(p,cap):
    return any(bary2(p,t).min()>-2e-7 for t in cap)

def boundary(tris):
    counts=Counter(tuple(sorted((a,b)))for t in tris for a,b in zip(t,(*t[1:],t[0])))
    return [e for e,n in counts.items()if n==1]

def weights(ob):
    return [{ob.vertex_groups[g.group].name:float(g.weight)for g in v.groups}for v in ob.data.vertices]

def save_json(path,data):path.write_text(json.dumps(data,indent=2)+'\n')

def coalesce_obsolete_support(body,auth):
    """Remove only whole planar one-ring subdivisions with affine UV/skin."""
    original=len(body.data.vertices);bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table()
    uv=bm.loops.layers.uv.active;deform=bm.verts.layers.deform.active;protected=[];regions=[]
    for row in auth['fins']:
        p=np.array(row['root_points_native'])
        if row['name'].startswith('Pectoral_'):regions.append((p.min(0)-.08,p.max(0)+.08))
        else:protected.extend(p)
    protected=np.array(protected);removed=0
    for vertex in list(bm.verts):
        if not vertex.is_valid or not vertex.is_manifold or len(vertex.link_faces)<3:continue
        center=np.array(vertex.co)
        if not any((center>=lo).all()and(center<=hi).all()for lo,hi in regions):continue
        if np.linalg.norm(protected-center,axis=1).min()<3e-6:continue
        fs=list(vertex.link_faces)
        if any(len(f.verts)!=3 or f.material_index!=fs[0].material_index for f in fs):continue
        first=max(fs,key=lambda f:float(np.linalg.norm(np.cross(np.array(f.verts[1].co)-np.array(f.verts[0].co),np.array(f.verts[2].co)-np.array(f.verts[0].co)))))
        xyz=np.array([l.vert.co[:]for l in first.loops]);u=np.array([l[uv].uv[:]for l in first.loops]);axis=np.column_stack((xyz[1]-xyz[0],xyz[2]-xyz[0]));inverse=np.linalg.pinv(axis);normal=np.cross(axis[:,0],axis[:,1]);normal/=max(np.linalg.norm(normal),1e-30);valid=True
        for f in fs:
            for loop in f.loops:
                p=np.array(loop.vert.co);q=inverse@(p-xyz[0]);be=np.array([1-q.sum(),*q])
                if abs((p-xyz[0])@normal)>1.5e-7 or np.max(abs(be@u-np.array(loop[uv].uv)))>1e-6:valid=False;break
                names=set(loop.vert[deform].keys())|set(k for v in first.verts for k in v[deform].keys())
                if any(abs(sum(float(g)*v[deform].get(k,0.)for g,v in zip(be,first.verts))-loop.vert[deform].get(k,0.))>2e-6 for k in names):valid=False;break
            if not valid:break
        if not valid:continue
        result=bmesh.ops.dissolve_verts(bm,verts=[vertex],use_face_split=False,use_boundary_tear=False)
        bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3]);assert all(e.is_manifold for e in bm.edges)
        removed+=1
    bm.to_mesh(body.data);bm.free();body.data.update()
    print('AFFINE_SUPPORT_VERTICES_REMOVED',removed,flush=True)
    return dict(source_vertices=original,remaining_vertices=len(body.data.vertices),redundant_vertices_removed=removed,plane_tolerance_m=1.5e-7,UV_affinity_tolerance=1e-6,skin_affinity_tolerance=2e-6,scope='Only redundant planar chest one-rings; whole footprint reinserted afterward. Other fin roots protected.')

def main():
    args=sys.argv[sys.argv.index('--')+1:];src,out=map(lambda x:Path(x).resolve(),args[:2])
    assert not out.exists()and '/experiments/'in str(out)
    out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'))
    auth=json.loads((src/'fin-authoring.json').read_text());body=bpy.data.objects['Reference_head_body'];coalescence=coalesce_obsolete_support(body,auth)if '--coalesce' in args[2:]else {'enabled':False};old=body.data;old.calc_loop_triangles()
    bv=np.array([v.co[:]for v in old.vertices]);bt=[tuple(t.vertices)for t in old.loop_triangles];bw=weights(body);newv=bv.tolist();neww=list(bw)
    lookup={tuple(round(float(x),8)for x in p):i for i,p in enumerate(newv)}
    caps=[]
    for row in auth['fins']:
        if not row['name'].startswith('Pectoral_'):continue
        ob=bpy.data.objects[row['name']];m=ob.data;m.calc_loop_triangles();v=np.array([p.co[:]for p in m.vertices]);roots=set(row['root_ids']);ct=[tuple(t.vertices)for t in m.loop_triangles if all(i in roots for i in t.vertices)]
        projected=[v[list(t)][:,[0,2]]for t in ct]
        assert ct and all(abs(np.linalg.det(np.column_stack((t[1]-t[0],t[2]-t[0]))))>1e-13 for t in projected)
        edges=boundary(ct);caps.append(dict(row=row,ob=ob,m=m,v=v,roots=roots,ct=ct,projected=projected,edges=edges,side=np.sign(v[list(roots),1].mean()),selected=[],weights=weights(ob)))
    faces=[];body_uv=[];body_mats=[];body_smooth=[];touched=[];body_face_sources=[]
    for fi,ids in enumerate(bt):
        xyz=bv[list(ids)];xz=xyz[:,[0,2]];center=xyz.mean(0);owner=next((c for c in caps if center[1]*c['side']>0 and np.all(center[[0,2]]>=c['v'][list(c['roots'])][:,[0,2]].min(0)-.3)and np.all(center[[0,2]]<=c['v'][list(c['roots'])][:,[0,2]].max(0)+.3)),None)
        rawuv=[[np.array(layer.data[li].uv[:])for li in old.loop_triangles[fi].loops]for layer in old.uv_layers]
        material=old.polygons[old.loop_triangles[fi].polygon_index].material_index;smooth=old.polygons[old.loop_triangles[fi].polygon_index].use_smooth
        points=[np.array([0.,0.]),np.array([1.,0.]),np.array([0.,1.])];constraints=[]
        if owner and abs(np.linalg.det(np.column_stack((xz[1]-xz[0],xz[2]-xz[0]))))>1e-13:
            for ia,ib in owner['edges']:
                a,b=owner['v'][[ia,ib]][:,[0,2]];ba=bary2(a,xz);bb=bary2(b,xz);lo,hi=0.,1.
                for start,delta in zip(ba,bb-ba):
                    if abs(delta)<1e-14:
                        if start < -2e-7:lo,hi=1.,0.;break
                    elif delta>0:lo=max(lo,-start/delta)
                    else:hi=min(hi,-start/delta)
                if hi-lo<1e-8:continue
                pair=[]
                for t in [lo,hi]:
                    be=ba+(bb-ba)*float(np.clip(t,0,1));be[abs(be)<4e-7]=0;be=np.maximum(be,0);be/=be.sum();p=be[1:]
                    nearest=min(range(len(points)),key=lambda j:np.linalg.norm(points[j]-p))
                    if np.linalg.norm(points[nearest]-p)>6e-7:nearest=len(points);points.append(p)
                    pair.append(nearest)
                if pair[0]!=pair[1]:constraints.append(tuple(pair))
        local=[(0,1,2)]
        for j in range(3,len(points)):
            match=None
            for k,t in enumerate(local):
                be=bary2(points[j],np.array([points[i]for i in t]))
                if be.min()>-1e-8:match=(k,t,be);break
            assert match is not None,('Uninserted finite cap point',fi,j)
            k,t,be=match;near=np.where(abs(be)<1e-8)[0]
            assert len(near)<2,('Duplicate point',fi,j,be)
            if len(near)==1:
                edge=[t[i]for i in range(3)if i!=near[0]];split=[]
                for face in local:
                    if set(edge).issubset(face):
                        other=next(i for i in face if i not in edge);split.extend([(edge[0],j,other),(j,edge[1],other)])
                    else:split.append(face)
                local=split
            else:local.pop(k);local.extend([(t[0],t[1],j),(t[1],t[2],j),(t[2],t[0],j)])
        if constraints:local=constrain(local,constraints,points)
        indices=[]
        for j,p in enumerate(points):
            be=np.array([1-p.sum(),*p]);co=be@xyz;key=tuple(round(float(x),8)for x in co)
            if j<3:gi=ids[j]
            elif key in lookup:gi=lookup[key]
            else:
                gi=len(newv);lookup[key]=gi;newv.append(co.tolist());mix={}
                for i,gain in zip(ids,be):
                    for name,w in bw[i].items():mix[name]=mix.get(name,0.)+max(0.,float(gain))*w
                mix={name:w for name,w in mix.items()if w>1e-8};total=sum(mix.values());assert 0<len(mix)<=4
                neww.append({name:w/total for name,w in mix.items()})
            indices.append(gi)
        if len(points)>3:touched.append(fi)
        original_normal=np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0])
        for t in local:
            ix=tuple(indices[i]for i in t);q=np.array([newv[i]for i in ix]);n=np.cross(q[1]-q[0],q[2]-q[0])
            if np.linalg.norm(n)<1e-14:continue
            if n@original_normal<0:ix=ix[::-1];t=t[::-1]
            oi=len(faces);faces.append(ix);body_mats.append(material);body_smooth.append(smooth);body_face_sources.append(fi)
            body_uv.append([[sum((rawuv[k][h]*float([1-points[i].sum(),*points[i]][h])for h in range(3)),np.zeros(2))for i in t]for k in range(len(rawuv))])
            if owner and inside(q[:,[0,2]].mean(0),owner['projected']):owner['selected'].append(oi)
    me=bpy.data.meshes.new('Exact finite body with relocated chest patch boundary');me.from_pydata(newv,[],faces);me.update()
    for mat in old.materials:me.materials.append(mat)
    for p,mat,sm in zip(me.polygons,body_mats,body_smooth):p.material_index=mat;p.use_smooth=sm
    for k,layer in enumerate(old.uv_layers):
        dst=me.uv_layers.new(name=layer.name)
        for p,uvs in zip(me.polygons,body_uv):
            for li,u in zip(p.loop_indices,uvs[k]):dst.data[li].uv=u
    body.data=me;body.vertex_groups.clear()
    for i,mix in enumerate(neww):
        for name,w in mix.items():(body.vertex_groups.get(name)or body.vertex_groups.new(name=name)).add([i],w,'REPLACE')
    bm=bmesh.new();bm.from_mesh(me);bad=[e.index for e in bm.edges if not e.is_manifold];bm.free()
    assert not bad,('Body T-junction after finite clipping',bad[:10])
    records=[]
    for c in caps:
        ob=c['ob'];old=c['m'];v=c['v'];roots=c['roots'];capfaces=[faces[i]for i in c['selected']];assert capfaces
        old_area=sum(abs(np.cross(t[1]-t[0],t[2]-t[0]))for t in c['projected'])/2
        new_area=sum(abs(np.cross(np.array(newv[t[1]])[[0,2]]-np.array(newv[t[0]])[[0,2]],np.array(newv[t[2]])[[0,2]]-np.array(newv[t[0]])[[0,2]]))for t in capfaces)/2
        assert abs(new_area-old_area)<max(2e-9,old_area*2e-5),('Whole cap area mismatch',ob.name,old_area,new_area)
        positions=v.tolist();mixes=list(c['weights']);attributes={a.name:[float(d.value)for d in a.data]for a in old.attributes if a.domain=='POINT'and a.data_type=='FLOAT'}
        src_attrs={name:list(values)for name,values in attributes.items()};capverts=sorted(set(i for t in capfaces for i in t));mapping={};cap_lookup={tuple(round(float(x),8)for x in v[i]):i for i in roots}
        def source_bary(p):
            best=None
            for ids,t in zip(c['ct'],c['projected']):
                be=bary2(p[[0,2]],t);score=float(be.min())
                if best is None or score>best[0]:best=(score,ids,be)
                if score>-1e-7:break
            assert best[0]>-5e-5,('Cap point outside full footprint',ob.name,p,best[0]);be=np.maximum(best[2],0);be/=be.sum();return best[1],be
        for bi in capverts:
            p=np.array(newv[bi]);key=tuple(round(float(x),8)for x in p)
            near=min(roots,key=lambda i:np.linalg.norm(v[i]-p))
            if key in cap_lookup:gi=cap_lookup[key]
            elif np.linalg.norm(v[near]-p)<3e-6:gi=near;positions[gi]=p.tolist()
            else:
                gi=len(positions);positions.append(p.tolist());mixes.append({});ids,be=source_bary(p)
                for name,values in attributes.items():values.append(float(be@np.array([src_attrs[name][i]for i in ids])))
            mapping[bi]=gi;mixes[gi]=neww[bi]
        capboundary=boundary(capfaces);boundary_bids=set(i for e in capboundary for i in e);edge_splits={}
        for ia,ib in c['edges']:
            a,b=v[[ia,ib]][:,[0,2]];d=b-a;den=float(d@d);splits=[]
            for bi in boundary_bids:
                p=np.array(newv[bi])[[0,2]];t=float((p-a)@d/max(den,1e-30));distance=float(np.linalg.norm(p-a-np.clip(t,0,1)*d))
                if 1e-6<t<1-1e-6 and distance<8e-7:splits.append((t,mapping[bi]))
            edge_splits[(ia,ib)]=sorted(splits);edge_splits[(ib,ia)]=[(1-t,i)for t,i in reversed(sorted(splits))]
        newfaces=[];newuv=[];newmat=[];newsm=[];rootids=set(mapping.values())
        for tri in old.loop_triangles:
            ids=list(tri.vertices)
            if all(i in roots for i in ids):continue
            uv=[np.array(old.uv_layers.active.data[i].uv[:])for i in tri.loops];poly=[];pu=[]
            for j,(a,b)in enumerate(zip(ids,ids[1:]+ids[:1])):
                poly.append(a);pu.append(uv[j]);n=(j+1)%3
                for t,i in edge_splits.get((a,b),[]):poly.append(i);pu.append(uv[j]*(1-t)+uv[n]*t)
            if len(poly)>3:
                pivot=next(j for j,i in enumerate(poly)if i not in rootids);poly=poly[pivot:]+poly[:pivot];pu=pu[pivot:]+pu[:pivot]
            for j in range(1,len(poly)-1):
                newfaces.append((poly[0],poly[j],poly[j+1]));newuv.append([pu[0],pu[j],pu[j+1]]);newmat.append(tri.material_index);newsm.append(old.polygons[tri.polygon_index].use_smooth)
        for t in capfaces:
            ids=[mapping[i]for i in t[::-1]];newfaces.append(tuple(ids));newmat.append(0);newsm.append(True)
            image=next(n.image for n in old.materials[0].node_tree.nodes if n.type=='TEX_IMAGE');W,H=image.size
            newuv.append([np.array([(attributes['source_mask_x_px'][i]+.5)/W,1-(attributes['source_mask_y_px'][i]+.5)/H])for i in ids])
        used=sorted(set(i for f in newfaces for i in f));remap={i:j for j,i in enumerate(used)};removed_roots=sorted(roots-set(used));positions=[positions[i]for i in used];mixes=[mixes[i]for i in used];attributes={name:[values[i]for i in used]for name,values in attributes.items()};newfaces=[tuple(remap[i]for i in f)for f in newfaces];rootids={remap[i]for i in rootids};mapping={bi:remap[i]for bi,i in mapping.items()}
        fm=bpy.data.meshes.new('Chest full finite body-matched basal skin');fm.from_pydata(positions,[],newfaces);fm.update()
        for mat in old.materials:fm.materials.append(mat)
        for p,mat,sm in zip(fm.polygons,newmat,newsm):p.material_index=mat;p.use_smooth=sm
        uv=fm.uv_layers.new(name=old.uv_layers.active.name)
        for p,values in zip(fm.polygons,newuv):
            for li,u in zip(p.loop_indices,values):uv.data[li].uv=u
        for name,values in attributes.items():
            a=fm.attributes.new(name,'FLOAT','POINT')
            for x,value in zip(a.data,values):x.value=value
        ob.data=fm;ob.vertex_groups.clear()
        for i,mix in enumerate(mixes):
            for name,w in mix.items():(ob.vertex_groups.get(name)or ob.vertex_groups.new(name=name)).add([i],w,'REPLACE')
        bm=bmesh.new();bm.from_mesh(fm);bad=[dict(vertices=[list(v.co)for v in e.verts],faces=len(e.link_faces))for e in bm.edges if not e.is_manifold];volume=bm.calc_volume(signed=True);bm.free()
        if bad:save_json(out/(ob.name+'-topology-diagnostic.json'),bad)
        assert not bad and volume>0,(ob.name,'Nonmanifold or inverted replacement',len(bad),volume)
        c['row'].update(vertices=len(fm.vertices),triangles=len(newfaces),root_ids=sorted(rootids),root_points_native=[positions[i]for i in sorted(rootids)],finite_body_triangle_basal_patch=True)
        records.append(dict(name=ob.name,old_cap_triangles=len(c['ct']),new_cap_triangles=len(capfaces),old_projected_area_m2=float(old_area),new_projected_area_m2=float(new_area),complete_original_footprint_preserved=True,redundant_old_interior_root_vertices_removed=removed_roots,new_complete_root_vertices=sorted(rootids),body_triangle_indices=c['selected'],new_body_vertex_to_fin_vertex={str(k):v for k,v in mapping.items()},free_boundary_split_vertices=sum(len(v)for k,v in edge_splits.items())//2,non_root_original_vertices_unchanged=True,closed=True,volume_m3=volume))
    total=0
    for ob in bpy.context.scene.objects:
        if ob.type=='MESH':ob.data.calc_loop_triangles();total+=len(ob.data.loop_triangles)
    auth['whole_triangles']=total;auth['body_triangles']=len(body.data.loop_triangles)
    bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
    for ob in bpy.context.scene.objects:
        if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
    bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
    for name in ['body-color-mask.npz','attachment-authoring.validation.json','root-embedding.validation.json']:
        if(src/name).exists():shutil.copyfile(src/name,out/name)
    save_json(out/'fin-authoring.json',auth)
    save_json(out/'finite-cap-authoring.validation.json',dict(ok=True,kind='whole_pectoral_caps_use_exact_actual_body_triangles',input_sha256=hashlib.sha256((src/'fish.glb').read_bytes()).hexdigest(),model_sha256=hashlib.sha256((out/'fish.glb').read_bytes()).hexdigest(),redundant_support_coalescence=coalescence,touched_original_body_triangles=touched,added_body_vertices=len(newv)-len(bv),body_UV_and_skin_interpolated_on_original_finite_faces=True,body_surface_and_all_pixels_unchanged=True,whole_triangles=total,records=records,scope='Every complete chest cap face is an actual body triangle with exact same vertex skin weights and reverse orientation. Full footprint retained; boundary/free-fin triangles split consistently. Fresh pose, volume, budget and visual gates pending.',formal_acceptance=False))
    print('FINITE_PECTORAL_CAPS',src.parent.name,total,[(r['old_cap_triangles'],r['new_cap_triangles'])for r in records],flush=True)

if __name__=='__main__':main()
