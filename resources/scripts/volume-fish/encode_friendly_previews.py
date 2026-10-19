"""Package actual GPU frames into individual, full comparison and quick gallery movies."""
import argparse, hashlib, json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--captures',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--ffmpeg',required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(a.config.read_text());movies=[];rows=[]
    for k in cfg['species']:
        source=a.captures/k;report=json.loads((source/'presentation.validation.json').read_text());assert report['ok'] and len(report['records'])==2
        for variant in ['before','after']:assert len(list((source/variant/'frames').glob('frame-*.png')))==192
        target=a.output/f'083-{k}-comparison.mp4';cmd=[a.ffmpeg,'-y','-threads','2','-framerate','12','-i',str(source/'before/frames/frame-%04d.png'),'-framerate','12','-i',str(source/'after/frames/frame-%04d.png'),'-filter_complex','[0:v][1:v]vstack=inputs=2[v]','-map','[v]','-c:v','libx264','-threads','2','-pix_fmt','yuv420p','-crf','19',str(target)]
        subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);movies.append(target.resolve());rows.append({'species':k,'name':cfg['profiles'][k]['name'],'path':str(target),'seconds':16,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()});print('ENCODE_DONE',k,flush=True)
    listing=a.output/'083-comparison.concat.txt';listing.write_text(''.join("file '"+str(f).replace("'","'\\''")+"'\n" for f in movies))
    combined=a.output/'083-all-ten-comparison.mp4';subprocess.run([a.ffmpeg,'-y','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(combined)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    grid=a.output/'083-all-ten-friendly.mp4';cmd=[a.ffmpeg,'-y']
    for movie in movies:cmd+=['-i',str(movie)]
    filters=[f'[{i}:v]crop=1280:378:0:378,scale=640:189:flags=neighbor[v{i}]' for i in range(len(movies))]
    layout='|'.join(f'{(i%2)*640}_{(i//2)*189}' for i in range(len(movies)))
    filters+=[''.join(f'[v{i}]' for i in range(len(movies)))+f'xstack=inputs={len(movies)}:layout={layout}:fill=black,pad=ceil(iw/2)*2:ceil(ih/2)*2[v]']
    cmd+=['-filter_complex',';'.join(filters),'-map','[v]','-c:v','libx264','-threads','2','-pix_fmt','yuv420p','-crf','19',str(grid)]
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    # A fixed identical viewport crop only for the review board; native captures remain intact.
    board=Image.new('RGB',(1600,1450),'#18303b');draw=ImageDraw.Draw(board);font=ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',22);small=ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',16)
    for i,k in enumerate(cfg['species']):
        x=i%2*800;y=i//2*285;s=cfg['profiles'][k];draw.text((x+12,y+5),s['name']+' · 左原版 / 右轻调',font=font,fill='white')
        for j,variant in enumerate(['before','after']):
            im=Image.open(a.captures/k/variant/'neutral.png').convert('RGB').crop((320,30,960,355));im=im.resize((400,203),Image.Resampling.NEAREST);board.paste(im,(x+j*400,y+38))
        draw.text((x+12,y+246),s['intent'],font=small,fill='#c6d5da')
    draw.text((12,1428),'同姿态、同镜头、同灯光；只在此总览图统一裁切显示；原始截图与完整动作视频保留。',font=small,fill='#c6d5da');poster=a.output/'083-ten-friendly-before-after.jpg';board.save(poster,quality=95)
    report={'schema_version':1,'command':'volume.friendly-preview-media','ok':True,'status':'done','next_action':'human_review','individual':rows,'comparison_movie':str(combined),'gallery_movie':str(grid),'poster':str(poster),'scope':'Actual engine renders, no generated or repainted source images. 16s per fish; quick gallery is2cols/5rows, full comparison160s. Individual comparison preserves both full viewport halves; quick gallery extracts only the after half and scales it uniformly to half size. Contact sheet has an additional fixed central crop.'};(a.output/'083-media.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
