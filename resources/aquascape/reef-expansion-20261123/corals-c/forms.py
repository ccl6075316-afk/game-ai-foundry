"""Object-specific three-dimensional authoring functions for Batch C reef colonies."""
import math
from functools import reduce

import numpy as np


def union(a, b, radius=.035):
    t = np.maximum(1 - np.abs(a - b) / radius, 0)
    return np.minimum(a, b) - radius * .25 * t * t


def join(pieces):
    return reduce(union, pieces)


def oval(grid, pos, radii):
    return (np.sqrt(sum(((q - c) / r) ** 2 for q, c, r in zip(grid, pos, radii))) - 1) * min(radii)


def branch(grid, points, scale=(1, 1, 1)):
    """Pairs of center coordinates and normalized cross-section radii."""
    result = None
    for (start, ra), (end, rb) in zip(points, points[1:]):
        v = [(b - a) / s for a, b, s in zip(start, end, scale)]
        offset = [(q - a) / s for q, a, s in zip(grid, start, scale)]
        t = np.clip(sum(d * u for d, u in zip(offset, v)) / sum(u * u for u in v), 0, 1)
        d = np.sqrt(sum((q - t * u) ** 2 for q, u in zip(offset, v))) - (ra + (rb - ra) * t)
        d *= min(scale)
        result = d if result is None else union(result, d, .018)
    return result


def staghorn(g):
    root = oval(g, (0,.046,0), (.231,.090,.185))
    limbs = [
        [((-.01,.055,-.02),.085),((-.075,.29,-.03),.068),((-.23,.54,-.09),.053),((-.38,.74,-.09),.037),((-.43,.85,-.06),.020)],
        [((-.152,.43,-.055),.053),((-.09,.69,-.075),.043),((-.115,.93,-.12),.018)],
        [((-.045,.10,-.01),.071),((.11,.38,.048),.061),((.25,.58,.105),.052),((.43,.71,.14),.024)],
        [((.19,.49,.075),.048),((.18,.72,.10),.041),((.26,.93,.13),.019)],
        [((.035,.12,-.04),.069),((-.01,.36,-.19),.056),((.07,.56,-.33),.047),((.165,.76,-.37),.024)],
        [((.032,.47,-.268),.049),((.145,.63,-.25),.038),((.20,.80,-.26),.020)],
        [((-.026,.127,.05),.074),((-.03,.29,.175),.061),((.02,.51,.31),.045),((-.01,.65,.39),.022)],
        [((-.02,.28,.166),.050),((-.19,.42,.29),.043),((-.28,.58,.31),.023)],
        [((-.06,.155,-.027),.063),((-.27,.24,-.18),.053),((-.42,.43,-.255),.039),((-.47,.58,-.255),.022)],
    ]
    return join([root] + [branch(g, item, (1, 1.25, 1)) for item in limbs])


def sponge_shell(g, shape):
    """One irregular hollow barrel or bent tube; the subtracted blind cavity has a solid bottom."""
    x, y, z = g
    x0, z0, start, peak, rx, rz, offx, offz, phase, barrel = shape
    v = np.clip((y - start) / (peak - start), 0, 1)
    dx = (x - x0 - offx * v**1.4) / rx
    dz = (z - z0 - offz * v**1.4) / rz
    ang = np.arctan2(dz, dx)
    radial = np.hypot(dx, dz)
    rib = (0.08 if barrel else 0.04) * np.cos((6 if barrel else 5) * ang + phase + .25*v)
    taper = (.61 + .45*np.sin(v * math.pi *.75)) if barrel else (.71 + .29*v)
    top = peak + (.025 if barrel else .017) * np.cos(ang * 3 + phase) + .027*dx - .020*dz
    exterior = np.maximum.reduce(np.broadcast_arrays((radial - taper - rib) * min(rx, rz), start-y, y-top))
    inset = .265 if barrel else .245
    inner_floor = start + (peak-start) * (.31 if barrel else .30)
    inner = np.maximum((radial - taper + inset - .36*rib)*min(rx,rz), inner_floor-y)
    return exterior, inner


def tube_sponge(g):
    tubes = [
        (-.08,-.115,.045,.98,.144,.120,-.056,-.052,1.0,False),
        (-.265,.095,.04,.64,.131,.116,-.065,.045,2.2,False),
        (.152,-.135,.04,.69,.122,.111,.101,-.047,0.4,False),
        (.075,.155,.035,.44,.157,.130,.094,.077,3.5,False),
    ]
    walls, voids = zip(*(sponge_shell(g, item) for item in tubes))
    bottom = oval(g, (-.013,.058,.002), (.372,.10,.28))
    return np.maximum(join([bottom,*walls]), -np.minimum.reduce(voids))


