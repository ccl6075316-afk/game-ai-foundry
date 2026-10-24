"""Explicit camera correction after operator rejection of the first top view."""
import json,shutil
from pathlib import Path
from catalog_workflows import call
root=Path(__file__).resolve().parents[3];project=root/'projects/aquascape-basalt_column-views-v5'
path=project/'plans/basalt_column_top.json';data=json.loads(path.read_text(encoding='utf-8'))
plan=data['plan']
plan['prompt']+='\nCAMERA CORRECTION AFTER REJECTED RESULT: The previous result was an isometric photograph, which is WRONG. Draw a FLAT MAP from the zenith. The tall central column must project as ONLY its small irregular polygon END CAP. No long dark vertical front walls anywhere. The lower columns appear as adjacent polygonal footprints/end caps, surrounding the tall column footprint. It should look like a compact cluster of rock end-caps seen straight downward, with subtle cracks and painted top surfaces only. Preserve the exact grey basalt pixel material. No elevated camera angle, no visible side facades, no depiction of column HEIGHT on the page.'
shutil.copy2(project/'output/basalt_column_top_raw.png',project/'output/basalt_column_top_rejected-r1.png')
path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(call(root,['assets','review','regenerate-batch','--pipeline-manifest',str(project/'pipeline/manifest.json'),'--asset','basalt_column_top','--reset-only','--no-recraft-prompt','--json'])['ok'])
