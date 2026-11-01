"""Measure current physical rings in a preserved material-reference chart.

Input points contain actual XYZ followed by reference XYZ. This deliberately
does not replace feature reference coordinates after a body shape edit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def build(source, x_range, size, ring_points, active_max_x):
    points = np.asarray(source['points'], dtype=float)
    sections = np.asarray(source['sections'], dtype=float)
    assert points.ndim == 2 and points.shape[1] == 6 and np.isfinite(points).all()
    assert np.all(np.diff(sections[:, 0]) > 0)
    width, height = size
    assert width >= 2 and height >= 3 and height % 2 == 1
    # texture() samples at texel centres; endpoints are not texel centres.
    angles = ((np.arange(height) + .5) / height - .5) * (2 * np.pi)
    sample_x = x_range[0] + (np.arange(width) + .5) / width * (x_range[1] - x_range[0])
    xs, rings = [], []
    for x in np.unique(np.round(points[:, 3], 6)):
        if not x_range[0] - 1e-6 <= x <= x_range[1] + 1e-6:
            continue
        ring = np.unique(np.round(points[np.round(points[:, 3], 6) == x], 6), axis=0)
        assert len(ring) == ring_points, f'Incomplete/ambiguous ring at {x}: {len(ring)}'
        if x <= active_max_x:
            assert np.max(abs(ring[:, 0] - ring[:, 3])) < 1e-6, 'Active longitudinal transport unsupported'
        cy, ry, rz = [np.interp(x, sections[:, 0], sections[:, i]) for i in (1, 2, 3)]
        assert min(ry, rz) > 0
        reference = np.stack(((ring[:, 4] - cy) / ry, np.clip(ring[:, 5] / rz, -1, 1)), 1)
        theta = np.arctan2(reference[:, 1], reference[:, 0])
        order = np.argsort(theta)
        theta, reference, yz = theta[order], reference[order], ring[order, 1:3]
        theta = np.r_[theta[-1] - 2*np.pi, theta, theta[0] + 2*np.pi]
        reference = np.vstack((reference[-1], reference, reference[0]))
        yz = np.vstack((yz[-1], yz, yz[0]))
        lengths = np.linalg.norm(np.diff(yz, axis=0), axis=1)
        cumulative = np.r_[0., lengths.cumsum()]

        def distance_at(target):
            index = np.clip(np.searchsorted(theta, target, side='right')-1, 0, len(theta)-2)
            direction = np.stack((np.cos(target), np.sin(target)), -1)
            origin, delta = reference[index], reference[index+1]-reference[index]
            cross = lambda a,b: a[...,0]*b[...,1]-a[...,1]*b[...,0]
            denominator = cross(delta, direction)
            assert np.all(abs(denominator)>1e-12)
            fraction = -cross(origin, direction)/denominator
            assert np.all((fraction>=-1e-5)&(fraction<=1+1e-5))
            return cumulative[index] + np.clip(fraction,0,1)*lengths[index]

        distance = distance_at(angles) - distance_at(np.array(0.))
        assert np.all(np.diff(distance)>=-1e-7)
        xs.append(float(x)); rings.append(distance)
    assert len(xs)>=3 and xs[0]<=sample_x[0] and xs[-1]>=sample_x[-1]
    rings = np.asarray(rings)
    lut = np.stack([np.interp(sample_x,xs,rings[:,j]) for j in range(height)]).astype('<f4')
    return lut, len(xs)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--report',type=Path,required=True)
    ap.add_argument('--x-range',type=float,nargs=2,required=True)
    ap.add_argument('--size',type=int,nargs=2,default=[512,513])
    ap.add_argument('--ring-points',type=int,required=True)
    ap.add_argument('--active-max-x',type=float,required=True,
                    help='Existing shader must have zero dorsal replacement beyond this reference X')
    args=ap.parse_args()
    assert args.x_range[1]>args.x_range[0]
    assert args.x_range[0]<args.active_max_x<=args.x_range[1]
    lut,count=build(json.loads(args.input.read_text()),args.x_range,args.size,args.ring_points,args.active_max_x)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(lut.tobytes())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report={'ok':True,'kind':'transported_surface_arc','input':str(args.input.resolve()),'input_sha256':sha(args.input),
            'output':str(args.output.resolve()),'output_sha256':sha(args.output),'builder_sha256':sha(Path(__file__)),
            'x_range':args.x_range,'size':args.size,'ring_count':count,'ring_points':args.ring_points,
            'active_max_x':args.active_max_x,
            'sampling':'GPU normalized texel centres; actual polygon lengths, preserved reference-theta index',
            'scope':'Numerical construction only. Independent finite-triangle test, actual GPU and visual review required.'}
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
