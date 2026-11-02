"""Compare reconstructed formulas with extracted ARM64 instructions in Unicorn.

Only the named math functions/windows execute. Unity static zero/initialization
data are supplied as fixtures; the Android application is never launched.
"""
from pathlib import Path
import hashlib, json, math, random, struct, sys
REPO = next(parent for parent in Path(__file__).resolve().parents if (parent / 'cli/gamefactory.py').is_file())
W = REPO / 'work/fish-motion-reconstruction-20261102'
sys.path.insert(0, str(W / 'deps'))
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_MEM_READ
from unicorn.arm64_const import *
from elftools.elf.elffile import ELFFile

native = W / 'libil2cpp.so'
raw = native.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '83ea8e5b7a353991f3ca10d0a3e16cfa9f734273e7e35596b5901a2b4b79757f', 'Wrong native version'
uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
with native.open('rb') as stream:
    elf = ELFFile(stream)
    segments = [seg for seg in elf.iter_segments() if seg['p_type'] == 'PT_LOAD']
    end = max(seg['p_vaddr'] + seg['p_memsz'] for seg in segments)
    uc.mem_map(0, (end + 0xfff) & ~0xfff)
    for seg in segments:
        uc.mem_write(seg['p_vaddr'], seg.data())
uc.mem_map(0x50000000, 0x100000)
uc.mem_map(0x60000000, 0x20000)
STOP = 0x500ff000
SREGS = [UC_ARM64_REG_S0 + i for i in range(32)]

def f32(value): return struct.unpack('<f', struct.pack('<f', value))[0]
def sf(index, value): uc.reg_write(SREGS[index], struct.unpack('<I', struct.pack('<f', value))[0])
def rf(index): return struct.unpack('<f', struct.pack('<I', uc.reg_read(SREGS[index])))[0]
def ptr(address, value): uc.mem_write(address, struct.pack('<Q', value))
def floats(address, values): uc.mem_write(address, struct.pack('<' + 'f' * len(values), *values))
def run(start, stop=STOP):
    uc.reg_write(UC_ARM64_REG_X30, STOP)
    uc.emu_start(start, stop, count=4000)
    assert uc.reg_read(UC_ARM64_REG_PC) == stop
def near(a, b):
    return all((math.isnan(x) and math.isnan(y)) or abs(x-y) <= 2e-5 * max(1, abs(y)) for x,y in zip(a,b))

# Fixtures for inlined Vector3.Normalize and Vector3.zero accesses in Flee.
uc.mem_write(0x3ed3b61, b'\x01')
uc.mem_write(0x3ed1995, b'\x01')
ptr(0x3bf8c80, 0x50002000)
ptr(0x50002000, 0x50002100)
uc.mem_write(0x50002100 + 0xe0, struct.pack('<I', 1))
ptr(0x3bf7380, 0x50003000)
ptr(0x50003000, 0x50003100)
ptr(0x50003100 + 0xb8, 0x50004000)
floats(0x50004000, [0,0,0,0,0,0,0,1,0])
ptr(0x3c2c720, 0x50005000)
ptr(0x50005000, 0x50006000)
uc.reg_write(UC_ARM64_REG_SP, 0x60010000)
def reject_null_fixture_read(uc, access, address, size, value, user_data):
    raise AssertionError('Unexpected null/low-pointer fixture read at ' + hex(address) + ' PC=' + hex(uc.reg_read(UC_ARM64_REG_PC)))
uc.hook_add(UC_HOOK_MEM_READ, reject_null_fixture_read, begin=0, end=0xfff)

rng = random.Random(20261102)
tests = []
for i in range(110):
    diff = tuple(f32(rng.uniform(-10,10)) for _ in range(3)) if i else (0.0,0.0,0.0)
    length = f32(math.sqrt(sum(x*x for x in diff)))
    radius = f32(rng.uniform(0.1,20))
    for j,v in enumerate((*diff,length,radius)): sf(j,v)
    run(0x207ee1c)
    actual = [rf(j) for j in range(3)]
    expected = [float('nan')]*3 if length == 0 else [x * min(1,max(0,1-length/radius)) / length for x in diff]
    tests.append({'kernel':'separation','case':i,'ok':near(actual,expected),'actual':actual,'expected':expected})

