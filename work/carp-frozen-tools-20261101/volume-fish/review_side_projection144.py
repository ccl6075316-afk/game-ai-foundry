"""Capture and publish an unchanged installed fish inventory against native art."""
import argparse, hashlib, io, json, math, re, shutil, struct, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf8'))
def write(p, data): p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
def embedded(p):
    data=p.read_bytes(); size=struct.unpack_from('<I',data,12)[0]; doc=json.loads(data[20:20+size]); start=28+size
    for image in doc['images']:
        view=doc['bufferViews'][image['bufferView']]; raw=data[start+view.get('byteOffset',0):start+view.get('byteOffset',0)+view['byteLength']]
        yield image.get('name',''), raw

ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,required=True); ap.add_argument('--godot',required=True); ap.add_argument('--json',action='store_true');args=ap.parse_args()
root=args.root.resolve(); game=root/'projects/fishing-2d/game'; scripts=root/'resources/scripts/volume-fish'; base=root/'projects/fishing-2d/experiments/blender-fish'; out=base/'side-projection-144';out.mkdir(exist_ok=True)
hall=(game/'scripts/aquarium/VolumeFishExhibit.gd').read_text(encoding='utf8')
species=json.loads(re.search(r'const SPECIES := (\[.*?\])',hall).group(1)); labels=json.loads(re.search(r'const LABELS := (\{.*?\})',hall).group(1))
prior={r['species']:r for r in read(base/'fin-rollout-143/scope.validation.json')['records']}
# Every source is matched to an original embedded image by decoded native RGBA.
rows=[]
for s in species:
    folder=out/s;folder.mkdir(exist_ok=True);model=game/'assets/models/fish'/f'{s}.glb'; images=list(embedded(model))
    if s in prior:
        ref=prior[s]; original=Image.open(ref['source']).convert('RGBA'); assert sha(ref['source'])==ref['source_sha256']
        matches=[(name,raw) for name,raw in images if (lambda im:im.size==original.size and im.tobytes()==original.tobytes())(Image.open(io.BytesIO(raw)).convert('RGBA'))]
        assert matches,('Source not in installed model',s); name,raw=matches[0]
    else:
        choices=[(name,raw)for name,raw in images if '_side' in name]; assert len(choices)==1,s;name,raw=choices[0]
    source=folder/'source-original.png';source.write_bytes(raw);im=Image.open(source).convert('RGBA');pad=[math.ceil(im.width*.15),math.ceil(im.height*.15)]
    row={'species':s,'name':labels[s],'source':str(source),'source_sha256':sha(source),'source_embedded_name':name,'model_sha256':sha(model),'padding':pad,'source_size':list(im.size)}
    if s in prior and 'pixel_mapping'in prior[s]:row['pixel_mapping']=prior[s]['pixel_mapping']
    rows.append(row)
