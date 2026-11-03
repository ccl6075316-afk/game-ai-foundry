"""Summarize actual old/current arrays and collect candidate review images.

No acceptance is inferred from these numerical comparisons or image sheets.
"""
import argparse,hashlib,json,sys
from io import BytesIO
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path[:0]=[str(HERE),str(HERE/'portable')]
from glb_io import read_glb,arrays
from audit_transverse_width import section
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
    d,b=read_glb(p);pr=d['meshes'][0]['primitives'][0];a={k:arrays(d,b,x) for k,x in pr['attributes'].items()};idx=arrays(d,b,pr['indices']).reshape(-1);view=d['bufferViews'][d['images'][0]['bufferView']];im=np.array(Image.open(BytesIO(b[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']])).convert('RGBA'));return d,b,a,idx,im
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sheet(root,paths,name,columns=2):
    cellw,cellh=600,440;out=Image.new('RGB',(cellw*columns,cellh*((len(paths)+columns-1)//columns)),(37,52,60));draw=ImageDraw.Draw(out)
    for i,p in enumerate(paths):
        im=Image.open(p).convert('RGB');im.thumbnail((600,410),Image.Resampling.NEAREST);x=(i%columns)*cellw;y=(i//columns)*cellh;out.paste(im,(x+(600-im.width)//2,y+26));draw.text((x+8,y+8),p.stem,fill='white')
    path=root/name;out.save(path,quality=94);return path
def main(a):
    root=a.directory.resolve();species=a.species;before=ROOT/f'projects/fishing-2d/game/assets/models/fish/{species}.glb';after=a.model.resolve() if a.model else root/'width-r2/fish.glb';delivery=a.delivery.resolve() if a.delivery else root/'delivery-r2';d,b,v,idx,img=load(after);od,ob,ov,oi,oimg=load(before)
    assert set(v)==set(ov) and np.array_equal(idx,oi) and d['nodes']==od['nodes']
    xyfile=after.parent/'xy-authoring.validation.json'
    if not xyfile.exists():xyfile=after.parent/'xy-preservation.validation.json'
    xy=json.loads(xyfile.read_text()) if xyfile.exists() else None;xyids=set()
    if xy:
        assert xy['ok'] and xy['model_sha256']==sha(after)
        for row in xy['vertices']:
            i=row['vertex'];xyids.add(i);assert np.max(abs(v['POSITION'][i,:2]-row['new_XY']))<1e-7 and np.max(abs(ov['POSITION'][i,:2]-row['old_XY']))<1e-7
    unchanged=[i for i in range(len(v['POSITION']))if i not in xyids];assert np.array_equal(v['POSITION'][unchanged,:2],ov['POSITION'][unchanged,:2])
    skinfile=after.parent/'skin-authoring.validation.json'
    if not skinfile.exists():skinfile=after.parent/'skin-preservation.validation.json'
    skin=json.loads(skinfile.read_text()) if skinfile.exists() else None
    permitted=set()
    if skin:
        assert skin['ok'] and skin['model_sha256']==sha(after)
        names=[d['nodes'][j]['name']for j in d['skins'][0]['joints']]
        for row in skin['changed_root_vertices']:
            i=row['vertex'];permitted.add(i)
            for stream,wanted in [(v,row['new_named_weights']),(ov,row['old_named_weights'])]:
                actual={names[int(j)]:float(w)for j,w in zip(stream['JOINTS_0'][i],stream['WEIGHTS_0'][i])if w>1e-8}
                assert actual.keys()==wanted.keys() and max(abs(actual[k]-wanted[k])for k in actual)<1e-6
    for k in v:
        if k not in ['POSITION','NORMAL']:
            ids=[i for i in range(len(v[k]))if i not in permitted] if k in ['JOINTS_0','WEIGHTS_0'] else slice(None)
            assert np.array_equal(v[k][ids],ov[k][ids]),k
    assert d['skins']==od['skins'] or np.array_equal(arrays(d,b,d['skins'][0]['inverseBindMatrices']),arrays(od,ob,od['skins'][0]['inverseBindMatrices']))
    animation_error=0.
    for x,y in zip(d['animations'],od['animations']):
        assert x['channels']==y['channels']
        for xx,yy in zip(x['samplers'],y['samplers']):
            for k in ['input','output']:animation_error=max(animation_error,float(np.max(np.abs(arrays(d,b,xx[k])-arrays(od,ob,yy[k])))))
    assert animation_error<1e-7
    mask=np.array(Image.open(a.mask if a.mask else root/'ventral-bake-r1/patch-mask.png'));assert np.array_equal(img[:,:,3],oimg[:,:,3]) and np.array_equal(img[mask==0],oimg[mask==0]);assert sha(after)==sha(after.parent/'cold-fish.glb')
    motion_table=json.loads((ROOT/'projects/fishing-2d/game/assets/models/fish/motion/width20261101/manifest.json').read_text())['profiles'];scale=motion_table[species]['model_scale'];body=np.concatenate([idx[p['index_start']:p['index_start']+p['index_count']] for p in d['extras']['geometry_parts'] if p['role']in ['body_skin','mouth']]);hi=float(v['POSITION'][body,0].max());length=float(np.ptp(v['POSITION'][body,0]));rows=[]
    for s in np.linspace(.005,.995,199):
        rows.append({'s_body':float(s),'before_width_cm':float(np.ptp(section(ov['POSITION'],body,hi-s*length)[:,2])*scale*100),'after_width_cm':float(np.ptp(section(v['POSITION'],body,hi-s*length)[:,2])*scale*100)})
    reference=json.loads((ROOT/f'output/five-fish-database-20261103/body-preflight/{species}.validation.json').read_text());rt=reference['sections']['reference'];maximum=max(rows,key=lambda x:x['after_width_cm']);oldmaximum=max(rows,key=lambda x:x['before_width_cm']);rm=max(rt,key=lambda x:x['width_over_body_axis'])
    proof={'ok':True,'kind':'whole_current_database_revision_invariants','species':species,'model_sha256':sha(after),'baseline_sha256':sha(before),'triangles':len(idx)//3,'bones':len(d['skins'][0]['joints']),'all_XY_UV_indices_skin_rig_actions_preserved':True,'animation_max_error':animation_error,'alpha_exact':True,'outside_ventral_mask_RGBA_exact':True,'source_cold_export_bytes_equal':True,'changed_atlas_pixels':int(np.any(img!=oimg,axis=2).sum()),'sections':rows,'body_axis_cm':length*scale*100,'before_maximum':oldmaximum,'after_maximum':maximum,'reference_maximum_width_cm':rm['width_over_body_axis']*length*scale*100,'reference_peak_s':rm['s'],'reference_kind':'third-party game-art bind geometry, not biological measurement','formal_acceptance':False}
    if skin:
        proof['all_XY_UV_indices_skin_rig_actions_preserved']=False
        proof['all_XY_UV_indices_rig_actions_and_unlisted_skin_preserved']=True
        proof['explicit_root_skin_exception']={'path':str(skinfile),'sha256':sha(skinfile),'vertices':sorted(permitted),'scope':'Only enumerated full-bank root weights changed, actual old/new named weights verified. All unlisted skin rows exact.'}
    if xy:
        proof['all_XY_UV_indices_skin_rig_actions_preserved']=False
        proof['all_XY_UV_indices_rig_actions_and_unlisted_skin_preserved']=False
        proof['all_UV_indices_rig_actions_and_unlisted_XY_and_skin_preserved']=True
        proof['explicit_fin_XY_exception']={'path':str(xyfile),'sha256':sha(xyfile),'vertices':sorted(xyids),'scope':'Only enumerated fin XY rows changed, actual old/new verified; all other XY exact.'}
    write(root/'revision-invariants.validation.json',proof)
    review=delivery/'review';names=['whole-left-texture','whole-right-texture','whole-top-texture','whole-bottom-texture','body-without-fins-top-texture','body-without-fins-bottom-texture','mouth-front-texture','mouth-oblique-clay','head-left-texture','head-bottom-texture','water-natural-freshwater-left','water-natural-freshwater-oblique']
    paths=[review/(n+'.png') for n in names];assert all(p.exists() for p in paths);sheet(root,paths,'current-visual-review.jpg')
    paths=[review/f'frames/frame-{i:04d}.jpg' for i in [0,24,48,96,144,192,240,252,264,276]];sheet(root,paths,'motion-review.jpg')
    original=json.loads((ROOT/f'output/five-fish-database-20261103/restored/{species}/frozen/spec-sop-review.json').read_text(encoding='utf8'));source=Path(original['candidate_files']['source_image']['path']);im=Image.open(source).convert('RGBA');W,H=im.size;capture=json.loads((review/'review-capture.validation.json').read_text());camera_width=next(x['camera_size'] for x in capture['captures'] if x['label']=='whole-left-texture');factor=scale*900/camera_width/W;im=im.resize((round(W*factor),round(H*factor)),Image.Resampling.NEAREST);aligned=Image.new('RGBA',(900,620),(37,52,60,255));aligned.alpha_composite(im,(round(450-W*factor/2),round(310-H*factor/2)));aligned.convert('RGB').save(root/'source-aligned.png');sheet(root,[root/'source-aligned.png',review/'whole-left-texture.png'],'source-final-side-comparison.jpg')
    print(json.dumps({'ok':True,'triangles':proof['triangles'],'before_max_width_cm':oldmaximum['before_width_cm'],'after_max_width_cm':maximum['after_width_cm'],'reference_max_width_cm':proof['reference_maximum_width_cm']}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--species',required=True);p.add_argument('--directory',required=True,type=Path)
    for k in ['model','delivery','mask']:p.add_argument('--'+k,type=Path)
    main(p.parse_args())
