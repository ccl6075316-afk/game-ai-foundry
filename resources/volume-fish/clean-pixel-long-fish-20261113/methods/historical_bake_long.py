"""Bake concept-derived color into native body and fin chart domains."""
import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
sys.path[:0] = [str(ROOT/'resources/scripts/volume-fish/portable'),
                str(ROOT/'resources/scripts/volume-fish'),
                str(ROOT/'resources/volume-fish/clean-pixel-yellow-croaker-20261111/method'),
                str(ROOT/'resources/volume-fish/clean-pixel-three-20261112/methods')]
from bake_material import (digest, export_image_candidate, load_image_chart, raster,
                           read_glb, read_image, sha, smooth, arrays)
from repair_upper import Surface

HAIRTAIL = 'hairtail'
AROWANA = 'silver_arowana'
FIN_POLYGONS = {
    HAIRTAIL: {
        'Hairtail_Continuous_Dorsal': [(809,452),(1024,444),(1190,441),(1241,454),(1238,462),(1010,467),(815,468)],
        'Hairtail_Pectoral': [(1263,505),(1282,510),(1292,518),(1285,529),(1274,522)],
    },
    AROWANA: {
        'Anal': [(356,558),(425,582),(515,606),(623,619),(664,625),(618,650),(553,665),(453,646),(374,605)],
        'Caudal': [(149,421),(196,402),(252,424),(280,454),(271,515),(233,579),(186,584),(150,533)],
        'Dorsal': [(337,352),(374,328),(431,327),(492,344),(515,365),(442,380),(379,418),(347,410)],
        'Pectoral': [(1000,642),(1046,608),(1112,588),(1118,591),(1087,618),(1041,646),(1000,662)],
        'Pelvic': [(757,646),(779,623),(824,617),(815,632),(785,653),(754,665)],
    },
}
# Complete clean torso transects, entirely between the inspected body edges.
# Fin roots, eyes, branchial markings and lip edges are excluded from color fitting.
TORSO_BOUNDS = {
    HAIRTAIL: [(565,493,534),(710,487,541),(855,482,545),(1000,477,550),(1130,476,551)],
    AROWANA: [(544,374,589),(660,373,602),(815,374,610),(950,379,610),(1020,389,590)],
}


def texture_roles(doc, material):
    roles = {}
    for role, texture in [('base', material.get('pbrMetallicRoughness', {}).get('baseColorTexture')),
                          ('emission', material.get('emissiveTexture'))]:
        if texture is not None:
            roles[role] = doc['textures'][texture['index']]['source']
    return roles


def parts(doc, blob):
    result = []
    for node in doc['nodes']:
        if 'mesh' not in node:
            continue
        for primitive in doc['meshes'][node['mesh']]['primitives']:
            attr = primitive['attributes']
            material = doc['materials'][primitive['material']]
            roles = texture_roles(doc, material)
            result.append(dict(node=node['name'], material=material['name'], roles=roles,
                               image=roles.get('emission', roles.get('base')),
                               pos=arrays(doc, blob, attr['POSITION']),
                               uv=arrays(doc, blob, attr['TEXCOORD_0']),
                               faces=arrays(doc, blob, primitive['indices']).reshape(-1,3)))
    return result


def mask_for(items, shape):
    mask = np.zeros(shape[:2], dtype=bool)
    for part in items:
        for face in part['faces']:
            points, _, _ = raster(part['uv'][face], shape[1], shape[0], 1.8)
            x, y = points.T
            mask[y, x] = True
    return mask


def fin_name(species, node):
    if species == HAIRTAIL and node.startswith('Hairtail_Pectoral_'):
        return 'Hairtail_Pectoral'
    if species == AROWANA and node.startswith(('Pectoral_', 'Pelvic_')):
        return node.rsplit('_',1)[0]
    return node if node in FIN_POLYGONS[species] else None


def body_name(species):
    return 'Hairtail_Ribbon_Body' if species == HAIRTAIL else 'Closed_body'


def band_quantiles(rgb, fraction, stations):
    return np.array([np.percentile(rgb[np.abs(fraction-station)<.078], [15,50,88], axis=0)
                     for station in stations])


