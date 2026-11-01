"""Prepare a new shark cage from project side/top test artwork, never scan masks.

The generated front/top/bottom views are artistic references, not biological
measurements. The side source canvas remains the longitudinal/material ruler.
"""
from pathlib import Path
import json,hashlib,argparse
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import binary_fill_holes

def prepare(cp,out):
    c=json.loads(cp.read_text());assert not out.exists();out.mkdir();sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest();profile=json.loads(Path(c['art_profile']).read_text());side=Image.open(c['side']).convert('RGBA');W,H=side.size;length=c['display_length_m'];rear=c['body_rear_u'];axis=(1-rear)*length;origin=(1+rear)/2;aspect=H/W
    # Source-profile side landmarks are a starting control polygon, recorded
    # against the original image; native silhouette review still blocks release.
    sections=np.array(profile['body']['sections']+c['additional_side_sections']);sections=sections[np.argsort(sections[:,0])]
    top=np.array(Image.open(c['clean_top']).convert('RGBA'));mask=top[:,:,3]>=c['top_alpha_threshold'];TH,TW=mask.shape;rows=[];source_widths=[]
    for t in np.linspace(0,1,c['body_stations']):
        u=1-(1-rear)*t;x=int(round(u*(TW-1)));x=np.clip(x,0,TW-1);ys=np.where(mask[:,x])[0]
        width=(ys[-1]-ys[0])/TW*length if len(ys)>1 else 0.0001
        hi,lo=np.interp(u,sections[:,0],sections[:,1]),np.interp(u,sections[:,0],sections[:,2]);rows.append(dict(t=float(t),x_m=axis*(.5-t),top_z_m=(.5-hi)*aspect*length,bottom_z_m=(.5-lo)*aspect*length,full_width_m=float(width),project_source_u=float(u),side_top_bottom_px=[float(hi*H),float(lo*H)],top_width_source_px=[int(ys[0]),int(ys[-1])]if len(ys)else[]));source_widths.append(width)
    neck_x=int(c['head_neck_u']*(TW-1));neck_y=np.where(mask[:,neck_x])[0];neck_width=(neck_y[-1]-neck_y[0])/TW*length
    for row in rows:
        if row['project_source_u']>c['head_neck_u']:
            row['full_width_m']=max(.0001,neck_width*(1-row['project_source_u'])/(1-c['head_neck_u']));row['width_role']='Internal core inside separately traced head; not head span or biological measurement.'
    # Head planform: trace the generated project head, with an explicit neck
    # ownership cut in its same canvas; no external model outline is loaded.
    roi=int(c['head_neck_u']*TW);ys,xs=np.where(mask[:,roi:]);head_lo,head_hi=int(ys.min()),int(ys.max());center=(head_lo+head_hi)/2;head=[]
    for y in np.linspace(head_lo,head_hi,c['head_rows']):
        iy=int(round(y));xx=np.where(mask[iy,roi:])[0]+roi;assert len(xx)
        head.append(dict(y_m=(y-center)/TW*length,front_x_m=(float(xx.max())/(TW-1)-origin)*length,rear_x_m=(float(xx.min())/(TW-1)-origin)*length,project_top_row_px=iy,project_front_rear_px=[int(xx.max()),int(xx.min())]))
    span=head[-1]['y_m']-head[0]['y_m'];depth=max(r['front_x_m']for r in head)-min(r['rear_x_m']for r in head);peak=max((r for r in rows if r['project_source_u']<c['head_neck_u']),key=lambda r:r['full_width_m'])
    mouth=c['mouth'];head_side=[r for r in rows if c['head_neck_u']<=r['project_source_u']<=.98];thickness=max(r['top_z_m']-r['bottom_z_m']for r in head_side)
    reference=dict(kind='project_art_shark_shape_input',species=profile['species'],scientific_name='Sphyrna lewini',reference_body_axis_m=axis,body_axis_definition='Project side-art body from u=1 to tail root; display metres, not measured biological TL.',body_axis_max_width_m=peak['full_width_m'],maximum_body_width_over_body_axis=peak['full_width_m']/axis,body_width_peak_t=peak['t'],body_stations=rows,head_transverse_stations=head,head_span_m=span,head_axial_extent_m=depth,body_mask_axis_pixels=dict(ventral=(1-rear)*TW),mouth_trial=mouth,cross_section_and_head_thickness=dict(head_projected_full_thickness_over_span=thickness/span),head_mid_z_from_side=True,source_canvas=dict(width=W,height=H,length_m=length,body_rear_u=rear,origin_u=origin),geometry_authority='Project accepted side and same-project generated dorsal form; no scanned/finished-model body or fin masks.',sources={k:dict(path=c[k],sha256=sha(c[k]))for k in['side','clean_top','front','bottom']},formal_acceptance=False)
    reference['inputs']=reference['sources']
    (out/'reference.input.json').write_text(json.dumps(reference,indent=2)+'\n')
    masks=out/'native-fin-masks';masks.mkdir();fins=[];fin_profiles=[f for f in profile['fins']if not f['name'].startswith('Caudal')]
    for f in fin_profiles:
        polygon=f['polygon'];name=f['name']
        if name in c.get('fin_polygon_overrides',{}):polygon=[[x/W,y/H]for x,y in c['fin_polygon_overrides'][name]]
        im=Image.new('L',(W,H),0);ImageDraw.Draw(im).polygon([(x*W,y*H)for x,y in polygon],fill=255);a=np.array(im)>0
        # Native alpha gives the exact visible free edge; the explicit internal
        # root path owns the still-hidden fin tissue inside the body.
        a&=np.array(side)[:,:,3]>128;result=np.where(a[:,::-1],0,255).astype(np.uint8);Image.fromarray(result).convert('RGB').save(masks/(name+'.png'))
        endpoints=c['fin_roots_px'][name];tip=[f['tip'][0]*W,f['tip'][1]*H];front=endpoints[0];settings=c['fin_settings'][name];fins.append(dict(name=name,mask=name,paired=f['paired'],ventral=f['tip'][1]>f['anchor'][1],root_endpoints_px=[[W-1-x,y]for x,y in endpoints],tip_px=[W-1-tip[0],tip[1]],onset_t=(1-front[0]/W)/(1-rear),root_full_thickness_m=settings['root_full_thickness_m'],span_levels=settings['span_levels'],chord_levels=settings['chord_levels'],roll_degrees=settings.get('roll_degrees',0),root_z_offset_m=settings.get('root_z_offset_m',0),project_source_projection=True,source_canvas_height_px=H,source_source_width_px=W,exact_complete_body_intersection=True))
    im=Image.new('L',(W,H),0);draw=ImageDraw.Draw(im)
    for f in profile['fins']:
        if f['name'].startswith('Caudal'):draw.polygon([(x*W,y*H)for x,y in f['polygon']],fill=255)
    a=np.array(im)>0;a&=np.array(side)[:,:,3]>128;Image.fromarray(np.where(a[:,::-1],0,255).astype(np.uint8)).convert('RGB').save(masks/'Cfin.png');endpoints=c['fin_roots_px']['Caudal'];front=endpoints[0];settings=c['fin_settings']['Caudal'];fins.append(dict(name='Caudal',mask='Cfin',paired=False,ventral=False,root_endpoints_px=[[W-1-x,y]for x,y in endpoints],tip_px=[W-1-7,28],onset_t=(1-front[0]/W)/(1-rear),anchor_z_m=(H/2-front[1])*length/W,plane_rotation_degrees=0,root_full_thickness_m=settings['root_full_thickness_m'],span_levels=[0,.1,.3,.5,.7,.9,.99],chord_levels=settings['chord_levels'],exact_complete_body_intersection=True))
    layout=dict(species=profile['species'],scientific_name='Sphyrna lewini',mask_directory=str(masks.resolve()),reference=str((out/'reference.input.json').resolve()),baseline=c['future_body_baseline'],metres_per_source_pixel=length/W,edge_full_thickness_m=c['edge_full_thickness_m'],fins=fins,geometry_source_provenance='Only project accepted source-art fin cutouts, horizontally mirrored into author coordinates; no external finished/scanned contour.');(out/'fin-layout.config.json').write_text(json.dumps(layout,indent=2)+'\n');print(json.dumps(dict(ok=True,head_span_m=span,body_max_width_m=peak['full_width_m'],head_depth_m=depth,body_axis_m=axis,anatomical_fins=8)))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',required=True,type=Path);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args();prepare(args.config.resolve(),args.output.resolve())
