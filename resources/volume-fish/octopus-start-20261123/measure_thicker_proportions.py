"""Measure the exported grey skin, independently of the authoring process."""
import bpy, bmesh, math, json, hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'motion-r5'
build=json.loads((ROOT/'motion-r3/rest/gray-build.validation.json').read_text())
profile=json.loads((ROOT/'proportion-constraints.json').read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(OUT/'octopus-actions.glb'))
skin=bpy.data.objects['Octopus_gray_skin']
bm=bmesh.new();bm.from_mesh(skin.data);bm.transform(skin.matrix_world)
exported_vertices=len(bm.verts)
# glTF splits coincident vertices at normal/UV boundaries. Reconstruct geometric
# adjacency for this check without editing the asset or merging distinct surfaces.
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bvh=BVHTree.FromBMesh(bm)
seen=set(bm.verts);components=[]
while seen:
    stack=[seen.pop()];size=0
    while stack:
        v=stack.pop();size+=1
        for e in v.link_edges:
            w=e.other_vert(v)
            if w in seen:seen.remove(w);stack.append(w)
    components.append(size)
mouth=Vector(build['mouth']);eye=Vector(build['mantle_eye_midpoint']);axis=Vector(build['mantle_measurement_axis'])
# Local region isolates the mantle cap from the long arms; geometry, not an
# ellipsoid parameter, supplies the endpoint. Its actual vertex is retained.
cap=[v.co for v in bm.verts if .3<(v.co-eye).dot(axis)<1.15 and ((v.co-eye)-axis*(v.co-eye).dot(axis)).length<.43]
posterior=max(cap,key=lambda v:(v-eye).dot(axis));ML=(posterior-eye).dot(axis)
paths=build['control_paths']
def curve(pts,t):
    u=max(0,min(1,t))*(len(pts)-1);i=min(int(u),len(pts)-2);f=u-i
    a,b,c,d=[Vector(pts[k]) for k in [max(0,i-1),i,i+1,min(len(pts)-1,i+2)]]
    return .5*(2*b+(-a+c)*f+(2*a-5*b+4*c-d)*f*f+(-a+3*b-3*c+d)*f*f*f)
def surface_guide(i,t):
    p=curve(paths[i],t);tangent=(curve(paths[i],min(1,t+.003))-curve(paths[i],max(0,t-.003))).normalized()
    side=tangent.cross(Vector((0,0,1))).normalized();up=side.cross(tangent).normalized()
    roll=0.
    up=up*math.cos(roll)-side*math.sin(roll)
    ease=lambda x:(lambda q:q*q*(3-2*q))(max(0.,min(1.,x)))
    r=.137*(1-t)**1.32+.009+.026*ease((t-.55)/.25)*(1-ease((t-.94)/.06))
    return p-up*(.83*r),up
arms=[]
for i,label in enumerate(build['arm_labels']):
    start,_=surface_guide(i,0)
    planned=[(mouth.lerp(start,k/12),Vector((0,0,1))) for k in range(12)]
    planned += [surface_guide(i,k/240) for k in range(241)]
    measured=[];miss=0;max_offset=0
    for point,up in planned:
        hit,normal,face,distance=bvh.ray_cast(point-up*.30,up,.60)
        if hit is None:
            miss+=1;hit,normal,face,distance=bvh.find_nearest(point)
        measured.append(hit);max_offset=max(max_offset,(hit-point).length)
    length=sum((b-a).length for a,b in zip(measured,measured[1:]))
    target=profile['chosen_targets']['AL_per_ML_by_pair'][label.split('_')[1]]
    arms.append({'arm':label,'measured_oral_surface_length':length,'AL_per_ML':length/ML,'target':target,'relative_error':abs(length/ML-target)/target,'projection_misses':miss,'max_surface_guide_offset':max_offset,'path_for_annotation':[list(p) for p in measured[::10]]+[list(measured[-1])]})
