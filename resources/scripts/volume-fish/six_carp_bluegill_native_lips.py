"""Apply the reviewed packed-rim method to bluegill's own independent source curves."""
from pathlib import Path
path=Path(__file__).with_name('six_cyprinid_native_lips.py')
source=path.read_text(encoding='utf8')
source=source.replace('{s.replace("_","-")}-central-material-20261031.json','bluegill-mouth-source-boundaries-20261031.json')
source=source.replace("out=root/'native-lips-r3'","out=root/'native-lips-r1'").replace("model=root/'width-r1/fish.glb'","model=root/'width-r3/fish.glb'")
exec(compile(source,str(path),'exec'))
