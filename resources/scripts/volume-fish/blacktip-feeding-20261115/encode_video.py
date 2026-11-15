from pathlib import Path
import subprocess,json,hashlib
W=Path(__file__).resolve().parent
capture=json.loads((W/'godot/capture.validation.json').read_text())
assert capture['model_sha256']==hashlib.sha256((W.parent/'r2/fish.glb').read_bytes()).hexdigest()
labels=['黑鳍礁鲨 R5 · 整身带动撕咬 / 正常速度','斜前方 · 半速回放','整鱼俯视 · 半速观察躯干与尾部'];font='C\\:/Windows/Fonts/msyh.ttc'
filters=[f"[{i}:v]drawtext=fontfile='{font}':text='{label}':x=30:y=28:fontsize=27:fontcolor=white:box=1:boxcolor=black@0.38:boxborderw=10[v{i}]"for i,label in enumerate(labels)]
filters.append('[v0][v1][v2]concat=n=3:v=1:a=0[out]');args=['ffmpeg','-y','-hide_banner','-loglevel','error']
for tag in ['wide','close','front']:args+=['-framerate','24','-i',str(W/'godot'/f'{tag}-%03d.png')]
args+=['-filter_complex',';'.join(filters),'-map','[out]','-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(W/'feeding-preview.mp4')]
subprocess.run(args,check=True)
report=json.loads(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration,size:stream=width,height,nb_frames,r_frame_rate','-of','json',str(W/'feeding-preview.mp4')],check=True,capture_output=True,text=True).stdout)
report['model_sha256']=capture['model_sha256'];report['video_sha256']=hashlib.sha256((W/'feeding-preview.mp4').read_bytes()).hexdigest()
(W/'video.validation.json').write_text(json.dumps(report,indent=2))
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(W/'feeding-preview.mp4'),'-vf','fps=1,scale=426:240,tile=4x5','-frames:v','1',str(W/'video-review.jpg')],check=True)
print(json.dumps(report))
