"""Source tail shell with explicit, finite body-section support.

Reallocates sampling from redundant interior points to the complete basal curve.
The native free outline/UV and existing rig are inputs, never a generated front.
Blender module; no runtime geometry patches.
"""
import math
import bpy,bmesh,numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
from volume_shape import fin_baseline_parameter
from build_fish import fin_source_geometry


def rebuild(ob,fin,cap_vertices,root_x,zmid,aspect,W,H,scale,settings,overlap,skin_to_body,tree,original_fin=None):
    old=ob.data;old.calc_loop_triangles();old_count=len(old.loop_triangles)
    original_fin=original_fin or fin
    assert not fin['paired']and fin.get('vertical_scale',1)==1 and fin['root_depth']==fin['tip_depth']==0,'Explicit native XZ caudal branch only'
    opoly,opoints=fin_source_geometry(original_fin,aspect)
    odv,_,odf,*_=delaunay_2d_cdt(opoints,[(i,(i+1)%len(opoly))for i in range(len(opoly))],[list(range(len(opoly)))],1,1e-7)
    ON=len(odv);assert len(old.vertices)==2*ON,'Original source point inventory differs; explicit remapping required'
    old_ts=old.attributes['foundry_fin_source_t'];identity_error=max(abs(fin_baseline_parameter(q,original_fin['source_baseline'],opoly,aspect)-old_ts.data[i].value)for i,q in enumerate(odv));assert identity_error<1e-5,'Original source point identity differs'
    old_uv=[None]*len(old.vertices)
    for l,v in zip(old.loops,old.uv_layers.active.data):old_uv[l.vertex_index]=np.array(v.uv)
    old_weights=[{ob.vertex_groups[g.group].name:g.weight for g in v.groups}for v in old.vertices]
    def original_mapping(q):
        errors=[float(np.linalg.norm((np.array(v)-np.array(q))*[W,H]))for v in odv];nearest=int(np.argmin(errors))
        if errors[nearest]<.001:return (nearest,),np.array([1.])
        for ids in odf:
            aa,bb,cc=[np.array(odv[j])for j in ids];matrix=np.column_stack((bb-aa,cc-aa))
            if abs(np.linalg.det(matrix))<1e-12:continue
            bc=np.linalg.solve(matrix,np.array(q)-aa);weights=np.r_[1-bc.sum(),bc]
            if min(weights)>=-1e-5:
                weights=np.maximum(weights,0);return tuple(ids),weights/weights.sum()
        raise AssertionError('New source point outside original geometric source domain')
    polygon=[Vector(q)for q in fin['polygon']]
    removed=[]
    # A case must explicitly nominate an almost collinear source point. Never
    # silently simplify a new species to squeeze it under the triangle budget.
    for i in sorted(settings.get('remove_collinear_outline_ids',[]),reverse=True):
        a,b,c=polygon[i-1],polygon[i],polygon[(i+1)%len(polygon)]
        aa,bb,cc=[np.asarray(v)*[W,H]for v in (a,b,c)]
        t=np.clip(np.dot(bb-aa,cc-aa)/np.dot(cc-aa,cc-aa),0,1)
        error=float(np.linalg.norm(bb-(aa+t*(cc-aa))));assert error<=.1,(ob.name,i,error)
        removed.append({'source_polygon_id':i,'deviation_source_px':error});polygon.pop(i)
    top=max(q.z for q in cap_vertices);bottom=min(q.z for q in cap_vertices)
    fractions=sorted(set(round((q.z-bottom)/(top-bottom),6)for q in cap_vertices))
    assert len(fractions)>=5
    a,b=map(Vector,fin['source_baseline']);assert abs(a.x-b.x)<1e-7
    # The source baseline runs bottom -> top. Match every height knot of the
    # actual finite body section, rather than inscribing an unrelated polygon.
    mids=[a.lerp(b,q)for q in fractions[1:-1]]
    for i in range(len(polygon)):
        l,r=polygon[i],polygon[(i+1)%len(polygon)]
        if (l-a).length<1e-7 and(r-b).length<1e-7:
            polygon=polygon[:i+1]+mids+polygon[i+1:];break
        if (l-b).length<1e-7 and(r-a).length<1e-7:
            polygon=polygon[:i+1]+list(reversed(mids))+polygon[i+1:];break
    else:raise AssertionError('Explicit complete boundary baseline required')
    dv,de,df,*_=delaunay_2d_cdt(polygon,[(i,(i+1)%len(polygon))for i in range(len(polygon))],[list(range(len(polygon)))],1,1e-8)
    assert len(dv)==len(polygon),'Unexpected CDT point loss/intersection'
    # Actual faceted section widths, not an analytic ellipse or its AABB.
    heights=sorted(set(round(q.z,8)for q in cap_vertices))
    widths=[max(abs(v.y)for v in cap_vertices if abs(v.z-z)<1e-7)for z in heights]
    N=len(dv);coords=[];uvs=[];ts=[];transfers=[]
    # Match build_fish's float32 Vector rounding before floor/ceil. Repeating
    # the normalized JSON calculation in float64 shifts integer pixel bounds
    # by one pixel for some sources, corrupting UV and barycentric identities.
    poly=np.array([Vector(q)for q in fin['polygon']]);left=max(0,math.floor(poly[:,0].min()*W)-2);right=min(W,math.ceil(poly[:,0].max()*W)+2);up=max(0,math.floor(poly[:,1].min()*H)-2);down=min(H,math.ceil(poly[:,1].max()*H)+2)
    image=next(n.image for n in old.materials[0].node_tree.nodes if n.type=='TEX_IMAGE');assert list(image.size)==[right-left,down-up],(ob.name,'Native crop bounds differ',list(image.size),[left,up,right,down])
    layer_sign=1 if np.median([old.vertices[i].co.y-old.vertices[i+ON].co.y for i in range(ON)])>0 else-1
    for layer,sign in enumerate([layer_sign,-layer_sign]):
        for q in dv:
            t=fin_baseline_parameter(q,fin['source_baseline'],fin['polygon'],aspect)
            root=abs(q.x-a.x)<1e-6 and min(a.y,b.y)-1e-6<=q.y<=max(a.y,b.y)+1e-6
            z=(.5-q.y)*aspect;u=q.x
            if root:
                v=(a.y-q.y)/(a.y-b.y);z=bottom+v*(top-bottom);u=root_x+.5
            s=max(0,min(1,(root_x+.5-u)/settings['taper_length_u']))
            edge=settings['edge_mm']/2000/scale
            h=max(edge,float(np.interp(z,heights,widths)))
            h=h+(edge-h)*(s*s*(3-2*s))
            # End knots are deliberately finite (.25mm total edge), avoiding
            # a collapsed two-sided shell while covering the body cap tips.
            x=u-.5+overlap/1000/scale*(1-s)**2
            ids,weights=original_mapping(q);ids=tuple(i+layer*ON for i in ids)
            # Geometry source domain and texture UV are distinct. Keep the
            # actual original UV mapping, including reviewed half-texel/opaque
            # edge adjustments, and transfer skin through source identities.
            coords.append((x,sign*h,z));uvs.append(sum((old_uv[i]*w for i,w in zip(ids,weights)),np.zeros(2)));ts.append(t);transfers.append((ids,weights))
    faces=[tuple(reversed(f))for f in df]+[tuple(i+N for i in f)for f in df]
    # CDT indices are not assumed to preserve the input perimeter order.
    index={tuple(round(v,7)for v in q):i for i,q in enumerate(dv)}
    boundary=[index[tuple(round(v,7)for v in q)]for q in polygon]
    faces +=[(i,j,j+N,i+N)for i,j in zip(boundary,boundary[1:]+boundary[:1])]
    mesh=bpy.data.meshes.new(old.name+'_matched_section');mesh.from_pydata(coords,[],faces);mesh.update()
    for m in old.materials:mesh.materials.append(m)
    uv=mesh.uv_layers.new(name=old.uv_layers.active.name)
    for f in mesh.polygons:
        f.use_smooth=True
        for li in f.loop_indices:uv.data[li].uv=uvs[mesh.loops[li].vertex_index]
    attr=mesh.attributes.new('foundry_fin_source_t','FLOAT','POINT')
    for i,t in enumerate(ts):attr.data[i].value=t
    # Entire original anatomical band, with new complete section support.
    ob.data=mesh
    for i,p in enumerate(coords):
        if ts[i]<=fin['root_attachment']['root_band']+1e-7:
            hit,normal,face,_=tree.find_nearest(Vector(p));skin_to_body(ob,i,hit,face)
        else:
            mix={}
            for j,w in zip(*transfers[i]):
                for bone,value in old_weights[j].items():mix[bone]=mix.get(bone,0)+max(0,w)*value
            total=sum(mix.values());assert total>0
            for bone,w in mix.items():
                if w>0:(ob.vertex_groups.get(bone)or ob.vertex_groups.new(name=bone)).add([i],w/total,'REPLACE')
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);bm.to_mesh(mesh);bm.free();mesh.calc_loop_triangles()
    return {'old_triangles':old_count,'new_triangles':len(mesh.loop_triangles),'complete_body_section_knots':len(fractions),'reallocated_interior_samples':True,'outline_removed':removed,'free_outline_native_UV_preserved_except_reported_subpixel_point':True,'native_crop_bounds_top_left':[left,up,right,down],'original_source_point_identity_error':identity_error,'original_source_points':ON,'geometry_domain_is_not_UV_domain':True,'actual_original_UV_and_skin_transferred':True}


