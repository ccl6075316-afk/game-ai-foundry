"""Independent octopus grey study. Run with Blender --background --python.

Reference roles and limitations are in handoff.md. Control curves are design
estimates, not measurements of the specimen or a biomechanical animation.
"""
import bpy, bmesh, math, json, hashlib, bisect
from pathlib import Path
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'r2'
OUT.mkdir(exist_ok=True)
PROFILE=json.loads((ROOT/'proportion-constraints.json').read_text())
MOUTH=Vector(PROFILE['landmarks']['mouth'])
ARM_LABELS=PROFILE['arm_mapping_in_existing_paths']
WEB_LABELS=PROFILE['web_mapping_between_consecutive_paths']
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
source=bpy.data.collections.new('EDITABLE_FORM_CONTROLS');scene.collection.children.link(source)
final=bpy.data.collections.new('GRAY_REVIEW');scene.collection.children.link(final)
def move(obj,coll):
    for c in list(obj.users_collection):c.objects.unlink(obj)
    coll.objects.link(obj)
def mat(name,c,rough=.75):
    m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough
    return m
skin=mat('Neutral clay',(.43,.46,.47));cupmat=mat('Sucker clay',(.57,.59,.59));eyemat=mat('Eye clay',(.22,.25,.26));pupil=mat('Pupil relief',(.10,.12,.13))
def mesh(name,vs,fs,coll=source,material=skin):
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();ob=bpy.data.objects.new(name,me);coll.objects.link(ob);me.materials.append(material)
    for p in me.polygons:p.use_smooth=True
    return ob
def ellipsoid(name,loc,scale,seg=32,rings=20,coll=source,material=skin):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,location=loc);ob=bpy.context.object;ob.name=name;ob.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);move(ob,coll);ob.data.materials.append(material)
    for p in ob.data.polygons:p.use_smooth=True
    return ob

# Arms ordered around the circumoral crown. Local bends differ intentionally.
paths=[
 [(-.10,-.20,.33),(-.25,-.65,.23),(-.40,-1.10,.15),(-.62,-1.48,.20),(-.83,-1.51,.33),(-.87,-1.32,.42),(-.75,-1.28,.45)],
 [(-.25,-.13,.32),(-.65,-.50,.24),(-1.20,-.85,.16),(-1.60,-.90,.20),(-1.78,-.70,.33),(-1.62,-.60,.42)],
 [(-.29,.10,.32),(-.70,.15,.23),(-1.30,.08,.16),(-1.65,.30,.19),(-1.60,.65,.33),(-1.35,.70,.38)],
 [(-.19,.26,.32),(-.55,.55,.24),(-.90,.95,.18),(-1.10,1.25,.19),(-1.15,1.50,.25),(-1.05,1.60,.28)],
 [(.17,.28,.32),(.51,.63,.24),(.92,1.00,.17),(1.10,1.35,.20),(.98,1.55,.33),(.83,1.45,.38)],
 [(.28,.12,.32),(.75,.20,.23),(1.20,.45,.16),(1.55,.68,.24),(1.50,.94,.41),(1.30,.90,.44)],
 [(.25,-.10,.32),(.70,-.30,.25),(1.20,-.60,.18),(1.60,-.70,.28),(1.75,-.50,.44),(1.60,-.40,.48)],
 [(.10,-.20,.33),(.38,-.60,.24),(.58,-1.10,.16),(.75,-1.55,.13),(.95,-1.80,.16),(1.12,-1.78,.24)]
]
# Extend the free arms relative to the mantle; keep the eight root positions.
for pts in paths:
    root=Vector(pts[0])
    for k in range(1,len(pts)):
        v=Vector(pts[k]);v.x=root.x+1.18*(v.x-root.x);v.y=root.y+1.18*(v.y-root.y);pts[k]=tuple(v)
