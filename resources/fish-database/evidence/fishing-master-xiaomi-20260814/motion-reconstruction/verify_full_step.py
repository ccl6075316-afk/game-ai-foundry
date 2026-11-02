"""Execute original ComputeFlockBehaviours with managed-list/expf fixtures.

This checks the reconstruction against the original native loop, not against
an invented Boids implementation. Unity rendering and actual gameplay are out
of scope. The deliberately observed order/cap quirks are retained.
"""
from pathlib import Path
import copy, json, math, random, struct
import verify_native_kernels as K
from unicorn import UC_HOOK_CODE
from unicorn.arm64_const import *

W, uc = K.W, K.uc
from reference_model import norm, reconstruct_step

cursor=0x50050000
def alloc(size):
    global cursor
    p=cursor;cursor=(cursor+size+15)&~15;assert cursor<0x500ef000
    uc.mem_write(p,b'\0'*size);return p
def u32(p,v):uc.mem_write(p,struct.pack('<I',v))
def u64(p,v):uc.mem_write(p,struct.pack('<Q',v))
def get32(p):return struct.unpack('<I',uc.mem_read(p,4))[0]
def get64(p):return struct.unpack('<Q',uc.mem_read(p,8))[0]
def make_list(elements, item_size, capacity=None):
    capacity=max(len(elements),capacity or 0);obj=alloc(0x28);array=alloc(0x20+capacity*item_size);u64(obj+0x10,array);u32(obj+0x18,len(elements));u64(array+0x18,capacity)
    for i,data in enumerate(elements):uc.mem_write(array+0x20+i*item_size,data)
    return obj
def item_pointer(obj,index,size):return get64(obj+0x10)+0x20+index*size
stats={'flee_calls':0,'stub_calls':0}
def return_stub():uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_X30))
def stub(uc,address,size,data):
    stats['stub_calls']+=1
    obj=uc.reg_read(UC_ARM64_REG_X0);index=uc.reg_read(UC_ARM64_REG_W1)
    if address==0x281fec4:
        uc.reg_write(UC_ARM64_REG_X0,get64(item_pointer(obj,index,8)))
    elif address==0x27fbf64:
        uc.mem_write(uc.reg_read(UC_ARM64_REG_X8),bytes(uc.mem_read(item_pointer(obj,index,56),56)))
    elif address==0x27fbfd4:
        uc.mem_write(item_pointer(obj,index,56),bytes(uc.mem_read(uc.reg_read(UC_ARM64_REG_X2),56)))
    elif address==0x2808134:
        uc.reg_write(UC_ARM64_REG_W0,get32(item_pointer(obj,index,4)))
    elif address==0x3a16bb0:
        K.sf(0,math.exp(K.rf(0)))
    else:raise AssertionError(hex(address))
    return_stub()
for address in (0x281fec4,0x27fbf64,0x27fbfd4,0x2808134,0x3a16bb0):
    uc.hook_add(UC_HOOK_CODE,stub,begin=address,end=address)
def count_flee(uc,address,size,data):stats['flee_calls']+=1
# Hook the call site, not Flee's already-JIT-cached entry from the kernel tests.
uc.hook_add(UC_HOOK_CODE,count_flee,begin=0x207e9ac,end=0x207e9ac)
uc.mem_write(0x3ed54f0,b'\x01');uc.mem_write(0x3ed3932,b'\x01')
for slot in (0x3c2c798,0x3c2c718,0x3bf86d8,0x3bf8258):K.ptr(slot,0x50005000)
uc.reg_write(UC_ARM64_REG_TPIDR_EL0,0x50020000);u64(0x50020028,0x12345678)

