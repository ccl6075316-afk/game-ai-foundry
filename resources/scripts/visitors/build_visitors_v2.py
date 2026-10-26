#!/usr/bin/env python3
"""Source-calibrated visitor rebuild: six silhouettes, eighteen appearances.

Geometry is authored here and in the reviewed species-independent profile.
The game only cold-loads the six saved meshes. All original image pixels are
preserved; source donor crops are packed without rescaling or invented paint.
Three head/hair variants are stored as mesh deltas and UVs, sharing one surface.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

ARCHETYPES = ("adult_male", "adult_female", "elderly_male", "elderly_female", "boy", "girl")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare_atlas(profile, root, output):
    """Pack named source rectangles, with edge padding and background extrusion."""
    sources = {name: Image.open(root / entry["path"]).convert("RGB") for name, entry in profile["sources"].items()}
    patches = {}
    for key, donor in profile["donors"].items():
        patch = sources[donor["source"]].crop(tuple(donor["rect"]))
        # Only source-sheet near-neutral cream is extruded, never skin/fabric.
        a = np.array(patch)
        mask = (a[:,:,0] > 238) & (a[:,:,1] > 229) & (a[:,:,2] > 214) & (a.max(2)-a.min(2)<29)
        face_interior=donor.get("facial_interior",False)
        if face_interior:
            # Source illustrations outline their 2D silhouette. Those border
            # pixels are not cheek/neck albedo. Extrude only verified interior
            # skin at the chart boundary; preserve central eyes/brows/lips.
            for row in range(a.shape[0]):
                v=row/max(1,a.shape[0]-1)
                margin=float(np.interp(v,[0,.16,.28,.45,.62,.80,1],[.22,.08,.07,.07,.12,.27,.42]))
                lo=int(a.shape[1]*margin);hi=a.shape[1]-lo
                mask[row,:lo]=True;mask[row,hi:]=True
        valid_rows = np.where((~mask).any(1))[0]
        if not len(valid_rows):
            raise ValueError(f"Empty donor {key}")
        for y in range(a.shape[0]):
            xs=np.where(~mask[y])[0]
            if len(xs):
                candidates=xs
                if face_interior:
                    # Border extrusion must not extend a brow/eyelash across
                    # the cheek. Use source skin pixels near the cheek tone.
                    tone=np.median(a[int(a.shape[0]*.55):int(a.shape[0]*.65),int(a.shape[1]*.33):int(a.shape[1]*.43)],axis=(0,1))
                    skin=xs[np.linalg.norm(a[y,xs].astype(float)-tone,axis=1)<65]
                    if len(skin): candidates=skin
                for x in np.where(mask[y])[0]:
                    a[y,x]=a[y,candidates[np.argmin(abs(candidates-x))]]
            else:
                a[y]=a[valid_rows[np.argmin(abs(valid_rows-y))]]
        patches[key]=Image.fromarray(a)
    # Shelf packing by height preserves source pixels and minimizes atlas area.
    width=2048; placements={}; x=y=row=4
    for key, patch in sorted(patches.items(),key=lambda kv:-kv[1].height):
        if x+patch.width+4>width:
            x=4; y+=row+8; row=0
        placements[key]=(x,y,patch.width,patch.height)
        x+=patch.width+8; row=max(row,patch.height)
    height=2**math.ceil(math.log2(y+row+4))
    if height>4096:
        raise ValueError("Atlas exceeds the reviewed 2048x4096 budget")
    atlas=Image.new("RGB",(width,height),(88,64,43))
    for key,patch in patches.items():
        x,y,w,h=placements[key]
        atlas.paste(patch,(x,y))
        atlas.paste(patch.crop((0,0,1,h)).resize((3,h)),(x-3,y))
        atlas.paste(patch.crop((w-1,0,w,h)).resize((3,h)),(x+w,y))
        atlas.paste(patch.crop((0,0,w,1)).resize((w,3)),(x,y-3))
        atlas.paste(patch.crop((0,h-1,w,h)).resize((w,3)),(x,y+h))
    atlas.save(output / "visitor_atlas.png")
    return placements,(width,height)


class Sculpt:
    def __init__(self, archetype, appearance, profile, rects, atlas_size):
        self.archetype=archetype
        self.settings=profile["archetypes"][archetype]
        self.appearance=self.settings["appearances"][appearance]
        self.rects=rects; self.atlas_size=atlas_size
        self.positions=[]; self.normals=[]; self.uv=[]; self.rig=[]; self.weights=[]; self.regions=[]
        self.parts=[]

    def texture(self,key,u,v):
        donor=self.appearance.get("textures",{}).get(key,self.settings["textures"].get(key))
        if donor is None:
            raise ValueError(f"No donor for {self.archetype}/{key}")
        x,y,w,h=self.rects[donor]
        return [(x+.5+max(0,min(1,u))*(w-1))/self.atlas_size[0],
                (y+.5+max(0,min(1,v))*(h-1))/self.atlas_size[1]]

    def triangle(self,points,uv,limb,pivot,weights,region,part):
        p=np.array(points,dtype=float)
        normal=np.cross(p[1]-p[0],p[2]-p[0])
        length=np.linalg.norm(normal)
        if length<1e-10:
            raise ValueError(f"Degenerate topology {part}")
        normal/=length
        # Mathematical outward normal; Godot's front face uses clockwise order.
        for i in (0,2,1):
            self.positions.append(points[i]); self.normals.append(normal.tolist())
            self.uv.append(uv[i]); self.rig.append([*pivot,limb]); self.weights.append(weights[i]); self.regions.append(region)
            self.parts.append(part)

    def grid(self,rows,key,limb,pivot,region,part,weights=None,front_uv=None,cap=True):
        """Closed ring surface with smooth normals and separate front/back donors."""
        n=len(rows[0]); count=len(rows)
        if weights is None: weights=[1.0]*count
        for j in range(count-1):
            for i in range(n):
                k=(i+1)%n
                angle=2*math.pi*(i+.5)/n
                direction="front" if math.cos(angle)>.48 else ("back" if math.cos(angle)<-.48 else "side")
                indices=[(j,i),(j,k),(j+1,k),(j+1,i)]
                points=[rows[a][b] for a,b in indices]
                uv=[]
                for a,b in indices:
                    t=2*math.pi*b/n
                    u=.5+.5*math.sin(t) if direction=="front" else (.5-.5*math.sin(t) if direction=="back" else .5+.5*math.cos(t))
                    v=1-a/(count-1)
                    if front_uv is not None:
                        u,v=front_uv(a,b,direction)
                    uv.append(self.texture(f"{key}_{direction}",u,v))
                w=[weights[a] for a,b in indices]
                self.triangle([points[0],points[2],points[1]],[uv[0],uv[2],uv[1]],limb,pivot,[w[0],w[2],w[1]],region,part)
                self.triangle([points[0],points[3],points[2]],[uv[0],uv[3],uv[2]],limb,pivot,[w[0],w[3],w[2]],region,part)
        if cap:
            caps=[(count-1,True)] if cap=="top" else [(0,False),(count-1,True)]
            for j,upper in caps:
                center=np.array(rows[j]).mean(0).tolist()
                for i in range(n):
                    k=(i+1)%n
                    ids=[k,i] if upper else [i,k]
                    points=[center,rows[j][ids[0]],rows[j][ids[1]]]
                    uv=[self.texture(f"{key}_back",.5,.5)]*3
                    self.triangle(points,uv,limb,pivot,[weights[j]]*3,region,part)

    def loft(self,rings,key,limb,pivot,region,part,sides=16,weights=None):
        rows=[]
        for y,rx,rz,cx,cz in rings:
            rows.append([[cx+rx*math.sin(t),y,cz-rz*math.cos(t)] for t in np.linspace(0,2*math.pi,sides,endpoint=False)])
        self.grid(rows,key,limb,pivot,region,part,weights)

    def ellipsoid(self,center,radius,key,limb,pivot,region,part,sides=12):
        rings=[]
        for angle in np.linspace(-math.pi*.48,math.pi*.48,9):
            rings.append([center[1]+radius[1]*math.sin(angle),radius[0]*math.cos(angle),radius[2]*math.cos(angle),center[0],center[2]])
        self.loft(rings,key,limb,pivot,region,part,sides)

    def head(self,base,height,width,depth,pivot):
        shape=self.appearance["shape"]
        n=32; levels=19
        width*=shape.get("width",1)
        depth*=shape.get("depth",1)
        cheek=shape.get("cheek",1)
        jaw=shape.get("jaw",1)
        nose=shape.get("nose",.027)
        nose_width=shape.get("nose_width",.055)
        mouth=shape.get("mouth",.006)
        rows=[]
        # Cranial form includes actual chin, cheek, brow, nose and lip volumes.
        for v in np.linspace(0,1,levels):
            rx=np.interp(v,[0,.10,.28,.48,.68,.88,1],[.46,.69,.88,1.0,1.0,.88,.43])*width
            rx*=1+(jaw-1)*math.exp(-((v-.18)/.18)**2)+(cheek-1)*math.exp(-((v-.48)/.19)**2)
            rz=np.interp(v,[0,.10,.30,.55,.78,1],[.45,.70,.90,1,1,.58])*depth
            row=[]
            for angle in np.linspace(0,2*math.pi,n,endpoint=False):
                x=rx*math.sin(angle); z=-rz*math.cos(angle)
                front=max(0,math.cos(angle))**8
                # Profile relief is part of the head topology, not pasted decals.
                relief=nose*math.exp(-(x/nose_width)**2)*math.exp(-((v-.30)/.085)**2)
                relief+=nose*.35*math.exp(-(x/(nose_width*.65))**2)*math.exp(-((v-.48)/.14)**2)
                relief+=mouth*math.exp(-(x/(width*.38))**4)*math.exp(-((v-.16)/.045)**2)
                relief+=.009*math.exp(-(x/(width*.50))**2)*math.exp(-((v-.055)/.05)**2)
                for eye in (-width*.43,width*.43):
                    relief-=.006*math.exp(-((x-eye)/.033)**2)*math.exp(-((v-.45)/.055)**2)
                    relief+=.006*math.exp(-((x-eye)/.042)**2)*math.exp(-((v-.55)/.040)**2)
                row.append([x,base+height*v,z-relief*front])
            rows.append(row)
        def head_uv(a,b,direction):
            v=a/(levels-1); angle=2*math.pi*b/n
            landmarks=self.appearance.get("face_uv_y",[1,.95,.82,.71,.55,.46,0])
            texture_v=float(np.interp(v,[0,.07,.16,.30,.45,.55,.62,1],landmarks[:-1]+[.08,landmarks[-1]]))
            if direction=="front":
                return .5+rows[a][b][0]/(2*width),texture_v
            if direction=="side":
                # Profile donor is nose-right: front maps toward the right edge.
                return .5+.5*math.cos(angle),texture_v
            return .5-.5*math.sin(angle),texture_v
        self.grid(rows,"head",9,pivot,0,"head",front_uv=head_uv)
        for side in (-1,1):
            self.ellipsoid((side*width*.97,base+height*.47,.0),(.027,.045,.022),"skin",9,pivot,0,"ear",12)
        self.hair(base,height,width,depth,pivot,shape)

    def hair(self,base,height,width,depth,pivot,shape):
        n=32; rows=[]
        kind=self.settings["hair"]
        curl=shape.get("curl",0)
        volume=shape.get("hair_volume",1.04)
        fringe=shape.get("fringe",.79)
        for v in np.linspace(0,1,9):
            row=[]
            for angle in np.linspace(0,2*math.pi,n,endpoint=False):
                front=max(0,math.cos(angle))
                if kind=="bob":
                    opening=max(0,min(1,(math.cos(angle)-.12)/.43))
                    opening=opening*opening*(3-2*opening)
                    lower=.15+(fringe-.15)*opening+.06*math.sin(angle)*front
                elif kind=="receding": lower=.39+.54*((1+math.cos(angle))*.5)**1.1
                elif kind=="short_soft": lower=.34+.42*((1+math.cos(angle))*.5)**1.1
                else: lower=.37+(fringe-.37)*((1+math.cos(angle))*.5)**1.1
                lower+=shape.get("hairline_wave",.025)*math.sin(angle*5+.7)
                if kind in ("short","ponytail"):
                    lower+=front*.032*math.sin(angle*11+shape.get("parting",.3))*(1-curl*.6)
                h=lower+(1.09-lower)*v
                # Cranial upper envelope continues smoothly into a modest crown.
                waves=1+curl*.035*math.cos(angle*9)*math.cos(v*math.pi*5)
                # Follow the authored skull's actual upper envelope. An ellipse
                # here buries the fringe inside the forehead and reads as bald.
                lateral=float(np.interp(h,[0,.28,.48,.68,.80,.92,1.02,1.09],[.5,.9,1.02,1.05,1.04,.94,.64,.10]))
                sagittal=float(np.interp(h,[0,.30,.55,.78,.90,1.02,1.09],[.5,.94,1.05,1.05,.98,.68,.10]))
                rx=width*volume*lateral*waves
                rz=depth*(volume+.03)*sagittal*waves
                if kind!="bob":
                    # Root follows the scalp so receding hair cannot float as
                    # a separate cap. Volume grows above the rooted hairline.
                    root_x=float(np.interp(lower,[0,.10,.28,.48,.68,.88,1],[.46,.69,.88,1,1,.88,.43]))*width*1.018
                    root_z=float(np.interp(lower,[0,.10,.30,.55,.78,1],[.45,.70,.90,1,1,.58]))*depth*1.018
                    rooted=max(0,1-v*5)
                    rx=rx*(1-rooted)+root_x*rooted
                    rz=rz*(1-rooted)+root_z*rooted
                if kind=="bob":
                    rx=max(rx,width*(1.30-.90*v*v))
                    rz=max(rz,depth*(1.18-.65*v*v))
                row.append([rx*math.sin(angle),base+h*height,-rz*math.cos(angle)+.007])
            rows.append(row)
        # The lower hairline is not planar. Capping it creates triangular hair
        # curtains across the face; the skull already closes this hidden side.
        hair_start=len(self.positions)
        self.grid(rows,"hair",9,pivot,3,"hair",cap="top")
        if kind=="bob":
            # Bob is a thin solid hair shell, with an inward-facing inner skin.
            # Without this, the rear shell vanishes through the frontal opening
            # and only razor-thin side edges remain visible in a front view.
            hair_end=len(self.positions)
            for j in range(hair_start,hair_end,3):
                for k in (0,2,1):
                    i=j+k
                    self.positions.append((np.array(self.positions[i])-np.array(self.normals[i])*.002).tolist())
                    self.normals.append((-np.array(self.normals[i])).tolist())
                    self.uv.append(self.uv[i]);self.rig.append(self.rig[i]);self.weights.append(self.weights[i]);self.regions.append(3);self.parts.append("hair_inside")
        if kind=="ponytail":
            self.loft([(base+height*y,width*x,depth*z,-width*.55,depth*offset) for y,x,z,offset in [
                (-.10,.12,.10,1.35),(.0,.24,.20,1.50),(.20,.29,.26,1.55),(.36,.25,.23,1.45),(.50,.12,.14,1.05)]],
                "hair",9,pivot,3,"ponytail",16)

    def build(self):
        s=self.settings["body"]
        h=s["height"]; head_h=s["head_height"]; base=h-head_h*1.09
        shoulder=s["shoulder_y"]; hip=s["hip_y"]
        shoulder_w=s["shoulder_half_width"]; waist=s["waist_half_width"]
        chest=s["chest_depth"]; head_pivot=(0,base+.025,0)
        torso=[(hip+.015,waist*.98,chest*.87,0,0),(hip+.06,waist,chest*.95,0,0),
               (hip+(shoulder-hip)*.38,waist*.97,chest,0,-.003),
               (hip+(shoulder-hip)*.72,shoulder_w*.94,chest,0,-.008),
               (shoulder-.025,shoulder_w,chest*.87,0,-.010),
               (shoulder+.025,shoulder_w*.80,chest*.69,0,-.010),
               (shoulder+.035,.068,chest*.46,0,-.008)]
        self.loft(torso,"shirt",0,(0,0,0),1,"torso",24)
        self.loft([(shoulder+.035,.058,.054,0,-.006),(base+.045,.053,.051,0,-.004)],
                  "skin",9,head_pivot,0,"neck",16,[0,1])
        if self.settings.get("collar","folded")=="folded":
            # Two shirt-collar leaves, with an actual V opening. A cylindrical
            # neck band would incorrectly turn every shirt into a turtleneck.
            for sign in (-1,1):
                points=[(sign*.056,shoulder+.038,-.049),(sign*.093,shoulder-.008,-.084),
                        (sign*.047,shoulder-.045,-.111),(sign*.014,shoulder+.006,-.067)]
                uv=[self.texture("collar_front",u,v) for u,v in [(0,0),(1,0),(1,1),(0,1)]]
                if sign<0:
                    self.triangle([points[0],points[1],points[2]],[uv[0],uv[1],uv[2]],0,(0,0,0),[0]*3,1,"collar")
                    self.triangle([points[0],points[2],points[3]],[uv[0],uv[2],uv[3]],0,(0,0,0),[0]*3,1,"collar")
                else:
                    self.triangle([points[0],points[2],points[1]],[uv[0],uv[2],uv[1]],0,(0,0,0),[0]*3,1,"collar")
                    self.triangle([points[0],points[3],points[2]],[uv[0],uv[3],uv[2]],0,(0,0,0),[0]*3,1,"collar")
        leg_x=s["leg_spacing"]
        knee=hip*.51
        shorts=s.get("shorts",False)
        self.loft([(hip-.135,waist*.87,chest*.82,0,0),(hip-.06,waist,chest*.92,0,0),
                   (hip+.012,waist*.99,chest*.89,0,0)],"pelvis",0,(0,0,0),2,"pelvis",24)
        self.loft([(hip-.008,waist*1.007,chest*.91,0,0),(hip+.022,waist*.997,chest*.90,0,0)],
                  "belt",0,(0,0,0),4,"waistband",24)
        for sign,limb in [(-1,3),(1,4)]:
            cx=sign*leg_x; pivot=(cx,hip-.075,0)
            ankle=.095*(h/1.72)
            if shorts:
                self.loft([(ankle,.044,.046,cx,0),(knee*.91,.049,.052,cx,0),
                           (hip*.72,.060,.062,cx,0),(hip-.06,.064,.065,cx,0)],
                          "skin",limb,pivot,0,"leg",14,[1,1,1,0])
                rings=[(hip*.61,.074,.073,cx,0),(hip*.78,.078,.077,cx,0),(hip-.030,.078,.081,cx,0)]
                weights=[1,1,0]
            else:
                thigh=min(.080,waist-leg_x-.006)
                rings=[(ankle,.059,.061,cx,0),(hip*.27,.064,.064,cx,0),(knee,.069,.071,cx,0),
                       (hip*.79,thigh,.082,cx,0),(hip-.050,thigh,.086,cx,0),(hip-.030,thigh,.083,cx,0)]
                weights=[1,1,1,1,.25,0]
            self.loft(rings,"pants",limb,pivot,2,"trousers",16,weights)
            scale=h/1.72
            self.loft([(y*scale,rx*scale,rz*scale,cx,z*scale) for y,rx,rz,z in [
                (.0,.063,.105,-.030),(.035,.073,.123,-.036),(.068,.075,.120,-.032),
                (.105,.061,.092,-.015),(.126,.052,.061,0)]],"shoe",limb,pivot,4,"shoe",16)
        elbow=hip+(shoulder-hip)*.40
        wrist=hip-.015
        for sign,limb in [(-1,1),(1,2)]:
            cx=sign*(shoulder_w+.004); pivot=(cx,shoulder-.015,-.005)
            arm_len=shoulder-wrist
            sleeve_bottom=shoulder-arm_len*self.settings.get("sleeve_fraction",.43)
            root=[(sleeve_bottom,.052,.057,cx+sign*.030,-.005),
                  (shoulder-arm_len*.25,.058,.062,cx+sign*.018,-.004),
                  (shoulder-.035,.061,.066,cx+sign*.003,-.004),
                  (shoulder+.010,.046,.049,cx-sign*.014,-.004),
                  (shoulder+.026,.018,.020,cx-sign*.019,-.004)]
            self.loft(root,"sleeve",limb,pivot,1,"sleeve",16,[1,.95,.30,0,0])
            forearm_top=max(wrist+.07,sleeve_bottom+.035)
            self.loft([(wrist,.034,.039,cx+sign*.045,-.023),
                       (wrist+(forearm_top-wrist)*.35,.045,.044,cx+sign*.046,-.013),
                       (wrist+(forearm_top-wrist)*.72,.049,.048,cx+sign*.041,-.006),
                       (forearm_top,.042,.042,cx+sign*.030,-.004)],
                      "skin",limb,pivot,0,"forearm",16)
            self.ellipsoid((cx+sign*.046,wrist-.029,-.026),(.043,.064,.037),"skin",limb,pivot,0,"mitten",14)
        self.head(base,head_h,s["head_half_width"],s["head_depth"],head_pivot)
        # Smooth normals within a physical component, even across UV seams.
        sums={}
        for p,n,part in zip(self.positions,self.normals,self.parts):
            key=(part,*[round(v,7) for v in p])
            sums[key]=sums.get(key,np.zeros(3))+n
        for i,(p,part) in enumerate(zip(self.positions,self.parts)):
            n=sums[(part,*[round(v,7) for v in p])]
            self.normals[i]=(n/np.linalg.norm(n)).tolist()
        return self


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile",type=Path,required=True)
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--game",type=Path,required=True)
    parser.add_argument("--godot",type=Path,required=True)
    args=parser.parse_args(); root=args.root.resolve(); output=args.output.resolve(); game=args.game.resolve()
    assert output.is_relative_to(game/'assets')
    profile=json.loads(args.profile.read_text())
    assert profile["source_review"]=="accepted_for_trial_by_agent", "Source visual review required before model build"
    for source in profile["sources"].values():
        assert sha(root/source["path"])==source["sha256"],"Source changed after review"
    output.mkdir(parents=True,exist_ok=True)
    rects,atlas_size=prepare_atlas(profile,root,output)
    payload={}; metadata={}
    for name in ARCHETYPES:
        forms=[Sculpt(name,i,profile,rects,atlas_size).build() for i in range(3)]
        base=forms[0]; positions=np.array(base.positions)
        assert all(len(f.positions)==len(base.positions) for f in forms)
        custom1=np.column_stack((np.array(forms[1].positions)-positions,np.zeros(len(positions)))).tolist()
        custom2=np.column_stack((np.array(forms[2].positions)-positions,np.zeros(len(positions)))).tolist()
        custom3=np.column_stack((forms[2].uv,base.weights,base.regions)).tolist()
        payload[name]={"vertices":positions.ravel().tolist(),"normals":np.array(base.normals).ravel().tolist(),
                       "uv":np.array(base.uv).ravel().tolist(),"uv2":np.array(forms[1].uv).ravel().tolist(),
                       "custom0":np.array(base.rig).ravel().tolist(),"custom1":np.array(custom1).ravel().tolist(),
                       "custom2":np.array(custom2).ravel().tolist(),"custom3":np.array(custom3).ravel().tolist()}
        metadata[name]={"triangles":len(positions)//3,"surfaces":1,"appearances":3,"height_m":profile["archetypes"][name]["body"]["height"]}
    intermediate=output/'mesh_build.json'; intermediate.write_text(json.dumps(payload,separators=(',',':')))
    exporter=Path(__file__).with_name('save_visitor_meshes_v2.gd').resolve()
    log=game.parent/'output/visitors-v2/review/offline-build.log'; log.parent.mkdir(parents=True,exist_ok=True)
    result=subprocess.run([str(args.godot),'--headless','--path',str(game),'--log-file',str(log),'--script',str(exporter),'--',str(output)],capture_output=True,text=True)
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    print(result.stdout)
    intermediate.unlink()
    for name in metadata:
        metadata[name]['sha256']=sha(output/f'visitor_{name}.res')
    manifest={'schema_version':2,'source_review':profile['source_review'],'user_acceptance':'pending',
              'profile_sha256':sha(args.profile),'builder_sha256':sha(__file__),'exporter_sha256':sha(exporter),
              'shader_sha256':sha(game/'scripts/aquarium/visitors/VisitorMaterialV2.gdshader'),
              'atlas_size':atlas_size,'atlas_sha256':sha(output/'visitor_atlas.png'),'rects':rects,'sources':profile['sources'],
              'meshes':metadata,'contract':{'forward':'-Z','custom':['phase_radians','motion_blend','clothing_palette','appearance_0_1_2'],
              'custom0':'joint pivot xyz; limb ID w','custom1':'appearance1 position delta','custom2':'appearance2 position delta',
              'custom3':'appearance2 UV xy, jointblend z, materialregion w','uv':'appearance0','uv2':'appearance1'}}
    (output/'build_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    shutil.copyfile(args.profile,output/'build_profile.json')
    print(json.dumps({'ok':True,'meshes':metadata,'atlas_size':atlas_size}))


if __name__=='__main__':
    main()
