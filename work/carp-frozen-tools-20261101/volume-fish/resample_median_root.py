"""Reallocate a median fin's basal stations to its actual finite body support.

Keeps every free source point and the complete original basal curve/domain.
Adds a peaked closing cap instead of deeply burying a wide flat root wall.
"""
import bpy,bmesh,numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
from fin_source_identity import OriginalFinSource
from volume_shape import fin_baseline_parameter


def resample(ob,fin,original_fin,body_vertices,aspect,W,H,settings):
    assert not fin['paired']and fin['root_depth']==fin['tip_depth']==0
    source=OriginalFinSource(ob,original_fin,aspect,W,H);old=ob.data;old.calc_loop_triangles();old_triangles=len(old.loop_triangles);base=np.array(fin['source_baseline']);assert np.all(np.diff(base[:,0])>0)
    xmin,xmax=base[0,0],base[-1,0];us=sorted([xmin,xmax,*base[:,0],*[v.x+.5 for v in body_vertices if xmin+1e-6<v.x+.5<xmax-1e-6]])
    unique=[]
    for u in us:
        if not unique or u-unique[-1]>1e-6:unique.append(float(u))
    baseline=[Vector((u,float(np.interp(u,base[:,0],base[:,1]))))for u in unique]
    original_polygon=[Vector(q)for q in fin['polygon']];original_boundary=list(original_polygon);removed=[]
    # Explicitly nominated redundant free-edge samples may fund the crest.
    # A strict subpixel deviation protects native tips/valleys and root domain.
    for i in sorted(settings.get('remove_collinear_outline_ids',[]),reverse=True):
        q=original_polygon[i];a=original_polygon[i-1];b=original_polygon[(i+1)%len(original_polygon)]
        aa=np.array(a)*[W,H];bb=np.array(b)*[W,H];qq=np.array(q)*[W,H];t=np.dot(qq-aa,bb-aa)/np.dot(bb-aa,bb-aa)
        error=float(np.linalg.norm(qq-aa-np.clip(t,0,1)*(bb-aa)))
        assert 0<t<1 and error<=.1 and fin_baseline_parameter(q,fin['source_baseline'],original_polygon,aspect)>fin['root_attachment']['root_band']
        removed.append({'original_polygon_id':i,'maximum_native_pixel_deviation':error});original_polygon.pop(i)
    root_ids=[]
    for i,q in enumerate(original_polygon):
        if fin_baseline_parameter(q,fin['source_baseline'],original_polygon,aspect)<1e-6:root_ids.append(i)
    if 0 in root_ids and len(original_polygon)-1 in root_ids:
        start=next(i for i in range(len(original_polygon))if i not in root_ids and(i-1)%len(original_polygon)in root_ids)
        original_polygon=original_polygon[start:]+original_polygon[:start]
        root_ids=[i for i,q in enumerate(original_polygon)if fin_baseline_parameter(q,fin['source_baseline'],original_polygon,aspect)<1e-6]
    # Both common polygon windings occur in native profiles. Replace the
    # complete contiguous basal chain in its original direction.
    if root_ids==list(range(root_ids[0],len(original_polygon))):
        polygon=original_polygon[:root_ids[0]]+list(reversed(baseline))
    elif root_ids==list(range(len(root_ids))):
        polygon=baseline+original_polygon[len(root_ids):]
    else:
        raise AssertionError('Basal source chain needs an explicit polygon mapping')
    extra=[]
    for q in source.points:
        if fin_baseline_parameter(Vector(q),fin['source_baseline'],original_polygon,aspect)>fin['root_attachment']['root_band']and all((Vector(q)-p).length>1e-7 for p in original_boundary):extra.append(Vector(q))
    points=polygon+extra;dv,_,df,*_=delaunay_2d_cdt(points,[(i,(i+1)%len(polygon))for i in range(len(polygon))],[list(range(len(polygon)))],1,1e-8);N=len(dv);coords=[];uvs=[];skin=[];ts=[];src=[]
    for layer in[0,1]:
        for q in dv:
            co,uv,weights=source.sample(q,layer);t=fin_baseline_parameter(q,fin['source_baseline'],original_polygon,aspect)
            if t<1e-6:co[0]=q.x-.5 # actual support station, no legacy inset X drift
            coords.append(co);uvs.append(uv);skin.append(weights);ts.append(t);src.append(q)
    index={tuple(round(v,7)for v in q):i for i,q in enumerate(dv)};boundary=[index[tuple(round(v,7)for v in q)]for q in polygon]
    faces=[tuple(f)for f in df]+[tuple(i+N for i in reversed(f))for f in df]+[(i,j,j+N,i+N)for i,j in zip(boundary,boundary[1:]+boundary[:1])]
    mesh=bpy.data.meshes.new(old.name+'_body_stations');mesh.from_pydata(coords,[],faces);mesh.update()
    for m in old.materials:mesh.materials.append(m)
    uv=mesh.uv_layers.new(name=old.uv_layers.active.name)
    for f in mesh.polygons:
        f.use_smooth=True
        for li in f.loop_indices:uv.data[li].uv=uvs[mesh.loops[li].vertex_index]
    for name,values in[('foundry_fin_source_t',ts),('foundry_fin_source_u',[q.x for q in src]),('foundry_fin_source_v',[q.y for q in src])]:
        attr=mesh.attributes.new(name,'FLOAT','POINT')
        for i,v in enumerate(values):attr.data[i].value=v
    ob.data=mesh
    for i,weights in enumerate(skin):
        total=sum(weights.values());assert total>0
        for bone,w in weights.items():
            if w>0:(ob.vertex_groups.get(bone)or ob.vertex_groups.new(name=bone)).add([i],w/total,'REPLACE')
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);bm.to_mesh(mesh);bm.free();mesh.calc_loop_triangles()
    return {'original_triangles':old_triangles,'before_crest_triangles':len(mesh.loop_triangles),'original_source_points':source.count,'new_source_points':N,'complete_baseline_stations':len(baseline),'full_original_baseline_curve_and_band_preserved':True,'free_outline_collinear_reallocation':removed,'every_other_free_source_outline_and_interior_point_retained':True,'original_source_point_identity_error':source.identity_error,'actual_original_UV_and_skin_transferred':True}