def barrel_sponge(g):
    wall, void = sponge_shell(g, (-.035,.025,.022,.958,.45,.448,.068,-.053,1.2,True))
    root = oval(g, (-.034,.033,.018), (.279,.089,.28))
    return np.maximum(union(wall, root, .06), -void)


def elkhorn(g):
    root = oval(g, (.005,.079,.02), (.21,.135,.22))
    trunk = branch(g, [((0,.04,0),.16),((-.06,.32,.015),.121),((-.157,.45,.017),.108)])
    limbs = [
        ([((-.11,.35,.03),.14),((-.275,.52,.057),.152),((-.36,.71,.093),.13),((-.42,.845,.137),.09)], (1,.97,.54)),
        ([((-.30,.57,.063),.125),((-.4,.625,-.113),.116),((-.475,.76,-.142),.069)], (.84,1,.75)),
        ([((-.027,.25,-.01),.135),((.175,.49,.06),.145),((.329,.65,.154),.13),((.411,.76,.285),.08)], (1,.83,.74)),
        ([((.217,.52,.081),.115),((.385,.65,.053),.12),((.47,.82,-.016),.077)], (.85,1,.70)),
        ([((-.029,.26,-.009),.133),((.023,.47,-.19),.122),((.103,.68,-.35),.115),((.19,.78,-.462),.070)], (.95,.91,.88)),
        ([((.05,.53,-.24),.10),((-.092,.68,-.37),.10),((-.172,.82,-.405),.068)], (1,.89,.70)),
        ([((-.085,.25,.062),.118),((-.178,.42,.233),.116),((-.24,.59,.38),.084)], (1,.75,.85)),
    ]
    return join([root,trunk,*[branch(g,axis,scale) for axis,scale in limbs]])


def brain(g):
    x,y,z=g
    angle=np.arctan2(z/.48,x/.50)
    r=np.hypot(x/.50,z/.48)
    wriggle = .048*np.sin(5*angle + .45*np.sin(13*r)) + .025*np.cos(3*angle + .30)
    waves = .021*np.sin(32*x + 17*z + 3.7*np.sin(16*z + 4*x) + 1.3*np.sin(11*x))
    dome=(np.sqrt((r * (1+wriggle))**2 + ((y-.042)/.91)**2)-1)*.46 + waves
    shelf=oval(g,(.01,.043,-.055),(.404,.093,.372))
    return union(dome,shelf,.035)


def finger(g):
    root = oval(g,(-.012,.073,.015),(.402,.17,.363))
    fingers = [
        ((-.257,.085,-.138),(-.36,.34,-.169),(-.353,.59,-.21),.114),
        ((-.08,.075,-.208),(-.055,.49,-.22),(-.081,.812,-.258),.103),
        ((.16,.07,-.215),(.15,.43,-.17),(.208,.64,-.22),.129),
        ((.284,.075,.035),(.332,.3,.08),(.359,.51,.125),.117),
        ((.063,.089,.235),(.120,.41,.307),(.077,.66,.333),.113),
        ((-.177,.077,.18),(-.22,.462,.208),(-.182,.746,.255),.106),
        ((.015,.083,.003),(.07,.51,.005),(.014,.91,.054),.117),
        ((-.034,.092,-.09),(-.15,.40,-.054),(-.205,.58,-.098),.082),
    ]
    return join([root,*[branch(g,[(a,r),(b,r*.92),(c,r*.77)],(1,1.1,1)) for a,b,c,r in fingers]])


def lobed(g):
    lobes = [
        ((-.025,.17,-.072),(.43,.23,.39)), ((-.205,.43,.128),(.245,.40,.287)),
        ((.19,.47,-.102),(.284,.49,.29)), ((.222,.235,.262),(.24,.24,.20)),
        ((-.30,.26,-.145),(.187,.273,.221)), ((-.06,.51,-.278),(.172,.365,.205)),
        ((-.055,.315,.311),(.217,.259,.19))
    ]
    return join([oval(g,p,r) for p,r in lobes])


