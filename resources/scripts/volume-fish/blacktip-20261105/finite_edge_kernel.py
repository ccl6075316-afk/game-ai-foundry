import numpy as np
EPS=1e-9
def cross2(a, b):
    return a[0] * b[1] - a[1] * b[0]

def overlap_area(a, b, normal):
    axes = [i for i in range(3) if i != int(np.argmax(abs(normal)))]
    subject = [p[axes] for p in a]
    clip = b[:, axes]
    orientation = 1 if cross2(clip[1] - clip[0], clip[2] - clip[0]) > 0 else -1
    for j in range(3):
        aa = clip[j]
        edge = clip[(j + 1) % 3] - aa
        new = []
        if not subject:
            break
        for p, q in zip(subject, subject[1:] + subject[:1]):
            dp = orientation * cross2(edge, p - aa)
            dq = orientation * cross2(edge, q - aa)
            pin = dp >= 0
            qin = dq >= 0
            if pin:
                new.append(p)
            if pin != qin:
                new.append(p + (q - p) * dp / (dp - dq))
        subject = new
    return abs(sum((cross2(p, q) for p, q in zip(subject, subject[1:] + subject[:1])))) / 2 if len(subject) >= 3 else 0.0

def coplanar_segment_hits(p,q,other):
    # Extended precision finite clipping, no larger geometric epsilon.
    normal=np.cross(other[1]-other[0],other[2]-other[0]);axes=[i for i in range(3)if i!=int(np.argmax(abs(normal)))];clip=other[:,axes].astype(np.longdouble);a=p[axes].astype(np.longdouble);b=q[axes].astype(np.longdouble);orientation=1 if cross2(clip[1]-clip[0],clip[2]-clip[0])>0 else -1;lo=np.longdouble(0);hi=np.longdouble(1)
    for i in range(3):
        origin=clip[i];edge=clip[(i+1)%3]-origin;da=orientation*cross2(edge,a-origin);db=orientation*cross2(edge,b-origin)
        if da<0 and db<0:return []
        if da>=0 and db>=0:continue
        t=da/(da-db)
        if da<0:lo=max(lo,t)
        else:hi=min(hi,t)
        if lo>hi:return []
    return [p+float(lo)*(q-p),p+float(hi)*(q-p)]

def intersect(a, b):
    na = np.cross(a[1] - a[0], a[2] - a[0])
    nb = np.cross(b[1] - b[0], b[2] - b[0])
    na /= np.linalg.norm(na)
    nb /= np.linalg.norm(nb)
    da = (b - a[0]) @ na
    db = (a - b[0]) @ nb
    if da.min() > EPS or da.max() < -EPS or db.min() > EPS or (db.max() < -EPS):
        return None
    shared = []
    for p in a:
        if np.linalg.norm(b - p, axis=1).min() < EPS * 4:
            shared.append(p)
    if abs(na @ nb) > 1 - 1e-10 and np.max(abs((b - a[0]) @ na)) < EPS:
        area = overlap_area(a, b, na)
        if area > EPS ** 2 * 4:
            return {'kind': 'coplanar_positive_area', 'area_m2': area, 'shared_vertices': len(shared)}
        return None
    if len(shared) == 2:
        return None
    hits = []
    for tri, other in [(a, b), (b, a)]:
        for i, j in [(0, 1), (1, 2), (2, 0)]:
            delta = tri[j] - tri[i]
            length = np.linalg.norm(delta)
            if length < EPS:
                continue
            other_normal=np.cross(other[1]-other[0],other[2]-other[0]);other_normal/=np.linalg.norm(other_normal)
            plane_distances=(tri[[i,j]]-other[0])@other_normal
            if np.max(abs(plane_distances))<=EPS:
                hits.extend(coplanar_segment_hits(tri[i],tri[j],other))
                continue
            direction = delta / length
            e1 = other[1] - other[0]
            e2 = other[2] - other[0]
            h = np.cross(direction, e2)
            det = e1 @ h
            hit = None
            if abs(det) > 1e-13 * np.linalg.norm(e1) * np.linalg.norm(e2):
                s = tri[i] - other[0]
                u = s @ h / det
                q = np.cross(s, e1)
                v = direction @ q / det
                t = e2 @ q / det
                if u >= -1e-10 and v >= -1e-10 and (u + v <= 1 + 1e-10):
                    hit = tri[i] + t * direction
            if hit is None:
                continue
            p = np.array(hit)
            distance = (p - tri[i]) @ (delta / length)
            if -EPS <= distance <= length + EPS:
                hits.append(p)

    def legal(p):
        if not shared:
            return False
        if len(shared) == 1:
            return np.linalg.norm(p - shared[0]) < EPS * 10
        edge = shared[1] - shared[0]
        t = np.clip((p - shared[0]) @ edge / (edge @ edge), 0, 1)
        return np.linalg.norm(p - shared[0] - t * edge) < EPS * 10
    bad = [p.tolist() for p in hits if not legal(p)]
    return {'kind': 'nonadjacent_segment_crossing', 'points_m': bad, 'shared_vertices': len(shared)} if bad else None

