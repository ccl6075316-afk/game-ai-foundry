"""Author the small coastal visitor's color atlas in sRGB.

Charts are designed in the loft's UV convention (V starts at the top). A thin
extruded border surrounds each chart so material colors stay local at UV seams.
The three character appearances share the sewn panels and trim.
"""

from PIL import Image, ImageColor, ImageDraw
import numpy as np


SIZE = (64, 80)
VIEWS = ("front", "side", "back")
# Small hue shifts within each ramp give the illustrated fabrics their color.
SEA = {"shade": "#367B83", "mid": "#58A69C", "light": "#9AD2AD", "seam": "#488A8B"}
DENIM = {"shade": "#364B62", "mid": "#566C80", "light": "#778B97", "seam": "#495E72"}
CANVAS = {"shade": "#A06A42", "mid": "#CE9456", "light": "#E5B471", "seam": "#AE7648"}
CREAM = "#F3E5C9"
CORAL = "#DD795F"

COMPLEXIONS = (
    # lit, middle, shadow, flush, hair light/middle/shadow, iris light/dark
    ("#FFDEAB", "#FAC59C", "#ECAE89", "#F48E7C", "#C38D5F", "#946144", "#684736", "#A08A56", "#56462E"),
    ("#FADCA8", "#F5C795", "#DDA67C", "#F18F75", "#927263", "#64504D", "#45383A", "#988158", "#56432C"),
    ("#E7A977", "#C98C62", "#AD704E", "#CF7A60", "#806350", "#5F4940", "#463931", "#977751", "#574330"),
)


def rgb(hex_color):
    return np.asarray(ImageColor.getrgb(hex_color), dtype=float)


def wash(top, base, bottom):
    """A gentle vertically painted falloff without fixed directional shadows."""
    w, h = SIZE
    y = np.linspace(0, 1, h)
    gradient = np.transpose([np.interp(y, (0, .44, 1), ramp) for ramp in zip(rgb(top), rgb(base), rgb(bottom))])
    pixels = np.broadcast_to(gradient[:, None, :], (h, w, 3))
    return Image.fromarray(np.rint(pixels).astype(np.uint8))


def solid(color):
    return Image.new("RGB", SIZE, color)


def cloth(part, view):
    p = SEA
    patch = wash("#97C9A9", p["mid"], "#539691")
    draw = ImageDraw.Draw(patch)
    if part == "shirt":
        # Pale sea-glass shoulder panel, pieced into the deeper dyed cotton body.
        yoke = [(0,23),(12,24),(26,28),(38,28),(54,24),(63,23)]
        draw.polygon([(0,0),(63,0),*reversed(yoke)],fill="#ACD4AE")
        draw.line(yoke,fill="#86B6A2",width=3)
        draw.line([(x,y+2) for x,y in yoke],fill="#D4D9A9")
        if view == "front":
            # The model carries a separate jersey triangle and collar tabs.
            draw.polygon([(29,0),(33,0),(33,79),(30,79)], fill=p["seam"])
            draw.line((33,11,33,78), fill="#8FBBA3")
            for y in (27, 43, 59, 72):
                draw.rectangle((30,y,32,y+2), fill="#467575")
                draw.line((30,y,31,y), fill="#EFC797")
            # A sewn breast pocket sits above the satchel. Its small woven tab
            # stays readable without duplicating the fish emblem on the bag.
            draw.polygon([(39,31),(52,31),(52,41),(46,44),(39,41)], fill="#538A82")
            draw.polygon([(40,33),(51,33),(51,40),(46,42),(40,40)], fill="#659E91")
            draw.line((39,32,52,32), fill="#9CBCAA")
            draw.rectangle((49,34,52,35), fill="#DDB480")
        elif view == "back":
            draw.polygon([(0,0),(63,0),(63,19),(47,23),(29,26),(13,23),(0,19)], fill="#ABD1AD")
            draw.line([(0,19),(13,23),(29,26),(47,23),(63,19)], fill=p["seam"])
        else:
            draw.line([(32,25),(31,48),(34,72)], fill="#568D84", width=2)
        # Flat-felled hem and two short folds pooling over the waistband.
        draw.line([(7,68),(15,66),(18,66)], fill="#689E91", width=2)
        draw.line([(52,69),(47,68),(45,68)], fill="#4B847E", width=2)
        draw.rectangle((0,75,63,79), fill="#508781")
        draw.line((0,74,63,74), fill="#7CAA97")
    else:
        # Short overshirt sleeve with a folded edge; the physical cuffs carry rib trim.
        draw.rectangle((0,0,63,22),fill="#A9D0AD")
        draw.rectangle((0,22,63,25),fill="#D9DCA9")
        # Woven marina badge on the outside of each sleeve.
        if view == "side":
            draw.rounded_rectangle((22,31,39,49),radius=3,fill="#447B82")
            draw.rounded_rectangle((24,32,37,47),radius=2,fill="#F4C08C")
            draw.polygon([(24,43),(28,40),(32,44),(36,42),(36,46),(24,46)],fill="#548E95")
            draw.polygon([(27,38),(30,34),(34,38)],fill="#FFF0BC")
            draw.line([(30,0),(31,25),(32,56)], fill="#69A391", width=2)
        draw.rectangle((0,64,63,78), fill="#6A9F8E")
        draw.line((0,64,63,64), fill="#4F8680")
        draw.line((0,76,63,76), fill="#9CBD9D")
    return patch


