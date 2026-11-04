"""Reshape only project cephalofoil thickness from declared coarse section data.

No external vertices, faces, UVs or contour curves enter this author. The project
XY outline, oral volume, all fins, rig and animation stay in their own source.
"""
import bpy
import bmesh
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform


def smooth(a,b,x):
    t=min(1.,max(0.,(x-a)/(b-a)));return t*t*(3-2*t)


def tree_for(ob):
    ob.data.calc_loop_triangles()
    return BVHTree.FromPolygons([v.co.copy() for v in ob.data.vertices],[tuple(t.vertices) for t in ob.data.loop_triangles],all_triangles=True,epsilon=1e-7)


def main():
    args=sys.argv[sys.argv.index('--')+1:];cp=Path(args[0]).resolve();out=Path(args[1]).resolve();c=json.loads(cp.read_text())
    assert '/experiments/' in out.as_posix() and not out.exists()
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert sha(c['baseline_blend'])==c['baseline_blend_sha256'];assert sha(c['reference_measurements'])==c['reference_measurements_sha256']
    bpy.ops.wm.open_mainfile(filepath=c['baseline_blend']);rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.scene.frame_set(1)
    body=bpy.data.objects[c['body']];oldtree=tree_for(body);old=np.array([v.co[:] for v in body.data.vertices]);old_triangles=[tuple(t.vertices) for t in body.data.loop_triangles];ref=json.loads(Path(c['project_reference']).read_text());rows=ref['head_transverse_stations'];ys=[r['y_m'] for r in rows];front=[r['front_x_m'] for r in rows];rear=[r['rear_x_m'] for r in rows];halfspan=ref['head_span_m']/2
    protected=set()
    oral_indices={i for i,m in enumerate(body.data.materials) if m.name==c['oral_material']}
    assert len(oral_indices)==1,'Freeze the actual oral material; slot numbers can change'
    for f in body.data.polygons:
        if f.material_index in oral_indices:protected.update(f.vertices)
    field = None
    if c.get('full_head_field'):
        fp=Path(c['full_head_field']); assert sha(fp)==c['full_head_field_sha256']
        field=json.loads(fp.read_text()); fieldrows=[r for r in field['rows'] if r['side']==1]
        fractions=[r['half_span_fraction'] for r in fieldrows]
        def field_height(f,t):
            hs=[]
            for r in fieldrows:
                hs.append(float(np.interp(t,[s['chord_fraction'] for s in r['samples']],[s['reference']['height'] for s in r['samples']])))
            return float(np.interp(f,fractions,hs))*c['whole_length_m']
    else:
        protected.update(i for i,p in enumerate(old) if abs(p[1])<=c['oral_protection']['half_width_m'] and p[0]<=c['oral_protection']['front_x_m'])
    def bounds(x,y):
        hi=oldtree.ray_cast(Vector((x,y,2)),Vector((0,0,-1)),4)[0];lo=oldtree.ray_cast(Vector((x,y,-2)),Vector((0,0,1)),4)[0]
        assert hi is not None and lo is not None,(x,y,'no finite vertical support')
        return lo.z,hi.z
    def mapping(p):
        x,y,z=p
        if field:
            a=float(np.interp(y,ys,front));b=float(np.interp(y,ys,rear))
            w=smooth(b-c['posterior_transition_m'],b,x)
        else:
            lat=smooth(*c['lateral_blend_m'],abs(y));nose=smooth(*c['anterior_blend_m'],x);w=max(lat,nose)*smooth(*c['neck_blend_m'],x)
        if w<=1e-10:return Vector(p)
        low,high=bounds(x,y);mid=(low+high)/2;depth=high-low
        if depth<1e-8:return Vector(p)
        a=float(np.interp(y,ys,front));b=float(np.interp(y,ys,rear));t=min(1.,max(0.,(a-x)/max(a-b,1e-5)))
        if field:
            target=field_height(abs(y)/halfspan,t)
            # Reference open throat is not a request to open the project's jaw.
            # Keep existing central posterior envelope wherever already thinner.
            if abs(y)/halfspan<.3:target=min(target,depth)
            target=max(c['minimum_edge_full_thickness_m'],target)
        else:
            peak=float(np.interp(abs(y)/halfspan,[v[0] for v in c['peak_thickness_over_length']],[v[1] for v in c['peak_thickness_over_length']]))*c['whole_length_m']
            bulb=smooth(*c['eye_end_span_fraction'],abs(y)/halfspan)
            edge=c['minimum_edge_full_thickness_m']*(1-bulb)+c['eye_end_minimum_full_thickness_m']*bulb
            target=edge+(max(peak,edge)-edge)*max(0.,math.sin(math.pi*t))**c['foil_exponent']
        depth2=depth*(1-w)+target*w
        return Vector((x,y,mid+(z-mid)*depth2/depth))
    changed=[]
    for v in body.data.vertices:
        if v.index in protected:continue
        q=mapping(v.co);delta=(q-v.co).length
        if delta>1e-9:changed.append({'id':v.index,'before':list(v.co),'after':list(q)});v.co=q
    assert len(changed)>=c['minimum_changed_body_vertices'],'No actual head repair; reject unchanged body'
    body.data.update();body.data.normals_split_custom_set([(0.,0.,0.)]*len(body.data.loops));newtree=tree_for(body)
    eyes=[]
    for name in c['eyes']:
        ob=bpy.data.objects[name];side=1 if np.mean([v.co.y for v in ob.data.vertices])>0 else -1
        cx=(min(v.co.x for v in ob.data.vertices)+max(v.co.x for v in ob.data.vertices))/2;cz=(min(v.co.z for v in ob.data.vertices)+max(v.co.z for v in ob.data.vertices))/2
        h=oldtree.ray_cast(Vector((cx,side,cz)),Vector((0,-side,0)),2)[0];assert h is not None
        # The external eye must keep its original painted footprint dimensions.
        # The declared terminal bulb provides support instead of flattening it
        # into the foil seam. Its lens covers the transported skin eye below.
        inset_y=h.y-side*c['eye_center_support_inset_m']
        hi=newtree.ray_cast(Vector((cx,inset_y,2)),Vector((0,0,-1)),4)[0]
        lo=newtree.ray_cast(Vector((cx,inset_y,-2)),Vector((0,0,1)),4)[0]
        assert hi is not None and lo is not None
        shift=(hi.z+lo.z)/2-cz;supports=[];shifts=[]
        for v in ob.data.vertices:
            oldh,oldn,oldfi,oldd=oldtree.ray_cast(Vector((v.co.x,side,v.co.z)),Vector((0,-side,0)),2);assert oldh is not None
            ids=old_triangles[oldfi];transport=barycentric_transform(oldh,*[Vector(old[i]) for i in ids],*[body.data.vertices[i].co for i in ids])
            offset=side*(v.co.y-oldh.y);shifts.append(shift);v.co.z+=shift
            h,n,fi,d=newtree.ray_cast(Vector((v.co.x,side,v.co.z)),Vector((0,-side,0)),2);assert h is not None and n.y*side>0,(name,v.index,'eye outside new support',list(v.co),list(h) if h is not None else None,list(n) if n is not None else None)
            v.co.y=h.y+side*offset;supports.append({'vertex':v.index,'support_triangle':fi,'signed_offset_m':offset,'body_hit':list(h)})
        ob.data.update();eyes.append({'name':name,'z_translation_m':float(np.mean(shifts)),'xz_size_and_native_UV_unchanged':True,'support_transport':'finite terminal bulb center; original eye X/Z dimensions and source pixels retained; actual lateral skin support per vertex','supports':supports})
    now=np.array([v.co[:] for v in body.data.vertices]);assert np.array_equal(now[:,:2],old[:,:2]);assert np.array_equal(now[list(protected)],old[list(protected)])
    bm=bmesh.new();bm.from_mesh(body.data);assert all(len(e.link_faces)==2 for e in bm.edges);assert bm.calc_volume()>0;bm.free()
    total=0
    for ob in bpy.context.scene.objects:
        if ob.type=='MESH':ob.data.calc_loop_triangles();total+=len(ob.data.loop_triangles)
    assert total==c['whole_triangles'] and total<=4000
    rig.data.pose_position='POSE';bpy.ops.object.select_all(action='DESELECT')
    for ob in bpy.context.scene.objects:
        if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
    bpy.context.view_layer.objects.active=body;out.mkdir();bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'))
    bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
    (out/'fin-authoring.json').write_bytes(Path(c['fin_authoring']).read_bytes())
    report={'ok':True,'kind':'project_hammerhead_thickness_section_author','formal_acceptance':False,'visual_review':'pending','config_sha256':sha(cp),'author_script_sha256':sha(__file__),'model_sha256':sha(out/'fish.glb'),'source_sha256':sha(out/'fish.blend'),'whole_triangles':total,'changed_body_vertices':changed,'protected_oral_vertices':len(protected),'oral_coordinates_exact':True,'project_XY_coordinates_exact':True,'fins_rig_animation_UV_materials_not_edited':True,'eyes':eyes,'basis':'Full finite head field, own outline and chord registration, central open-jaw envelope capped by project pose; no artificial eye-end thickness floor.' if field else 'Declared coarse game-model section ratios and analytic foil; project XY, topology, UVs and mouth retained. Not biological tissue thickness or copied library geometry.'}
    (out/'authoring.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'ok':True,'triangles':total,'changed_body_vertices':len(changed),'eyes':[{'name':e['name'],'z_shift':e['z_translation_m']} for e in eyes]}))


if __name__=='__main__':main()
