extends RefCounted
static func vector(values: Array) -> Vector3:return Vector3(values[0],values[1],values[2])
static func array(value: Vector3) -> Array:return [value.x,value.y,value.z]
static func valid(row: Dictionary) -> bool:
    for key in ["rotation","stretch"]:
        if not row.has(key):continue
        if not row[key] is Array or row[key].size()!=3:return false
        for v in row[key]:
            if not (v is float or v is int) or not is_finite(float(v)):return false
            if key=="stretch" and (v<.04 or v>3):return false
    return true
static func apply(node: Node3D,row: Dictionary,multiplier:=1.0) -> void:
    node.rotation=vector(row.rotation) if row.has("rotation") else Vector3(0,row.yaw,0)
    node.scale=(vector(row.stretch) if row.has("stretch") else Vector3.ONE*row.scale)*multiplier
