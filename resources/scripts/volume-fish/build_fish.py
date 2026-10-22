"""Foundry parameter-only native-texture fish reconstruction backend for Blender 4.5+.
Usage: blender --background --python build_fish.py -- handoff.json [--render-only]
The approved source pixels remain unchanged. No vendor/API calls or executable profile fields.
"""
import sys, json, math, hashlib, struct, traceback, array
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "cli"))
from volume_shape import validate_revision, revision_source, width_scale, vertical_position, validate_root_attachment, root_attachment_gain,root_attachment_inset,validate_fin_baseline,fin_baseline_parameter
from volume_mouth import validate_oral_jaws,validate_oral_context
sys.path.insert(0,str(Path(__file__).resolve().parent))
from oral_jaws import build_closed_oral_jaws
from separate_jaw import build_separate_lower_jaw,rig_lower_jaw
import bpy, bmesh
from mathutils import Vector, Quaternion
from mathutils.geometry import delaunay_2d_cdt
from mathutils.bvhtree import BVHTree


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(test, message):
    if not test: raise ValueError(message)
def number(v, lo, hi): return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and lo<=v<=hi
def keys(value, allowed, label):
    require(isinstance(value,dict) and not set(value)-set(allowed.split()),label+' has unknown fields')
def inside(pt,polygon):
    x,y=pt;yes=False
    for (ax,ay),(bx,by) in zip(polygon,polygon[1:]+polygon[:1]):
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:yes=not yes
    return yes

def fin_source_geometry(fin,aspect):
    """Constrain actual basal boundary subdivisions, instead of free slivers.

    A float32 interpolated point beside a long unsplit boundary can create an
    almost collinear CDT triangle; projecting that triangle to the body folds
    or collapses it. Internal authored baselines retain their existing meaning.
    """
    polygon=[Vector(v) for v in fin['polygon']];extra=[]
    for a,b in zip(fin.get('source_baseline',[]),fin.get('source_baseline',[])[1:]):
        va,vb=Vector(a),Vector(b)
        attachment=fin.get('root_attachment',{})
        spacing=attachment.get('baseline_spacing',.001 if attachment.get('surface_clearance') and not fin['paired'] else .004)
        count=max(1,math.ceil(math.hypot(b[0]-a[0],(b[1]-a[1])*aspect)/spacing))
        mids=[va.lerp(vb,j/count) for j in range(1,count)]
        for i in range(len(polygon)):
            left,right=polygon[i],polygon[(i+1)%len(polygon)]
            forward=(left-va).length<1e-7 and (right-vb).length<1e-7
            reverse=(left-vb).length<1e-7 and (right-va).length<1e-7
            if forward or reverse:
                polygon=polygon[:i+1]+(mids if forward else list(reversed(mids)))+polygon[i+1:]
                break
        else:extra.extend(mids)
    points=polygon+extra
    xmin=min(v[0] for v in polygon);xmax=max(v[0] for v in polygon);ymin=min(v[1] for v in polygon);ymax=max(v[1] for v in polygon)
    for i in range(1,13):
        for j in range(1,7):
            pt=[xmin+(xmax-xmin)*i/13,ymin+(ymax-ymin)*j/7]
            if inside(pt,polygon):points.append(Vector(pt))
    return polygon,points
def polygons_overlap(a,b):
    if any(inside(v,b) for v in a) or any(inside(v,a) for v in b):return True
    def cross(p,q,r):return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    for p,q in zip(a,a[1:]+a[:1]):
        for r,s in zip(b,b[1:]+b[:1]):
            if max(p[0],q[0])<min(r[0],s[0]) or max(r[0],s[0])<min(p[0],q[0]) or max(p[1],q[1])<min(r[1],s[1]) or max(r[1],s[1])<min(p[1],q[1]):continue
            if cross(p,q,r)*cross(p,q,s)<=0 and cross(r,s,p)*cross(r,s,q)<=0:return True
    return False

def head_vertical_offset(cap,u):
    rows=cap.get('vertical_offsets',[])
    if not rows:return 0.
    if u<=rows[0][0]:return rows[0][1]
    for a,b in zip(rows,rows[1:]):
        if a[0]<=u<=b[0]:
            t=(u-a[0])/(b[0]-a[0]);return a[1]+(b[1]-a[1])*t
    return rows[-1][1]
def uvpoint(p): return isinstance(p,list) and len(p)==2 and all(number(v,0,1) for v in p)
def validate_profile(p):
    keys(p,'schema_version species display_name coordinate_space source_aspect_ratio profile_review_status real_length_cm style body body_uv_patches head_projection dorsal_projection ventral_projection cephalofoil rest_shape_revision rig fins eyes barbels animation notes oral_jaws','profile')
    if 'oral_jaws' in p:
        validate_oral_jaws(p['oral_jaws'])
        require(not p.get('rest_shape_revision') and not p.get('cephalofoil') and (not p.get('head_projection') or p['head_projection'].get('continuous_atlas')),'Oral cleft requires longitudinal build and a continuous atlas when using multiple skin sources')
    if 'rest_shape_revision' in p:validate_revision(p['rest_shape_revision'])
    require(p['schema_version']==1 and p['coordinate_space']=='normalized_source_top_left','Unsupported profile coordinates/version')
    require(p['profile_review_status']=='approved','Profile landmarks need review: profile_review_status must be approved')
    require(number(p['real_length_cm'],.1,1000) and number(p['source_aspect_ratio'],.1,20),'Invalid length/aspect')
    style=p['style'];keys(style,'pixel_art reference_image texture_filter roughness','style')
    require(style['pixel_art'] is True and style['texture_filter']=='nearest' and style['roughness']==1,'Pixel style requires nearest, roughness 1')
    body=p['body'];keys(body,'sections rings radial','body'); sections=body['sections']
    require(4<=len(sections)<=128 and all(len(r)==4 and all(number(v,0,1) for v in r[:3]) and r[1]<r[2] and number(r[3],.0001,.3) for r in sections),'Invalid body sections')
    require(all(a[0]<b[0] for a,b in zip(sections,sections[1:])),'Sections must increase in source u')
    if p.get('cephalofoil'):
        head=p['cephalofoil'];keys(head,'sections center_v mouth','cephalofoil')
        require(number(head['center_v'],0,1) and 5<=len(head['sections'])<=64,'Invalid head sections')
        require(all(len(r)==4 and number(r[0],-.3,.3) and 0<=r[1]<r[2]<=1 and number(r[3],.001,.05) for r in head['sections']),'Invalid head geometry')
        require(all(a[0]<b[0] for a,b in zip(head['sections'],head['sections'][1:])),'Head sections must increase laterally')
    require(isinstance(body['rings'],int) and 16<=body['rings']<=256 and isinstance(body['radial'],int) and 12<=body['radial']<=96,'Invalid ring detail')
    for patch in p.get('body_uv_patches',[]):
        keys(patch,'polygon offset','body UV patch')
        require(3<=len(patch['polygon'])<=128 and all(uvpoint(v) for v in patch['polygon']) and len(patch['offset'])==2 and all(number(v,-1,1) for v in patch['offset']),'Invalid body UV patch')
    if p.get('head_projection'):
        cap=p['head_projection'];keys(cap,'start_u end_u normal_threshold side_limit source_rect model_depth_range model_v_range uv_patches continuous_atlas blend_end_u vertical_offsets','head projection')
        if 'vertical_offsets' in cap:
            rows=cap['vertical_offsets'];require(isinstance(rows,list) and 2<=len(rows)<=64 and all(isinstance(r,list) and len(r)==2 and number(r[0],0,1) and number(r[1],-.2,.2) for r in rows) and all(a[0]<b[0] for a,b in zip(rows,rows[1:])),'Invalid head vertical offsets')
        require(type(cap.get('continuous_atlas',False)) is bool and not (cap.get('continuous_atlas') and p.get('cephalofoil')),'Continuous atlas requires boolean flag and longitudinal body')
        if 'blend_end_u' in cap:require(cap.get('continuous_atlas') and number(cap['blend_end_u'],0,1) and min(cap['start_u'],cap['end_u'])<cap['blend_end_u']<=p['body']['sections'][-1][0],'Invalid continuous head blend interval')
        require(all(number(cap[k],0,1) for k in ['start_u','end_u']) and cap['start_u']!=cap['end_u'],'Invalid head interval')
        rect=cap['source_rect'];require(len(rect)==4 and all(number(v,0,1) for v in rect) and rect[0]<rect[2] and rect[1]<rect[3],'Invalid front source rectangle')
        depth=cap['model_depth_range'];require(len(depth)==2 and all(number(v,-.5,.5) for v in depth) and depth[0]<depth[1],'Invalid front depth range')
        vr=cap['model_v_range'];require(uvpoint(vr) and vr[0]<vr[1],'Invalid front model height range')
        require(number(cap['normal_threshold'],-1,.95) and number(cap['side_limit'],.1,1),'Invalid head projection facing limits')
        patches=cap.get('uv_patches',[]);require(isinstance(patches,list) and len(patches)<=16,'Too many front UV patches')
        for patch in patches:
            keys(patch,'polygon offset','front UV patch');polygon=patch['polygon'];offset=patch['offset']
            require(3<=len(polygon)<=128 and all(uvpoint(v) for v in polygon) and len(offset)==2 and all(number(v,-1,1) for v in offset),'Invalid front UV patch')
            require(all(uvpoint([v[0]+offset[0],v[1]+offset[1]]) for v in polygon),'Front UV donor leaves source bounds')
    for projection_name in ['dorsal_projection','ventral_projection']:
        if not p.get(projection_name):continue
        surface=p[projection_name];keys(surface,'start_u end_u normal_threshold source_rect model_depth_range head_source_rect sections',projection_name)
        if surface.get('sections'):
            rows=surface['sections']
            require(4<=len(rows)<=128 and all(len(r)==5 and all(number(v,0,1) for v in r) and r[2]<r[3] and number(r[4],.0001,.3) for r in rows),'Invalid surface correspondence sections')
            require(all(a[0]<b[0] for a,b in zip(rows,rows[1:])),'Surface correspondence must increase')
        require(all(number(surface[k],0,1) for k in ['start_u','end_u']) and surface['start_u']!=surface['end_u'],'Invalid surface interval')
        rect=surface['source_rect'];require(len(rect)==4 and all(number(v,0,1) for v in rect) and rect[0]<rect[2] and rect[1]<rect[3],'Invalid surface source rectangle')
        depth=surface['model_depth_range'];require(len(depth)==2 and all(number(v,-.5,.5) for v in depth) and depth[0]<depth[1],'Invalid surface depth range')
        require(number(surface['normal_threshold'],0,.95),'Invalid surface projection normal threshold')
    keys(p['rig'],'spine','rig');spine=p['rig']['spine']
    require(4<=len(spine)<=32 and all(uvpoint(v) for v in spine),'Invalid spine')
    require(all(a[0]<b[0] for a,b in zip(spine,spine[1:])) or all(a[0]>b[0] for a,b in zip(spine,spine[1:])),'Spine must consistently run head to tail')
    if p.get('oral_jaws'):validate_oral_context(p['oral_jaws'],body,spine)
    require(len(p['fins'])<=32,'Too many fins')
    fin_names=[f.get('name','')+suffix for f in p['fins'] for suffix in (['_left','_right'] if f.get('paired') else [''])]
    require(len(set(fin_names))==len(fin_names) and all(n!='root' and not n.startswith('body_') for n in fin_names),'Duplicate or reserved fin names')
    for f in p['fins']:
        keys(f,'name polygon anchor tip paired root_depth tip_depth thickness amplitude phase axis vertical_scale opaque source_rect root_attachment source_baseline','fin')
        if f.get('source_baseline'):validate_fin_baseline(f['source_baseline'])
        if 'root_attachment' in f:
            require('rest_shape_revision' not in p or f.get('paired') is True,'Native root_attachment supports authored paired fin roots only')
            validate_root_attachment(f['root_attachment'])
            require(not f.get('paired') or 'root_band_depth' not in f['root_attachment'],'Finite collar depth is for median fins; paired roots retain their two-dimensional flank mapping')
        require(number(f.get('vertical_scale',1),0,1) and isinstance(f.get('opaque',False),bool),'Invalid fin geometry options')
        require(isinstance(f['name'],str) and f['name'] and len(f['name'])<80,'Invalid fin name')
        require(3<=len(f['polygon'])<=128 and all(uvpoint(v) for v in f['polygon']) and uvpoint(f['anchor']) and uvpoint(f['tip']),'Invalid fin landmarks')
        require(isinstance(f['paired'],bool) and number(f['root_depth'],0,.3) and number(f['tip_depth'],0,.5) and number(f['thickness'],.0001,.02),'Invalid fin depth')
        require(number(f['amplitude'],0,.5) and number(f['phase'],-20,20),'Invalid fin movement')
        require(len(f['axis'])==3 and all(number(v,-1,1) for v in f['axis']) and Vector(f['axis']).length>.1,'Invalid fin axis')
    if p['eyes'] is not None:
        e=p['eyes'];keys(e,'center radius depth mode source_rect thickness surface_offset source_uv','eyes')
        require(uvpoint(e['center']) and number(e['radius'],.001,.05) and number(e['depth'],.001,.2),'Invalid eyes')
        if 'mode' in e:
            require(e['mode']=='surface_patch','Invalid eye mode')
            rect=e['source_rect'];require(len(rect)==4 and all(number(v,0,1) for v in rect) and rect[0]<rect[2] and rect[1]<rect[3],'Invalid eye source rectangle')
            require(number(e['thickness'],.0001,.01) and number(e['surface_offset'],0,.003),'Invalid eye patch depth')
            height=e['radius']*((rect[3]-rect[1])/(rect[2]-rect[0]))/p['source_aspect_ratio']
            require(number(height,0,.05) and height>0,'Derived eye patch half-height exceeds geometry budget')
        else:require(not any(k in e for k in ['source_rect','thickness','surface_offset']),'Eye patch fields require surface_patch mode')
    require(len(p['barbels'])<=8,'Too many barbels')
    for b in p['barbels']:
        keys(b,'name path radius','barbel')
        require(2<=len(b['path'])<=64 and all(len(v)==3 and uvpoint(v[:2]) and number(v[2],-.5,.5) for v in b['path']) and number(b['radius'],.0001,.01),'Invalid barbels')
    a=p['animation'];keys(a,'fps period_seconds body_amplitudes phase_step','animation')
    require(isinstance(a['fps'],int) and 12<=a['fps']<=60 and number(a['period_seconds'],.5,10) and number(a['phase_step'],0,3),'Invalid animation')
    require(len(a['body_amplitudes'])==len(spine) and all(number(v,0,.5) for v in a['body_amplitudes']),'Invalid body amplitudes')