def underlayer(part):
    if part == "cuff":
        patch = wash("#598982","#527C77","#497570")
        draw = ImageDraw.Draw(patch)
        draw.rectangle((0,38,63,70), fill="#E9B384")
        draw.rectangle((0,71,63,77), fill="#E6D7AC")
        return patch
    patch = wash("#FBEDCF","#F4E7CD","#D8C7B3")
    draw = ImageDraw.Draw(patch)
    # Large jersey bands survive the small triangular opening at the neckline.
    for y in (16, 38, 60):
        draw.rectangle((0,y,63,y+5), fill="#799F9C")
        draw.line((0,y+7,63,y+7), fill="#D5AF86")
    return patch


def trousers(view, pelvis):
    p = DENIM
    patch = wash("#61788A",p["mid"],p["shade"])
    draw = ImageDraw.Draw(patch)
    if pelvis:
        if view == "back":
            for x in (8,37):
                draw.line([(x,20),(x+1,41),(x+10,47),(x+17,42),(x+18,21)], fill=p["seam"], width=2)
            draw.line([(1,4),(31,14),(63,4)], fill=p["seam"], width=2)
        return patch
    if view == "side":
        draw.line([(31,1),(31,32),(33,52),(30,77)],fill="#677F89",width=2)
    elif view == "front":
        draw.line([(49,4),(45,11),(41,15)],fill=p["shade"],width=2)
        draw.polygon([(6,41),(12,41),(25,45),(16,44)], fill="#607788")
        draw.polygon([(55,45),(41,47),(47,45)], fill="#4F6478")
    patch.paste("#526878",(0,69,64,80))
    draw.line((0,69,63,69), fill="#384F64")
    draw.line((0,77,63,77), fill="#6C8190")
    return patch


def satchel(view):
    p = CANVAS
    patch = wash(p["light"],p["mid"],"#B78151")
    draw = ImageDraw.Draw(patch)
    if view == "front":
        draw.polygon([(0,0),(63,0),(63,31),(58,37),(10,40),(0,35)], fill="#DAA45F")
        draw.line([(0,35),(10,40),(58,37),(63,31)], fill="#986948", width=2)
        draw.line([(4,33),(12,36),(55,34)], fill="#EDC688")
        # Woven aquarium ticket patch with the silhouette of a fish.
        draw.polygon([(35,11),(51,10),(52,23),(36,24)], fill="#EEE0B1")
        draw.polygon([(37,18),(40,15),(44,14),(47,16),(50,13),(50,19),(47,18),(43,20),(40,20)],fill="#518380")
        draw.point((40,16),fill="#294B58")
        draw.rounded_rectangle((10,49,49,67), radius=3, fill="#C68D59")
        draw.line((12,51,46,51),fill="#9A6E4E",width=2)
        draw.rectangle((42,52,44,57),fill="#EBC38A")
    elif view == "back":
        draw.line([(9,20),(8,56),(12,64),(51,64),(54,58),(54,20)], fill=p["seam"], width=2)
    else:
        draw.line((26,12,28,69),fill=p["seam"],width=2)
        draw.line((30,12,31,68),fill=p["light"])
    return patch


def shoe(view):
    patch = wash("#F1DFC1", "#E6D8BC", "#C2B49D")
    draw = ImageDraw.Draw(patch)
    if view == "front":
        draw.polygon([(10,0),(55,0),(49,34),(39,44),(18,38)], fill="#527F7F")
        draw.line([(8,42),(16,50),(29,54),(44,53),(57,47)], fill="#D6C5AA", width=2)
        for x,y in ((22,48),(28,51),(34,51),(40,49)):
            draw.rectangle((x,y,x+1,y+1),fill="#C7B9A3")
    elif view == "side":
        draw.polygon([(0,9),(12,12),(33,42),(53,40),(63,29),(63,50),(49,59),(27,58),(8,33)], fill="#598D86")
        draw.line([(14,24),(32,48),(48,47)], fill="#8FB2A1", width=2)
        draw.polygon([(43,9),(57,1),(63,1),(63,11),(53,21)],fill=CORAL)
    else:
        draw.polygon([(9,0),(55,0),(51,39),(41,50),(22,49),(12,37)],fill="#5F9289")
        draw.rectangle((28,1,35,21),fill=CORAL)
        draw.line((30,5,33,5),fill=CREAM)
    return patch