for i in range(110):
    pos = tuple(f32(rng.uniform(-4,4)) for _ in range(3)); evade = pos if i == 0 else tuple(f32(rng.uniform(-4,4)) for _ in range(3))
    vel = tuple(f32(rng.uniform(-1,1)) for _ in range(3)); speed = f32(rng.uniform(0.1,5))
    floats(0x50001000, (*pos,*vel,speed))
    uc.reg_write(UC_ARM64_REG_X0,0x50000000);uc.reg_write(UC_ARM64_REG_X1,0x50001000)
    for j,v in enumerate(evade): sf(j,v)
    run(0x207de90)
    actual = [rf(j) for j in range(3)]; diff=[x-y for x,y in zip(pos,evade)]; length=math.sqrt(sum(x*x for x in diff))
    expected=[-v for v in vel] if length<=1e-5 else [d/length*speed-v for d,v in zip(diff,vel)]
    tests.append({'kernel':'flee','case':i,'ok':near(actual,expected),'actual':actual,'expected':expected})

for i in range(110):
    def unit():
        a=[rng.uniform(-1,1) for _ in range(3)];n=math.sqrt(sum(x*x for x in a));return [f32(x/n) for x in a]
    current,desired=unit(),unit();pos=[f32(rng.uniform(-3,3)) for _ in range(3)];speed=f32(rng.uniform(.1,5));dt=f32(rng.uniform(.001,.1));rot=f32(rng.uniform(.1,6));factor=f32(math.exp(-dt*rot))
    if i==0:current=[1,0,0];desired=[-1,0,0];factor=.5
    sp=0x60010000;uc.reg_write(UC_ARM64_REG_SP,sp)
    uc.reg_write(UC_ARM64_REG_X27,0x50010000);uc.reg_write(UC_ARM64_REG_X19,0x50011000);uc.reg_write(UC_ARM64_REG_X0,0x50012000);uc.reg_write(UC_ARM64_REG_X25,sp+0xe9)
    floats(0x50010000+0x78,[dt]);floats(sp+0x7c,[speed,rot,pos[0]])
    sf(0,current[2]);sf(1,current[1]);sf(2,current[0]);sf(3,dt);sf(8,factor);sf(9,desired[0]);sf(10,desired[1]);sf(12,desired[2]);sf(11,pos[2]);sf(15,pos[1])
    run(0x207eb80,0x207ec08)
    actual_pos=struct.unpack('<3f',uc.mem_read(sp+0xc0,12));actual_dir=struct.unpack('<3f',uc.mem_read(sp+0xcc,12))
    expected_dir=[d+factor*(c-d) for c,d in zip(current,desired)];expected_pos=[p+d*speed*dt for p,d in zip(pos,expected_dir)]
    tests.append({'kernel':'turn_and_integrate','case':i,'ok':near(actual_pos,expected_pos) and near(actual_dir,expected_dir),'actual':list(actual_pos)+list(actual_dir),'expected':expected_pos+expected_dir})

failed=[x for x in tests if not x['ok']]
report={'schema_version':1,'native_sha256':hashlib.sha256(raw).hexdigest(),'engine':'Unicorn ARM64; pure math functions/window only, Unity data fixtures','tests':len(tests),'passed':len(tests)-len(failed),'failures':failed,'cases':tests,'limitations':['No Android/game runtime playback','Full steering loop and managed Unity calls not executed','No proof of production fish-size clearance, collision continuity or FPS'],'edge_cases':['Original zero-distance separation produces NaN','Opposite current/desired headings with factor 0.5 produce zero interpolated direction, reducing translation to zero for that step']}
def json_safe(value):
    if isinstance(value, float) and not math.isfinite(value): return str(value)
    if isinstance(value, list): return [json_safe(x) for x in value]
    if isinstance(value, dict): return {k:json_safe(v) for k,v in value.items()}
    return value
(W/'native-kernel-verification.json').write_text(json.dumps(json_safe(report),indent=2,allow_nan=False)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
assert not failed
