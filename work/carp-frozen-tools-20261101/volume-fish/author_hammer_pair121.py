"""Freeze individually reviewed hammerhead landmarks; trace fins from source alpha.

These are production inferences, not anatomical measurements. The two side
sources have different layouts. Never apply their numbers to other fish.
"""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]


def outline(image, box, baseline, tip, direction):
    h, w = image.shape[:2]
    yy, xx = np.mgrid[:h, :w]
    u, v = (xx + .5) / w, (yy + .5) / h
    mask = (image[:, :, 3] > 128) & (u >= box[0]) & (u <= box[2]) & (v >= box[1]) & (v <= box[3])
    a, b = np.array(baseline[0]), np.array(baseline[-1])
    if direction=='posterior':distance=a[0]-u
    else:
        line=a[1]+(u-a[0])*(b[1]-a[1])/(b[0]-a[0])
        distance=line-v if direction=='dorsal' else v-line
    peak=np.unravel_index(np.argmax(np.where(mask,distance,-np.inf)),mask.shape)
    tip=np.array([u[peak],v[peak]])
    cs, _ = cv2.findContours(mask.astype('uint8'), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour = max(cs, key=cv2.contourArea)
    # Do not rasterize the authored base: staircase slivers at the clipping
    # line can touch at one vertex and become four-face edges after solidify.
    epsilon = 1.6
    while True:
        poly = cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2)
        if len(poly) <= 110:
            break
        epsilon += .25
    points=(poly + .5) / [w, h]
    pixel_scale=np.array([w,h]);ia=int(np.argmin(np.linalg.norm((points-a)*pixel_scale,axis=1)))
    ib=int(np.argmin(np.linalg.norm((points-b)*pixel_scale,axis=1)))
    assert ia!=ib
    def path(step):
        ids=[ia]
        while ids[-1]!=ib:ids.append((ids[-1]+step)%len(points))
        return points[ids]
    choices=[path(1),path(-1)]
    selected=min(choices,key=lambda q:float(np.min(np.linalg.norm((q-tip)*pixel_scale,axis=1))))
    # The ROI alpha also contains body-edge runs. Keep only the continuous
    # positive-side free-fin arc containing its actual tip, then connect the
    # whole authored base to that arc with an explicit finite root collar.
    # Encoding several islands as a single clipped polygon creates pinches.
    def signed_distance(q):
        if direction=='posterior':return (a[0]-q[:,0])*w
        aa=a*pixel_scale;bb=b*pixel_scale;qq=q*pixel_scale
        cross=(bb[0]-aa[0])*(qq[:,1]-aa[1])-(bb[1]-aa[1])*(qq[:,0]-aa[0])
        return cross/np.linalg.norm(bb-aa)*(1 if direction=='ventral' else -1)
    ds=signed_distance(selected);peak_id=int(np.argmin(np.linalg.norm((selected-tip)*pixel_scale,axis=1)))
    assert ds[peak_id]>.35
    lo=peak_id;hi=peak_id
    while lo>0 and ds[lo-1]>.35:lo-=1
    while hi+1<len(selected) and ds[hi+1]>.35:hi+=1
    selected=selected[lo:hi+1]
    distances=[float(np.linalg.norm((points[i]-p)*pixel_scale)) for i,p in [(ia,a),(ib,b)]]
    joined=[a.tolist()]+selected.tolist()+[b.tolist()]
    polygon=[]
    for point in joined:
        if not polygon or np.linalg.norm((np.array(point)-polygon[-1])*pixel_scale)>.15:polygon.append(point)
    if np.linalg.norm((np.array(polygon[-1])-polygon[0])*pixel_scale)<.15:polygon.pop()
    return polygon,tip.tolist(), {'join_distance_px':distances,'join_review_required':True,'stitch_segments':[[a.tolist(),selected[0].tolist()],[selected[-1].tolist(),b.tolist()]],'tip':tip.tolist(),'tip_path_distance_px':float(np.min(np.linalg.norm((selected-tip)*pixel_scale,axis=1))),'method':'Source alpha extremum beyond the authored baseline defines the real tip. Keep its continuous positive-side free arc; connect full authored A/B with a finite hidden root collar. Excludes body-edge islands; internal stitches require visual review, alpha distance is not an anatomical measurement.'}