def skin(view, colors, face):
    light, mid, shadow, cheek = colors[:4]
    w,h=SIZE
    yy, xx = np.mgrid[:h,:w]
    u, v = xx/(w-1), yy/(h-1)
    pixels = np.broadcast_to(rgb(mid), (h,w,3)).copy()

    def tone(color, influence):
        nonlocal pixels
        amount = np.clip(influence,0,1)[:,:,None]
        pixels = pixels*(1-amount)+rgb(color)*amount

    def oval(cx,cy,rx,ry):
        return np.exp(-((u-cx)/rx)**2-((v-cy)/ry)**2)

    # Airbrushed broad local planes, independent of the light direction.
    # Keep neck, eyelids and the separate nose within the same skin ramp.
    if face:
        tone(shadow, .22*v**3)
        if view == "front":
            tone(light, .48*oval(.50,.35,.47,.46)+.26*oval(.50,.77,.23,.16))
            tone(cheek, .79*(oval(.20,.625,.13,.089)+oval(.80,.625,.13,.089)))
            tone(cheek, .22*oval(.50,.69,.11,.05))
        elif view == "side":
            tone(cheek, .28*oval(.73,.64,.22,.12))
    else:
        tone(light, .22*oval(.52,.32,.46,.36))
        tone(shadow,.12*v**2)
    patch=Image.fromarray(np.rint(pixels).astype(np.uint8))
    if face and view=="front":
        # Short asymmetrical freckle constellations under the outer corners of the eyes.
        ink=tuple(np.rint(.55*rgb(cheek)+.28*rgb(shadow)+.17*rgb("#9C5B46")).astype(int))
        draw=ImageDraw.Draw(patch)
        for x,y in [(12,49),(15,47),(18,50),(49,48),(52,49),(46,50)]:
            draw.point((x,y),fill=ink)
    return patch


def painted_hair(part,view,colors):
    light, mid, dark=colors[4:7]
    w,h=SIZE
    yy,xx=np.mgrid[:h,:w]
    u,v=xx/(w-1),yy/(h-1)
    if part=="hair_strand":
        # A soft long reflected strip; ends of the raised lock return to cap hue.
        crest=np.sin(np.pi*v)**.72*np.exp(-((u-.49)/.32)**2)
        base=rgb(mid)
        return Image.fromarray(np.rint(base+(rgb(light)-base)*(.58*crest[:,:,None])).astype(np.uint8))

    # Differently wide swept clumps in a continuous angular domain. The loft
    # atlas shares the same front/side seam values on each side of the head.
    if view=="front":
        angle=np.arcsin(np.clip(2*u-1,-1,1))
    elif view=="back":
        angle=np.pi-np.arcsin(np.clip(1-2*u,-1,1))
    else:
        angle=np.arccos(np.clip(2*u-1,-1,1))
    angle=np.arccos(np.cos(angle))
    flow=angle+(1-v)**1.25*.82+.08*np.sin(np.pi*v)
    ridges=.6*np.cos(10.8*flow)+.24*np.cos(17.3*flow+.9)+.16*np.cos(6.4*flow-.6)
    tone=np.clip(.54+.15*np.sin(np.pi*v)-.20*v+.22*ridges,0,1)
    pixels=rgb(dark)+(rgb(light)-rgb(dark))*tone[:,:,None]
    return Image.fromarray(np.rint(pixels).astype(np.uint8))


def head_chart(part, view, colors):
    light, mid, shadow, cheek, hair_light, hair_mid, hair_dark, iris_light, iris_dark = colors
    if part in ("skin","head"):
        return skin(view,colors,part=="head")
    if part == "ear_inner":
        return wash(cheek,cheek,shadow)
    if part in ("hair","hair_light","hair_strand"):
        return painted_hair(part,view,colors)
    if part == "iris":
        return wash(iris_dark,iris_dark,iris_light)
    lookup = {"brow":hair_dark, "pupil":"#272731", "eye_white":"#FBEDD9", "glint":"#FFF7DC",
              "lip":("#C16D68","#BF7764","#935F52")[COMPLEXIONS.index(colors)]}
    return solid(lookup[part])


