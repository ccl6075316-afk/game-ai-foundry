"""Cold export the formal hairtail or silver arowana from its packed source."""
import argparse
import sys
from pathlib import Path

import bpy

ROOT = next(path for path in Path(__file__).resolve().parents if (path/'cli/gamefactory.py').is_file())
sys.path[:0] = [str(ROOT/'resources/volume-fish/clean-pixel-three-20261112/methods'),
                str(ROOT/'resources/scripts/volume-fish/hairtail_20261104')]
from author_three import native_export
from export_contract import export_current

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('species',choices=('hairtail','silver_arowana'))
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
source, output = args.source.resolve(), args.output.resolve()
assert source.is_file() and source.suffix == '.blend'
assert not output.exists() and output.suffix == '.glb' and output.is_relative_to(ROOT/'work')
output.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source))
if args.species=='hairtail':
    export_current(output)
else:
    native_export(output)
