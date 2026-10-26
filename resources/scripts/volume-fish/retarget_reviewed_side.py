"""Transport a complete frozen fish through a reviewed side-envelope field.

All co-located body/overlay points share one field. Fin free-span adjustments
vanish at the old body support; topology, weights and source attributes survive.
This makes a candidate, never substitutes for current contact/motion validation.
"""
import argparse, json, hashlib
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def resolve_paths(plan, plan_path):
    resolved=dict(plan)
    base=(Path(plan_path).resolve().parent/plan.get('path_base','.')).resolve()
    for key in ('baseline','output','source'):
        if key in plan:
            path=Path(plan[key])
            resolved[key]=str(path if path.is_absolute() else base/path)
    return resolved

class SideField:
    def __init__(self, p, body):
        self.p=p
        # Rebuilt heads do not retain equal-X rings. Their measured finite
        # surface sections must override the regular trunk-ring estimator;
        # extrapolating the final trunk section collapses a short broad muzzle.
        if 'support_sections' in p:
            sections=np.asarray(p['support_sections'],float)
            if (sections.ndim!=2 or sections.shape[1]!=4 or len(sections)<2
                    or not np.isfinite(sections).all()
                    or not np.all(np.diff(sections[:,0])>0)
                    or not np.all(sections[:,2]>sections[:,1])
                    or not np.all(sections[:,3]>=0)):
                raise ValueError('support_sections require finite increasing X, positive height and nonnegative half-width')
        else:
            rows=[]
            for x in np.unique(np.round(body[:,0],6)):
                q=body[np.abs(body[:,0]-x)<5.1e-7]
                if len(q)>=24:
                    rows.append([x,q[:,1].min(),q[:,1].max(),np.abs(q[:,2]).max()])
            if len(rows)<=100:
                raise ValueError('Irregular body requires measured support_sections; regular ring fallback is unavailable')
            sections=np.asarray(rows)
        self.old=sections
        self.x=PchipInterpolator(*np.array(p['x_stations']).T)
        self.top=PchipInterpolator(*np.array(p['top_px']).T)
        self.bottom=PchipInterpolator(*np.array(p['bottom_px']).T)

    def support(self,v):
        x=v[:,0]
        lo,hi,rz=[np.interp(x,self.old[:,0],self.old[:,i]) for i in (1,2,3)]
        cy=(hi+lo)/2; ry=np.maximum((hi-lo)/2,1e-5)
        lateral=rz*np.sqrt(np.maximum(0,1-((v[:,1]-cy)/ry)**2))
        return lo,hi,rz,lateral

    def __call__(self,v,name='Closed_body'):
        v=np.asarray(v,float);o=v.copy();lo,hi,rz,lateral=self.support(v)
        x=self.x(v[:,0]);px=self.p['source_left']+(x+.5)*self.p['source_length']
        px=np.clip(px,self.p['top_px'][0][0],self.p['top_px'][-1][0])
        nyhi=(self.p['source_axis_y']-self.top(px))/self.p['source_length']
        nylo=(self.p['source_axis_y']-self.bottom(px))/self.p['source_length']
        t=(v[:,1]-lo)/np.maximum(hi-lo,1e-5)
        amount=np.clip((v[:,0]-.30)/.07,0,1);amount=amount*amount*(3-2*amount)
        # Interior feature line drops toward the short mouth, preserving endpoints.
        interior=np.maximum(0,1-(2*t-1)**2)
        t=t-self.p.get('head_feature_drop',0)*amount*interior
        if self.p.get('mouth_alignment'):
            cfg=self.p['mouth_alignment']
            old_mouth=PchipInterpolator(*np.asarray(cfg['old_curve']).T)(v[:,0])
            source_mouth=PchipInterpolator(*np.asarray(cfg['source_curve']).T)(px)
            knot=np.clip((old_mouth-lo)/np.maximum(hi-lo,1e-5),.03,.97)
            target=np.clip(((self.p['source_axis_y']-source_mouth)/self.p['source_length']-nylo)/np.maximum(nyhi-nylo,1e-5),.03,.97)
            raw=(v[:,1]-lo)/np.maximum(hi-lo,1e-5)
            aligned=np.where(raw<knot,raw*target/knot,target+(raw-knot)*(1-target)/(1-knot))
            gain=np.clip((v[:,0]-cfg['support'][0])/(cfg['support'][1]-cfg['support'][0]),0,1)
            gain=gain*gain*(3-2*gain);t=t*(1-gain)+aligned*gain
        o[:,0]=x;o[:,1]=nylo+t*(nyhi-nylo)
        if name.startswith(('Pectoral','Pelvic')):
            cfg=self.p['paired'][name.split('_')[0]]
            span=np.maximum(0,np.abs(v[:,2])-lateral-cfg['root_guard'])
            # Linear free-span field with a C1 transition at the protected root.
            k=cfg['blend_span'];span=np.where(span<k,span*span/(2*k),span-k/2)
            o[:,0]+=cfg['sweep_per_span']*span
            o[:,1]+=cfg['drop_per_span']*span
            o[:,2]-=np.sign(v[:,2])*cfg['fold_per_span']*span
        if name.startswith('Dorsal'):
            extra=np.maximum(v[:,1]-hi,0)
            o[:,1]=np.where(extra>0,nyhi+extra*self.p['dorsal_height_gain'].get(name,1),o[:,1])
        return o

    def jacobian(self,v,name):
        result=np.empty((len(v),3,3));eps=1e-6
        for j in range(3):
            delta=np.zeros_like(v);delta[:,j]=eps
            result[:,:,j]=(self(v+delta,name)-self(v-delta,name))/(2*eps)
        return result

