"""Blender test: compare rig/rest/actions from two independently opened sources."""
import argparse
import json
from pathlib import Path
import sys
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fish_asset_spec import fresh_outputs,sha
from source_snapshot import rig_action_snapshot
p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True);p.add_argument('--authored',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
fresh_outputs([a.output],[a.original,a.authored]);before={str(p.resolve()):sha(p)for p in (a.original,a.authored)}
bpy.ops.wm.open_mainfile(filepath=str(a.original.resolve()));original=rig_action_snapshot()
bpy.ops.wm.open_mainfile(filepath=str(a.authored.resolve()));authored=rig_action_snapshot()
assert original==authored,'Cold-opened authored source changed rig/rest/pose/actions/NLA'
assert before=={str(p.resolve()):sha(p)for p in (a.original,a.authored)}
a.output.write_text(json.dumps({'ok':True,'kind':'synthetic_cold_source_rig_rest_action_parity','inputs':before,'all_rig_rest_pose_actions_NLA_equal':True},indent=2)+'\n')
print(json.dumps({'ok':True,'report':str(a.output.resolve())}))
