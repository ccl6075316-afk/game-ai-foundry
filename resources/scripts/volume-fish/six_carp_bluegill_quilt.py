from pathlib import Path
p=Path(__file__).parent/'portable/six_cyprinid_quilt.py';s=p.read_text(encoding='utf8');s=s.replace("normalized=np.clip(np.rint(np.array(c['plain_RGB'])+detail*.9),0,255).astype(np.uint8)","normalized=rgb.astype(np.uint8)")
s=s.replace("f'Native ROI RGB minus Gaussian sigma{sigma} illumination plus declared target palette; residual gain0.9. Color-corrected material, not raw RGB-exact.'","'Raw original own lower-jaw ROI RGB exact; no color normalization, no resized samples.'")
s=s.replace("ROOT=Path(__file__).resolve().parents[4]","ROOT=Path(__file__).resolve().parents[3]")
exec(compile(s,str(Path(__file__).resolve()),'exec'))
