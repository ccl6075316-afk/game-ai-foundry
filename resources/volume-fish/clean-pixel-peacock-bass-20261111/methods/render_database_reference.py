from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

stage = Path(__file__).resolve().parent
root = stage.parents[2]
obj = root / 'resources/fish-database/artifacts/fishing-master-cdn-cnformal1-20261102/mesh-exports/8aee5194fdb8db65405f37ee81b7a3540bf0de5c572920dcc767b049b4bbe9f1.obj'
verts, normals, faces, normal_indices = [], [], [], []
for line in obj.read_text().splitlines():
    fields = line.split()
    if not fields:
        continue
    if fields[0] == 'v':
        verts.append(list(map(float, fields[1:])))
    elif fields[0] == 'vn':
        normals.append(list(map(float, fields[1:])))
    elif fields[0] == 'f':
        tokens = [field.split('/') for field in fields[1:]]
        assert len(tokens) == 3
        faces.append([int(token[0])-1 for token in tokens])
        normal_indices.append([int(token[-1])-1 for token in tokens])
verts, normals, faces, normal_indices = map(np.array, (verts, normals, faces, normal_indices))
assert len(verts) == 1950 and len(faces) == 3156

def render(angle, center, scale, size):
    yaw = np.radians(angle)
    toward_camera = np.array([np.cos(yaw), -np.sin(yaw), .0])
    right = np.array([-np.sin(yaw), -np.cos(yaw), .0])
    up = np.array([0,0,1.])
    light = (toward_camera - right + up) / np.sqrt(3)
    xyz = verts - center
    w,h = size
    xx, yy, zz = (w/2 + scale * xyz @ right, h/2 - scale * xyz @ up, xyz @ toward_camera)
    buffer = np.zeros((h,w,3), np.uint8)
    buffer[:] = (32,45,53)
    depth = np.full((h,w), -np.inf)
    for tri, ns in zip(faces, normal_indices):
        x,y,z = xx[tri], yy[tri], zz[tri]
        x0,x1 = max(0,int(np.floor(x.min()))), min(w,int(np.ceil(x.max()))+1)
        y0,y1 = max(0,int(np.floor(y.min()))), min(h,int(np.ceil(y.max()))+1)
        if x0>=x1 or y0>=y1:
            continue
        denom=(y[1]-y[2])*(x[0]-x[2])+(x[2]-x[1])*(y[0]-y[2])
        if abs(denom)<1e-8:
            continue
        px,py=np.meshgrid(np.arange(x0,x1)+.5,np.arange(y0,y1)+.5)
        a=((y[1]-y[2])*(px-x[2])+(x[2]-x[1])*(py-y[2]))/denom
        b=((y[2]-y[0])*(px-x[2])+(x[0]-x[2])*(py-y[2]))/denom
        c=1-a-b
        zz1=a*z[0]+b*z[1]+c*z[2]
        target=depth[y0:y1,x0:x1]
        visible=(a>=0)&(b>=0)&(c>=0)&(zz1>target)
        if not visible.any():
            continue
        target[visible]=zz1[visible]
        normal=a[visible,None]*normals[ns[0]]+b[visible,None]*normals[ns[1]]+c[visible,None]*normals[ns[2]]
        normal/=np.maximum(1e-8,np.linalg.norm(normal,axis=1,keepdims=True))
        lambert=.33+.67*np.maximum(0,normal@light)
        buffer[y0:y1,x0:x1][visible]=(lambert[:,None]*np.array([210,218,221])).astype(np.uint8)
    return Image.fromarray(buffer)

render(0,[0,.05,.44],420,(1150,620)).save(stage/'Orinoco-game-reference-side.png')
for name,angle in [('side',0),('three-quarter',42),('front',90)]:
    render(angle,[0,-.76,.31],925,(780,600)).save(stage/f'Orinoco-game-reference-head-{name}.png')