def binary_inspect(path):
    data=Path(path).read_bytes(); require(data[:4]==b'glTF','Invalid GLB magic')
    size=struct.unpack_from('<I',data,12)[0]; doc=json.loads(data[20:20+size]); binary=data[28+size:]
    def values(idx):
        a=doc['accessors'][idx]; view=doc['bufferViews'][a['bufferView']]
        count={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
        fmt={5126:'f',5125:'I',5123:'H',5121:'B'}[a['componentType']]; step=struct.calcsize(fmt)*count
        off=view.get('byteOffset',0)+a.get('byteOffset',0);stride=view.get('byteStride',step)
        return [struct.unpack_from('<'+fmt*count,binary,off+i*stride) for i in range(a['count'])]
    total=0;bad=0
    for i,a in enumerate(doc['accessors']):
        if a['componentType']==5126:
            for row in values(i):
                total+=len(row);bad+=sum(not math.isfinite(v) for v in row)
    tracks=[]
    for a in doc.get('animations',[]):
        for c in a['channels']:
            if c['target']['path']!='rotation':continue
            rows=values(a['samplers'][c['sampler']]['output'])
            tracks.append({'bone':doc['nodes'][c['target']['node']]['name'],'max_change':max(max(abs(x-y) for x,y in zip(row,rows[0])) for row in rows),'seam_delta':max(abs(x-y) for x,y in zip(rows[0],rows[-1]))})
    nearest=all(s.get('magFilter')==9728 and s.get('minFilter')==9728 for s in doc.get('samplers',[])) and bool(doc.get('samplers'))
    rough=all(m.get('pbrMetallicRoughness',{}).get('metallicFactor',1)==0 and m.get('pbrMetallicRoughness',{}).get('roughnessFactor',1)==1 for m in doc.get('materials',[]))
    return {'finite_components':total,'nonfinite_components':bad,'animation_tracks':tracks,'nearest':nearest,'roughness':rough,'images_embedded':all('bufferView' in i for i in doc.get('images',[])),'animations':[a.get('name') for a in doc.get('animations',[])]}


def export_native(outputs,rig,meshes):
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    for o in meshes:o.select_set(True)
    bpy.context.view_layer.objects.active=rig;bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(outputs['blend']))
    bpy.ops.export_scene.gltf(filepath=str(outputs['glb']),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIVE_ACTIONS',export_frame_range=True,export_force_sampling=True,export_skins=True,export_materials='EXPORT',export_apply=False,export_yup=True)
    # Blender chooses nearest mipmaps by default. Pixel-art contract forbids mip interpolation.
    raw=outputs['glb'].read_bytes();size=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+size])
    for sampler in doc.get('samplers',[]):sampler.update(magFilter=9728,minFilter=9728)
    encoded=json.dumps(doc,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
    tail=raw[20+size:];outputs['glb'].write_bytes(struct.pack('<4sII',b'glTF',2,20+len(encoded)+len(tail))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+tail)


def build(h,p,source,outputs):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    image=bpy.data.images.load(str(source),check_existing=False);image.pack();W,H=image.size[:];aspect=H/W
    require(16<=W<=8192 and 16<=H<=8192 and W*H<=32000000,'Source image dimensions out of range')
    pixels=array.array('f',[0])*(W*H*4);image.pixels.foreach_get(pixels)
    require(any(a<.1 for a in pixels[3::4]) and any(a>.9 for a in pixels[3::4]),'Source must contain transparent background and opaque fish')
    uv_edge_repairs=0
    def opaque_uv(u,v,towards):
        nonlocal uv_edge_repairs
        original=v
        for step in range(65):
            x=min(W-1,max(0,int(u*W)));y=min(H-1,max(0,int((1-v)*H)))
            if pixels[(y*W+x)*4+3]>=.85:
                if step:uv_edge_repairs+=1
                return (u,v)
            v=original+(1 if towards>original else -1)*(step+1)/H
        raise ValueError('Body UV cannot find opaque source pixels: review contour profile')
    require(abs(W/H/p['source_aspect_ratio']-1)<.02,'Source aspect differs from approved profile; review landmarks')
    scene=bpy.context.scene;scene.render.fps=p['animation']['fps']; frames=round(scene.render.fps*p['animation']['period_seconds'])
    scene.frame_start=0;scene.frame_end=frames
    def xyz(u,v,depth=0):return Vector((u-.5,depth,(.5-v)*aspect))
    def uv(co):return (co.x+.5,.5+co.z/aspect)
    mat=bpy.data.materials.new('Native pixel art · nearest · matte');mat.use_nodes=True
    # Node display names are localized in Blender 5, so resolve by stable node type.
    bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bsdf.inputs['Metallic'].default_value=0;bsdf.inputs['Roughness'].default_value=1;bsdf.inputs['Specular IOR Level'].default_value=0
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image;tex.interpolation='Closest';tex.extension='EXTEND'
    mat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color']);mat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Emission Color']);bsdf.inputs['Emission Strength'].default_value=.35
    finmat=mat.copy();finmat.name='Native pixel fins · alpha silhouette'
    fintex=next(n for n in finmat.node_tree.nodes if n.type=='TEX_IMAGE')
    fin_bsdf=next(n for n in finmat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    finmat.node_tree.links.new(fintex.outputs['Alpha'],fin_bsdf.inputs['Alpha']);finmat.surface_render_method='DITHERED'
    front_image=None;frontmat=None;front_face_count=0
    if p.get('head_projection'):
        require(bool(h.get('front_source_image')),'head_projection requires accepted front_source_image')
        front_image=bpy.data.images.load(h['front_source_image'],check_existing=False);front_image.pack()
        FW,FH=front_image.size[:];require(16<=FW<=8192 and 16<=FH<=8192 and FW*FH<=32000000,'Front source dimensions out of range')
        frontmat=mat.copy();frontmat.name='Accepted frontal pixel art · native nearest'
        next(n for n in frontmat.node_tree.nodes if n.type=='TEX_IMAGE').image=front_image
    surface_images={};surface_materials={};surface_face_counts={'top':0,'bottom':0}
    for label,projection in [('top','dorsal_projection'),('bottom','ventral_projection')]:
        if not p.get(projection):continue
        key=label+'_source_image';require(bool(h.get(key)),projection+' requires accepted '+key)
        source=bpy.data.images.load(h[key],check_existing=False);source.pack();sw,sh=source.size[:]
        require(16<=sw<=8192 and 16<=sh<=8192 and sw*sh<=32000000,label.capitalize()+' source dimensions out of range')
        material=mat.copy();material.name='Accepted '+label+' pixel art · native nearest'
        next(n for n in material.node_tree.nodes if n.type=='TEX_IMAGE').image=source
        surface_images[label]=source;surface_materials[label]=material
    arm=bpy.data.armatures.new(p['species']+'_Skeleton');rig=bpy.data.objects.new(p['species']+'_Rig',arm);scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    root=arm.edit_bones.new('root');root.head=(0,0,0);root.tail=(0,0,.03)
    spine=p['rig']['spine'];names=[]
    for i,point in enumerate(spine):
        b=arm.edit_bones.new('body_%02d'%i);b.head=xyz(*point)
        b.tail=xyz(*(spine[i+1] if i+1<len(spine) else [point[0]+(point[0]-spine[i-1][0])*.4,point[1]]))
        b.parent=arm.edit_bones[names[-1]] if names else root;names.append(b.name)
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    def weights(u):
        ordered=sorted(zip([v[0] for v in spine],names))
        if u<=ordered[0][0]:return {ordered[0][1]:1}
        if u>=ordered[-1][0]:return {ordered[-1][1]:1}
        for (a,na),(b,nb) in zip(ordered,ordered[1:]):
            if a<=u<=b:
                t=(u-a)/(b-a);return {na:1-t,nb:t}
    meshes=[];fin_motion=[]
    surface_pixels={label:list(source.pixels[:]) for label,source in surface_images.items()}
    surface_columns={}
    surface_rows={}
    front_pixels=list(front_image.pixels[:]) if front_image else None
    front_columns={}
    def frontal_uv(u,v):
        x=max(0,min(FW-1,int(u*FW)))
        if x not in front_columns:
            r=p['head_projection']['source_rect']
            ys=[y for y in range(int((1-r[3])*FH),int((1-r[1])*FH)) if front_pixels[(y*FW+x)*4+3]>.95]
            require(bool(ys),'Front head donor column has no opaque pixels')
            front_columns[x]=(min(ys)+2,max(ys)-2)
        low,high=front_columns[x];r=p['head_projection']['source_rect']
        t=max(0,min(1,(v-r[1])/(r[3]-r[1])))
        y=high-(high-low)*t
        return ((x+.5)/FW,(y+.5)/FH)
    fin_columns={}
    def fin_uv(u,v):
        x=max(0,min(W-1,int(u*W)))
        if x not in fin_columns:fin_columns[x]=[y for y in range(H) if pixels[(y*W+x)*4+3]>.9]
        rows=fin_columns[x];require(bool(rows),'Fin donor column has no opaque pixels')
        y=max(0,min(H-1,int((1-v)*H)))
        if pixels[(y*W+x)*4+3]<.9:y=min(rows,key=lambda a:abs(a-y))
        return ((x+.5)/W,(y+.5)/H)
    def surface_uv(label,u,v):
        source=surface_images[label];sw,sh=source.size[:];x=max(0,min(sw-1,int(u*sw)))
        cache_key=(label,x)
        if cache_key not in surface_columns:
            px=surface_pixels[label]
            surface_columns[cache_key]=[y for y in range(sh) if px[(y*sw+x)*4+3]>.9]
        rows=surface_columns[cache_key]
        require(bool(rows),'Surface donor column has no opaque pixels')
        y=max(0,min(sh-1,int((1-v)*sh)))
        if surface_pixels[label][(y*sw+x)*4+3]<.9:y=min(rows,key=lambda a:abs(a-y))
        return ((x+.5)/sw,(y+.5)/sh)
    def surface_section(rows,u):
        if u<=rows[0][0]:return rows[0][1:]
        for a,b in zip(rows,rows[1:]):
            if a[0]<=u<=b[0]:
                t=(u-a[0])/(b[0]-a[0]);return [x*(1-t)+y*t for x,y in zip(a[1:],b[1:])]
        return rows[-1][1:]
    def head_surface_uv(label,co,surface):
        rect=surface['head_source_rect'];dr=surface['model_depth_range']
        source=surface_images[label];sw,sh=source.size[:]
        depth=max(dr[0],min(dr[1],co.y))
        sv=rect[1]+(depth-dr[0])/(dr[1]-dr[0])*(rect[3]-rect[1])
        # Terminal eyes are separate surface patches. Keep their baked
        # dorsal/ventral copies out of the head pigment projection.
        sv=max(rect[1]+.08*(rect[3]-rect[1]),min(rect[3]-.08*(rect[3]-rect[1]),sv))
        sy=max(0,min(sh-1,int((1-sv)*sh)));key=(label,sy)
        if key not in surface_rows:
            px=surface_pixels[label]
            xs=[x for x in range(int(rect[0]*sw),min(sw,int(rect[2]*sw))) if px[(sy*sw+x)*4+3]>.95]
            require(bool(xs),'Head donor row has no opaque silhouette')
            surface_rows[key]=(min(xs)+2,max(xs)-2)
        left,right=surface_rows[key]
        rear,front,_=surface_section(p['cephalofoil']['sections'],depth)
        t=max(0,min(1,(co.x+.5-rear)/(front-rear)))
        # Source silhouette ink belongs to the outline. Do not stretch it
        # across the rounded leading edge of the solid cephalofoil.
        t=.08+.84*t
        return ((left+(right-left)*t+.5)/sw,(sy+.5)/sh)
    def mesh(name,verts,faces,uvs,ws,thickness=0,opaque=False,source_parameters=None):
        nonlocal front_face_count,surface_face_counts
        data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update();obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);data.materials.append(finmat if thickness and not opaque else mat)
        layer=data.uv_layers.new(name='NativeSourceUV')
        for poly in data.polygons:
            poly.use_smooth=True
            for li in poly.loop_indices:layer.data[li].uv=uvs[data.loops[li].vertex_index]
        for i,w in enumerate(ws):
            for n,value in w.items():
                if value>1e-8:(obj.vertex_groups.get(n) or obj.vertex_groups.new(name=n)).add([i],value/sum(w.values()),'REPLACE')
        if source_parameters is not None:
            attribute=data.attributes.new('foundry_fin_source_t','FLOAT','POINT')
            for i,value in enumerate(source_parameters):attribute.data[i].value=value
        bpy.context.view_layer.objects.active=obj;obj.select_set(True)
        if thickness:
            mod=obj.modifiers.new('Closed fin membrane','SOLIDIFY');mod.thickness=thickness;mod.offset=0;bpy.ops.object.modifier_apply(modifier=mod.name)
        bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
        if frontmat and (name=='Cephalofoil' or (name=='Closed_body' and not p.get('cephalofoil'))):
            data.materials.append(frontmat);layer=data.uv_layers.active;cap=p['head_projection']
            head_sign=1 if spine[0][0]>spine[-1][0] else -1
            for poly in data.polygons:
                center=sum((data.vertices[i].co for i in poly.vertices),Vector())/len(poly.vertices);u=center.x+.5
                if name=='Cephalofoil' or (min(cap['start_u'],cap['end_u'])<=u<=max(cap['start_u'],cap['end_u']) and poly.normal.x*head_sign>=cap['normal_threshold'] and abs(poly.normal.y)<=cap['side_limit']):
                    poly.material_index=1;front_face_count+=1
                    rect=cap['source_rect'];dr=cap['model_depth_range'];vr=cap['model_v_range']
                    projected=[]
                    for li in poly.loop_indices:
                        co=data.vertices[data.loops[li].vertex_index].co
                        side=max(0,min(1,(co.y*head_sign-dr[0])/(dr[1]-dr[0])))
                        high=max(0,min(1,((.5-co.z/aspect)+head_vertical_offset(cap,co.x+.5)-vr[0])/(vr[1]-vr[0])))
                        projected.append((rect[0]+side*(rect[2]-rect[0]),rect[1]+high*(rect[3]-rect[1])))
                    # A donor is a face-level UV island. Mixing donor and original
                    # corners would interpolate back through the removed pigment.
                    offset=(0,0)
                    for patch in cap.get('uv_patches',[]):
                        if polygons_overlap(projected,patch['polygon']):
                            offset=patch['offset'];break
                    for li,(tu,tv) in zip(poly.loop_indices,projected):
                        tu+=offset[0];tv+=offset[1]
                        require(0<=tu<=1 and 0<=tv<=1,'Front UV donor left source bounds')
                        layer.data[li].uv=frontal_uv(tu,tv) if name=='Cephalofoil' else (tu,1-tv)
        if name in ('Closed_body','Cephalofoil') and surface_materials:
            material_indices={}
            for label,material in surface_materials.items():
                data.materials.append(material);material_indices[label]=len(data.materials)-1
            layer=data.uv_layers.active
            for label,projection,normal_sign in [('top','dorsal_projection',1),('bottom','ventral_projection',-1)]:
                if label not in surface_materials:continue
                surface=p[projection];rect=surface.get('head_source_rect',surface['source_rect']) if name=='Cephalofoil' else surface['source_rect'];dr=surface['model_depth_range']
                for poly in data.polygons:
                    center=sum((data.vertices[i].co for i in poly.vertices),Vector())/len(poly.vertices);u=center.x+.5
                    if name=='Cephalofoil' and abs(poly.normal.y)>.85:continue
                    threshold=0 if name=='Cephalofoil' else surface['normal_threshold']
                    if min(surface['start_u'],surface['end_u'])<=u<=max(surface['start_u'],surface['end_u']) and poly.normal.z*normal_sign>=threshold:
                        poly.material_index=material_indices[label];surface_face_counts[label]+=1
                        for li in poly.loop_indices:
                            co=data.vertices[data.loops[li].vertex_index].co;tu=co.x+.5
                            if name=='Cephalofoil':
                                layer.data[li].uv=head_surface_uv(label,co,surface)
                                continue
                            if name=='Cephalofoil':
                                rows=p['cephalofoil']['sections'];start=min(r[1] for r in rows);end=max(r[2] for r in rows)
                            else:start=p['body']['sections'][0][0];end=p['body']['sections'][-1][0]
                            along=max(0,min(1,(tu-start)/(end-start)))
                            if name=='Closed_body' and surface.get('sections'):
                                su,low,high,half_depth=surface_section(surface['sections'],tu)
                                across=max(0,min(1,(co.y/half_depth+1)/2))
                                # Leave a few source pixels inside the silhouette;
                                # retain the full longitudinal pigment/shading field.
                                inset=3/surface_images[label].size[1]
                                sv=(low+inset)+(high-low-2*inset)*across
                            else:
                                across=max(0,min(1,(co.y-dr[0])/(dr[1]-dr[0])))
                                su=rect[0]+along*(rect[2]-rect[0]);sv=rect[1]+across*(rect[3]-rect[1])
                            layer.data[li].uv=surface_uv(label,su,sv)
        mod=obj.modifiers.new('Swim skin','ARMATURE');mod.object=rig;obj.parent=rig;obj.select_set(False);meshes.append(obj);return obj
    def section(u):
        rows=p['body']['sections']
        if u<=rows[0][0]:return rows[0][1:]
        for a,b in zip(rows,rows[1:]):
            if a[0]<=u<=b[0]:
                t=(u-a[0])/(b[0]-a[0]);return [x*(1-t)+y*t for x,y in zip(a[1:],b[1:])]
        return rows[-1][1:]
    verts=[];faces=[];coords=[];ws=[];N=p['body']['rings'];R=p['body']['radial'];lo=p['body']['sections'][0][0];hi=p['body']['sections'][-1][0]
    for i in range(N):
        u=lo+(hi-lo)*i/(N-1);top,bottom,depth=section(u)
        for j in range(R):
            angle=math.tau*j/R;v=(top+bottom)/2-(bottom-top)/2*math.cos(angle)
            verts.append(xyz(u,v,depth*math.sin(angle)))
            inset=min(12/H,(bottom-top)*.20)
            tu,tv=u,max(top+inset,min(bottom-inset,v))
            for patch in p.get('body_uv_patches',[]):
                if inside([tu,tv],patch['polygon']):
                    tu+=patch['offset'][0];tv+=patch['offset'][1];break
            require(0<=tu<=1 and 0<=tv<=1,'Body donor UV left source bounds')
            tu,tv=opaque_uv(tu,tv,(top+bottom)/2)
            coords.append((tu,1-tv));ws.append(weights(u))
            if i:
                a=(i-1)*R+j;b=(i-1)*R+(j+1)%R;faces.append((a,b,b+R,a+R))
    faces += [tuple(reversed(range(R))),tuple((N-1)*R+j for j in range(R))]
    body_object=mesh('Closed_body',verts,faces,coords,ws)
    continuous_atlas_metrics=None
    if p.get('head_projection',{}).get('continuous_atlas'):
        # Freeze the side/front mixture into one native-resolution head atlas.
        # A face-normal material switch breaks painted lips when the snout changes.
        # Interpolate in surface coordinates instead; the anterior cap uses the
        # same frontal UV mapping as the final atlas column.
        cap=p['head_projection'];start=min(cap['start_u'],cap['end_u']);end=cap.get('blend_end_u',hi)
        head_sign=1 if spine[0][0]>spine[-1][0] else -1
        require(start<end and front_image is not None,'Continuous atlas needs an anterior frontal donor')
        atlas_pixels=array.array('f',[0])*(W*H*4)
        rect=cap['source_rect'];dr=cap['model_depth_range'];vr=cap['model_v_range']
        angular=[(math.cos(math.tau*(y+.5)/H),math.sin(math.tau*(y+.5)/H)) for y in range(H)]
        def sample_rgba(values,width,height,u,v):
            x=max(0,min(width-1,int(u*width)));y=max(0,min(height-1,int((1-v)*height)))
            at=(y*width+x)*4;return values[at:at+3]
        clean_metrics=None
        head_front_pixels=front_pixels
        if p.get('oral_jaws'):
            # Remove the obsolete painted lip line from one declared derivative.
            # Use the same texels for the cap and side atlas. Preserve some native
            # skin pixel variation from the adjacent donor strip, rather than
            # replacing the whole chin with a flat gradient.
            low,high=p['oral_jaws']['front_pigment_band']
            clean_pixels=array.array('f',front_pixels)
            for cy in range(FH):
                fv=1-(cy+.5)/FH
                if not low<fv<high:continue
                t=(fv-low)/(high-low)
                for cx in range(FW):
                    fu=(cx+.5)/FW
                    above=sample_rgba(front_pixels,FW,FH,fu,low)
                    below=sample_rgba(front_pixels,FW,FH,fu,high)
                    donor=sample_rgba(front_pixels,FW,FH,fu,low-.04+((fv-low)%.04))
                    donor_base=sample_rgba(front_pixels,FW,FH,fu,low-.02)
                    color=[max(0,min(1,a+(b-a)*t+.45*math.sin(math.pi*t)*(d-c))) for a,b,d,c in zip(above,below,donor,donor_base)]
                    at=(cy*FW+cx)*4;clean_pixels[at:at+3]=array.array('f',color)
            clean=bpy.data.images.new('Frontal skin - old painted mouth removed',width=FW,height=FH,alpha=True)
            clean.pixels.foreach_set(clean_pixels)
            clean_path=outputs['blend'].parent/'front-skin.png';clean.filepath_raw=str(clean_path);clean.file_format='PNG';clean.save();clean.pack()
            cleanmat=frontmat.copy();cleanmat.name='Frontal skin around geometric oral cleft'
            next(n for n in cleanmat.node_tree.nodes if n.type=='TEX_IMAGE').image=clean
            data=body_object.data
            bm=bmesh.new();bm.from_mesh(data);bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>4]);bm.to_mesh(data);bm.free()
            data.materials.append(cleanmat);clean_index=len(data.materials)-1
            # Untouched forehead triangles continue using the original donor.
            for poly in data.polygons:
                if len(poly.vertices)==3 and poly.material_index==1:
                    values=[1-data.uv_layers.active.data[li].uv.y for li in poly.loop_indices]
                    if max(values)>low and min(values)<high:poly.material_index=clean_index
            head_front_pixels=clean_pixels
            clean_metrics={'path':str(clean_path),'sha256':sha(clean_path),'size':[FW,FH],'source_front_sha256':sha(Path(h['front_source_image'])),'band':[low,high],'method':'Linear boundary color plus adjacent native skin pixel residual; same derivative sampled by cap and atlas.'}
        for x in range(max(0,int((start-.025)*W)),W):
            u=min(hi,(x+.5)/W);top,bottom,depth=section(u)
            blend=max(0,min(1,(u-start)/(end-start)));blend=blend*blend*(3-2*blend)
            for y,(cosine,sine) in enumerate(angular):
                v=(top+bottom)/2-(bottom-top)/2*cosine
                inset=min(12/H,(bottom-top)*.20);tu,tv=u,max(top+inset,min(bottom-inset,v))
                for patch in p.get('body_uv_patches',[]):
                    if inside([tu,tv],patch['polygon']):
                        tu+=patch['offset'][0];tv+=patch['offset'][1];break
                tu,tv=opaque_uv(tu,tv,(top+bottom)/2)
                side_color=sample_rgba(pixels,W,H,tu,tv)
                across=max(0,min(1,(depth*sine*head_sign-dr[0])/(dr[1]-dr[0])))
                high=max(0,min(1,(v+head_vertical_offset(cap,u)-vr[0])/(vr[1]-vr[0])))
                fu=rect[0]+across*(rect[2]-rect[0]);fv=rect[1]+high*(rect[3]-rect[1])
                front_color=sample_rgba(head_front_pixels,FW,FH,fu,fv)
                at=(y*W+x)*4
                atlas_pixels[at:at+4]=array.array('f',[a+(b-a)*blend for a,b in zip(side_color,front_color)]+[1])
        atlas=bpy.data.images.new('Continuous head atlas - derived from reviewed side and front',width=W,height=H,alpha=True)
        atlas.pixels.foreach_set(atlas_pixels)
        atlas_path=outputs['blend'].parent/'head-atlas.png';atlas.filepath_raw=str(atlas_path);atlas.file_format='PNG';atlas.save();atlas.pack()
        atlasmat=mat.copy();atlasmat.name='Continuous head pixels - baked side-front transition'
        next(n for n in atlasmat.node_tree.nodes if n.type=='TEX_IMAGE').image=atlas
        data=body_object.data;data.materials.append(atlasmat);atlas_index=len(data.materials)-1;layer=data.uv_layers.active
        atlas_faces=0
        for poly in data.polygons:
            if len(poly.vertices)!=4:continue # anterior cap retains exact front projection
            center_u=sum(data.vertices[i].co.x+.5 for i in poly.vertices)/len(poly.vertices)
            if center_u<start:continue
            if p.get('oral_jaws') and center_u>=end:
                projected=[]
                for li in poly.loop_indices:
                    co=data.vertices[data.loops[li].vertex_index].co
                    across=max(0,min(1,(co.y*head_sign-dr[0])/(dr[1]-dr[0])))
                    high_v=max(0,min(1,(.5-co.z/aspect+head_vertical_offset(cap,co.x+.5)-vr[0])/(vr[1]-vr[0])))
                    projected.append((rect[0]+across*(rect[2]-rect[0]),rect[1]+high_v*(rect[3]-rect[1])))
                low,high=p['oral_jaws']['front_pigment_band']
                if max(v for u,v in projected)<=low or min(v for u,v in projected)>=high:
                    poly.material_index=1
                    for li,(tu,tv) in zip(poly.loop_indices,projected):layer.data[li].uv=(tu,1-tv)
                    continue
            poly.material_index=atlas_index;atlas_faces+=1
            angular_indices=[data.loops[li].vertex_index%R for li in poly.loop_indices]
            wraps=0 in angular_indices and R-1 in angular_indices
            for li in poly.loop_indices:
                i=data.loops[li].vertex_index;j=i%R
                layer.data[li].uv=(data.vertices[i].co.x+.5,1. if wraps and j==0 else j/R)
        continuous_atlas_metrics={'path':str(atlas_path),'sha256':sha(atlas_path),'size':[W,H],'source_side_sha256':sha(source),'source_front_sha256':sha(Path(h['front_source_image'])),'baked_faces':atlas_faces,'method':'Nearest source sampling; spatial smoothstep color blend into a packed atlas; no face-normal material switch in head band. Derived texels, not unmodified source pixels.'}
        if clean_metrics:continuous_atlas_metrics['front_skin']=clean_metrics
    oral_metrics=None
    if p.get('oral_jaws'):
        if p['oral_jaws'].get('separate_lower'):
            jaw,oral_metrics=build_separate_lower_jaw(body_object,p['oral_jaws'],p['head_projection'],aspect,weights,head_vertical_offset,section,p.get('body_uv_patches',[]))
            for oral_obj in [jaw]+[bpy.data.objects[name] for name in jaw.get('oral_web_names',[])]:
                oral_obj.parent=rig;mod=oral_obj.modifiers.new('Swim skin','ARMATURE');mod.object=rig;meshes.append(oral_obj)
            rig_lower_jaw(rig,jaw,p['oral_jaws'],aspect,weights)
            if p['oral_jaws'].get('articulation'):
                oral_metrics['articulated_jaw']=True
                oral_metrics['articulation']=p['oral_jaws']['articulation']
                oral_metrics['jaw_bone']='jaw_lower'
        else:oral_metrics=build_closed_oral_jaws(body_object,p['oral_jaws'],aspect,weights)
    if p.get('cephalofoil'):
        head=p['cephalofoil'];control=head['sections'];rows=[]
        for i in range(97):
            y=control[0][0]+(control[-1][0]-control[0][0])*i/96
            rows.append([y,*surface_section(control,y)])
        vs=[];fs=[];uvs=[];wts=[];radial=64
        # Sweep laterally, rather than widening longitudinal body rings. Each
        # section supplies independent leading/trailing edges and thickness.
        for i,(depth,rear,front,height) in enumerate(rows):
            for j in range(radial):
                angle=math.tau*j/radial;u=(rear+front)/2+(front-rear)/2*math.cos(angle)
                co=xyz(u,head['center_v'],depth);co.z+=height*math.sin(angle)
                vs.append(co);uvs.append(uv(co));wts.append({names[0]:1})
                if i:
                    a=(i-1)*radial+j;b=(i-1)*radial+(j+1)%radial;fs.append((a,b,b+radial,a+radial))
        fs.extend([tuple(reversed(range(radial))),tuple((len(rows)-1)*radial+j for j in range(radial))])
        head_object=mesh('Cephalofoil',vs,fs,uvs,wts)
        if head.get('mouth'):
            mouth=head['mouth'];vs=[];fs=[]
            for i,(u,depth,z) in enumerate(mouth['points']):
                for offset in [-mouth['width']/2,mouth['width']/2]:
                    co=xyz(u+offset,head['center_v'],depth);co.z+=z;vs.append(co)
                if i:fs.append(((i-1)*2,(i-1)*2+1,i*2+1,i*2))
            donor=mouth['source_uv'];mesh('Ventral_mouth',vs,fs,[(donor[0],1-donor[1]) for _ in vs],[{names[0]:1} for _ in vs],.0002,True)
    def finbone(name,anchor,tip,axis,amplitude,phase):
        bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT');b=arm.edit_bones.new(name);b.head=anchor;b.tail=tip
        if (tip-anchor).length<.001:b.tail.z+=.005
        parent=max(weights(anchor.x+.5),key=weights(anchor.x+.5).get);b.parent=arm.edit_bones[parent];bpy.ops.object.mode_set(mode='OBJECT')
        fin_motion.append((name,Vector(axis),amplitude,phase));return name
    attachment_metrics={}
    for f in p['fins']:
        polygon,points=fin_source_geometry(f,aspect)
        xmin=min(v[0] for v in polygon);xmax=max(v[0] for v in polygon);ymin=min(v[1] for v in polygon);ymax=max(v[1] for v in polygon)
        dv,de,df,*_=delaunay_2d_cdt(points,[(i,(i+1)%len(polygon)) for i in range(len(polygon))],[list(range(len(polygon)))],1,1e-7)
        require(bool(df),'Fin polygon cannot be triangulated: '+f['name'])
        for side in ([-1,1] if f['paired'] else [1]):
            name=f['name']+('_left' if side<0 else '_right' if f['paired'] else '')
            scale=f.get('vertical_scale',1)
            def finpos(u,v,depth):return xyz(u,f['anchor'][1]+(v-f['anchor'][1])*scale,depth)
            attachment=f.get('root_attachment')
            posterior_bvh=None
            if attachment and attachment.get('surface_region')=='posterior':
                body_object.data.calc_loop_triangles();pv=[v.co.copy() for v in body_object.data.vertices];rear=min(v.x for v in pv);span=max(v.x for v in pv)-rear
                pf=[tuple(t.vertices) for t in body_object.data.loop_triangles if max(pv[i].x for i in t.vertices)<=rear+.025*span and (pv[t.vertices[1]]-pv[t.vertices[0]]).cross(pv[t.vertices[2]]-pv[t.vertices[0]]).normalized().x<-.5]
                require(bool(pf),'No posterior body region for fin root: '+name);posterior_bvh=BVHTree.FromPolygons(pv,pf,all_triangles=True)
            def attach(point,t):
                if not attachment:return point
                gain=root_attachment_gain(t,attachment['root_band'],attachment['blend_end'])
                if gain<=0 and not attachment.get('surface_clearance'):return point
                if posterior_bvh:
                    hit,normal,face,_=posterior_bvh.find_nearest(point);found=face is not None
                elif attachment.get('surface_clearance') and not f['paired']:
                    vertical=1 if f['tip'][1]<f['anchor'][1] else -1
                    origin=Vector((point.x,point.y,vertical*2.))
                    found,hit,normal,_=body_object.ray_cast(origin,Vector((0,0,-vertical)),distance=4.)
                    if not found:found,hit,normal,_=body_object.closest_point_on_mesh(point)
                else:found,hit,normal,_=body_object.closest_point_on_mesh(point)
                require(found and normal.length>.5 and (not f['paired'] or normal.y*side>=-1e-5),'Fin root does not resolve to matching body surface: '+name)
                result=point.lerp(hit-normal.normalized()*root_attachment_inset(t,attachment),gain)
                clearance=attachment.get('surface_clearance',0)
                if clearance and t>attachment['root_band']:
                    # Full membrane safety is distinct from basal projection.
                    # Keep source side silhouette while clearing the actual flank.
                    if f['paired']:
                        origin=Vector((result.x,side*2.,result.z))
                        found_side,side_hit,_,_=body_object.ray_cast(origin,Vector((0,-side,0)),distance=4.)
                        if found_side:result.y=side*max(abs(result.y),abs(side_hit.y)+clearance)
                    else:
                        if not posterior_bvh:
                            origin=Vector((result.x,result.y,vertical*2.))
                            free_hit,near,n,_=body_object.ray_cast(origin,Vector((0,0,-vertical)),distance=4.)
                            if free_hit:result.z=vertical*max(vertical*result.z,vertical*near.z+clearance)
                        if posterior_bvh:near,n,face,distance=posterior_bvh.find_nearest(result)
                        else:
                            found_free,near,n,_=body_object.closest_point_on_mesh(result)
                            require(found_free,'Free fin surface has no body donor')
                            distance=(result-near).length
                        signed=distance*(1 if (result-near).dot(n)>=0 else -1)
                        if signed<clearance:result=near+n.normalized()*clearance
                return result
            anchor=attach(finpos(*f['anchor'],side*f['root_depth']),0);tip=finpos(*f['tip'],side*f['tip_depth']);bn=finbone(name,anchor,tip,f['axis'],f['amplitude']*side,f['phase'])
            delta=Vector(f['tip'])-Vector(f['anchor']);denom=max(delta.length_squared,1e-8);vs=[];uvs=[];wts=[];source_parameters=[]
            for v in dv:
                t=fin_baseline_parameter(v,f['source_baseline'],polygon,aspect) if f.get('source_baseline') else max(0,min(1,(v-Vector(f['anchor'])).dot(delta)/denom));depth=side*(f['root_depth']+(f['tip_depth']-f['root_depth'])*t)
                vs.append(attach(finpos(v.x,v.y,depth),t));source_parameters.append(t)
                if f.get('opaque'):
                    # Fin silhouette comes from geometry; sample an opaque
                    # interior donor rather than clipping the mesh with alpha.
                    if f.get('source_rect'):
                        r=f['source_rect'];u=r[0]+(v.x-xmin)/max(xmax-xmin,1e-8)*(r[2]-r[0]);vv=r[1]+(v.y-ymin)/max(ymax-ymin,1e-8)*(r[3]-r[1])
                        uvs.append(fin_uv(u,vv))
                    else:uvs.append(fin_uv(v.x,v.y))
                else:uvs.append((v.x,1-v.y))
                fin_weight=t*(1-root_attachment_gain(t,attachment['root_band'],attachment['blend_end'])) if attachment else t
                w={n:w*(1-fin_weight) for n,w in weights(vs[-1].x+.5 if attachment else v.x).items()};w[bn]=fin_weight;wts.append(w)
            mesh(name,vs,df,uvs,wts,f['thickness'],f.get('opaque',False),source_parameters if attachment else None)
            if attachment:attachment_metrics[name]={'root_attachment':attachment,'root_bone_anchor':list(anchor),'distal_tip':list(tip),'body_weighted_root':True}
    if p['eyes']:
        e=p['eyes'];u,v=e['center']
        for side in [-1,1]:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=1)
            tmp=bpy.context.object;fs=[tuple(poly.vertices) for poly in tmp.data.polygons]
            if e.get('mode')=='surface_patch':
                target=head_object if p.get('cephalofoil') else body_object
                found,anchor,normal,_=target.closest_point_on_mesh(xyz(u,v,side*e['depth']))
                require(found and normal.y*side>0,'Eye landmark does not resolve to the matching body side')
                normal.normalize();horizontal=Vector((1,0,0));horizontal=(horizontal-normal*horizontal.dot(normal)).normalized()
                vertical=horizontal.cross(normal)*side;vertical.normalize()
                rect=e['source_rect'];height=e['radius']*(H/W)*((rect[3]-rect[1])/(rect[2]-rect[0]))
                require(number(height,0,.05) and height>0,'Derived eye patch half-height exceeds native-image geometry budget')
                center=anchor+normal*e['surface_offset']
                vs=[center+horizontal*pt.co.x*e['radius']+normal*pt.co.y*e['thickness']+vertical*pt.co.z*height for pt in tmp.data.vertices]
                uvs=[((rect[0]+rect[2])/2+pt.co.x*(rect[2]-rect[0])/2,1-((rect[1]+rect[3])/2-pt.co.z*(rect[3]-rect[1])/2)) for pt in tmp.data.vertices]
                wts=[weights(anchor.x+.5) for _ in vs]
            else:
                vs=[xyz(u,v,side*e['depth'])+Vector((pt.co.x*e['radius'],pt.co.y*e['radius']*.3,pt.co.z*e['radius'])) for pt in tmp.data.vertices]
                uvs=[(e['source_uv'][0],1-e['source_uv'][1]) for _ in vs] if e.get('source_uv') else [uv(co) for co in vs]
                wts=[{names[0]:1} for _ in vs]
            bpy.data.objects.remove(tmp,do_unlink=True);mesh('Textured_eye_'+str(side),vs,fs,uvs,wts)
    for b in p['barbels']:
        path=[xyz(*v) for v in b['path']];vs=[];fs=[];uvs=[]
        for i,point in enumerate(path):
            tangent=(path[min(i+1,len(path)-1)]-path[max(0,i-1)]).normalized();a=tangent.cross(Vector((0,0,1))).normalized();bb=tangent.cross(a).normalized()
            for j in range(8):
                co=point+(a*math.cos(j*math.tau/8)+bb*math.sin(j*math.tau/8))*b['radius']*(1-.8*i/(len(path)-1));vs.append(co);uvs.append(uv(point))
                if i:
                    n=i*8+j;k=i*8+(j+1)%8;fs.append((n-8,k-8,k,n))
        fs.extend([tuple(reversed(range(8))),tuple((len(path)-1)*8+j for j in range(8))]);mesh(b['name'],vs,fs,uvs,[{names[0]:1} for _ in vs])
    for frame in range(frames+1):
        phase=math.tau*(frame%frames)/frames
        for i,n in enumerate(names):
            pb=rig.pose.bones[n];pb.rotation_mode='QUATERNION';axis=pb.bone.matrix_local.to_3x3().inverted()@Vector((0,0,1));pb.rotation_quaternion=Quaternion(axis,p['animation']['body_amplitudes'][i]*math.sin(phase-i*p['animation']['phase_step']));pb.keyframe_insert('rotation_quaternion',frame=frame,group=n)
        for n,axis,amp,delay in fin_motion:
            pb=rig.pose.bones[n];pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion(pb.bone.matrix_local.to_3x3().inverted()@axis,amp*math.sin(phase-delay));pb.keyframe_insert('rotation_quaternion',frame=frame,group=n)
    rig.animation_data.action.name='Swim';scene.frame_set(0)
    closure={};bad_weights=0
    for o in meshes:
        bm=bmesh.new();bm.from_mesh(o.data);closure[o.name]=all(e.is_manifold for e in bm.edges);bm.free()
        bad_weights+=sum(abs(sum(g.weight for g in v.groups)-1)>1e-5 for v in o.data.vertices)
    export_native(outputs,rig,meshes)
    glb=binary_inspect(outputs['glb']);tracks=glb['animation_tracks']
    surface_sources_ok=all(source.packed_file is not None and surface_face_counts[label]>0 for label,source in surface_images.items())
    checks={'closed_mesh':all(closure.values()),'normalized_weights':bad_weights==0,'finite_glb':glb['nonfinite_components']==0,'animation_loop':bool(tracks) and all(t['seam_delta']<1e-6 for t in tracks) and any(t['max_change']>1e-5 for t in tracks),'root_motion':rig.location.length==0 and rig.rotation_euler.x==0 and rig.rotation_euler.y==0 and rig.rotation_euler.z==0,'texture_original_resolution':tuple(image.size)==(W,H) and image.packed_file is not None and glb['images_embedded'] and (front_image is None or (front_image.packed_file is not None and tuple(front_image.size)==(FW,FH) and front_face_count>0)) and surface_sources_ok,'texture_nearest':glb['nearest'],'roughness_contract':glb['roughness']}
    return checks,{'oral_jaws':oral_metrics,'root_attachments':attachment_metrics,'source_size':[W,H],'source_packed':image.packed_file is not None,'continuous_head_atlas':continuous_atlas_metrics,'body_uv_edge_repairs':uv_edge_repairs,'front_source_size':list(front_image.size) if front_image else None,'front_projected_faces':front_face_count,'surface_source_sizes':{label:list(source.size) for label,source in surface_images.items()},'surface_projected_faces':surface_face_counts,'bones':len(arm.bones),'vertices':sum(len(o.data.vertices) for o in meshes),'closed_meshes':closure,'unnormalized_weights':bad_weights,'glb':glb,'source_loop_seconds':frames/scene.render.fps}


