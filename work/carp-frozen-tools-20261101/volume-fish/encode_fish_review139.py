"""Encode actual480-frame game orbits and verify the resulting20-second videos."""
import argparse,concurrent.futures,hashlib,json,shutil,subprocess,sys
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture',type=Path,required=True);p.add_argument('--game',type=Path,required=True);a=p.parse_args();d=json.loads(a.capture.read_text());assert d['ok']
    assert d['config_sha256']==sha(a.game/'assets/models/fish/motion/mouth-repair139.json')
    log=a.capture.parent.with_suffix('.stderr.log');assert log.exists() and 'ERROR:' not in log.read_text(encoding='utf8'),'Capture engine errors'
    for path,h in d['runtime_dependencies'].items():assert sha(a.game/path)==h
    ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe');assert ffmpeg and ffprobe
    def encode(row):
        s=row['species'];folder=a.capture.parent/s;frames=folder/'video-frames';assert {p.name for p in frames.glob('frame-*.png')}=={f'frame-{i:04d}.png' for i in range(480)}
        for sample in row['video']['samples']:assert sha(sample['file'])==sample['sha256']
        out=folder/'orbit-actions.mp4';run=subprocess.run([ffmpeg,'-y','-hide_banner','-loglevel','error','-framerate','24','-i',str(frames/'frame-%04d.png'),'-frames:v','480','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],capture_output=True,text=True,timeout=120);assert run.returncode==0,run.stderr
        probe=subprocess.run([ffprobe,'-v','error','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,nb_frames,duration','-of','json',str(out)],capture_output=True,text=True,timeout=30);stream=json.loads(probe.stdout)['streams'][0];assert stream['r_frame_rate']=='24/1' and int(stream['nb_frames'])==480 and abs(float(stream['duration'])-20)<.001 and (stream['width'],stream['height'])==(600,400)
        result={'species':s,'ok':True,'video':str(out),'sha256':sha(out),'stream':stream,'source_capture_sha256':sha(a.capture)};print('FISH_VIDEO139',s,flush=True);return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(encode,d['rows']))
    result={'ok':len(rows)==len(d['rows']),'records':rows,'capture_sha256':sha(a.capture),'scope':'20seconds,480 actual engine-rendered frames at24fps; no generated motion or interpolated frames. Visual review remains necessary.'};(a.capture.parent/'video.validation.json').write_text(json.dumps(result,indent=2));return 0
if __name__=='__main__':sys.exit(main())
