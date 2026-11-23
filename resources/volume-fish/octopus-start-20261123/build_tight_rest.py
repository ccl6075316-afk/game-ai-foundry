"""R3 straight-rest arm controls with a <=50k full-instance trial budget."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=(ROOT/'build_gray.py').read_text()
replacements={"OUT=ROOT/'r2'":"OUT=ROOT/'motion-r3'/'rest'",'OUT.mkdir(exist_ok=True)':'OUT.mkdir(parents=True,exist_ok=True)',".024*math.sin(math.pi*1.3)-.009":".024*math.sin(math.pi*1.3)-.028",'(.018*(1-u)+.009)':'(.025*(1-u)+.028)','2800/tri':'26000/tri','sm.iterations=3':'sm.iterations=2','N=65;K=12':'N=129;K=16',"for n in range(10):":"for n in range(32):",'t=t_at_arm_fraction(i,.13+n*.082)':'t=t_at_arm_fraction(i,.14+.82*(1-(1-n/31)**1.4))',"[(cr,.018*(1-t)+.003),(cr*.48,-.001)]":"[(cr*.72,0),(cr,.021*(1-t)+.003),(cr*.48,.004*(1-t))]",'range(6)':'range(8)','math.tau/6':'math.tau/8','for l in range(1):':'for l in range(2):','base+l*6+k':'base+l*8+k','base+l*6+(k+1)%6':'base+l*8+(k+1)%8','b+6,a+6':'b+8,a+8','base+6+k':'base+16+k','seg=32,rings=20':'seg=48,rings=28'}
for a,b in replacements.items():
 assert a in source,a
 source=source.replace(a,b)
# Replace the former bent paths before the shared physical AL solver runs.
anchor='for i in range(8):\n    target=PROFILE'
straight='''for i in range(8):
    root=Vector(paths[i][0]);direction=Vector((root.x,root.y,0)).normalized()
    paths[i]=[tuple(root+direction*(3.6*k/6)) for k in range(7)]
for i in range(8):
    target=PROFILE'''
assert anchor in source;source=source.replace(anchor,straight)
# Straight radial arms share a fixed oral-down frame without a rest twist.
source=source.replace("roll=math.sin(t*math.pi*.8)*([-.25,.35,-.45,.1,-.2,.4,-.4,.2][idx])","roll=0.0")
source=source.replace("Paired_sucker_rows_160_proxy_cups","Paired_sucker_rows_512_cups")
source=source.replace("'revision':2","'revision':4")
source=source.replace('160 representative cups; not anatomical sucker count','512 simplified cups; not anatomical sucker count')
source=source.replace("def radius(t):return .137*(1-t)**1.32+.009", """def radius(t):
    def ease(x):
        x=max(0.,min(1.,x));return x*x*(3-2*x)
    return .137*(1-t)**1.32+.009+.026*ease((t-.55)/.25)*(1-ease((t-.94)/.06))
""")
exec(compile(source,str(ROOT/'build_gray.py'),'exec'))
