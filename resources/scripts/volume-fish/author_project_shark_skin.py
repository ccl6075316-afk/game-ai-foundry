"""Bake project-art body views and native lips onto their own sparse geometry.

Primary side pixels remain the lateral skin. Generated donors are confined to
the occluded fin/eye/mouth footprint or the corresponding dorsal/ventral view.
No repeated skin tile and no scanned-model UV/shape source is used.
"""
import bpy,bmesh,json,hashlib,sys,math
from pathlib import Path
import numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from rim_material_transport import nearest_arc,native_lip_ownership

args=sys.argv[sys.argv.index('--')+1:];cp=Path(args[0]).resolve();out=Path(args[1]).resolve();c=json.loads(cp.read_text());assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir();sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest();src=Path(c['baseline']);assert sha(src/'fish.glb')==c['baseline_sha256'];bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));body=bpy.data.objects['Reference_head_body'];mesh=body.data;ref=json.loads(Path(c['reference']).read_text());canvas=ref['source_canvas'];length=canvas['length_m'];origin=canvas['origin_u'];aspect=canvas['height']/canvas['width'];density=c['pixels_per_m'];coords=np.array([v.co[:]for v in mesh.vertices]);images={};bounds={}
for role,item in c['sources'].items():
    assert sha(item['path'])==item['sha256'];image=bpy.data.images.load(item['path'],check_existing=False);w,h=image.size;pixels=np.array(image.pixels[:]).reshape(h,w,4)[::-1].copy();mask=pixels[:,:,3]>.9;lo=np.zeros(w);hi=np.zeros(w)
    for x in range(w):
        ys=np.where(mask[:,x])[0];lo[x]=ys.min()if len(ys)else np.nan;hi[x]=ys.max()if len(ys)else np.nan
    valid=np.isfinite(lo);lo=np.interp(np.arange(w),np.where(valid)[0],lo[valid]);hi=np.interp(np.arange(w),np.where(valid)[0],hi[valid]);images[role]=(w,h,pixels);bounds[role]=(lo,hi)
sampler_indices=np.load(c['sampler_indices']) if c.get('sampler_indices') else None
def sample(role,xy):
    w,h,pixels=images[role];lo,hi=bounds[role];inset=12 if role in ['dorsal','clean_bottom','clean_side'] else 2;ix=np.clip(np.rint(xy[:,0]).astype(int),inset,w-1-inset);iy=np.clip(np.rint(xy[:,1]).astype(int),0,h-1);iy=np.maximum(iy,np.ceil(lo[ix]+inset).astype(int));iy=np.minimum(iy,np.floor(hi[ix]-inset).astype(int));iy=np.clip(iy,0,h-1)
    if sampler_indices is not None and role in sampler_indices:
        index=sampler_indices[role];iy,ix=index[:,iy,ix]
    result=pixels[iy,ix].copy();result[:,3]=1;return result
def source_sample(role,xy):
    w,h,pixels=images[role];indices=np.rint(xy).astype(int);indices[:,0]=np.clip(indices[:,0],0,w-1);indices[:,1]=np.clip(indices[:,1],0,h-1);result=pixels[indices[:,1],indices[:,0]].copy();assert np.all(result[:,3]>.9);result[:,3]=1;return result,indices
bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();edges=[tuple(v.index for v in e.verts)for e in bm.edges if len(e.link_faces)==2 and any(f.material_index==1 for f in e.link_faces)and any(f.material_index in c.get('skin_material_slots',[0]) for f in e.link_faces)];bm.free();adj={}
for a,b in edges:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
assert adj and all(len(v)==2 for v in adj.values());lo=min(adj,key=lambda i:coords[i,1]);hi=max(adj,key=lambda i:coords[i,1]);paths=[]
for first in adj[lo]:
    ids=[lo,first]
    while ids[-1]!=hi:
        nxt=[i for i in adj[ids[-1]]if i!=ids[-2]];assert len(nxt)==1;ids.append(nxt[0]);assert len(ids)<=len(adj)
    points=coords[ids];paths.append((points,np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]))
paths.sort(key=lambda path:path[0][:,0].mean(),reverse=True);rims=dict(zip(['upper','lower'],paths));rows=ref['body_stations'];ts=[r['t']for r in rows];axis=ref['reference_body_axis_m'];top_head=ref['head_transverse_stations'];head_top_center=(top_head[0]['project_top_row_px']+top_head[-1]['project_top_row_px'])/2;head_span=ref['head_span_m'];native_samples=[];tiles=[];protected=0
def view_xy(role,points,u):
    w,h,_=images[role];lo,hi=bounds[role];x=np.clip(u*(w-1),0,w-1);mid=(np.interp(x,np.arange(w),lo)+np.interp(x,np.arange(w),hi))/2
    if role=='dorsal':y=head_top_center+points[:,1]/length*w
    else:
        # Generated views can have different canvas aspect; head span registers
        # transverse physical landmarks rather than stretching an unrelated fish.
        roi=int(c['head_neck_u']*w);mask=images[role][2][:,roi:,3]>.9;ys=np.where(mask)[0];center=(ys.min()+ys.max())/2;span=float(ys.max()-ys.min());y=center+points[:,1]/head_span*span
    return np.stack([x,y],1)
