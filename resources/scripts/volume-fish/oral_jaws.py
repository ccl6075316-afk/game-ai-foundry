"""Reusable closed oral cleft + lip bevel for longitudinal fish shells.

Creates actual oral roof/floor surfaces and asymmetric jaw tips. The shell stays
connected behind the commissure; no articulated jaw or muscles are claimed.
"""
import bpy,bmesh,math
from mathutils import Vector
from volume_mouth import validate_oral_jaws,slit_v,jaw_shift

def build_closed_oral_jaws(body,settings,aspect,weights,gap_profile=None,cut_profile=None):
    validate_oral_jaws(settings)
    corner,front=settings['corner'],settings['front']
    original=[v.co.copy() for v in body.data.vertices]
    # The anterior cap becomes nonplanar when upper and lower tips move apart.
    # Triangulate its original planar surface before shaping/cutting it.
    bm=bmesh.new();bm.from_mesh(body.data)
    if settings.get('lip_roll'):
        end_x=max(v.co.x for v in bm.verts)
        cap=[f for f in bm.faces if all(abs(v.co.x-end_x)<1e-7 for v in f.verts)]
        if cap:
            # A long perimeter fan wrinkles when two jaw tips diverge. Give the
            # cap an interior lattice before shaping; interpolate existing UVs.
            region=bmesh.ops.dissolve_faces(bm,faces=cap,use_verts=False)['region']
            caps=[f for f in region if isinstance(f,bmesh.types.BMFace)]
            triangles=bmesh.ops.poke(bm,faces=caps)['faces']
            edges=list({e for f in triangles for e in f.edges})
            bmesh.ops.subdivide_edges(bm,edges=edges,cuts=3,use_grid_fill=True)
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>4])
    bm.to_mesh(body.data);bm.free()
    moved=0
    for vertex in body.data.vertices:
        u=vertex.co.x+.5;v=.5-vertex.co.z/aspect
        shift=jaw_shift(settings,u,v)
        if shift:
            vertex.co.x+=shift;moved+=1
    body.data.update()
    start=corner[0]
    roll_metrics=None
    if settings.get('lip_roll'):
        roll=settings['lip_roll'];bm=bmesh.new();bm.from_mesh(body.data);bm.normal_update()
        changed=0;maximum=0.;offsets=[]
        for vertex in bm.verts:
            skin=list(vertex.link_faces)
            if not skin:continue
            u=vertex.co.x+.5
            if u<start or u>front[0]+settings['lower_projection']+.015:continue
            z=(.5-slit_v(settings,u))*aspect
            slope=(slit_v(settings,u+.0001)-slit_v(settings,u-.0001))*aspect/.0002
            distance=(vertex.co.z-z)/math.sqrt(1+slope*slope)
            if abs(distance)>=roll['radius']:continue
            # Smooth fade at the commissure; only a band at the actual lip
            # boundary inflates. The jaw/chin outside that band stays unchanged.
            t=max(0.,min(1.,(u-start)/.018));fade=t*t*(3-2*t)
            amount=roll['height']*(1+(roll['lower_ratio']-1)*(.5-.5*math.tanh(distance/(roll['radius']*.25))))*.5*(1+math.cos(math.pi*distance/roll['radius']))*fade
            normal=sum((f.normal*f.calc_area() for f in skin),Vector())
            # Anterior-cap normals point lengthwise; displacing them can fold
            # their fan across neighboring rings. Inflate the lip cross-section
            # here; longitudinal coverage is controlled by the jaw projection.
            normal.x=0
            if normal.length<1e-10:continue
            offsets.append((vertex,normal.normalized()*amount))
            changed+=1;maximum=max(maximum,amount)
        for vertex,offset in offsets:vertex.co+=offset
        bm.to_mesh(body.data);bm.free()
        roll_metrics={'changed_vertices':changed,'maximum_offset_native':maximum,**roll}
        bm=bmesh.new();bm.from_mesh(body.data)
        bmesh.ops.triangulate(bm,faces=list(bm.faces))
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
    body.data.update()
    bm=bmesh.new();bm.from_mesh(body.data)
    pre_cut={'vertices':len(bm.verts),'faces':len(bm.faces),'volume':bm.calc_volume(signed=True),'nonmanifold':sum(not e.is_manifold for e in bm.edges)};bm.free()
    inner=bpy.data.materials.new('Oral cavity - actual inner surface')
    inner.use_nodes=True
    bsdf=next(n for n in inner.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value=(.025,.018,.012,1)
    bsdf.inputs['Roughness'].default_value=1;bsdf.inputs['Metallic'].default_value=0;bsdf.inputs['Specular IOR Level'].default_value=0
    inner.diffuse_color=(.025,.018,.012,1)
    body.data.materials.append(inner)
    start=corner[0];end=front[0]+.012 if 'bill_tip_u'in settings else max(v.co.x+.5 for v in body.data.vertices)+.04
    half_width=max(abs(v.co.y) for v in body.data.vertices)+.02
    points=[]
    if settings.get('slit_path'):
        candidates=sorted([start,end]+[p[0] for p in settings['slit_path']]+[start+(front[0]-start)*i/64 for i in range(65)])
        samples=[]
        for u in candidates:
            if not samples or u-samples[-1]>1e-7:samples.append(u)
    else:samples=[start,end]
    if gap_profile:
        assert len(gap_profile)>=2 and all(b[0]>a[0] for a,b in zip(gap_profile,gap_profile[1:]))
        assert all(math.isfinite(u) and math.isfinite(g) and g>0 for u,g in gap_profile)
        samples=sorted(set(samples+[u for u,g in gap_profile if start<u<end]))
    if cut_profile:
        assert not gap_profile and len(cut_profile)>=2
        assert all(b[0]>a[0] for a,b in zip(cut_profile,cut_profile[1:]))
        assert all(all(math.isfinite(x) for x in r) and r[2]>r[1] for r in cut_profile)
        samples=sorted(set([start,end]+[r[0] for r in cut_profile if start<r[0]<end]))
    def cut_at(u):
        if not cut_profile:
            z=(.5-slit_v(settings,u))*aspect
            return [z-gap_at(u)/2,z+gap_at(u)/2]
        if u<=cut_profile[0][0]:return cut_profile[0][1:]
        for a,b in zip(cut_profile,cut_profile[1:]):
            if u<=b[0]:
                t=(u-a[0])/(b[0]-a[0]);return [a[k]+(b[k]-a[k])*t for k in [1,2]]
        return cut_profile[-1][1:]
    def gap_at(u):
        if not gap_profile:return settings['gap']
        if u<=gap_profile[0][0]:return gap_profile[0][1]
        for a,b in zip(gap_profile,gap_profile[1:]):
            if u<=b[0]:return a[1]+(b[1]-a[1])*(u-a[0])/(b[0]-a[0])
        return gap_profile[-1][1]
    arch=settings.get('transverse_gap_arch')
    if arch:
        # Measure each ORIGINAL shell entry at its own upper/lower source
        # height. The arch is zero at that side entry, expanding only the
        # cavity's hidden transverse center; do not move eyes/head widths.
        from mathutils.bvhtree import BVHTree
        body.data.calc_loop_triangles()
        tree=BVHTree.FromPolygons([v.co for v in body.data.vertices],
             [tuple(t.vertices)for t in body.data.loop_triangles],all_triangles=True)
        max_u=max(v.co.x+.5 for v in body.data.vertices)
        fractions=[-2,-1,-.5,0,.5,1,2];ny=len(fractions)
        def shell_entry_width(u,z):
            hit=tree.ray_cast(Vector((min(u,max_u-1e-6)-.5,-half_width,z)),Vector((0,1,0)),2*half_width)[0]
            if hit is None:raise ValueError('Transverse mouth source boundary lies outside the actual shell')
            return abs(hit.y)
        for u in samples:
            levels=cut_at(u)
            widths=[shell_entry_width(u,z)for z in levels]
            for f in fractions:
                for level,(z,w)in enumerate(zip(levels,widths)):
                    y=math.copysign(half_width,f)if abs(f)>1 else f*w
                    amount=max(0,1-f*f)**2
                    delta=(-arch['lower']if level==0 else arch['upper'])*amount
                    points.append((u-.5,y,z+delta))
        idx=lambda i,j,k:i*ny*2+j*2+k
        faces=[]
        for i in range(len(samples)-1):
            for j in range(ny-1):
                for k in [0,1]:faces.append((idx(i,j,k),idx(i+1,j,k),idx(i+1,j+1,k),idx(i,j+1,k)))
            for j in [0,ny-1]:faces.append((idx(i,j,0),idx(i,j,1),idx(i+1,j,1),idx(i+1,j,0)))
        for i in [0,len(samples)-1]:
            for j in range(ny-1):faces.append((idx(i,j,0),idx(i,j+1,0),idx(i,j+1,1),idx(i,j,1)))
    else:
        for u in samples:
            for y in [-half_width,half_width]:
                for z in cut_at(u):points.append((u-.5,y,z))
        last=(len(samples)-1)*4
        faces=[(0,1,3,2),(last,last+2,last+3,last+1)]
        for i in range(len(samples)-1):
            a=i*4;b=a+4
            faces.extend([(a,b,b+1,a+1),(a+2,a+3,b+3,b+2),(a,a+2,b+2,b),(a+1,b+1,b+3,a+3)])
    mesh=bpy.data.meshes.new('Oral cleft cutter');mesh.from_pydata(points,[],faces);mesh.materials.append(inner)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    cutter=bpy.data.objects.new('Oral cleft temporary volume',mesh);bpy.context.scene.collection.objects.link(cutter)
    bpy.context.view_layer.objects.active=body;body.select_set(True)
    solver=settings.get('boolean_solver','MANIFOLD' if settings.get('slit_path') else 'EXACT')
    modifier=body.modifiers.new('Real oral roof and floor','BOOLEAN');modifier.operation='DIFFERENCE';modifier.solver=solver;modifier.object=cutter
    if hasattr(modifier,'material_mode'):modifier.material_mode='TRANSFER'
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    cap_metrics=None
    if settings.get('anterior_cap_rounding'):
        # Replace both existing cut-cap patches. Pull their entire support back
        # first, then rebuild a shallow two-ring curved surface WITHIN the old
        # maximum X. This is not a spike appended ahead of the old plane.
        cap=settings['anterior_cap_rounding'];bm=bmesh.new();bm.from_mesh(body.data);bm.normal_update()
        end_x=max(v.co.x for v in bm.verts);layer=bm.loops.layers.uv.active
        selected={f for f in bm.faces if f.material_index==0 and all(abs(v.co.x-end_x)<1e-7 for v in f.verts)}
        if not selected:raise ValueError('No existing anterior skin cap to replace')
        pending=set(selected);patches=[]
        while pending:
            seed=pending.pop();group={seed};stack=[seed]
            while stack:
                face=stack.pop()
                for e in face.edges:
                    for other in e.link_faces:
                        if other in pending:pending.remove(other);group.add(other);stack.append(other)
            edges={e for f in group for e in f.edges};boundary=[e for e in edges if sum(f in group for f in e.link_faces)==1]
            adjacent={}
            for e in boundary:
                a0,a1=e.verts;adjacent.setdefault(a0,[]).append(a1);adjacent.setdefault(a1,[]).append(a0)
            if not adjacent or any(len(ns)!=2 for ns in adjacent.values()):raise ValueError('Anterior cap has no simple closed boundary')
            first=next(iter(adjacent));loop=[first];previous=None;v=first
            while True:
                nxt=next(q for q in adjacent[v]if q!=previous)
                if nxt==first:break
                loop.append(nxt);previous,v=v,nxt
                if len(loop)>len(adjacent):raise ValueError('Anterior cap boundary folded')
            if len(loop)!=len(adjacent):raise ValueError('Anterior cap has multiple boundary cycles')
            values={l.vert:l[layer].uv.copy()for f in group for l in f.loops}
            patches.append((loop,values))
        before_cap_faces=len(selected);before_extent=end_x
        for v in bm.verts:
            t=max(0,min(1,(v.co.x-(end_x-cap['support']))/cap['support']))
            v.co.x-=cap['depth']*t*t*(3-2*t)
        internal={e for f in selected for e in f.edges if all(q in selected for q in e.link_faces)}
        for f in selected:bm.faces.remove(f)
        for e in internal:
            if e.is_valid and not e.link_faces:bm.edges.remove(e)
        new_faces=0
        for loop,values in patches:
            center=sum((v.co for v in loop),Vector())/len(loop);center.x=end_x
            uv_center=sum((values[v]for v in loop),values[loop[0]]*0)/len(loop)
            middle=[];uvs=dict(values)
            for v in loop:
                co=center+(v.co-center)*.5;co.x=end_x-cap['depth']*.25
                q=bm.verts.new(co);middle.append(q);uvs[q]=uv_center+(values[v]-uv_center)*.5
            tip=bm.verts.new(center);uvs[tip]=uv_center
            for i in range(len(loop)):
                j=(i+1)%len(loop)
                for verts in [(loop[i],loop[j],middle[j],middle[i]),(middle[i],middle[j],tip)]:
                    face=bm.faces.new(verts);face.material_index=0;face.smooth=True
                    for l in face.loops:l[layer].uv=uvs[l.vert]
                    new_faces+=1
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
        maximum=max(v.co.x for v in body.data.vertices)
        if maximum>before_extent+1e-7:raise ValueError('Rounded cap protruded beyond original fish envelope')
        cap_metrics={'patches':len(patches),'removed_cap_faces':before_cap_faces,'new_cap_faces':new_faces,
            'depth_native':cap['depth'],'support_native':cap['support'],'max_anterior_extent_delta':maximum-before_extent,
            'method':'Existing cap removed, anterior support pulled back, two-ring shallow curved patches rebuilt within old maximum X; no appended anterior spike.'}
    oral_indices={i for i,m in enumerate(body.data.materials) if m==inner}
    bm=bmesh.new();bm.from_mesh(body.data);bm.edges.ensure_lookup_table()
    border=[edge.index for edge in bm.edges if any(f.material_index in oral_indices for f in edge.link_faces) and any(f.material_index not in oral_indices for f in edge.link_faces)]
    bm.free()
    if settings['lip_bevel'] and border:
        attr=body.data.attributes.get('bevel_weight_edge') or body.data.attributes.new('bevel_weight_edge','FLOAT','EDGE')
        for i in border:attr.data[i].value=1
        modifier=body.modifiers.new('Rounded upper and lower lip margins','BEVEL');modifier.limit_method='WEIGHT';modifier.width=settings['lip_bevel'];modifier.segments=3
        modifier.use_clamp_overlap=True
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    # Lip bevel endpoints can create microscopic coincident wedges at the oral
    # corner. Weld below export precision, then dissolve zero-length edges.
    bm=bmesh.new();bm.from_mesh(body.data)
    if settings.get('slit_path') or settings.get('lip_roll'):bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
    if settings.get('slit_path') or settings.get('lip_roll'):
        for edge in bm.edges:
            if any(f.material_index in oral_indices for f in edge.link_faces) and any(f.material_index not in oral_indices for f in edge.link_faces):edge.smooth=False
        for face in bm.faces:face.smooth=face.material_index not in oral_indices
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
    # Boolean/bevel creates vertices. Pin all generated points to the same body
    # chain field instead of trusting interpolated or cutter vertex groups.
    body.vertex_groups.clear()
    for vertex in body.data.vertices:
        for name,value in weights(vertex.co.x+.5).items():
            (body.vertex_groups.get(name) or body.vertex_groups.new(name=name)).add([vertex.index],value,'REPLACE')
    body.select_set(False);body.data.update()
    oral_faces=sum(p.material_index in oral_indices for p in body.data.polygons)
    if not oral_faces or not border:raise ValueError(f'Oral cavity did not intersect shell at a verifiable lip boundary (faces={len(body.data.polygons)}, oral={oral_faces}, boundary={len(border)}, before={pre_cut})')
    return {'method':'Connected shell with real oral cleft, roof/floor and asymmetric jaw tips; optional curved path, local lip volume and lip-edge bevel. Static mouth simplification.',
            'corner_source_uv':corner,'front_source_uv':front,'gap_native_units':settings['gap'],
            'upper_retraction_native_units':settings['upper_retraction'],'lower_projection_native_units':settings['lower_projection'],
            'lip_bevel_native_units':settings['lip_bevel'],'moved_shell_vertices':moved,'oral_faces':oral_faces,'lip_border_edges_before_bevel':len(border),
            'slit_path':settings.get('slit_path'),'lip_roll':roll_metrics,'gap_profile':gap_profile,'cut_profile':cut_profile,'transverse_gap_arch':arch,'anterior_cap_rounding':cap_metrics,
            'pre_cut':pre_cut,'boolean_solver':solver,
            'original_body_vertices':len(original),'final_body_vertices':len(body.data.vertices),'articulated_jaw':False}
