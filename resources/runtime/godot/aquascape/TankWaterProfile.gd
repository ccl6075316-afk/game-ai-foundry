extends RefCounted
## Rendering properties only; independent of animal welfare / water cleanliness.
const DEFAULT := {"enabled":true,"tint":"2f829c","visibility_m":8.0,"strength":0.82,"reflection":0.12,"ripple":0.28,"caustics":0.44}
const LIMITS := {"visibility_m":[2.0,30.0],"strength":[0.0,1.0],"reflection":[0.0,0.4],"ripple":[0.0,1.0],"caustics":[0.0,1.0]}
const PRESETS := [
    {"name":"浅礁日光","tint":"398ba2","visibility_m":6.8,"strength":0.96,"reflection":0.14,"ripple":0.28,"caustics":0.58},
    {"name":"蓝色观赏缸","tint":"2f829c","visibility_m":8.0,"strength":0.82,"reflection":0.12,"ripple":0.28,"caustics":0.44},
    {"name":"深蓝大缸","tint":"19547b","visibility_m":6.0,"strength":0.95,"reflection":0.14,"ripple":0.22,"caustics":0.42},
    {"name":"自然淡水","tint":"4ca68a","visibility_m":7.6,"strength":0.92,"reflection":0.12,"ripple":0.24,"caustics":0.52}
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
