"""Transport own curved 2D lip strips along actual skin/oral shared boundaries.

Experimental source-authoring step, no visual approval. No geometry changes,
flat forehead/chin rectangles, independent lip meshes or runtime recoloring.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
from collections import defaultdict
import bpy,bmesh,numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'cli'),str(Path(__file__).parent)]
from export_source_with_frozen_normals import export_guarded,EXACT_NORMAL_ATTRIBUTE
from patch_existing_fin_meshes import read as read_glb,write as write_glb
from triangulate_export_mesh import triangulate_export_mesh
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
p=argparse.ArgumentParser()
for key in ['blend','config','output']:p.add_argument('--'+key,type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);cfg=read(a.config);assert sha(a.blend)==cfg['blend_sha256'];out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists()
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));body=bpy.data.objects[cfg['body']]
assert EXACT_NORMAL_ATTRIBUTE not in body.data.attributes,'Edit an ordinary body source, preserve any existing guarded normals'
triangulation=triangulate_export_mesh(body);mesh=body.data
assert all(len(f.vertices)==3 for f in mesh.polygons)
def geometry():return hashlib.sha256(repr(([(tuple(v.co),[(body.vertex_groups[g.group].name,g.weight)for g in v.groups])for v in mesh.vertices],[tuple(f.vertices)for f in mesh.polygons])).encode()).hexdigest()
frozen=geometry();image=next(n.image for n in mesh.materials[0].node_tree.nodes if n.type=='TEX_IMAGE');W,H=image.size;assert[W,H]==cfg['source_size'];pixels=np.asarray(image.pixels[:]).reshape(H,W,4);coords=np.asarray([v.co[:]for v in mesh.vertices]);old_uv=np.asarray([v.uv[:]for v in mesh.uv_layers.active.data])
bm=bmesh.new();bm.from_mesh(mesh);bm.normal_update();bm.verts.ensure_lookup_table();boundaries={}
for name,sign in [('upper',-1),('lower',1)]:
    edges=[]
    for edge in bm.edges:
        if len(edge.link_faces)!=2:continue
        if any(f.material_index==0 for f in edge.link_faces)and any(f.material_index==1 and f.normal.z*sign>.1 for f in edge.link_faces):edges.append(tuple(v.index for v in edge.verts))
    adjacent=defaultdict(list)
    for u,v in edges:adjacent[u].append(v);adjacent[v].append(u)
    ends=[v for v,neighbors in adjacent.items()if len(neighbors)==1];assert len(ends)==2 and all(len(n)<=2 for n in adjacent.values()),(name,'Expected one unbranched actual lip chain',len(ends))
    first=min(ends,key=lambda i:coords[i,1]);chain=[first];previous=None;current=first
    while True:
        nexts=[v for v in adjacent[current]if v!=previous]
        if not nexts:break
        nxt=nexts[0];chain.append(nxt);previous,current=current,nxt
    assert len(chain)==len(adjacent);points=coords[chain];arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]*W
    source=np.asarray(cfg[name+'_inner_edge_px'],float)
    if 'donor_end_x' in cfg:source=source[source[:,0]<=cfg['donor_end_x']]
    assert len(source)>=3,'Curved2D donor needs a full explicit source interval'
    source_arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(source,axis=0),axis=1))]
    join_x=cfg.get('front_blend_start_px',source[-2,0])/W-.5;joins=[]
    for i,(a0,a1)in enumerate(zip(points,points[1:])):
        if (a0[0]-join_x)*(a1[0]-join_x)<0:
            t=(join_x-a0[0])/(a1[0]-a0[0]);joins.append(arc[i]+t*(arc[i+1]-arc[i]))
    assert len(joins)==2,(name,'Expected two actual source-side joins',joins)
    boundaries[name]={'chain':chain,'points':points,'arc':arc,'source':source,'source_arc':source_arc,'edges':edges,'joins':sorted(joins),'anchor':float(np.interp(cfg.get('front_blend_start_px',source[-2,0]),source[:,0],source_arc))}
bm.free()
front_data=None
if cfg.get('front_color_image'):
    front_path=ROOT/cfg['front_color_image']['path'];assert sha(front_path)==cfg['front_color_image']['sha256']
    front_image=bpy.data.images.load(str(front_path),check_existing=False);front_image.pack();FW,FH=front_image.size;front_pixels=np.asarray(front_image.pixels[:]).reshape(FH,FW,4);front_curves={}
    for name in ['upper','lower']:
        curve=np.asarray(cfg['front_'+name+'_edge_px'],float);curve_arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(curve,axis=0),axis=1))];front_curves[name]=(curve,curve_arc)
    front_data=(FW,FH,front_pixels,front_curves)
def nearest(points,boundary):
    ends=boundary['points'];a=ends[:-1];d=np.diff(ends,axis=0);lengths=(d*d).sum(axis=1);best=np.full(len(points),np.inf);arc=np.zeros(len(points))
    for i,(origin,delta)in enumerate(zip(a,d)):
        t=np.clip(((points-origin)@delta)/max(lengths[i],1e-16),0,1);q=origin+t[:,None]*delta;distance=np.linalg.norm(points-q,axis=1)*W;take=distance<best;best[take]=distance[take];arc[take]=boundary['arc'][i]+t[take]*(boundary['arc'][i+1]-boundary['arc'][i])
    return best,arc
def reflected(value,span):
    p=np.mod(value,2*span);return np.where(p<=span,p,2*span-p)
def sample(uv):return pixels[np.clip((uv[:,1]*H).astype(int),0,H-1),np.clip((uv[:,0]*W).astype(int),0,W-1)]
donor_records=[]
def color(points,uv,role,record=False):
    distances={name:nearest(points,b)for name,b in boundaries.items()};choose=distances['upper'][0]<=distances['lower'][0];result=sample(uv)if role==0 else np.tile(np.asarray([.025,.018,.012,1.]),(len(points),1));changed=np.zeros(len(points),bool)
    for name,flag,normal_sign in [('upper',True,-1),('lower',False,1)]:
        mask=choose==flag
        if not mask.any():continue
        dist,arc=distances[name];b=boundaries[name];phase=b['anchor']+np.minimum(arc[mask]-b['joins'][0],b['joins'][1]-arc[mask]);along=reflected(phase,b['source_arc'][-1]);source=b['source']
        if role==1:
            start=float(np.interp(cfg['oral_donor_start_px'],source[:,0],b['source_arc']));along=start+reflected(phase,b['source_arc'][-1]-start)
        sx=np.interp(along,b['source_arc'],source[:,0]);sy=np.interp(along,b['source_arc'],source[:,1]);segment=np.clip(np.searchsorted(b['source_arc'],along,side='right')-1,0,len(source)-2);tangent=source[segment+1]-source[segment];normal=np.stack([-tangent[:,1],tangent[:,0]],axis=1)*normal_sign;normal/=np.linalg.norm(normal,axis=1)[:,None]
        if role==0:
            across=np.minimum(dist[mask],cfg['skin_band_px']);amount=np.clip((cfg['skin_band_px']-dist[mask])/cfg['blend_px'],0,1);amount=amount*amount*(3-2*amount)
            front=np.clip(((points[mask,0]+.5)*W-cfg['front_blend_start_px'])/(cfg['front_blend_full_px']-cfg['front_blend_start_px']),0,1);amount*=front*front*(3-2*front)
            if cfg.get('preserve_side_pixels'):
                sections=read(ROOT/cfg['profile'])['body']['sections'];u=points[mask,0]+.5;width=np.interp(u,[r[0]for r in sections],[r[3]for r in sections]);side=np.abs(points[mask,1])/np.maximum(width,1e-8);fade=np.clip((side-.5)/.3,0,1);fade=fade*fade*(3-2*fade);cap=np.clip((u-cfg.get('cap_blend_start_u',1))/(cfg.get('cap_blend_full_u',1.001)-cfg.get('cap_blend_start_u',1)),0,1);cap=cap*cap*(3-2*cap);amount*=1-fade*(1-cap)
        else:
            other=boundaries['lower'if name=='upper'else'upper']['source'];other_y=np.interp(sx,other[:,0],other[:,1]);span=np.maximum(abs(other_y-sy)*.70,1.);across=-reflected(dist[mask],span);amount=np.ones(len(across))
        donor=np.stack([sx,sy],axis=1)+normal*across[:,None]
        if role==1:
            # Retain 2D dark oral pixels from the actual between-lip region;
            # keep depth samples away from cyan exterior skin, no flat RGB fill.
            fraction=.35+.30*reflected(dist[mask],10.)/10.;donor[:,0]=sx;donor[:,1]=sy+(other_y-sy)*fraction
        xy=np.rint(donor).astype(int);assert np.all((xy[:,0]>=0)&(xy[:,0]<W)&(xy[:,1]>=0)&(xy[:,1]<H));rgba=pixels[H-1-xy[:,1],xy[:,0]]
        if front_data is not None:
            # Material-only semantic transport along the ACTUAL current3D rim.
            # Generated image geometry/pixel registration is never adopted.
            FW,FH,front_pixels,front_curves=front_data;curve,curve_arc=front_curves[name];fraction=np.clip(arc[mask]/b['arc'][-1],0,1);front_along=fraction*curve_arc[-1];fx=np.interp(front_along,curve_arc,curve[:,0]);fy=np.interp(front_along,curve_arc,curve[:,1]);seg=np.clip(np.searchsorted(curve_arc,front_along,side='right')-1,0,len(curve)-2);tangent=curve[seg+1]-curve[seg];n=np.stack([-tangent[:,1],tangent[:,0]],axis=1)*normal_sign;n/=np.linalg.norm(n,axis=1)[:,None];ratio=curve_arc[-1]/b['arc'][-1]
            if role==0:front_xy=np.stack([fx,fy],axis=1)+n*np.minimum(dist[mask],cfg['skin_band_px'])[:,None]*ratio
            else:
                other_curve,other_arc=front_curves['lower'if name=='upper'else'upper'];other_along=fraction*other_arc[-1];other_xy=np.stack([np.interp(other_along,other_arc,other_curve[:,0]),np.interp(other_along,other_arc,other_curve[:,1])],axis=1);weight=.30+.40*reflected(dist[mask],10.)/10.;front_xy=np.stack([fx,fy],axis=1)*(1-weight[:,None])+other_xy*weight[:,None]
            fxy=np.rint(front_xy).astype(int);assert np.all((fxy[:,0]>=0)&(fxy[:,0]<FW)&(fxy[:,1]>=0)&(fxy[:,1]<FH));rgba=front_pixels[FH-1-fxy[:,1],fxy[:,0]]
        invalid=(amount>.001)&(rgba[:,3]<=.95)
        assert not invalid.any(),('Lip strip donor left opaque source',name,role,xy[invalid][:8].tolist())
        result[mask]=result[mask]*(1-amount[:,None])+rgba*amount[:,None];changed[mask]=amount>.001
        if record:
            locations=fxy if front_data is not None else xy
            donor_records.extend({'jaw':name,'role':'skin'if role==0 else'oral','source_kind':'generated_front_color'if front_data is not None else'original_side','source_xy':q.tolist()}for q in locations[amount>.001][::max(1,len(locations)//32)])
    if front_data is not None and role==0 and cfg.get('front_camera'):
        FW,FH,front_pixels,_=front_data;camera=cfg['front_camera'];u=points[:,0]+.5;native_y=H/2-points[:,2]*W;roof=np.interp(u*W,np.asarray(cfg['upper_inner_edge_px'])[:,0],np.asarray(cfg['upper_inner_edge_px'])[:,1]);sections=read(ROOT/cfg['profile'])['body']['sections'];width=np.interp(u,[r[0]for r in sections],[r[3]for r in sections]);side=np.abs(points[:,1])/np.maximum(width,1e-8)
        smooth=lambda t:np.clip(t,0,1)**2*(3-2*np.clip(t,0,1))
        amount=smooth((u-.94)/.02)*(1-smooth((side-.4)/.4))*smooth((roof-native_y-12)/16)
        x=.5+points[:,1]*camera['model_scale']/camera['width_m'];y=.5-(points[:,2]*camera['model_scale']-camera['focus_y_m'])/(camera['width_m']*camera['aspect_h_over_w']);inside=(x>=0)&(x<1)&(y>=0)&(y<1);amount*=inside
        fxy=np.stack([np.clip(np.floor(x*FW),0,FW-1),np.clip(np.floor(y*FH),0,FH-1)],axis=1).astype(int);rgba=front_pixels[FH-1-fxy[:,1],fxy[:,0]];result=result*(1-amount[:,None])+rgba*amount[:,None]
        if record:donor_records.extend({'jaw':'forehead','role':'skin','source_kind':'generated_front_color','source_xy':q.tolist()}for q in fxy[amount>.001][::max(1,len(fxy)//32)])
    result[:,3]=1;return result
tiles=[]
for face in mesh.polygons:
    role=face.material_index;assert role in[0,1];co=coords[list(face.vertices)];center=co.mean(axis=0);dist=min(nearest(co,b)[0].min()for b in boundaries.values())
    forehead=front_data is not None and cfg.get('front_camera')and co[:,0].max()+.5>.94
    if role==0 and not forehead and(dist>cfg['skin_band_px']+2 or co[:,0].max()+.5<cfg['start_u']):continue
    x=co[1]-co[0];x/=np.linalg.norm(x);normal=np.cross(co[1]-co[0],co[2]-co[0]);normal/=np.linalg.norm(normal);y=np.cross(normal,x);q=np.stack([(co-co[0])@x,(co-co[0])@y],axis=1)*W;low=np.floor(q.min(axis=0))-3;high=np.ceil(q.max(axis=0))+3;tw,th=(high-low+1).astype(int);assert tw*th<400000
    yy,xx=np.mgrid[:th,:tw];plane=np.stack([xx.ravel()+low[0],yy.ravel()+low[1]],axis=1);matrix=np.stack([q[1]-q[0],q[2]-q[0]],axis=1);v=(plane-q[0])@np.linalg.inv(matrix).T;bary=np.stack([1-v.sum(axis=1),v[:,0],v[:,1]],axis=1);bary=np.maximum(bary,0);bary/=bary.sum(axis=1)[:,None];uv=old_uv[list(face.loop_indices)];texels=color(bary@co,bary@uv,role,True).reshape(th,tw,4);tiles.append({'face':face.index,'role':role,'pixels':texels,'q':q-low,'w':tw,'h':th})
assert tiles;aw=1024;px=3;py=3;row=0
for tile in tiles:
    if px+tile['w']+3>aw:px=3;py+=row+3;row=0
    tile['at']=(px,py);px+=tile['w']+3;row=max(row,tile['h'])
ah=2**math.ceil(math.log2(py+row+3));atlas=np.ones((ah,aw,4),dtype='float32')
for t in tiles:x,y=t['at'];atlas[y:y+t['h'],x:x+t['w']]=t['pixels']
chart=bpy.data.images.new('Actual own lip edge and full2D source strip',aw,ah,alpha=True);chart.colorspace_settings.name=image.colorspace_settings.name;chart.pixels.foreach_set(atlas.ravel());chart.pack()
for role in[0,1]:
    mat=mesh.materials[0].copy();mat.name='Source lip skin chart'if role==0 else'Source lip oral roof-floor chart';next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE').image=chart;mesh.materials.append(mat)
for t in tiles:
    face=mesh.polygons[t['face']];face.material_index=2+t['role']
    for li,q in zip(face.loop_indices,t['q']):mesh.uv_layers.active.data[li].uv=((q[0]+t['at'][0]+.5)/aw,(q[1]+t['at'][1]+.5)/ah)
assert geometry()==frozen;out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));model=out/'fish.glb';proof=export_guarded(model)
d,b=read_glb(model)
for node in d['nodes']:
    if'mesh'not in node:continue
    for pr in d['meshes'][node['mesh']]['primitives']:
        mat=d['materials'][pr['material']];mat.update(alphaMode='OPAQUE'if node['name']==cfg['body']else'MASK',doubleSided=False)
        if mat['alphaMode']=='MASK':mat['alphaCutoff']=.5
for s in d['samplers']:s.update(magFilter=9728,minFilter=9728)
write_glb(model,d,b);node=next(n for n in d['nodes']if n.get('name')==cfg['body']);roles={str(i):('mouth'if 'oral'in d['materials'][pr['material']].get('name','').lower()else'body_skin')for i,pr in enumerate(d['meshes'][node['mesh']]['primitives'])};triangles=sum(d['accessors'][p['indices']]['count']//3 for m in d['meshes']for p in m['primitives']);assert triangles<=cfg['hard_triangles']
report={'ok':True,'kind':'actual_lip_2D_source_strip_authoring','input_blend_sha256':sha(a.blend),'config_sha256':sha(a.config),'geometry_weights_triangles_unchanged':geometry()==frozen,'whole_fish_triangles':triangles,'body_surface_roles':roles,'atlas_size':[aw,ah],'boundary_edges':{name:[list(e)for e in b['edges']]for name,b in boundaries.items()},'boundary_arc_native_pixels':{name:float(b['arc'][-1])for name,b in boundaries.items()},'donor_records':donor_records,'model_sha256':sha(model),'blend_sha256':sha(out/'fish.blend'),'normal_export':proof,'visual_review':'pending','scope':'Actual shared upper/lower lip boundaries; reflected complete curved2D source strip at native density. Hidden frontal/interior continuation is artistic. No geometry or flat forehead/chin rectangles. Requires actual mouth-first review.'};(out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'triangles':triangles,'roles':roles,'atlas':[aw,ah]}))