def revise_native(h,p,source,outputs):
    """Keep accepted topology/UV/weights/actions; apply declared native Y/Z fields."""
    revision=p['rest_shape_revision']
    original=revision_source(revision,Path(h['profile']).parent,h)
    native=(Path(h['profile']).parent/revision['source_blend']).resolve()
    bpy.ops.wm.open_mainfile(filepath=str(native),use_scripts=False)
    scene=bpy.context.scene;scene.frame_set(scene.frame_start)
    rigs=[o for o in scene.objects if o.type=='ARMATURE']
    require(len(rigs)==1,'Native revision requires exactly one armature')
    rig=rigs[0];meshes=[o for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
    require(meshes,'Native revision has no rigged meshes')
    require(all(o.data.shape_keys is None for o in meshes),'Native revision does not support shape keys')
    require(all(o.matrix_world==rig.matrix_world for o in meshes),'Native revision requires shared mesh/armature coordinates')
    stations=revision['stations'];vertical=revision.get('vertical_stations',[]);aspect=1/p['source_aspect_ratio']
    def scale(u):return width_scale(stations,u)
    def shifted(point):
        result=point.copy();result.y*=scale(point.x+.5);result.z=vertical_position(vertical,point.x+.5,point.z,aspect);return result
    # A paired appendage preserves its own span/shape while its root follows the body.
    # Eye patches similarly retain their roundness instead of flattening with the head.
    shifts={}
    for fin in p['fins']:
        if not fin['paired'] and not vertical:continue
        for side,suffix in ([(-1,'_left'),(1,'_right')] if fin['paired'] else [(1,'')]):
            name=fin['name']+suffix
            bone=rig.data.bones.get(name)
            require(bone is not None,'Native paired fin bone missing: '+name)
            anchor=bone.head_local
            shifts[name]=shifted(anchor)-anchor
    before={o.name:(len(o.data.vertices),len(o.data.polygons),[tuple(v.uv) for v in o.data.uv_layers.active.data]) for o in meshes}
    native_attachment={}
    for fin in p['fins']:
        if not fin.get('root_attachment'):continue
        require(fin['paired'],'Native attachment only supports authored paired fins')
        for side,suffix in [(-1,'_left'),(1,'_right')]:
            name=fin['name']+suffix;obj=bpy.data.objects[name]
            delta=Vector(fin['tip'])-Vector(fin['anchor']);denom=delta.length_squared
            require(denom>1e-8 and fin.get('vertical_scale',1)>0,'Invalid native fin parameter axis')
            attribute=obj.data.attributes.get('foundry_fin_source_t')
            if attribute is None:
                values=[]
                for vertex in obj.data.vertices:
                    u=vertex.co.x+.5;v=fin['anchor'][1]+((.5-vertex.co.z/aspect)-fin['anchor'][1])/fin.get('vertical_scale',1)
                    values.append(max(0,min(1,(Vector((u,v))-Vector(fin['anchor'])).dot(delta)/denom)))
                attribute=obj.data.attributes.new('foundry_fin_source_t','FLOAT','POINT')
                for item,value in zip(attribute.data,values):item.value=value
            native_attachment[name]=(fin,side,[item.value for item in attribute.data])
    for obj in meshes:
        if obj.name in shifts:
            delta=shifts[obj.name]
            for vertex in obj.data.vertices:vertex.co+=delta
        elif obj.name.startswith('Textured_eye_'):
            center=sum((v.co for v in obj.data.vertices),Vector())/len(obj.data.vertices)
            delta=shifted(center)-center
            for vertex in obj.data.vertices:vertex.co+=delta
        else:
            for vertex in obj.data.vertices:vertex.co=shifted(vertex.co)
        obj.data.update()
    bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in rig.data.edit_bones:
        if bone.name in shifts:
            bone.head+=shifts[bone.name];bone.tail+=shifts[bone.name]
        else:
            bone.head=shifted(bone.head);bone.tail=shifted(bone.tail)
    bpy.ops.object.mode_set(mode='OBJECT')
    # Opt-in repairs reuse the accepted native membrane/UVs. The proximal band
    # follows the current actual body and carries body-only weights; distal
    # geometry and the independent fin animation remain intact.
    attachment_metrics={}
    if native_attachment:
        body=bpy.data.objects.get('Closed_body');require(body is not None,'Native attachment requires Closed_body')
        saved_pose=rig.data.pose_position;rig.data.pose_position='REST'
        bpy.context.view_layer.update()
        ordered=sorted((point[0],'body_%02d'%i) for i,point in enumerate(p['rig']['spine']))
        def body_weights(u):
            if u<=ordered[0][0]:return {ordered[0][1]:1}
            if u>=ordered[-1][0]:return {ordered[-1][1]:1}
            for (a,na),(b,nb) in zip(ordered,ordered[1:]):
                if a<=u<=b:
                    t=(u-a)/(b-a);return {na:1-t,nb:t}
        for name,(fin,side,parameters) in native_attachment.items():
            obj=bpy.data.objects[name];option=fin['root_attachment'];moved=0
            for vertex,t in zip(obj.data.vertices,parameters):
                gain=root_attachment_gain(t,option['root_band'],option['blend_end'])
                if gain<=0:continue
                found,hit,normal,_=body.closest_point_on_mesh(vertex.co)
                require(found and normal.length>.5 and normal.y*side>=-1e-5,'Native fin root resolves to wrong body side: '+name)
                vertex.co=vertex.co.lerp(hit-normal.normalized()*option['inset'],gain)
                own=t*(1-gain);weights={n:value*(1-own) for n,value in body_weights(vertex.co.x+.5).items()};weights[name]=own
                for group in list(vertex.groups):obj.vertex_groups[group.group].remove([vertex.index])
                for bone,value in weights.items():
                    require(rig.data.bones.get(bone) is not None,'Native attachment bone missing: '+bone)
                    if value>1e-8:(obj.vertex_groups.get(bone) or obj.vertex_groups.new(name=bone)).add([vertex.index],value,'REPLACE')
                moved+=1
            obj.data.update()
            attachment_metrics[name]={'vertices_adjusted':moved,'root_attachment':option,'body_weighted_root':True,'distal_vertices_preserved':sum(t>=option['blend_end'] for t in parameters)}
        rig.data.pose_position=saved_pose;bpy.context.view_layer.update()
    closure={};bad_weights=0
    for obj in meshes:
        bm=bmesh.new();bm.from_mesh(obj.data);closure[obj.name]=all(e.is_manifold for e in bm.edges);bm.free()
        bad_weights+=sum(abs(sum(g.weight for g in v.groups)-1)>1e-5 for v in obj.data.vertices)
    unchanged=all(before[o.name]==(len(o.data.vertices),len(o.data.polygons),[tuple(v.uv) for v in o.data.uv_layers.active.data]) for o in meshes)
    require(unchanged,'Native revision changed topology or UVs')
    packed={sha256 for image in bpy.data.images if image.packed_file for sha256 in [hashlib.sha256(bytes(image.packed_file.data)).hexdigest()]}
    expected={h[key]['sha256'] for key in ['source','front_source','top_source','bottom_source'] if h.get(key)}
    require(expected<=packed,'Native revision textures differ from accepted source bytes')
    export_native(outputs,rig,meshes)
    glb=binary_inspect(outputs['glb']);tracks=glb['animation_tracks']
    checks={'closed_mesh':all(closure.values()),'normalized_weights':bad_weights==0,'finite_glb':glb['nonfinite_components']==0,'animation_loop':bool(tracks) and all(t['seam_delta']<1e-6 for t in tracks) and any(t['max_change']>1e-5 for t in tracks),'root_motion':rig.location.length==0 and rig.rotation_euler.x==0 and rig.rotation_euler.y==0 and rig.rotation_euler.z==0,'texture_original_resolution':expected<=packed and glb['images_embedded'],'texture_nearest':glb['nearest'],'roughness_contract':glb['roughness']}
    return checks,{'native_revision':True,'width_only':not bool(vertical),'vertical_stations':vertical,'topology_uv_unchanged':unchanged,'stations':stations,'root_attachments':attachment_metrics,'fin_root_shifts':{name:list(value) for name,value in shifts.items()},'bones':len(rig.data.bones),'vertices':sum(len(o.data.vertices) for o in meshes),'closed_meshes':closure,'unnormalized_weights':bad_weights,'glb':glb,'source_loop_seconds':(scene.frame_end-scene.frame_start)/scene.render.fps}


def render_review(h,outputs):
    bpy.ops.wm.open_mainfile(filepath=str(outputs['blend']));scene=bpy.context.scene;scene.frame_set(0)
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=False
    scene.render.resolution_x=900;scene.render.resolution_y=600;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard';scene.render.film_transparent=False
    world=bpy.data.worlds.new('Review neutral world');world.use_nodes=True
    background=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');background.inputs[0].default_value=(.13,.16,.19,1);background.inputs[1].default_value=.75;scene.world=world
    fish=[o for o in scene.objects if o.type=='MESH'];bound=[o.matrix_world@Vector(c) for o in fish for c in o.bound_box];lo=Vector([min(v[i] for v in bound) for i in range(3)]);hi=Vector([max(v[i] for v in bound) for i in range(3)]);center=(lo+hi)/2;span=max((hi-lo).x,.2)
    camdata=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('Review camera',camdata);scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=span*1.35
    lampdata=bpy.data.lights.new('Soft review light','AREA');lampdata.energy=35;lampdata.size=3;lamp=bpy.data.objects.new('Soft review light',lampdata);scene.collection.objects.link(lamp);lamp.location=(0,-2,3);lamp.rotation_euler=(Vector((0,0,0))-lamp.location).to_track_quat('-Z','Y').to_euler()
    review=Path(outputs['review_dir']);review.mkdir(parents=True,exist_ok=True);files={}
    spine=json.loads(Path(h['profile']).read_text())['rig']['spine'];head_sign=1 if spine[0][0]>spine[-1][0] else -1
    for name,direction in [('side',(0,-3,0)),('front',(head_sign*3,0,0)),
                           ('oblique',(head_sign*2,-3,1.2)),('top',(0,0,3)),('bottom',(0,0,-3))]:
        cam.location=center+Vector(direction)*span;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        bpy.context.view_layer.update();projected=[cam.matrix_world.inverted()@v for v in bound]
        extent_x=max(v.x for v in projected)-min(v.x for v in projected);extent_y=max(v.y for v in projected)-min(v.y for v in projected)
        camdata.ortho_scale=max(extent_x,extent_y*scene.render.resolution_x/scene.render.resolution_y)*1.25
        scene.render.filepath=str(review/(name+'.png'));bpy.ops.render.render(write_still=True);files[name]=scene.render.filepath
    # Clay geometry is reviewed independently of texture and alpha masks.
    clay=bpy.data.materials.new('Geometry review clay');clay.diffuse_color=(.5,.5,.5,1)
    scene.view_layers[0].material_override=clay
    for name,direction in [('clay_side',(0,-3,0)),('clay_front',(head_sign*3,0,0)),('clay_top',(0,0,3)),('clay_bottom',(0,0,-3)),('clay_oblique',(head_sign*2,-3,1.2))]:
        cam.location=center+Vector(direction)*span;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        camdata.ortho_scale=span*1.5
        scene.render.filepath=str(review/(name+'.png'));bpy.ops.render.render(write_still=True);files[name]=scene.render.filepath
    scene.view_layers[0].material_override=None
    profile=json.loads(Path(h['profile']).read_text())
    if profile.get('oral_jaws'):
        body=next(o for o in fish if o.name=='Closed_body')
        points=[body.matrix_world@v.co for v in body.data.vertices if v.co.x+.5>=profile['oral_jaws']['corner'][0]-.04]
        head_lo=Vector([min(v[i] for v in points) for i in range(3)])
        head_hi=Vector([max(v[i] for v in points) for i in range(3)])
        target=(head_lo+head_hi)/2
        scene.cycles.samples=32
        for gray in [False,True]:
            scene.view_layers[0].material_override=clay if gray else None
            for view,direction in [('side',(0,-3,0)),('front',(3,0,0)),('oblique',(2,-3,.65))]:
                name=('clay_' if gray else '')+'oral_'+view
                cam.location=target+Vector(direction)*span
                cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
                camdata.ortho_scale=max((head_hi-head_lo).x,(head_hi-head_lo).z*1.5)*1.35
                scene.render.filepath=str(review/(name+'.png'));bpy.ops.render.render(write_still=True);files[name]=scene.render.filepath
        scene.view_layers[0].material_override=None
    # Build a true Blender comparison scene: unchanged source/anchor planes above model.
    def image_plane(path,name,cx,cz,width):
        image=bpy.data.images.load(str(path),check_existing=True);w,hh=image.size[:];height=width*hh/w
        data=bpy.data.meshes.new(name);data.from_pydata([(cx-width/2,-.1,cz-height/2),(cx+width/2,-.1,cz-height/2),(cx+width/2,-.1,cz+height/2),(cx-width/2,-.1,cz+height/2)],[],[(0,1,2,3)]);obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
        layer=data.uv_layers.new();coords=[(0,0),(1,0),(1,1),(0,1)]
        for i in range(4):layer.data[i].uv=coords[i]
        mat=bpy.data.materials.new(name);mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();tex=nodes.new('ShaderNodeTexImage');tex.image=image;tex.interpolation='Closest';em=nodes.new('ShaderNodeEmission');out=nodes.new('ShaderNodeOutputMaterial');transparent=nodes.new('ShaderNodeBsdfTransparent');mix=nodes.new('ShaderNodeMixShader');links=mat.node_tree.links;links.new(tex.outputs['Color'],em.inputs[0]);links.new(tex.outputs['Alpha'],mix.inputs[0]);links.new(transparent.outputs[0],mix.inputs[1]);links.new(em.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],out.inputs[0]);data.materials.append(mat)
    source=Path(h['source_image']);anchor=Path(h['style_contract']['style_reference_image'])
    image_plane(source,'Approved source',-.57,.68,.92);image_plane(anchor,'Style reference',.57,.68,.92)
    rig=next(o for o in scene.objects if o.type=='ARMATURE')
    def text(label,pos,size=.05):
        data=bpy.data.curves.new(label,'FONT');data.body=label;data.size=size;obj=bpy.data.objects.new(label,data);scene.collection.objects.link(obj);obj.location=pos;obj.rotation_euler=(math.pi/2,0,0)
    text('APPROVED SIDE SOURCE',(-1.03,-.12,1.02),.045);text('STYLE REFERENCE',(.12,-.12,1.02))
    if h.get('front_source_image'):
        fi=bpy.data.images.load(h['front_source_image'],check_existing=True)
        image_plane(Path(h['front_source_image']),'Approved front source',-.57,-.23,min(.92,.48*fi.size[0]/fi.size[1]))
        rig.location=(.57,0,-.23);rig.scale*=.92/span
        text('APPROVED FRONT SOURCE',(-1.03,-.12,.09),.04);text('RECONSTRUCTED 3D',(.12,-.12,.09),.04)
    else:
        rig.location.z=-.22
        text('RECONSTRUCTED 3D / SAME NATIVE PIXELS',(-.75,-.12,.08),.04)
    cam.location=(0,-4,.34);cam.rotation_euler=(Vector((0,0,.34))-cam.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=2.35;scene.render.resolution_x=1100;scene.render.resolution_y=800;scene.render.filepath=str(review/'style-comparison.png');bpy.ops.render.render(write_still=True);files['style_comparison']=scene.render.filepath
    master=h.get('source',{}).get('generation_reference_image') if not h.get('accepted_archive') else None
    if master:
        for o in scene.objects:
            if o.type=='FONT' or o.name in ('Approved source','Style reference','Approved front source'):o.hide_render=True
        image_plane(Path(master),'Accepted identity master',-.57,.34,.92)
        rig.location=(.57,0,.34);rig.rotation_euler=(.20,.05,-.35)
        text('SELECTED MASTER B',(-1.03,-.12,.89),.045)
        text('RECONSTRUCTED 3D',(.12,-.12,.89),.045)
        scene.render.filepath=str(review/'master-comparison.png');bpy.ops.render.render(write_still=True);files['master_comparison']=scene.render.filepath
    return files


def main():
    args=sys.argv[sys.argv.index('--')+1:];require(len(args) in (1,2) and (len(args)==1 or args[1]=='--render-only'),'Expected handoff.json [--render-only]')
    handoff=Path(args[0]).resolve();h=json.loads(handoff.read_text());outputs={k:Path(v).resolve() for k,v in h['outputs'].items() if k in ['blend','glb','validation_report','review_dir','render_report']}
    for destination in outputs.values():
        require(destination.is_relative_to(handoff.parent),'Outputs must stay within the handoff directory')
    report={'schema_version':1,'run_id':h.get('run_id'),'ok':False,'status':'failed','next_action':'fix_input','outputs':{k:str(v) for k,v in outputs.items()},'checks':{},'failures':[],'style_visual_review':'pending'}
    try:
        source=Path(h['source_image']).resolve();profile=Path(h['profile']).resolve();p=json.loads(profile.read_text());validate_profile(p)
        contract=h['style_contract'];require(contract.get('pixel_art') is True and contract.get('texture_filter')=='nearest' and contract.get('roughness')==1,'Invalid pixel style contract')
        source_sha=sha(source);profile_sha=sha(profile);anchor=Path(contract['style_reference_image']).resolve();anchor_sha=sha(anchor)
        require(source_sha==contract['source_sha256'],'Source hash changed');require(anchor_sha==contract['style_reference_sha256'],'Style reference hash changed')
        frozen=h.get('profile_snapshot',{});require(not frozen.get('sha256') or frozen['sha256']==profile_sha,'Profile hash changed')
        for key in ['blend','glb','validation_report']:
            require(key in outputs,'Missing output '+key);outputs[key].parent.mkdir(parents=True,exist_ok=True)
        report.update(source_sha256=source_sha,profile_sha256=profile_sha,style_reference_sha256=anchor_sha)
        require(bool(h.get('front_source_image'))==bool(p.get('head_projection')),'Front input and head_projection must be supplied together')
        if h.get('front_source_image'):
            front_sha=sha(h['front_source_image']);require(front_sha==h.get('front_source',{}).get('sha256'),'Front source hash changed or missing provenance')
            report['front_source_sha256']=front_sha
        for label,projection in [('top','dorsal_projection'),('bottom','ventral_projection')]:
            image_key=label+'_source_image';source_key=label+'_source';require(bool(h.get(image_key))==bool(p.get(projection)),label.capitalize()+' input and '+projection+' must be supplied together')
            if h.get(image_key):
                surface_sha=sha(h[image_key]);require(surface_sha==h.get(source_key,{}).get('sha256'),label.capitalize()+' source hash changed or missing provenance')
                report[label+'_source_sha256']=surface_sha
        if '--render-only' in args:
            require(outputs['blend'].is_file() and outputs['glb'].is_file(),'Build model before render')
            previous=json.loads(outputs['validation_report'].read_text())
            source_keys=['source_sha256','profile_sha256','style_reference_sha256']+(['front_source_sha256'] if h.get('front_source_image') else [])+[label+'_source_sha256' for label in ['top','bottom'] if h.get(label+'_source_image')]
            require(all(previous.get(key)==report[key] for key in source_keys),'Render inputs differ from successful build inputs')
            require(previous.get('ok') is True and previous.get('blend_sha256')==sha(outputs['blend']) and previous.get('glb_sha256')==sha(outputs['glb']),'Model outputs differ from successful build validation')
            files=render_review(h,outputs);report.update(ok=True,status='done',next_action='human_review',review=files,glb_sha256=sha(outputs['glb']),blend_sha256=sha(outputs['blend']))
            target=outputs.get('render_report',outputs['validation_report'])
        else:
            checks,metrics=(revise_native(h,p,source,outputs) if p.get("rest_shape_revision") else build(h,p,source,outputs));report.update(checks=checks,metrics=metrics,glb_sha256=sha(outputs['glb']),blend_sha256=sha(outputs['blend']));passed=all(checks.values());report.update(ok=passed,status='done' if passed else 'failed',next_action='human_review' if passed else 'fix_input')
            report['failures']=[{'kind':'validation','code':k,'message':'Model check failed: '+k} for k,v in checks.items() if not v];target=outputs['validation_report']
    except Exception as exc:
        report['failures'].append({'kind':'validation','code':type(exc).__name__,'message':str(exc)});report['traceback']=traceback.format_exc();target=outputs.get('render_report') if '--render-only' in args else outputs['validation_report']
    target=target or outputs['validation_report'];target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('FOUNDRY_VOLUME_REPORT '+json.dumps(report,ensure_ascii=False))
    if not report['ok']:raise SystemExit(2)

if __name__=='__main__':main()
