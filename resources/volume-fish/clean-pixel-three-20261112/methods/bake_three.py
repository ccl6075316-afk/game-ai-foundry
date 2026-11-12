"""Bake approved color onto the frozen native charts, body before fins."""
import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
SCRIPTS = ROOT / 'resources/scripts/volume-fish'
sys.path[:0] = [str(SCRIPTS), str(SCRIPTS/'portable'),
                str(ROOT/'resources/volume-fish/clean-pixel-yellow-croaker-20261111/method')]
from bake_material import (Donor, biggest_component, columns, digest,
                           export_image_candidate, load_image_chart, raster,
                           read_glb, read_image, read_parts, sha, smooth)

HEAD_TRANSITION = {
    'zander': (.69, .84),
    'mahi_mahi': (.74, .88),
    'african_catfish': (.72, .88),
}

# Interior color areas on each accepted 1536x1024 concept. Existing fin
# texture supplies the authored ray placement, thickness edges and coverage.
FIN_DONORS = {
    'zander': {
        'Anal': [(486,557),(541,553),(650,569),(605,618),(564,650),(530,631)],
        'Caudal': [(168,349),(268,397),(310,442),(309,507),(255,559),(169,617),(217,481)],
        'Dorsal_soft': [(476,409),(538,345),(629,286),(668,293),(718,355),(739,378),(625,388)],
        'Dorsal_spiny': [(811,362),(882,302),(923,252),(950,260),(983,281),(1015,289),(1040,370)],
        'Pectoral': [(944,495),(980,487),(1055,495),(1080,508),(1065,529),(1005,545),(971,529)],
        'Pelvic': [(950,677),(957,628),(980,598),(1043,583),(1022,623),(995,655)],
    },
    'mahi_mahi': {
        'Anal': [(425,521),(516,539),(677,565),(798,578),(777,603),(735,601),(620,571)],
        'Caudal': [(198,366),(292,413),(358,468),(357,496),(297,548),(200,590),(289,478)],
        'Dorsal': [(434,428),(594,390),(780,354),(970,315),(1113,271),(1161,295),(1230,345),(1000,353),(776,381),(594,406)],
        'Pectoral': [(1031,513),(1080,505),(1149,505),(1169,516),(1120,542),(1078,528)],
        'Pelvic': [(1045,642),(1074,618),(1083,599),(1124,592),(1105,632),(1082,647)],
    },
    'african_catfish': {
        'Anal': [(354,520),(468,533),(601,544),(738,550),(710,569),(632,573),(505,557)],
        'Caudal': [(164,412),(207,392),(249,402),(267,421),(253,460),(266,508),(229,533),(175,521),(152,472)],
        'Dorsal': [(355,398),(468,371),(654,342),(839,327),(966,331),(1017,368),(858,372),(687,374),(510,391)],
        'Pectoral': [(984,520),(1005,505),(1040,507),(1083,523),(1067,542),(1028,553),(1002,545)],
        'Pelvic': [(778,591),(796,563),(816,550),(839,549),(825,575),(795,596)],
    },
}


def body_mask(image):
    background = np.median(image[:15,:,:3].reshape(-1,3), axis=0)
    distance = np.linalg.norm(image[:,:,:3].astype(np.float32)-background, axis=2)
    mask = biggest_component(distance > 27)
    return cv2.erode(mask.astype('uint8'), np.ones((5,5),'uint8')).astype(bool)


class BodyProjection:
    def __init__(self, body, axis, donor, fraction=(.055,.945)):
        self.axis = axis
        self.donor = donor
        self.fraction = fraction
        vertices = np.concatenate([part['pos'] for part in body])
        planar = self.project(vertices)
        self.low = planar.min(0)
        self.span = planar.max(0) - self.low
        target = np.zeros((516,1540),'uint8')
        for part in body:
            points = np.rint(self.pixel(part['pos'])).astype('int32')
            for face in part['faces']:
                cv2.fillConvexPoly(target, points[face], 1)
        self.bounds = columns(target)

    def project(self, positions):
        return np.c_[positions[:,0], -positions[:,1] if self.axis == 'side' else positions[:,2]]

    def pixel(self, positions):
        return (self.project(positions)-self.low)/self.span * [1535,511]+2

    def sample(self, positions):
        points = self.pixel(positions)
        start, end, top, bottom = self.bounds
        col = np.clip(np.rint(points[:,0]).astype(int), 0, len(top)-1)
        along = np.clip((points[:,0]-start)/(end-start),0,1)
        cross = np.clip((points[:,1]-top[col])/np.maximum(1,bottom[col]-top[col]),0,1)
        if self.axis != 'side':
            # Identical physical positions on mirrored UV charts share one sample.
            cross = np.abs(2*cross-1)
        low, high = self.fraction
        cross = low + (high-low)*cross
        left, right, upper, lower = self.donor.bounds
        x = left + along*(right-left)
        x_index = np.rint(x).astype(int)
        y = upper[x_index] + cross*(lower[x_index]-upper[x_index])
        return self.donor.sample(x,y)