def concept_palette(species, concept, stations):
    knots, top, bottom = np.array(TORSO_BOUNDS[species]).T
    x = np.arange(knots[0], knots[-1]+1, 2)
    fractions = np.linspace(.015,.985,65)
    lower = np.interp(x,knots,top)
    height = np.interp(x,knots,bottom)-lower
    y = np.rint(lower[None,:]+fractions[:,None]*height[None,:]).astype(int)
    colors = concept[y,x,:3].reshape(-1,3)
    return band_quantiles(colors,np.repeat(fractions,len(x)),stations)


def skin_coordinates(surface, points):
    along = (points[:,0]-surface.lo)/(surface.hi-surface.lo)
    low = np.interp(points[:,0],surface.x,surface.bounds[:,0])
    high = np.interp(points[:,0],surface.x,surface.bounds[:,1])
    cross = np.clip((high-points[:,1])/np.maximum(high-low,1e-7),0,1)
    return along, cross


def raster_body(species, inventory, images, concept):
    body = [p for p in inventory if p['node']==body_name(species)]
    # Silver arowana's real oral and cap charts have different ownership.
    skin = [p for p in body if species==HAIRTAIL or p['material']=='Front skin source chart']
    assert len(skin)==1
    part = skin[0]
    image_id = part['image']
    image = images[image_id]
    guards = [p for p in inventory if p is not part and image_id in p['roles'].values()]
    protected = mask_for(guards,image.shape)
    section = Surface(body)
    rank = np.zeros(image.shape[:2],np.float32)
    along = np.zeros_like(rank)
    cross = np.zeros_like(rank)
    for face in part['faces']:
        pixels, beta, priority = raster(part['uv'][face],image.shape[1],image.shape[0],1.8)
        x,y = pixels.T
        keep = (priority>rank[y,x]) & ~protected[y,x]
        x,y = x[keep],y[keep]
        along[y,x],cross[y,x] = skin_coordinates(section,beta[keep] @ part['pos'][face])
        rank[y,x] = priority[keep]
    domain = rank>0
    central = (rank==2) & (along>.33) & (along<.70)
    stations = np.linspace(0,1,13)
    prior = band_quantiles(image[central,:3],cross[central],stations)
    target = concept_palette(species,concept,stations)
    # Arowana uses both base and emission. Compensate for the brighter lit
    # response while retaining its native scale positions and pixel edges.
    if species==AROWANA:
        target *= np.interp(stations,[0,.55,1],[.86,.92,.94])[:,None,None]
    rgb = image[domain,:3].astype(float)
    fractions = cross[domain]
    sampled_prior = np.stack([np.interp(fractions,stations,prior[:,1,c]) for c in range(3)],1)
    sampled_target = np.stack([np.interp(fractions,stations,target[:,1,c]) for c in range(3)],1)
    contrast = np.clip((target[:,2]-target[:,0])/np.maximum(prior[:,2]-prior[:,0],14),.65,1.12)
    scale = np.stack([np.interp(fractions,stations,contrast[:,c]) for c in range(3)],1)
    candidate = sampled_target + (rgb-sampled_prior)*scale
    u = along[domain]
    if species==HAIRTAIL:
        weight = .83*smooth((u-.015)/.10)*(1-smooth((u-.805)/.115))
    else:
        weight = .94*smooth((u-.025)/.09)*(1-smooth((u-.76)/.13))
        # Carry the same cool-neutral treatment across the gill/cheek, and
        # ease to the unchanged mouth and eye domain before their landmarks.
        cheek = .58*smooth((u-.72)/.13)*(1-smooth((u-.84)/.085))
        candidate = candidate*weight[:,None] + (rgb*np.array([.88,.90,.94]))*cheek[:,None]
        mixed = rgb*(1-weight-cheek)[:,None]+candidate
    if species==HAIRTAIL:
        mixed = rgb+(candidate-rgb)*weight[:,None]
    result = image.copy()
    result[domain,:3] = np.rint(mixed).clip(0,255).astype(np.uint8)
    assert np.array_equal(result[protected],image[protected])
    assert np.array_equal(result[:,:,3],image[:,:,3])
    return {image_id:result}, {'body_texels':int(domain.sum()),'protected_texels':int(protected.sum()),
                               'source_quantiles':prior.tolist(),'concept_quantiles_used':target.tolist(),
                               'concept_torso_transects':TORSO_BOUNDS[species]}