paths[3][-2]=(-1.38,1.65,.19);paths[3][-1]=(-1.40,1.85,.21)
paths[6][-2]=(1.95,-.55,.62);paths[6][-1]=(1.80,-.42,.72)
def catmull(pts,t):
    pts=[Vector(v) for v in pts];u=max(0,min(t,1))*(len(pts)-1);i=min(int(u),len(pts)-2);f=u-i
    p0=pts[max(0,i-1)];p1=pts[i];p2=pts[i+1];p3=pts[min(len(pts)-1,i+2)]
    return .5*((2*p1)+(-p0+p2)*f+(2*p0-5*p1+4*p2-p3)*f*f+(-p0+3*p1-3*p2+p3)*f*f*f)
def frame(idx,t):
    p=catmull(paths[idx],t);tangent=(catmull(paths[idx],min(1,t+.003))-catmull(paths[idx],max(0,t-.003))).normalized()
    side=tangent.cross(Vector((0,0,1))).normalized();up=side.cross(tangent).normalized()
    # Mild distal roll presents a few suckers in an oblique view.
    roll=math.sin(t*math.pi*.8)*([-.25,.35,-.45,.1,-.2,.4,-.4,.2][idx])
    side2=side*math.cos(roll)+up*math.sin(roll);up2=up*math.cos(roll)-side*math.sin(roll)
    return p,tangent,side2,up2
def radius(t):return .137*(1-t)**1.32+.009

# The old t value was a knot parameter, not a length fraction. First solve the
# mouth-to-tip oral-guide length, then invert arc length for all web landmarks.
def oral_point(i,t):
    p,ta,side,up=frame(i,t)
    return p-up*(.83*radius(t))
def oral_guide(i,n=800):
    points=[MOUTH]+[oral_point(i,k/n) for k in range(n+1)]
    distances=[0.0]
    for a,b in zip(points,points[1:]):distances.append(distances[-1]+(b-a).length)
    return points,distances
for i in range(8):
    target=PROFILE['chosen_targets']['AL_per_ML_by_pair'][ARM_LABELS[i].split('_')[1]]
    original=[Vector(p) for p in paths[i]];base=original[0]
    lo,hi=.4,3.0
    for iteration in range(25):
        scale=(lo+hi)*.5
        paths[i]=[tuple(base+(p-base)*scale) for p in original]
        length=oral_guide(i,400)[1][-1]
        if length<target:lo=scale
        else:hi=scale
    paths[i]=[tuple(base+(p-base)*((lo+hi)*.5)) for p in original]
ARM_GUIDES=[oral_guide(i) for i in range(8)]
ARM_LENGTHS=[x[1][-1] for x in ARM_GUIDES]
def t_at_arm_fraction(i,f):
    distances=ARM_GUIDES[i][1];target=f*distances[-1]
    k=bisect.bisect_left(distances,target)
    if k<=1:return 0.0
    k=min(k,len(distances)-1)
    local=(target-distances[k-1])/(distances[k]-distances[k-1])
    return (k-2+local)/800
WEB_MID_FRACTIONS=[]
WEB_DEPTHS=[]
for i in range(8):
    j=(i+1)%8
    target=PROFILE['chosen_targets']['WD_per_longest_AL_by_sector'][WEB_LABELS[i][0]]*max(ARM_LENGTHS)
    lo,hi=.05,.5
    for iteration in range(35):
        q=(lo+hi)*.5
        # Free-edge oral midpoint after lower thickness offset.
        mid=(frame(i,t_at_arm_fraction(i,q))[0]+frame(j,t_at_arm_fraction(j,q))[0])*.5
        mid.z+=.024*math.sin(math.pi*1.3)-.009
        if (mid-MOUTH).length<target:lo=q
        else:hi=q
    WEB_MID_FRACTIONS.append((lo+hi)*.5)
    WEB_DEPTHS.append(target)