def run_original(groups,obstacles,dt,force=20.,lookahead=3,axis=0):
    global cursor
    cursor=0x50050000;stats.update(flee_calls=0,stub_calls=0);controller=alloc(0xb0);gs=[];flists=[]
    for g in groups:
        go=alloc(0xb0);uc.mem_write(go+0x25,bytes([g['controlled']]));u32(go+0x38,g['priority']);K.floats(go+0x40,[g['flee_radius'],g['neighbor'],g['neighbor']]);K.floats(go+0x94,g['anchor']);fish=[]
        for f in g['fish']:
            buf=bytearray(56);struct.pack_into('<10f',buf,0,*f['p'],*f['v'],f['speed'],f['rot'],0.,1.);buf[0x28]=f.get('controlled',True);fish.append(bytes(buf))
        fl=make_list(fish,56);u64(go+0x60,fl);flists.append(fl);gs.append(go)
    u64(controller+0x88,make_list([struct.pack('<Q',g) for g in gs],8));u64(controller+0x90,make_list([],4,512));u32(controller+0x30,axis);u32(controller+0x44,lookahead);K.floats(controller+0x48,[force]);K.floats(controller+0x78,[dt]);coll=[]
    for o in obstacles:coll.append(struct.pack('<6fi',*o['p'],*o['size'],o['type']))
    u64(controller+0x60,make_array(coll,28));u32(controller+0x68,len(coll))
    uc.reg_write(UC_ARM64_REG_X0,controller);uc.reg_write(UC_ARM64_REG_SP,0x60010000);uc.reg_write(UC_ARM64_REG_X30,K.STOP);uc.emu_start(0x207dfa8,K.STOP,count=2000000);assert uc.reg_read(UC_ARM64_REG_PC)==K.STOP
    result=copy.deepcopy(groups)
    for group,fl in zip(result,flists):
        for i,f in enumerate(group['fish']):
            values=struct.unpack('<6f',uc.mem_read(item_pointer(fl,i,56),24));f['p']=list(values[:3]);f['v']=list(values[3:])
    return result,stats.copy()
def make_array(elements,size):
    p=alloc(0x20+len(elements)*size);u64(p+0x18,len(elements))
    for i,data in enumerate(elements):uc.mem_write(p+0x20+i*size,data)
    return p

rng=random.Random(58213);cases=[]
for case in range(65):
    axis=case%3;dt=K.f32(.02);groups=[]
    for gi in range(2 if case%4 else 3):
        fish=[]
        for fi in range(2+(case%3)):
            p=[K.f32(rng.uniform(-2,2)) for _ in range(3)];v=norm([rng.uniform(-1,1) for _ in range(3)])
            if axis:p[2 if axis==1 else 1]=0.;v[2 if axis==1 else 1]=0.
            fish.append({'p':p,'v':[K.f32(x) for x in v],'speed':K.f32(rng.uniform(.5,2)),'rot':K.f32(rng.uniform(.5,4)),'controlled':True})
        groups.append({'anchor':[K.f32(3+gi),0.,1. if axis!=1 else 0.],'fish':fish,'priority':1 if gi==1 and case%2 else 0,'controlled':not (gi==1 and case%2),'neighbor':K.f32(3.),'flee_radius':K.f32(8.)})
    obstacles=[]
    if case%3==1:obstacles=[{'p':[-1.,-1.,-1.],'size':[2.,2.,2.],'type':0}]
    elif case%3==2:obstacles=[{'p':[.3,.2,.1],'size':[3.,0.,0.],'type':1},{'p':[-1.,-1.,-1.],'size':[2.,2.,2.],'type':0}]
    if case==64:
        groups=groups[:1];groups[0]['fish']*=4
        for i,f in enumerate(groups[0]['fish']):
            f=copy.deepcopy(f);f['p'][0]+=i*.07;groups[0]['fish'][i]=f
    expected,expected_flee=reconstruct_step(groups,obstacles,dt,axis=axis);actual,actual_stats=run_original(groups,obstacles,dt,axis=axis);ok=expected_flee==actual_stats['flee_calls'];max_error=0.
    for eg,ag in zip(expected,actual):
        for ef,af in zip(eg['fish'],ag['fish']):
            ok=ok and K.near(af['p']+af['v'],ef['p']+ef['v']);max_error=max(max_error,max(abs(a-b) for a,b in zip(af['p']+af['v'],ef['p']+ef['v'])))
    cases.append({'case':case,'axis':axis,'groups':len(groups),'fish':sum(len(x['fish']) for x in groups),'obstacles':len(obstacles),'ok':ok,'maximum_absolute_component_error':max_error,'expected_flee_calls':expected_flee,'native_flee_calls':actual_stats['flee_calls']})
report={'schema_version':1,'native_sha256':K.hashlib.sha256(K.raw).hexdigest(),'function_rva':'0x207dfa8','method':'Original ARM64 ComputeFlockBehaviours executed in Unicorn; only managed List<T> data-access APIs and expf stubbed; Flee executes original machine code','tests':len(cases),'passed':sum(x['ok'] for x in cases),'cases':cases,'failures':[x for x in cases if not x['ok']],'limitations':['Unity/game playback not performed','Unity scene/collider extraction and worker scheduling not emulated','Native step matched on synthetic fixtures, not live server aquarium configurations']}
(W/'full-native-step-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2));assert not report['failures']
