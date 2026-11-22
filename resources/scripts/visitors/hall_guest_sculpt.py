"""Adult aquarium guest. Coordinates in metres, facing -Z.

Clothes, eyelids, ear rims and hair have their own silhouettes. The three
appearances share connectivity so the hall can retain its instanced renderer.
"""
import math
from functools import lru_cache

import numpy as np

from build_visitors_v2 import Sculpt


class HallGuest(Sculpt):
    hip_y = .724
    shoulder_y = 1.177
    head_pivot = (0, 1.267, -.006)
    root = (0, 0, 0)

    def __init__(self, archetype, appearance, profile, rects, atlas_size):
        super().__init__(archetype, appearance, profile, rects, atlas_size)
        self.variant = appearance

    def stroke(self, knots, key, part, limb=0, pivot=root, region=4,
               normal=(0, 0, -1), sides=8):
        """Elliptical sweep with coupled width and relief along a 3D path."""
        centers = np.array([k[:3] for k in knots])
        rows = []
        for i, (_, _, _, width, relief) in enumerate(knots):
            tangent = centers[min(i+1,len(knots)-1)]-centers[max(i-1,0)]
            tangent /= np.linalg.norm(tangent)
            direction = np.array(normal, dtype=float)
            direction -= tangent*np.dot(tangent,direction)
            if np.linalg.norm(direction) < 1e-4:
                direction = np.array([1.,0.,0.])-tangent*tangent[0]
            direction /= np.linalg.norm(direction)
            across = np.cross(direction,tangent)
            row = []
            for k in range(sides):
                a = k*math.tau/sides
                row.append((centers[i]+direction*(relief*math.cos(a))+
                            across*(width*math.sin(a))).tolist())
            rows.append(row)
        self.grid(rows,key,limb,pivot,region,part)

    def panel(self, rows, key, part, outward, limb=0, pivot=root, region=1):
        """Open charted patch, wound to follow the garment/face surface."""
        for j in range(len(rows)-1):
            for i in range(len(rows[0])-1):
                for triangle in [((j,i),(j+1,i),(j+1,i+1)),((j,i),(j+1,i+1),(j,i+1))]:
                    ids=list(triangle)
                    points=np.array([rows[y][x] for y,x in ids])
                    if np.dot(np.cross(points[1]-points[0],points[2]-points[0]),outward)<0:
                        ids.reverse()
                    self.triangle([rows[y][x] for y,x in ids],
                                  [self.texture(key+"_front",x/(len(rows[0])-1),y/(len(rows)-1))
                                   for y,x in ids],limb,pivot,[1]*3,region,part)

    @staticmethod
    @lru_cache(maxsize=8192)
    def skull_profile(y):
        levels = np.array([1.268,1.287,1.315,1.357,1.409,1.468,1.521,1.580,1.620,1.653,1.665])
        profile = np.array([[.030,.053,-.054],[.064,.080,-.050],[.102,.106,-.037],
                            [.132,.127,-.025],[.158,.140,-.017],[.169,.147,-.009],
                            [.167,.151,-.005],[.155,.147,.001],[.126,.126,.009],
                            [.064,.078,.014],[.008,.013,.014]])
        # Hermite interpolation gives both sides of every cheek ring the same tangent.
        j=int(np.clip(np.searchsorted(levels,y)-1,0,len(levels)-2))
        h=levels[j+1]-levels[j]
        t=np.clip((y-levels[j])/h,0,1)
        slopes=np.gradient(profile,levels,axis=0)
        return ((2*t**3-3*t**2+1)*profile[j]+(t**3-2*t*t+t)*h*slopes[j]
                +(-2*t**3+3*t**2)*profile[j+1]+(t**3-t*t)*h*slopes[j+1])

    def skull_shape(self,y):
        rx,rz,cz=self.skull_profile(y)
        return rx*(1,1.035,.98)[self.variant],rz*(1,.98,1.025)[self.variant],cz

    @staticmethod
    def head_y(y):
        return y-.030+.040*(max(0,1-(y-1.268)/.145))**1.35

    def skin_surface(self,x,y):
        rx,rz,cz=self.skull_shape(y)
        xfrac=min(abs(x)/rx,1.0)
        front=(1-xfrac**2.4)**(1/2.4)
        cheek=.007*math.exp(-((abs(x)-.088)/.037)**2-((y-1.413)/.034)**2)
        muzzle=.009*math.exp(-(x/.052)**2-((y-1.376)/.03)**2)
        bridge=.019*math.exp(-(x/.025)**2-((y-1.450)/.047)**2)
        tip=.034*math.exp(-(x/.024)**2-((y-1.420)/.019)**2)
        wing=.012*math.exp(-((abs(x)-.019)/.012)**2-((y-1.416)/.011)**2)
        return cz-rz*front-(cheek+muzzle+bridge+tip+wing)*front

    def face(self):
        pivot=self.head_pivot
        rows=[]
        levels=sorted(set([*np.linspace(1.268,1.665,21),1.287,1.315,1.357,1.409,1.468,
                           1.521,1.580,1.620,1.653,1.401,1.412,1.418,1.425,1.433,1.446]))
        # Extra samples around the nose bridge make a single continuous skin surface.
        angles=sorted(set([*np.arange(32)*math.tau/32,.052,.103,.148,math.tau-.052,
                           math.tau-.103,math.tau-.148]))
        def surface(a,y,transformed=False):
            rx,rz,cz=self.skull_shape(y)
            x=rx*math.sin(a)
            z=self.skin_surface(x,y) if math.cos(a)>1e-8 else cz-rz*math.cos(a)
            # Sink the unseen scalp only above the visible hairline, including
            # the far side of the asymmetrical part in every face morph.
            covered=np.clip((y-self.hairline(a)+.002)/.044,0,1)
            scale=1-.25*covered*covered*(3-2*covered)
            return np.array([x*scale,self.head_y(y) if transformed else y,cz+(z-cz)*scale])
        self.face_normals={}
        for y in levels:
            row=[]
            for a in angles:
                point=surface(a,y)
                across=surface(a+.002,y,True)-surface(a-.002,y,True)
                along=(surface(a,min(1.665,y+.0005),True)-surface(a,max(1.268,y-.0005),True))
                n=np.cross(along,across); n/=np.linalg.norm(n)
                self.face_normals[(point[0],self.head_y(y),point[2])]=n.tolist()
                row.append(point.tolist())
            rows.append(row)
        # Front and both cheeks project into one chart up to the ear plane.
        for j in range(len(rows)-1):
            for i,a in enumerate(angles):
                k=(i+1)%len(angles)
                end=angles[k] if k else math.tau
                front=math.cos((a+end)*.5)>0
                chart="head_front" if front else "head_back"
                for ids in [((j,i),(j+1,k),(j,k)),((j,i),(j+1,i),(j+1,k))]:
                    uv=[self.texture(chart,.5+(.5 if front else -.5)*math.sin(angles[x]),
                                     (1.665-levels[y])/.397) for y,x in ids]
                    self.triangle([rows[y][x] for y,x in ids],uv,9,pivot,[1]*3,0,"face")
        for j in (0,len(rows)-1):
            center=np.mean(rows[j],axis=0).tolist()
            for i in range(len(angles)):
                k=(i+1)%len(angles)
                a,b=(i,k) if j==0 else (k,i)
                self.triangle([center,rows[j][a],rows[j][b]],
                              [self.texture("skin_back",.5,.5)]*3,9,pivot,[1]*3,0,"skull_cap")
        for sign in (-1,1):
            ear_x=sign*self.skull_shape(1.444)[0]*.978
            self.loft([(1.392,.012,.013,ear_x,.001),(1.404,.023,.021,ear_x,-.002),
                       (1.431,.031,.026,ear_x,-.008),(1.455,.029,.024,ear_x,-.005),
                       (1.476,.018,.017,ear_x,.001),(1.480,.009,.009,ear_x,.002)],
                      "skin",9,pivot,0,"ear",14)
            self.ellipsoid((ear_x+sign*.022,1.440,-.018),(.007,.019,.013),
                           "ear_inner",9,pivot,0,"concha",10)
            self.eye(sign)
        smile=[]
        for t in np.linspace(-1,1,11):
            x=.043*t
            y=1.359+.010*t*t+.0025*t
            smile.append((x,y,self.skin_surface(x,y)-.0015,.0011+.0024*(1-t*t),.002))
        self.stroke(smile,"lip","smile",9,pivot,0,sides=8)
        self.hairstyle()

    def eye(self, sign):
        # Trimmed almond surface and shallow domed iris follow the curved face.
        pivot=self.head_pivot
        cx=sign*.069
        cy=1.465
        eye_w=.034
        eye_h=(.017,.015,.018)[self.variant]
        def lid(x):
            t=(x-cx)/eye_w
            return cy+.003*sign*t
        def eye_z(x,y):
            amt=max(0,1-((x-cx)/eye_w)**2-((y-lid(x))/eye_h)**2)
            return self.skin_surface(x,y)-.0035-.009*amt
        rows=[]
        for v in np.linspace(1,-1,7):
            row=[]
            for u in np.linspace(-.998,.998,15):
                x=cx+eye_w*u
                y=lid(x)+v*eye_h*(max(.001,1-u*u)**.74)*(.83 if v<0 else 1)
                row.append([x,y,eye_z(x,y)])
            rows.append(row)
        self.panel(rows,"eye_white","sclera",(0,0,-1),9,pivot,5)
        # The iris is inset under the dark upper lid and has a soft colored rim.
        iris_x=cx-sign*.0025
        def disk(xc,yc,w,h,depth,key,part):
            pts=[[xc,yc,eye_z(xc,yc)-depth]]
            for i in range(20):
                a=i*math.tau/20
                x=xc+w*math.cos(a); y=yc+h*math.sin(a)
                limit=eye_h*(1-((x-cx)/eye_w)**2)**.74
                y=np.clip(y,lid(x)-limit*.83,lid(x)+limit)
                pts.append([x,y,eye_z(x,y)-depth])
            for i in range(20):
                p=[pts[0],pts[(i+1)%20+1],pts[i+1]]
                self.triangle(p,[self.texture(key+"_front",.5+(q[0]-xc)/(2*w),
                                                .5-(q[1]-yc)/(2*h)) for q in p],
                              9,pivot,[1]*3,5,part)
        disk(iris_x,cy+.001,eye_w*.51,eye_h*1.1,.0013,"iris","iris")
        disk(iris_x,cy+.001,eye_w*.29,eye_h*.71,.002,"pupil","pupil")
        disk(iris_x-.0045,cy+.007,.0040,.0045,.0031,"glint","catchlight")
        ridge=[]
        brow=[]
        for u in np.linspace(-.99,.99,13):
            x=cx+u*eye_w
            y=lid(x)+eye_h*(1-u*u)**.74
            ridge.append((x,y,eye_z(x,y)-.0005,.001+.0024*(1-u*u),.0018))
            y=cy+.035+.007*(1-(u+.14*sign)**2)-.003*u*sign+.003*sign
            brow.append((x,y,self.skin_surface(x,y)-.003,
                         .0015+.0055*(1-u*u)**.65,.004))
        self.stroke(ridge,"brow","upperlid",9,pivot,0)
        self.stroke(brow,"brow","brow",9,pivot,0)

    @staticmethod
    def hairline(a):
        a=(a+math.pi)%math.tau-math.pi
        front=max(0,math.cos(a));side=math.sin(a)
        y=1.446+.102*front-.094*max(0,-math.cos(a))+.047*side*front
        y-=.028*math.exp(-((a+.48)/.19)**2)*front
        y-=.018*math.exp(-((a+.94)/.15)**2)*front
        y+=.023*math.exp(-((a-.49)/.19)**2)*front
        y-=.019*math.exp(-((abs(side)-.977)/.055)**2)*front
        return y

    def hairstyle(self):
        # Relief is formed directly in a single hair shell. Long convex ridges
        # and pinched grooves read as clumps without floating hair strips.
        waves=[
            ([-1.27,-.78,-.26,.15,.64],[.025,.13,.29,.48,.65],.082,.023),
            ([-1.57,-1.04,-.60,-.02,.49],[.13,.32,.48,.67,.80],.095,.024),
            ([-1.78,-1.08,-.52,.16],[.32,.58,.79,.96],.078,.019),
            ([.37,.68,1.02,1.50],[.58,.41,.19,.035],.084,.016),
            ([1.05,1.53,1.94,2.45],[.76,.57,.33,.075],.085,.013),
            ([-3.3,-2.72,-2.16,-1.70],[.12,.34,.52,.74],.10,.009)]
        def envelope(a,v):
            f=math.cos(a); side=math.sin(a)
            front=max(0,f)
            base=self.hairline(a)
            skull_y=base+(1.664-base)*v
            rx,rz,cz=self.skull_shape(skull_y)
            crest=.050*math.exp(-((side+.47)/.70)**2)*front*math.sin(v*math.pi*.90)**1.5
            fullness=(.010+.008*front)*math.cos(v*math.pi*.495)+.42*crest
            x=(rx+fullness)*side-.033*v*v
            if f>0:
                z=self.skin_surface(rx*side,skull_y)-fullness*f
            else:
                z=cz-(rz+fullness)*f
            ridge=0
            for aa,vv,span,depth in waves:
                if aa[0]<a<aa[-1]:
                    t=(a-aa[0])/(aa[-1]-aa[0])
                    width=span*(.45+.55*math.sin(math.pi*t))
                    across=(v-np.interp(a,aa,vv))/width
                    ridge+=depth*math.sin(math.pi*t)**.7*(math.exp(-across*across)
                              -.21*math.exp(-((abs(across)-1.45)/.48)**2))
            normal=np.array([side,.12+v*1.5,-f])
            normal/=np.linalg.norm(normal)
            return (np.array([x,skull_y+.020*v+crest,z])+normal*ridge).tolist()
        count=72
        angles=[(i*math.tau/count+math.pi)%math.tau-math.pi for i in range(count)]
        rows=[[envelope(a,v) for a in angles] for v in np.linspace(0,1,29)]
        # Return the hairline edge through the skull so a grazing view under
        # the forelock and the back of the neck both see a solid underside.
        rim=[[x*.90,y+.006,z*.90] for x,y,z in rows[0]]
        self.grid([rim]+rows,"hair",9,self.head_pivot,3,"swept_hair",cap="top")

    def jacket(self,rings):
        # Each sleeve emerges from an open armhole. Both sides share the very
        # same boundary positions/normals; this retains a continuous shoulder.
        n=24
        rows=[[[cx+rx*math.sin(i*math.tau/n),y,cz-rz*math.cos(i*math.tau/n)]
               for i in range(n)] for y,rx,rz,cx,cz in rings]
        low,high=4,8
        half_hole=3
        def uv(j,i,view):
            a=i*math.tau/n
            u=.5+.5*math.sin(a) if view=="front" else (.5-.5*math.sin(a) if view=="back" else .5+.5*math.cos(a))
            return self.texture("shirt_"+view,u,1-j/(len(rows)-1))

        for j in range(len(rows)-1):
            for i in range(n):
                if low<=j<high and (3<=i<9 or 15<=i<21): continue
                k=(i+1)%n
                cosine=math.cos((i+.5)*math.tau/n)
                view="front" if cosine>.48 else ("back" if cosine<-.48 else "side")
                for ids in [((j,i),(j+1,k),(j,k)),((j,i),(j+1,i),(j+1,k))]:
                    self.triangle([rows[y][x] for y,x in ids],[uv(y,x,view) for y,x in ids],
                                  0,self.root,[0]*3,1,"shirt")
        for row,top in [(rows[0],False),(rows[-1],True)]:
            center=np.mean(row,axis=0).tolist()
            for i in range(n):
                a,b=(i,(i+1)%n) if not top else ((i+1)%n,i)
                self.triangle([center,row[a],row[b]],[self.texture("shirt_back",.5,.5)]*3,
                              0,self.root,[0]*3,1,"shirt")

        for side in (-1,1):
            limb=1 if side<0 else 2
            pivot=(side*.187,self.shoulder_y,.003)
            left=(6 if side>0 else 18)-half_hole
            right=left+2*half_hole
            ids=([(low,i) for i in range(left,right+1)]+[(j,right) for j in range(low+1,high+1)]
                 +[(high,i) for i in range(right-1,left-1,-1)]+[(j,left) for j in range(high-1,low,-1)])
            # Ring parameters map top-of-shoulder to outer sleeve and armpit to inside.
            edge=[np.array(rows[j][i]) for j,i in ids]
            middle=(rings[high][0]+rings[low][0])*.5
            half_height=(rings[high][0]-rings[low][0])*.5
            def arm_ring(y,w,d,x,z,edge_mix,round_up):
                result=[]
                for point in edge:
                    angle=math.atan2((point[2]+.009)/.079,(point[1]-middle)/half_height)
                    radial=math.cos(angle)
                    target=np.array([side*(x+w*radial),y+round_up*radial,z+d*math.sin(angle)])
                    result.append((target*(1-edge_mix)+point*edge_mix).tolist())
                return result
            tube=[[e.tolist() for e in edge],
                  arm_ring(1.133,.066,.070,.195,.001,.61,.051),
                  arm_ring(1.097,.064,.068,.207,.006,.18,.029),
                  arm_ring(1.056,.059,.064,.214,.011,0,.010),
                  arm_ring(1.014,.052,.058,.221,.012,0,.002),
                  arm_ring(1.006,.050,.057,.221,.012,0,0)]
            # Winding must face out on both mirrored sleeve tubes.
            for j in range(len(tube)-1):
                for i in range(len(edge)):
                    k=(i+1)%len(edge)
                    cell=[tube[j][i],tube[j][k],tube[j+1][k],tube[j+1][i]]
                    radial=np.mean(cell,axis=0)-(np.mean(tube[j],axis=0)+np.mean(tube[j+1],axis=0))*.5
                    outside=radial[0]*side>.025 and abs(radial[2])<.046
                    view="side" if outside else ("front" if radial[2]<0 else "back")
                    # The socket is vertical; texture height follows the actual
                    # shoulder, including the low underarm at its first ring.
                    # This keeps the sea-glass yoke level through the armhole.
                    chart=[]
                    for x,y,z in cell:
                        u=.5+z/.165 if outside else .5+(x-side*.210)/.145
                        v=np.clip((1.204-y)/.192,0,.78)
                        chart.append((u,v))
                    weights=[0,.20,.65,.95,1,1]
                    blend=[weights[j],weights[j],weights[j+1],weights[j+1]]
                    # The retained torso traverses the cut's bottom edge
                    # left-to-right. Reverse that exact boundary throughout the
                    # branch, including its concave armpit.
                    for tri in [(0,2,1),(0,3,2)]:
                        self.triangle([cell[q] for q in tri],[self.texture("sleeve_"+view,*chart[q]) for q in tri],
                                      limb,pivot,[blend[q] for q in tri],1,"shirt")
                        if j==0:
                            # A seam vertex also needs the torso sway/twist
                            # branch, even when local arm swing weight is zero.
                            for corner in range(len(self.rig)-3,len(self.rig)):
                                if self.weights[corner]==0:
                                    self.rig[corner]=[*self.root,0]

            # Close the sleeve under the separate folded cuff where the
            # forearm is thinner than the garment opening.
            last=tube[-1]
            center=np.mean(last,axis=0).tolist()
            for i in range(len(last)):
                k=(i+1)%len(last)
                self.triangle([center,last[k],last[i]],[self.texture("cuff_back",.5,.5)]*3,
                              limb,pivot,[1,1,1],1,"shirt")

    def torso(self):
        hip=self.hip_y
        self.loft([(.680,.085,.043,0,.012),(.698,.131,.078,0,.008),
                   (.723,.150,.101,0,.007),(.752,.159,.114,0,.003),
                   (.786,.141,.101,0,0)],"pelvis",0,self.root,2,"seat",20)
        # Rounded boxy work jacket with a soft dropped shoulder and nipped hem.
        rings=[(.730,.147,.109,0,.001),(.747,.164,.120,0,0),
               (.792,.170,.122,0,-.002),(.900,.165,.117,0,-.006),
               (1.016,.174,.126,0,-.010),(1.105,.193,.127,0,-.011),
               (1.150,.202,.116,0,-.009),(1.178,.185,.107,0,-.009),
               (1.198,.146,.091,0,-.008),(1.221,.087,.067,0,-.009)]
        self.jacket(rings)
        self.loft([(.739,.155,.117,0,.001),(.749,.165,.122,0,0),
                   (.763,.167,.123,0,0)],"cuff",0,self.root,1,"jacket_welt",24)
        def cloth_z(x,y):
            yy=[r[0] for r in rings]
            rx=np.interp(y,yy,[r[1] for r in rings])
            rz=np.interp(y,yy,[r[2] for r in rings])
            cz=np.interp(y,yy,[r[4] for r in rings])
            return cz-rz*math.sqrt(max(.01,1-(x/rx)**2))
        tee_rows=[]
        for y,half in [(1.219,.057),(1.204,.066),(1.179,.072),(1.155,.059),
                       (1.114,.046),(1.075,.035),(1.022,.019),(.981,.006)]:
            tee_rows.append([[x,y,cloth_z(x,y)-.0028] for x in np.linspace(-half,half,9)])
        self.panel(tee_rows,"tee","undershirt",(0,0,-1))
        self.loft([(1.191,.069,.060,0,-.013),(1.224,.067,.059,0,-.014),
                   (1.264,.063,.055,0,-.020),(1.299,.063,.054,0,-.029)],
                  "skin",9,self.head_pivot,0,"neck",16)
        for side in (-1,1):
            collar=[]
            for x1,x2,y1,y2 in [(.048,.071,1.233,1.228),(.053,.105,1.206,1.194),
                                   (.054,.109,1.179,1.166),(.056,.072,1.121,1.154)]:
                r=[]
                for u in np.linspace(0,1,5):
                    x=side*(x1*(1-u)+x2*u)
                    y=y1*(1-u)+y2*u
                    r.append([x,y,cloth_z(x,y)-.006-.008*math.sin(math.pi*u)])
                collar.append(r)
            self.panel(collar,"collar","collar",(0,0,-1))
        # Canvas sling. All front and back runs converge at the two bag attachments.
        front=[]
        for y,x in [(1.213,-.096),(1.18,-.100),(1.13,-.080),(1.06,-.050),
                    (.99,-.001),(.93,.044),(.87,.091),(.836,.119)]:
            front.append((x,y,cloth_z(x,y)-.008,.017,.005))
        self.stroke(front,"strap","strap_front")
        self.stroke([(-.096,1.205,-.064,.017,.005),(-.102,1.213,-.041,.017,.006),
                     (-.114,1.211,-.009,.017,.006),(-.116,1.201,.029,.017,.006),
                     (-.113,1.177,.071,.017,.005),(-.092,1.118,.099,.017,.006),
                     (-.041,1.036,.123,.017,.006),(.032,.953,.111,.017,.005),
                     (.103,.876,.090,.017,.005),(.147,.814,.054,.017,.005),
                     (.168,.802,.012,.017,.006),(.160,.795,-.060,.017,.006)],
                    "strap","strap_back",normal=(0,.6,1))
        self.loft([(.721,.052,.031,.116,-.095),(.732,.076,.043,.116,-.099),
                   (.751,.085,.045,.116,-.100),(.805,.085,.045,.116,-.100),
                   (.829,.077,.042,.115,-.099),(.844,.056,.034,.111,-.094)],
                  "pack",0,self.root,4,"satchel",18)
        self.loft([(.774,.061,.013,.116,-.141),(.782,.070,.014,.116,-.141),
                   (.810,.070,.013,.116,-.139),(.822,.056,.011,.116,-.136)],
                  "flap",0,self.root,4,"bag_flap",16)
        self.ellipsoid((.119,.779,-.153),(.009,.008,.004),"buckle",0,self.root,4,"snap",8)

    def arms(self,side):
        limb=1 if side<0 else 2
        pivot=(side*.187,self.shoulder_y,.003)
        def rings(data):
            return [(y,w,d,side*x,z) for y,w,d,x,z in data]
        self.loft(rings([(1.000,.050,.055,.221,.012),(1.006,.055,.061,.221,.012),
                         (1.031,.057,.062,.221,.013),(1.037,.054,.058,.220,.012)]),
                  "cuff",limb,pivot,1,"rolled_cuff",16)
        self.loft(rings([(.751,.027,.031,.236,-.039),(.781,.031,.033,.237,-.035),
                         (.834,.038,.040,.241,-.022),(.890,.043,.047,.240,.000),
                         (.941,.040,.044,.235,.021),(.975,.046,.048,.227,.022),
                         (1.030,.047,.050,.220,.013)]),
                  "skin",limb,pivot,0,"forearm",16)
        # A relaxed cupped palm has knuckles, a broad palm heel and an opposed thumb.
        self.loft(rings([(.660,.012,.014,.235,-.052),(.670,.021,.028,.240,-.048),
                         (.688,.024,.036,.242,-.047),(.708,.025,.041,.244,-.049),
                         (.732,.026,.039,.240,-.047),(.751,.024,.034,.237,-.044),
                         (.768,.024,.028,.235,-.037)]),
                  "skin",limb,pivot,0,"palm",14)
        self.stroke([(side*.222,.735,-.061,.012,.014),(side*.221,.728,-.077,.015,.014),
                     (side*.220,.716,-.085,.015,.012),(side*.216,.705,-.085,.012,.010),
                     (side*.214,.700,-.080,.005,.005)],"skin","thumb",limb,pivot,0)

    def legs(self,side):
        limb=3 if side<0 else 4
        cx=side*.100
        pivot=(cx,self.hip_y,0)
        rings=[(.104,.054,.054,cx,.004),(.119,.061,.063,cx,.005),
               (.178,.061,.062,cx,.005),(.272,.069,.072,cx,.016),
               (.344,.070,.070,cx,.015),(.396,.073,.071,cx,-.005),
               (.428,.076,.078,cx,-.004),(.519,.089,.090,cx,.004),
               (.617,.091,.108,side*.087,.010),(.688,.096,.117,side*.078,.009),
               (.726,.085,.105,side*.072,.007)]
        self.loft(rings,"pants",limb,pivot,2,"trousers",16,
                  [1,1,1,1,1,1,1,1,.97,.50,.05])
        self.loft([(.095,.054,.059,cx,.006),(.104,.063,.064,cx,.006),
                   (.134,.064,.066,cx,.006),(.14,.061,.062,cx,.006)],
                  "pants",limb,pivot,2,"ankle_cuff",16)
        self.shoe(cx,limb,pivot)

    def shoe(self,cx,limb,pivot):
        # A welt, toe spring and padded heel create a distinct sole in silhouette.
        def rows(rings):
            result=[]
            for y,w,front,back,toe_rise in rings:
                row=[]
                for k in range(20):
                    a=k*math.tau/20
                    sn,cs=math.sin(a),math.cos(a)
                    x=cx+w*math.copysign(abs(sn)**.87,sn)*(1+.06*cs)
                    z=(front if cs>0 else back)*abs(cs)**.88
                    row.append([x,y+toe_rise*max(0,cs)**3,z])
                result.append(row)
            return result
        self.grid(rows([(0,.054,-.137,.065,.005),(.005,.061,-.148,.071,.008),
                        (.018,.064,-.150,.073,.010),(.026,.063,-.148,.073,.010)]),
                  "sole",limb,pivot,4,"outsole")
        self.grid(rows([(.024,.062,-.148,.072,.010),(.034,.063,-.145,.071,.012),
                        (.049,.063,-.137,.071,.007),(.064,.061,-.119,.070,.005),
                        (.078,.058,-.094,.067,.004),(.095,.053,-.071,.062,.001),
                        (.113,.049,-.052,.060,0),(.122,.044,-.039,.057,0)]),
                  "shoe",limb,pivot,4,"trainer")
        for j,(y,front,half) in enumerate([(.070,-.118,.029),(.083,-.094,.027),
                                           (.095,-.077,.025)]):
            points=[]
            for t in np.linspace(-1,1,7):
                points.append((cx+half*t,y-.002*t*t,front+.016*t*t,.0034,.0027))
            self.stroke(points,"lace","lace%d"%j,limb,pivot,4,normal=(0,.65,-.8))
        self.stroke([(cx,.062,.070,.014,.0025),(cx,.088,.067,.015,.003),
                     (cx,.109,.064,.014,.003),(cx,.129,.056,.011,.004)],
                    "trim","heel_tab",limb,pivot,4,normal=(0,0,1))

    def build(self):
        self.torso()
        for side in (-1,1):
            self.arms(side)
            self.legs(side)
        head_start=len(self.positions)
        self.face()
        for i in range(head_start,len(self.positions)):
            x,y,z=self.positions[i]
            self.positions[i]=[x,self.head_y(y),z]
        # Average across UV islands but never across different garment pieces.
        normal_sums={}
        for part,p,n in zip(self.parts,self.positions,self.normals):
            key=(part,*np.round(p,7))
            normal_sums[key]=normal_sums.get(key,np.zeros(3))+n
        for i,(part,p) in enumerate(zip(self.parts,self.positions)):
            if part=="face":
                self.normals[i]=self.face_normals[tuple(p)]
                continue
            n=normal_sums[(part,*np.round(p,7))]
            if np.linalg.norm(n)>1e-8:
                self.normals[i]=(n/np.linalg.norm(n)).tolist()
        return self