def crust(g):
    x,y,z=g
    ang = np.arctan2(z/.45,x/.47)
    r = np.hypot(x/.47,z/.45)
    edge = r - 1 - .09*np.cos(3*ang+.18) - .047*np.cos(8*ang+.40*r)
    relief = np.clip(1-r*r,0,1)*(.12*np.cos(17*x+10*z+np.sin(9*z))+.13*np.sin(12*z-8*x))
    height = .18 + .69*np.maximum(0,1-r*r)**.42 + relief
    return np.maximum(edge*.25, (y-height)*.28)


def table(g):
    x,y,z=g
    core = oval(g,(.071,.052,-.01),(.222,.14,.20))
    stalk = branch(g,[((.068,.05,-.013),.12),((.05,.38,.018),.108),((.011,.64,.015),.147)],(1,1.35,1))
    theta = np.arctan2(z/.42,x/.49)
    r = np.hypot(x/.49,z/.42)
    edge = r - (1+.087*np.cos(7*theta+.5)+.054*np.sin(4*theta+.2)+.048*np.cos(12*theta))
    ups = .71 + .130*x - .12*z + .13*r**1.50 + .055*np.cos(theta*5+.28)*(r**1.8)
    thickness = (.142 + .13*np.clip(1-r,0,1))
    crown = np.maximum(edge*.36, (np.abs(y-ups)-thickness*.5)*.38)
    growth = [oval(g,(u, .83+.14*u-.17*v, v),(.036,.106,.033))
              for u,v in [(-.25,.071),(-.148,-.18),(.041,.239),(.18,.16),(.277,-.18),(.376,.09),(.15,-.33),(-.215,-.28),(-.322,.206),(.060,-.088),(-.079,.04)]]
    return join([core,stalk,crown,*growth])


def curved_plate(g, spec):
    x,y,z=g
    cx,cz,rotation,arc,ry,scale=spec
    dx,dz=x-cx,z-cz
    r=np.hypot(dx,dz)
    theta=np.arctan2(dz,dx)
    dtheta=np.abs(np.arctan2(np.sin(theta-rotation),np.cos(theta-rotation)))
    wavy = .033*np.sin(7*theta + 14*r) + .020*np.cos(10*theta+.4)
    s = np.minimum(dtheta/arc,1)
    maxr = scale * (1-.44*s**3+.13*np.sin(4*theta+.67))
    height=.12+(ry-.12)*np.clip(r/maxr,0,1.4)**1.34 + r*2.02*np.sin(5*theta+.37) * .10 + wavy
    outline=np.maximum((dtheta-arc)*r,r-maxr)
    plate=(np.abs(y-height)-(.029+.038*np.maximum(1-r/maxr,0)))*.55
    return np.maximum(outline,plate)


def foliose(g):
    center=oval(g,(-.015,.085,.018),(.18,.19,.19))
    sheets=[
        (-.025,.01,2.72,1.02,.76,.49),
        (.040,.026,1.23,.90,.57,.45),
        (.060,-.022,-.72,1.32,.89,.42),
        (-.042,-.04,-2.15,.76,.59,.43),
        (.03,.040,.03,1.27,.55,.47)
    ]
    return join([center,*[curved_plate(g, item) for item in sheets]])


def scroll(g):
    x,y,z=g
    r = np.sqrt((x*.97)**2+(z*1.12)**2)
    theta = np.arctan2(z*1.12,x*.97)
    walls=[]
    for radius,peak,phase,arc in [(.362,.94,2.97,2.53),(.214,.59,2.34,2.21)]:
        turn=np.arctan2(np.sin(theta-phase),np.cos(theta-phase))
        shift = .04*np.sin(4*theta+.35)+.021*np.sin(9*theta+1.4)
        t=np.clip(y/peak,0,1.25)
        aim = radius*(.38 + .75*t) + shift*t + .025*turn
        height = peak*(1-.27*np.abs(turn/arc)**4)+.10*np.sin(theta)+.042*np.cos(theta*4)
        envelope=np.maximum.reduce(np.broadcast_arrays((y-height)*.42,(np.abs(turn)-arc)*r,(.085-y)*.4))
        walls.append(np.maximum(envelope,np.abs(r-aim)-(.026+ .015*(1-t))))
    root=oval(g,(0,.043,0),(.242,.124,.237))
    return join([root,*walls])


