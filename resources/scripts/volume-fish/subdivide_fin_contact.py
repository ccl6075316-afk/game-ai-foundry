"""Conforming contact-region refinement for GLB attributes, before projection.

Interpolates UV and skin weights; retains the complete original root selection.
Every new basal vertex is recorded, never inferred later from a smaller region.
"""
import math

def midpoint(a,b):
    return interpolate([a,b],[.5,.5])

def interpolate(rows,weights):
    result={}
    for key in rows[0]:
        if key in ('JOINTS_0','WEIGHTS_0','root'):continue
        result[key]=tuple(sum(w*r[key][j] for r,w in zip(rows,weights)) for j in range(len(rows[0][key])))
    result['root']=all(r['root'] for r in rows)
    if 'JOINTS_0' in rows[0]:
        skin={}
        for row,w in zip(rows,weights):
            for joint,amount in zip(row['JOINTS_0'],row['WEIGHTS_0']):skin[joint]=skin.get(joint,0)+w*amount
        items=sorted(skin.items(),key=lambda v:-v[1])[:4]
        while len(items)<4:items.append((0,0.))
        total=sum(v for _,v in items)
        result['JOINTS_0']=tuple(j for j,_ in items)
        result['WEIGHTS_0']=tuple(v/total for _,v in items)
    return result

def refine(rows,triangles,limit,near_surface,max_rounds=24):
    original=len(rows)
    for iteration in range(max_rounds):
        edges={}
        for tri in triangles:
            for a,b in zip(tri,tri[1:]+tri[:1]):
                edge=tuple(sorted((a,b)))
                if edge in edges:continue
                pa,pb=rows[a]['POSITION'],rows[b]['POSITION']
                if math.dist(pa,pb)<=limit:continue
                mid=midpoint(rows[a],rows[b])
                if rows[a]['root'] or rows[b]['root'] or near_surface(mid['POSITION']):edges[edge]=mid
        if not edges:return rows,triangles,{'rounds':iteration,'added_vertices':len(rows)-original,'max_contact_edge':limit}
        added={}
        for edge,row in edges.items():added[edge]=len(rows);rows.append(row)
        rebuilt=[]
        for tri in triangles:
            mids=[added.get(tuple(sorted((tri[k],tri[(k+1)%3])))) for k in range(3)]
            if all(m is not None for m in mids):
                a,b,c=tri;ab,bc,ca=mids
                rebuilt.extend([(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)])
                continue
            pieces=[tri]
            for a,b in zip(tri,tri[1:]+tri[:1]):
                m=added.get(tuple(sorted((a,b))))
                if m is None:continue
                split=[]
                for piece in pieces:
                    if a not in piece or b not in piece:split.append(piece);continue
                    for k in range(3):
                        x,y,z=piece[k],piece[(k+1)%3],piece[(k+2)%3]
                        if {x,y}=={a,b}:split.extend([(x,m,z),(m,y,z)]);break
                pieces=split
            rebuilt.extend(pieces)
        triangles=rebuilt
        assert len(rows)<250000,'Contact refinement exceeded safe size'
    raise AssertionError('Contact refinement did not converge')