for i in range(8):
    cu=bpy.data.curves.new(f'Arm_{i+1:02d}_control','CURVE');cu.dimensions='3D';sp=cu.splines.new('POLY');sp.points.add(len(paths[i])-1)
    for p,v in zip(sp.points,paths[i]):p.co=(*v,1)
    co=bpy.data.objects.new(cu.name,cu);source.objects.link(co);co['anatomical_arm']=ARM_LABELS[i]
    vs=[];fs=[];N=65;K=12
    for n in range(N):
        t=n/(N-1);p,ta,side,up=frame(i,t);r=radius(t)
        for j in range(K):
            a=j*2*math.pi/K;vs.append(p+r*(math.cos(a)*side+.83*math.sin(a)*up))
    for n in range(N-1):
        for j in range(K):a=n*K+j;b=n*K+(j+1)%K;fs.append((a,b,b+K,a+K))
    fs.append(tuple(range(K-1,-1,-1)));fs.append(tuple((N-1)*K+j for j in range(K)))
    mesh(f'Arm_{i+1:02d}_volume',vs,fs)

# Broad proximal web scallops. Each patch's sides follow its two actual arms;
# the middle free edge retreats toward the crown rather than spanning arm tips.
for i in range(8):
    vs=[];fs=[];N=15;K=13;j=(i+1)%8
    for bottom in (False,True):
        for n in range(N):
            u=n/(N-1)
            for k in range(K):
                v=k/(K-1)
                # Explicit physical depth controls the middle of the scallop.
                # A narrow lateral continuation reaches farther along each arm.
                edge_q=WEB_MID_FRACTIONS[i]+.10*(1-math.sin(math.pi*v))**.7
                q=.06+u*(edge_q-.06)
                a=frame(i,t_at_arm_fraction(i,q))[0];b=frame(j,t_at_arm_fraction(j,q))[0];p=a.lerp(b,v)
                p.z+=.024*math.sin(math.pi*v)*math.sin(math.pi*u*1.3)
                p.z+=(-1 if bottom else 1)*(.018*(1-u)+.009)
                vs.append(p)
    layer=N*K
    for n in range(N-1):
        for k in range(K-1):
            a=n*K+k;fs.append((a,a+1,a+K+1,a+K));fs.append((a+layer+K,a+layer+K+1,a+layer+1,a+layer))
    edge=list(range(K))+[n*K+K-1 for n in range(1,N)]+[(N-1)*K+k for k in range(K-2,-1,-1)]+[n*K for n in range(N-2,0,-1)]
    for a,b in zip(edge,edge[1:]+edge[:1]):fs.append((a,a+layer,b+layer,b))
    ob=mesh(f'Web_{i+1:02d}_control_surface',vs,fs);ob['anatomical_sector']=WEB_LABELS[i]
ellipsoid('Circumoral_crown',(0,.03,.32),(.34,.36,.20))
ellipsoid('Head',(0,.28,.47),(.28,.38,.27))
ellipsoid('Mantle_neck',(0,.51,.50),(.25,.28,.23))
mantle=ellipsoid('Mantle',(0,.81,.58),(.35,.47,.34))
# A raised-mantle review pose exposes dorsal sector A. This is a rigid pose
# rotation, not a new proportion: the eye-plane-to-posterior axis stays 1 ML.
mantle_pivot=Vector((0,.28,.55));mantle_rotation=Matrix.Rotation(math.radians(45),3,'X')
for ob in [mantle,bpy.data.objects['Mantle_neck']]:
    ob.location=mantle_pivot+mantle_rotation@(ob.location-mantle_pivot)
    ob.rotation_euler.x=math.radians(45)
# Lateral eye bulges belong to skin; eye inserts remain editable.
for side in (-1,1):ellipsoid('Eye_brow_'+str(side),(side*.25,.29,.55),(.105,.15,.12),24,14)

# Freeze the skin union in a derived review mesh; all original controls remain
# hidden and editable in the blend. This is not a deformation-ready retopology.
parts=[o for o in source.objects if o.type=='MESH']
copies=[]
for o in parts:
    c=o.copy();c.data=o.data.copy();final.objects.link(c);copies.append(c)
