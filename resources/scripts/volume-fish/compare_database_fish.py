"""Render finite library body components and installed fish at the same body-axis length.

Diagnostic only: source names are not biological verification and plots do not approve assets.
"""
import argparse, csv, hashlib, json, sys
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(Path(__file__).parent),str(Path(__file__).parent/'portable')]
from glb_io import read_glb, arrays
from audit_transverse_width import section
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
SOURCES={'rainbow_trout':('Rainbowtrout',1),'brown_trout':('BrownTrout',0),'atlantic_salmon':('AtlanticSalmon',0),'sea_bass':('EuropeanSeabass',0),'red_emperor':('ShortTailRedSnapper',0)}

def read_obj(p):
    v=[]; groups={}; group='default'
    for line in p.read_text().splitlines():
        q=line.split()
        if not q:continue
        if q[0]=='v':v.append(list(map(float,q[1:4])))
        if q[0] in ['g','usemtl']:group=' '.join(q[1:]);groups.setdefault(group,[])
        if q[0]=='f':
            ids=[int(x.split('/')[0])-1 for x in q[1:]]
            groups.setdefault(group,[]).extend([[ids[0],ids[i],ids[i+1]] for i in range(1,len(ids)-1)])
    return np.array(v),{k:np.array(x,dtype=int) for k,x in groups.items() if x}

def split_components(v,f):
    # Weld OBJ seams before computing physical components.
    _, inv=np.unique(np.round(v,6),axis=0,return_inverse=True)
    ff=inv[f];edges=np.concatenate([ff[:,[0,1]],ff[:,[1,2]],ff[:,[2,0]]])
    mat=coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(inv.max()+1,)*2)
    _,labels=connected_components(mat,directed=False)
    components=[]
    for label in np.unique(labels[ff[:,0]]):
        fi=f[labels[ff[:,0]]==label];vv=v[np.unique(fi)]
        components.append((fi,{'faces':len(fi),'bounds':[vv.min(0).tolist(),vv.max(0).tolist()]}))
    return sorted(components,key=lambda q:len(q[0]),reverse=True)

def normalized(v,f,axes,nose_positive=True):
    # Axes output: longitudinal toward nose, vertical, transverse.
    w=v[:,axes].copy();w[:,0]*=1 if nose_positive else -1
    body=w[np.unique(f)];lo,hi=body[:,0].min(),body[:,0].max();length=hi-lo
    center=(body.min(0)+body.max(0))/2
    w=(w-center)/length
    return w,{'axes':axes,'nose_positive':nose_positive,'body_axis_length':float(length),'bounds_native':[body.min(0).tolist(),body.max(0).tolist()]}

def widths(v,f):
    lo,hi=v[f,0].min(),v[f,0].max();L=hi-lo;result=[]
    for s in np.linspace(.005,.995,199):
        q=section(v,f.reshape(-1),hi-s*L)
        result.append({'s':float(s),'width_over_body_axis':float(np.ptp(q[:,2])/L),'height_over_body_axis':float(np.ptp(q[:,1])/L)})
    return result

def main(out):
    out=out.resolve();assert out.is_relative_to(ROOT/'output') and not out.exists();out.mkdir(parents=True)
    db=ROOT/'resources/fish-database';catalog=list(csv.DictReader((db/'catalogs/fishing-master-cdn-cnformal1-20261102/collection-status.csv').open(encoding='utf-8-sig')))
    canvas=Image.new('RGB',(1600,1500),'white');draw=ImageDraw.Draw(canvas);records=[]
    for row,(species,(base,groupno)) in enumerate(SOURCES.items()):
        entry=next(x for x in catalog if list(x.values())[1]==base);ref=db/list(entry.values())[7]
        rv,groups=read_obj(ref);group=next(k for k in groups if k.endswith('_'+str(groupno)));components=split_components(rv,groups[group]);rf=components[0][0]
        # Library base fishes here face -Y, Z is vertical, X is bilateral.
        rn,rmeta=normalized(rv,rf,[1,2,0],False)
        game=ROOT/f'projects/fishing-2d/game/assets/models/fish/{species}.glb';d,b=read_glb(game);pr=d['meshes'][0]['primitives'][0];v=arrays(d,b,pr['attributes']['POSITION']);idx=arrays(d,b,pr['indices']).reshape(-1)
        f=np.concatenate([idx[p['index_start']:p['index_start']+p['index_count']] for p in d['extras']['geometry_parts'] if p['role'] in ['body_skin','mouth']]).reshape(-1,3)
        vn,vmeta=normalized(v,f,[0,1,2]);rr=widths(rn,rf);vr=widths(vn,f)
        for col,(a1,a2,title) in enumerate([(0,2,'Top: body thickness'),(0,1,'Side: project drawing retained')]):
            left=col*800; top=row*300
            draw.text((left+20,top+12),f'{species} / {base} - {title}',fill='black')
            draw.text((left+20,top+30),'ORANGE: library body   BLUE: installed body; equal body-axis length',fill='black')
            for vv,ff,c,label in [(rn,rf,'#e49b38','Library body'),(vn,f,'#2878bd','Installed body')]:
                layer=Image.new('RGBA',canvas.size,(0,0,0,0));ld=ImageDraw.Draw(layer)
                for triangle in vv[ff][:,:,[a1,a2]]:
                    pts=[(left+400+float(q[0])*660,top+175-float(q[1])*660) for q in triangle]
                    ld.polygon(pts,fill=c+'70')
                canvas=Image.alpha_composite(canvas.convert('RGBA'),layer).convert('RGB');draw=ImageDraw.Draw(canvas)
        record={'species':species,'installed':{'path':str(game.relative_to(ROOT)),'sha256':SHA(game)},'reference':{'path':str(ref.relative_to(ROOT)),'sha256':SHA(ref),'base_name':base,'group':group,'components':[x[1] for x in components],'normalization':rmeta},'game_normalization':vmeta,'sections':{'reference':rr,'installed':vr},'reference_kind':'third-party game art, not biological measurement','species_match':'named same-kind candidate, unverified identity' if species!='red_emperor' else 'proposed related snapper reference; not same species; pending visual review','formal_acceptance':False}
        records.append(record);(out/f'{species}.validation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    canvas.save(out/'body-comparison.png')
    (out/'manifest.json').write_text(json.dumps({'kind':'five_fish_database_preflight','status':'pending','next_action':'visual_review_and_reference_correspondence','records':records,'assets_modified':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'ok':True,'output':str(out),'species':list(SOURCES),'assets_modified':False}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);main(p.parse_args().output)
