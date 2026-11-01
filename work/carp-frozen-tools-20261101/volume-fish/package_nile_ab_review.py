"""Review figures/video from actual cold renders; no asset texture alterations."""
import json,hashlib,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
repo=Path(__file__).resolve().parents[3]
out=repo/'projects/fishing-2d/experiments/nile-dorsal-route-trial/round4-ab-textured'
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def figure(names,path):
    canvas=Image.new('RGB',(1800,len(names)*660),(28,38,45));draw=ImageDraw.Draw(canvas)
    for row,name in enumerate(names):
        for col,route in enumerate(['A','B']):
            im=Image.open(out/f'{route}-artifacts/review/{name}.png').convert('RGB')
            canvas.paste(im,(col*900,row*660+40))
            draw.text((col*900+20,row*660+7),f'{route} / {1492 if route=="A" else 1458} triangles / {name}',font=font,fill='white')
    canvas.save(out/path,quality=94)
figure(['side-texture','oblique-texture'],'comparison-texture.jpg')
figure(['side-clay','front-clay','top-clay'],'comparison-clay.jpg')
figure(['front-texture','back-side-texture','top-texture'],'comparison-other-views.jpg')
# Explicit diagram of saved control coordinates over the body-only donor.
control=json.loads((out/'B-artifacts/control-cage.validation.json').read_text())
im=Image.open(out/'shared/body-side.png').convert('RGBA');canvas=Image.new('RGBA',im.size,(35,49,58,255));canvas.alpha_composite(im);draw=ImageDraw.Draw(canvas)
def xy(v):return ((v[0]+.5)*1961,972*.5-v[2]*1961)
radial=control['radial'];verts=control['vertices']
for ring in range(control['rings']):
    draw.line([xy(verts[ring*radial+j]) for j in range(radial)]+[xy(verts[ring*radial])],fill=(70,230,255,140),width=2)
for j in range(radial):draw.line([xy(verts[i*radial+j]) for i in range(control['rings'])],fill=(255,190,45,180),width=2)
draw.text((25,25),'B: saved 25 x 16 control cage / body first / fins excluded',font=font,fill='white')
canvas.convert('RGB').save(out/'B-control-cage.jpg',quality=94)

frames=json.loads((out/'movie-frames.validation.json').read_text(encoding='utf8'))
label_dir=out/'movie-labeled';label_dir.mkdir(exist_ok=True)
for index,row in enumerate(frames['frames']):
    image=Image.open(row['path']).convert('RGB');draw=ImageDraw.Draw(image)
    draw.text((20,2),f'A / 1492 triangles / {row["mode"]}',font=font,fill='white')
    draw.text((920,2),f'B / 1458 triangles / {row["mode"]}',font=font,fill='white')
    image.save(label_dir/f'frame-{index:04d}.jpg',quality=94)
ffmpeg=Path('C:/Users/admin/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin/ffmpeg.exe')
run=subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-y','-framerate','15','-i',str(label_dir/'frame-%04d.jpg'),'-c:v','libx264','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'comparison-motion.mp4')],capture_output=True,text=True)
assert run.returncode==0,run.stderr
print(json.dumps({'ok':True,'video':str(out/'comparison-motion.mp4'),'video_sha256':sha(out/'comparison-motion.mp4'),'frames':len(frames['frames'])}))
