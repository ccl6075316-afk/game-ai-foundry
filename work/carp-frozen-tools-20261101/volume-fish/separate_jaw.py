"""Trim old lower shell; create an independently editable, closed cupped jaw."""
import bpy,bmesh,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from volume_mouth import slit_v,jaw_shift,validate_oral_jaws

def finish(obj,weights):
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if not all(e.is_manifold for e in bm.edges):raise ValueError('Separate oral part is not manifold: '+obj.name)
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    obj.vertex_groups.clear()
    for vertex in obj.data.vertices:
        for name,value in weights(vertex.co.x+.5).items():
            (obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)).add([vertex.index],value,'REPLACE')

def build_separate_lower_jaw(body,settings,cap,aspect,weights,vertical_offset,body_section=None,side_patches=None):
    validate_oral_jaws(settings);lower=settings['separate_lower'];start=settings['corner'][0]
    original_vertices=len(body.data.vertices)
    # Triangulate the original planar cap before the upper jaw retreats.
    bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free()
    for vertex in body.data.vertices:
        u=vertex.co.x+.5;v=.5-vertex.co.z/aspect
        vertex.co.x+=jaw_shift(settings,u,v)
    body.data.update()
    inner=bpy.data.materials.new('Oral interior - matte');inner.use_nodes=True
    bsdf=next(n for n in inner.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value=(.035,.024,.014,1);bsdf.inputs['Roughness'].default_value=1
    bsdf.inputs['Metallic'].default_value=0;bsdf.inputs['Specular IOR Level'].default_value=0
    inner.diffuse_color=(.035,.024,.014,1);body.data.materials.append(inner)
    end=max(v.co.x+.5 for v in body.data.vertices)+.05
    samples=sorted(set([start,end]+[start+(settings['front'][0]-start)*i/48 for i in range(49)]+[p[0] for p in settings.get('slit_path',[])]))
    unique=[]
    for u in samples:
        if not unique or u-unique[-1]>1e-7:unique.append(u)
    width=max(abs(v.co.y) for v in body.data.vertices)+.05
    verts=[]
    for u in unique:
        for y in [-width,width]:
            verts.extend([(u-.5,y,-.5),(u-.5,y,(.5-slit_v(settings,u))*aspect+settings['gap']/2)])
    last=(len(unique)-1)*4;faces=[(0,1,3,2),(last,last+2,last+3,last+1)]
    for i in range(len(unique)-1):
        a=i*4;b=a+4;faces.extend([(a,b,b+1,a+1),(a+2,a+3,b+3,b+2),(a,a+2,b+2,b),(a+1,b+1,b+3,a+3)])
    data=bpy.data.meshes.new('Old lower-jaw removal');data.from_pydata(verts,[],faces);data.materials.append(inner)
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    cutter=bpy.data.objects.new('Temporary lower-shell removal',data);bpy.context.scene.collection.objects.link(cutter)
    bpy.context.view_layer.objects.active=body;body.select_set(True)
    mod=body.modifiers.new('Remove old lower snout volume','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='MANIFOLD';mod.object=cutter;mod.material_mode='TRANSFER'
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True);body.select_set(False)
    finish(body,weights)
    # Add a local upper lip roll without beveling the tiny Boolean triangles.
    rounding=settings.get('upper_lip_rounding',0)
    if rounding:
        for vertex in body.data.vertices:
            u=vertex.co.x+.5
            if u<=start:continue
            floor=(.5-slit_v(settings,u))*aspect+settings['gap']/2
            height=vertex.co.z-floor
            if height<0 or height>rounding*8:continue
            fade=max(0,min(1,(u-start)/.025));fade=fade*fade*(3-2*fade)
            swell=rounding*math.exp(-((height-rounding*2)/(rounding*2.5))**2)*fade
            vertex.co.z+=swell*.7
            vertex.co.y+=math.copysign(swell*.7,vertex.co.y) if abs(vertex.co.y)>.008 else 0
        finish(body,weights)
    if lower.get('reference_shape'):
        from reference_jaw import build_reference_jaw
        jaw,metrics=build_reference_jaw(body,settings,aspect,weights,body_section,side_patches or [])
        metrics.update(original_body_vertices=original_vertices,upper_body_vertices=len(body.data.vertices),removed_original_lower_shell=True)
        return jaw,metrics
    # A radial lattice gives a smooth solid plate without a large warped fan.
    rear,front=lower['rear_u'],lower['front_u'];cx=(rear+front)/2;rx=(front-rear)/2;ry=lower['half_width'];power=lower['planform_power']
    sections=lower.get('lip_sections')
    lower_curve=dict(settings,slit_path=lower['lip_path']) if lower.get('lip_path') else settings
    N=128;K=24 if sections else 14;vertices=[];polygons=[];materials=[]
    def section(u):
        rows=sections
        if u<=rows[0][0]:return rows[0][1:]
        if u>=rows[-1][0]:return rows[-1][1:]
        for a,b in zip(rows,rows[1:]):
            if a[0]<=u<=b[0]:
                t=(u-a[0])/(b[0]-a[0]);t=t*t*(3-2*t)
                return [x+(y-x)*t for x,y in zip(a[1:],b[1:])]
    def point(r,angle,top):
        co=math.cos(angle);si=math.sin(angle)
        u=cx+rx*r*math.copysign(abs(co)**(2/power),co)
        y=ry*r*math.copysign(abs(si)**(2/power),si)
        t=max(0,min(1,(u-start)/.025));fade=t*t*(3-2*t)
        if sections:
            local_width,band,edge,rise,crest,underside=section(u)
            blend=max(0,min(1,(u-(start-.0073))/.014));blend=blend*blend*(3-2*blend)
            y*=1+(local_width/ry-1)*blend
        base=(.5-slit_v(lower_curve,u))*aspect-settings['gap']/2
        if top:
            z=base-lower['cup_depth']*(1-r*r)+lower['rim_rise']*r**6*fade+lower['rim_height']*math.exp(-((r-.88)/.13)**2)*fade
            if sections:
                # Section-aligned lip band returns into the oral lining. It is
                # narrow near the corner and fuller at the forward contact edge.
                relative_band=band/max(local_width,.001)
                center=1-relative_band*.45
                bead=crest*math.exp(-((r-center)/max(.025,relative_band*.50))**2)
                shoulder=max(0,min(1,(r-(1-relative_band))/(relative_band)))
                shoulder=shoulder*shoulder*(3-2*shoulder)
                revised=base-lower['cup_depth']*(1-r*r)+rise*shoulder+bead
                z=z*(1-blend)+revised*blend
        else:
            heel=max(0,min(1,(u-start)/(front-start)));heel=1-heel*heel*(3-2*heel)
            across=max(0,1-(y/ry)**2)**.7
            thickness=lower.get('root_thickness',lower['thickness'])+(lower['thickness']-lower.get('root_thickness',lower['thickness']))*fade
            if sections:thickness=thickness*(1-blend)+edge*blend
            z=base-lower['cup_depth']*(1-r*r)-thickness*(1+.25*(1-r*r))-lower.get('heel_depth',0)*heel*across
            y*=lower.get('bottom_width_ratio',1) if not sections else lower.get('bottom_width_ratio',1)*(1-blend)+underside*blend
        return (u-.5,y,z)
    top_center=len(vertices);vertices.append(point(0,0,True));top_rings=[]
    for j in range(1,K+1):
        ring=[]
        for i in range(N):ring.append(len(vertices));vertices.append(point(j/K,math.tau*i/N,True))
        top_rings.append(ring)
    bottom_center=len(vertices);vertices.append(point(0,0,False));bottom_rings=[]
    for j in range(1,K+1):
        ring=[]
        for i in range(N):ring.append(len(vertices));vertices.append(point(j/K,math.tau*i/N,False))
        bottom_rings.append(ring)
    def face(ids,material=0):polygons.append(tuple(ids));materials.append(material)
    for rings,center,top in [(top_rings,top_center,True),(bottom_rings,bottom_center,False)]:
        for i in range(N):face([center,rings[0][i],rings[0][(i+1)%N]],1 if top else 0)
        for j in range(K-1):
            for i in range(N):
                material=1 if top and (j+2)/K<.72 else 0
                if sections and top:
                    u=vertices[rings[j+1][i]][0]+.5
                    local_width,band,*_=section(u)
                    material=1 if (1-(j+1.5)/K)*local_width>band else 0
                face([rings[j][i],rings[j][(i+1)%N],rings[j+1][(i+1)%N],rings[j+1][i]],material)
    # Rounded outside edge bridges the top/bottom of the independent plate.
    rim_rings=[top_rings[-1]]
    rim_steps=10 if sections else 5
    for j in range(1,rim_steps):
        t=j/rim_steps;ring=[]
        for i in range(N):
            angle=math.tau*i/N;a=Vector(point(1,angle,True));b=Vector(point(1,angle,False))
            q=a.lerp(b,.5-.5*math.cos(math.pi*t))
            if sections:
                q.y=b.y+(a.y-b.y)*math.cos(math.pi*t/2)
                q.z=a.z+(b.z-a.z)*math.sin(math.pi*t/2)
            else:
                q.x+=(a.x-(cx-.5))*.018*math.sin(math.pi*t);q.y+=a.y*.018*math.sin(math.pi*t)
            ring.append(len(vertices));vertices.append(tuple(q))
        rim_rings.append(ring)
    rim_rings.append(bottom_rings[-1])
    for a,b in zip(rim_rings,rim_rings[1:]):
        for i in range(N):face([a[i],a[(i+1)%N],b[(i+1)%N],b[i]])
    data=bpy.data.meshes.new('Independent cupped lower jaw');data.from_pydata(vertices,[],polygons);data.update()
    skin=next(m for m in body.data.materials if m.name.startswith('Frontal skin around geometric'))
    atlas=next((m for m in body.data.materials if m.name.startswith('Continuous head pixels')),None) if sections and body_section else None
    if atlas:skin=atlas
    data.materials.append(skin);data.materials.append(inner)
    uv=data.uv_layers.new(name='FrontalSkinUV');rect=cap['source_rect'];dr=cap['model_depth_range'];vr=cap['model_v_range']
    for poly,material in zip(data.polygons,materials):
        poly.material_index=material;poly.use_smooth=material==0
        for li in poly.loop_indices:
            co=data.vertices[data.loops[li].vertex_index].co;u=co.x+.5;v=.5-co.z/aspect
            across=max(0,min(1,(co.y-dr[0])/(dr[1]-dr[0])));high=max(0,min(1,(v+vertical_offset(cap,u)-vr[0])/(vr[1]-vr[0])))
            uv.data[li].uv=(rect[0]+across*(rect[2]-rect[0]),1-(rect[1]+high*(rect[3]-rect[1])))
            if atlas:
                top,bottom,depth=body_section(u)
                center=(.5-(top+bottom)/2)*aspect;radius=(bottom-top)*aspect/2
                theta=math.atan2(co.y/max(depth,1e-6),(co.z-center)/max(radius,1e-6))%math.tau
                uv.data[li].uv=(u,theta/math.tau)
        if atlas:
            values=[uv.data[li].uv.y for li in poly.loop_indices]
            if max(values)-min(values)>.5:
                for li in poly.loop_indices:
                    if uv.data[li].uv.y<.5:uv.data[li].uv.y+=1
    jaw=bpy.data.objects.new('Lower_jaw_separate',data);bpy.context.scene.collection.objects.link(jaw)
    root_fit={'vertices':0,'maximum_shift_native':0}
    if lower.get('root_surface_inset'):
        bm=bmesh.new();bm.from_mesh(body.data);tree=BVHTree.FromBMesh(bm);bm.free()
        for vertex in jaw.data.vertices:
            u=vertex.co.x+.5
            if u>=start+.008:continue
            near,normal,_,distance=tree.find_nearest(vertex.co)
            if normal.dot(vertex.co-near)<=0:continue
            t=max(0,min(1,(u-(start-.004))/.012));fade=1-t*t*(3-2*t)
            shift=(distance+lower['root_surface_inset'])*fade
            vertex.co-=normal*shift
            root_fit['vertices']+=1;root_fit['maximum_shift_native']=max(root_fit['maximum_shift_native'],shift)
    finish(jaw,weights)
    return jaw,{'method':'Old lower snout removed from head; independent closed cupped oval lower jaw with thick rolled rim and recessed oral surface.',
        'separate_lower':lower,'root_surface_fit':root_fit,'outer_skin_uv':'Shared head cylindrical atlas' if atlas else 'Frontal projection','original_body_vertices':original_vertices,'upper_body_vertices':len(body.data.vertices),'lower_jaw_vertices':len(jaw.data.vertices),'lower_jaw_object':jaw.name,'articulated_jaw':False,'removed_original_lower_shell':True}

def rig_lower_jaw(rig,jaw,settings,aspect,weights):
    """Add a transverse jaw hinge; posterior skin retains the carrier weights."""
    motion=settings.get('articulation')
    if not motion:return
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    bone=rig.data.edit_bones.new('jaw_lower')
    u,v=motion['hinge'];bone.head=(u-.5,0,(.5-v)*aspect)
    # Local Y is transverse, so a local Y rotation opens towards ventral.
    bone.tail=bone.head+Vector((0,.025,0));bone.parent=rig.data.edit_bones['body_00']
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    for obj in [jaw]+[bpy.data.objects[name] for name in jaw.get('oral_web_names',[])]:
        # Adding deform groups reallocates Blender CustomData. Copy the reference
        # attributes first; retaining their RNA handles while adding groups can
        # silently read a different layer (source u as jaw influence).
        source_u=obj.data.attributes.get('reference_source_u');source_weight=obj.data.attributes.get('reference_jaw_weight')
        source_us=[item.value for item in source_u.data] if source_u else None
        source_weights=[item.value for item in source_weight.data] if source_weight else None
        obj.vertex_groups.clear()
        for vertex in obj.data.vertices:
            u=source_us[vertex.index] if source_us is not None else vertex.co.x+.5
            t=max(0,min(1,(u-motion['fixed_root_u'])/(motion['rigid_start_u']-motion['fixed_root_u'])))
            amount=source_weights[vertex.index] if source_weights is not None else t*t*(3-2*t)
            values={name:value*(1-amount) for name,value in weights(u).items()};values['jaw_lower']=amount
            for name,value in values.items():
                if value>0:(obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)).add([vertex.index],value,'REPLACE')
    rig['jaw_max_open_degrees']=motion['max_open_degrees']
    rig.pose.bones['jaw_lower'].rotation_mode='XYZ'
    rig.pose.bones['jaw_lower']['open_axis']='local Y; radians(0..max_open_degrees)'
