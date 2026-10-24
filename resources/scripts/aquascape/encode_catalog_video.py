"""Encode genuine Godot captures, leaving source images and textures untouched."""
import argparse,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);a=p.parse_args()
ffmpeg=shutil.which('ffmpeg')
if not ffmpeg:raise SystemExit('ffmpeg missing')
for folder,name in [('frames','plants-overview'),('detail-frames','vallisneria-current')]:
    subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-framerate','12','-i',str(a.input/folder/'frame%04d.png'),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(a.input/(name+'.mp4'))],check=True)
subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(a.input/'vallisneria-current.mp4'),'-filter_complex','[0:v]crop=1000:680:100:110,scale=800:-1:flags=neighbor,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=none','-loop','0',str(a.input/'vallisneria-current.gif')],check=True)
print('Encoded native ten-second loops: overview MP4, detail MP4 and detail GIF.')