def rope(g):
    root=oval(g,(0,.037,0),(.151,.079,.121))
    limbs=[
        [((-.038,.034,-.003),.053),((-.222,.29,-.012),.039),((-.255,.56,.120),.026),((-.388,.73,.210),.022),((-.413,.93,.229),.011)],
        [((-.019,.034,-.04),.051),((-.078,.31,-.175),.038),((-.006,.57,-.241),.026),((-.125,.83,-.317),.020),((-.110,.974,-.359),.011)],
        [((.042,.041,-.037),.045),((.219,.31,-.091),.033),((.172,.56,-.134),.028),((.294,.73,-.142),.024),((.36,.895,-.097),.012)],
        [((.029,.037,.053),.052),((.012,.269,.217),.037),((.084,.48,.302),.031),((.064,.624,.393),.022),((-.018,.771,.402),.013)],
        [((-.056,.29,-.166),.038),((-.18,.54,-.289),.028),((-.24,.70,-.30),.019),((-.255,.82,-.295),.011)],
        [((.173,.546,-.128),.028),((.333,.662,-.264),.020),((.386,.831,-.29),.012)],
    ]
    return join([root,*[branch(g, item, (1, 1.4, 1)) for item in limbs]])


def leather(g):
    x,y,z=g
    q=x-.018
    r=np.hypot(q/.466,z/.447)
    theta=np.arctan2(z/.447,q/.466)
    root = oval(g,(-.079,.06,.034),(.21,.14,.198))
    stalk=branch(g,[((-.084,.05,.029),.16),((-.025,.34,.022),.101),((.018,.57,-.02),.128)],(1,1.2,1))
    edge=r-1-.065*np.sin(6*theta)-.043*np.cos(11*theta+.4)
    folds=(.105*np.cos(4*theta+.2)+.043*np.cos(8*theta-.8))*np.clip(r,0,1.2)**2
    h=.70+.13*x-.12*z+.17*np.clip(r,0,1.2)**1.5+folds
    crown=np.maximum(.4*edge,.43*(np.abs(y-h)-.09-.11*np.clip(1-r,0,1)))
    return join([root,stalk,crown])


def sea_fan(g):
    root=oval(g,(.006,.031,.005),(.121,.081,.18))
    trunk=branch(g,[((.006,.035,0),.052),((-.012,.22,.08),.044),((.005,.42,.096),.038),((.03,.64,.093),.022),((.048,.926,.068),.018)])
    bases=[-.98,-.75,-.48,-.23,.01,.26,.49,.72,.92]
    ribs=[]
    for i,t in enumerate(bases):
        end=np.array([t*.47,.95-.31*abs(t)**1.5+.019*math.sin(4*i),.10+.29*t*t-.16*t])
        start=np.array([.02,.18,.086])
        def at(s):
            point=(1-s)*start+s*end
            point[0] += .064*math.sin(t*math.pi)*math.sin(s*math.pi)
            point[1] += .13*abs(t)*math.sin(s*math.pi)
            point[2] -= .055*math.sin(math.pi*s*1.6)
            return tuple(point)
        ribs.append([at(t) for t in (.0,.24,.40,.56,.70,.84,1)])
    fields=[root,trunk]
    for rib in ribs:
        fields.append(branch(g,list(zip(rib,[.039,.028,.023,.020,.017,.014,.012])),(1,1,1.35)))
    for i,a in enumerate(ribs[:-1]):
        b=ribs[i+1]
        for s in (2,3,4,5):
            if (i+s)%6==0 or s==2 and i%3==1:
                continue
            p1=np.array(a[s])
            p3=.23*np.array(b[s+1])+.77*np.array(b[s])
            p2=.5*(p1+p3)+[.004,.017,-.016]
            fields.append(branch(g,[(p1,.014),(p2,.012),(p3,.013)],(1,1,1.2)))
    # Keep the modest volume and the open reticulate spaces; no alpha card.
    return join(fields)


FORMS = {
    "reef_staghorn_coral": staghorn, "reef_tube_sponge": tube_sponge,
    "reef_elkhorn_coral": elkhorn, "reef_brain_coral": brain,
    "reef_table_coral": table, "reef_finger_coral": finger,
    "reef_knob_coral": lobed, "reef_foliose_coral": foliose,
    "reef_scroll_coral": scroll, "reef_crust_coral": crust,
    "reef_sea_fan": sea_fan, "reef_rope_octocoral": rope,
    "reef_leather_octocoral": leather, "reef_barrel_sponge": barrel_sponge,
}
