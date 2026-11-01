"""Verified original geometric source points; texture UV is a separate field."""
import numpy as np
from mathutils.geometry import delaunay_2d_cdt
from build_fish import fin_source_geometry
from volume_shape import fin_baseline_parameter


class OriginalFinSource:
    def __init__(self,ob,fin,aspect,W,H):
        polygon,points=fin_source_geometry(fin,aspect)
        dv,_,df,*_=delaunay_2d_cdt(points,[(i,(i+1)%len(polygon))for i in range(len(polygon))],[list(range(len(polygon)))],1,1e-7)
        self.count=len(dv);assert len(ob.data.vertices)==2*self.count,'Original source point inventory differs; explicit mapping required'
        self.points=np.array(dv);self.triangles=df;self.W=W;self.H=H
        ts=ob.data.attributes['foundry_fin_source_t'];self.identity_error=max(abs(fin_baseline_parameter(q,fin['source_baseline'],polygon,aspect)-ts.data[i].value)for i,q in enumerate(dv));assert self.identity_error<1e-5,'Source geometric point identities differ'
        self.uv=[None]*len(ob.data.vertices)
        for loop,q in zip(ob.data.loops,ob.data.uv_layers.active.data):self.uv[loop.vertex_index]=np.array(q.uv)
        self.coords=np.array([v.co[:]for v in ob.data.vertices]);self.skin=[{ob.vertex_groups[g.group].name:g.weight for g in v.groups}for v in ob.data.vertices]

    def mapping(self,q):
        errors=np.linalg.norm((self.points-np.array(q))*[self.W,self.H],axis=1);nearest=int(np.argmin(errors))
        if errors[nearest]<.001:return(nearest,),np.array([1.])
        for ids in self.triangles:
            aa,bb,cc=self.points[list(ids)];matrix=np.column_stack((bb-aa,cc-aa))
            if abs(np.linalg.det(matrix))<1e-12:continue
            bc=np.linalg.solve(matrix,np.array(q)-aa);weights=np.r_[1-bc.sum(),bc]
            if min(weights)>=-1e-5:
                weights=np.maximum(weights,0);return tuple(ids),weights/weights.sum()
        raise AssertionError('Target outside original geometric source domain')

    def sample(self,q,layer):
        ids,weights=self.mapping(q);ids=[i+layer*self.count for i in ids];skin={}
        for i,w in zip(ids,weights):
            for bone,v in self.skin[i].items():skin[bone]=skin.get(bone,0)+w*v
        return(sum((self.coords[i]*w for i,w in zip(ids,weights)),np.zeros(3)),sum((self.uv[i]*w for i,w in zip(ids,weights)),np.zeros(2)),skin)