def add_crest(ob,fin,tree,scale,inset,skin_to_body):
    mesh=ob.data;uv=[[]for v in mesh.vertices]
    for loop,q in zip(mesh.loops,mesh.uv_layers.active.data):uv[loop.vertex_index].append(q.uv[:])
    groups={};ts=[x.value for x in mesh.attributes['foundry_fin_source_t'].data]
    for i,q in enumerate(uv):groups.setdefault(tuple(np.round(np.mean(q,axis=0),7)),[]).append(i)
    bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();old=list(bm.verts);new=[];direction=1 if fin['tip'][1]<fin['anchor'][1]else-1
    for ids in groups.values():
        if len(ids)!=2 or not all(ts[i]<1e-6 for i in ids):continue
        i,j=ids;edge=bm.edges.get((old[i],old[j]));assert edge,'Complete basal transverse closing edge missing'
        edge,vert=bmesh.utils.edge_split(edge,old[i],.5);hit,normal,face,_=tree.ray_cast(Vector((vert.co.x,0,direction*2)),Vector((0,0,-direction)),4);assert hit is not None and abs(normal.z)>.1
        vert.co=hit+Vector((0,0,-direction*inset/1000/scale/abs(normal.z)));new.append((vert,hit,face))
    assert new
    # Preserve the actual body crest as an edge. A generic triangulation of
    # the resulting six-sided wall can cut diagonally through the body ridge.
    crest_vertices={v for v,_,_ in new}
    for face in list(bm.faces):
        ridge=[v for v in face.verts if v in crest_vertices]
        if len(ridge)==2 and bm.edges.get(tuple(ridge))is None:
            bmesh.ops.connect_vert_pair(bm,verts=ridge)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.index_update();indices=[(v.index,h,f)for v,h,f in new];bm.to_mesh(mesh);bm.free()
    for i,hit,face in indices:skin_to_body(ob,i,hit,face)
    return {'added_crest_vertices':len(indices),'body_station_crest_support':True,'full_original_band_retained':True}