max_arm=max(a['measured_oral_surface_length'] for a in arms)
webs=[]
for label,raw in zip(build['web_labels'],build['web_edge_midplanes']):
    middle=Vector(raw);direction=(middle-mouth).normalized()
    # The membrane is curved; a straight radial ray can pass below its interior.
    # Sweep vertical rays through the oral surface and locate the real projected
    # free edge. A mantle hit well above the membrane does not count as web.
    def web_surface(p):
        hit,n,face,distance=bvh.ray_cast(Vector((p.x,p.y,-1)),Vector((0,0,1)),3)
        if hit is None or abs(hit.z-middle.z)>.10:return None
        return hit
    a=middle-direction*.08;b=middle+direction*.08
    h_a=web_surface(a);h_b=web_surface(b)
    crosses=h_a is not None and h_b is None
    if crosses:
        for _ in range(35):
            m=(a+b)*.5
            if web_surface(m) is not None:a=m
            else:b=m
        edge=web_surface(a)
    else:edge=bvh.find_nearest(middle)[0]
    depth=(edge-mouth).length
    target=profile['chosen_targets']['WD_per_longest_AL_by_sector'][label[0]]
    webs.append({'sector':label,'actual_mid_edge':list(edge),'WD':depth,'WD_per_longest_AL':depth/max_arm,'target':target,'absolute_fraction_error':abs(depth/max_arm-target),'verified_solid_to_air_edge':crosses,'initial_inside_outside_coverage':[h_a is not None,h_b is not None]})
tol=profile['final_measurement_tolerances']
checks={'one_connected_skin':len(components)==1,'skin_closed_manifold':all(e.is_manifold for e in bm.edges),'no_degenerate_skin_faces':all(f.calc_area()>1e-12 for f in bm.faces),'mantle_target':abs(ML-1)<tol['ML_relative'],'arm_targets':all(a['relative_error']<tol['AL_target_relative'] for a in arms),'arm_reference_range':all(3<=a['AL_per_ML']<=5 for a in arms),'web_midpoints_exposed':all(w['verified_solid_to_air_edge'] for w in webs),'web_targets':all(w['absolute_fraction_error']<tol['WD_target_absolute_longest_AL'] for w in webs),'max_web_reference_range':.18<=max(w['WD_per_longest_AL'] for w in webs)<=.28}
by_arm={a['arm']:a['AL_per_ML'] for a in arms}
checks['arm_formula_nearly_equal_I_II_then_III_IV']=all(abs(by_arm[side+'_I']-by_arm[side+'_II'])/by_arm[side+'_I']<.01 and min(by_arm[side+'_I'],by_arm[side+'_II'])>by_arm[side+'_III']>by_arm[side+'_IV'] for side in ['L','R'])
by_web={w['sector']:w['WD_per_longest_AL'] for w in webs}
checks['dorsal_ventral_web_shallower_than_lateral']=max(by_web['A'],by_web['E'])<min(v for k,v in by_web.items() if k not in ['A','E'])
report={'kind':'octopus_exported_skin_proportions','model_sha256':hashlib.sha256((OUT/'octopus-actions.glb').read_bytes()).hexdigest(),'method':'Cold GLB import; oral measurement guides projected onto actual skin; ML posterior vertex measured along rigid dorsal axis; web boundary coverage-to-air crossing at each sector midpoint in oral projection. Reference ranges are species diagnostics, exact within-range targets are documented model choices.','export_vertices_before_geometric_weld':exported_vertices,'ML':ML,'eye_midpoint':list(eye),'posterior_vertex':list(posterior),'mouth':list(mouth),'arms':arms,'webs':webs,'skin_components':components,'checks':checks,'ok':all(checks.values()),'limitations':['No full species morphology acceptance','Widths, thickness and the pose itself are not specimen measurements','Oral length uses a sampled surface path; the sparse display annotation is not the integration sample set']}
(OUT/'proportions.validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'ML':ML,'arms':[{k:v for k,v in a.items() if k!='path_for_annotation'} for a in arms],'webs':webs,'checks':checks},indent=2))