def author(kind):
    great = kind == 'great'
    species = kind + '_hammerhead'
    src = ROOT / f'projects/{kind}-hammerhead-side121/output/char_{species}_side121_nobg.png'
    if not src.exists():src=ROOT/f'projects/fishing-2d/experiments/blender-fish/hammer-pair-121/source-workflows/{kind}-side/output/char_{species}_side121_nobg.png'
    image = np.asarray(Image.open(src).convert('RGBA'))
    h, w = image.shape[:2]
    if great:
        body = [[.235,.48,.585,.007],[.28,.475,.586,.013],[.35,.45,.619,.024],[.42,.422,.689,.035],[.50,.397,.727,.047],[.60,.39,.765,.059],[.68,.393,.762,.063],[.75,.413,.762,.058],[.82,.464,.745,.046],[.88,.522,.719,.031],[.915,.555,.674,.021],[.945,.58,.655,.012]]
        eye = [.977,.623]
        specs = [
            ('FirstDorsal',[.57,0,.75,.43],[[.59,.392],[.738,.404]],[.60,.005],'dorsal'),
            ('SecondDorsal',[.306,.33,.405,.49],[[.317,.463],[.398,.431]],[.333,.35],'dorsal'),
            ('Caudal',[0,0,.245,.80],[[.235,.48],[.235,.585]],[.003,.074],'posterior'),
            ('Pectoral',[.638,.70,.744,1],[[.64,.745],[.737,.707]],[.652,.994],'ventral'),
            ('Pelvic',[.38,.62,.49,.805],[[.387,.649],[.481,.72]],[.388,.795],'ventral'),
            ('Anal',[.295,.56,.353,.666],[[.303,.585],[.350,.615]],[.300,.658],'ventral'),
        ]
    else:
        body = [[.245,.477,.59,.007],[.28,.471,.59,.012],[.35,.457,.628,.021],[.42,.434,.674,.031],[.50,.401,.724,.041],[.60,.374,.763,.051],[.68,.38,.765,.055],[.75,.407,.76,.051],[.82,.449,.74,.042],[.88,.493,.703,.028],[.915,.522,.632,.019],[.945,.544,.635,.011]]
        eye = [.947,.594]
        specs = [
            ('FirstDorsal',[.58,0,.735,.41],[[.584,.379],[.726,.398]],[.60,.005],'dorsal'),
            ('SecondDorsal',[.347,.335,.42,.47],[[.352,.456],[.415,.436]],[.359,.35],'dorsal'),
            ('Caudal',[0,0,.255,.80],[[.245,.477],[.245,.59]],[.003,.05],'posterior'),
            ('Pectoral',[.673,.65,.778,1],[[.679,.72],[.768,.667]],[.69,.993],'ventral'),
            ('Pelvic',[.408,.64,.50,.80],[[.416,.68],[.49,.718]],[.423,.793],'ventral'),
            ('Anal',[.32,.585,.371,.679],[[.323,.596],[.365,.637]],[.325,.668],'ventral'),
        ]
    fins = [];trace_review={}
    for name, box, base, tip, direction in specs:
        paired = name in ('Pectoral', 'Pelvic')
        attachment = dict(mode='body_surface', root_band=.025, blend_end=.32, inset=.000025, surface_clearance=.0015)
        if name=='SecondDorsal':attachment['root_band_depth']=.00002 if great else .00004
        if great and name=='Pectoral':attachment['baseline_spacing']=.0005
        if name == 'Caudal':
            attachment['surface_region'] = 'posterior'
        polygon,tip,evidence=outline(image,box,base,tip,direction);trace_review[name]=evidence
        fins.append(dict(name=name, polygon=polygon, source_baseline=base,
                         anchor=np.mean(base,axis=0).tolist(), tip=tip, paired=paired,
                         root_depth=.04 if paired else 0, tip_depth=(.155 if name=='Pectoral' else .075) if paired else 0,
                         thickness=.00012 if great else .00015, amplitude=.022 if paired else .016,
                         phase=1.0 if paired else 2.0, axis=[1,0,0] if name!='Caudal' else [0,0,1],
                         vertical_scale=.35 if paired else 1, opaque=True, root_attachment=attachment))
    half = .13 if great else .1375
    # Adult Great: straight leading edge with a central indentation. Smooth:
    # broad convex edge without an indentation. Lateral chord/thickness remain
    # explicit reconstruction choices, independently reviewed in clay views.
    if great:
        halfrows = [[0,.881,.982,.014],[.012,.893,.990,.014],[.035,.916,.992,.013],[.075,.927,.992,.012],[.112,.938,.990,.011],[half,.953,.979,.008]]
    else:
        halfrows = [[0,.878,.997,.012],[.025,.895,.995,.012],[.060,.917,.988,.011],[.10,.931,.978,.010],[.127,.94,.966,.009],[half,.946,.956,.007]]
    rows = [[-q,*r] for q,*r in halfrows[:0:-1]] + halfrows
    p = json.loads((ROOT/'resources/volume-fish/scalloped-hammerhead-reviewed-056.profile.json').read_text())
    p.update(species=species, display_name='大双髻鲨' if great else '无沟双髻鲨', source_aspect_ratio=w/h,
             profile_review_status='approved', real_length_cm=400 if great else 300,
             body=dict(sections=body,rings=193,radial=64), fins=fins,
             cephalofoil=dict(center_v=eye[1],sections=rows),
             eyes=dict(center=eye,radius=.008,depth=half,mode='surface_patch',
                       source_rect=[eye[0]-.011,eye[1]-.029,eye[0]+.011,eye[1]+.029],thickness=.001,surface_offset=.0004))
    us=[.968,.88,.78,.66,.53,.41,.31,body[0][0]]
    p['rig']['spine']=[[u,float(np.interp(u,[r[0] for r in body],[(r[1]+r[2])/2 for r in body]))] for u in us]
    p['head_projection'].update(source_rect=[.09,.60 if great else .55,.91,.73 if great else .69],
                                model_depth_range=[-half,half],model_v_range=[eye[1]-.045,eye[1]+.045])
    for key in ['dorsal_projection','ventral_projection']:
        surface=p[key]
        surface.update(start_u=body[0][0],model_depth_range=[-half,half],
                       head_source_rect=[.90 if great else .86,.10,.994,.90],
                       sections=[[u,max(.28,min(u,.85)),.46-width,.54+width,width] for u,top,bottom,width in body])
        if key=='ventral_projection':
            # The generated bottom tail is anatomically invalid. It is NOT
            # a geometry guide or tail donor; use interior ivory body only.
            surface['sections']=[[u,max(.32,min(u,.83)),.46-width,.54+width,width] for u,top,bottom,width in body]
            surface['head_source_rect']=[.88,.16,.985,.84]
    p['notes']=[
        '121: independently authored from accepted species side art; reuse builder/rig methods, not lewini dimensions.',
        'Great head width 26% TL (FAO diagnostic 23–27%); Smooth 27.5% TL is an artistic choice below CITES one-third diagnostic ceiling, not measured from generated art.',
        'Regional top/front/bottom pigment donors only. Great top median notch used; tall dorsal silhouette in top and incorrect bottom caudal are excluded from geometry.',
        'All six fin groups have species-source baselines; eight actual fins after pairing. Whole heterocercal caudal is one closed mesh.',
        'Thickness and unseen transverse body widths are production inferences; real length is display scale, not animal age determination.',
        'Operator landmark approval applies to input geometry only; actual model/style/fin/body gates remain pending.'
    ]
    target=ROOT/f'resources/volume-fish/{kind}-hammerhead-121.profile.json'
    target.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
    out=ROOT/f'projects/hammer-pair-121/review/{species}';out.mkdir(parents=True,exist_ok=True)
    (out/'fin-source-trace.validation.json').write_text(json.dumps({'ok':True,'fins':trace_review},indent=2)+'\n')
    drawing=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w} {h}"><image href="../../../{kind}-hammerhead-side121/output/char_{species}_side121_nobg.png" width="{w}" height="{h}"/>']
    for f in fins:
        poly=' '.join(f'{u*w:.1f},{v*h:.1f}' for u,v in f['polygon'])
        base=' '.join(f'{u*w:.1f},{v*h:.1f}' for u,v in f['source_baseline'])
        drawing += [f'<polygon points="{poly}" fill="none" stroke="#00e5ff" stroke-width="2"/>',f'<polyline points="{base}" fill="none" stroke="#ff4a41" stroke-width="5"/>']
    for u,t,b,z in body:
        drawing.append(f'<path d="M{u*w},{t*h}V{b*h}" stroke="#ffe55b" stroke-width="2"/>')
    drawing.append('</svg>');(out/'landmarks.svg').write_text(''.join(drawing))
    print(species, 'profile', target)


if __name__=='__main__':
    for kind in ['great','smooth']:
        author(kind)
