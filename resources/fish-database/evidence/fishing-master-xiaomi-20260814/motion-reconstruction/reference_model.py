"""Research reconstruction of the source steering step, verified against ARM64.

Preserves source order, neighbor cap and repeated priority-list entries.
Not production gameplay code; no Unity rendering, route authoring or biological claim.
"""
import copy
import math

EPS = 1e-5
def add(a,b): return [x+y for x,y in zip(a,b)]
def sub(a,b): return [x-y for x,y in zip(a,b)]
def mul(a,s): return [x*s for x in a]
def length(a): return math.sqrt(sum(x*x for x in a))
def norm(a):
    n=length(a)
    return mul(a,1/n) if n>EPS else [0.,0.,0.]
def separation(diff,distance,radius):
    return mul(diff,max(0.,min(1.,1-distance/radius))/distance) if distance else [float('nan')]*3

def reconstruct_step(groups, obstacles, dt, force=20., lookahead=3, axis=0):
    groups=copy.deepcopy(groups); flee_calls=0
    for gi,g in enumerate(groups):
        if not g['controlled']: continue
        high=[] # Native clears once per GROUP, not once per fish.
        for fi,f in enumerate(g['fish']):
            if not f.get('controlled',True): continue
            p=f['p'][:]
            if axis==1:p[2]=0.
            elif axis==2:p[1]=0.
            center=g['anchor'][:];sep=[0.,0.,0.];align=[0.,0.,0.];avoid=[0.,0.,0.];count=1
            ahead=add(p,mul(f['v'],f['speed']*dt*lookahead))
            for obstacle in obstacles:
                if obstacle['type']==0:
                    lo,size=obstacle['p'],obstacle['size'];hit=all(a<=q<=a+s for q,a,s in zip(ahead,lo,size));c=add(lo,mul(size,.5))
                else:
                    c=obstacle['p'];hit=length(sub(ahead,c))<=obstacle['size'][0]
                if hit:avoid=mul(norm(add(avoid,sub(ahead,c))),force)
            for gj,other in enumerate(groups):
                if other['priority']==g['priority']:
                    radius=max(g['neighbor'],other['neighbor'])
                    for fj,n in enumerate(other['fish']):
                        if gi==gj and fi==fj:continue
                        diff=sub(p,n['p']);dist=length(diff)
                        if dist<radius:
                            center=add(center,n['p']);sep=add(sep,separation(diff,dist,radius));align=add(align,n['v']);count+=1
                            if count>9:break # Break this group's inner loop only.
                elif g['priority']<other['priority']:
                    high.append(gj)
            steer=add(add(norm(sub(mul(center,1/count),p)),mul(align,1/count)),add(sep,avoid))
            if axis==1:steer[2]=0.
            elif axis==2:steer[1]=0.
            flee=[0.,0.,0.]
            for gj in high:
                for other in groups[gj]['fish']:
                    if length(sub(p,other['p']))<groups[gj]['flee_radius']:
                        flee=add(flee,sub(mul(norm(sub(p,other['p'])),f['speed']),f['v']));flee_calls+=1
            desired=norm(add(steer,flee));current=norm(f['v']);factor=min(1,math.exp(-dt*f['rot']))
            f['v']=add(desired,mul(sub(current,desired),factor))
            f['p']=add(p,mul(f['v'],f['speed']*dt))
    return groups,flee_calls
