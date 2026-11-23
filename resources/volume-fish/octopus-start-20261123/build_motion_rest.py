"""Derivative of R2 controls with a thicker membrane and sufficient skin density."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=(ROOT/'build_gray.py').read_text()
replacements={"OUT=ROOT/'r2'":"OUT=ROOT/'motion-r1'/'rest'",'OUT.mkdir(exist_ok=True)':'OUT.mkdir(parents=True,exist_ok=True)',".024*math.sin(math.pi*1.3)-.009":".024*math.sin(math.pi*1.3)-.028",'(.018*(1-u)+.009)':'(.025*(1-u)+.028)','2800/tri':'4800/tri',"sm.iterations=3":"sm.iterations=2"}
for old,new in replacements.items():
 assert old in source,old
 source=source.replace(old,new)
exec(compile(source,str(ROOT/'build_gray.py'),'exec'))
