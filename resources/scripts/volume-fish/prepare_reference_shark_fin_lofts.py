"""Freeze actual named same-species planar masks, roots and sparse sections."""
import argparse,hashlib,json
from pathlib import Path
import cv2,numpy as np

p=argparse.ArgumentParser();p.add_argument('--config',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();c=json.loads(a.config.read_text());records=[]
def sample(path,t):
    path=np.array(path,float);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))];u=np.clip(t,0,1)*arc[-1];return [float(np.interp(u,arc,path[:,i]))for i in range(2)]
for fin in c['fins']:
    path=Path(c['mask_directory'])/(fin['mask']+'.png');aimage=cv2.imread(str(path));mask=(aimage.max(2)<80).astype(np.uint8);contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE);poly=max(contours,key=cv2.contourArea)[:,0,:].astype(float);base=np.array(fin['root_endpoints_px']);ids=[int(np.linalg.norm(poly-p,axis=1).argmin())for p in base];tip=int(np.linalg.norm(poly-np.array(fin['tip_px']),axis=1).argmin())
    def walk(start,end,step):
        points=[poly[start].tolist()];i=start
        while i!=end:i=(i+step)%len(poly);points.append(poly[i].tolist())
        return points
    paths=[walk(ids[0],ids[1],step)for step in [1,-1]];free=next(path for path in paths if any(np.linalg.norm(np.array(q)-poly[tip])<.1 for q in path));root=next(path for path in paths if path is not free);it=min(range(len(free)),key=lambda i:np.linalg.norm(np.array(free[i])-poly[tip]));leading=free[:it+1];trailing=free[it:][::-1];levels=fin['span_levels'];chords=fin['chord_levels'];sections=[]
    for s in levels:
        left,right=np.array(sample(leading,s)),np.array(sample(trailing,s));sections.append([sample(root,q)if s==0 else (left*(1-q)+right*q).tolist()for q in chords])
    if fin['mask']=='Cfin' and not fin.get('boundary_cdt',False):
        # Complete horizontal connected intervals; never bridge a transparent notch.
        yy,xx=np.where(mask);lo,hi=int(yy.min()),int(yy.max());sections=[]
        levels_y=list(np.linspace(lo+1,hi-1,17))
        if fin.get('body_section_support'):
            ref=json.loads(Path(c['reference']).read_text());rear=ref['body_stations'][-1];mid=(rear['top_z_m']+rear['bottom_z_m'])/2;half=(rear['top_z_m']-rear['bottom_z_m'])/2;scale=c['metres_per_source_pixel'];height=ref['source_canvas']['height'];extra=sorted(set(round(height/2-(mid+half*np.cos(i*np.pi/4))/scale,7)for i in range(8)))
            removable=levels_y[1:-1]
            for y in extra:removable.remove(min(removable,key=lambda q:abs(q-y)))
            levels_y=sorted([levels_y[0],levels_y[-1],*removable,*extra])
        for y in levels_y:
            xs=np.where(mask[int(round(y))])[0];runs=np.split(xs,np.where(np.diff(xs)>1)[0]+1)
            # A one/two-pixel detached stair-step is raster noise, not a chord.
            # Never bridge a genuine notch or a second substantial interval.
            native_project=json.loads(Path(c['reference']).read_text()).get('kind')=='project_art_shark_shape_input'
            minimum_run=int(c.get('maximum_detached_raster_run_pixels',2 if native_project else 0))
            substantial=[run for run in runs if len(run)>minimum_run];assert len(substantial)==1,(y,'split chord requires explicit interval topology')
            xs=substantial[0];x0,x1=int(xs.min()),int(xs.max());sections.append([[float(x0+(x1-x0)*q),float(y)]for q in chords])
    if fin.get('boundary_cdt',False):
        work=mask.copy();a0,b0=np.array(fin['root_endpoints_px']);xattach=float(a0[0]);cv2.rectangle(work,(int(np.floor(xattach-3)),int(np.ceil(min(a0[1],b0[1])))),(int(np.ceil(xattach+3)),int(np.floor(max(a0[1],b0[1])))),1,-1)
        n,labels,stats,_=cv2.connectedComponentsWithStats(work);assert n==2,'Undeclared disconnected caudal component'
        con,_=cv2.findContours(work,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE);boundary=cv2.approxPolyDP(max(con,key=cv2.contourArea),1.1,True)[:,0,:].astype(float);points=boundary.tolist();lo=boundary.min(0);hi=boundary.max(0)
        for y in np.linspace(lo[1],hi[1],11)[1:-1]:
            for x in np.linspace(lo[0],hi[0],7)[1:-1]:
                if cv2.pointPolygonTest(boundary.astype(np.float32),(float(x),float(y)),True)>4:points.append([float(x),float(y)])
        fin=dict(fin,cdt_points_px=points,cdt_boundary_count=len(boundary),cdt_scope='Entire concave native contour including terminal notch. Only3px basal extension for exact body intersection.1.1px contour simplification; no bridging of multiple intervals.')
    records.append(dict(fin,source_path=str(path.resolve()),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),root_curve_px=root,leading_curve_px=leading,trailing_curve_px=trailing,sections_px=sections,tip_actual_px=poly[tip].tolist(),source_black_area_pixels=int(mask.sum())))
r=dict(c,rows=records,scope=c.get('source_scope','Same-species validation masks.')+' Placement/roll and normal thickness are declared engineering pose choices checked against published orthogonal figure; no unseen tissue metrology. Generic Sphyrna example parameters are not imported. Whole-fish source/material/rig/pose gates remain pending.');assert not a.output.exists();a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(fins=len(records),anatomical_count=sum(2 if r['paired']else 1 for r in records))))
