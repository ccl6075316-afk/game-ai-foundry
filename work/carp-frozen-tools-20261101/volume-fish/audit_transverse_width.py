"""Measure actual finite body sections, preserving independent species evidence."""
import argparse,csv,hashlib,json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def section(positions,indices,x):
    triangles=positions[indices.reshape(-1,3)];hits=[]
    for i,j in [(0,1),(1,2),(2,0)]:
        a,b=triangles[:,i],triangles[:,j];on=np.abs(a[:,0]-x)<1e-8
        if on.any():hits.append(a[on])
        cross=(a[:,0]-x)*(b[:,0]-x)<0
        if cross.any():
            aa,bb=a[cross],b[cross];hits.append(aa+(bb-aa)*((x-aa[:,0])/(bb[:,0]-aa[:,0]))[:,None])
    assert hits,'No actual body section';return np.concatenate(hits)

def audit(spec_path,scientific_name,csv_path):
    spec=json.loads(spec_path.read_text(encoding='utf8'));model=Path(spec['model']['path']);assert sha(model)==spec['model']['sha256']
    doc,blob=read_glb(model);assert len(doc['meshes'])==1 and len(doc['meshes'][0]['primitives'])==1
    primitive=doc['meshes'][0]['primitives'][0];pos=arrays(doc,blob,primitive['attributes']['POSITION']);idx=arrays(doc,blob,primitive['indices']).reshape(-1)
    body=np.concatenate([idx[p['index_start']:p['index_start']+p['index_count']]for p in doc['extras']['geometry_parts']if p['role']in ['body_skin','mouth']]);scale=spec['viewer']['model_scale']*100;lo,hi=pos[:,0].min(),pos[:,0].max();L=hi-lo
    stations=[.005,.012,.025,.04,.06,.08,.10,.12,.15,.18,.22,.27,.32,.37,.42,.48,.55,.62,.70,.78,.84,.88,.92,.96]
    rows=[]
    for s in stations:
        x=hi-s*L
        try:q=section(pos,body,x)
        except AssertionError:continue
        w,h=np.ptp(q[:,2])*scale,np.ptp(q[:,1])*scale
        rows.append({'s_from_nose_over_visible_TL':s,'width_cm':float(w),'height_cm':float(h),'W_over_H':float(w/h)if h>0 else None})
    empirical=[]
    for r in csv.DictReader(csv_path.open(encoding='utf-8-sig')):
        if r['Tree_name'].replace('_',' ').lower()!=scientific_name.lower():continue
        values={k:float(v)for k,v in r.items()if k not in ['SpecimenID','Tree_name','Family','Order']and v not in['','NA']}
        empirical.append({'specimen_id':r['SpecimenID'],'scientific_name':scientific_name,'original':values,'units':'linear mm; weight g','W_over_SL':values['Max_fish_width']/values['Standard_length'],'W_over_H':values['Max_fish_width']/values['Max_body_depth'],'peduncle_W_over_H':values['Min_caudalpeduncle_width']/values['Min_caudalpeduncle_depth'],'jaw_joint_span_over_SL':values['Mouth_width']/values['Standard_length']})
    assert empirical,'No same-species original measurements'
    return {'ok':True,'kind':'actual_finite_body_width_and_same_species_measurements','species':spec['species'],'scientific_name':scientific_name,'model':str(model),'model_sha256':sha(model),'spec_sha256':sha(spec_path),'model_scale_cm':scale,'display_length_cm':float(L*scale),'sections':rows,'empirical':empirical,'sources':{'csv':str(csv_path.resolve()),'csv_sha256':sha(csv_path),'url':'https://zenodo.org/records/6642650'},'limits':['Smithsonian preserved small sample; observed range is not population limits.','Maximum fish width can occur at head; station and head transverse widths unavailable.','Mouth_width means jaw-joint span, not lip aperture.','SL differs from TL; no unreported TL conversion or allometry assumed.','Displayed shape and interpolation remain D-level authoring inferences.']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['spec','csv','output']:p.add_argument('--'+k,required=True,type=Path)
    p.add_argument('--scientific-name',required=True);a=p.parse_args();out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();out.parent.mkdir(parents=True,exist_ok=True);result=audit(a.spec.resolve(),a.scientific_name,a.csv.resolve());out.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode());print(json.dumps({'ok':True,'species':result['species'],'specimens':len(result['empirical']),'sections':len(result['sections'])}))
