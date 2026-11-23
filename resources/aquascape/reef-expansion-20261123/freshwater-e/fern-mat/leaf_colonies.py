"""Build independently authored whole-plant clusters with rooted geometry and source pixels."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator
from scipy import ndimage as ndi

folder = Path(__file__).resolve().parent
root = folder.parents[4]
work = root / "work/reef-expansion-20261123/freshwater-e/fern-mat"
common = folder.parents[1] / "corals-c"
sys.path.insert(0,str(common))
from build_colonies import Glb, inspect, blender, sha, write_json, make_glb, estimate_topology
from rig_plant_current import array, read_glb
from validate_shader_shells import points as shader_pose

spp = {
    "laceleaf_rosette": {"name":"透孔莲座水草","scientific_name":"Aponogeton madagascariensis",
                         "habitat":"马达加斯加及科摩罗的沉水淡水莲座，叶柄由一个完整地下根冠生长。用于淡水中景。",
                         "source_url":"https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:82957-1",
                         "size":(.78,.72,.63),"amplitude":.061,"mask":True},
    "bolbitis_fern_clump": {"name":"沉木羽叶蕨","scientific_name":"Bolbitis heudelotii",
                           "habitat":"热带非洲溪流硬基附生蕨，沿水平根茎出叶，羽状复叶可供淡水溪景搭配。",
                           "source_url":"https://biodiversityadvisor.sanbi.org/search/detail/0c4c5fdf-7c21-4d81-a085-1204c3680c62",
                           "size":(.93,.57,.62),"amplitude":.041,"mask":False},
}
ATLAS=1024
LACE_WIDTH=132
LACE_HEIGHT=312
LACE_STRIP_GUIDES=(
    ((432,445),(463,450),(487,455),(518,461),(543,476),(552,488)),
    ((415,428),(408,406),(398,384),(388,359),(374,344),(363,335)),
    ((407,457),(403,480),(394,510),(387,540),(379,558),(369,569)),
    ((432,423),(441,404),(450,382),(454,362),(463,346),(466,339)),
)


def norm(a):
    return a / max(np.linalg.norm(a),1e-8)


def curve(values, t):
    values=np.asarray(values,dtype=float)
    fraction=np.linspace(0,1,len(values))
    return PchipInterpolator(fraction,values,axis=0)(t)


def source_strip(rgb, guide, index):
    """Straighten an intact fenestrated donor blade without antialiasing its openings."""
    h,w=rgb.shape[:2]
    prep=np.array(guide,dtype=float)*[w/900,h/600]
    t=np.linspace(0,1,LACE_HEIGHT)
    points=curve(prep,t)
    tangent=np.gradient(points,axis=0)
    side=np.column_stack([-tangent[:,1],tangent[:,0]])
    side/=np.maximum(np.linalg.norm(side,axis=1)[:,None],.001)
    # Distinct taper and bend from each source blade. Width remains large
    # enough to retain both natural blade edges and all transparent spaces.
    width=curve([10,24,34,32,21,7],t)*w/900
    width*=(1.,.90,.89,.84)[index]
    s=np.linspace(-1,1,LACE_WIDTH)
    xy=points[:,None,:]+width[:,None,None]*side[:,None,:]*s[None,:,None]
    xy=xy.round().astype(int)
    sample=rgb[np.clip(xy[...,1],0,h-1),np.clip(xy[...,0],0,w-1)]
    sample=sample.astype(np.int16)
    mask=(sample[...,1]-sample[...,2]>11)&(sample.min(2)<190)
    mask[:,0]=False
    mask[:,-1]=False
    mask=ndi.binary_opening(mask,structure=np.array([[0,1,0],[1,1,1],[0,1,0]])) | (mask & (sample.min(2)<77))
    mask[:5]=True
    mask[:5, : LACE_WIDTH//2-9]=False
    mask[:5,LACE_WIDTH//2+9:]=False
    sample[:5,:]=[78,99,36]
    result=np.empty((LACE_HEIGHT,LACE_WIDTH,4),dtype=np.uint8)
    result[:,:,:3]=sample
    result[:,:,3]=mask.astype(np.uint8)*255
    return result


def build_atlas(raw, lace):
    rgb=np.asarray(Image.open(raw).convert("RGB"),dtype=np.uint8)
    image=np.full((ATLAS,ATLAS,4),255,dtype=np.uint8)
    h,w=rgb.shape[:2]
    if lace:
        for i, guide in enumerate(LACE_STRIP_GUIDES):
            strip=source_strip(rgb,guide,i)
            x=15+(i%2)*(LACE_WIDTH+14)
            y=14+(i//2)*(LACE_HEIGHT+14)
            image[y:y+LACE_HEIGHT,x:x+LACE_WIDTH]=strip
    else:
        # Source image supplies different patches selected from the basal,
        # medial and distal areas of complete frond tissue (top and back).
        pos=((413,510),(436,438),(353,446),(461,405),(669,477),(721,428))
        for i,(u,v) in enumerate(pos):
            x,y=round(u*w/900),round(v*h/600)
            patch=rgb[y-25:y+25,x-25:x+25]
            p=patch.astype(int)
            m=(p[...,1]-p[...,2]>11)&(p.min(2)<170)
            if not m.any():
                raise ValueError(f"No fern tissue swatch {i}")
            ind=ndi.distance_transform_edt(~m,return_distances=False,return_indices=True)
            atlas_x=17+i*58
            image[32:82,atlas_x:atlas_x+50,:3]=patch[ind[0],ind[1]]
    # Sample the root pigments from the bottom view and extend them as
    # a small bounded swatch separate from foliage and its cutouts.
    u,v=((736,439) if lace else (733,456))
    x,y=round(u*w/900),round(v*h/600)
    patch=rgb[y-22:y+22,x-28:x+28]
    dark=patch.astype(int)
    good=(dark.min(2)<115)&(dark.max(2)-dark.min(2)>18)
    m=ndi.distance_transform_edt(~good,return_distances=False,return_indices=True)
    image[854:898,18:74,:3]=patch[m[0],m[1]] if good.any() else [78,67,35]
    root_rgb=image[854:898,18:74,:3].astype(float)
    image[854:898,18:74,:3]=np.clip(root_rgb*.65+[27,12,9],0,255).astype(int)
    image[912:958,18:74,:3]=np.asarray(image[854:898,18:74,:3]).mean(axis=(0,1)).astype(int)
    image[912:958,18:74,:3]=np.minimum(image[912:958,18:74,:3].astype(float)*1.33+[12,5,0],255).astype(int)
    return Image.fromarray(image,"RGBA")


class Assembly:
    def __init__(self):
        self.xyz=[]
        self.uv=[]
        self.data=[]
        self.faces=[]
        self.groups=[]

    def surface(self, xyz, uv, faces, motion, phase, anchor, kind):
        xyz=np.asarray(xyz,dtype=float)
        uv=np.asarray(uv)
        i=len(self.xyz)
        self.xyz.extend(xyz)
        self.uv.extend(uv/ATLAS)
        for weight in np.broadcast_to(motion,(len(xyz),)):
            self.data.append((weight,phase,*anchor))
        self.faces.extend(np.asarray(faces)+i)
        self.groups.append((kind, len(faces)))

    def tube(self, path, widths, sectors, swatch, motion, phase, anchor, kind):
        rings=[]
        coords=[]
        split=(swatch==0)
        for i, point in enumerate(path):
            axis=norm(np.asarray(path[min(i+1,len(path)-1)])-path[max(0,i-1)])
            helper=np.array([0,1,0] if abs(axis[1])<.78 else [0,0,1])
            u=norm(np.cross(axis,helper))
            v=np.cross(axis,u)
            for j in range(sectors):
                a=2*np.pi*j/sectors
                rings.append(point+widths[i]*(np.cos(a)*u+np.sin(a)*v))
                if swatch>=0:
                    coords.append([20+46*j/(sectors-1), (859 if split else 916)+30*i/(len(path)-1)])
                elif swatch==-1:
                    coords.append([48+12*j/(sectors-1),859+34*i/(len(path)-1)])
                else:
                    coords.append([22+100*j/(sectors-1),16+6*i/(len(path)-1)])
        faces=[]
        for i in range(len(path)-1):
            ring=i*sectors
            for j in range(sectors):
                a,b=ring+j,ring+(j+1)%sectors
                faces.extend([(a,b,b+sectors),(a,b+sectors,a+sectors)])
        for j in range(1,sectors-1):
            end=(len(path)-1)*sectors
            faces.extend([(0,j+1,j),(end,end+j,end+j+1)])
        self.surface(rings,coords,faces,np.repeat(motion,sectors),phase,anchor,kind)


def lace_shell(m, stem, midline, width, strip, phase, bend, tilt):
    lateral=norm(np.cross(np.array([0,1,0]),midline[-1]-midline[0]))
    line=norm(midline[2]-midline[0])
    lateral=norm(lateral*np.cos(tilt)+np.cross(line,lateral)*np.sin(tilt))
    normal=norm(np.cross(line,lateral))
    anchor=np.asarray(stem[0])
    sections=np.array([.025,.19,.41,.68,.91,.999])
    centers=curve(midline,sections)
    spread=curve(np.array([.091,.64,1,.78,.32,.018])*width,sections)
    xyz=[]
    uv=[]
    motion=[]
    n=len(sections)
    x=15+(strip%2)*(LACE_WIDTH+14)
    y=14+(strip//2)*(LACE_HEIGHT+14)
    for sign in (1,-1):
        for i,(p,r,t) in enumerate(zip(centers,spread,sections)):
            for s in (-1,0,1):
                q=p+s*r*lateral+(abs(s)*bend+r*.20*np.sin(t*np.pi)*s)*normal+normal*sign*.00085
                xyz.append(q)
                uv.append([x+LACE_WIDTH*(.5+.47*s),y+(LACE_HEIGHT-2)*t])
                motion.append(.29+t*.69)
    faces=[]
    for i in range(n-1):
        for j in range(2):
            a,b=3*i+j,3*(i+1)+j
            faces.extend([(a,b,a+1),(a+1,b,b+1)])
            a,b=a+n*3,b+n*3
            faces.extend([(a,a+1,b),(a+1,b+1,b)])
    edges=list(range(3))+list(range(5,3*n,3))+[3*n-2,3*n-3]+list(range(3*(n-2),0,-3))
    for a,b in zip(edges,edges[1:]+edges[:1]):
        faces.extend([(a,b,a+3*n),(a+3*n,b,b+3*n)])
    m.surface(xyz,uv,faces,motion,phase,anchor,"fenestrated_closed_blade")
    m.tube(np.array([*stem,centers[0]+.010*(centers[1]-centers[0])]),[.0085,.006,.0047],
           5,-2,[0.,.12,.30],phase,anchor,"petiole_closed_sweep")


def roots(m, root_segments, anchor):
    for a,b,c,r in root_segments:
        m.tube(np.array([a,b,c]),[r,r*.69,r*.30],4,1,[0,0,0],0,anchor,"rootlet_closed_sweep")


def lace():
    m=Assembly()
    # Matched from orthographic concept: four erect long central leaves,
    # four lower arcs with depth, and short foliage near the actual crown.
    spans=[
        ((-.102,.313,.003),(-.169,.540,-.008),(-.217,.641,.002),.062,1,.009),
        ((.079,.335,-.083),(.139,.536,-.114),(.227,.634,-.161),.062,3,-.006),
        ((-.133,.292,.054),(-.276,.377,.120),(-.388,.300,.118),.053,0,.006),
        ((.132,.273,.056),(.278,.349,.169),(.381,.237,.176),.058,0,-.004),
        ((-.079,.334,-.106),(-.127,.478,-.222),(-.182,.508,-.311),.059,2,.004),
        ((.089,.280,-.035),(.188,.414,-.105),(.294,.466,-.197),.053,3,-.006),
        ((.051,.222,.099),(.099,.333,.230),(.078,.250,.309),.047,3,.002),
        ((-.032,.192,.098),(-.130,.269,.193),(-.252,.231,.244),.049,2,-.005),
    ]
    rolls=(.48,-.34,1.04,-1.07,-.37,.66,1.01,-.95)
    for i,(a,b,c,r,strip,bend) in enumerate(spans):
        a,b,c=np.array(a),np.array(b),np.array(c)
        p0=np.array([.025*np.sign(a[0]),.136,.019*np.sign(a[2])])
        mid_p=p0*.29+a*.71
        petiole=(p0,p0*.58+mid_p*.42)
        lace_shell(m,petiole,[mid_p,a,b,c],r*1.20,strip,(.11*i)%1,bend,rolls[i])
    m.tube(np.array([[-.062,.125,-.004],[-.028,.14,.004],[.025,.139,0],[.069,.125,.004]]),
           [.018,.031,.025,.016],8,0,[0,0,0,0],0,[0,.13,0],"horizontal_tuber")
    roots(m,[
        ((-.040,.135,.006),(-.064,.060,.036),(-.081,.009,.032),.008),
        ((-.021,.132,.012),(-.039,.071,.051),(-.034,.0,.072),.007),
        ((.002,.132,.013),(.009,.055,.064),(.027,.013,.084),.007),
        ((.025,.132,.009),(.046,.079,.049),(.066,.024,.064),.0065),
        ((.045,.132,-.005),(.074,.067,-.037),(.085,.008,-.040),.007),
        ((.004,.123,-.026),(.006,.041,-.058),(-.014,.012,-.067),.007),
        ((-.043,.127,-.014),(-.067,.058,-.045),(-.069,.008,-.072),.0055),
    ],[0,.13,0])
    return m


def fern_leaflet(m, base, tip, side, width, droop, phase, anchor, k, weight):
    """Closed pointed pinna with central ridge. All visible gaps are geometric."""
    center=(.47*base+.53*tip)
    axis=norm(tip-base)
    lateral=norm(np.cross(np.array([0,1,0]),axis))
    if np.linalg.norm(lateral)<.1:
        lateral=np.array([0,0,1])
    rolled=.77*side + .19*np.sin(phase*14)
    lateral=norm(lateral*np.cos(rolled)+np.cross(axis,lateral)*np.sin(rolled))
    n=norm(np.cross(axis,lateral))
    l=center+width*lateral
    r=center-width*lateral
    ridge=.44*base+.56*tip+n*(.0043+droop)
    below=.46*base+.54*tip-n*.0019
    swatch=17+(k%6)*58
    m.surface([base,l,tip,r,ridge,below],
              [[swatch+25,39],[swatch+3,57],[swatch+26,76],[swatch+45,58],[swatch+24,61],[swatch+22,57]],
              [(0,1,4),(1,2,4),(2,3,4),(3,0,4),(0,5,1),(1,5,2),(2,5,3),(3,5,0)],
              weight,phase,anchor,"pinnate_closed_leaflet")


def fern():
    m=Assembly()
    root_guide=np.array([[-.300,.105,.033],[-.171,.122,-.010],[.011,.123,-.014],
                         [.172,.113,.016],[.303,.099,.041]])
    m.tube(root_guide,[.011,.021,.026,.020,.009],7,0,np.zeros(5),0,[0,.12,0],"creeping_rhizome_closed")
    # Fronds rise at deliberately different positions on the creeping rhizome;
    # in plan view they fan fore/aft instead of facing the same view.
    layout=[
        ((-.222,.113,.010),(-.340,.337,.137),(-.463,.306,.259),.065,.15,4),
        ((-.156,.118,-.020),(-.263,.385,-.135),(-.325,.493,-.266),.055,.24,4),
        ((-.076,.126,-.016),(-.127,.370,.039),(-.182,.564,.080),.071,.35,5),
        ((.043,.122,-.024),(.151,.379,-.119),(.217,.510,-.234),.072,.46,5),
        ((.126,.120,.009),(.277,.337,.134),(.429,.380,.223),.058,.57,4),
        ((.181,.113,.035),(.320,.247,-.053),(.449,.242,-.205),.051,.67,4),
        ((-.017,.116,.019),(.018,.242,.210),(-.046,.221,.313),.053,.75,4),
    ]
    for i,(a,b,c,w,phase,count) in enumerate(layout):
        anchor=np.asarray(a)
        b,c=np.asarray(b),np.asarray(c)
        line=[anchor,anchor*.50+b*.50,b,c]
        m.tube(curve(line,np.linspace(0,1,5)),np.linspace(.0069,.0018,5),4,-1,
               np.linspace(0,.94,5),phase,anchor,"frond_rachis_closed")
        ts=np.linspace(.31,.86,count)
        for side in (-1,1):
            for j,t in enumerate(ts):
                t=min(.94,t+.022*((i+j)%3)*side)
                base=curve(line,t)
                forward=norm(curve(line,min(t+.024,1))-base)
                lateral=norm(np.cross(np.array([0,1,0]),forward))
                size=1.36*w*(.67+.33*np.sin(np.pi*t))*(1-.76*((t-.23)/.78)**1.81)
                width=size*(.285+.060*((i+j)%3))
                tip=base+side*lateral*size+forward*(size*.53)+[0,.009+.003*j,0]
                fern_leaflet(m,base,tip,side,width,.003,phase,anchor,(i+j)%6,t)
        tip0=curve(line,.88)
        fern_leaflet(m,tip0,c,0,w*.23,.001,phase,anchor,1,.94)
    paths=[
        ((-.245,.110,.02),(-.264,.055,.071),(-.299,.0,.073),.0063),
        ((-.194,.115,.003),(-.173,.046,.079),(-.177,.016,.092),.0071),
        ((-.142,.122,-.003),(-.151,.041,-.056),(-.168,.0,-.069),.0065),
        ((-.075,.123,-.008),(-.059,.050,-.057),(-.090,.016,-.083),.0064),
        ((-.009,.126,.006),(.016,.060,.066),(.002,.014,.085),.0067),
        ((.072,.122,-.013),(.104,.041,-.060),(.117,.014,-.072),.0075),
        ((.135,.118,.005),(.161,.043,.082),(.133,.0,.095),.0066),
        ((.200,.111,.027),(.229,.062,.071),(.208,.013,.087),.0060),
        ((.251,.106,.028),(.273,.071,-.026),(.298,.023,-.059),.0063),
    ]
    roots(m,[paths[i] for i in (0,2,3,5,6,8)],[0,.12,0])
    return m


def build(key):
    info=spp[key]
    dims=np.asarray(info["size"])
    lace=info["mask"]
    out=folder/"candidates"/key
    out.mkdir(parents=True,exist_ok=True)
    review=work/"review-input"/key
    review.mkdir(parents=True,exist_ok=True)
    project=root/"projects"/("aquascape-e-"+key.replace("_","-"))
    source=project/"output"/f"{key}_six_views_raw.png"
    art=out/"six-material-views.png"
    shutil.copyfile(source,art)
    texture=build_atlas(art,lace)
    texture.save(review/"atlas-preview.png")
    m=globals()["lace" if lace else "fern"]()
    xyz=np.array(m.xyz,dtype=np.float64)
    minpos,maxpos=xyz.min(0),xyz.max(0)
    center=(minpos+maxpos)/2
    center[1]=minpos[1]
    factor=dims/(maxpos-minpos)
    xyz=((xyz-center)*factor).astype(np.float32)
    faces=np.array(m.faces)
    tri=xyz[faces]
    topo=estimate_topology(xyz,faces)
    if len(faces)>1000 or topo["open_edges"] or topo["nonmanifold_edges"]:
        raise ValueError(f"Invalid complete plant topology: {len(faces)} {topo}")
    coords=np.array(m.data,dtype=np.float32)
    anchor=(coords[:,2:]-center)*factor
    anchor_min=anchor.min(0)-.0001
    anchor_size=np.maximum(anchor.max(0)-anchor_min,.0002)
    rgba=np.concatenate([(anchor-anchor_min)/anchor_size,np.ones((len(anchor),1))],axis=1)
    uv=np.array(m.uv)
    model=out/f"{key}.glb"
    glb=Glb()
    material=glb.material(texture,info["name"])
    if lace:
        mat=glb.doc["materials"][material]
        mat["alphaMode"]="MASK"
        mat["alphaCutoff"]=.5
    glb.mesh(xyz,faces,uv,material,key)
    prim=glb.doc["meshes"][0]["primitives"][0]
    attrs=prim["attributes"]
    attrs["TEXCOORD_1"]=glb.accessor(coords[faces,:2].reshape(-1,2),"VEC2")
    attrs["COLOR_0"]=glb.accessor(rgba[faces].reshape(-1,4),"VEC4")
    glb.save(model)
    parsed=inspect(model,allow_alpha_mask=lace)
    if not parsed["ok"] or parsed["nonmanifold_edges"]:
        raise ValueError(parsed)
    positions=tri.reshape(-1,3)
    motion=coords[faces,:2].reshape(-1,2)
    colors=rgba[faces].reshape(-1,4)
    roots=motion[:,0]<=.08
    tips=motion[:,0]>.8
    max_root=0.
    max_tip=0.
    max_loop=0.
    for phase in (0,.31,.62):
        initial=shader_pose(positions,motion,colors,anchor_min,anchor_size,0.,phase,info["amplitude"])
        end=shader_pose(positions,motion,colors,anchor_min,anchor_size,10.,phase,info["amplitude"])
        max_loop=max(max_loop,float(np.linalg.norm(end-initial,axis=1).max()))
        for t in np.linspace(0,10,81):
            pose=shader_pose(positions,motion,colors,anchor_min,anchor_size,float(t),phase,info["amplitude"])
            max_tip=max(max_tip,float(np.linalg.norm((pose-initial)[tips],axis=1).max()))
            max_root=max(max_root,float(np.linalg.norm((pose-positions)[roots],axis=1).max()))
    if max_root>1e-6 or max_loop>1e-6 or max_tip<.001:
        raise ValueError(f"Invalid rooted deformation {max_root, max_loop, max_tip}")
    node=np.arange(len(faces)*3).reshape(-1,3)
    gray=review/f"{key}-gray.glb"
    if lace:
        g=Glb()
        gray_array=np.array(texture)
        gray_array[:,:,:3]=[161,166,166]
        mat=g.material(Image.fromarray(gray_array),"Gray and source cutouts")
        g.doc["materials"][mat].update(alphaMode="MASK",alphaCutoff=.5)
        g.mesh(xyz,faces,uv,mat,key)
        g.save(gray)
    else:
        make_glb(gray,"Gray reference",xyz,faces,np.full((len(faces)*3,2),.5,np.float32),Image.new("RGBA",(2,2),(161,166,166,255)))
    np.savez_compressed(model.with_suffix(".npz"),vertices=xyz,faces=faces)
    editable=out/f"{key}.blend"
    run=[str(blender),"-b","--python-exit-code","1","--python",str(common/"blend_source.py"),
         "--",str(model),"--editable-dir",str(out)]
    subprocess.run(run,check=True)
    model.with_suffix(".npz").unlink()
    augment=[str(blender),"-b",str(editable),"--python-exit-code","1","--python",str(folder/"editable_channels.py"),
             "--",str(model)]
    subprocess.run(augment,check=True)
    verify=[str(blender),"-b",str(editable),"--python-exit-code","1","--python",
            str(root/"work/reef-expansion-20261123/verify_blend_source.py"),"--",str(out)]
    subprocess.run(verify,check=True)
    opts={"anchor_min":anchor_min.tolist(),"anchor_size":anchor_size.tolist(),"amplitude":info["amplitude"]}
    catalog={"id":key,"name":info["name"],"label":info["name"],"category":"plant","budget_type":"broadleaf_plant",
             "nominal_xyz_m":dims.tolist(),"triangles":len(faces),"model":str(model),"source_glb":str(model),
             "editable_source":str(editable),"source_intent":str(art),"validation":str(out/"validation.json"),
             "scientific_name":info["scientific_name"],"source_url":info["source_url"],"habitat":info["habitat"],
             "rooted_current":opts,"user_acceptance":"pending"}
    if lace:
        catalog["material_mode"]="mask"
    report={**catalog,"source_sha256":sha(art),"editable_sha256":sha(editable),"native_atlas_size":list(texture.size),
            "glb":parsed,"passes":{"complete_budget":True,"cold_blender_positions_uv_texture":True},
            "closed_geometry":topo,"geometry_groups":m.groups,
            "immobile_base_vertices":int(roots.sum()),"shader_tests":{"phase_instances":3,"steps":81,"period_s":10.0,
            "max_fixed_point_um":max_root*1e6,"max_loop_error_um":max_loop*1e6,"max_running_tip_displacement_cm":max_tip*1e2,
            "native_runtime":"pending"},
            "art_review":"六面完整植株来源，先核对整簇高低、前后、叶形和根，再定三维。作者独立选取图中代表性枝叶轮廓，来源视图不作为实测。",
            "scope":"透孔二维 alpha .5 随封闭双壳转动，肉眼可见孔，微观孔壁不逐个建模。" if lace else "实际有厚度的羽片与独立叶隙。活动范围为对照用设计值。"}
    write_json(out/"validation.json",report)
    write_json(out/"catalog-entry.json",catalog)
    print(key,len(faces),topo,"motion",round(max_tip,4),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("keys",nargs="+",choices=spp)
    args=parser.parse_args()
    for key in args.keys:
        build(key)
