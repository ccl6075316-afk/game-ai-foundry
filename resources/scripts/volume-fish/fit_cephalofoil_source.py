"""Fit an existing swept cephalofoil to an accepted top-source silhouette.

Head width and maximum anterior X are fixed. The source is isotropically scaled
by head width, never independently stretched in X. Hidden central root height
is a documented construction inference. Rig, fins, source images and ventral
mouth UVs are preserved. The anterior body collar changes only in width.
"""
import argparse, base64, copy, hashlib, json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d
from freeze_surface_ownership import read_glb, accessor
from patch_existing_fin_meshes import write

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def fit(row, output):
    source, model = Path(row['top_source']), Path(row['model'])
    assert sha(source) == row['source_sha256'] and sha(model) == row['model_sha256']
    doc, blob = read_glb(model); old_doc = copy.deepcopy(doc); binary = bytearray(blob)
    wing = next(n for n in doc['nodes'] if n.get('name') == 'Cephalofoil')
    primitives = doc['meshes'][wing['mesh']]['primitives']
    vertices = np.concatenate([accessor(doc, blob, p['attributes']['POSITION']) for p in primitives])
    half = float(np.max(np.abs(vertices[:, 2]))); nose = float(vertices[:, 0].max())
    z = np.linspace(-half, half, 97)
    ring = np.rint((vertices[:, 2]+half)/(2*half)*96).astype(int)
    old_rear = np.array([vertices[ring == i, 0].min() for i in range(97)])
    old_front = np.array([vertices[ring == i, 0].max() for i in range(97)])
    im = np.asarray(Image.open(source).convert('RGBA')); mask = im[:, :, 3] > 240
    yy, xx = np.where(mask); xmax = int(xx.max())
    yy, xx = np.where(mask & (np.arange(im.shape[1])[None, :] > xmax*row['head_roi_min_x']))
    ymin, ymax = int(yy.min()), int(yy.max()); center = (ymin+ymax)/2
    scale = 2*half/(ymax-ymin); source_half = (ymax-ymin)/2
    # A source-pixel antialias margin keeps the terminal rings finite and closed.
    yp = center + z/half*(source_half-.75)
    front_rows=[]; rear_rows=[]
    for y in range(ymin, ymax+1):
        xs = np.where(mask[y] & (np.arange(im.shape[1]) > xmax*row['head_roi_min_x']))[0]
        assert len(xs), ('empty source head row', y)
        # Concave shoulders can have two separate opaque intervals on one row:
        # posterior neck and anterior wing. Never bridge the transparent gap.
        gaps=np.where(np.diff(xs)>5)[0]
        components=np.split(xs,gaps+1)
        substantial=[c for c in components if c[-1]-c[0]>=max(10,(ymax-ymin)*.02)]
        if substantial:xs=substantial[-1]
        front_rows.append(xs.max()); rear_rows.append(xs.min())
    front_src = np.interp(yp, np.arange(ymin,ymax+1), gaussian_filter1d(np.array(front_rows,dtype=float), .8))
    rear_src = np.interp(yp, np.arange(ymin,ymax+1), gaussian_filter1d(np.array(rear_rows,dtype=float), .8))
    # Pixel drawings have mild left/right asymmetry; do not bake it into anatomy.
    front_src = (front_src+front_src[::-1])/2; rear_src = (rear_src+rear_src[::-1])/2
    new_front = nose+(front_src-front_src.max())*scale
    sampled_rear = nose+(rear_src-front_src.max())*scale
    # The old central trailing edge was too far anterior, producing two hooks
    # where a corrected thick wing met the narrow old neck. Continue the source
    # cut through the hidden root, and fit the anterior body collar separately.
    new_rear = sampled_rear
    assert np.all(new_front-new_rear > .0001)
    gain = (new_front-new_rear)/(old_front-old_rear)
    offset = new_rear-gain*old_rear
    def transform(v):
        a = np.interp(v[:,2],z,gain); c=np.interp(v[:,2],z,offset)
        result=v.copy().astype(float);result[:,0]=a*v[:,0]+c
        # The hidden central collar rises into the actual body cross-section.
        # Keeping it at wing-tip height leaves its back wall outside the belly.
        wx=np.clip((result[:,0]-cut_x)/.070,0,1);wx=1-wx*wx*(3-2*wx)
        wz=np.clip((np.abs(v[:,2])/half-.18)/.24,0,1);wz=1-wz*wz*(3-2*wz)
        w=wx*wz;yc=np.interp(result[:,0],bx,(bymin+bymax)/2)
        result[:,1]=head_y+(v[:,1]-head_y)*(1-.5*w)+(yc-head_y)*w
        return result
    body_node=next(n for n in doc['nodes'] if n.get('name')=='Closed_body')
    body_vertices=np.concatenate([accessor(doc,blob,p['attributes']['POSITION']) for p in doc['meshes'][body_node['mesh']]['primitives']])
    bx=np.unique(body_vertices[:,0].round(5));bw=np.array([np.abs(body_vertices[np.abs(body_vertices[:,0]-x)<.000011,2]).max() for x in bx])
    bymin=np.array([body_vertices[np.abs(body_vertices[:,0]-x)<.000011,1].min() for x in bx])
    bymax=np.array([body_vertices[np.abs(body_vertices[:,0]-x)<.000011,1].max() for x in bx])
    head_y=float((vertices[:,1].min()+vertices[:,1].max())/2)
    head_halfheight=float(np.ptp(vertices[:,1])/2)
    fin_x=max(float(accessor(doc,blob,p['attributes']['POSITION'])[:,0].max()) for n in doc['nodes'] if 'mesh' in n and any(token in n['name'].lower() for token in ['pectoral','dorsal','pelvic','anal','caudal']) for p in doc['meshes'][n['mesh']]['primitives'])
    start=fin_x+.006
    cut_x=nose+(xmax*row['head_roi_min_x']-front_src.max())*scale
    assert cut_x>start+.01,(start,cut_x)
    source_cut=int(np.ceil(xmax*row['head_roi_min_x']))+2
    source_ys=np.where(mask[:,source_cut])[0]
    collar_width=float((source_ys.max()-source_ys.min())*.5*scale)
    sx=np.arange(int((start-nose)/scale+front_src.max())-2,source_cut+1)
    sw=np.array([(np.ptp(np.where(mask[:,int(x)])[0]))*.5*scale for x in sx])
    def body_gain(x):
        desired=np.interp((x-nose)/scale+front_src.max(),sx,sw)
        target=np.maximum(1.,desired/np.maximum(np.interp(x,bx,bw),.0001))
        blend=np.clip((x-start)/(cut_x-start),0,1);blend=blend*blend*(3-2*blend)
        fade=np.clip((x-cut_x-.005)/(float(bx.max())-cut_x-.005),0,1);fade=fade*fade*(3-2*fade)
        return 1+(target-1)*blend*(1-fade)
    def body_transform(v):
        result=v.copy().astype(float);result[:,2]*=body_gain(v[:,0])
        return result
    def add(values, template):
        data=np.asarray(values,dtype='<f4');binary.extend(b'\0'*(-len(binary)%4));start=len(binary);binary.extend(data.tobytes())
        vi=len(doc['bufferViews']);doc['bufferViews'].append(dict(buffer=0,byteOffset=start,byteLength=data.nbytes,target=34962))
        ac=copy.deepcopy(template);ac.update(bufferView=vi,byteOffset=0,count=len(data),componentType=5126,min=data.min(0).tolist(),max=data.max(0).tolist())
        idx=len(doc['accessors']);doc['accessors'].append(ac);return idx
    changed=[]
    for node in doc['nodes']:
        if 'mesh' not in node or not (node['name'] in ['Cephalofoil','Closed_body'] or node['name'].startswith('Textured_eye_')): continue
        assert not any(k in node for k in ['matrix','translation','rotation','scale'])
        eye_shift=None
        if node['name'].startswith('Textured_eye_'):
            ev=np.concatenate([accessor(old_doc,blob,p['attributes']['POSITION']) for p in doc['meshes'][node['mesh']]['primitives']])
            ec=(ev.max(0)+ev.min(0))/2
            target_z=float(ec[2])
            sample_z=float(np.sign(ec[2])*half*.975)
            ef=float(np.interp(sample_z,z,new_front));er=float(np.interp(sample_z,z,new_rear))
            # Preserve the spherical eye itself; a nonlinear wing warp would
            # stretch it into a pointed horn as the tip chord narrows.
            eye_shift=np.array([ef-(ef-er)*.20-ec[0],0,target_z-ec[2]])
        for surface,p in enumerate(doc['meshes'][node['mesh']]['primitives']):
            attrs=p['attributes'];v=accessor(old_doc,blob,attrs['POSITION']);is_body=node['name']=='Closed_body';nv=body_transform(v) if is_body else transform(v)
            if eye_shift is not None:nv=v+eye_shift
            attrs['POSITION']=add(nv,old_doc['accessors'][attrs['POSITION']])
            if surface==1 and node['name'] in ['Cephalofoil','Closed_body']:
                old_uv=accessor(old_doc,blob,attrs['TEXCOORD_0']).astype(float)
                projected=np.column_stack((((nv[:,0]-nose)/scale+front_src.max())/im.shape[1],(center-nv[:,2]/scale)/im.shape[0]))
                weight=np.ones(len(v))
                if not is_body:
                    ny=accessor(old_doc,blob,attrs['NORMAL'])[:,1]
                    weight=np.clip((ny-.20)/.55,0,1);weight=weight*weight*(3-2*weight)
                if is_body:
                    weight=np.clip((v[:,0]-start)/(cut_x-start),0,1);weight=weight*weight*(3-2*weight)
                uv=old_uv*(1-weight[:,None])+projected*weight[:,None]
                attrs['TEXCOORD_0']=add(uv,old_doc['accessors'][attrs['TEXCOORD_0']])
            eps=1e-5
            if 'NORMAL' in attrs:
                normal=accessor(old_doc,blob,attrs['NORMAL']).astype(float)
                if is_body:
                    g=body_gain(v[:,0]);dg=(body_gain(v[:,0]+eps)-body_gain(v[:,0]-eps))/(2*eps)
                    normal[:,0]-=v[:,2]*dg*normal[:,2]/g;normal[:,2]/=g
                elif eye_shift is None:
                    jac=np.empty((len(v),3,3))
                    for axis in range(3):
                        up=v.copy().astype(float);dn=v.copy().astype(float);up[:,axis]+=eps;dn[:,axis]-=eps
                        jac[:,:,axis]=(transform(up)-transform(dn))/(2*eps)
                    assert np.all(np.linalg.det(jac)>.01),'Folded cephalofoil map'
                    normal=np.linalg.solve(jac.transpose(0,2,1),normal[:,:,None])[:,:,0]
                normal/=np.maximum(np.linalg.norm(normal,axis=1),1e-12)[:,None]
                attrs['NORMAL']=add(normal,old_doc['accessors'][attrs['NORMAL']])
            assert 'TANGENT' not in attrs, 'Tangent transform must be implemented explicitly'
            changed.append(dict(mesh=node['name'],vertices=len(v),max_displacement=float(np.max(np.linalg.norm(nv-v,axis=1)))))
    assert bytes(binary[:len(blob)])==bytes(blob)
    for key in ['nodes','skins','animations','images','textures','materials']: assert doc.get(key)==old_doc.get(key)
    for node in doc['nodes']:
        if 'mesh' not in node:continue
        mesh=doc['meshes'][node['mesh']];old_mesh=old_doc['meshes'][node['mesh']]
        allowed=node['name'] in ['Cephalofoil','Closed_body'] or node['name'].startswith('Textured_eye_')
        if not allowed:assert mesh==old_mesh,'Changed fin or unrelated mesh'
        for si,(p,op) in enumerate(zip(mesh['primitives'],old_mesh['primitives'])):
            assert p['indices']==op['indices']
            for key in ['JOINTS_0','WEIGHTS_0']:assert p['attributes'].get(key)==op['attributes'].get(key)
            if not (node['name'] in ['Cephalofoil','Closed_body'] and si==1):assert p['attributes'].get('TEXCOORD_0')==op['attributes'].get('TEXCOORD_0')
            if node['name']=='Closed_body':
                old_v=accessor(old_doc,blob,op['attributes']['POSITION']);new_v=accessor(doc,binary,p['attributes']['POSITION'])
                assert np.array_equal(old_v[:,:2],new_v[:,:2])
                assert np.array_equal(old_v[old_v[:,0]<=start],new_v[old_v[:,0]<=start])
    target=output/(row['species']+'.glb');write(target,doc,binary)
    # Review uses source + actual mesh silhouette, not a plot of desired controls.
    def outline(d,b,color):
        raster=np.zeros((600,640),np.uint8)
        for n in d['nodes']:
            if 'mesh' not in n or not(n['name'] in ['Cephalofoil','Closed_body'] or n['name'].startswith('Textured_eye_')):continue
            for p in d['meshes'][n['mesh']]['primitives']:
                v=accessor(d,b,p['attributes']['POSITION']);tri=accessor(d,b,p['indices']).reshape(-1,3)
                q=np.rint(np.column_stack((560+(v[:,0]-nose)*500/(2*half),300-v[:,2]*500/(2*half)))).astype(np.int32)
                for face in tri: cv2.fillConvexPoly(raster,q[face],255)
        contours,_=cv2.findContours(raster,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        return ''.join('<path d="M '+' L '.join(f'{x},{y}' for x,y in c[:,0,:])+' Z" fill="none" stroke="'+color+'" stroke-width="2"/>' for c in contours)
    display_scale=500/(ymax-ymin)
    image_tag=f'<image x="{560-front_src.max()*display_scale}" y="{300-center*display_scale}" width="{im.shape[1]*display_scale}" height="{im.shape[0]*display_scale}" opacity=".8" href="data:image/png;base64,{base64.b64encode(source.read_bytes()).decode()}"/>'
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="650"><rect width="1280" height="650" fill="#162c38"/><defs><clipPath id="panel"><rect width="640" height="600"/></clipPath></defs>'
    for i,(d,b,color,label) in enumerate([(old_doc,blob,'#ffad60','修前'),(doc,binary,'#70e4c4','修后')]):
        svg+=f'<g transform="translate({i*640},35)" clip-path="url(#panel)">{image_tag}{outline(d,b,color)}</g><text x="{i*640+25}" y="28" fill="{color}" font-family="sans-serif" font-size="21">{row["label"]} · {label}</text>'
    svg+='<text x="25" y="638" fill="white" font-family="sans-serif" font-size="16">头宽统一、等比缩放；源图左右均值约束；中央不可见后缘保留结构推断。</text></svg>'
    (output/(row['species']+'-head.svg')).write_text(svg,encoding='utf8')
    return dict(species=row['species'],model=str(target.resolve()),model_sha256=sha(target),source_model_sha256=sha(model),source_sha256=sha(source),head_width=2*half,source_bounds_y=[ymin,ymax],source_front_max=float(front_src.max()),source_scale_to_model=scale,model_nose=nose,changes=changed,sections=[[float(zi),float(re+.5),float(fr+.5)] for zi,re,fr in zip(z,new_rear,new_front)],old_sections=[[float(zi),float(re+.5),float(fr+.5)] for zi,re,fr in zip(z,old_rear,old_front)],rig_fins_images_preserved=True,ventral_mouth_uv_preserved=True,top_uv_reprojected=True,body_side_xy_preserved=True,collar=dict(start_x=start,source_cut_x=cut_x,half_width=collar_width,fin_max_x=fin_x),visual_review='pending',hidden_root_height_inferred=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    plan=json.loads(a.plan.read_text(encoding='utf8'));a.output.mkdir(parents=True,exist_ok=True)
    rows=[fit(row,a.output) for row in plan['items']]
    report=dict(ok=True,status='done',next_action='human_review',items=rows,script_sha256=sha(Path(__file__)),plan_sha256=sha(a.plan),scope='Candidate geometry only; all imported runtime gates pending.')
    (a.output/'fit.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({'ok':True,'species':[r['species'] for r in rows]}))
if __name__=='__main__':main()
