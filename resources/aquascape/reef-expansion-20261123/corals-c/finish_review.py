"""Link native six-view review evidence and produce the Batch C candidate catalog."""
import json
from pathlib import Path

from PIL import Image, ImageDraw

folder = Path(__file__).resolve().parent
root = folder.parents[3]
work = root / "work/reef-expansion-20261123/corals-c"
profile = json.loads((folder / "profile.json").read_text())
notes = {
    "reef_staghorn_coral": "金棕分枝和淡轴端，俯视有实际前后分叉。低面枝尖与原画圆钝程度有差，分枝未逐节复刻。",
    "reef_tube_sponge": "可见四个不同高低、倾向的空腔；色层移除原画大尺度腔影，底座当前比原画更整齐。",
    "reef_elkhorn_coral": "顶视各主桨分开，局部沿两翼与分叉铺开。边缘低面，细小扇缺只保留在颜色。",
    "reef_brain_coral": "岩栖圆丘及表面脑纹明确。从俯视可见少量较利的基面沟边，细密蜿纹以颜色为主。",
    "reef_table_coral": "短柄托开有厚度的伞盘，下方保有留白，稀疏冠凸和冠纹各有对应。细枝进材质。",
    "reef_finger_coral": "数列粗短指型柱轮廓前后交错，顶端封实。细杯纹与宽窄阴影来自六面取色。",
    "reef_knob_coral": "真实团块与低鞍；珊瑚杯和部分阴影进入材质。多峰低面，以较大的凸凹为主。",
    "reef_foliose_coral": "真薄片与错高向外展开，局部小搭桥空隙是多片在共根位置的并壳结果。",
    "reef_scroll_coral": "内外卷片与两层开缘可见，夹层有真负空间。卷缘和底座偏几何化。",
    "reef_crust_coral": "低趴附着层与小弧褶；俯视局部面片的颜色转向较明显。",
    "reef_sea_fan": "曲扇弧度、主脉、基部及贯通网孔均由网格形成。细密分网简化为较大孔和较粗连接。",
    "reef_rope_octocoral": "多根独立柔性枝、共根和少量分叉，能从两侧透视；尖端和折点保留低面形。",
    "reef_leather_octocoral": "冠柄、浅冠褶和上方珊瑚虫纹，冠下实面从中柄渐展。仅静态阶段审查。",
    "reef_barrel_sponge": "单一波纹口沿、纵向外沟、实厚壁与不贯通的深腔。方向性大阴影削弱，由几何承担。",
}
rows=[]
for key,*_ in profile:
    directory=folder/"candidates"/key
    files=directory/"catalog-entry.json"
    if not files.exists():
        continue
    row=json.loads(files.read_text())
    report_path=directory/"validation.json"
    validation=json.loads(report_path.read_text())
    frames=["angle","front","right","rear","left","top","bottom","oblique"]
    cellw,cellh=185,172
    evidence=Image.new("RGB",(cellw*len(frames),2*cellh+38),(44,60,66))
    draw=ImageDraw.Draw(evidence)
    draw.text((12,10),f"{key}  |  {row['triangles']} tris  |  Godot 4.7.1 native cold GLB",fill=(235,242,241))
    for j in range(2):
        kind="material" if j==0 else "gray"
        for i,angle in enumerate(frames):
            path=work/"captures"/f"{key}-{kind}-{angle}.png"
            image=Image.open(path).convert("RGB")
            image.thumbnail((cellw,cellh-22), Image.Resampling.LANCZOS)
            x,y=i*cellw+((cellw-image.width)//2), j*cellh+38
            evidence.paste(image,(x,y+14))
            draw.text((i*cellw+8,y),f"{kind} / {angle}",fill=(235,242,241))
    path=directory/"godot-native-review.jpg"
    evidence.save(path,quality=92, optimize=True)
    row["native_review"]=str(path)
    rows.append(row)
    validation["native_review"]={"file":path.name,"engine":"Godot 4.7.1 stable, macOS Compatibility", "rendered_views":frames,
                                 "mode":"fresh-process direct GLB, gray and material under the same lights",
                                 "verified_texture_filter":"nearest","observations":notes[key],"user_acceptance":"pending"}
    validation["current_status"]="static_candidate_for_user_review"
    if row["category"]=="octocoral":
        validation["motion"]={"status":"not_in_this_review","conditions":"各件柔性组织、根部锚定及在展缸内的实际水流单独核对。"}
    report_path.write_text(json.dumps(validation,ensure_ascii=False,indent=2)+"\n")
out=folder/"candidate-catalog.json"
out.write_text(json.dumps({"schema_version":1,"scope":"reef-expansion C static candidate assets", "assets":rows},ensure_ascii=False,indent=2)+"\n")
print(f"{len(rows)} published candidates in {out}")
