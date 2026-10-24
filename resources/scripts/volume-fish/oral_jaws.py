"""Reusable closed oral cleft + lip bevel for longitudinal fish shells.

Creates actual oral roof/floor surfaces and asymmetric jaw tips. The shell stays
connected behind the commissure; no articulated jaw or muscles are claimed.
"""
import bpy,bmesh,math
from mathutils import Vector
from volume_mouth import validate_oral_jaws,slit_v,jaw_shift

def build_closed_oral_jaws(body,settings,aspect,weights):
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
    for u in samples:
        for y in [-half_width,half_width]:
            for sign in [-1,1]:
                points.append((u-.5,y,(.5-slit_v(settings,u))*aspect+sign*settings['gap']/2))
    last=(len(samples)-1)*4
    faces=[(0,1,3,2),(last,last+2,last+3,last+1)]
    for i in range(len(samples)-1):
        a=i*4;b=a+4
        faces.extend([(a,b,b+1,a+1),(a+2,a+3,b+3,b+2),(a,a+2,b+2,b),(a+1,b+1,b+3,a+3)])
    mesh=bpy.data.meshes.new('Oral cleft cutter');mesh.from_pydata(points,[],faces);mesh.materials.append(inner)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    cutter=bpy.data.objects.new('Oral cleft temporary volume',mesh);bpy.context.scene.collection.objects.link(cutter)
    bpy.context.view_layer.objects.active=body;body.select_set(True)
    modifier=body.modifiers.new('Real oral roof and floor','BOOLEAN');modifier.operation='DIFFERENCE';modifier.solver='MANIFOLD' if settings.get('slit_path') else 'EXACT';modifier.object=cutter
    if hasattr(modifier,'material_mode'):modifier.material_mode='TRANSFER'
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
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
            'slit_path':settings.get('slit_path'),'lip_roll':roll_metrics,
            'pre_cut':pre_cut,'boolean_solver':'MANIFOLD' if settings.get('slit_path') else 'EXACT',
            'original_body_vertices':len(original),'final_body_vertices':len(body.data.vertices),'articulated_jaw':False}
