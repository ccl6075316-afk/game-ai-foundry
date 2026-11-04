"""Measure registered hammerhead wing surfaces and anterior trunk chords.

Reference fins are not interpreted as body height. Reference eye components are
removed before defining head span. Values remain game-model shape evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from measure_hammerhead_head_field import load_reference, load_candidate, plane_intervals, vertical


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--reference',type=Path,required=True);ap.add_argument('--candidate',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    assert not args.output.exists()
    v,f=load_reference(args.reference);cv,cf=load_candidate(args.candidate,2.4914281368255615,1.032794117647059)
    w,inv=np.unique(np.round(v,7),axis=0,return_inverse=True);q=inv[f];e=np.concatenate([q[:,[0,1]],q[:,[1,2]],q[:,[2,0]]]);_,labels=connected_components(coo_matrix((np.ones(len(e)),(e[:,0],e[:,1])),shape=(len(w),len(w))),directed=False)
    face_labels=labels[q[:,0]];ids,counts=np.unique(face_labels,return_counts=True);body_label=ids[np.argmax(counts)];body_faces=f[face_labels==body_label]
    assert sorted(counts.tolist())==[64,64,3040]
    body_vertices=v[np.unique(body_faces)];rs=float(np.max(abs(body_vertices[body_vertices[:,0]<.14,2])));cs=.719661/2/2.4914281368255615
    fractions=[0,.025,.05,.075,.1,.15,.2,.25,.3,.35,.4,.425,.45,.5,.55,.6,.65,.7,.75,.8,.85,.9,.925,.95,.975,.99,.995]
    chord=[.005,.025,.05,.1,.15,.2,.3,.4,.5,.6,.7,.8,.85,.9,.95,.975,.995]
    rows=[]
    for frac in fractions:
        z=max(frac,1e-6)*rs;front,rear=plane_intervals(v[body_faces],z)[0];rear=min(rear,.1074)
        samples=[{'t':t,**vertical(v[body_faces],front+(rear-front)*t,z)}for t in chord]
        assert all(s['height'] is not None for s in samples)
        rows.append({'span_fraction':frac,'front':front,'rear':rear,'samples':samples})
    # Engineering axial correspondence: minimum anterior neck and source tail
    # joint Bone074 at .71975; own exported posterior body cap at .83096683.
    cn,rn,ct,rt=.1234,.1074,float(cv[:,0].max()),.71975
    trunk=[]
    for p in np.linspace(cn,.73,50):
        refp=rn+(p-cn)/(ct-cn)*(rt-rn)
        samples=[]
        for z in [.012,.015,.02]:
            r=vertical(v[body_faces],refp,z);c=vertical(cv[cf],p,z)
            if r['height'] is not None and c['height'] is not None:samples.append({'z_over_length':z,'reference':r,'candidate':c,'gain':r['height']/c['height']})
        assert samples
        # Declared .015L body chord; avoid unstable near-tail extrapolation.
        s=min(samples,key=lambda s:abs(s['z_over_length']-.015));trunk.append({'p':float(p),'reference_p':float(refp),'samples':samples,'height_gain':max(1.,s['gain'])})
    # Smooth envelope controls, each taken from the actual nearest measured row.
    controls=[]
    for p in [cn,.16,.2,.25,.3,.35,.4,.45,.5,.55,.6,.65,.7,.73]:
        row=min(trunk,key=lambda r:abs(r['p']-p));controls.append([p,row['height_gain']])
    controls += [[.78,1.],[ct,1.],[1.,1.]]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report={'kind':'registered_hammerhead_head_and_trunk_shape_reference','inputs':[{'path':str(p.resolve()),'sha256':sha(p)}for p in [args.reference,args.candidate]],'reference_eye_components_excluded':[int(k)for k in counts if k==64],'reference_body_fin_triangles':len(body_faces),'head_half_span_over_length':{'reference_body_without_eyes':rs,'candidate_body':cs},'neck_span_fraction':{'reference':.1107876206544594/2/rs,'candidate':.08168404043669747/2/cs},'axial_landmarks':{'candidate_neck':cn,'reference_neck':rn,'candidate_body_cap':ct,'reference_tail_joint_Bone074':rt},'head_rows':rows,'trunk_rows':trunk,'body_gain_controls':controls,'limits':['Reference game species unverified; no biological measurement or transferred acceptance.','Trunk data are actual off-centre finite body chord heights, not an asserted biological maximum body height. Median/paired-fin-free measurement channels are checked in separate silhouette diagnostics.','Tail joint is an engineering registration, not measured biological precaudal length.','Open reference jaw is excluded from direct adoption; project finite mouth pose must remain intact.','No external vertices, faces, outline or UV enters the author; only declared scalar/envelope samples.']}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'ok':True,'neck_span_fraction':report['neck_span_fraction'],'body_gain_controls':controls}))


if __name__=='__main__':main()
