"""Species pair entry point, standard gates with two physical worker processes."""
from pathlib import Path
p=Path(__file__).with_name('run_delivery_checks.py')
s=p.read_text(encoding='utf8').replace("'--membrane-workers','4'", "'--membrane-workers','2'")
exec(compile(s,str(p),'exec'))