def raster_fins(species, inventory, images, concept):
    result = {}
    records = []
    categories = FIN_POLYGONS[species]
    for category, polygon in categories.items():
        matching = [p for p in inventory if fin_name(species,p['node'])==category]
        assert matching
        ids = {p['image'] for p in matching}
        assert len(ids)==1
        image_id = ids.pop()
        image = images[image_id]
        all_fins = [p for p in inventory if fin_name(species,p['node']) and p['image']==image_id]
        guards = [p for p in inventory if not fin_name(species,p['node']) and image_id in p['roles'].values()]
        protected = mask_for(guards,image.shape)
        domain = mask_for(matching,image.shape) & ~protected
        other = mask_for([p for p in all_fins if fin_name(species,p['node'])!=category],image.shape)
        domain &= ~other
        mask = np.zeros(concept.shape[:2],np.uint8)
        cv2.fillPoly(mask,[np.array(polygon,np.int32)],1)
        valid = domain & (image[:,:,3]>127)
        assert valid.sum()>32
        original = np.percentile(image[valid,:3],[15,50,88],axis=0)
        target = np.percentile(concept[mask>0,:3],[15,50,88],axis=0)
        if species==AROWANA:
            target *= .92
        scale = np.clip((target[2]-target[0])/np.maximum(original[2]-original[0],12),.66,1.20)
        delta = np.clip(target[1]-original[1],-38,38)
        rgb = image[domain,:3].astype(float)
        remap = original[1]+delta+(rgb-original[1])*scale
        output = result.setdefault(image_id,image.copy())
        output[domain,:3] = np.rint(rgb+.80*(remap-rgb)).clip(0,255).astype(np.uint8)
        assert np.array_equal(output[protected],image[protected])
        assert np.array_equal(output[:,:,3],image[:,:,3])
        records.append({'category':category,'nodes':[p['node'] for p in matching], 'image':image_id,
                        'changed_domain':int(domain.sum()), 'protected_texels':int(protected.sum()),
                        'concept_polygon':polygon,'concept_median_used':target[1].tolist()})
    assert sum(len(row['nodes']) for row in records)==sum(bool(fin_name(species,p['node'])) for p in inventory)
    return result, {'fins':records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('species',choices=[HAIRTAIL,AROWANA])
    parser.add_argument('stage',choices=['body','fins'])
    args = parser.parse_args()
    species = args.species
    folder = WORK/species
    output = folder/args.stage
    assert not output.exists()
    item = next(i for i in json.loads((WORK/'manifest.json').read_text())['items'] if i['species']==species)
    baseline = Path(item['canonical']['path'])
    concept_path = Path(item['concept']['path'])
    assert sha(baseline)==item['canonical']['sha256'] and sha(concept_path)==item['concept']['sha256']
    source = baseline
    if args.stage=='fins':
        source = folder/'body/fish.glb'
        proof = json.loads((folder/'body-review.validation.json').read_text())
        assert proof['ok'] and proof['model_sha256']==sha(source)
    doc,blob = read_glb(source)
    inventory = parts(doc,blob)
    images = {i:load_image_chart(doc,blob,i) for i in range(len(doc['images']))}
    bake = raster_body if args.stage=='body' else raster_fins
    patched,report = bake(species,inventory,images,read_image(concept_path))
    output.mkdir()
    records = {}
    for idx, image in patched.items():
        path = output/f'image-{idx}.png'
        Image.fromarray(image).save(path)
        count = int(np.any(image[:,:,:3]!=images[idx][:,:,:3],axis=2).sum())
        assert count>0
        records[idx] = {'path':str(path),'sha256':sha(path),'changed_rgb_texels':count}
    glb = output/'fish.glb'
    export_image_candidate(doc,blob,glb,{idx:Path(r['path']) for idx,r in records.items()})
    report.update(ok=True,species=species,stage=args.stage,model_sha256=sha(glb),input_model_sha256=sha(source),
                  concept_sha256=sha(concept_path),changed_images=records,alpha_preserved=True)
    (output/'bake.validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(species,args.stage,[(i,r['changed_rgb_texels']) for i,r in records.items()],flush=True)

if __name__=='__main__':
    main()
