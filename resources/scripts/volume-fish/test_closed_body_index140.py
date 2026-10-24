"""Blender regression: seam precision and inconsistent winding must not hide burial."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from closed_body_index140 import build
v=np.array([[-.5,-.5,-.5],[.5,-.5,-.5],[.5,.5,-.5],[-.5,.5,-.5],[-.5,-.5,.5],[.5,-.5,.5],[.5,.5,.5],[-.5,.5,.5]])
t=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])
tests=0
for mode in ['original','mixed_winding','split_seams']:
 points=v.copy();faces=t.copy()
 if mode=='mixed_winding':faces[::2]=faces[::2][:,[0,2,1]]
 if mode=='split_seams':
  points=v[t].reshape(-1,3);points+=np.random.default_rng(140).uniform(-2e-8,2e-8,points.shape);faces=np.arange(len(points)).reshape(-1,3)
 contains=build(points,faces)
 for point,expected in [([0,0,0],True),([.4999,0,0],True),([.5001,0,0],False),([.7,.7,0],False),([-.5001,-.499,0],False)]:
  assert contains(point)==expected,(mode,point,expected);tests+=1
print('CLOSED_BODY_INDEX140',tests,'known inside/outside cases passed')