scope=out/'scope.validation.json';write(scope,{'ok':True,'records':rows,'audit_species':species,'scope':'All installed exhibit fish; original native embedded side images, including three hammerheads. No asset repair.'})
watched=[*game.glob('assets/models/fish/**/*.glb'),*game.glob('assets/models/fish/**/*.res'),*game.glob('assets/models/fish/**/*.json'),*game.glob('scripts/aquarium/**/*.gd'),*game.glob('scripts/aquarium/**/*.gdshader'),*game.glob('scripts/aquarium/**/*.gdshaderinc')]
bindings={str(p.relative_to(game)):sha(p) for p in watched};write(out/'inputs.validation.json',{'ok':True,'files':bindings})
with(out/'capture.log').open('w',encoding='utf8')as log:
    proc=subprocess.run([args.godot,'--path',str(game),'--rendering-method','gl_compatibility','--position','-3000,-3000','--script',str(scripts/'capture_side_projection144.gd'),'--',str(out),str(scope)],stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
assert proc.returncode==0,(out/'capture.log').read_text(encoding='utf8')[-3000:]
assert 'ERROR:'not in(out/'capture.log').read_text(encoding='utf8'),(out/'capture.log')
report=read(out/'capture.validation.json');assert report['ok'] and len(report['records'])==25
for rel,h in bindings.items():assert sha(game/rel)==h,('Game changed',rel)
bg=(25,48,60);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
def fit(canvas,im,box):
    im=im.convert('RGB');im.thumbnail((box[2],box[3]),Image.Resampling.NEAREST);canvas.paste(im,(box[0]+(box[2]-im.width)//2,box[1]+(box[3]-im.height)//2))
for r,c in zip(rows,report['records']):
    assert r['species']==c['species'];s=r['species'];f=out/s;im=Image.open(f/'source-original.png').convert('RGBA');pad=r['padding'];source=Image.new('RGB',tuple(c['canvas']),bg);source.paste(im,pad,im);source.save(f/'source-canvas.png')
    for mode in ['texture','albedo']:
        p=f/f'side-{mode}.png';assert sha(p)==c['images'][mode]['sha256'];assert Image.open(p).size==source.size
    sheet=Image.new('RGB',(1800,520),bg);draw=ImageDraw.Draw(sheet)
    for j,(label,name)in enumerate([('原始材质','source-canvas'),('当前游戏 · 侧面正交投影','side-texture'),('当前模型 · 无光照原色','side-albedo')]):
        draw.text((j*600+15,10),r['name']+' · '+label,font=small,fill='white');fit(sheet,Image.open(f/(name+'.png')),(j*600+5,45,590,465))
    sheet.save(f/'comparison.png')
for start in range(0,25,5):
    sheet=Image.new('RGB',(1800,5*520),bg)
    for j,r in enumerate(rows[start:start+5]):
        im=Image.open(out/r['species']/'comparison.png');sheet.paste(im,(0,j*520))
    sheet.save(out/f'overview-{start//5+1:02}.png')
web=base/'fish-quality-138';prefix='side-projection144/'
for row in rows:
    target=web/'side-projection144'/row['species'];target.mkdir(parents=True,exist_ok=True)
    for name in ['source-canvas.png','side-texture.png','side-albedo.png']:shutil.copy2(out/row['species']/name,target/name)
for p in out.glob('overview-*.png'):shutil.copy2(p,web/'side-projection144'/p.name)
data=[{'species':r['species'],'name':r['name'],'source_size':r['source_size'],'model_sha256':r['model_sha256']}for r in rows]
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>全部25条鱼 · 侧面投影与原材质</title>
<style>body{margin:0;background:#102832;color:#e3edf0;font:16px system-ui}header{padding:24px;background:#1b3945}h1{font-size:25px;margin:0 0 12px}p{line-height:1.7;margin:8px 0}.controls{position:sticky;top:0;z-index:2;padding:16px 24px;background:#102832;display:flex;gap:12px;flex-wrap:wrap;align-items:center}button,select{background:#294c5b;color:white;border:1px solid #57717d;border-radius:5px;padding:10px;font:inherit}main{padding:0 24px 30px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}figure{margin:0;background:#19303c;border:1px solid #36535e;border-radius:6px;overflow:hidden}figcaption{background:#294653;padding:12px;font-weight:600}figure img{display:block;width:100%;image-rendering:pixelated}a{color:#9fdfef}.overlay{position:relative;background:#19303c}.overlay img{width:100%;display:block;image-rendering:pixelated}.overlay .model{position:absolute;inset:0;opacity:.5}details{margin:22px 0}summary{cursor:pointer;padding:12px;background:#213d49}#all img{width:100%;image-rendering:pixelated}input{vertical-align:middle;width:250px}.note{color:#afc7d0;font-size:14px}h2{font-size:20px}@media(max-width:900px){.grid{grid-template-columns:1fr}}@media print{.controls,.overlay,details{display:none}.grid{grid-template-columns:repeat(3,1fr)}} </style>
<header><h1>全部25条鱼 · 当前侧面投影与原材质</h1><p>左：原始侧面材质图　中：当前游戏模型的侧面正交投影　右：同一模型去除光照后的原色投影。</p><p class="note">同一原生像素坐标、同一画布和共同留白，无局部配准或独立拉伸。模型为原生静止姿态；源图嘴部开度、折叠鳍与三维鳍的展开角度可能不同。此页用于对照，不代表新一轮形态验收。</p></header>
<div class="controls"><button id="prev">上一条</button><select id="fish" aria-label="选择鱼"></select><button id="next">下一条</button><span id="count"></span><a href="#all">25条总览</a></div>
<main><h2 id="name"></h2><div class="grid"><figure><figcaption>原始材质</figcaption><a id="sourceLink" target="_blank"><img id="source" alt="原始侧面材质"></a></figure><figure><figcaption>当前游戏 · 侧面正交投影</figcaption><a id="textureLink" target="_blank"><img id="texture" alt="当前游戏侧面正交投影"></a></figure><figure><figcaption>当前模型 · 无光照原色</figcaption><a id="albedoLink" target="_blank"><img id="albedo" alt="当前模型无光照侧面投影"></a></figure></div><p class="note" id="meta"></p><details open><summary>同坐标叠加对照</summary><p>模型不透明度 <input id="opacity" aria-label="模型不透明度" type="range" min="0" max="100" value="50"><span id="percent">50%</span>（0%为原图，100%为模型原色）</p><div class="overlay"><img id="overlaySource" alt="叠加底图：原材质"><img id="overlayModel" class="model" alt="叠加上层：模型原色"></div></details><details id="all"><summary>全部25条 · 五张总览图（点击打开原尺寸）</summary>OVERVIEWS</details><p class="note">本页由当前正式游戏直接渲染；源图与模型、运行时文件均记录哈希，制作过程中未修改游戏资产。</p></main>
<script>const rows=DATA,prefix=PREFIX;const fish=document.querySelector('#fish');rows.forEach(r=>fish.add(new Option(r.name,r.species)));function show(s){let i=rows.findIndex(r=>r.species===s);if(i<0)i=0;let r=rows[i];fish.value=r.species;document.querySelector('#name').textContent=r.name;document.querySelector('#count').textContent=`${i+1} / ${rows.length}`;for(const[k,n]of Object.entries({source:'source-canvas',texture:'side-texture',albedo:'side-albedo',overlaySource:'source-canvas',overlayModel:'side-albedo'})){let p=prefix+r.species+'/'+n+'.png';document.querySelector('#'+k).src=p;const a=document.querySelector('#'+k+'Link');if(a)a.href=p;}document.querySelector('#meta').textContent=`原图 ${r.source_size.join(' × ')} 像素 · 原生静止姿态 · 点击图片查看原尺寸`;history.replaceState(null,'','?fish='+r.species);}fish.onchange=()=>show(fish.value);document.querySelector('#prev').onclick=()=>show(rows[(fish.selectedIndex+24)%25].species);document.querySelector('#next').onclick=()=>show(rows[(fish.selectedIndex+1)%25].species);document.querySelector('#opacity').oninput=e=>{document.querySelector('#overlayModel').style.opacity=e.target.value/100;document.querySelector('#percent').textContent=e.target.value+'%';};show(new URLSearchParams(location.search).get('fish'));</script></html>'''
html=html.replace('OVERVIEWS',''.join(f'<a href="{prefix}overview-{i:02}.png" target="_blank"><img loading="lazy" alt="总览 {i}，每张5条鱼" src="{prefix}overview-{i:02}.png"></a>'for i in range(1,6))).replace('DATA',json.dumps(data,ensure_ascii=False)).replace('PREFIX',json.dumps(prefix))
page=web/'side-projection144.html';page.write_text(html,encoding='utf8')
files=[p for p in out.rglob('*.png')]+[page,scope,out/'capture.validation.json',out/'inputs.validation.json']
write(out/'completion.validation.json',{'ok':True,'status':'done','next_action':'human_review','species_count':25,'game_unchanged':True,'records':rows,'files':{str(p):sha(p)for p in files},'url':'http://127.0.0.1:8768/side-projection144.html','scope':'Side orthographic/source comparison only; no model changes or new acceptance.'})
print(json.dumps({'ok':True,'status':'done','next_action':'human_review','species_count':25,'url':'http://127.0.0.1:8768/side-projection144.html'},ensure_ascii=False))