def main():
    a=argparse.ArgumentParser();a.add_argument('--plan',type=Path,required=True);args=a.parse_args()
    p=resolve_paths(json.loads(args.plan.read_text()),args.plan);base=Path(p['baseline']);out=Path(p['output']);out.mkdir(parents=True,exist_ok=True)
    receipt=json.loads((base/'baseline.validation.json').read_text())
    body=np.concatenate([np.fromfile(base/s['attributes']['0'],dtype='<f4').reshape(-1,3) for n in receipt['nodes'] if n['name']=='Closed_body' for s in n['parts']])
    field=SideField(p,body);rows=[]
    for node in receipt['nodes']:
        name=node['name']
        for s in node['parts']:
            v=np.fromfile(base/s['attributes']['0'],dtype='<f4').reshape(-1,3).astype(float)
            normal=np.fromfile(base/s['attributes']['1'],dtype='<f4').reshape(-1,3).astype(float)
            new=field(v,name);j=field.jacobian(v,name)
            nn=np.linalg.solve(j.transpose(0,2,1),normal[:,:,None])[:,:,0]
            nn/=np.maximum(np.linalg.norm(nn,axis=1)[:,None],1e-12)
            if p.get('finite_surface_normals') and name=='Closed_body':
                tri=np.fromfile(base/s['attributes']['12'],dtype='<i4').reshape(-1,3)[:,[0,2,1]]
                face=np.cross(new[tri[:,1]]-new[tri[:,0]],new[tri[:,2]]-new[tri[:,0]])
                _,identity=np.unique(np.round(new,7),axis=0,return_inverse=True)
                totals=np.zeros((identity.max()+1,3))
                for k in range(3):np.add.at(totals,identity[tri[:,k]],face)
                actual=totals[identity];length=np.linalg.norm(actual,axis=1)
                valid=length>1e-12;nn[valid]=actual[valid]/length[valid,None]
            for slot,data in [('0',new),('1',nn)]:data.astype('<f4').tofile(out/s['attributes'][slot])
            uv=np.stack(((p['source_left']+(new[:,0]+.5)*p['source_length'])/p['source_width'],(p['source_axis_y']-new[:,1]*p['source_length'])/p['source_height']),1)
            uv.astype('<f4').tofile(out/(name+'-'+str(s['surface'])+'-source-uv.bin'))
            det=np.linalg.det(j)
            rows.append({'name':name,'surface':s['surface'],'vertices':len(v),'bounds':[new.min(0).tolist(),new.max(0).tolist()],'jacobian_min':float(det.min())})
    (out/'geometry.validation.json').write_text(json.dumps({'ok':all(x['jacobian_min']>0 for x in rows),'plan_sha256':sha(args.plan),'surfaces':rows,'scope':'Local geometry candidate; contact, full motion and export checks required.'},indent=2)+'\n')
    print(json.dumps(rows))
    return 0 if all(x['jacobian_min']>0 for x in rows) else 1

if __name__=='__main__':raise SystemExit(main())
