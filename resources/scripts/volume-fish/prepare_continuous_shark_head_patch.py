"""Make a sparse, shared head/neck surface cage from frozen reference contours.

Only XY envelopes are source-derived. Interior sections and the compact smooth
join are engineering interpolation, explicitly recorded; no voxel/high mesh.
The patch shares its posterior ring with the existing sparse body loft.
"""
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from shapely.geometry import Polygon, Point


def prepare(source, output, radial=12):
    cfg = json.loads(source.read_text(encoding='utf8'))
    rows = cfg['body_stations']; head = cfg['head_transverse_stations']
    axis = cfg['reference_body_axis_m']; join_t = rows[10]['t']
    join_x = rows[10]['x_m']; assert radial in [8,12]
    ts = np.array([r['t'] for r in rows])
    bw = PchipInterpolator(ts, [max(.00005,r['full_width_m']/2) for r in rows])
    bt = PchipInterpolator(ts, [r['top_z_m'] for r in rows])
    bb = PchipInterpolator(ts, [r['bottom_z_m'] for r in rows])
    ys = [r['y_m'] for r in head]
    front = PchipInterpolator(ys, [r['front_x_m'] for r in head])
    rear = PchipInterpolator(ys, [r['rear_x_m'] for r in head])
    hp = Polygon([(r['front_x_m'], r['y_m']) for r in head] +
                 [(r['rear_x_m'], r['y_m']) for r in head[::-1]])
    # The front core end is wholly inside the head. It cannot add a nose point.
    core_t = np.linspace(.075, join_t, 18)
    bp = Polygon([(axis*(.5-t),float(bw(t))) for t in core_t] +
                 [(axis*(.5-t),-float(bw(t))) for t in core_t[::-1]])
    domain = hp.union(bp)
    assert domain.geom_type == 'Polygon' and not domain.interiors
    boundary = list(domain.exterior.coords)[:-1]
    # Explicit posterior top/bottom semicircle samples for the same 12-gon.
    join_w = float(bw(join_t))
    ring_y = sorted(set(round(join_w*math.sin(i*math.tau/radial),12) for i in range(radial)))
    boundary = [p for p in boundary if abs(p[0]-join_x)>1e-9]
    rear_points = [(join_x,y) for y in ring_y]
    # Recover polygon order by inserting the posterior ring into its one edge.
    ordered = []
    raw = list(domain.exterior.coords)[:-1]
    for a,b in zip(raw,raw[1:]+raw[:1]):
        ordered.append(a)
        if abs(a[0]-join_x)<1e-9 and abs(b[0]-join_x)<1e-9:
            ordered.extend(sorted((p for p in rear_points if min(a[1],b[1])+1e-10<p[1]<max(a[1],b[1])-1e-10),key=lambda p:p[1],reverse=b[1]<a[1]))
    points = ordered[:]
    def add(x,y):
        if domain.contains(Point(x,y)) and min(math.hypot(x-a,y-b) for a,b in points)>.0006:
            points.append((float(x),float(y)))
    # Local chord rows support a continuous foil, without radial fans.
    for y in np.linspace(ys[0],ys[-1],25)[1:-1]:
        f,r = float(front(y)),float(rear(y))
        for q in [.12,.3,.5,.7,.88]: add(f*(1-q)+r*q,y)
    for t in np.linspace(.075,join_t,12):
        w=float(bw(t))
        for a in [-.8660254,-.5,0,.5,.8660254]: add(axis*(.5-t),a*w)
    head_z=float(np.mean([(r['top_z_m']+r['bottom_z_m'])/2 for r in rows if r['t']<.15]))
    half=cfg['head_span_m']*cfg['cross_section_and_head_thickness']['head_projected_full_thickness_over_span']/2
    smooth_k=.003  # Compact joining radius, engineering choice; <=.75mm bulge.
    def smax(a,b): return max(a,b)+max(0,smooth_k-abs(a-b))**2/(4*smooth_k)
    layers=[]
    for i,(x,y) in enumerate(points):
        t=(axis/2-x)/axis;w=float(bw(np.clip(t,0,1)))
        in_head=ys[0]-1e-10<=y<=ys[-1]+1e-10 and hp.covers(Point(x,y))
        in_body=x<=axis*(.5-.075)+1e-10 and abs(y)<=w+1e-10
        h=0.
        if in_head:
            f,r=float(front(np.clip(y,ys[0],ys[-1]))),float(rear(np.clip(y,ys[0],ys[-1])))
            q=np.clip((f-x)/max(f-r,1e-9),0,1)
            h=half*math.sin(math.pi*q)**.65
        local_mid=head_z
        if cfg.get('head_mid_z_from_side'):
            local_mid=float(bt(np.clip(t,0,1))+bb(np.clip(t,0,1)))/2
            if in_head:
                edge=cfg.get('head_edge_thickness_fraction',0.)
                h=(float(bt(np.clip(t,0,1))-bb(np.clip(t,0,1)))/2)*(edge+(1-edge)*math.sin(math.pi*q)**.65)
        top,bottom=local_mid+h,local_mid-h
        if in_body:
            mid=float(bt(t)+bb(t))/2;bh=float(bt(t)-bb(t))/2*math.sqrt(max(0,1-(y/w)**2))
            if in_head:
                g=np.clip((t-.075)/.045,0,1);g=g*g*(3-2*g)
                top=smax(top,local_mid*(1-g)+(mid+bh)*g)
                bottom=-smax(-bottom,-(local_mid*(1-g)+(mid-bh)*g))
            else: top,bottom=mid+bh,mid-bh
        # Boundary is a shared anatomical edge, except the open posterior ring.
        if i<len(ordered) and abs(x-join_x)>1e-8 and not cfg.get('head_edge_thickness_fraction',0):
            mid=(top+bottom)/2;top=bottom=mid
        layers.append([top,bottom])
    report=dict(kind='sparse_shared_cephalofoil_neck_cage',reference=str(source.resolve()),
                reference_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                points_xy=points,boundary_count=len(ordered),layers_z=layers,
                join_t=float(join_t),join_x_m=join_x,join_radial_segments=radial,
                source_input=cfg,head_thickness_power=.65,compact_join_radius_m=smooth_k,
                provenance='XY union of the same frozen head/body envelopes; shared surface, no Boolean overlap, voxel remesh, dense mesh or decimation. Interior thickness/compact smoothing are engineering interpolation, not measurements.',
                formal_acceptance=False)
    assert not output.exists();output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(points=len(points),boundary=len(ordered),join_t=float(join_t))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--radial',type=int,choices=[8,12],default=12);a=p.parse_args();prepare(a.reference,a.output,a.radial)