def junction_normals(body,tail,root_x):
    """Exclude the buried end caps from flank normals and match the root tangents."""
    def normals(ob,selector):
        mesh=ob.data;mesh.update();sums=[Vector()for _ in mesh.vertices]
        for f in mesh.polygons:
            if selector(f):
                for vi in f.vertices:sums[vi]+=f.normal*f.area
        return [q.normalized()if q.length>1e-12 else mesh.vertices[i].normal.copy()for i,q in enumerate(sums)]
    bn=normals(body,lambda f:not all(abs(body.data.vertices[i].co.x-root_x)<1e-6 for i in f.vertices))
    original=[n.vector.copy()for n in body.data.corner_normals]
    body.data.normals_split_custom_set([f.normal if all(abs(body.data.vertices[i].co.x-root_x)<1e-6 for i in f.vertices)else(bn[body.data.loops[li].vertex_index]if abs(body.data.vertices[body.data.loops[li].vertex_index].co.x-root_x)<1e-6 else original[li])for f in body.data.polygons for li in f.loop_indices])
    tn=normals(tail,lambda f:len({tail.data.vertices[i].co.y>0 for i in f.vertices})==1)
    caps=[v for v in body.data.vertices if abs(v.co.x-root_x)<1e-6]
    ts=tail.data.attributes['foundry_fin_source_t']
    for v in tail.data.vertices:
        if ts.data[v.index].value<1e-7:
            near=min(caps,key=lambda q:(q.co-v.co).length);tn[v.index]=bn[near.index]
    tail.data.normals_split_custom_set([tn[li.vertex_index]for li in tail.data.loops])
    return {'body_cap_excluded_from_flank_normals':True,'tail_root_uses_matching_body_flank_normal':True,'source_custom_normals':True,'body_normal_changes_limited_to_posterior_ring':True}