def bake_body(species, directory, parts, original):
    body = [p for p in parts if p['node']=='Closed_body']
    skin = [p for p in body if p['material']!='Front mouth oral chart']
    side = read_image(directory/'body-side-v1.png')
    sheet = read_image(directory/'body-top-bottom-v1.png')
    top, bottom = np.split(sheet, [len(sheet)//2])
    donors = {name:Donor(im,body_mask(im),grid=1)
              for name,im in [('side',side),('top',top),('bottom',bottom)]}
    projections = {
        'side':BodyProjection(skin,'side',donors['side']),
        # Limit the asymmetric generated mahi color band to actual blue dorsal skin.
        'top':BodyProjection(skin,'top',donors['top'],(.075,.51) if species=='mahi_mahi' else (.31,.59)),
        'bottom':BodyProjection(skin,'bottom',donors['bottom'],(.50,.86)),
    }
    results = {i:original[i].copy() for i in {p['image'] for p in skin}}
    rank = {i:np.zeros(result.shape[:2],'float32') for i,result in results.items()}
    protected = {i:np.zeros(result.shape[:2],bool) for i,result in results.items()}
    for part in parts:
        i = part['image']
        if i not in protected or part in skin:
            continue
        h,w = protected[i].shape
        for face in part['faces']:
            pixels,_,_ = raster(part['uv'][face],w,h,2.0)
            protected[i][pixels[:,1],pixels[:,0]] = True
    start,end = HEAD_TRANSITION[species]
    counts = []
    for part in skin:
        i = part['image']
        h,w = rank[i].shape
        samples = 0
        for face in part['faces']:
            pixels,bary,priority = raster(part['uv'][face],w,h,1.4)
            x,y = pixels.T
            keep = (priority>rank[i][y,x]) & ~protected[i][y,x]
            x,y,bary,priority = x[keep],y[keep],bary[keep],priority[keep]
            if not len(x):
                continue
            pos = bary @ part['pos'][face]
            normal = bary @ part['norm'][face]
            normal /= np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-7)
            ref = projections['side']
            along = np.clip((pos[:,0]-ref.low[0])/ref.span[0],0,1)
            side_rgb = ref.sample(pos)
            top_rgb = projections['top'].sample(pos)
            bottom_rgb = projections['bottom'].sample(pos)
            if species=='mahi_mahi':
                # Compensate the native emissive material in the exposed back.
                # Keep the narrow tail stalk free of stretched dark specks.
                top_rgb *= [.88,.77,.83]
                tail_detail = smooth((along-.09)/.20)
                top_rgb = top_rgb*tail_detail[:,None] + np.array([21,105,139])*(1-tail_detail)[:,None]
            top_mix = smooth((normal[:,1]-.39)/.46)
            bottom_mix = smooth((-normal[:,1]-.40)/.45)
            axial_mix = top_mix+bottom_mix
            axial = top_rgb*top_mix[:,None]+bottom_rgb*bottom_mix[:,None]
            original_rgb = original[i][y,x,:3].astype(float)
            head = smooth((along-start)/(end-start))
            tail = smooth((along-.013)/.051)
            side_weight = .96*(1-head)*tail*(1-axial_mix)
            axial_tail = smooth((along-.007)/.025) if species=='mahi_mahi' else tail
            axial_weight = (.94 if species=='mahi_mahi' else .90)*axial_tail*(1-smooth((along-.865)/.092))
            color = original_rgb*(1-side_weight-axial_weight*axial_mix)[:,None]
            color += side_rgb*side_weight[:,None]+axial*axial_weight[:,None]
            results[i][y,x,:3] = np.rint(np.clip(color,0,255)).astype('uint8')
            rank[i][y,x] = priority
            samples += len(x)
        counts.append({'part':part['node'],'material':part['material'],'image':i,'samples':samples})
    for i,p in protected.items():
        assert np.array_equal(results[i][p],original[i][p])
    return results, {'parts':counts,'head_transition_normalized':list(HEAD_TRANSITION[species]),
                     'protected_texels':{str(i):int(p.sum()) for i,p in protected.items()},
                     'donor_samples':{k:[v.count,v.fallback] for k,v in donors.items()}}


def bake_fins(species, directory, parts, original):
    concept = read_image(directory/'style-concept-v1.png')
    assert concept.shape[:2]==(1024,1536)
    results = {}
    records = []
    for part in parts:
        name,i = part['node'],part['image']
        category = name.split('_')[0] if name.startswith(('Pectoral','Pelvic')) else name
        if category not in FIN_DONORS[species]:
            continue
        if i not in results:
            mask = np.zeros(concept.shape[:2],'uint8')
            cv2.fillPoly(mask,[np.array(FIN_DONORS[species][category],dtype='int32')],1)
            values = concept[mask.astype(bool),:3]
            base = original[i]
            covered = base[:,:,3]>8
            if covered.all():
                covered = np.zeros(base.shape[:2],bool)
                h,w = covered.shape
                for fin in (p for p in parts if p['image']==i):
                    for face in fin['faces']:
                        pixels,_,_ = raster(fin['uv'][face],w,h,2.0)
                        covered[pixels[:,1],pixels[:,0]]=True
            valid = base[:,:,3]>127
            assert np.count_nonzero(covered & valid)>32 and len(values)>32
            rgb = base[covered,:3].astype(float)
            baseline = base[covered & valid,:3]
            prior = np.percentile(baseline,[15,50,85],axis=0)
            target = np.percentile(values,[15,50,85],axis=0)
            offset = np.clip(target[1]-prior[1],-37,37)
            scale = np.clip((target[2]-target[0])/np.maximum(prior[2]-prior[0],12),.70,1.24)
            remapped = prior[1]+offset+(rgb-prior[1])*scale
            strength = .68 if species!='mahi_mahi' else .60
            result = base.copy()
            result[covered,:3] = np.rint(np.clip(rgb+strength*(remapped-rgb),0,255)).astype('uint8')
            results[i] = result
            records.append({'image':i,'category':category,'fin_texels':int(covered.sum()),'donor_texels':len(values),
                            'donor_polygon':FIN_DONORS[species][category],'channel_offset':offset.tolist(),
                            'channel_contrast':scale.tolist(),'strength':strength})
    return results, {'fin_inventory':[p['node'] for p in parts if p['image'] in results],
                     'fin_chart_recipes':records}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('species',choices=tuple(HEAD_TRANSITION))
    parser.add_argument('stage',choices=['body','fins'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--checkpoint',type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    assert out.is_relative_to(WORK) and not out.exists()
    manifest = json.loads((WORK/'manifest.json').read_bytes())
    item = next(i for i in manifest['items'] if i['species']==args.species)
    assert item['source_generation']['user_acceptance']=='accepted'
    baseline = Path(item['model']['path'])
    assert sha(baseline)==item['model']['sha256']
    if args.stage=='fins':
        checkpoint = args.checkpoint.resolve()
        source = checkpoint/'fish.glb'
        proof = json.loads((checkpoint/'body-review.validation.json').read_bytes())
        assert proof['ok'] and proof['model_sha256']==sha(source)
        body = json.loads((checkpoint/'bake.validation.json').read_bytes())
    else:
        source = baseline
    doc,blob = read_glb(source)
    parts = read_parts(doc,blob)
    original = {i:load_image_chart(doc,blob,i) for i in range(len(doc['images']))}
    directory = WORK/args.species
    func = bake_body if args.stage=='body' else bake_fins
    result,records = func(args.species,directory,parts,original)
    body_ids = {p['image'] for p in parts if p['node']=='Closed_body' or 'eye' in p['node'].lower()}
    assert set(result)<=body_ids if args.stage=='body' else not(set(result)&body_ids)
    body_hashes = {str(i):digest(result.get(i,original[i])) for i in sorted(body_ids)}
    if args.stage=='fins':
        assert body_hashes==body['body_rgba']
    out.mkdir(parents=True)
    images,patches = {},{}
    for i,rgba in result.items():
        assert np.array_equal(rgba[:,:,3],original[i][:,:,3])
        changed = np.count_nonzero(np.any(rgba[:,:,:3]!=original[i][:,:,:3],axis=2))
        if not changed:
            continue
        path = out/f'image-{i}.png'
        Image.fromarray(rgba).save(path)
        images[i] = path
        patches[str(i)] = {'path':str(path),'sha256':sha(path),'changed_rgb_texels':int(changed)}
    candidate = out/'fish.glb'
    assert images
    export_image_candidate(doc,blob,candidate,images)
    after,after_blob = read_glb(candidate)
    for k in ['meshes','nodes','skins','animations','materials','textures','samplers','accessors']:
        assert after[k]==doc[k]
    assert after_blob[:len(blob)]==blob
    receipt = {'ok':True,'species':args.species,'stage':args.stage,'model_sha256':sha(candidate),
               'input_model_sha256':sha(source),'body_rgba':body_hashes,'body_frozen':args.stage=='fins',
               'changed_images':patches,'active_and_inactive_accessor_bytes_exact':len(doc['accessors']),
               'alpha_exact':True,**records}
    (out/'bake.validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ['species','stage','model_sha256','changed_images']}))


if __name__=='__main__':
    main()
