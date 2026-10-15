"""Read-only Blender audit of accepted native and a declared width/height revision.

blender --background --python audit_native_revision.py -- original.blend candidate.blend profile.json report.json
"""
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/"cli"))
from volume_shape import validate_revision, width_scale, vertical_position


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def action_curves(action):
    curves=[]
    # Blender 4.5 layered action storage; retain every slot/channelbag.
    for layer in action.layers:
        for strip in layer.strips:
            for bag in getattr(strip,'channelbags',[]):
                curves.extend(bag.fcurves)
    if not curves:
        curves=list(getattr(action,'fcurves',[]))
    return sorted([(curve.data_path,curve.array_index,[(tuple(point.co),point.interpolation,tuple(point.handle_left),tuple(point.handle_right)) for point in curve.keyframe_points]) for curve in curves],key=lambda x:(x[0],x[1]))


def section(mesh,x):
    points=[]
    for edge in mesh.edges:
        a,b=[mesh.vertices[i].co for i in edge.vertices]
        if abs(a.x-x)<1e-8:points.append(tuple(a))
        if (a.x-x)*(b.x-x)<0:
            t=(x-a.x)/(b.x-a.x)
            points.append(tuple(a.lerp(b,t)))
    if not points:return None
    return {'width':max(p[1] for p in points)-min(p[1] for p in points),'height':max(p[2] for p in points)-min(p[2] for p in points),'left':min(p[1] for p in points),'right':max(p[1] for p in points),'top_z':max(p[2] for p in points),'bottom_z':min(p[2] for p in points)}


def capture(path,stations):
    bpy.ops.wm.open_mainfile(filepath=str(path),use_scripts=False)
    meshes={}
    all_x=[]
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH':continue
        data=obj.data
        vertices=[tuple(v.co) for v in data.vertices]
        all_x.extend(v[0] for v in vertices)
        meshes[obj.name]={'vertices':vertices,'polygons':[tuple(p.vertices) for p in data.polygons],'edges':[tuple(e.vertices) for e in data.edges],'uvs':{uv.name:[tuple(v.uv) for v in uv.data] for uv in data.uv_layers},'groups':[[[obj.vertex_groups[g.group].name,g.weight] for g in vertex.groups] for vertex in data.vertices],'sections':{str(u):section(data,u-.5) for u in stations}}
    bones={}
    for obj in bpy.context.scene.objects:
        if obj.type!='ARMATURE':continue
        bones[obj.name]={bone.name:{'parent':bone.parent.name if bone.parent else None,'head':tuple(bone.head_local),'tail':tuple(bone.tail_local),'connected':bone.use_connect} for bone in obj.data.bones}
    return {'meshes':meshes,'bones':bones,'actions':{a.name:action_curves(a) for a in bpy.data.actions},'images':sorted(hashlib.sha256(bytes(i.packed_file.data)).hexdigest() for i in bpy.data.images if i.packed_file),'length_units':max(all_x)-min(all_x)}


