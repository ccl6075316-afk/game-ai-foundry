"""Declarative native rest-shape revisions, shared by CLI and Blender."""
import hashlib
import json
import math
import re
from pathlib import Path


def validate_revision(revision):
    allowed = {'source_handoff', 'source_handoff_sha256', 'source_blend', 'source_glb', 'blend_sha256', 'glb_sha256', 'stations'}
    if not isinstance(revision, dict) or not allowed <= set(revision) or set(revision)-allowed-{'vertical_stations'}:
        raise ValueError('rest_shape_revision requires ' + ', '.join(sorted(allowed)) + '; only vertical_stations is optional')
    for key in ['source_handoff', 'source_blend', 'source_glb']:
        if not isinstance(revision[key], str) or not revision[key]:
            raise ValueError('Revision requires ' + key)
    for key in ['source_handoff_sha256', 'blend_sha256', 'glb_sha256']:
        if not isinstance(revision[key], str) or not re.fullmatch('[0-9a-f]{64}', revision[key]):
            raise ValueError('Invalid revision ' + key)
    rows = revision['stations']
    if not isinstance(rows, list) or not 2 <= len(rows) <= 128:
        raise ValueError('Revision requires 2–128 stations [u, source_half_width, target_half_width]')
    previous = -1
    for row in rows:
        if not isinstance(row, list) or len(row) != 3 or not all(type(v) in (int, float) and math.isfinite(v) for v in row):
            raise ValueError('Invalid revision station')
        u, old, new = row
        # Native terminal rings can be very narrow; broad muzzle experiments may
        # need >4x there. Absolute half-width remains bounded to half the image.
        if not previous < u <= 1 or u < 0 or not .0001 <= old <= .5 or not .0001 <= new <= .5 or not .25 <= new / old <= 12:
            raise ValueError('Revision stations require increasing u, positive bounded widths and scale .25–12')
        previous = u
    if 'vertical_stations' in revision:
        rows=revision['vertical_stations']
        if not isinstance(rows,list) or not 2<=len(rows)<=128:
            raise ValueError('Vertical revision requires 2–128 stations [u, old_top_v, old_bottom_v, new_top_v, new_bottom_v]')
        previous=-1
        for row in rows:
            if not isinstance(row,list) or len(row)!=5 or not all(type(v) in (int,float) and math.isfinite(v) and 0<=v<=1 for v in row):
                raise ValueError('Invalid vertical revision station')
            u,ot,ob,nt,nb=row
            if not previous<u or not ot<ob or not nt<nb or not .25<=(nb-nt)/(ob-ot)<=4:
                raise ValueError('Vertical stations require increasing u, top<bottom and height scale .25–4')
            previous=u


def validate_root_attachment(value):
    if not isinstance(value,dict) or set(value)!={'mode','root_band','blend_end','inset'} or value['mode']!='body_surface':
        raise ValueError('root_attachment requires mode=body_surface, root_band, blend_end, inset')
    if not all(type(value[k]) in (int,float) and math.isfinite(value[k]) for k in ['root_band','blend_end','inset']):
        raise ValueError('Nonfinite root attachment value')
    if not 0<=value['root_band']<value['blend_end']<=1 or not 0<=value['inset']<=.005:
        raise ValueError('Root attachment requires 0<=root_band<blend_end<=1 and inset 0–.005')


def root_attachment_gain(t,root_band,blend_end):
    """One across the complete root band, fading smoothly to zero distally."""
    t=max(0,min(1,(t-root_band)/(blend_end-root_band)))
    return 1-t*t*(3-2*t)


def vertical_position(stations,u,z,aspect):
    """Map native Z by interpolating bounded affine maps in normalized source v."""
    def coefficients(row):
        _,ot,ob,nt,nb=row
        scale=(nb-nt)/(ob-ot)
        return scale,aspect*((.5-(nt+nb)/2)-scale*(.5-(ot+ob)/2))
    if not stations:return z
    if u<=stations[0][0]:scale,offset=coefficients(stations[0])
    elif u>=stations[-1][0]:scale,offset=coefficients(stations[-1])
    else:
        for left,right in zip(stations,stations[1:]):
            if u<=right[0]:
                t=(u-left[0])/(right[0]-left[0]);t=t*t*(3-2*t)
                a,b=coefficients(left);c,d=coefficients(right)
                scale,offset=(1-t)*a+t*c,(1-t)*b+t*d
                break
    return z*scale+offset


def width_scale(stations, u):
    """C1 smoothstep interpolation of width ratio; endpoint ratios extend outside."""
    if u <= stations[0][0]:
        return stations[0][2] / stations[0][1]
    for left, right in zip(stations, stations[1:]):
        if u <= right[0]:
            t = (u - left[0]) / (right[0] - left[0])
            t = t * t * (3 - 2 * t)
            return (1 - t) * left[2] / left[1] + t * right[2] / right[1]
    return stations[-1][2] / stations[-1][1]


def revision_source(revision, base, current):
    """Check historical acceptance without reinterpreting its old procedural profile."""
    validate_revision(revision)
    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    handoff = (Path(base) / revision['source_handoff']).resolve()
    if digest(handoff) != revision['source_handoff_sha256']:
        raise ValueError('Revision source handoff hash changed')
    original = json.loads(handoff.read_text(encoding='utf-8'))
    if original.get('kind') != 'fish_volume_handoff' or original.get('status') != 'done' or original.get('style_visual_review') != 'accepted':
        raise ValueError('Revision requires an accepted historical volume handoff')
    review = original.get('style_review', {})
    if review.get('reviewer') != 'command_operator' or not review.get('note', '').strip():
        raise ValueError('Revision source visual review missing')
    hashes = review.get('hashes', {})
    for key in ['blend', 'glb']:
        path = (Path(base) / revision['source_' + key]).resolve()
        if any(path == Path(value).resolve() for name, value in current.get('outputs', {}).items() if name in ['blend', 'glb']):
            raise ValueError('Revision output must not overwrite accepted native inputs')
        expected = revision[key + '_sha256']
        if digest(path) != expected or hashes.get(key + '_sha256') != expected:
            raise ValueError('Revision source ' + key + ' differs from accepted hashes')
    for key in ['source', 'front_source', 'top_source', 'bottom_source']:
        expected = current.get(key, {}).get('sha256')
        if original.get(key, {}).get('sha256') != expected:
            raise ValueError('Revision must retain original ' + key + ' texture')
        if expected and (hashes.get(key + '_sha256') != expected):
            raise ValueError('Revision source texture acceptance hash missing: ' + key)
    if any(original.get('style_contract', {}).get(k) != current.get('style_contract', {}).get(k) for k in ['pixel_art', 'source_sha256', 'style_reference_sha256', 'texture_filter', 'roughness']):
        raise ValueError('Revision must retain original style contract')
    return original
