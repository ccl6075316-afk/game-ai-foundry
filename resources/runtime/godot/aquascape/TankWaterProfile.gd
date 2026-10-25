extends RefCounted
## Rendering properties only; independent of animal welfare / water cleanliness.
const DEFAULT := {"enabled":true,"tint":"237b98","visibility_m":9.0,"strength":0.65,"reflection":0.10,"ripple":0.28,"caustics":0.28}
const LIMITS := {"visibility_m":[2.0,30.0],"strength":[0.0,1.0],"reflection":[0.0,0.4],"ripple":[0.0,1.0],"caustics":[0.0,1.0]}
const PRESETS := [
    {"name":"清澈浅水","tint":"398ca3","visibility_m":22.0,"strength":0.45,"reflection":0.07,"ripple":0.2,"caustics":0.22},
    {"name":"蓝色观赏缸","tint":"237b98","visibility_m":9.0,"strength":0.65,"reflection":0.10,"ripple":0.28,"caustics":0.28},
    {"name":"深蓝大缸","tint":"19547b","visibility_m":5.5,"strength":0.85,"reflection":0.13,"ripple":0.22,"caustics":0.18},
    {"name":"自然淡水","tint":"537d62","visibility_m":7.0,"strength":0.65,"reflection":0.08,"ripple":0.22,"caustics":0.25}
]

static func valid(value: Variant) -> bool:
    if not value is Dictionary:return false
    if not value.get("enabled") is bool or not value.get("tint") is String:return false
    var tint: String=value.tint
    if tint.length()!=6 or not tint.is_valid_hex_number(false):return false
    for key in LIMITS:
        var n: Variant=value.get(key)
        if not (n is float or n is int) or not is_finite(float(n)) or n<LIMITS[key][0] or n>LIMITS[key][1]:return false
    return true

static func normalized(value: Dictionary={}) -> Dictionary:
    return value.duplicate(true) if valid(value) else DEFAULT.duplicate(true)

static func preset(index: int) -> Dictionary:
    var result := DEFAULT.duplicate(true)
    for key in PRESETS[clampi(index,0,PRESETS.size()-1)]:
        if key!="name":result[key]=PRESETS[index][key]
    return result
