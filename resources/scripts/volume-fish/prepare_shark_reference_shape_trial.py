"""Measure explicit same-species reference masks for a bounded static shape trial.

No old fish width profile, generated smoothing curve or adult extrapolation.
The complete fish SOP and anatomy-specific mouth/fin production remain separate.
"""
import argparse,json,hashlib,math
from pathlib import Path
import numpy as np
from PIL import Image

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bounds(mask):
 y,x=np.where(mask);return [int(x.min()),int(y.min()),int(x.max()),int(y.max())]
def readmask(path):
 a=np.array(Image.open(path).convert('RGB'));return a.max(axis=2)<80
def column(mask,x):
 ys=np.where(mask[:,int(round(x))])[0];assert len(ys);return float(ys.min()),float(ys.max())

def prepare(config_path,output):
 cfg=json.loads(config_path.read_text(encoding='utf8'));assert cfg['species']=='scalloped_hammerhead' and cfg['dataset_directory_label']=='Sphyrna_lewini'
 directory=Path(cfg['reference_directory']);paths={k:directory/(k+'.png')for k in ['BodyL','BodyV','Ceph']};masks={k:readmask(v)for k,v in paths.items()};bb={k:bounds(v)for k,v in masks.items()}
 axis=cfg['reference_body_axis_m'];assert .56<axis<.57
 # Both body masks were normalized by the authors to approximately3000px.
 # Preserve their separate endpoint registration and report the17px difference.
 length_v=bb['BodyV'][2]-bb['BodyV'][0];length_l=bb['BodyL'][2]-bb['BodyL'][0];metres_per_pixel=axis/length_v
 ts=np.linspace(0,1,49);rows=[];vertical_origin=(bb['BodyL'][1]+bb['BodyL'][3])/2
 for t in ts:
  top,bottom=column(masks['BodyL'],bb['BodyL'][0]+t*length_l);left,right=column(masks['BodyV'],bb['BodyV'][0]+t*length_v)
  rows.append(dict(t=float(t),x_m=float(axis*(.5-t)),top_z_m=float((vertical_origin-top)*axis/length_l),bottom_z_m=float((vertical_origin-bottom)*axis/length_l),full_width_m=float((right-left)*metres_per_pixel),width_source_row=[left,right]))
 dense=[]
 for x in range(bb['BodyV'][0],bb['BodyV'][2]+1):
  lo,hi=column(masks['BodyV'],x);dense.append((hi-lo,(x-bb['BodyV'][0])/length_v))
 width,peak=max(dense);ceph=masks['Ceph'];head=[];center_y=(bb['Ceph'][1]+bb['Ceph'][3])/2;front=bb['Ceph'][0]
 for y in np.linspace(bb['Ceph'][1],bb['Ceph'][3],65):
  xs=np.where(ceph[int(round(y))])[0];assert len(xs)
  head.append(dict(y_m=float((y-center_y)*metres_per_pixel),front_x_m=float(axis/2-(xs.min()-front)*metres_per_pixel),rear_x_m=float(axis/2-(xs.max()-front)*metres_per_pixel)))
 result=dict(kind='same_species_reference_shape_trial_input',species=cfg['species'],scientific_name='Sphyrna lewini',reference_body_axis_m=axis,body_axis_definition='Original paper/package body.axis.l; CSV header FL_m retained separately, not silently relabelled TL/SL.',body_axis_max_width_m=float(width*metres_per_pixel),maximum_body_width_over_body_axis=float(width/length_v),body_width_peak_t=float(peak),head_span_m=float((bb['Ceph'][3]-bb['Ceph'][1])*metres_per_pixel),head_axial_extent_m=float((bb['Ceph'][2]-front)*metres_per_pixel),body_stations=rows,head_transverse_stations=head,raw_mask_bounds=bb,body_mask_axis_pixels=dict(lateral=length_l,ventral=length_v),inputs={k:dict(path=str(v.resolve()),sha256=sha(v))for k,v in paths.items()},reference_provenance=cfg['reference_provenance'],transverse_body_symmetry='Average the two actual silhouette sides around their local midpoint; source width retained. Does not recover unseen3D cross-section.',cross_section_and_head_thickness=cfg['cross_section_and_head_thickness'],mouth_trial=cfg['mouth_trial'],scope='Static head/body/oral trial at reference scale; no adult250cm replacement, no complete fins/rig/motion or user acceptance. Geometry representation and mouth engineering choices are explicit, not biological tissue measurements.')
 assert not output.exists();output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();r=prepare(a.config,a.output);print(json.dumps({k:r[k]for k in ['reference_body_axis_m','body_axis_max_width_m','maximum_body_width_over_body_axis','body_width_peak_t','head_span_m','head_axial_extent_m']}))