bpy.ops.object.select_all(action='DESELECT')
for o in copies:o.select_set(True)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();body=bpy.context.object;body.name='Octopus_gray_skin'
rem=body.modifiers.new('Continuous skin union','REMESH');rem.mode='VOXEL';rem.voxel_size=.005;rem.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=rem.name)
sm=body.modifiers.new('Surface relax','SMOOTH');sm.factor=.55;sm.iterations=3;bpy.ops.object.modifier_apply(modifier=sm.name)
tri=sum(len(p.vertices)-2 for p in body.data.polygons);dec=body.modifiers.new('Grey study density','DECIMATE');dec.ratio=min(1,2800/tri);bpy.ops.object.modifier_apply(modifier=dec.name)
body.data.materials.clear();body.data.materials.append(skin)
# Voxel/decimation left two microscopic single triangles at the eye-brow union.
# Remove only isolated fragments smaller than 0.001 ML; main skin must close.
bm=bmesh.new();bm.from_mesh(body.data);unseen=set(bm.verts);components=[]
while unseen:
    todo=[unseen.pop()];component=[]
    while todo:
        v=todo.pop();component.append(v)
        for e in v.link_edges:
            w=e.other_vert(v)
            if w in unseen:unseen.remove(w);todo.append(w)
    components.append(component)
removed_microscopic_fragments=[]
for component in sorted(components,key=len)[:-1]:
    center=sum((body.matrix_world@v.co for v in component),Vector())/len(component)
    diameter=max((a.co-b.co).length for a in component for b in component)
    assert len(component)<=3 and diameter<.001, 'Unexpected disconnected skin: do not hide it'
    removed_microscopic_fragments.append({'vertices':len(component),'center':list(center),'diameter':diameter})
    bmesh.ops.delete(bm,geom=component,context='VERTS')
assert all(e.is_manifold for e in bm.edges), 'Skin must remain closed after tip cleanup'
bm.to_mesh(body.data);bm.free();body.data.update()

# Representative two-row cup geometry; grey study count is deliberately reduced.
cv=[];cf=[];cup_count=0
for i in range(8):
    for n in range(10):
        t=t_at_arm_fraction(i,.13+n*.082)
        p,tan,side,up=frame(i,t);r=radius(t);cr=r*.37
        for s in (-1,1):
            center=p+side*(s*r*.47)-up*(r*.69)
            normal=(-up+side*(s*.16)).normalized();u=tan;v=normal.cross(u).normalized();base=len(cv)
            for rad,h in [(cr,.018*(1-t)+.003),(cr*.48,-.001)]:
                for k in range(6):cv.append(center+normal*h+rad*(u*math.cos(k*math.tau/6)+v*math.sin(k*math.tau/6)))
            for l in range(1):
                for k in range(6):a=base+l*6+k;b=base+l*6+(k+1)%6;cf.append((a,b,b+6,a+6))
            cf.append(tuple(base+6+k for k in reversed(range(6))));cup_count+=1
cups=mesh('Paired_sucker_rows_160_proxy_cups',cv,cf,final,cupmat)
# Each cup is a 16-triangle flared dish with a recessed floor.
# Keep the silhouette ring and recessed floor (middle ring not needed at this scale).
for s in (-1,1):
    eye=ellipsoid('Eye_'+str(s),(s*.306,.28,.55),(.053,.082,.061),12,6,final,eyemat)
    slit=ellipsoid('Eye_slit_'+str(s),(s*.354,.265,.55),(.008,.047,.013),8,4,final,pupil)

# Visible open siphon on the ventral side of the head, independent of oral centre.
fv=[];ff=[];K=12
centers=[Vector((.14,.43,.27)),Vector((.19,.25,.13)),Vector((.24,.08,.07))]
axis=(centers[-1]-centers[-2]).normalized();u=axis.cross(Vector((1,0,0))).normalized();v=axis.cross(u)
for layer in range(2):
    for n,c in enumerate(centers):
        rr=[.080,.061,.047][n]-(.014 if layer else 0)
        for j in range(K):fv.append(c+rr*(u*math.cos(j*math.tau/K)+v*math.sin(j*math.tau/K)))
for n in range(2):
    for j in range(K):a=n*K+j;b=n*K+(j+1)%K;ff.append((a,b,b+K,a+K));ff.append((a+36+K,b+36+K,b+36,a+36))
