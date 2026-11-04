"""Finite full-head sections, including the previously omitted medial wings.

The library's default/bind-pose equivalence was checked separately. This is a
game-model shape comparison, not biological data or a mesh transfer.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'cli/gamefactory.py').exists())
sys.path.insert(0, str(ROOT/'resources/scripts/volume-fish/portable'))
from glb_io import read_glb, arrays


def load_reference(path):
    v, f, group = [], [], ''
    for line in path.read_text().splitlines():
        if line.startswith('v '): v.append(list(map(float, line.split()[1:])))
        elif line.startswith('g '): group = line[2:]
        elif line.startswith('f ') and group == 'HammerheadShark_0':
            f.append([int(x.split('/')[0])-1 for x in line.split()[1:]])
    v = np.array(v)[:, [1,2,0]]
    length = float(np.ptp(v[:,0])); v[:,0] -= v[:,0].min(); v /= length
    return v, np.array(f)


def load_candidate(path, length, nose):
    d,b = read_glb(path); v,f,offset = [],[],0
    for node in d['nodes']:
        if node.get('name') != 'Reference_head_body': continue
        assert not any(k in node for k in ['matrix','rotation','scale','translation'])
        for p in d['meshes'][node['mesh']]['primitives']:
            q = arrays(d,b,p['attributes']['POSITION']).astype(float)
            q[:,0] = nose-q[:,0]; q[:,2] *= -1; q /= length
            v.append(q); f.append(arrays(d,b,p['indices']).reshape(-1,3)+offset); offset += len(q)
    return np.concatenate(v),np.concatenate(f)


def plane_intervals(tris,z):
    """Union the projected X intervals of finite transverse-plane cuts."""
    hits=[]
    for t in tris:
        ps=[]
        for i,j in [(0,1),(1,2),(2,0)]:
            a,b=t[i],t[j]
            if (a[2]-z)*(b[2]-z)<0:
                ps.append(a+(z-a[2])/(b[2]-a[2])*(b-a))
        if len(ps)==2: hits.append((min(p[0] for p in ps),max(p[0] for p in ps)))
    merged=[]
    for a,b in sorted(hits):
        if merged and a <= merged[-1][1]+1e-7: merged[-1][1]=max(merged[-1][1],b)
        else: merged.append([a,b])
    return merged


def vertical(tris,x,z):
    a,b,c=tris[:,0],tris[:,1],tris[:,2]
    den=(b[:,2]-c[:,2])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,2]-c[:,2])
    valid=np.abs(den)>1e-14
    aa=np.zeros(len(tris));bb=aa.copy()
    aa[valid]=((b[valid,2]-c[valid,2])*(x-c[valid,0])+(c[valid,0]-b[valid,0])*(z-c[valid,2]))/den[valid]
    bb[valid]=((c[valid,2]-a[valid,2])*(x-c[valid,0])+(a[valid,0]-c[valid,0])*(z-c[valid,2]))/den[valid]
    cc=1-aa-bb; k=valid&(aa>=-1e-8)&(bb>=-1e-8)&(cc>=-1e-8)
    ys=np.unique(np.round((aa*a[:,1]+bb*b[:,1]+cc*c[:,1])[k],10))
    return {'height':float(np.ptp(ys)) if len(ys)>=2 else None,'bottom':float(ys.min()) if len(ys) else None,'top':float(ys.max()) if len(ys) else None,'hits':len(ys)}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--candidate',required=True);ap.add_argument('--output',required=True);args=ap.parse_args()
    out=Path(args.output).resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments') and not out.exists();out.mkdir(parents=True)
    project=ROOT/'projects/fishing-2d/experiments/scalloped-art-rebuild-20261102'
    obj=ROOT/'resources/fish-database/artifacts/fishing-master-cdn-cnformal1-20261102/mesh-exports/f516b1aa036a3161d9504b4b29a8523861e22d658d417078e60c6e95ca44f6a8.obj'
    candidate=Path(args.candidate).resolve(); ref=json.loads((project/'reference-r3.input.json').read_text())
    L=2.4914281368255615;nose=1.032794117647059
    rv,rf=load_reference(obj);cv,cf=load_candidate(candidate,L,nose);rt=rv[rf];ct=cv[cf]
    rspan=float(np.max(np.abs(rv[rv[:,0]<.14,2])));cspan=ref['head_span_m']/2/L
    fractions=[0,.05,.1,.15,.2,.25,.3,.35,.4,.45,.5,.55,.6,.65,.7,.75,.8,.85,.9,.925,.95,.975,.99]
    chord=[.005,.025,.05,.1,.15,.2,.3,.4,.5,.6,.7,.8,.85,.9,.95,.975,.995]
    rows=[]
    for side in [-1,1]:
        for frac in fractions:
            z=side*max(frac,1e-6)*rspan
            intervals=plane_intervals(rt,z);front,rear=intervals[0];rear=min(rear,.108)
            y=side*frac*ref['head_span_m']/2
            fr=float(np.interp(y,[r['y_m'] for r in ref['head_transverse_stations']],[r['front_x_m'] for r in ref['head_transverse_stations']]))
            re=float(np.interp(y,[r['y_m'] for r in ref['head_transverse_stations']],[r['rear_x_m'] for r in ref['head_transverse_stations']]))
            cfront,crear=(nose-fr)/L,(nose-re)/L
            samples=[]
            for t in chord:
                r=vertical(rt,front+(rear-front)*t,z);c=vertical(ct,cfront+(crear-cfront)*t,side*max(frac,1e-6)*cspan)
                samples.append({'chord_fraction':t,'reference':r,'candidate':c})
            rows.append({'side':side,'half_span_fraction':frac,'reference_front':front,'reference_rear':rear,'candidate_front':cfront,'candidate_rear':crear,'samples':samples})
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report={'kind':'finite_full_head_thickness_field','inputs':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in [obj,candidate,project/'reference-r3.input.json']],
        'reference_species':'Unverified game-name HammerheadShark; family shape reference, not biological measurement',
        'normalization':'Full longitudinal whole-fish rest extent = 1, no head rescaling. Span fractions independently refer to each original head silhouette.',
        'reference_posterior_boundary':{'x_from_snout_over_length':.108,'definition':'Engineering head/neck boundary at the minimum transverse width after the wide cephalofoil; central sections truncated here, outside the neck use the frontmost connected cut interval if shorter. Not a biological landmark.'},
        'candidate_boundary':'Unchanged project clean-top front/rear rows; corresponding front-to-rear chord fractions, not equal absolute X.',
        'candidate_length_m':L,'reference_half_span_over_length':rspan,'candidate_half_span_over_length':cspan,'rows':rows,
        'limitations':['Reference jaw open, project near-closed: central ventral mouth envelope is not a direct target.','Fin triangles remain in the library body group, but head interval is before their roots.','Finite triangles only; no tissue thickness, species or user acceptance claim.']}
    (out/'sections.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    image=Image.new('RGB',(1650,950),'white');draw=ImageDraw.Draw(image)
    draw.text((20,12),'Full head sections | normalized whole length | reference / candidate',fill='black')
    for j,key in enumerate(['reference','candidate']):
        ox=25+j*820;draw.text((ox,40),key+' : side + ; front -> rear ; height / length',fill='black')
        for i,row in enumerate([r for r in rows if r['side']==1]):
            yy=75+i*36;draw.text((ox,yy+8),f"{row['half_span_fraction']:4.1%}",fill='black')
            for k,s in enumerate(row['samples']):
                h=s[key]['height'];t=min(1,max(0,(h or 0)/.09));color=(int(245*t+10),int(100+100*(1-t)),int(245*(1-t)))
                xx=ox+70+k*42;draw.rectangle((xx,yy,xx+40,yy+33),fill=color)
                draw.text((xx+2,yy+9),f'{h*100:.1f}' if h is not None else '?',fill='white' if t<.2 else 'black')
        for k,t in enumerate(chord):draw.text((ox+70+k*42,910),str(round(t,2)),fill='black')
    image.save(out/'thickness-field.png')
    print('frac ref_peak% current_peak% (positive side)')
    for row in rows:
        if row['side']==1:
            print(row['half_span_fraction'],round(max(s['reference']['height'] or 0 for s in row['samples'])*100,3),round(max(s['candidate']['height'] or 0 for s in row['samples'])*100,3))


if __name__=='__main__':main()
