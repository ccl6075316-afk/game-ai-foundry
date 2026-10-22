"""Replace only an anterior head shell using frozen source lip/outline curves.

The posterior cut follows the actual old mesh boundary. Fins, images, rig and
animation buffers remain byte-for-byte in the original BIN prefix. This is an
explicit species/source plan, not a universal rounded-snout recipe.
"""
import argparse,copy,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator,CubicHermiteSpline
from scipy.ndimage import gaussian_filter1d
from freeze_surface_ownership import read_glb,accessor
from patch_existing_fin_meshes import write

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def key(v):return tuple(np.round(v,7))
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);a=ap.parse_args()
    plan=json.loads(a.plan.read_text());reports=[]
    for p in plan['items']:
        assert sha(p['source'])==p['source_sha256'];assert sha(p['source_image'])==p['source_image_sha256']
        d,b=read_glb(Path(p['source']));old=copy.deepcopy(d);binary=bytearray(b)
        node=next(n for n in d['nodes'] if n.get('name')=='Closed_body' and 'mesh' in n);mi=node['mesh'];pr=d['meshes'][mi]['primitives'];assert len(pr)==2
        assert not any(k in node for k in ['matrix','translation','rotation','scale'])
        source=[{k:accessor(d,b,i).copy() for k,i in q['attributes'].items()} for q in pr]
        oldfaces=[accessor(d,b,q['indices']).reshape(-1,3) for q in pr]
        cut=float(p['join_u'])-.5
        assert source[1]['POSITION'][:,0].min()>cut+1e-5,'Join must be behind the real mouth corner'
        values={k:[v.copy() for v in arr] for k,arr in source[0].items()};faces=[];intersections={}
        def cross(i,j):
            pair=tuple(sorted([i,j]))
            if pair in intersections:return intersections[pair]
            vv=source[0]['POSITION'];t=float((cut-vv[i,0])/(vv[j,0]-vv[i,0]));idx=len(values['POSITION'])
            for name,arr in source[0].items():
                if name in ['JOINTS_0','WEIGHTS_0']:continue
                v=arr[i]*(1-t)+arr[j]*t
                if name=='POSITION':v[0]=cut
                if name in ['NORMAL','TANGENT']:v[:3]/=max(np.linalg.norm(v[:3]),1e-12)
                values[name].append(v)
            influences=defaultdict(float)
            for vertex,amount in [(i,1-t),(j,t)]:
                for bone,w in zip(source[0]['JOINTS_0'][vertex],source[0]['WEIGHTS_0'][vertex]):influences[int(bone)]+=float(w)*amount
            n=source[0]['JOINTS_0'].shape[1];best=sorted(influences.items(),key=lambda z:z[1],reverse=True)[:n]
            while len(best)<n:best.append((0,0.))
            total=sum(v for _,v in best);values['JOINTS_0'].append(np.array([i for i,_ in best]));values['WEIGHTS_0'].append(np.array([v/total for _,v in best]));intersections[pair]=idx
            return idx
        for face in oldfaces[0]:
            poly=[]
            for i,j in zip(face,np.roll(face,-1)):
                inside=source[0]['POSITION'][i,0]<=cut
                if inside:poly.append(int(i))
                if inside!=(source[0]['POSITION'][j,0]<=cut):poly.append(cross(int(i),int(j)))
            for i in range(1,len(poly)-1):faces.append([poly[0],poly[i],poly[i+1]])
        cut_edges=Counter()
        for face in faces:
            for i,j in zip(face,np.roll(face,-1)):
                if abs(values['POSITION'][i][0]-cut)<1e-7 and abs(values['POSITION'][j][0]-cut)<1e-7:
                    cut_edges[tuple(sorted([key(values['POSITION'][i]),key(values['POSITION'][j])]))]+=1
        edges=[e for e,n in cut_edges.items() if n==1 and e[0]!=e[1]];graph=defaultdict(list)
        for aa,zz in edges:graph[aa].append(zz);graph[zz].append(aa)
        assert graph and all(len(v)==2 for v in graph.values()),'Posterior section is not one closed loop'
        start=next(iter(graph));loop=[start];previous=None;current=start
        while True:
            following=next(q for q in graph[current] if q!=previous)
            if following==start:break
            assert following not in loop,'Multiple section loops';loop.append(following);previous,current=current,following
        assert len(loop)==len(graph)
        index_lookup={key(v):i for i,v in enumerate(values['POSITION'])};ids=[index_lookup[q] for q in loop]
        boundary=np.array([values['POSITION'][i] for i in ids]);center=(boundary.min(0)+boundary.max(0))*.5
        # Rotate/reverse the real boundary to match the canonical upper/lower
        # traversal. The first index is the left lateral point closest to lips.
        image=np.array(Image.open(p['source_image']).convert('RGBA'));h,w=image.shape[:2];aspect=h/w
        alpha=(image[:,:,3]>=200).astype(np.uint8)
        count,labels,stats,_=cv2.connectedComponentsWithStats(alpha,8)
        alpha=labels==(1+np.argmax(stats[1:,cv2.CC_STAT_AREA]))
        columns=np.arange(w);top=np.full(w,np.nan);bottom=top.copy()
        for x in range(round(p['join_u']*w)-4,w):
            yy=np.flatnonzero(alpha[:,x])
            if len(yy):top[x]=yy[0];bottom[x]=yy[-1]
        known=np.flatnonzero(np.isfinite(top));assert len(known)>30
        top=gaussian_filter1d(np.interp(columns,known,top[known]),8.);bottom=gaussian_filter1d(np.interp(columns,known,bottom[known]),8.)
        lip=np.array(p['lip_pixels'],float);roof=PchipInterpolator(lip[:,0]/w,lip[:,1]/h);floor=PchipInterpolator(lip[:,0]/w,lip[:,2]/h)
        mouth_u=float(lip[0,0]/w);end_u=float(p['end_u']);assert p['join_u']<mouth_u<end_u
        old_width=float(np.max(abs(boundary[:,2])));width_stations=np.array([[p['join_u'],old_width]]+p['half_width_stations'],float)
        width=PchipInterpolator(width_stations[:,0],width_stations[:,1])
        old_envelope=None
        if p.get('outer_envelope_blend_end_u'):
            end_blend=float(p['outer_envelope_blend_end_u']);assert p['join_u']<end_blend<mouth_u
            triangles=source[0]['POSITION'][oldfaces[0]].astype(float);envelope=[]
            for uu in np.linspace(p['join_u'],end_blend,64):
                points=[];sx=uu-.5
                for ia,ib in [(0,1),(1,2),(2,0)]:
                    va=triangles[:,ia];vb=triangles[:,ib];hit=(va[:,0]-sx)*(vb[:,0]-sx)<0;va=va[hit];vb=vb[hit];t=(sx-va[:,0])/(vb[:,0]-va[:,0]);points.extend(va+t[:,None]*(vb-va))
                points=np.array(points);assert len(points)>2;envelope.append([uu,points[:,1].max(),points[:,1].min(),abs(points[:,2]).max()])
            old_envelope=np.array(envelope)
            tangents=width.derivative()(width_stations[:,0]);tangents[0]=(old_envelope[1,3]-old_envelope[0,3])/(old_envelope[1,0]-old_envelope[0,0])
            width=CubicHermiteSpline(width_stations[:,0],width_stations[:,1],tangents)
            assert np.all(width(np.linspace(p['join_u'],p['end_u'],500))>0.)
        def section(u):
            x=u*w;lo=float(np.interp(x,columns,bottom));hi=float(np.interp(x,columns,top))
            top_y=(.5-hi/h)*aspect;bottom_y=(.5-lo/h)*aspect
            if old_envelope is not None and u<old_envelope[-1,0]:
                blend=np.clip((u-p['join_u'])/(old_envelope[-1,0]-p['join_u']),0.,1.);blend=blend*blend*(3.-2.*blend)
                top_y=float(np.interp(u,old_envelope[:,0],old_envelope[:,1]))*(1.-blend)+top_y*blend
                bottom_y=float(np.interp(u,old_envelope[:,0],old_envelope[:,2]))*(1.-blend)+bottom_y*blend
            cy=(top_y+bottom_y)*.5;ry=(top_y-bottom_y)*.5
            at=max(mouth_u,min(end_u,u));ru=float(roof(at));fl=float(floor(at))
            if u<mouth_u:ru=fl=(ru+fl)*.5
            else:
                fade=np.clip((u-mouth_u)/float(p['corner_blend_u']),0.,1.);fade=fade*fade*(3-2*fade);middle=(ru+fl)*.5;gap=(fl-ru)*fade;ru=middle-gap*.5;fl=middle+gap*.5
            ry=max(ry,1e-5);upper=np.clip((.5-ru)*aspect,bottom_y+ry*.03,top_y-ry*.03);lower=np.clip((.5-fl)*aspect,bottom_y+ry*.03,upper)
            return cy,ry,float(width(u)),upper,lower
        cy,ry,rz,upper,lower=section(mouth_u)
        start_point=np.array([cut,(upper+lower)/2,-old_width]);pivot=np.linalg.norm(boundary-start_point,axis=1).argmin();ids=ids[pivot:]+ids[:pivot]
        boundary=np.array([values['POSITION'][i] for i in ids])
        if boundary[1,1]<boundary[-1,1]:ids=[ids[0]]+list(reversed(ids[1:]));boundary=np.array([values['POSITION'][i] for i in ids])
        n=len(ids)
        old_cy=(boundary[:,1].max()+boundary[:,1].min())*.5;old_ry=np.ptp(boundary[:,1])*.5
        angle=np.unwrap(np.arctan2(boundary[:,2]/old_width,(boundary[:,1]-old_cy)/old_ry))
        assert np.all(np.diff(angle)>-1e-4),'Section angles must follow the actual loop'
        right=np.array([cut,boundary[0,1],old_width])
        nup=int(np.linalg.norm(boundary-right,axis=1).argmin());nlow=n-nup;assert nup>=4 and nlow>=4
        end_angle=angle[0]+2*np.pi
        upper_t=(angle[:nup+1]-angle[0])/(angle[nup]-angle[0])
        lower_t=(np.r_[angle[nup:],end_angle]-angle[nup])/(end_angle-angle[nup])
        # Re-sample by the existing loop's index; every posterior edge is retained.
        canonical_count=n;previous_ring=ids
        new_skin_start=len(values['POSITION']);oral_values={k:[] for k in values};oral_faces=[]
        if 'TEXCOORD_1' not in values:
            values['TEXCOORD_1']=[np.zeros(2) for _ in values['POSITION']];oral_values['TEXCOORD_1']=[]
        template={k:np.asarray(v)[ids].copy() for k,v in values.items()}
        def add_point(target,position,uv,upper_flag,half_width=0.,sample_index=0):
            index=len(target['POSITION'])
            for name in target:
                if name=='POSITION':v=np.array(position,float)
                elif name=='NORMAL':v=template[name][sample_index%n].copy()
                elif name=='TANGENT':v=np.array([0.,1.,0.,1.])
                elif name=='TEXCOORD_0':v=np.asarray(uv)
                elif name=='TEXCOORD_1':v=np.array([half_width,upper_flag])
                else:v=template[name][sample_index%n].copy()
                target[name].append(v)
            return index
        def add_skin(position,upper_flag,sample_index=0,front=False,tvertical=None):
            u=position[0]+.5;v=.5-position[1]/aspect
            if front:
                donor_u=float(p['front_donor_u']);cy0,ry0,_,ru0,fl0=section(donor_u)
                top0=cy0+ry0;bottom0=cy0-ry0
                y=(ru0+(top0-ru0)*tvertical if upper_flag else fl0+(bottom0-fl0)*tvertical)
                y+=(-1 if upper_flag else 1)*2/w
                u=donor_u;v=.5-y/aspect
            return add_point(values,position,[u,v],upper_flag,sample_index=sample_index)
        rings=np.unique(np.r_[np.linspace(p['join_u']+.00025,mouth_u,int(p.get('premouth_rings',8))),np.linspace(mouth_u,end_u,int(p['longitudinal_rings']))])
        corner_up=None;corner_low=None;roof_previous=None;floor_previous=None
        for u in rings:
            cy,ry,rz,upper,lower=section(float(u));theta_up=float(np.arccos(np.clip((upper-cy)/ry,-1,1)));theta_low=float(np.arccos(np.clip((lower-cy)/ry,-1,1)))
            uppers=[];lowers=[]
            for i in range(nup+1):
                theta=-theta_up+2*theta_up*float(upper_t[i]);point=np.array([u-.5,cy+ry*np.cos(theta),rz*np.sin(theta)])
                if i in [0,nup]:point[1]=upper
                if u<mouth_u:
                    blend=np.clip((u-p['join_u'])/(mouth_u-p['join_u']),0,1);blend=blend*blend*(3-2*blend)
                    reference=boundary[i%n];point[1:]=reference[1:]*(1-blend)+point[1:]*blend
                uppers.append(add_skin(point,1,i))
            for i in range(nlow+1):
                theta=theta_low+(2*np.pi-2*theta_low)*float(lower_t[i]);point=np.array([u-.5,cy+ry*np.cos(theta),rz*np.sin(theta)])
                if i in [0,nlow]:point[1]=lower
                if u<mouth_u:
                    blend=np.clip((u-p['join_u'])/(mouth_u-p['join_u']),0,1);blend=blend*blend*(3-2*blend)
                    reference=boundary[(nup+i)%n];point[1:]=reference[1:]*(1-blend)+point[1:]*blend
                if u<=mouth_u and i==0:lowers.append(uppers[-1])
                elif u<=mouth_u and i==nlow:lowers.append(uppers[0])
                else:lowers.append(add_skin(point,0,nup+i))
            if u<=mouth_u:
                ring=uppers[:-1]+lowers[:-1]
                for i in range(n):
                    j=(i+1)%n;faces.extend([[previous_ring[i],ring[i],ring[j]],[previous_ring[i],ring[j],previous_ring[j]]])
                previous_ring=ring;corner_up=uppers;corner_low=lowers
            else:
                for oldrow,newrow in [(corner_up,uppers),(corner_low,lowers)]:
                    for i in range(len(newrow)-1):faces.extend([[oldrow[i],newrow[i],newrow[i+1]],[oldrow[i],newrow[i+1],oldrow[i+1]]])
                corner_up=uppers;corner_low=lowers
            if u>=mouth_u:
                roof_ids=[];floor_ids=[];steps=int(p['oral_across'])
                for flag,row_y,arc in [(1,upper,uppers),(0,lower,lowers)]:
                    za=values['POSITION'][arc[0]][2];zb=values['POSITION'][arc[-1]][2]
                    # Lower arc traverses right to left; roof traverses left to right.
                    row_ids=[]
                    for i in range(steps+1):
                        z=za+(zb-za)*i/steps;point=[u-.5,row_y,z]
                        uv=[u,.5-row_y/aspect];row_ids.append(add_point(oral_values,point,uv,flag,max(abs(za),abs(zb)),sample_index=0))
                    if flag:roof_ids=row_ids
                    else:floor_ids=row_ids
                if roof_previous is not None:
                    for oldrow,newrow in [(roof_previous,roof_ids),(floor_previous,floor_ids)]:
                        for i in range(steps):oral_faces.extend([[oldrow[i],newrow[i],newrow[i+1]],[oldrow[i],newrow[i+1],oldrow[i+1]]])
                roof_previous=roof_ids;floor_previous=floor_ids
        # Canonical upper/lower arcs traverse opposite to the exterior's
        # outward winding. Keep the posterior and inward oral lining intact.
        new_faces_start=sum(1 for face in faces if all(values['POSITION'][i][0]<=cut+1e-8 for i in face))
        faces[new_faces_start:]=[[f[0],f[2],f[1]] for f in faces[new_faces_start:]]
        # Each anterior lip section gets a shallow convex skin cap. No tapered
        # single-pole snout and no repeated side-outline texture at the front.
        for flag,arc,oralrow in [(1,corner_up,roof_previous),(0,corner_low,floor_previous)]:
            polygon=list(arc)
            for i in reversed(oralrow[1:-1]):
                pos0=oral_values['POSITION'][i];polygon.append(add_skin(pos0,flag,front=True,tvertical=0.))
            pts=np.array([values['POSITION'][i] for i in polygon]);center_pos=pts.mean(0);center_pos[0]+=.00015
            cy,ry,rz,ru,fl=section(end_u);height=(cy+ry-ru if flag else fl-(cy-ry));tvertical=abs(center_pos[1]-(ru if flag else fl))/max(height,1e-7)
            center_id=add_skin(center_pos,flag,front=True,tvertical=tvertical)
            for i in range(len(polygon)):faces.append([center_id,polygon[i],polygon[(i+1)%len(polygon)]])
        # Welded-coordinate edge counts expose any missing oral/skin joins.
        arrays_out=[];indices_out=[]
        for vals,ff in [(values,faces),(oral_values,oral_faces)]:
            vv=np.asarray(vals['POSITION']);tt=np.asarray(ff,np.int64)
            area=np.linalg.norm(np.cross(vv[tt[:,1]]-vv[tt[:,0]],vv[tt[:,2]]-vv[tt[:,0]]),axis=1);tt=tt[area>1e-16]
            used=np.unique(tt);remap=np.full(len(vv),-1,np.int64);remap[used]=np.arange(len(used));tt=remap[tt]
            arr={k:np.asarray(v)[used] for k,v in vals.items()};arrays_out.append(arr);indices_out.append(tt)
        edge_counts=Counter();directed_edges=Counter()
        for arr,tt in zip(arrays_out,indices_out):
            keys=[key(v) for v in arr['POSITION']]
            for face in tt:
                for i,j in zip(face,np.roll(face,-1)):
                    if keys[i]!=keys[j]:edge_counts[tuple(sorted([keys[i],keys[j]]))]+=1;directed_edges[(keys[i],keys[j])]+=1
        bad=[(e,n) for e,n in edge_counts.items() if n!=2]
        if bad:
            print('BAD_EDGES',[(list(map(list,e)),n) for e,n in bad],flush=True)
        assert not bad,('Head is not closed/manifold',len(bad),bad[:3])
        assert all(count==directed_edges[(bb,aa)] for (aa,bb),count in directed_edges.items()),'Inconsistent exterior/lining winding'
        def append(array,typ,component=5126):
            array=np.asarray(array,dtype={5126:'<f4',5123:'<u2',5125:'<u4'}[component]);binary.extend(b'\0'*(-len(binary)%4));offset=len(binary);binary.extend(array.tobytes());vi=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':array.nbytes,'target':34963 if typ=='SCALAR' else 34962});ac={'bufferView':vi,'componentType':component,'count':len(array),'type':typ}
            if typ!='SCALAR':ac.update(min=array.min(0).tolist(),max=array.max(0).tolist())
            ix=len(d['accessors']);d['accessors'].append(ac);return ix
        for surface,(arr,tt) in enumerate(zip(arrays_out,indices_out)):
            vv=arr['POSITION'];nn=np.zeros_like(vv);fn=np.cross(vv[tt[:,1]]-vv[tt[:,0]],vv[tt[:,2]]-vv[tt[:,0]])
            for j in range(3):np.add.at(nn,tt[:,j],fn)
            grouped=defaultdict(lambda:np.zeros(3))
            for i,v in enumerate(vv):grouped[key(v)]+=nn[i]
            nn=np.array([grouped[key(v)] for v in vv])
            nn/=np.maximum(np.linalg.norm(nn,axis=1)[:,None],1e-12)
            if surface==0 and p.get('preserve_join_shading_u'):
                blend=np.clip((vv[:,0]-cut)/float(p['preserve_join_shading_u']),0.,1.);blend=blend*blend*(3.-2.*blend)
                nn=arr['NORMAL']*(1.-blend[:,None])+nn*blend[:,None]
                nn/=np.maximum(np.linalg.norm(nn,axis=1)[:,None],1e-12)
            # Retain all original posterior custom normals; new head normals
            # are independently oriented by the final topology below.
            if surface==0:nn[vv[:,0]<=cut+1e-8]=arr['NORMAL'][vv[:,0]<=cut+1e-8]
            arr['NORMAL']=nn
            for name,value in arr.items():
                typ='VEC'+str(value.shape[1]);component=5123 if name.startswith('JOINTS') else 5126
                pr[surface]['attributes'][name]=append(value,typ,component)
            pr[surface]['indices']=append(tt.reshape(-1),'SCALAR',5125)
        assert bytes(binary[:len(b)])==bytes(b)
        for k in ['nodes','skins','animations','images','materials','textures','samplers']:assert d.get(k)==old.get(k),k
        for i,mesh in enumerate(d['meshes']):
            if i!=mi:assert mesh==old['meshes'][i],'Non-body mesh changed'
        target=Path(p['target']);target.parent.mkdir(parents=True,exist_ok=True);write(target,d,binary)
        reports.append({'species':p['species'],'source_sha256':p['source_sha256'],'model_sha256':sha(target),'source_image_sha256':p['source_image_sha256'],'join_u':p['join_u'],'posterior_loop_vertices':n,'skin_vertices':len(arrays_out[0]['POSITION']),'oral_vertices':len(arrays_out[1]['POSITION']),'welded_edges_all_two':True,'all_fins_rig_animation_images_original_bin_preserved':True,'limits':'Transverse width and shallow anterior convexity are explicit art inferences; actual source/gray-model/multi-view and complete fin/body gates remain mandatory.'})
        print('REBUILT_SOURCE_HEAD',p['species'],flush=True)
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps({'ok':True,'plan_sha256':sha(a.plan),'script_sha256':sha(__file__),'items':reports},indent=2)+'\n')
if __name__=='__main__':main()