def check(v, t):
    points = v[t]
    lo = points.min(1)
    hi = points.max(1)
    candidate = np.all((hi[:, None, :] + EPS >= lo[None, :, :]) & (hi[None, :, :] + EPS >= lo[:, None, :]), axis=2)
    pairs = np.transpose(np.where(np.triu(candidate, 1))).tolist()
    fail = []
    shared = 0
    total_pairs = len(pairs)
    if pairs:
        pp = np.array(pairs)
        aa = points[pp[:, 0]]
        bb = points[pp[:, 1]]
        normal = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
        normal /= np.linalg.norm(normal, axis=1)[:, None]
        na = normal[pp[:, 0]]
        nb = normal[pp[:, 1]]
        da = np.einsum('pij,pj->pi', bb - aa[:, :1], na)
        db = np.einsum('pij,pj->pi', aa - bb[:, :1], nb)
        keep = ~((da.min(1) > EPS) | (da.max(1) < -EPS) | (db.min(1) > EPS) | (db.max(1) < -EPS))
        common = (t[pp[:, 0], :, None] == t[pp[:, 1], None, :]).any(2).sum(1)
        coplanar = (abs(np.einsum('ij,ij->i', na, nb)) > 1 - 1e-10) & (abs(da).max(1) < EPS)
        keep &= ~((common >= 2) & ~coplanar)
        geometric_shared = np.linalg.norm(bb[:, :, None, :] - aa[:, None, :, :], axis=3) < EPS * 4
        shared_b = geometric_shared.any(2)
        shared_a = geometric_shared.any(1)
        legal_b = ((da.min(1) >= -EPS) | (da.max(1) <= EPS)) & np.all((abs(da) > EPS) | shared_b, axis=1) & ~coplanar
        legal_a = ((db.min(1) >= -EPS) | (db.max(1) <= EPS)) & np.all((abs(db) > EPS) | shared_a, axis=1) & ~coplanar
        keep &= ~(legal_a | legal_b)
        ci = np.where(keep & coplanar)[0]
        if len(ci):
            ca = aa[ci]
            cb = bb[ci]
            normal_c = na[ci]
            edge = np.concatenate([np.roll(ca, -1, axis=1) - ca, np.roll(cb, -1, axis=1) - cb], axis=1)
            axes = np.cross(normal_c[:, None, :], edge)
            axes /= np.linalg.norm(axes, axis=2)[:, :, None]
            pa = np.einsum('ptj,paj->pat', ca, axes)
            pb = np.einsum('ptj,paj->pat', cb, axes)
            overlap = np.minimum(pa.max(2), pb.max(2)) - np.maximum(pa.min(2), pb.min(2))
            separated = (overlap <= EPS).any(1)
            keep[ci[separated]] = False
        pairs = pp[keep].tolist()
    for a, b in pairs:
        shared += bool(set(t[a]) & set(t[b]))
        hit = intersect(v[t[a]], v[t[b]])
        if hit:
            fail.append({'triangles': [a, b], **hit})
    return {'bvh_candidate_pairs': total_pairs, 'finite_plane_candidate_pairs': len(pairs), 'candidate_pairs_with_shared_indices': shared, 'illegal_intersections': fail, 'ok': not fail}