def clothing_chart(part, view):
    if part in ("shirt","sleeve"):
        return cloth(part,view)
    if part in ("cuff","tee"):
        return underlayer(part)
    if part in ("pants","pelvis"):
        return trousers(view,part=="pelvis")
    if part == "collar":
        patch = wash("#A6D2B0", "#83B6A2", "#7BAA99")
        draw = ImageDraw.Draw(patch)
        draw.line([(3,2),(3,49),(10,74)], fill="#CAE0B9", width=2)
        draw.line([(60,3),(60,49),(54,73)], fill="#75A69C", width=2)
        return patch
    if part == "flap":
        patch = wash("#EABA7C","#E2A967","#CF935F")
        draw = ImageDraw.Draw(patch)
        draw.rounded_rectangle((16,17,49,55),radius=4,fill="#F7DEA2")
        draw.polygon([(19,36),(25,29),(34,27),(39,31),(46,26),(46,43),(39,38),(32,43),(24,42)],fill="#488C86")
        draw.point((25,34),fill="#284E5B")
        draw.line((0,68,63,68),fill="#A47554",width=3)
        return patch
    if part == "pack":
        return satchel(view)
    if part == "shoe":
        return shoe(view)
    if part == "sole":
        patch = wash(CREAM,"#DCD0AF","#D6BF9B")
        draw=ImageDraw.Draw(patch)
        draw.rectangle((0,54,63,64),fill="#AC9279")
        draw.rectangle((0,65,63,79),fill="#AF805C")
        return patch
    if part == "strap":
        patch=solid("#DFB777")
        draw=ImageDraw.Draw(patch)
        draw.rectangle((0,0,8,79), fill="#BD905E")
        draw.rectangle((55,0,63,79), fill="#BB8A59")
        draw.line((11,0,11,79), fill="#ECCE9C", width=2)
        draw.line((51,0,51,79), fill="#ECCE9C", width=2)
        return patch
    return solid({"trim":"#E8A075","lace":"#FAEAD0","buckle":"#D9AB61","belt":"#89684F"}[part])


HEAD_KEYS = ("skin","head","ear_inner","hair","hair_light","hair_strand","brow","iris","pupil","eye_white","glint","lip")
CLOTH_KEYS = ("shirt","sleeve","tee","cuff","pants","pelvis","pack","shoe","sole","strap","trim","lace","buckle","belt","collar","flap")
ALIASES = {"face":"head","jacket":"shirt","rib":"cuff","sneaker":"shoe","laces":"lace","brass":"buckle","bag":"pack"}


def paint_guest_atlas(profile, output):
    """Set Sculpt's chart references in-place, save PNG and return atlas rects/size."""
    hero = profile["archetypes"]["adult_male"]
    charts = []
    maps = [hero["textures"]] + [form["textures"] for form in hero["appearances"]]
    for part in CLOTH_KEYS:
        for view in VIEWS:
            key=f"{part}_{view}"
            chart_id=f"guest/{key}"
            hero["textures"][key]=chart_id
            charts.append((chart_id,clothing_chart(part,view)))
    for i, appearance in enumerate(hero["appearances"]):
        for part in HEAD_KEYS:
            for view in VIEWS:
                key=f"{part}_{view}"
                chart_id=f"guest/{appearance['id']}/{key}"
                appearance["textures"][key]=chart_id
                charts.append((chart_id,head_chart(part,view,COMPLEXIONS[i])))
    for mapping in maps:
        for alias,part in ALIASES.items():
            for view in VIEWS:
                if f"{part}_{view}" in mapping:
                    mapping[f"{alias}_{view}"]=mapping[f"{part}_{view}"]

    # Identical surface views (skin, lashes, trim) can point to the same texels.
    rects={}
    unique={}
    w,h=SIZE
    atlas=Image.new("RGB",(1024,1024),"#7F7370")
    columns=atlas.width//(w+4)
    for key,chart in charts:
        signature=chart.tobytes()
        if signature not in unique:
            index=len(unique)
            x=(index%columns)*(w+4)+2
            y=(index//columns)*(h+4)+2
            if y+h+2>atlas.height:
                raise ValueError("Visitor charts exceed atlas height")
            pad=np.pad(np.asarray(chart),((2,2),(2,2),(0,0)),mode="edge")
            atlas.paste(Image.fromarray(pad),(x-2,y-2))
            unique[signature]=(x,y,w,h)
        rects[key]=unique[signature]
    used_height=((len(unique)+columns-1)//columns)*(h+4)
    atlas=atlas.crop((0,0,atlas.width,used_height))
    atlas.save(output/"visitor_atlas.png")
    return rects,atlas.size