for j in range(K):a=24+j;b=24+(j+1)%K;ff.append((a,b,b+36,a+36))
mesh('Open_siphon',fv,ff,final,skin)
# Small ventral oral mound and recessed aperture, not a fish jaw.
ellipsoid('Oral_mound',(0,0,.152),(.085,.085,.035),12,6,final,skin)
ellipsoid('Oral_aperture',(0,-.005,.124),(.032,.036,.006),8,4,final,eyemat)

# Hide source collection in review/export without destroying editable controls.
source.hide_render=True;source.hide_viewport=True
bpy.ops.object.select_all(action='DESELECT')
for o in final.objects:o.select_set(True)
bpy.context.view_layer.objects.active=body
for ob in final.objects:
    ob['stage']='grey_form_review_not_final';ob['source']='independently authored from observed reference roles'
bpy.ops.export_scene.gltf(filepath=str(OUT/'octopus-gray.glb'),export_format='GLB',use_selection=True,export_animations=False,export_yup=True)

# Quiet studio render setup. No external textures and no generated images.
world=bpy.data.worlds.new('Grey studio');scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.19,.22,.25,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5
def area(name,loc,power,size):
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=name;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,0,.2))-o.location).to_track_quat('-Z','Y').to_euler()
area('Key',(-3,-4,6),550,5);area('Fill',(4,1,4),400,4);area('Rim',(0,4,4),450,3)
bpy.ops.object.camera_add();cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=8.3
scene.render.engine='BLENDER_EEVEE_NEXT';scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'
views={'oblique':((3.5,-4.8,4.5),(0,-.05,.30)),'top':((0,-.05,7),(0,-.05,0)),'side':((6,-.1,1.5),(0,-.05,.40)),'underside':((2,-3,-5),(0,0,.25))}
for name,(loc,target) in views.items():
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()
    local=[cam.matrix_world.inverted()@(o.matrix_world@v.co) for o in final.objects for v in o.data.vertices]
    cam.data.ortho_scale=1.12*max(2*max(abs(v.x) for v in local),2*max(abs(v.y) for v in local)*1400/1100)
    scene.render.filepath=str(OUT/f'gray-{name}.png');bpy.ops.render.render(write_still=True)
loc,target=views['oblique'];cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':a.spaces.active.region_3d.view_distance=5;a.spaces.active.region_3d.view_location=(0,0,.3)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'octopus-gray.blend'))
report={'kind':'octopus_gray_build','status':'candidate','revision':2,'arms':8,'web_sectors':8,'representative_suckers':cup_count,'rigged':False,'animations':0,'units':'ML-normalized model units, not a real specimen scale','control_paths':paths,'arm_labels':ARM_LABELS,'web_labels':WEB_LABELS,'oral_guide_lengths':ARM_LENGTHS,'web_depth_targets':WEB_DEPTHS,'web_mid_fractions':WEB_MID_FRACTIONS,'parts':{o.name:sum(len(p.vertices)-2 for p in o.data.polygons) for o in final.objects if o.type=='MESH'},'limitations':['Published reference ranges constrain lengths, not a reconstruction of a measured individual','Skin union is static; animation retopology and rig remain to be built','160 representative cups; not anatomical sucker count','Exact arm/sector differences are documented target interpolation; width/thickness and pose are not measured specimen data']}
report['triangles']=sum(report['parts'].values());report['glb_sha256']=hashlib.sha256((OUT/'octopus-gray.glb').read_bytes()).hexdigest()
report['removed_microscopic_fragments']=removed_microscopic_fragments
report['mantle_measurement_axis']=list(mantle_rotation@Vector((0,1,0)))
report['mantle_eye_midpoint']=list(mantle_pivot)
report['mouth']=list(MOUTH)
report['web_edge_midplanes']=[]
for i,q in enumerate(WEB_MID_FRACTIONS):
    mid=(frame(i,t_at_arm_fraction(i,q))[0]+frame((i+1)%8,t_at_arm_fraction((i+1)%8,q))[0])*.5
    mid.z+=.024*math.sin(math.pi*1.3)
    report['web_edge_midplanes'].append(list(mid))
(OUT/'gray-build.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('GRAY_RESULT',json.dumps({'triangles':report['triangles'],'parts':report['parts']}))
