"""Build the freshwater plant forms from independently reviewed whole-cluster art."""

import argparse
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[4]
ART = ROOT/"resources/aquascape/reef-expansion-20261123"
WORK = ROOT/"work/reef-expansion-20261123/freshwater-e"
WORK.mkdir(parents=True,exist_ok=True)
E = ART/"freshwater-e"
D = ART/"marine-d"
sys.path.insert(0,str(D))
spec = importlib.util.spec_from_file_location("marine_build",D/"build.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
from layouts import part, blade

SOURCE = {
    "hairgrass_meadow": ("Eleocharis acicularis","https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:1169169-2/general-information","ribbon_plant","Submerged needle spikerush patch; narrow fine culms on several short, linked sand-bed runners."),
    "lake_quillwort_rosette": ("Isoetes lacustris","https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:310437-2/general-information","ribbon_plant","A single basal quill rosette and fine roots for a cool freshwater lake floor."),
    "marsilea_runner_patch": ("Marsilea hirsuta","https://tropica.com/en/inspiration/layout/Layout7/4835","broadleaf_plant","Small freshwater runner with both spatulate submerged leaves and occasional four-part leaf blades."),
    "water_lily_float_stems": (None,"https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:330032-2/general-information","broadleaf_plant","Freshwater Nymphaea growth form. Floating split pads with separate petioles and a rooted rhizome."),
    "duckweed_root_patch": ("Lemna minor","https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:526194-1/general-information","broadleaf_plant","Free-floating shallow islands of rounded fronds with single pendant roots. Game island size is enlarged."),
}
REVISED = {"lake_quillwort_rosette"}

def tube(name, track, radii, patch="root", **options):
    return part(name,track,radii,patch,sides=options.pop("sides",3),**options)

def crowns(anchors):
    result=[]
    for i, (x,y,z) in enumerate(anchors):
        turn = i*1.83+.2
        for j in [0,1]:
            delta=(math.cos(turn+j*2.6)*.045,math.sin(turn+j*2.6)*.05)
            result.append(tube(f"fine_root_{i}_{j}",[(x,y,z),(x+delta[0]*.4,y*.47,z+delta[1]*.45),
                    (x+delta[0],.006+j*.007,z+delta[1])],[.0043,.0026,.0009],sway=False))
    return result

def hairgrass(_):
    # Six clump centers read from the channels in the full top/bottom board.
    clumps=[(-.30,.095,.075),(-.16,.106,.237),(-.111,.119,-.189),(.024,.122,-.005),(.165,.11,.161),(.302,.098,-.115)]
    result=crowns([clumps[i] for i in (0,2,4)])
    heights=[[.41,.60,.69,.54,.37],[.63,.72,.63,.41],[.80,.92,.63,.55,.72],
             [.79,.89,1.,.68,.52,.74],[.57,.63,.68,.49],[.58,.74,.71,.45,.39]]
    for i,(x,y,z) in enumerate(clumps):
        for j,h in enumerate(heights[i]):
            angle=i*.74+j*2.19
            dx=math.cos(angle)
            dz=math.sin(angle)
            spread=.122+.071*(.64-.35*math.cos(j*4.2+i))
            anchor=(x+dx*.018,y,z+dz*.014)
            ax,ay,az=anchor
            arc=1.79 + .15*math.cos(j*2.4+i)
            pts=[(ax+dx*spread*t*t,ay+(h-ay)*math.sin(t*arc),az+dz*spread*1.17*t*t)
                 for t in (0.,.31,.66,1.)]
            result.append(tube(f"fine_culm_{i}_{j}",pts,[.0058,.00615,.0048,.001],"blade",
                               phase=(i*.19+j*.061)%1,point_tip=True))
    for group in [(0,1,3,4),(0,2,3,5)]:
        route=[(clumps[i][0],clumps[i][1]-.006,clumps[i][2]) for i in group]
        result.append(tube("walking_runner",route,[.008,.006,.005,.003],"runner",sway=False))
    return result

def quillwort(_):
    result=[]
    origin=(0.,.115,0.)
    tips=[(-.22,.84,-.11),(-.27,.67,.22),(-.42,.72,-.14),(-.36,.86,-.23),(-.08,.95,-.20),
          (.02,1.,.04),(.11,.90,.16),(.26,.81,-.28),(.32,.70,-.29),(.33,.74,.19),(.36,.56,.34),
          (.06,.59,.38),(-.12,.72,.38),(.04,.76,-.37),(-.29,.55,-.28),(.25,.63,.02),(-.17,.64,.06)]
    for i,(x,y,z) in enumerate(tips):
        anchor=(x*.14,origin[1]+(i%3)*.013,z*.14)
        track=[anchor,(x*.28,y*.49,z*.32),(x*.61,y*.79,z*.68),(x,y,z)]
        result.append(tube(f"quill_{i}",track,[.010,.0105,.007,.001],"blade",phase=(i*.113)%1.0))
    result+=crowns([(-.032,.125,-.04),(.03,.11,.02),(.018,.109,-.044),(-.013,.101,.07)])
    result.append(tube("basal_corm",[(.002,.035,0),(.004,.087,.006),(-.002,.149,-.004)],
                       [.025,.062,.057],"runner",sides=7,sway=False))
    return result

def oval_leaf(name,start,end,width):
    a=np.asarray(start);b=np.asarray(end)
    vector=b-a
    turn=math.degrees(math.atan2(vector[2],vector[0]))+90
    return blade(name,[tuple(a),tuple(a+.30*vector),tuple(a+.65*vector),tuple(b)],width,
                 [turn]*4,rim=[.12,.8,1,.07],sway=False)

def marsilea(_):
    joints=[(-.43,.19,.12),(-.32,.27,.06),(-.21,.23,-.11),(-.05,.29,-.09),
            (.10,.23,.065),(.24,.27,.09),(.37,.229,-.08),(.44,.22,.045)]
    leaves=[(-.43,.52,.26),(-.31,.68,-.08),(-.17,.45,-.28),(-.07,.85,-.17),
            (.09,.54,.27),(.24,.65,.18),(.43,.73,-.15),(.45,.49,.12)]
    result=crowns([joints[i] for i in [0,2,4,6,7]])
    result.append(tube("creeping_rhizome",joints,[.014,.016,.016,.013,.014,.012,.011,.008],"runner",sway=False))
    for i, (joint, tip) in enumerate(zip(joints,leaves)):
        mid=tuple(a*.53+b*.47 for a,b in zip(joint,tip))
        result.append(tube(f"petiole_{i}",[joint,(mid[0],mid[1],mid[2]-.05),tip],[.006,.005,.004],"runner",sway=False))
        if i in (3,5,6):
            angles=[.3,1.87,3.36,5.03] if i==3 else [.07,1.70,3.21,4.82]
            for k,angle in enumerate(angles):
                offset=(math.cos(angle)*.08,.095+math.sin(angle)*.034,math.sin(angle)*.10)
                end=(tip[0]+offset[0],tip[1]+offset[1],tip[2]+offset[2])
                result.append(oval_leaf(f"four_lobe_{i}_{k}",tip,end,.035 if i==3 else .032))
        else:
            end=(tip[0]+(.06 if i in [0,2] else -.015),tip[1]+.135,tip[2]+(.068 if i%2 else -.05))
            result.append(oval_leaf(f"spatulate_{i}",tip,end,.039))
    return result

def pad_outline(cx, cz, rx, rz, angle):
    path=[(0.0,0.0)]
    for i in range(15):
        t=.19+(math.tau-.39)*i/14
        x,z=rx*math.cos(t),rz*math.sin(t)
        path.append((x*math.cos(angle)-z*math.sin(angle),x*math.sin(angle)+z*math.cos(angle)))
    return [(cx+x,cz+z) for x,z in path]

def lily(_):
    result=crowns([(-.06,.076,-.055),(0,.093,.02),(.095,.068,.039)])
    result.append(tube("anchored_rhizome",[(-.146,.083,-.02),(-.02,.095,-.011),(.118,.088,.041)],
                       [.031,.047,.031],"root",sides=7,sway=False))
    pads=[(-.286,-.155,.168,.182,-.45,.982),(-.126,-.314,.174,.16,1.18,.994),
          (.127,-.26,.186,.15,-2.33,.997),(.291,-.01,.198,.181,.15,.989),
          (-.252,.183,.166,.168,1.87,.972),(.05,.284,.182,.174,3.66,.986)]
    for i,(x,z,rx,rz,angle,y) in enumerate(pads):
        start=(-.05+i*.023,.1,-.018+i*.006)
        track=[start,(x*.35,.43 if i%2 else .37,z*.37),(x*.74,y*.64,z*.76),(x,y-.002,z)]
        result.append(tube(f"floating_petiole_{i}",track,[.008,.0055,.0048,.0041],"runner",sway=False))
        outline=pad_outline(x,z,rx,rz,angle)
        rings=[(1,y-.005,0.),(1,y-.002,0.),(1,y+.002,0.),(1,y+.004,0.)]
        result.append({"kind":"bank","patch":"blade","outline":outline,"rings":rings})
    return result

def duckweed(board):
    # Leaf centers come from pigment peaks in the same top view, so detached
    # islands and density gradients survive rather than filling a rectangle.
    crop=board.crop((526,632,1010,914)).convert("RGB")
    pixels=np.asarray(crop).astype(float)
    g=pixels[:,:,1]
    mask=(g>55)&(g<235)&(g-pixels[:,:,2]>35)&(g-pixels[:,:,0]>1.8)
    mask=ndi.binary_closing(mask,iterations=2)
    dist=ndi.distance_transform_edt(mask)
    extrema=(dist==ndi.maximum_filter(dist,size=35)) & (dist>=8)
    identified=[]
    for r,c in np.argwhere(extrema):
        if any((r-pr)**2+(c-pc)**2<12**2 for pr,pc in identified):
            continue
        identified.append((int(r),int(c)))
    if len(identified)<8:
        identified=[(79,61),(105,116),(110,170),(83,188),(63,251),(119,227),(152,283),
                    (156,143),(172,197),(113,300),(105,362),(146,415),(199,354),(196,86),(73,403)]
    width,height=crop.size
    result=[]
    for i,(r,c) in enumerate(identified[:22]):
        x,z=(c/width-.5)*.87,(r/height-.5)*.93
        theta=(i*2.39)%math.tau
        direction=np.array([math.cos(theta),math.sin(theta)])
        size=.043+min(.037,dist[r,c]/width*.57)
        a=np.array([x,z])-size*.80*direction
        b=np.array([x,z])+size*.86*direction
        da=(a+b)*.5-direction*.31*size
        db=(a+b)*.5+direction*.27*size
        y=.92-(i%3)*.019
        result.append(blade(f"float_frond_{i}",[(a[0],y,a[1]),(da[0],y+.006,da[1]),(db[0],y+.008,db[1]),(b[0],y,b[1])],
                            size,[math.degrees(theta)+90]*4,rim=[.22,.96,.90,.24],sway=False))
        root_end=(x+.018*math.cos(theta),.20+(i%7)*.065,z+.012*math.sin(theta))
        result.append(tube(f"frond_root_{i}",[(x,y-.006,z),root_end],[.0024,.00065],sway=False))
    return result

LAYOUT = {
    "hairgrass_meadow":hairgrass, "lake_quillwort_rosette":quillwort,
    "marsilea_runner_patch":marsilea, "water_lily_float_stems":lily, "duckweed_root_patch":duckweed,
}

def sources_for(key,board):
    # Use complete camera regions and sample only foreground leaf/root pixels.
    # Separate foliage against brighter backing from pale anchoring structures.
    # Camera selection covers the original front/rear and both plan views.
    mode = "float" if key=="duckweed_root_patch" else "plant"
    if mode=="float":
        return {
            "blade":[[("top",536,674,596,723)], [("bottom",1132,685,1185,737)]],
            "root":[[("front",181,289,256,370)], [("right",749,276,822,393)]],
            "runner":[[("front",181,253,256,347)], [("back",1184,303,1295,356)]],
        }
    if key=="water_lily_float_stems":
        return {
            "blade":[[("top",759,662,879,783)], [("bottom",1326,660,1429,785)]],
            "root":[[("front",175,387,346,445)], [("bottom",1220,775,1355,838)]],
            "runner":[[("front",195,265,312,423)], [("back",1137,252,1330,421)]],
        }
    # A foreground swatch finder anchors the crop to each camera's own silhouette.
    panels=[("front",(7,113,506,493)),("back",(1034,115,1530,493)),
            ("top",(523,624,1014,991)),("bottom",(1034,629,1531,980))]
    swatches={}
    for target in ("blade","runner","root"):
        directions=[]
        for side,rect in (panels[2:] if target=="blade" else panels[:2]):
            x0,y0,x1,y1=rect
            data=np.asarray(board.crop(rect).convert("RGB")).astype(float)
            red,green,blue=np.moveaxis(data,-1,0)
            if target=="blade":
                weight=np.maximum(0,green-blue-15)*(green>red+2)*(green<235)
            else:
                weight=np.maximum(0,red-blue-18)*(red>green+3)*(red<218)
                cutoff=data.shape[0]*(.48 if target=="runner" else .60)
                weight[:int(cutoff)]=0
            if weight.sum()<10:
                weight=np.maximum(0,np.max(data,axis=2)-np.min(data,axis=2)-14)
                weight[:round(data.shape[0]*.48)]=0
            cy,cx=map(int,np.unravel_index(np.argmax(ndi.gaussian_filter(weight,7)),weight.shape))
            half=32 if target=="blade" else 40
            directions.append([(side,max(x0,x0+cx-half),max(y0,y0+cy-half),
                                 min(x1,x0+cx+half),min(y1,y0+cy+half))])
        swatches[target]=directions
    return swatches

def trim_paper_pixels(path,key):
    pixels=np.array(Image.open(path).convert("RGB"))
    channels=("blade","runner","root")
    for index,channel in enumerate(channels):
        for y in (0,64):
            tile=pixels[y:y+64,index*64:(index+1)*64,:]
            hi=tile.max(axis=2)
            lo=tile.min(axis=2)
            trusted=(hi<177)&(hi-lo>14)
            if channel=="blade":
                green=tile[:,:,1].astype(int)
                trusted=(green<186)&(green>=tile[:,:,0])&(green>tile[:,:,2]+12)
            if trusted.sum()<12:
                raise ValueError(f"{key} {channel}: insufficient plant pigment")
            replacement=ndi.distance_transform_edt(~trusted,return_distances=False,return_indices=True)
            tile[:]=tile[replacement[0],replacement[1]]
    Image.fromarray(pixels).save(path,optimize=True)

def main(key,blender):
    subject=json.loads((E/"subjects.json").read_text())[key]
    scientific,url,budget,desc=SOURCE[key]
    name=subject["name"]
    output=E/key
    output.mkdir(exist_ok=True)
    source_folder=ART/"sources"/("aquascape-e-"+key.replace("_","-")+("-r2" if key in REVISED else ""))
    src=source_folder/"output"/(key+"_six_views_raw.png")
    board=Image.open(src).convert("RGB")
    parts=LAYOUT[key](board)
    amplitude={"hairgrass_meadow":.045,"lake_quillwort_rosette":.033}.get(key,0.)
    layout={"notes":[desc,"Whole front profile and plan/underside root positions constrained by equal-scale six-view source."],
            "patches":["blade","runner","root"],"swatches":sources_for(key,board),
            "parts":parts,"motion":1.0 if amplitude else 0.0,"amplitude":amplitude}
    row={"id":key,"name_zh":name,"category":"plant","environment":"freshwater",
         "nominal_xyz_m":subject["dimensions_m"],"budget_type":budget,"scientific_name":scientific,
         "source_url":url,"habitat":desc,"source_board_sha256":driver.sha(src),"layout":layout}
    raw=output/(key+".glb")
    inputs=WORK/(key+"-layout.json")
    texture=WORK/(key+"-atlas.png")
    driver.dump(inputs,row)
    driver.make_atlas(board,layout,texture)
    trim_paper_pixels(texture,key)
    command=[str(blender),"-b","-t","2","--python-exit-code","19","--python",str(D/"model.py"),"--",str(inputs),str(texture),str(raw)]
    with (WORK/(key+"-blender.log")).open("w") as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    original=WORK/(key+"-raw.glb")
    raw.replace(original)
    driver.expand_blender_glb(original,raw)
    original.unlink()
    build=raw.with_suffix(".build.json")
    check=driver.validate(raw,row,json.loads(build.read_text()))
    build.unlink()
    check["source_board"]={"file":driver.relative(src),"sha256":driver.sha(src),
                          "camera_order":["front","right","back","left","top","bottom"],
                          "swatches":layout["swatches"],"art_review":"candidate reviewed by agent, user pending"}
    proof=output/"geometry-and-material.validation.json"
    driver.dump(proof,check)
    row.pop("layout")
    row.update(model=driver.relative(raw),editable_source=driver.relative(raw.with_suffix(".blend")),
               source_board=driver.relative(src),validation=driver.relative(proof),triangles=check["triangles"])
    if key=="duckweed_root_patch": row["placement_anchor"]="water_surface"
    if "rooted_current" in check: row["rooted_current"]=check["rooted_current"]
    driver.dump(output/"candidate.json",row)
    print(key,check["triangles"], flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("ids",choices=LAYOUT,nargs="+")
    p.add_argument("--blender",type=Path,required=True)
    a=p.parse_args()
    for key in a.ids:
        main(key,a.blender)