def donor(name,phase,total,distance):
    curve=np.array(c[name+'_source_curve_px'],float);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(curve,axis=0),axis=1))];s=np.clip(phase/total,0,1)*arc[-1];xy=np.stack([np.interp(s,arc,curve[:,i])for i in[0,1]],1);ids=np.clip(np.searchsorted(arc,s,side='right')-1,0,len(curve)-2);tangent=curve[ids+1]-curve[ids];normal=np.stack([tangent[:,1],-tangent[:,0]],1);normal/=np.linalg.norm(normal,axis=1)[:,None]
    if name=='lower':normal*=-1
    return xy+normal*distance[:,None]
for face in mesh.polygons:
    if face.material_index not in c.get('skin_material_slots',[0]):continue
    points=coords[list(face.vertices)];ex=points[1]-points[0];ex/=np.linalg.norm(ex);normal=np.cross(points[1]-points[0],points[2]-points[0]);normal/=np.linalg.norm(normal);ey=np.cross(normal,ex);q=np.stack([(points-points[0])@ex,(points-points[0])@ey],1)*density;q-=np.floor(q.min(0))-2;tw,th=np.ceil(q.max(0)+3).astype(int);xx,yy=np.meshgrid(np.arange(tw),np.arange(th));local=np.stack([xx.ravel(),yy.ravel()],1);beta=np.c_[np.ones(len(local)),(local-q[0])@np.linalg.inv(np.column_stack([q[1]-q[0],q[2]-q[0]])).T];beta[:,0]-=beta[:,1:].sum(1);in_face=(beta.min(1)>=-1e-6);b=np.maximum(beta,0);b/=b.sum(1)[:,None];p=b@points;u=p[:,0]/length+origin;v=.5-p[:,2]/(aspect*length);t=(axis/2-p[:,0])/axis;zt=np.interp(t,ts,[r['top_z_m']for r in rows]);zb=np.interp(t,ts,[r['bottom_z_m']for r in rows]);mid=(zt+zb)/2;half=np.maximum((zt-zb)/2,1e-6);height=(p[:,2]-mid)/half;side_color=sample('side',np.stack([u*images['side'][0],v*images['side'][1]],1))
    # Own-source occluded footprints only; preserve native lateral gills and
    # all unaffected body pigment, rather than replacing the entire side skin.
    patch=((u>.685)&(u<.79)&(v>.60))|((u>.86)&(v>.50))
    for name,a0,a1,b0,b1 in c['additional_side_patch_rects']:
        patch|=(u>a0)&(u<a1)&(v>b0)&(v<b1)
    if patch.any():
        w,h,_=images['clean_side'];lo,hi=bounds['clean_side'];x=u[patch]*(w-1);r=(v[patch]-(.5-zt[patch]/(aspect*length)))/np.maximum((zt[patch]-zb[patch])/(aspect*length),1e-6);y=np.interp(x,np.arange(w),lo)+r*(np.interp(x,np.arange(w),hi)-np.interp(x,np.arange(w),lo));side_color[patch]=sample('clean_side',np.stack([x,y],1))
    dorsal=sample('dorsal',view_xy('dorsal',p,u));ventral=sample('clean_bottom',view_xy('clean_bottom',p,u));gain=np.clip((abs(height)-.18)/.42,0,1);gain=gain*gain*(3-2*gain);base=side_color*(1-gain[:,None])+np.where(height[:,None]>0,dorsal,ventral)*gain[:,None]
    head_gain=np.clip((u-.86)/.025,0,1);head_gain=head_gain*head_gain*(3-2*head_gain);upper_gain=np.clip((height+.65)/1.3,0,1);upper_gain=upper_gain*upper_gain*(3-2*upper_gain)
    head_skin=dorsal*upper_gain[:,None]+ventral*(1-upper_gain[:,None]);base=base*(1-head_gain[:,None])+head_skin*head_gain[:,None]
    if c.get('front_skin_roi_px'):
        xa,ya,xb,yb=c['front_skin_roi_px'];front_x=np.interp(p[:,1],[r['y_m']for r in top_head],[r['front_x_m']for r in top_head]);rear_x=np.interp(p[:,1],[r['y_m']for r in top_head],[r['rear_x_m']for r in top_head]);chord=np.clip((front_x-p[:,0])/np.maximum(front_x-rear_x,1e-6),0,1);front_gain=np.clip((.16-chord)/.12,0,1)*head_gain;front_gain=front_gain*front_gain*(3-2*front_gain)
        xy=np.stack([xa+(p[:,1]/head_span+.5)*(xb-xa),ya+(1-np.clip(height,-1,1))/2*(yb-ya)],1);front_skin=sample('front',xy);base=base*(1-front_gain[:,None])+front_skin*front_gain[:,None]
    near={name:nearest_arc(p,rim)for name,rim in rims.items()};is_upper=near['upper'][0]<=near['lower'][0];distance=np.where(is_upper,near['upper'][0],near['lower'][0])*density;domain=np.where(is_upper,c['lip_domain']['upper_width_px'],c['lip_domain']['lower_width_px']);ownership=native_lip_ownership(distance,domain,c['lip_domain']['outer_fade_px']);maps=[]
    for name in['upper','lower']:
        take=(is_upper if name=='upper'else~is_upper)&(ownership>0)
        if not take.any():continue
        xy=donor(name,near[name][1][take],rims[name][1][-1],distance[take]);native,indices=source_sample('ventral',xy);gain=ownership[take,None];base[take]=base[take]*(1-gain)+native*gain;flat=np.where(take)[0];core=(distance[flat]<=domain[flat])&in_face[flat];maps.extend((int(i),int(x),int(y))for i,(x,y)in zip(flat[core],indices[core]))
    assert np.all(ownership[distance<=domain]==1);base[:,3]=1;protected+=len(maps);tiles.append(dict(face=face.index,q=q,w=int(tw),h=int(th),pixels=base.reshape(th,tw,4),native_map=maps))
