from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=(ROOT/'measure_gray.py').read_text().replace("OUT=ROOT/'r2'", "OUT=ROOT/'motion-r1'").replace("(OUT/'gray-build.validation.json')", "(ROOT/'motion-r1/rest/gray-build.validation.json')").replace("octopus-gray.glb", "octopus-motion.glb")
exec(compile(source,str(ROOT/'measure_gray.py'),'exec'))