def main():
    args=sys.argv[sys.argv.index('--')+1:]
    if len(args)!=4:raise ValueError('Expected original.blend candidate.blend profile.json report.json')
    original,candidate,profile_path,out=map(lambda value:Path(value).resolve(),args)
    profile=json.loads(profile_path.read_text())
    revision=profile.get('rest_shape_revision')
    if revision is None:raise ValueError('This preservation audit requires a native revision; procedural rebuilds must report intentional per-part topology/UV changes separately')
    validate_revision(revision)
    stations=sorted(set([row[0] for row in revision['stations']]+[row[0] for row in revision.get('vertical_stations',[])]))
    before=capture(original,stations);after=capture(candidate,stations)
    vertical=revision.get('vertical_stations',[]);aspect=1/profile['source_aspect_ratio']
    def mapped(point):
        x,y,z=point
        return (x,y*width_scale(revision['stations'],x+.5),vertical_position(vertical,x+.5,z,aspect))
    fin_names={f['name']+suffix for f in profile['fins'] for suffix in (['_left','_right'] if f['paired'] else ['']) if f['paired'] or vertical}
    bones={name:bone for rig in before['bones'].values() for name,bone in rig.items()}
    shifts={name:tuple(b-a for a,b in zip(bones[name]['head'],mapped(bones[name]['head']))) for name in fin_names if name in bones}
    def expected_vertices(name,vertices):
        if name in shifts:shift=shifts[name]
        elif name.startswith('Textured_eye_'):
            center=tuple(sum(v[i] for v in vertices)/len(vertices) for i in range(3))
            shift=tuple(b-a for a,b in zip(center,mapped(center)))
        else:return [mapped(v) for v in vertices]
        return [tuple(a+b for a,b in zip(v,shift)) for v in vertices]
    checks={'matches_declared_source':digest(original)==revision['blend_sha256'],'same_mesh_names':set(before['meshes'])==set(after['meshes']),'same_bone_hierarchy':set(before['bones'])==set(after['bones']),'same_actions':before['actions']==after['actions'],'same_packed_textures':before['images']==after['images'],'same_x':True,'declared_y_mapping':True,'declared_z_mapping' if vertical else 'same_z':True,'same_topology':True,'same_uvs':True,'same_weights':True}
    measurements={};deformation={};bone_deformation={}
    checks['declared_bone_rest_mapping']=True
    for name,old in before['meshes'].items():
        new=after['meshes'].get(name)
        if new is None:
            for key in ['same_x','declared_y_mapping','declared_z_mapping' if vertical else 'same_z','same_topology','same_uvs','same_weights']:checks[key]=False
            continue
        expected=expected_vertices(name,old['vertices'])
        same_count=len(old['vertices'])==len(new['vertices'])
        checks['same_x'] &= same_count and all(abs(a[0]-b[0])<1e-7 for a,b in zip(old['vertices'],new['vertices']))
        checks['declared_y_mapping'] &= same_count and all(abs(a[1]-b[1])<1e-7 for a,b in zip(expected,new['vertices']))
        checks['declared_z_mapping' if vertical else 'same_z'] &= same_count and all(abs(a[2]-b[2])<1e-7 for a,b in zip(expected,new['vertices']))
        deformation[name]={'z_vertices_changed':sum(abs(a[2]-b[2])>1e-7 for a,b in zip(old['vertices'],new['vertices'])),'maximum_z_mapping_error_units':max((abs(a[2]-b[2]) for a,b in zip(expected,new['vertices'])),default=0),'maximum_y_mapping_error_units':max((abs(a[1]-b[1]) for a,b in zip(expected,new['vertices'])),default=0)}
        checks['same_topology'] &= len(old['vertices'])==len(new['vertices']) and old['polygons']==new['polygons'] and old['edges']==new['edges']
        checks['same_uvs'] &= old['uvs']==new['uvs']
        checks['same_weights'] &= old['groups']==new['groups']
        if name in ['Closed_body','Cephalofoil']:
            factor=float(profile['real_length_cm'])/before['length_units']
            measurements[name]=[{'u':u,'before_cm':None if old['sections'][str(u)] is None else {k:v*factor for k,v in old['sections'][str(u)].items()},'after_cm':None if new['sections'][str(u)] is None else {k:v*factor for k,v in new['sections'][str(u)].items()}} for u in stations]
    for name,old in before['bones'].items():
        new=after['bones'].get(name,{})
        checks['same_bone_hierarchy'] &= set(old)==set(new) and all(bone in new and data['parent']==new[bone]['parent'] and data['connected']==new[bone]['connected'] for bone,data in old.items())
        for bone,data in old.items():
            errors={};expected={}
            for endpoint in ['head','tail']:
                point=data[endpoint]
                expected[endpoint]=tuple(a+b for a,b in zip(point,shifts[bone])) if bone in shifts else mapped(point)
                actual=new.get(bone,{}).get(endpoint)
                finite=actual is not None and all(math.isfinite(v) for v in (*actual,*expected[endpoint]))
                error=max(abs(a-b) for a,b in zip(actual,expected[endpoint])) if finite else None
                errors[endpoint]=error
                checks['declared_bone_rest_mapping'] &= finite and error<=1e-7
            bone_deformation[name+'/'+bone]={'expected_head':expected['head'],'expected_tail':expected['tail'],'maximum_head_error_units':errors['head'],'maximum_tail_error_units':errors['tail'],'mode':'whole_fin_root_offset' if bone in shifts else 'declared_point_field'}
    report={'schema_version':1,'ok':all(checks.values()),'status':'done' if all(checks.values()) else 'failed','next_action':'human_review','command':'volume.native-revision.preservation-audit','original_blend_sha256':digest(original),'candidate_blend_sha256':digest(candidate),'profile_sha256':digest(profile_path),'checks':checks,'vertical_change_declared':bool(vertical),'mesh_deformation':deformation,'bone_rest_deformation':bone_deformation,'bone_rest_tolerance_native_units':1e-7,'station_measurements':measurements,'notes':['Measurements use edge-plane intersections on native rest meshes; u is source-image coordinate, not a biological landmark by itself.','Lengths use full-model X bounds and profile total length.','Widths are finite-triangle interpolations; target station ratios can differ slightly between mesh rings.','Z changes pass only against the profile-declared affine map; undeclared Z must stay unchanged.','Bone rest heads/tails must match the declared field, with whole-root offsets for retained fin shapes; finite-coordinate tolerance is 1e-7 native units.','This audit applies only to native topology-preserving revisions. A procedural rebuild cannot claim preservation of intentionally rebuilt tail or fin meshes.','This audit does not approve anatomy or visual appearance.']}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('NATIVE_REVISION_AUDIT '+json.dumps({'ok':report['ok'],'checks':checks,'output':str(out)}))
    if not report['ok']:raise SystemExit(2)


if __name__=='__main__':main()