width=2048;x=y=3;row=0
for tile in tiles:
    if x+tile['w']+3>width:x=3;y+=row+3;row=0
    tile['at']=(x,y);x+=tile['w']+3;row=max(row,tile['h'])
height=2**math.ceil(math.log2(y+row+3));atlas=np.ones((height,width,4),np.float32);pixel_map=[]
for tile in tiles:
    x,y=tile['at'];atlas[y:y+tile['h'],x:x+tile['w']]=tile['pixels']
    for flat,sx,sy in tile['native_map']:pixel_map.append([x+flat%tile['w'],height-1-(y+flat//tile['w']),sx,sy])
image=bpy.data.images.new('Project source body and complete native lip domains',width,height,alpha=True);image.colorspace_settings.name='sRGB';image.pixels.foreach_set(atlas.ravel());image.pack();material=bpy.data.materials.new('Project-native views; generated occluded patches; native ventral lips');material.use_nodes=True;material.use_backface_culling=True;bs=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Roughness'].default_value=1;bs.inputs['Specular IOR Level'].default_value=0;texture=material.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image;texture.interpolation='Closest';material.node_tree.links.new(texture.outputs['Color'],bs.inputs['Base Color']);mesh.materials.append(material);slot=len(mesh.materials)-1;uv=mesh.uv_layers.active or mesh.uv_layers.new(name='ProjectArtNativeUV')
for tile in tiles:
    face=mesh.polygons[tile['face']];face.material_index=slot
    for loop,q in zip(face.loop_indices,tile['q']):uv.data[loop].uv=((q[0]+tile['at'][0]+.5)/width,(q[1]+tile['at'][1]+.5)/height)
assert protected>0;np.savez_compressed(out/'native-lip-pixel-map.npz',map=np.array(pixel_map,dtype=np.int32));bpy.ops.object.select_all(action='DESELECT');[o.select_set(True) for o in bpy.context.scene.objects if o.type in ['MESH','ARMATURE']];bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());report=dict(ok=True,kind='complete_anterior_semantic_color_chart',species=ref['species'],source_sha256=c['sources']['side']['sha256'],lip_donor_source_sha256=c['sources']['ventral']['sha256'],model_sha256=sha(out/'fish.glb'),geometry_weights_triangles_unchanged=True,actual_3d_rim_transport=dict(upper_edges=len(rims['upper'][0])-1,lower_edges=len(rims['lower'][0])-1),complete_native_lip_ownership=dict(protected_texels=protected,maximum_front_weight_inside_complete_lip=0,maximum_central_weight_inside_complete_lip=0,domain=c['lip_domain']),pixel_map_sha256=sha(out/'native-lip-pixel-map.npz'),atlas_size=[width,height],config_sha256=sha(cp),body_material_basis='Project side source, same-project cleaned dorsal/ventral views and explicitly bounded occluded-body patches. Native lateral body outside footprints retained. No external mesh/scan shape source or repeated skin tiles.',formal_acceptance=False);(out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(ok=True,protected=protected,atlas=[width,height])))
